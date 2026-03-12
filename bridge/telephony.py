"""
TorxFlow Telephony Bridge
=========================

WebSocket bridge between clients (Twilio/Web) and AI pipeline.

AUDIO PIPELINE (Deepgram STT + Gemini LLM + ElevenLabs TTS):
┌─────────────────────────┬──────────────┬───────────────┐
│ Stream Direction        │ Format       │ Sample Rate   │
├─────────────────────────┼──────────────┼───────────────┤
│ Twilio → Bridge         │ Mu-law       │ 8,000 Hz      │
│ Bridge → Deepgram       │ PCM Int16    │ 16,000 Hz     │
│ Deepgram → Bridge       │ JSON text    │ N/A           │
│ Bridge → Gemini LLM     │ Text         │ N/A           │
│ Gemini LLM → Bridge     │ Text         │ N/A           │
│ Bridge → ElevenLabs     │ Text         │ N/A           │
│ ElevenLabs → Bridge     │ PCM Int16    │ 24,000 Hz     │
│ Bridge (noise mix)      │ PCM Int16    │ 24,000 Hz     │
│ Bridge → Twilio         │ Mu-law       │ 8,000 Hz      │
│ Web Mic → Bridge        │ PCM Int16    │ 16,000 Hz     │
│ Bridge → Web Speaker    │ PCM Int16    │ 24,000 Hz     │
└─────────────────────────┴──────────────┴───────────────┘

Split pipeline: Deepgram (STT) → Gemini 2.5 Flash (text LLM) → ElevenLabs (TTS).
Background office noise mixed into all outgoing audio.
"""

import os
import json
import base64
import asyncio
import logging
import re
import difflib
from datetime import datetime
from pathlib import Path
from enum import Enum
from typing import Optional
from fastapi import APIRouter, WebSocket, Request, FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.websockets import WebSocketDisconnect
from dotenv import load_dotenv
from bridge.audio import AudioResampler
from bridge.deepgram_stt import DeepgramSTT
from bridge.elevenlabs import ElevenLabsStreamer
from bridge.gemini_llm import GeminiLLM
from bridge.noise import OfficeNoiseMixer
from bridge.state import get_custom_instructions


# ============================================
# CALL STATE MANAGEMENT
# ============================================

class CallState(str, Enum):
    IDLE = "idle"
    HARRY_TALKING = "harry_talking"
    PROCESSING = "processing"
    TAKEOVER = "takeover"


# Sentiment Tag Regex
SENTIMENT_PATTERN = re.compile(r"\[\[SENTIMENT:\s*(.+?)\]\]")
THOUGHT_PATTERN = re.compile(r"\[\[THOUGHT:.*?\]\]", re.DOTALL)
BOLD_HEADER_PATTERN = re.compile(r"\*\*.*?\*\*", re.DOTALL)
CONTROL_CHAR_PATTERN = re.compile(r"<ctrl\d+>")

load_dotenv()

router = APIRouter()

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")

# Tool Imports
from app.tools import (
    lookup_vehicle_rdw,
    check_apk_status,
    get_vehicle_recalls,
    web_search,
    request_appointment,
    search_available_cars,
)

# --- System Instruction ---
SYSTEM_INSTRUCTION = """
You are Harry, the friendly AI receptionist for Garage Wiefferink. Be concise (max 2 sentences). Be warm and professional.

LANGUAGE RULES (STRICT):
- Default language: Dutch.
- If the customer speaks English, switch to English for the ENTIRE rest of the call.
- Once you switch to English: EVERY response must be in English. NEVER mix in Dutch phrases, NEVER switch back to Dutch, not even for error messages or fallback phrases.
- The ONLY exception: the initial greeting is always in Dutch.

RULES:
- Before calling a tool, say a brief filler phrase like "Even kijken..." or "Momentje..." so the caller knows you're working on it. Keep it natural and short.
- NEVER say you can't help or that something is unavailable. If you cannot find what the customer needs:
  - Dutch: "Ik kan dat zo snel even niet voor u vinden. Belt u ons gerust terug op 0546-577766, dan helpen mijn collega's u graag verder!"
  - English: "I can't find that right now. Please call us back at 0546-577766 and my colleagues will be happy to help!"
  Use the language that matches the current conversation language.

GREETING:
- Greet immediately when the conversation starts. Do NOT wait for the customer to speak.
- Always start in Dutch: "Moin! Ik ben Harry van Garage Wiefferink. Waar kan ik je mee helpen?"
- Greet ONCE only. If the customer greets you, do NOT repeat your greeting. Just respond to their question.

ACCURACY — READ BACK CRITICAL DETAILS:
- Names: After the customer says their name, repeat it back: "Your name is [name], correct?" If unsure, ask them to spell it.
- Phone numbers: Read the number back digit by digit for confirmation.
- Email addresses: Read the email back character by character: "That's r-o-m-i-r dot m-a-l-i-k 13 at gmail dot com, correct?"
- If the customer corrects you, update the value and confirm again.

APPOINTMENT FLOW:
1. Ask for NAME ("Mag ik uw naam?" / "May I have your name?")
2. READ BACK name for confirmation.
3. Ask for PHONE NUMBER ("En uw telefoonnummer?" / "And your phone number?")
4. READ BACK phone number for confirmation.
5. Ask for EMAIL ("En uw e-mailadres voor de bevestiging?" / "And your email for the confirmation?")
6. READ BACK email for confirmation.
7. Ask for KENTEKEN (optional — skip for test drives of stock cars)
8. If kenteken provided → offer APK check
9. Ask for PREFERRED DATE/TIME. Minimum 3 weeks out.
   Say: "De eerstvolgende mogelijkheid is over 3 weken. Heeft u een voorkeur?" / "The earliest option is 3 weeks from now. Do you have a preference?"
10. Confirm ALL details in a summary, then IMMEDIATELY call the request_appointment tool.
    CRITICAL: You MUST call request_appointment. NEVER say the appointment is registered or confirmed without calling the tool first. If you skip the tool call, the appointment will NOT be created.
11. ONLY after request_appointment returns a successful result, say: "We sturen u een bevestigingsmail zodra de afspraak is bevestigd." / "We'll send you a confirmation email once the appointment is confirmed."
12. If request_appointment returns an error (e.g. date too soon), relay the error and ask for a new date.
13. End the call naturally after confirming. Do not keep the customer waiting.

CAR SALES FLOW:
When a customer asks about buying a car, occasions, or any vehicle for sale:
1. First, be a good car advisor! Ask about their needs:
   - "Wat voor auto zoekt u?" (type: SUV, sedan, hatchback, bedrijfswagen?)
   - "Heeft u een voorkeur voor brandstof?" (benzine, diesel, elektrisch, hybride?)
   - "Wat is uw budget ongeveer?"
   Ask 1-2 questions at a time, not all at once.
2. Once you understand their needs, call search_available_cars with relevant filters.
3. If they ask about a SPECIFIC car by name, call search_available_cars immediately with that as the brand filter.
4. Present your top 2-3 recommendations with WHY each car fits their needs.
5. Offer to schedule a test drive. When they accept, follow the APPOINTMENT FLOW.
6. Mention they can view all cars at wiefferink.com/occasions.

ENDING:
Before saying goodbye, ask: "Hoe vond u dit gesprek?" / "How did you find this conversation?" (match conversation language). Wait for feedback, then end warmly.
"""

# --- Tool Schema for Gemini ---
TOOLS_SCHEMA = [
    {
        "function_declarations": [
            {
                "name": "lookup_vehicle_rdw",
                "description": "Look up vehicle info by kenteken (Dutch license plate) from RDW database. Returns make, model, year, fuel type, and APK expiry.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "kenteken": {"type": "STRING", "description": "Dutch license plate (e.g., 'AB-123-CD' or 'AB123CD')."}
                    },
                    "required": ["kenteken"]
                }
            },
            {
                "name": "check_apk_status",
                "description": "Check APK (Dutch MOT) expiry status for a vehicle.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "kenteken": {"type": "STRING", "description": "Dutch license plate."}
                    },
                    "required": ["kenteken"]
                }
            },
            {
                "name": "get_vehicle_recalls",
                "description": "Check for active manufacturer recalls (terugroepacties) for a vehicle.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "kenteken": {"type": "STRING", "description": "Dutch license plate."}
                    },
                    "required": ["kenteken"]
                }
            },
            {
                "name": "request_appointment",
                "description": "REQUIRED: You MUST call this tool to register any appointment. Without calling it, no appointment is created. Creates a proposal for the owner to review. Minimum date: 3 weeks out. Collect name, phone, email, kenteken (optional), date_time, description BEFORE calling.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "date_time": {"type": "STRING", "description": "Date/Time (YYYY-MM-DD HH:MM). Minimum 3 weeks from today."},
                        "description": {"type": "STRING", "description": "Service description (APK, beurt, proefrit, etc.)."},
                        "customer_name": {"type": "STRING", "description": "Customer's full name."},
                        "phone_number": {"type": "STRING", "description": "Phone number."},
                        "customer_email": {"type": "STRING", "description": "Email address for confirmation."},
                        "kenteken": {"type": "STRING", "description": "Vehicle license plate (optional for test drives)."}
                    },
                    "required": ["date_time", "description", "customer_name", "phone_number", "customer_email"]
                }
            },
            {
                "name": "web_search",
                "description": "Search the internet for general information, car maintenance costs, or answers not in the database.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "query": {"type": "STRING", "description": "The search query"}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "search_available_cars",
                "description": "Search Garage Wiefferink's own car inventory (occasions). ALWAYS use this tool (not web_search) when the customer asks about any car for sale.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "budget": {"type": "STRING", "description": "Maximum price in euros (e.g., '15000')"},
                        "fuel_type": {"type": "STRING", "description": "Fuel type: benzine, diesel, elektrisch, hybride"},
                        "brand": {"type": "STRING", "description": "Car brand or model name"}
                    }
                }
            }
        ]
    }
]

def _build_system_instruction() -> str:
    """Build system instruction with any custom instructions appended."""
    custom = get_custom_instructions()
    if not custom.strip():
        return SYSTEM_INSTRUCTION
    return SYSTEM_INSTRUCTION + "\n\nCUSTOM INSTRUCTIONS FROM GARAGE OWNER (follow these with priority):\n" + custom

# Logger
logger = logging.getLogger("telephony-bridge")
logging.basicConfig(level=logging.INFO)

# ============================================
# SESSION REGISTRY (for takeover)
# ============================================

_active_sessions: dict[str, dict] = {}
# Key: "twilio" or "web", Value: {"twilio_ws": ws, "llm": GeminiLLM, "takeover": bool}

# ============================================
# MONITOR CLIENTS (dashboard broadcast)
# ============================================

_monitor_clients: set[WebSocket] = set()

async def _broadcast(message: dict):
    """Broadcast a message to all connected monitor clients."""
    global _monitor_clients
    if not _monitor_clients:
        return
    payload = json.dumps(message)
    dead: set[WebSocket] = set()
    for ws in _monitor_clients:
        try:
            await ws.send_text(payload)
        except Exception:
            dead.add(ws)
    _monitor_clients -= dead

# ============================================
# TRANSCRIPT SAVING
# ============================================

from bridge.transcripts import save_transcript as _persist_transcript


def _save_transcript(channel: str, start_time: datetime, transcript: list, tools_used: list, sentiments: list):
    """Save a conversation transcript via the transcripts module (GCS or local)."""
    filename = f"{start_time.strftime('%Y-%m-%d_%H%M%S')}_{channel}.json"
    duration_secs = int((datetime.now() - start_time).total_seconds())
    data = {
        "id": filename.replace(".json", ""),
        "channel": channel,
        "date": start_time.isoformat(),
        "duration": duration_secs,
        "message_count": len(transcript),
        "transcript": transcript,
        "tools_used": tools_used,
        "sentiments": sentiments,
    }
    _persist_transcript(filename, data)

# ============================================
# LANGUAGE DETECTION
# ============================================

DUTCH_MARKERS = {"de", "het", "een", "van", "is", "dat", "niet", "voor", "met", "zijn", "op", "aan", "er", "maar", "ook", "nog", "wel", "kan", "zou", "bij", "dit", "die", "wat", "naar", "dan", "mijn", "uw", "je", "jij", "wij", "zij", "ons", "hun", "mij", "hem", "haar", "ik", "goed", "hallo", "dank", "bedankt", "graag", "alstublieft", "ja", "nee", "hoe", "waar", "wanneer", "welke", "moin"}

def _detect_language(text: str) -> Optional[str]:
    words = set(re.findall(r'\b\w+\b', text.lower()))
    dutch_count = len(words & DUTCH_MARKERS)
    if dutch_count >= 2:
        return "Dutch"
    if len(words) >= 3 and dutch_count == 0:
        return "English"
    return None

# ============================================
# ANTI-LOOP PROTECTION
# ============================================

def _is_loop_detected(recent_responses: list[str], threshold: float = 0.8, window: int = 3) -> bool:
    if len(recent_responses) < window:
        return False
    last_n = recent_responses[-window:]
    for i in range(len(last_n)):
        for j in range(i + 1, len(last_n)):
            ratio = difflib.SequenceMatcher(None, last_n[i], last_n[j]).ratio()
            if ratio >= threshold:
                return True
    return False

# ============================================
# TOOL EXECUTION HELPER
# ============================================

def _execute_tool_sync(f_name: str, f_args: dict) -> str:
    """Execute a tool by name with given args (blocking). Returns result string."""
    if f_name == "lookup_vehicle_rdw":
        return lookup_vehicle_rdw.invoke(f_args)
    elif f_name == "check_apk_status":
        return check_apk_status.invoke(f_args)
    elif f_name == "get_vehicle_recalls":
        return get_vehicle_recalls.invoke(f_args)
    elif f_name == "request_appointment":
        return request_appointment.invoke(f_args)
    elif f_name == "web_search":
        return web_search.invoke(f_args)
    elif f_name == "search_available_cars":
        return search_available_cars.invoke(f_args)
    else:
        return f"Error: Unknown tool {f_name}"


async def _execute_tool(f_name: str, f_args: dict) -> str:
    """Execute a tool in a thread pool to avoid blocking the event loop.

    Tools use synchronous requests.get() which blocks. Running them in a
    thread keeps the WebSocket alive (Twilio pings still get answered).
    """
    return await asyncio.to_thread(_execute_tool_sync, f_name, f_args)


# ============================================
# SHARED: Tool call handler for LLM pipeline
# ============================================

async def _handle_tool_call(f_name: str, f_args: dict, session_tools_used: list, session_transcript: list,
                             session_sentiments: list, broadcast_fn, emit_vehicle_data=None) -> str:
    """Handle a tool call from GeminiLLM. Returns result string."""
    logger.info(f"Executing Tool: {f_name} with args: {f_args}")
    session_tools_used.append({"name": f_name, "args": f_args, "timestamp": datetime.now().isoformat()})
    session_transcript.append({"role": "system", "text": f"Tool: {f_name}({json.dumps(f_args)})", "timestamp": datetime.now().isoformat(), "type": "tool_call"})

    if f_name != "report_sentiment":
        await broadcast_fn({"type": "tool_call", "name": f_name, "args": f_args})

    try:
        if f_name == "report_sentiment":
            sentiment = f_args.get("sentiment", "neutral")
            session_sentiments.append(sentiment)
            result = "ok"
        elif f_name == "request_appointment":
            result = await _execute_tool(f_name, f_args)
            try:
                from bridge.email import send_owner_notification
                send_owner_notification(
                    customer_name=f_args.get("customer_name", ""),
                    phone_number=f_args.get("phone_number", ""),
                    customer_email=f_args.get("customer_email", ""),
                    date_time=f_args.get("date_time", ""),
                    description=f_args.get("description", ""),
                    kenteken=f_args.get("kenteken", ""),
                )
            except Exception as email_err:
                logger.error(f"Owner notification failed: {email_err}")
        else:
            result = await _execute_tool(f_name, f_args)
    except Exception as e:
        result = f"Tool Execution Error: {e}"

    session_transcript.append({"role": "system", "text": f"Result: {str(result)[:200]}", "timestamp": datetime.now().isoformat(), "type": "tool_result"})

    if f_name != "report_sentiment":
        await broadcast_fn({"type": "tool_result", "name": f_name, "result": str(result)[:500]})

    # Broadcast vehicle data for RDW lookups
    if f_name == "lookup_vehicle_rdw" and "Voertuig gevonden" in str(result) and emit_vehicle_data:
        try:
            await emit_vehicle_data(f_args.get("kenteken", ""))
        except Exception as ve:
            logger.error(f"vehicle_data broadcast error: {ve}")

    return str(result)


# ============================================
# TWILIO WEBSOCKET HANDLER
# ============================================

@router.websocket("/ws/twilio")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for Twilio Media Streams — Deepgram STT + Gemini LLM + ElevenLabs TTS."""
    await websocket.accept()
    logger.info("Twilio WebSocket connection accepted")

    resampler = AudioResampler()
    stream_sid = None

    session_transcript: list[dict] = []
    session_tools_used: list[dict] = []
    session_sentiments: list[str] = []
    session_start = datetime.now()
    recent_responses: list[str] = []
    loop_break_attempts = 0

    # --- Wait for Twilio "start" event to get stream_sid ---
    try:
        while True:
            message = await websocket.receive_text()
            data = json.loads(message)
            if data.get("event") == "start":
                stream_sid = data["start"]["streamSid"]
                logger.info(f"Stream started: {stream_sid}")
                break
    except (WebSocketDisconnect, Exception) as e:
        logger.error(f"Twilio WS closed before start: {e}")
        return

    # Register session
    _active_sessions["twilio"] = {
        "twilio_ws": websocket,
        "takeover": False,
        "stream_sid": stream_sid,
        "llm": None,
    }

    # Initialize pipeline components
    stt = DeepgramSTT(language="multi", sample_rate=16000)
    llm = GeminiLLM(system_instruction=_build_system_instruction(), tools_schema=TOOLS_SCHEMA)
    tts = ElevenLabsStreamer(output_format="pcm_24000")
    await tts.connect()  # Pre-connect to eliminate first-response delay
    noise_mixer = OfficeNoiseMixer(sample_rate=24000)
    is_speaking = False
    generating_task: asyncio.Task | None = None

    _active_sessions["twilio"]["llm"] = llm

    await _broadcast({"type": "call_state", "state": "harry_talking"})
    logger.info("[CALL] Harry answering Twilio call immediately")

    async def emit_vehicle_data(kenteken: str):
        clean_kt = re.sub(r'[^A-Z0-9]', '', kenteken.upper())
        from bridge.api import rdw_lookup
        rdw_data = await rdw_lookup(clean_kt)
        if isinstance(rdw_data, dict) and rdw_data.get("status") == "success":
            await _broadcast({"type": "vehicle_data", "data": rdw_data["data"]})

    try:
        await stt.connect()
        logger.info("Deepgram STT connected for Twilio call")

        # Task 1: Relay ElevenLabs audio → noise mix → Twilio
        async def relay_tts_to_twilio():
            try:
                while True:
                    try:
                        audio_chunk = await asyncio.wait_for(tts.get_audio(), timeout=0.1)
                    except asyncio.TimeoutError:
                        if _active_sessions.get("twilio", {}).get("takeover"):
                            continue
                        noise_chunk = noise_mixer.get_ambient_chunk(100)
                        mulaw_chunk = resampler.pcm_24k_to_mulaw(noise_chunk)
                        if stream_sid:
                            await websocket.send_text(json.dumps({
                                "event": "media", "streamSid": stream_sid,
                                "media": {"payload": base64.b64encode(mulaw_chunk).decode("utf-8")}
                            }))
                        continue

                    if audio_chunk is None:
                        break

                    if _active_sessions.get("twilio", {}).get("takeover"):
                        continue

                    mixed = noise_mixer.mix_into_pcm(audio_chunk)
                    mulaw_chunk = resampler.pcm_24k_to_mulaw(mixed)
                    if stream_sid:
                        await websocket.send_text(json.dumps({
                            "event": "media", "streamSid": stream_sid,
                            "media": {"payload": base64.b64encode(mulaw_chunk).decode("utf-8")}
                        }))
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(f"Error in relay_tts_to_twilio: {e}")

        tts_relay_task = asyncio.create_task(relay_tts_to_twilio())

        # Task 2: Receive Twilio audio → forward to Deepgram
        async def receive_from_twilio():
            nonlocal stream_sid
            try:
                while True:
                    message = await websocket.receive_text()
                    data = json.loads(message)
                    event = data.get("event")

                    if event == "media":
                        if _active_sessions.get("twilio", {}).get("takeover"):
                            continue
                        payload = data["media"]["payload"]
                        chunk = base64.b64decode(payload)
                        pcm_data = resampler.mulaw_to_pcm(chunk)
                        await stt.send_audio(pcm_data)

                    elif event == "stop":
                        logger.info("Twilio stream stopped")
                        break
            except WebSocketDisconnect:
                logger.info("Twilio client disconnected")
            except Exception as e:
                logger.error(f"Error in receive_from_twilio: {e}")

        # Task 3: Process Deepgram STT events → Gemini LLM → ElevenLabs TTS
        async def process_stt_pipeline():
            nonlocal is_speaking, generating_task, loop_break_attempts
            accumulated_text = ""

            # Trigger greeting immediately
            twilio_gen_start_time = 0.0

            async def generate_turn(user_text: str):
                nonlocal is_speaking, loop_break_attempts, twilio_gen_start_time
                is_speaking = True
                twilio_gen_start_time = asyncio.get_event_loop().time()
                await _broadcast({"type": "call_state", "state": "harry_talking"})
                logger.info(f"[TWILIO] generate_turn starting: '{user_text[:80]}'")

                full_response = ""

                async def on_text_chunk(chunk: str):
                    nonlocal full_response
                    full_response += chunk
                    # Clean for dashboard display
                    display = chunk
                    match = SENTIMENT_PATTERN.search(display)
                    if match:
                        await _broadcast({"type": "sentiment", "emoji": match.group(1)})
                        display = SENTIMENT_PATTERN.sub("", display)
                    display = THOUGHT_PATTERN.sub("", display)
                    display = BOLD_HEADER_PATTERN.sub("", display)
                    display = CONTROL_CHAR_PATTERN.sub("", display)
                    display = display.strip()
                    if display:
                        await _broadcast({"type": "thought", "text": display})
                        # Feed cleaned text to ElevenLabs TTS
                        await tts.send_text(display)

                async def on_tool_call(name: str, args: dict) -> str:
                    await _broadcast({"type": "call_state", "state": "processing"})
                    return await _handle_tool_call(
                        name, args, session_tools_used, session_transcript,
                        session_sentiments, _broadcast, emit_vehicle_data
                    )

                try:
                    logger.info("[TWILIO] calling llm.generate_response...")
                    await llm.generate_response(user_text, on_text_chunk, on_tool_call)
                    logger.info("[TWILIO] LLM done, flushing TTS...")
                    await tts.flush()
                    logger.info("[TWILIO] TTS flushed")
                except asyncio.CancelledError:
                    logger.info("[TWILIO] generate_turn cancelled")
                    raise
                except Exception as e:
                    logger.error(f"[TWILIO] LLM generate error: {e}", exc_info=True)

                # Transcript
                clean_response = SENTIMENT_PATTERN.sub("", full_response)
                clean_response = THOUGHT_PATTERN.sub("", clean_response)
                clean_response = BOLD_HEADER_PATTERN.sub("", clean_response)
                clean_response = CONTROL_CHAR_PATTERN.sub("", clean_response).strip()
                if clean_response:
                    session_transcript.append({"role": "assistant", "text": clean_response, "timestamp": datetime.now().isoformat(), "type": "speech"})
                    await _broadcast({"type": "transcript", "role": "assistant", "text": clean_response})

                    recent_responses.append(clean_response)
                    if len(recent_responses) > 5:
                        recent_responses.pop(0)
                    if _is_loop_detected(recent_responses):
                        loop_break_attempts += 1
                        if loop_break_attempts >= 2:
                            await llm.generate_response(
                                "Excuus, ik verstond u niet goed. Belt u ons gerust terug op 0546-577766. Tot ziens!",
                                on_text_chunk, on_tool_call
                            )
                            await tts.flush()

                llm.trim_history()
                is_speaking = False
                await _broadcast({"type": "call_state", "state": "idle"})
                logger.info(f"[TWILIO] generate_turn done: '{clean_response[:80]}'" if clean_response else "[TWILIO] generate_turn done (empty)")

            # Trigger greeting
            generating_task = asyncio.create_task(generate_turn(
                "START: Een nieuwe klant belt. Begroet de klant nu met je standaard begroeting."
            ))
            logger.info("Triggered initial AI greeting for Twilio call")

            # Helper: cancel any in-progress generation
            async def cancel_twilio_generation():
                nonlocal is_speaking, generating_task
                if generating_task and not generating_task.done():
                    llm.cancel()
                    await tts.cancel()
                    generating_task.cancel()
                    try:
                        await generating_task
                    except asyncio.CancelledError:
                        pass
                is_speaking = False

            try:
                while True:
                    event = await stt.event_queue.get()
                    if event is None:
                        break

                    if event.type == "speech_started":
                        elapsed = asyncio.get_event_loop().time() - twilio_gen_start_time
                        if is_speaking and elapsed > 1.5:
                            logger.info(f"[INTERRUPT] User speaking after {elapsed:.1f}s, cancelling")
                            await cancel_twilio_generation()
                            if stream_sid:
                                await websocket.send_text(json.dumps({"event": "clear", "streamSid": stream_sid}))

                    elif event.type == "transcript_final":
                        accumulated_text += " " + event.text

                    elif event.type == "speech_final":
                        accumulated_text += " " + event.text
                        user_text = accumulated_text.strip()
                        accumulated_text = ""
                        if user_text:
                            await cancel_twilio_generation()
                            session_transcript.append({"role": "user", "text": user_text, "timestamp": datetime.now().isoformat(), "type": "speech"})
                            await _broadcast({"type": "transcript", "role": "user", "text": user_text})
                            generating_task = asyncio.create_task(generate_turn(user_text))

                    elif event.type == "utterance_end":
                        user_text = accumulated_text.strip()
                        accumulated_text = ""
                        if user_text:
                            await cancel_twilio_generation()
                            session_transcript.append({"role": "user", "text": user_text, "timestamp": datetime.now().isoformat(), "type": "speech"})
                            await _broadcast({"type": "transcript", "role": "user", "text": user_text})
                            generating_task = asyncio.create_task(generate_turn(user_text))
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(f"Error in process_stt_pipeline: {e}")

        task1 = asyncio.create_task(receive_from_twilio())
        task2 = asyncio.create_task(process_stt_pipeline())

        done, pending = await asyncio.wait(
            [task1, task2],
            return_when=asyncio.FIRST_COMPLETED
        )

        for task in pending:
            task.cancel()

        tts_relay_task.cancel()

        if session_transcript:
            try:
                _save_transcript("twilio", session_start, session_transcript, session_tools_used, session_sentiments)
            except Exception as te:
                logger.error(f"Failed to save Twilio transcript: {te}")

    except Exception as e:
        logger.error(f"Bridge error: {e}")
        await websocket.close()
    finally:
        await tts.close()
        await stt.close()
        await _broadcast({"type": "call_state", "state": "idle"})
        _active_sessions.pop("twilio", None)


# ============================================
# WEB WEBSOCKET HANDLER
# ============================================

@router.websocket("/ws/web")
async def websocket_web_endpoint(websocket: WebSocket):
    """WebSocket endpoint for Web dashboard (owner talks to Harry or monitors calls)."""
    await websocket.accept()

    mode = websocket.query_params.get("mode", "talk")

    # --- Monitor mode: receive broadcast events from Twilio calls ---
    if mode == "monitor":
        logger.info("Web monitor client connected")
        _monitor_clients.add(websocket)

        # Send current state if Twilio call is active
        twilio_session = _active_sessions.get("twilio")
        if twilio_session:
            if twilio_session.get("takeover"):
                await websocket.send_text(json.dumps({"type": "call_state", "state": "takeover"}))
            elif twilio_session.get("llm"):
                await websocket.send_text(json.dumps({"type": "call_state", "state": "harry_talking"}))

        try:
            while True:
                msg = await websocket.receive_text()
                data = json.loads(msg)
                msg_type = data.get("type")

                if msg_type == "takeover":
                    action = data.get("action")
                    twilio_session = _active_sessions.get("twilio")
                    if action == "start" and twilio_session:
                        twilio_session["takeover"] = True
                        logger.info("[TAKEOVER] Owner taking over from monitor")
                        twilio_llm = twilio_session.get("llm")
                        if twilio_llm:
                            twilio_llm.add_context("SYSTEM: The garage owner is now speaking directly to the customer. Be completely silent.")
                        await _broadcast({"type": "call_state", "state": "takeover"})
                    elif action == "stop" and twilio_session:
                        twilio_session["takeover"] = False
                        logger.info("[TAKEOVER] Returning control to Harry from monitor")
                        twilio_llm = twilio_session.get("llm")
                        if twilio_llm:
                            twilio_llm.add_context("SYSTEM: The garage owner has finished. You (Harry) can resume the conversation.")
                        await _broadcast({"type": "call_state", "state": "harry_talking"})

                elif msg_type == "takeover_audio":
                    twilio_session = _active_sessions.get("twilio")
                    if twilio_session and twilio_session.get("takeover"):
                        twilio_ws = twilio_session.get("twilio_ws")
                        s_sid = twilio_session.get("stream_sid")
                        if twilio_ws and s_sid:
                            try:
                                b64_pcm = data.get("data", "")
                                pcm_bytes = base64.b64decode(b64_pcm)
                                r = AudioResampler()
                                mulaw_chunk = r.pcm_16k_to_mulaw(pcm_bytes)
                                media_message = {
                                    "event": "media",
                                    "streamSid": s_sid,
                                    "media": {
                                        "payload": base64.b64encode(mulaw_chunk).decode("utf-8")
                                    }
                                }
                                await twilio_ws.send_text(json.dumps(media_message))
                            except Exception as ta_err:
                                logger.error(f"Monitor takeover audio error: {ta_err}")

        except WebSocketDisconnect:
            logger.info("Monitor client disconnected")
        except Exception as e:
            logger.error(f"Monitor error: {e}")
        finally:
            _monitor_clients.discard(websocket)
        return

    # --- Talk mode: owner talks to Harry directly ---
    logger.info("Web Test WebSocket connection accepted")

    session_transcript: list[dict] = []
    session_tools_used: list[dict] = []
    session_sentiments: list[str] = []
    session_start = datetime.now()
    recent_responses: list[str] = []
    loop_break_attempts = 0

    # Initialize pipeline components
    web_stt = DeepgramSTT(language="multi", sample_rate=16000)
    web_llm = GeminiLLM(system_instruction=_build_system_instruction(), tools_schema=TOOLS_SCHEMA)
    web_tts = ElevenLabsStreamer(output_format="pcm_24000")
    await web_tts.connect()  # Pre-connect to eliminate first-response delay
    web_noise_mixer = OfficeNoiseMixer(sample_rate=24000)
    is_speaking = False
    generating_task: asyncio.Task | None = None

    async def emit_vehicle_data_web(kenteken: str):
        clean_kt = re.sub(r'[^A-Z0-9]', '', kenteken.upper())
        from bridge.api import rdw_lookup
        rdw_data = await rdw_lookup(clean_kt)
        if isinstance(rdw_data, dict) and rdw_data.get("status") == "success":
            await websocket.send_text(json.dumps({"type": "vehicle_data", "data": rdw_data["data"]}))

    async def web_broadcast(msg: dict):
        """Send to this web client (acts as its own broadcast)."""
        try:
            await websocket.send_text(json.dumps(msg))
        except Exception:
            pass

    try:
        await web_stt.connect()
        logger.info("Deepgram STT connected for Web call")

        # Task 1: Relay ElevenLabs audio → noise mix → web client
        async def relay_tts_to_web():
            try:
                while True:
                    try:
                        audio_chunk = await asyncio.wait_for(web_tts.get_audio(), timeout=1.0)
                    except asyncio.TimeoutError:
                        # No noise during idle — prevents audio buffer buildup
                        continue

                    if audio_chunk is None:
                        break
                    mixed = web_noise_mixer.mix_into_pcm(audio_chunk)
                    b64_audio = base64.b64encode(mixed).decode("utf-8")
                    await websocket.send_text(json.dumps({"type": "audio", "audio": b64_audio}))
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(f"Error in relay_tts_to_web: {e}")

        web_tts_relay_task = asyncio.create_task(relay_tts_to_web())

        # Shared: generate a turn (LLM → TTS)
        generation_start_time = 0.0

        async def generate_turn(user_text: str):
            nonlocal is_speaking, loop_break_attempts, generation_start_time
            is_speaking = True
            generation_start_time = asyncio.get_event_loop().time()
            await websocket.send_text(json.dumps({"type": "call_state", "state": "harry_talking"}))
            logger.info(f"[WEB] generate_turn starting: '{user_text[:80]}'")

            full_response = ""

            async def on_text_chunk(chunk: str):
                nonlocal full_response
                full_response += chunk
                display = chunk
                match = SENTIMENT_PATTERN.search(display)
                if match:
                    await websocket.send_text(json.dumps({"type": "sentiment", "emoji": match.group(1)}))
                    display = SENTIMENT_PATTERN.sub("", display)
                display = THOUGHT_PATTERN.sub("", display)
                display = BOLD_HEADER_PATTERN.sub("", display)
                display = CONTROL_CHAR_PATTERN.sub("", display).strip()
                if display:
                    await websocket.send_text(json.dumps({"type": "thought", "text": display}))
                    # Send cleaned text to TTS (no sentiment markers, formatting, etc.)
                    await web_tts.send_text(display)

            async def on_tool_call(name: str, args: dict) -> str:
                await websocket.send_text(json.dumps({"type": "call_state", "state": "processing"}))
                return await _handle_tool_call(
                    name, args, session_tools_used, session_transcript,
                    session_sentiments, web_broadcast, emit_vehicle_data_web
                )

            try:
                await web_llm.generate_response(user_text, on_text_chunk, on_tool_call)
                await web_tts.flush()
            except asyncio.CancelledError:
                logger.info("[WEB] generate_turn cancelled (interruption)")
                raise
            except Exception as e:
                logger.error(f"Web LLM generate error: {e}", exc_info=True)

            clean_response = SENTIMENT_PATTERN.sub("", full_response)
            clean_response = THOUGHT_PATTERN.sub("", clean_response)
            clean_response = BOLD_HEADER_PATTERN.sub("", clean_response)
            clean_response = CONTROL_CHAR_PATTERN.sub("", clean_response).strip()
            if clean_response:
                session_transcript.append({"role": "assistant", "text": clean_response, "timestamp": datetime.now().isoformat(), "type": "speech"})
                try:
                    await websocket.send_text(json.dumps({"type": "transcript", "role": "assistant", "text": clean_response}))
                except Exception:
                    pass  # WebSocket may be closed

                recent_responses.append(clean_response)
                if len(recent_responses) > 5:
                    recent_responses.pop(0)
                if _is_loop_detected(recent_responses):
                    loop_break_attempts += 1
            else:
                logger.warning(f"[WEB] generate_turn produced empty response for: '{user_text[:80]}'")

            web_llm.trim_history()
            is_speaking = False
            try:
                await websocket.send_text(json.dumps({"type": "call_state", "state": "idle"}))
            except Exception:
                pass  # WebSocket may be closed
            logger.info(f"[WEB] generate_turn done: '{clean_response[:80]}'" if clean_response else "[WEB] generate_turn done (empty)")

        # Trigger greeting
        generating_task = asyncio.create_task(generate_turn(
            "START: Een nieuwe klant is verbonden. Begroet de klant nu met je standaard begroeting."
        ))

        # Task 2: Receive from web client (audio, text, commands)
        async def receive_from_web():
            nonlocal is_speaking, generating_task
            try:
                while True:
                    message = await websocket.receive_text()
                    data = json.loads(message)
                    msg_type = data.get("type")

                    if msg_type == "audio":
                        # Decode and forward to Deepgram
                        b64_pcm = data["data"]
                        pcm_bytes = base64.b64decode(b64_pcm)
                        await web_stt.send_audio(pcm_bytes)

                    elif msg_type == "text":
                        text_content = data.get("text", "")
                        if text_content:
                            # Direct text input — bypass STT
                            session_transcript.append({"role": "user", "text": text_content, "timestamp": datetime.now().isoformat(), "type": "speech"})
                            await websocket.send_text(json.dumps({"type": "transcript", "role": "user", "text": text_content}))
                            generating_task = asyncio.create_task(generate_turn(text_content))

                    elif msg_type == "set_language":
                        lang = data.get("value", "en")
                        if lang == "nl":
                            web_llm.add_context("LANGUAGE_SWITCH: Switch to Dutch now.")
                        else:
                            web_llm.add_context("LANGUAGE_SWITCH: Switch to English now.")

                    elif msg_type == "update_prompt":
                        new_prompt = data.get("prompt", "")
                        if new_prompt:
                            web_llm.add_context(f"SYSTEM_UPDATE: From now on, follow these instructions: {new_prompt}")

                    elif msg_type == "takeover":
                        action = data.get("action")
                        twilio_session = _active_sessions.get("twilio")
                        if action == "start" and twilio_session:
                            twilio_session["takeover"] = True
                            logger.info("[TAKEOVER] Owner taking over Twilio call")
                            twilio_llm = twilio_session.get("llm")
                            if twilio_llm:
                                twilio_llm.add_context("SYSTEM: The garage owner is now speaking directly to the customer. Be completely silent.")
                            await websocket.send_text(json.dumps({"type": "call_state", "state": "takeover"}))
                        elif action == "stop" and twilio_session:
                            twilio_session["takeover"] = False
                            logger.info("[TAKEOVER] Returning control to Harry")
                            twilio_llm = twilio_session.get("llm")
                            if twilio_llm:
                                twilio_llm.add_context("SYSTEM: The garage owner has finished. You (Harry) can resume the conversation.")
                            await websocket.send_text(json.dumps({"type": "call_state", "state": "idle"}))

                    elif msg_type == "takeover_audio":
                        twilio_session = _active_sessions.get("twilio")
                        if twilio_session and twilio_session.get("takeover"):
                            twilio_ws = twilio_session.get("twilio_ws")
                            s_sid = twilio_session.get("stream_sid")
                            if twilio_ws and s_sid:
                                try:
                                    b64_pcm = data.get("data", "")
                                    pcm_bytes = base64.b64decode(b64_pcm)
                                    r = AudioResampler()
                                    mulaw_chunk = r.pcm_16k_to_mulaw(pcm_bytes)
                                    await twilio_ws.send_text(json.dumps({
                                        "event": "media", "streamSid": s_sid,
                                        "media": {"payload": base64.b64encode(mulaw_chunk).decode("utf-8")}
                                    }))
                                except Exception as ta_err:
                                    logger.error(f"Takeover audio forward error: {ta_err}")

            except WebSocketDisconnect:
                logger.info("Web client disconnected")
            except Exception as e:
                logger.error(f"Error in receive_from_web: {e}")

        # Helper: cancel any in-progress generation
        async def cancel_generation():
            nonlocal is_speaking, generating_task
            if generating_task and not generating_task.done():
                logger.info("[WEB] cancel_generation: cancelling active task")
                web_llm.cancel()
                await web_tts.cancel()
                generating_task.cancel()
                try:
                    await generating_task
                except asyncio.CancelledError:
                    pass
            elif generating_task and generating_task.done():
                # Check if previous task had an exception we missed
                exc = generating_task.exception() if not generating_task.cancelled() else None
                if exc:
                    logger.error(f"[WEB] cancel_generation: previous task had unhandled exception: {exc}")
            is_speaking = False

        # Task 3: Process Deepgram STT events — respond immediately, no debounce
        async def process_web_stt():
            nonlocal is_speaking, generating_task
            accumulated_text = ""
            logger.info("[WEB] process_web_stt started")
            try:
                while True:
                    event = await web_stt.event_queue.get()
                    if event is None:
                        logger.info("[WEB] STT event queue closed (None received)")
                        break

                    logger.info(f"[WEB] STT event: type={event.type}, text='{event.text[:80] if event.text else ''}', accumulated='{accumulated_text[:40]}', is_speaking={is_speaking}")

                    if event.type == "speech_started":
                        # Don't interrupt based on speech_started alone — it fires
                        # from TTS audio leaking into the mic (echo). Only interrupt
                        # when we get actual transcript text (speech_final/utterance_end).
                        logger.debug(f"[WEB] speech_started (is_speaking={is_speaking}) — ignoring, will interrupt on actual text")

                    elif event.type == "transcript_interim":
                        pass  # Log only, no action needed

                    elif event.type == "transcript_final":
                        accumulated_text += " " + event.text
                        logger.info(f"[WEB] Accumulated text now: '{accumulated_text.strip()[:80]}'")

                    elif event.type == "speech_final":
                        accumulated_text += " " + event.text
                        user_text = accumulated_text.strip()
                        accumulated_text = ""
                        if user_text:
                            logger.info(f"[WEB] speech_final → generating response for: '{user_text[:80]}'")
                            await cancel_generation()
                            session_transcript.append({"role": "user", "text": user_text, "timestamp": datetime.now().isoformat(), "type": "speech"})
                            await websocket.send_text(json.dumps({"type": "transcript", "role": "user", "text": user_text}))
                            generating_task = asyncio.create_task(generate_turn(user_text))
                        else:
                            logger.info("[WEB] speech_final but empty text, ignoring")

                    elif event.type == "utterance_end":
                        user_text = accumulated_text.strip()
                        accumulated_text = ""
                        if user_text:
                            logger.info(f"[WEB] utterance_end → generating response for: '{user_text[:80]}'")
                            await cancel_generation()
                            session_transcript.append({"role": "user", "text": user_text, "timestamp": datetime.now().isoformat(), "type": "speech"})
                            await websocket.send_text(json.dumps({"type": "transcript", "role": "user", "text": user_text}))
                            generating_task = asyncio.create_task(generate_turn(user_text))
                        else:
                            logger.debug("[WEB] utterance_end but no accumulated text")
            except asyncio.CancelledError:
                logger.info("[WEB] process_web_stt cancelled")
            except Exception as e:
                logger.error(f"Error in process_web_stt: {e}", exc_info=True)

        task1 = asyncio.create_task(receive_from_web())
        task2 = asyncio.create_task(process_web_stt())

        done, pending = await asyncio.wait(
            [task1, task2],
            return_when=asyncio.FIRST_COMPLETED
        )

        for task in pending:
            task.cancel()

        web_tts_relay_task.cancel()

        if session_transcript:
            try:
                _save_transcript("web", session_start, session_transcript, session_tools_used, session_sentiments)
            except Exception as te:
                logger.error(f"Failed to save Web transcript: {te}")

    except Exception as e:
        logger.error(f"Web Bridge error: {e}")
        await websocket.close()
    finally:
        await web_tts.close()
        await web_stt.close()
