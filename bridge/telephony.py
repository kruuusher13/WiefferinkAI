"""
TorxFlow Telephony Bridge
=========================

WebSocket bridge between clients (Twilio/Web) and Google Gemini Live API.

AUDIO SAMPLE RATE REFERENCE:
┌─────────────────────────┬──────────────┬───────────────┐
│ Stream Direction        │ Format       │ Sample Rate   │
├─────────────────────────┼──────────────┼───────────────┤
│ Twilio → Bridge         │ Mu-law       │ 8,000 Hz      │
│ Bridge → Gemini         │ PCM Int16    │ 16,000 Hz     │
│ Gemini → Bridge         │ PCM Int16    │ 24,000 Hz     │
│ Bridge → Twilio         │ Mu-law       │ 8,000 Hz      │
│ Web Mic → Bridge        │ PCM Int16    │ 16,000 Hz     │
│ Bridge → Web Speaker    │ PCM Int16    │ 24,000 Hz     │
└─────────────────────────┴──────────────┴───────────────┘

CRITICAL: Gemini accepts 16kHz input but outputs 24kHz audio!
"""

import os
import json
import base64
import asyncio
import logging
import websockets
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
from bridge.state import get_custom_instructions


# ============================================
# CALL STATE MANAGEMENT
# ============================================

class CallState(str, Enum):
    IDLE = "idle"
    INCOMING = "incoming"
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

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
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

# Gemini Live API Configuration
GEMINI_HOST = "generativelanguage.googleapis.com"
GEMINI_URI = os.getenv("GEMINI_URL_OVERRIDE") or f"wss://{GEMINI_HOST}/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent?key={GOOGLE_API_KEY}"
GEMINI_MODEL = "models/gemini-2.5-flash-native-audio-preview-12-2025"

# --- System Instruction ---
SYSTEM_INSTRUCTION = """
You are Harry, the friendly AI receptionist for Garage Wiefferink. Be concise (max 2 sentences). Be warm and professional.

LANGUAGE RULES (STRICT):
- Default language: Dutch.
- If the customer speaks English, switch to English for the ENTIRE rest of the call.
- Once you switch to English: EVERY response must be in English. NEVER mix in Dutch phrases, NEVER switch back to Dutch, not even for error messages or fallback phrases.
- The ONLY exception: the initial greeting is always in Dutch.

RULES:
- Before EVERY response, silently call report_sentiment with the customer's mood (happy/neutral/frustrated/sad). Never mention sentiment aloud.
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
                "name": "report_sentiment",
                "description": "Report the detected customer sentiment. Call this ONCE at the start of EVERY response BEFORE speaking. This is silent and invisible to the customer.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "sentiment": {
                            "type": "STRING",
                            "enum": ["happy", "neutral", "frustrated", "sad"],
                            "description": "The customer's current emotional state"
                        }
                    },
                    "required": ["sentiment"]
                }
            },
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
# Key: "twilio" or "web", Value: {"twilio_ws": ws, "gemini_ws": ws, "takeover": bool}

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

def _execute_tool(f_name: str, f_args: dict) -> str:
    """Execute a tool by name with given args. Returns result string."""
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


# ============================================
# TWILIO WEBSOCKET HANDLER
# ============================================

@router.websocket("/ws/twilio")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for Twilio Media Streams."""
    await websocket.accept()
    logger.info("Twilio WebSocket connection accepted")

    resampler = AudioResampler()
    stream_sid = None
    takeover_active = False

    session_transcript: list[dict] = []
    session_tools_used: list[dict] = []
    session_sentiments: list[str] = []
    session_start = datetime.now()
    recent_responses: list[str] = []
    loop_break_attempts = 0
    current_turn_text = ""

    try:
        async with websockets.connect(GEMINI_URI) as gemini_ws:
            logger.info("Connected to Gemini Live API")

            # Register session
            _active_sessions["twilio"] = {
                "twilio_ws": websocket,
                "gemini_ws": gemini_ws,
                "takeover": False,
            }

            setup_config = {
                "setup": {
                    "model": GEMINI_MODEL,
                    "systemInstruction": {
                         "parts": [{"text": _build_system_instruction()}]
                    },
                    "tools": TOOLS_SCHEMA,
                    "generation_config": {
                        "response_modalities": ["AUDIO"],
                        "speech_config": {
                            "voice_config": {
                                "prebuilt_voice_config": {
                                    "voice_name": "Orus"
                                }
                            }
                        }
                    },
                    "inputAudioTranscription": {},
                    "outputAudioTranscription": {}
                }
            }
            await gemini_ws.send(json.dumps(setup_config))
            logger.info("Sent setup config to Gemini")

            async def receive_from_twilio():
                nonlocal stream_sid
                try:
                    while True:
                        message = await websocket.receive_text()
                        data = json.loads(message)
                        event = data.get("event")

                        if event == "start":
                            stream_sid = data["start"]["streamSid"]
                            logger.info(f"Stream started: {stream_sid}")
                            # Store stream_sid for takeover audio forwarding
                            if "twilio" in _active_sessions:
                                _active_sessions["twilio"]["stream_sid"] = stream_sid

                        elif event == "media":
                            # Don't send caller audio to Gemini during takeover
                            if _active_sessions.get("twilio", {}).get("takeover"):
                                continue

                            payload = data["media"]["payload"]
                            chunk = base64.b64decode(payload)
                            pcm_data = resampler.mulaw_to_pcm(chunk)

                            realtime_input = {
                                "realtime_input": {
                                    "media_chunks": [{
                                        "mime_type": "audio/pcm",
                                        "data": base64.b64encode(pcm_data).decode("utf-8")
                                    }]
                                }
                            }
                            await gemini_ws.send(json.dumps(realtime_input))

                        elif event == "stop":
                            logger.info("Twilio stream stopped")
                            break

                except WebSocketDisconnect:
                    logger.info("Twilio client disconnected")
                except Exception as e:
                    logger.error(f"Error in receive_from_twilio: {e}")

            async def receive_from_gemini():
                nonlocal stream_sid, current_turn_text, loop_break_attempts
                pending_assistant_transcript = ""
                pending_caller_transcript = ""
                try:
                    async for message in gemini_ws:
                        response = json.loads(message)

                        if "toolCall" in response:
                            tool_calls = response["toolCall"]["functionCalls"]
                            tool_responses = []

                            for call in tool_calls:
                                f_name = call["name"]
                                f_args = call["args"]
                                call_id = call["id"]

                                logger.info(f"Executing Tool: {f_name} with args: {f_args}")
                                session_tools_used.append({"name": f_name, "args": f_args, "timestamp": datetime.now().isoformat()})
                                session_transcript.append({"role": "system", "text": f"Tool: {f_name}({json.dumps(f_args)})", "timestamp": datetime.now().isoformat(), "type": "tool_call"})

                                try:
                                    if f_name == "report_sentiment":
                                        sentiment = f_args.get("sentiment", "neutral")
                                        logger.info(f"[SENTIMENT] Twilio call: {sentiment}")
                                        session_sentiments.append(sentiment)
                                        result = "ok"
                                    elif f_name == "request_appointment":
                                        result = _execute_tool(f_name, f_args)
                                        # Fire owner notification email
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
                                        result = _execute_tool(f_name, f_args)
                                except Exception as e:
                                    result = f"Tool Execution Error: {e}"

                                session_transcript.append({"role": "system", "text": f"Result: {str(result)[:200]}", "timestamp": datetime.now().isoformat(), "type": "tool_result"})
                                tool_responses.append({
                                    "id": call_id,
                                    "name": f_name,
                                    "response": {"result": result}
                                })

                            await gemini_ws.send(json.dumps({"toolResponse": {"functionResponses": tool_responses}}))

                        if "serverContent" in response:
                            model_turn = response["serverContent"].get("modelTurn", {})
                            parts = model_turn.get("parts", [])

                            for part in parts:
                                if "inlineData" in part:
                                    mime_type = part["inlineData"]["mimeType"]
                                    if mime_type.startswith("audio"):
                                        # Suppress Gemini audio during takeover
                                        if _active_sessions.get("twilio", {}).get("takeover"):
                                            continue

                                        b64_data = part["inlineData"]["data"]
                                        pcm_data = base64.b64decode(b64_data)
                                        mulaw_chunk = resampler.pcm_24k_to_mulaw(pcm_data)

                                        if stream_sid:
                                            media_message = {
                                                "event": "media",
                                                "streamSid": stream_sid,
                                                "media": {
                                                    "payload": base64.b64encode(mulaw_chunk).decode("utf-8")
                                                }
                                            }
                                            await websocket.send_text(json.dumps(media_message))

                                if "text" in part:
                                    text_content = part["text"]
                                    match = SENTIMENT_PATTERN.search(text_content)
                                    if match:
                                        text_content = SENTIMENT_PATTERN.sub("", text_content)
                                    text_content = THOUGHT_PATTERN.sub("", text_content)
                                    text_content = BOLD_HEADER_PATTERN.sub("", text_content)
                                    text_content = CONTROL_CHAR_PATTERN.sub("", text_content)
                                    text_content = text_content.strip()
                                    if text_content:
                                        current_turn_text += " " + text_content

                        sc = response.get("serverContent", {})
                        input_transcription = (
                            response.get("inputAudioTranscription")
                            or sc.get("inputAudioTranscription")
                            or sc.get("inputTranscription")
                        )
                        if input_transcription:
                            chunk = input_transcription if isinstance(input_transcription, str) else input_transcription.get("text", "")
                            if chunk:
                                pending_caller_transcript += chunk

                        output_transcription = (
                            response.get("outputAudioTranscription")
                            or sc.get("outputAudioTranscription")
                            or sc.get("outputTranscription")
                        )
                        if output_transcription:
                            chunk = output_transcription if isinstance(output_transcription, str) else output_transcription.get("text", "")
                            if chunk:
                                pending_assistant_transcript += chunk

                        is_turn_complete = "turnComplete" in response or response.get("serverContent", {}).get("turnComplete", False)
                        if is_turn_complete:
                            if pending_caller_transcript.strip():
                                caller_text = pending_caller_transcript.strip()
                                session_transcript.append({"role": "user", "text": caller_text, "timestamp": datetime.now().isoformat(), "type": "speech"})
                                pending_caller_transcript = ""

                            if pending_assistant_transcript.strip():
                                full_text = pending_assistant_transcript.strip()
                                session_transcript.append({"role": "assistant", "text": full_text, "timestamp": datetime.now().isoformat(), "type": "speech"})
                                pending_assistant_transcript = ""

                            turn_text = current_turn_text.strip()
                            if turn_text:
                                recent_responses.append(turn_text)
                                if len(recent_responses) > 5:
                                    recent_responses.pop(0)

                                if _is_loop_detected(recent_responses):
                                    loop_break_attempts += 1
                                    logger.warning(f"[LOOP] Twilio: loop detected (attempt {loop_break_attempts})")
                                    if loop_break_attempts >= 2:
                                        goodbye_msg = {
                                            "client_content": {
                                                "turns": [{"role": "user", "parts": [{"text": "Excuus, ik verstond u niet goed. Belt u ons gerust terug op 0546-577766. Tot ziens!"}]}],
                                                "turn_complete": True
                                            }
                                        }
                                        await gemini_ws.send(json.dumps(goodbye_msg))

                            current_turn_text = ""

                except Exception as e:
                    logger.error(f"Error in receive_from_gemini: {e}")

            task1 = asyncio.create_task(receive_from_twilio())
            task2 = asyncio.create_task(receive_from_gemini())

            done, pending = await asyncio.wait(
                [task1, task2],
                return_when=asyncio.FIRST_COMPLETED
            )

            for task in pending:
                task.cancel()

            if session_transcript:
                try:
                    _save_transcript("twilio", session_start, session_transcript, session_tools_used, session_sentiments)
                except Exception as te:
                    logger.error(f"Failed to save Twilio transcript: {te}")

    except Exception as e:
        logger.error(f"Bridge error: {e}")
        await websocket.close()
    finally:
        _active_sessions.pop("twilio", None)


# ============================================
# WEB WEBSOCKET HANDLER
# ============================================

@router.websocket("/ws/web")
async def websocket_web_endpoint(websocket: WebSocket):
    """WebSocket endpoint for Web dashboard (owner talks to Harry or monitors calls)."""
    await websocket.accept()
    logger.info("Web Test WebSocket connection accepted")

    session_transcript: list[dict] = []
    session_tools_used: list[dict] = []
    session_sentiments: list[str] = []
    session_start = datetime.now()
    recent_responses: list[str] = []
    loop_break_attempts = 0
    current_turn_text = ""

    try:
        async with websockets.connect(GEMINI_URI) as gemini_ws:
            logger.info("Connected to Gemini Live API (Web Mode)")

            setup_config = {
                "setup": {
                    "model": GEMINI_MODEL,
                    "systemInstruction": {"parts": [{"text": _build_system_instruction()}]},
                    "tools": TOOLS_SCHEMA,
                    "generation_config": {
                        "response_modalities": ["AUDIO"],
                        "speech_config": {
                            "voice_config": {"prebuilt_voice_config": {"voice_name": "Orus"}}
                        }
                    },
                    "inputAudioTranscription": {},
                    "outputAudioTranscription": {}
                }
            }
            await gemini_ws.send(json.dumps(setup_config))
            logger.info("Sent Gemini setup config")

            # Trigger initial greeting with explicit instruction
            initial_msg = {
                "client_content": {
                    "turns": [{
                        "role": "user",
                        "parts": [{"text": "START: Een nieuwe klant is verbonden. Begroet de klant nu met je standaard begroeting."}]
                    }],
                    "turn_complete": True
                }
            }
            await gemini_ws.send(json.dumps(initial_msg))
            logger.info("Triggered initial AI greeting")

            last_sent_sentiment = "😐"

            async def receive_from_web():
                try:
                    while True:
                        message = await websocket.receive_text()
                        data = json.loads(message)
                        msg_type = data.get("type")

                        if msg_type == "audio":
                            b64_pcm = data["data"]
                            realtime_input = {
                                "realtime_input": {
                                    "media_chunks": [{
                                        "mime_type": "audio/pcm",
                                        "data": b64_pcm
                                    }]
                                }
                            }
                            await gemini_ws.send(json.dumps(realtime_input))

                        elif msg_type == "set_language":
                            lang = data.get("value", "en")
                            logger.info(f"Language switch requested: {lang}")
                            if lang == "nl":
                                switch_msg = {
                                    "client_content": {
                                        "turns": [{"role": "user", "parts": [{"text": "LANGUAGE_SWITCH: Switch to Dutch now."}]}],
                                        "turn_complete": True
                                    }
                                }
                            else:
                                switch_msg = {
                                    "client_content": {
                                        "turns": [{"role": "user", "parts": [{"text": "LANGUAGE_SWITCH: Switch to English now."}]}],
                                        "turn_complete": True
                                    }
                                }
                            await gemini_ws.send(json.dumps(switch_msg))

                        elif msg_type == "text":
                            text_content = data.get("text", "")
                            if text_content:
                                logger.info(f"Text message received: {text_content}")
                                text_msg = {
                                    "client_content": {
                                        "turns": [{"role": "user", "parts": [{"text": text_content}]}],
                                        "turn_complete": True
                                    }
                                }
                                await gemini_ws.send(json.dumps(text_msg))

                        elif msg_type == "update_prompt":
                            new_prompt = data.get("prompt", "")
                            if new_prompt:
                                logger.info(f"Updating system prompt to: {new_prompt[:50]}...")
                                update_msg = {
                                    "client_content": {
                                        "turns": [{"role": "user", "parts": [{"text": f"SYSTEM_UPDATE: From now on, follow these instructions: {new_prompt}"}]}],
                                        "turn_complete": True
                                    }
                                }
                                await gemini_ws.send(json.dumps(update_msg))

                        elif msg_type == "takeover":
                            action = data.get("action")
                            twilio_session = _active_sessions.get("twilio")
                            if action == "start" and twilio_session:
                                twilio_session["takeover"] = True
                                logger.info("[TAKEOVER] Owner taking over Twilio call")
                                # Tell Gemini to be silent
                                silence_msg = {
                                    "client_content": {
                                        "turns": [{"role": "user", "parts": [{"text": "SYSTEM: The garage owner is now speaking directly to the customer. Be completely silent. Do not respond with audio or text until told to resume."}]}],
                                        "turn_complete": True
                                    }
                                }
                                await twilio_session["gemini_ws"].send(json.dumps(silence_msg))
                                await websocket.send_text(json.dumps({"type": "call_state", "state": "takeover"}))
                            elif action == "stop" and twilio_session:
                                twilio_session["takeover"] = False
                                logger.info("[TAKEOVER] Returning control to Harry")
                                resume_msg = {
                                    "client_content": {
                                        "turns": [{"role": "user", "parts": [{"text": "SYSTEM: The garage owner has finished. You (Harry) can resume the conversation with the customer now."}]}],
                                        "turn_complete": True
                                    }
                                }
                                await twilio_session["gemini_ws"].send(json.dumps(resume_msg))
                                await websocket.send_text(json.dumps({"type": "call_state", "state": "idle"}))

                        elif msg_type == "takeover_audio":
                            # Owner's audio → forward to Twilio caller
                            twilio_session = _active_sessions.get("twilio")
                            if twilio_session and twilio_session.get("takeover"):
                                twilio_ws = twilio_session.get("twilio_ws")
                                if twilio_ws:
                                    try:
                                        b64_pcm = data.get("data", "")
                                        pcm_bytes = base64.b64decode(b64_pcm)
                                        resampler = AudioResampler()
                                        mulaw_chunk = resampler.pcm_16k_to_mulaw(pcm_bytes)
                                        # Get stream_sid from the Twilio session — we need it for media messages
                                        # Since we can't easily get stream_sid here, send clear event
                                        # Actually, for Twilio we need stream_sid. We'll need to store it.
                                        # For now, use a simple approach: store stream_sid in session
                                        stream_sid = twilio_session.get("stream_sid")
                                        if stream_sid:
                                            media_message = {
                                                "event": "media",
                                                "streamSid": stream_sid,
                                                "media": {
                                                    "payload": base64.b64encode(mulaw_chunk).decode("utf-8")
                                                }
                                            }
                                            await twilio_ws.send_text(json.dumps(media_message))
                                    except Exception as ta_err:
                                        logger.error(f"Takeover audio forward error: {ta_err}")

                except WebSocketDisconnect:
                    logger.info("Web client disconnected")
                except Exception as e:
                    logger.error(f"Error in receive_from_web: {e}")

            async def receive_from_gemini():
                nonlocal last_sent_sentiment, current_turn_text, loop_break_attempts
                current_state = CallState.IDLE
                pending_assistant_transcript = ""
                pending_caller_transcript = ""

                async def emit_state(new_state: CallState):
                    nonlocal current_state
                    if new_state != current_state:
                        current_state = new_state
                        await websocket.send_text(json.dumps({
                            "type": "call_state",
                            "state": new_state.value
                        }))

                try:
                    async for message in gemini_ws:
                        response = json.loads(message)

                        keys = list(response.keys())
                        sc = response.get("serverContent", {})
                        sc_keys = list(sc.keys()) if sc else []
                        if keys != ["serverContent"] or "modelTurn" not in sc:
                            logger.info(f"[GEMINI] keys={keys} serverContent_keys={sc_keys}")

                        if "serverContent" in response:
                            model_turn = response["serverContent"].get("modelTurn", {})
                            parts = model_turn.get("parts", [])

                            if parts:
                                await emit_state(CallState.HARRY_TALKING)

                            for part in parts:
                                if "inlineData" in part:
                                    b64_data = part["inlineData"]["data"]
                                    await websocket.send_text(json.dumps({
                                        "type": "audio",
                                        "audio": b64_data
                                    }))
                                if "text" in part:
                                    text_content = part["text"]

                                    match = SENTIMENT_PATTERN.search(text_content)
                                    if match:
                                        sentiment = match.group(1)
                                        await websocket.send_text(json.dumps({
                                            "type": "sentiment",
                                            "emoji": sentiment
                                        }))
                                        text_content = SENTIMENT_PATTERN.sub("", text_content)

                                    text_content = THOUGHT_PATTERN.sub("", text_content)
                                    text_content = BOLD_HEADER_PATTERN.sub("", text_content)
                                    text_content = CONTROL_CHAR_PATTERN.sub("", text_content)
                                    text_content = text_content.strip()

                                    if text_content:
                                        current_turn_text += " " + text_content
                                        await websocket.send_text(json.dumps({
                                            "type": "thought",
                                            "text": text_content
                                        }))

                        input_transcription = (
                            response.get("inputAudioTranscription")
                            or sc.get("inputAudioTranscription")
                            or sc.get("inputTranscription")
                        )
                        if input_transcription:
                            chunk = input_transcription.get("text", "") if isinstance(input_transcription, dict) else (input_transcription if isinstance(input_transcription, str) else "")
                            if chunk:
                                pending_caller_transcript += chunk

                        output_transcription = (
                            response.get("outputAudioTranscription")
                            or sc.get("outputAudioTranscription")
                            or sc.get("outputTranscription")
                        )
                        if output_transcription:
                            chunk = output_transcription.get("text", "") if isinstance(output_transcription, dict) else (output_transcription if isinstance(output_transcription, str) else "")
                            if chunk:
                                pending_assistant_transcript += chunk

                        is_turn_complete = "turnComplete" in response or response.get("serverContent", {}).get("turnComplete", False)
                        if is_turn_complete:
                            if pending_caller_transcript.strip():
                                caller_text = pending_caller_transcript.strip()
                                session_transcript.append({"role": "user", "text": caller_text, "timestamp": datetime.now().isoformat(), "type": "speech"})
                                await websocket.send_text(json.dumps({
                                    "type": "transcript",
                                    "role": "user",
                                    "text": caller_text
                                }))
                                pending_caller_transcript = ""

                            if pending_assistant_transcript.strip():
                                full_text = pending_assistant_transcript.strip()
                                session_transcript.append({"role": "assistant", "text": full_text, "timestamp": datetime.now().isoformat(), "type": "speech"})
                                await websocket.send_text(json.dumps({
                                    "type": "transcript",
                                    "role": "assistant",
                                    "text": full_text
                                }))
                                pending_assistant_transcript = ""
                            await emit_state(CallState.IDLE)

                            turn_text = current_turn_text.strip()
                            if turn_text:
                                recent_responses.append(turn_text)
                                if len(recent_responses) > 5:
                                    recent_responses.pop(0)

                                if _is_loop_detected(recent_responses):
                                    loop_break_attempts += 1
                                    logger.warning(f"[LOOP] Web: loop detected (attempt {loop_break_attempts})")
                                    if loop_break_attempts >= 2:
                                        goodbye_msg = {
                                            "client_content": {
                                                "turns": [{"role": "user", "parts": [{"text": "Excuus, ik verstond u niet goed. Belt u ons gerust terug op 0546-577766. Tot ziens!"}]}],
                                                "turn_complete": True
                                            }
                                        }
                                        await gemini_ws.send(json.dumps(goodbye_msg))

                            current_turn_text = ""

                        # Tool Handling
                        if "toolCall" in response:
                            await emit_state(CallState.PROCESSING)
                            tool_calls = response["toolCall"]["functionCalls"]
                            tool_responses = []
                            for call in tool_calls:
                                f_name = call["name"]
                                f_args = call["args"]
                                call_id = call["id"]

                                session_tools_used.append({"name": f_name, "args": f_args, "timestamp": datetime.now().isoformat()})
                                session_transcript.append({"role": "system", "text": f"Tool: {f_name}({json.dumps(f_args)})", "timestamp": datetime.now().isoformat(), "type": "tool_call"})

                                if f_name != "report_sentiment":
                                    await websocket.send_text(json.dumps({
                                        "type": "tool_call",
                                        "name": f_name,
                                        "args": f_args
                                    }))

                                try:
                                    if f_name == "report_sentiment":
                                        sentiment_map = {
                                            "happy": "🙂",
                                            "neutral": "😐",
                                            "frustrated": "😠",
                                            "sad": "😢"
                                        }
                                        sentiment = f_args.get("sentiment", "neutral")
                                        emoji = sentiment_map.get(sentiment, "😐")
                                        logger.info(f"[SENTIMENT] Web call: {sentiment} -> {emoji}")
                                        session_sentiments.append(sentiment)
                                        await websocket.send_text(json.dumps({
                                            "type": "sentiment",
                                            "emoji": emoji
                                        }))
                                        result = "ok"
                                    elif f_name == "request_appointment":
                                        result = _execute_tool(f_name, f_args)
                                        # Fire owner notification email
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
                                        result = _execute_tool(f_name, f_args)
                                except Exception as e:
                                    result = f"Tool Execution Error: {e}"

                                session_transcript.append({"role": "system", "text": f"Result: {str(result)[:200]}", "timestamp": datetime.now().isoformat(), "type": "tool_result"})

                                if f_name != "report_sentiment":
                                    await websocket.send_text(json.dumps({
                                        "type": "tool_result",
                                        "name": f_name,
                                        "result": str(result)[:500]
                                    }))

                                # Send structured vehicle_data for RDW lookups
                                if f_name == "lookup_vehicle_rdw" and "Voertuig gevonden" in str(result):
                                    try:
                                        kenteken_arg = f_args.get("kenteken", "")
                                        clean_kt = re.sub(r'[^A-Z0-9]', '', kenteken_arg.upper())
                                        from bridge.api import rdw_lookup
                                        rdw_data = await rdw_lookup(clean_kt)
                                        if isinstance(rdw_data, dict) and rdw_data.get("status") == "success":
                                            await websocket.send_text(json.dumps({
                                                "type": "vehicle_data",
                                                "data": rdw_data["data"]
                                            }))
                                    except Exception as ve:
                                        logger.error(f"vehicle_data WS send error: {ve}")

                                tool_responses.append({"id": call_id, "name": f_name, "response": {"result": result}})

                            await gemini_ws.send(json.dumps({"toolResponse": {"functionResponses": tool_responses}}))

                except Exception as e:
                    logger.error(f"Error in receive_from_gemini: {e}")

            task1 = asyncio.create_task(receive_from_web())
            task2 = asyncio.create_task(receive_from_gemini())

            done, pending = await asyncio.wait(
                [task1, task2],
                return_when=asyncio.FIRST_COMPLETED
            )

            for task in pending:
                task.cancel()

            if session_transcript:
                try:
                    _save_transcript("web", session_start, session_transcript, session_tools_used, session_sentiments)
                except Exception as te:
                    logger.error(f"Failed to save Web transcript: {te}")

    except Exception as e:
        logger.error(f"Web Bridge error: {e}")
        await websocket.close()
