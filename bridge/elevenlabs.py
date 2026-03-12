"""
ElevenLabs WebSocket Streaming TTS Client
==========================================

Streams text from Gemini to ElevenLabs and receives audio chunks back.
Supports output in PCM (for mixing) with configurable sample rates.

Text is buffered and sent at sentence/clause boundaries for smooth,
natural speech (avoids choppy word-by-word synthesis).

Auto-reconnects between conversation turns (each flush → isFinal cycle
closes the ElevenLabs WS, so a new connection is needed for the next turn).
"""

import os
import json
import base64
import asyncio
import logging
import websockets
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("elevenlabs-tts")

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "")
ELEVENLABS_MODEL_ID = os.getenv("ELEVENLABS_MODEL_ID", "eleven_flash_v2_5")

# Characters that mark a good point to trigger TTS generation
_SENTENCE_BOUNDARIES = set(".!?,;:")


class ElevenLabsStreamer:
    """
    Manages a streaming WebSocket connection to ElevenLabs TTS.

    Buffers incoming text and sends at sentence/clause boundaries so
    ElevenLabs generates smooth, natural speech instead of choppy
    word-by-word fragments.
    """

    def __init__(self, output_format: str = "pcm_16000"):
        self.output_format = output_format
        self._ws = None
        self._audio_queue: asyncio.Queue[bytes | None] = asyncio.Queue()
        self._receive_task: asyncio.Task | None = None
        self._connected = False
        self._closed = False
        self._text_buffer = ""  # Accumulates text until sentence boundary
        self._first_chunk_sent = False  # Send first chunk faster for low latency

    async def connect(self):
        """Open WebSocket connection to ElevenLabs streaming TTS."""
        if self._closed:
            return
        if not ELEVENLABS_API_KEY:
            raise ValueError("ELEVENLABS_API_KEY not set")
        if not ELEVENLABS_VOICE_ID:
            raise ValueError("ELEVENLABS_VOICE_ID not set")

        uri = (
            f"wss://api.elevenlabs.io/v1/text-to-speech/"
            f"{ELEVENLABS_VOICE_ID}/stream-input"
            f"?model_id={ELEVENLABS_MODEL_ID}"
            f"&output_format={self.output_format}"
            f"&optimize_streaming_latency=3"
        )

        self._ws = await websockets.connect(uri)
        self._connected = True

        # Send initial BOS (Beginning of Stream) message
        bos_message = {
            "text": " ",
            "voice_settings": {
                "stability": 0.4,
                "similarity_boost": 0.75,
                "use_speaker_boost": True,
            },
            "xi_api_key": ELEVENLABS_API_KEY,
        }
        await self._ws.send(json.dumps(bos_message))

        # Start background receiver
        self._receive_task = asyncio.create_task(self._receive_loop())
        logger.info(f"ElevenLabs connected (format={self.output_format})")

    async def _receive_loop(self):
        """Receive audio chunks from ElevenLabs and queue them."""
        try:
            async for msg in self._ws:
                data = json.loads(msg)
                if data.get("audio"):
                    audio_bytes = base64.b64decode(data["audio"])
                    await self._audio_queue.put(audio_bytes)
                if data.get("isFinal"):
                    self._connected = False
                    return
        except websockets.exceptions.ConnectionClosed:
            logger.debug("ElevenLabs WebSocket closed between turns")
        except Exception as e:
            logger.error(f"ElevenLabs receive error: {e}")
        finally:
            self._connected = False

    async def send_text(self, text: str):
        """Buffer text and send to ElevenLabs at clause boundaries.

        Text arrives in chunks from Gemini. We buffer and send at
        punctuation boundaries for smooth speech, but send the first
        chunk faster to minimize time-to-first-audio.
        """
        if self._closed:
            return
        if not self._connected:
            await self.connect()

        self._text_buffer += text

        # Check if buffer ends at a sentence/clause boundary
        stripped = self._text_buffer.rstrip()
        if stripped and stripped[-1] in _SENTENCE_BOUNDARIES:
            await self._send_buffer(trigger=True)
        elif not self._first_chunk_sent and len(self._text_buffer) > 15:
            # First chunk: send ASAP for fast time-to-first-audio
            await self._send_buffer(trigger=True)
        elif len(self._text_buffer) > 50:
            # Safety valve: send long buffers even without boundary
            await self._send_buffer(trigger=True)

    async def _send_buffer(self, trigger: bool = False):
        """Send accumulated text buffer to ElevenLabs."""
        if not self._text_buffer or not self._connected:
            return
        text = self._text_buffer
        self._text_buffer = ""
        self._first_chunk_sent = True
        try:
            await self._ws.send(json.dumps({
                "text": text + " ",
                "try_trigger_generation": trigger,
            }))
        except Exception as e:
            logger.error(f"ElevenLabs send error: {e}")
            self._connected = False

    async def flush(self):
        """Signal end of text input for this turn.

        Sends any remaining buffered text, then EOS.
        ElevenLabs finishes generating, sends isFinal, and closes.
        The next send_text() call will auto-reconnect.
        """
        if not self._connected or not self._ws:
            return
        try:
            # Send any remaining buffered text
            if self._text_buffer:
                await self._send_buffer(trigger=True)
            # Send EOS
            await self._ws.send(json.dumps({"text": ""}))
        except Exception as e:
            logger.error(f"ElevenLabs flush error: {e}")
        finally:
            self._first_chunk_sent = False  # Reset for next turn

    async def get_audio(self) -> bytes | None:
        """Get next audio chunk. Returns None only on permanent close."""
        return await self._audio_queue.get()

    async def cancel(self):
        """Cancel current generation (interruption).

        Closes the WebSocket and drains the audio queue.
        Next send_text() call will auto-reconnect.
        """
        self._text_buffer = ""
        self._first_chunk_sent = False
        if self._receive_task:
            self._receive_task.cancel()
            self._receive_task = None
        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
            self._ws = None
        self._connected = False
        # Drain audio queue
        while not self._audio_queue.empty():
            try:
                self._audio_queue.get_nowait()
            except asyncio.QueueEmpty:
                break
        logger.debug("ElevenLabs cancelled (interruption)")

    async def close(self):
        """Permanently close (end of call). Signals relay task to stop."""
        self._closed = True
        self._connected = False
        if self._receive_task:
            self._receive_task.cancel()
        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
        await self._audio_queue.put(None)
        logger.info("ElevenLabs connection closed permanently")
