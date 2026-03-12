"""
Deepgram Streaming STT Client
==============================

Real-time speech-to-text via Deepgram's WebSocket API.
Handles VAD (voice activity detection) and endpointing for turn-taking.
"""

import os
import json
import asyncio
import logging
import websockets
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("deepgram-stt")

DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY", "")


@dataclass
class STTEvent:
    """Event emitted by Deepgram STT."""
    type: str  # "transcript_interim", "transcript_final", "speech_final", "utterance_end", "speech_started"
    text: str = ""


class DeepgramSTT:
    """
    Streaming STT client using Deepgram Nova-2.
    Sends raw PCM audio, receives transcription events via a queue.
    """

    def __init__(self, language: str = "multi", sample_rate: int = 16000):
        self.language = language
        self.sample_rate = sample_rate
        self._ws = None
        self._receive_task: asyncio.Task | None = None
        self._connected = False
        self.event_queue: asyncio.Queue[STTEvent | None] = asyncio.Queue()

    async def connect(self):
        """Open WebSocket connection to Deepgram streaming API."""
        if not DEEPGRAM_API_KEY:
            raise ValueError("DEEPGRAM_API_KEY not set")

        params = (
            f"model=nova-2"
            f"&language={self.language}"
            f"&encoding=linear16"
            f"&sample_rate={self.sample_rate}"
            f"&channels=1"
            f"&smart_format=true"
            f"&interim_results=true"
            f"&utterance_end_ms=1000"
            f"&endpointing=300"
            f"&vad_events=true"
        )
        uri = f"wss://api.deepgram.com/v1/listen?{params}"

        self._ws = await websockets.connect(
            uri,
            extra_headers={"Authorization": f"Token {DEEPGRAM_API_KEY}"},
        )
        self._connected = True
        self._receive_task = asyncio.create_task(self._receive_loop())
        logger.info(f"Deepgram connected (lang={self.language}, rate={self.sample_rate}Hz)")

    async def send_audio(self, pcm_data: bytes):
        """Send raw PCM audio bytes to Deepgram."""
        if not self._connected or not self._ws:
            return
        try:
            await self._ws.send(pcm_data)
        except Exception as e:
            logger.error(f"Deepgram send error: {e}")
            self._connected = False
            # Auto-reconnect
            logger.info("Deepgram disconnected, attempting reconnect...")
            try:
                await self.connect()
                logger.info("Deepgram reconnected successfully")
            except Exception as re_err:
                logger.error(f"Deepgram reconnect failed: {re_err}")

    async def _receive_loop(self):
        """Background task: receive JSON events from Deepgram."""
        try:
            async for msg in self._ws:
                data = json.loads(msg)
                msg_type = data.get("type")

                if msg_type == "Results":
                    alt = data.get("channel", {}).get("alternatives", [{}])[0]
                    text = alt.get("transcript", "")
                    is_final = data.get("is_final", False)
                    speech_final = data.get("speech_final", False)

                    if text:
                        if speech_final:
                            await self.event_queue.put(STTEvent(type="speech_final", text=text))
                        elif is_final:
                            await self.event_queue.put(STTEvent(type="transcript_final", text=text))
                        else:
                            await self.event_queue.put(STTEvent(type="transcript_interim", text=text))

                elif msg_type == "UtteranceEnd":
                    await self.event_queue.put(STTEvent(type="utterance_end"))

                elif msg_type == "SpeechStarted":
                    await self.event_queue.put(STTEvent(type="speech_started"))

        except websockets.exceptions.ConnectionClosed as e:
            logger.warning(f"Deepgram WebSocket closed: {e}")
        except Exception as e:
            logger.error(f"Deepgram receive error: {e}", exc_info=True)
        finally:
            logger.warning("Deepgram receive loop exited — no more STT events will be produced")
            self._connected = False

    async def reconnect(self, language: str):
        """Reconnect with a new language without closing the event queue."""
        self._connected = False
        if self._ws:
            try:
                await self._ws.send(json.dumps({"type": "CloseStream"}))
                await self._ws.close()
            except Exception:
                pass
        if self._receive_task:
            self._receive_task.cancel()
        self.language = language
        await self.connect()
        logger.info(f"Deepgram reconnected with language={language}")

    async def close(self):
        """Close the Deepgram connection."""
        self._connected = False
        if self._ws:
            try:
                # Send CloseStream message per Deepgram protocol
                await self._ws.send(json.dumps({"type": "CloseStream"}))
                await self._ws.close()
            except Exception:
                pass
        if self._receive_task:
            self._receive_task.cancel()
        await self.event_queue.put(None)
        logger.info("Deepgram connection closed")
