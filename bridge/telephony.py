"""
GarageAI Telephony Bridge
========================

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
# CALL STATE MANAGEMENT (Component A: Live Stream)
# ============================================

class CallState(str, Enum):
    """Call states for the Live Stream status pill."""
    IDLE = "idle"
    INCOMING = "incoming"
    HARRY_TALKING = "harry_talking"
    PROCESSING = "processing"


# Sentiment Tag Regex
SENTIMENT_PATTERN = re.compile(r"\[\[SENTIMENT:\s*(.+?)\]\]")
# Thought Tag Regex (to strip internal reasoning)
THOUGHT_PATTERN = re.compile(r"\[\[THOUGHT:.*?\]\]", re.DOTALL)
# Fallback: Bold Headers (e.g. **Thinking**) - strip these too if they appear
BOLD_HEADER_PATTERN = re.compile(r"\*\*.*?\*\*", re.DOTALL)

# Load environment variables
load_dotenv()

router = APIRouter()


GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")

# Tool Imports (Restored)
# Import tools for execution
from app.tools import (
    identify_customer,
    check_werkorder_status,
    check_part_stock,
    schedule_appointment,
    generate_payment_link,
    lookup_vehicle_rdw,
    check_apk_status,
    get_vehicle_recalls,
    web_search,
    get_service_price,
    search_available_cars
)

# Gemini Live API Configuration
GEMINI_HOST = "generativelanguage.googleapis.com"
GEMINI_URI = os.getenv("GEMINI_URL_OVERRIDE") or f"wss://{GEMINI_HOST}/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent?key={GOOGLE_API_KEY}"
GEMINI_MODEL = "models/gemini-2.5-flash-native-audio-preview-12-2025"

# --- System Instruction & Tool Schema (Restored) ---
SYSTEM_INSTRUCTION = """
You are Harry, the friendly AI receptionist for Garage Wiefferink. Be concise (max 2 sentences). Be warm and professional.

RULES:
- Before EVERY response, silently call report_sentiment with the customer's mood (happy/neutral/frustrated/sad). Never mention sentiment aloud.
- NEVER say you can't help or that something is unavailable. If you cannot find what the customer needs, say: "Ik kan dat zo snel even niet voor u vinden. Belt u ons gerust terug op 0546-577766, dan helpen mijn collega's u graag verder!" (or English equivalent).
- Start in Dutch. If the customer speaks English, switch to English. Once set, NEVER switch languages for the rest of the call.

GREETING:
- Start the conversation immediately with your greeting. Do NOT wait for the customer to speak first.
- Dutch: "Moin! Ik ben Harry van Garage Wiefferink. Waar kan ik je mee helpen?"
- English: "Hi! I'm Harry from Garage Wiefferink. How can I help?"
- Greet ONCE only. Never repeat the greeting.

APPOINTMENT FLOW:
When scheduling any appointment or test drive, collect info in this EXACT order:
1. First ask for the customer's NAME ("Mag ik uw naam?")
2. Then ask for their PHONE NUMBER ("En uw telefoonnummer?")
3. Only THEN ask for their KENTEKEN / license plate ("Heeft u het kenteken bij de hand?")
4. If they don't have a kenteken (e.g. test drive for a car from our stock), skip it and proceed.
5. Offer APK check if kenteken is provided.
6. Confirm all details before calling schedule_appointment.
NEVER ask for kenteken first. Always name → phone → kenteken.

CAR SALES FLOW:
When a customer asks about buying a car, occasions, or any vehicle for sale:
1. First, be a good car advisor! Ask about their needs:
   - "Wat voor auto zoekt u?" (type: SUV, sedan, hatchback, bedrijfswagen?)
   - "Heeft u een voorkeur voor brandstof?" (benzine, diesel, elektrisch, hybride?)
   - "Wat is uw budget ongeveer?"
   - "Waar gaat u de auto vooral voor gebruiken?" (woon-werk, gezin, zakelijk?)
   Ask 1-2 questions at a time, not all at once.
2. Once you understand their needs, call search_available_cars with relevant filters (brand, fuel_type, budget).
3. If they ask about a SPECIFIC car by name (e.g. "Lynk & Co", "BMW i3"), call search_available_cars immediately with that as the brand filter.
4. Present your top 2-3 recommendations with WHY each car fits their needs. Mention price, year, km.
5. Proactively suggest alternatives: "En als u iets sportiever wilt..." or "Voor iets zuinigers hebben we ook..."
6. Offer to schedule a test drive. When they accept, follow the APPOINTMENT FLOW (name → phone → kenteken).
7. Mention they can view all cars at wiefferink.com/occasions.
8. If search returns no matches, say you'll check with colleagues and ask the customer to call back.

ENDING:
Before saying goodbye, ask: "Hoe vond u dit gesprek?" (or English equivalent). Wait for feedback, then end warmly.
"""

# Full Schema restoration
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
                "name": "identify_customer",
                "description": "Look up a customer by phone number.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "phone_number": {"type": "STRING", "description": "Phone number"}
                    },
                    "required": ["phone_number"]
                }
            },
            {
                "name": "check_werkorder_status",
                "description": "Check status of a repair work order.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "license_plate": {"type": "STRING", "description": "Vehicle license plate"}
                    },
                    "required": ["license_plate"]
                }
            },
             {
                "name": "check_part_stock",
                "description": "Check price and availability of a part.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "part_name": {"type": "STRING", "description": "Name of the part"}
                    },
                    "required": ["part_name"]
                }
            },
            {
                "name": "schedule_appointment",
                "description": "Schedule a workshop appointment. IMPORTANT: Always collect customer name, phone number AND kenteken before calling this tool.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "date_time": {"type": "STRING", "description": "Date/Time (YYYY-MM-DD HH:MM)."},
                        "description": {"type": "STRING", "description": "Service description (APK, beurt, etc.)."},
                        "customer_name": {"type": "STRING", "description": "Customer's full name."},
                        "phone_number": {"type": "STRING", "description": "Phone number for confirmation."},
                        "kenteken": {"type": "STRING", "description": "Vehicle license plate (REQUIRED)."}
                    },
                    "required": ["date_time", "description", "customer_name", "phone_number", "kenteken"]
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
                "description": "Check APK (Dutch MOT) expiry status for a vehicle. Use to inform customers about upcoming APK requirements.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "kenteken": {"type": "STRING", "description": "Dutch license plate (e.g., 'AB-123-CD' or 'AB123CD')."}
                    },
                    "required": ["kenteken"]
                }
            },
            {
                "name": "get_vehicle_recalls",
                "description": "Check for active manufacturer recalls (terugroepacties) for a vehicle. Use to inform customers about safety recalls.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "kenteken": {"type": "STRING", "description": "Dutch license plate (e.g., 'AB-123-CD' or 'AB123CD')."}
                    },
                    "required": ["kenteken"]
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
                "name": "get_service_price",
                "description": "Look up service pricing for maintenance, repairs, APK, etc. Use when customer asks 'wat kost...' or 'hoeveel is...'",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "service_type": {"type": "STRING", "description": "Service type (APK, grote beurt, remblokken, etc.)"},
                        "vehicle_info": {"type": "STRING", "description": "Vehicle make/model (optional)"}
                    },
                    "required": ["service_type"]
                }
            },
            {
                "name": "search_available_cars",
                "description": "Search Garage Wiefferink's own car inventory (occasions). ALWAYS use this tool (not web_search) when the customer asks about any car for sale, occasions, a specific car model, or buying a car. This searches our real-time stock of 50+ vehicles.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "budget": {"type": "STRING", "description": "Maximum price in euros (e.g., '15000')"},
                        "fuel_type": {"type": "STRING", "description": "Fuel type: benzine, diesel, elektrisch, hybride"},
                        "brand": {"type": "STRING", "description": "Car brand or model name (e.g., 'Volkswagen', 'Lynk', 'BMW i3')"}
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
# TRANSCRIPT SAVING
# ============================================

TRANSCRIPTS_DIR = Path(__file__).resolve().parent.parent / "transcripts"

def _save_transcript(channel: str, start_time: datetime, transcript: list, tools_used: list, sentiments: list):
    """Save a conversation transcript to a JSON file."""
    TRANSCRIPTS_DIR.mkdir(exist_ok=True)
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
    (TRANSCRIPTS_DIR / filename).write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str))
    logger.info(f"Transcript saved: {filename} ({len(transcript)} messages, {duration_secs}s)")

# ============================================
# LANGUAGE DETECTION
# ============================================

DUTCH_MARKERS = {"de", "het", "een", "van", "is", "dat", "niet", "voor", "met", "zijn", "op", "aan", "er", "maar", "ook", "nog", "wel", "kan", "zou", "bij", "dit", "die", "wat", "naar", "dan", "mijn", "uw", "je", "jij", "wij", "zij", "ons", "hun", "mij", "hem", "haar", "ik", "goed", "hallo", "dank", "bedankt", "graag", "alstublieft", "ja", "nee", "hoe", "waar", "wanneer", "welke", "moin"}

def _detect_language(text: str) -> Optional[str]:
    """Detect Dutch vs English from text using word markers. Returns 'Dutch', 'English', or None."""
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
    """Detect if Harry is looping by comparing recent responses for similarity."""
    if len(recent_responses) < window:
        return False
    last_n = recent_responses[-window:]
    for i in range(len(last_n)):
        for j in range(i + 1, len(last_n)):
            ratio = difflib.SequenceMatcher(None, last_n[i], last_n[j]).ratio()
            if ratio >= threshold:
                return True
    return False

@router.websocket("/ws/twilio")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for Twilio Media Streams.
    Acts as a bridge between Twilio (phone) and Gemini Live (AI).
    """
    await websocket.accept()
    logger.info("Twilio WebSocket connection accepted")

    resampler = AudioResampler()
    stream_sid = None

    # Session state
    session_transcript: list[dict] = []
    session_tools_used: list[dict] = []
    session_sentiments: list[str] = []
    session_start = datetime.now()
    recent_responses: list[str] = []
    loop_break_attempts = 0
    current_turn_text = ""

    try:
        # Connect to Gemini Live
        async with websockets.connect(GEMINI_URI) as gemini_ws:
            logger.info("Connected to Gemini Live API")
            
            # Initial Setup for Gemini
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
                                    "voice_name": "Fenrir"
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
                            
                        elif event == "media":
                            payload = data["media"]["payload"]
                            # Twilio sends base64 encoded 8kHz mu-law
                            chunk = base64.b64decode(payload)

                            # Resample to 16kHz PCM for Gemini
                            pcm_data = resampler.mulaw_to_pcm(chunk)

                            # Send to Gemini
                            realtime_input = {
                                "realtime_input": {
                                    "media_chunks": [
                                        {
                                            "mime_type": "audio/pcm",
                                            "data": base64.b64encode(pcm_data).decode("utf-8")
                                        }
                                    ]
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

                                # Execute Python function
                                try:
                                    if f_name == "report_sentiment":
                                        sentiment = f_args.get("sentiment", "neutral")
                                        logger.info(f"[SENTIMENT] Twilio call: {sentiment}")
                                        session_sentiments.append(sentiment)
                                        result = "ok"
                                    elif f_name == "identify_customer":
                                        result = identify_customer.invoke(f_args)
                                    elif f_name == "check_werkorder_status":
                                        result = check_werkorder_status.invoke(f_args)
                                    elif f_name == "check_part_stock":
                                        result = check_part_stock.invoke(f_args)
                                    elif f_name == "schedule_appointment":
                                        result = schedule_appointment.invoke(f_args)
                                    elif f_name == "lookup_vehicle_rdw":
                                        result = lookup_vehicle_rdw.invoke(f_args)
                                    elif f_name == "check_apk_status":
                                        result = check_apk_status.invoke(f_args)
                                    elif f_name == "get_vehicle_recalls":
                                        result = get_vehicle_recalls.invoke(f_args)
                                    elif f_name == "web_search":
                                        result = web_search.invoke(f_args)
                                    elif f_name == "get_service_price":
                                        result = get_service_price.invoke(f_args)
                                    elif f_name == "search_available_cars":
                                        result = search_available_cars.invoke(f_args)
                                    else:
                                        result = f"Error: Unknown tool {f_name}"
                                except Exception as e:
                                    result = f"Tool Execution Error: {e}"

                                session_transcript.append({"role": "system", "text": f"Result: {str(result)[:200]}", "timestamp": datetime.now().isoformat(), "type": "tool_result"})
                                tool_responses.append({
                                    "id": call_id,
                                    "name": f_name,
                                    "response": {"result": result}
                                })

                            tool_response_msg = {
                                "toolResponse": {
                                    "functionResponses": tool_responses
                                }
                            }
                            await gemini_ws.send(json.dumps(tool_response_msg))

                        # Handle Server Content (Audio)
                        if "serverContent" in response:
                            model_turn = response["serverContent"].get("modelTurn", {})
                            parts = model_turn.get("parts", [])

                            for part in parts:
                                if "inlineData" in part:
                                    mime_type = part["inlineData"]["mimeType"]
                                    if mime_type.startswith("audio"):
                                        b64_data = part["inlineData"]["data"]
                                        pcm_data = base64.b64decode(b64_data)

                                        # Gemini outputs 24kHz PCM - resample to 8kHz mu-law for Twilio
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

                                # Handle text parts (for transcription & sentiment extraction)
                                if "text" in part:
                                    text_content = part["text"]

                                    # 1. Extract Sentiment
                                    match = SENTIMENT_PATTERN.search(text_content)
                                    if match:
                                        sentiment = match.group(1)
                                        logger.info(f"Twilio Call Sentiment: {sentiment}")
                                        text_content = SENTIMENT_PATTERN.sub("", text_content)

                                    # 2. Strip Thoughts & Headers
                                    text_content = THOUGHT_PATTERN.sub("", text_content)
                                    text_content = BOLD_HEADER_PATTERN.sub("", text_content)
                                    text_content = text_content.strip()

                                    # Text parts are Gemini's internal reasoning — only use for loop detection
                                    if text_content:
                                        current_turn_text += " " + text_content

                        # Handle input audio transcription — what the CALLER actually said
                        if "inputAudioTranscription" in response:
                            transcript_text = response["inputAudioTranscription"].get("text", "")
                            if transcript_text:
                                session_transcript.append({"role": "user", "text": transcript_text, "timestamp": datetime.now().isoformat(), "type": "speech"})

                        # Handle output audio transcription — what HARRY actually said
                        if "outputAudioTranscription" in response:
                            transcript_text = response["outputAudioTranscription"].get("text", "")
                            if transcript_text:
                                session_transcript.append({"role": "assistant", "text": transcript_text, "timestamp": datetime.now().isoformat(), "type": "speech"})

                        # Handle TurnComplete
                        if "turnComplete" in response:
                            turn_text = current_turn_text.strip()
                            if turn_text:
                                recent_responses.append(turn_text)
                                if len(recent_responses) > 5:
                                    recent_responses.pop(0)

                                # Loop detection — only intervene if truly stuck
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

            # Run both listeners concurrently using wait to ensure cleanup
            task1 = asyncio.create_task(receive_from_twilio())
            task2 = asyncio.create_task(receive_from_gemini())
            
            done, pending = await asyncio.wait(
                [task1, task2],
                return_when=asyncio.FIRST_COMPLETED
            )

            for task in pending:
                task.cancel()

            # Save transcript
            if session_transcript:
                try:
                    _save_transcript("twilio", session_start, session_transcript, session_tools_used, session_sentiments)
                except Exception as te:
                    logger.error(f"Failed to save Twilio transcript: {te}")

    except Exception as e:
        logger.error(f"Bridge error: {e}")
        await websocket.close()

@router.websocket("/ws/web")
async def websocket_web_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for Local Web Test (Direct PCM, no Resampling needed if client sends 16k).
    """
    await websocket.accept()
    logger.info("Web Test WebSocket connection accepted")

    # Session state
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
            
            # Initial Setup for Gemini (matching Twilio config)
            setup_config = {
                "setup": {
                    "model": GEMINI_MODEL,
                    "systemInstruction": {"parts": [{"text": _build_system_instruction()}]},
                    "tools": TOOLS_SCHEMA,
                    "generation_config": {
                        "response_modalities": ["AUDIO"],
                        "speech_config": {
                            "voice_config": {"prebuilt_voice_config": {"voice_name": "Fenrir"}}
                        }
                    },
                    "inputAudioTranscription": {},
                    "outputAudioTranscription": {}
                }
            }
            await gemini_ws.send(json.dumps(setup_config))
            logger.info("Sent Gemini setup config")

            # --- TRIGGER INITIAL GREETING ---
            # Send a short prompt to make Harry greet first
            initial_msg = {
                "client_content": {
                    "turns": [{
                        "role": "user",
                        "parts": [{"text": "Hallo"}]
                    }],
                    "turn_complete": True
                }
            }
            await gemini_ws.send(json.dumps(initial_msg))
            logger.info("Triggered initial AI greeting")

            # Track last sent sentiment to avoid duplicate sends
            last_sent_sentiment = "😐"

            async def receive_from_web():
                try:
                    while True:
                        message = await websocket.receive_text()
                        data = json.loads(message)
                        msg_type = data.get("type")
                        
                        if msg_type == "audio":
                            # Client sends Base64 PCM 16kHz
                            b64_pcm = data["data"]

                            # Send directly to Gemini (it expects 16k/24k PCM)
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
                            # Handle language switch signal
                            lang = data.get("value", "en")
                            logger.info(f"Language switch requested: {lang}")
                            
                            # Send a text message to Gemini to trigger language switch
                            if lang == "nl":
                                switch_msg = {
                                    "client_content": {
                                        "turns": [{
                                            "role": "user",
                                            "parts": [{"text": "LANGUAGE_SWITCH: Switch to Dutch now."}]
                                        }],
                                        "turn_complete": True
                                    }
                                }
                            else:
                                switch_msg = {
                                    "client_content": {
                                        "turns": [{
                                            "role": "user",
                                            "parts": [{"text": "LANGUAGE_SWITCH: Switch to English now."}]
                                        }],
                                        "turn_complete": True
                                    }
                                }
                            await gemini_ws.send(json.dumps(switch_msg))
                        
                        elif msg_type == "text":
                            # Handle text chat input
                            text_content = data.get("text", "")
                            if text_content:
                                logger.info(f"Text message received: {text_content}")
                                text_msg = {
                                    "client_content": {
                                        "turns": [{
                                            "role": "user",
                                            "parts": [{"text": text_content}]
                                        }],
                                        "turn_complete": True
                                    }
                                }
                                await gemini_ws.send(json.dumps(text_msg))
                        
                        elif msg_type == "update_prompt":
                            # Dynamically update the system instruction for prototyping
                            new_prompt = data.get("prompt", "")
                            if new_prompt:
                                logger.info(f"Updating system prompt to: {new_prompt[:50]}...")
                                update_msg = {
                                    "client_content": {
                                        "turns": [{
                                            "role": "user",
                                            "parts": [{"text": f"SYSTEM_UPDATE: From now on, follow these instructions: {new_prompt}"}]
                                        }],
                                        "turn_complete": True
                                    }
                                }
                                await gemini_ws.send(json.dumps(update_msg))
                except WebSocketDisconnect:
                    logger.info("Web client disconnected")
                except Exception as e:
                    logger.error(f"Error in receive_from_web: {e}")

            async def receive_from_gemini():
                nonlocal last_sent_sentiment, current_turn_text, loop_break_attempts
                current_state = CallState.IDLE

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

                        # Debug: Log all response types from Gemini
                        keys = list(response.keys())
                        if keys != ["serverContent"] or "modelTurn" not in response.get("serverContent", {}):
                            logger.info(f"[GEMINI] Response type: {keys}")

                        # Audio Handling - Harry is talking
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

                                    # 1. Extract Sentiment (from text tags)
                                    match = SENTIMENT_PATTERN.search(text_content)
                                    if match:
                                        sentiment = match.group(1)
                                        await websocket.send_text(json.dumps({
                                            "type": "sentiment",
                                            "emoji": sentiment
                                        }))
                                        text_content = SENTIMENT_PATTERN.sub("", text_content)

                                    # 2. Strip Thoughts & Bold Headers
                                    text_content = THOUGHT_PATTERN.sub("", text_content)
                                    text_content = BOLD_HEADER_PATTERN.sub("", text_content)
                                    text_content = text_content.strip()

                                    # Text parts are Gemini's internal reasoning
                                    # Send as "thought" (separate from speech transcript)
                                    if text_content:
                                        current_turn_text += " " + text_content
                                        await websocket.send_text(json.dumps({
                                            "type": "thought",
                                            "text": text_content
                                        }))

                        # Handle input audio transcription - What the CALLER actually said
                        if "inputAudioTranscription" in response:
                            transcript_text = response["inputAudioTranscription"].get("text", "")
                            if transcript_text:
                                session_transcript.append({"role": "user", "text": transcript_text, "timestamp": datetime.now().isoformat(), "type": "speech"})
                                await websocket.send_text(json.dumps({
                                    "type": "transcript",
                                    "role": "user",
                                    "text": transcript_text
                                }))
                                await emit_state(CallState.INCOMING)

                        # Handle output audio transcription
                        if "outputAudioTranscription" in response:
                            transcript_text = response["outputAudioTranscription"].get("text", "")
                            if transcript_text:
                                session_transcript.append({"role": "assistant", "text": transcript_text, "timestamp": datetime.now().isoformat(), "type": "speech"})
                                await websocket.send_text(json.dumps({
                                    "type": "transcript",
                                    "role": "assistant",
                                    "text": transcript_text
                                }))

                        # Turn complete - back to listening
                        if "turnComplete" in response:
                            await emit_state(CallState.IDLE)

                            turn_text = current_turn_text.strip()
                            if turn_text:
                                recent_responses.append(turn_text)
                                if len(recent_responses) > 5:
                                    recent_responses.pop(0)

                                # Loop detection — only intervene if truly stuck
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

                        # Tool Handling - Now with UI notifications + transcript collection
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

                                # Notify frontend about tool call (skip sentiment)
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
                                    elif f_name == "identify_customer": result = identify_customer.invoke(f_args)
                                    elif f_name == "check_werkorder_status": result = check_werkorder_status.invoke(f_args)
                                    elif f_name == "check_part_stock": result = check_part_stock.invoke(f_args)
                                    elif f_name == "schedule_appointment": result = schedule_appointment.invoke(f_args)
                                    elif f_name == "lookup_vehicle_rdw": result = lookup_vehicle_rdw.invoke(f_args)
                                    elif f_name == "check_apk_status": result = check_apk_status.invoke(f_args)
                                    elif f_name == "get_vehicle_recalls": result = get_vehicle_recalls.invoke(f_args)
                                    elif f_name == "web_search": result = web_search.invoke(f_args)
                                    elif f_name == "get_service_price": result = get_service_price.invoke(f_args)
                                    elif f_name == "search_available_cars": result = search_available_cars.invoke(f_args)
                                    else: result = f"Error: Unknown tool {f_name}"
                                except Exception as e:
                                    result = f"Tool Execution Error: {e}"

                                session_transcript.append({"role": "system", "text": f"Result: {str(result)[:200]}", "timestamp": datetime.now().isoformat(), "type": "tool_result"})

                                # Notify frontend about tool result (skip sentiment)
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

            # Run concurrently using wait to ensure cleanup
            task1 = asyncio.create_task(receive_from_web())
            task2 = asyncio.create_task(receive_from_gemini())
            
            done, pending = await asyncio.wait(
                [task1, task2],
                return_when=asyncio.FIRST_COMPLETED
            )

            for task in pending:
                task.cancel()

            # Save transcript
            if session_transcript:
                try:
                    _save_transcript("web", session_start, session_transcript, session_tools_used, session_sentiments)
                except Exception as te:
                    logger.error(f"Failed to save Web transcript: {te}")

    except Exception as e:
        logger.error(f"Web Bridge error: {e}")
        await websocket.close()