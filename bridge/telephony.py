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
from fastapi import APIRouter, WebSocket, Request, FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.websockets import WebSocketDisconnect
from dotenv import load_dotenv
from bridge.audio import AudioResampler

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
    get_service_price  # Added get_service_price
)

# Gemini Live API Configuration
GEMINI_HOST = "generativelanguage.googleapis.com"
GEMINI_URI = os.getenv("GEMINI_URL_OVERRIDE") or f"wss://{GEMINI_HOST}/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent?key={GOOGLE_API_KEY}"
GEMINI_MODEL = "models/gemini-2.5-flash-native-audio-preview-12-2025"

# --- System Instruction & Tool Schema (Restored) ---
SYSTEM_INSTRUCTION = """
YOU ARE: Harry, a professional and friendly smart assistant for Garage Wiefferink.

OBJECTIVE:
- Greet the user warmly and introduce yourself as Harry.
- Help customers with questions about APK, service, parts, or appointments.
- Be concise (max 2 sentences per response).
- Be helpful and professional.

LANGUAGE RULES:
- You normally speak ENGLISH.
- However, if the user speaks Dutch, OR if you receive a "LANGUAGE_SWITCH" signal, switch to Dutch immediately.
- Once switched, stay in that language unless the user switches back.

APPOINTMENT BOOKING FLOW:
Before scheduling an appointment, you MUST collect:
1. Customer name: "Mag ik uw naam?"
2. Phone number: "En uw telefoonnummer voor bevestiging?"
3. Kenteken (License Plate): "Om welke auto gaat het? Mag ik het kenteken?"
4. ASK PERMISSION to check vehicle status: "Zal ik gelijk even de APK status controleren?" -> If yes, call check_apk_status.
5. Then confirm the appointment details before booking.

DUTCH GREETING:
"Moin! Ik ben Harry, de slimme assistent van Garage Wiefferink. Ik kan je helpen bij bijna al je vragen! Zeg het maar, waar kan ik je vandaag mee helpen?"

ENGLISH GREETING:
"Hello! I'm Harry, the smart assistant for Garage Wiefferink. I can help you with almost any question you have. How can I assist you today?"
"""

# Full Schema restoration
TOOLS_SCHEMA = [
    {
        "function_declarations": [
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
            }
        ]
    }
]

# Logger
logger = logging.getLogger("telephony-bridge")
logging.basicConfig(level=logging.INFO)

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
    
    try:
        # Connect to Gemini Live
        async with websockets.connect(GEMINI_URI) as gemini_ws:
            logger.info("Connected to Gemini Live API")
            
            # Initial Setup for Gemini
            setup_config = {
                "setup": {
                    "model": GEMINI_MODEL,
                    "systemInstruction": {
                         "parts": [{"text": SYSTEM_INSTRUCTION}]
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
                    }
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
                nonlocal stream_sid
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
                                
                                # Execute Python function (Restored Real Logic)
                                try:
                                    if f_name == "identify_customer":
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
                                    else:
                                        result = f"Error: Unknown tool {f_name}"
                                except Exception as e:
                                    result = f"Tool Execution Error: {e}"
                                
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
                                        # CRITICAL: Use pcm_24k_to_mulaw, NOT pcm_to_mulaw (which assumes 16kHz)
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
                        
                        # Handle TurnComplete
                        if "turnComplete" in response:
                            pass

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

    try:
        async with websockets.connect(GEMINI_URI) as gemini_ws:
            logger.info("Connected to Gemini Live API (Web Mode)")
            
            # Initial Setup (Reuse same config as Twilio for consistency)
            setup_config = {
                "setup": {
                    "model": GEMINI_MODEL,
                    "systemInstruction": {"parts": [{"text": SYSTEM_INSTRUCTION}]},
                    "tools": TOOLS_SCHEMA,
                    "generation_config": {
                        "response_modalities": ["AUDIO"],
                        "speech_config": {
                            "voice_config": {"prebuilt_voice_config": {"voice_name": "Fenrir"}}
                        }
                    }
                }
            }
            await gemini_ws.send(json.dumps(setup_config))

            # --- TRIGGER INITIAL GREETING ---
            # Send an initial message to the AI to start the conversation
            initial_msg = {
                "client_content": {
                    "turns": [{
                        "role": "user",
                        "parts": [{"text": "Please introduce yourself and greet me in the current language."}]
                    }],
                    "turn_complete": True
                }
            }
            await gemini_ws.send(json.dumps(initial_msg))
            logger.info("Triggered initial AI greeting")

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
                try:
                    async for message in gemini_ws:
                        response = json.loads(message)
                        
                        # Audio Handling
                        if "serverContent" in response:
                            model_turn = response["serverContent"].get("modelTurn", {})
                            parts = model_turn.get("parts", [])
                            for part in parts:
                                if "inlineData" in part:
                                    # Gemini returns PCM. Forward to Web Client.
                                    b64_data = part["inlineData"]["data"]
                                    await websocket.send_text(json.dumps({
                                        "type": "audio",
                                        "audio": b64_data
                                    }))
                                # Handle text parts (for transcription)
                                if "text" in part:
                                    await websocket.send_text(json.dumps({
                                        "type": "transcript",
                                        "role": "assistant",
                                        "text": part["text"]
                                    }))
                        
                        # Handle input audio transcription
                        if "inputAudioTranscription" in response:
                            transcript_text = response["inputAudioTranscription"].get("text", "")
                            if transcript_text:
                                await websocket.send_text(json.dumps({
                                    "type": "transcript",
                                    "role": "user",
                                    "text": transcript_text
                                }))
                        
                        # Handle output audio transcription
                        if "outputAudioTranscription" in response:
                            transcript_text = response["outputAudioTranscription"].get("text", "")
                            if transcript_text:
                                await websocket.send_text(json.dumps({
                                    "type": "transcript",
                                    "role": "assistant",
                                    "text": transcript_text
                                }))

                        # Tool Handling (Same logic) - Now with UI notifications
                        if "toolCall" in response:
                            tool_calls = response["toolCall"]["functionCalls"]
                            tool_responses = []
                            for call in tool_calls:
                                f_name = call["name"]
                                f_args = call["args"]
                                call_id = call["id"]

                                # Notify frontend about tool call
                                await websocket.send_text(json.dumps({
                                    "type": "tool_call",
                                    "name": f_name,
                                    "args": f_args
                                }))

                                try:
                                    if f_name == "identify_customer": result = identify_customer.invoke(f_args)
                                    elif f_name == "check_werkorder_status": result = check_werkorder_status.invoke(f_args)
                                    elif f_name == "check_part_stock": result = check_part_stock.invoke(f_args)
                                    elif f_name == "schedule_appointment": result = schedule_appointment.invoke(f_args)
                                    elif f_name == "lookup_vehicle_rdw": result = lookup_vehicle_rdw.invoke(f_args)
                                    elif f_name == "check_apk_status": result = check_apk_status.invoke(f_args)
                                    elif f_name == "get_vehicle_recalls": result = get_vehicle_recalls.invoke(f_args)
                                    elif f_name == "web_search": result = web_search.invoke(f_args)
                                    elif f_name == "get_service_price": result = get_service_price.invoke(f_args)
                                    else: result = f"Error: Unknown tool {f_name}"
                                except Exception as e:
                                    result = f"Tool Execution Error: {e}"

                                # Notify frontend about tool result
                                await websocket.send_text(json.dumps({
                                    "type": "tool_result",
                                    "name": f_name,
                                    "result": str(result)[:200]  # Truncate for UI
                                }))

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

    except Exception as e:
        logger.error(f"Web Bridge error: {e}")
        await websocket.close()
