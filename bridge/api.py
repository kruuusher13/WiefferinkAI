import os
import logging
import time
import json
import httpx
from typing import Dict, Any, Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_core.messages import HumanMessage
from app.graph import app as agent_app, get_initial_messages
from app.init_db import wait_for_db, execute_script
import pyodbc

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GarageAI")

from bridge.telephony import router as telephony_router

# --- FastAPI App ---
app = FastAPI(title="GarageAI WinCar Integration", version="2.0.0")

# CORS — allow Next.js dev server and production origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Telephony/Websocket Routes
app.include_router(telephony_router)

# --- Database Integration & Visualization ---
DB_CONFIG = {
    'server': 'localhost',
    'database': 'WinCarLive',
    'username': 'sa',
    'password': 'StrongPassword123!',
    'driver': '{ODBC Driver 17 for SQL Server}'
}
DB_CONN_STR = f"DRIVER={DB_CONFIG['driver']};SERVER={DB_CONFIG['server']};DATABASE={DB_CONFIG['database']};UID={DB_CONFIG['username']};PWD={DB_CONFIG['password']}"

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    logger.info("Initializing database...")
    try:
        wait_for_db()
        # Check if WinCarLive DB already exists before re-creating
        import pyodbc
        from app.init_db import CONN_STR
        conn = pyodbc.connect(CONN_STR, timeout=3)
        cursor = conn.cursor()
        cursor.execute("SELECT DB_ID('WinCarLive')")
        exists = cursor.fetchone()[0] is not None
        conn.close()
        if exists:
            logger.info("Database WinCarLive already exists, skipping init.")
        else:
            execute_script("mock_wincar_db.sql")
            logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")

@app.get("/api/db/{table_name}")
async def get_db_table(table_name: str):
    """Fetch all rows from a specified table for visualization."""
    valid_tables = [
        "customers", "vehicles", "werkorders", "lines", 
        "stock", "categories", "services", "rates", "invoices"
    ]
    if table_name not in valid_tables:
        raise HTTPException(status_code=400, detail="Invalid table name")
    
    try:
        conn = pyodbc.connect(DB_CONN_STR)
        cursor = conn.cursor()
        
        # Determine actual table name in DB
        db_table = ""
        if table_name == "customers": db_table = "Communicatie_Relaties"
        elif table_name == "vehicles": db_table = "Werkplaats_Voertuigen"
        elif table_name == "werkorders": db_table = "Werkplaats_Werkorders"
        elif table_name == "lines": db_table = "Werkplaats_WerkorderRegels"
        elif table_name == "stock": db_table = "Magazijn_Artikelen"
        elif table_name == "categories": db_table = "Magazijn_Categorieen"
        elif table_name == "services": db_table = "Diensten_Services"
        elif table_name == "rates": db_table = "Diensten_Tarieven"
        elif table_name == "invoices": db_table = "Financieel_Facturen"
        
        cursor.execute(f"SELECT * FROM {db_table}")
        columns = [column[0] for column in cursor.description]
        results = []
        for row in cursor.fetchall():
            results.append(dict(zip(columns, row)))
            
        conn.close()
        return results
    except Exception as e:
        logger.error(f"Database error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

# --- RDW Direct Lookup (structured JSON for frontend) ---

RDW_VEHICLE_URL = "https://opendata.rdw.nl/resource/m9d7-ebf2.json"

def _normalize_kenteken(kenteken: str) -> str:
    import re
    return re.sub(r'[^A-Z0-9]', '', kenteken.upper())

def _format_rdw_date(date_str: str) -> str | None:
    if not date_str or len(date_str) < 8:
        return None
    try:
        from datetime import datetime
        dt = datetime.strptime(date_str[:8], "%Y%m%d")
        return dt.strftime("%d-%m-%Y")
    except ValueError:
        return date_str

@app.get("/api/rdw-lookup/{kenteken}")
async def rdw_lookup(kenteken: str):
    """Structured RDW vehicle lookup — returns JSON data."""
    clean = _normalize_kenteken(kenteken)
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(RDW_VEHICLE_URL, params={"kenteken": clean})
            resp.raise_for_status()
            data = resp.json()

        if not data:
            return {"status": "not_found", "data": None}

        v = data[0]
        merk = v.get("merk", "Onbekend")
        handelsbenaming = v.get("handelsbenaming", "Onbekend")
        brandstof = v.get("brandstof_omschrijving", "Onbekend")
        eerste_toelating = _format_rdw_date(v.get("datum_eerste_toelating", ""))
        vervaldatum_apk = _format_rdw_date(v.get("vervaldatum_apk", ""))
        kleur = v.get("eerste_kleur", "Onbekend")

        # Calculate APK days remaining
        apk_days = None
        raw_apk = v.get("vervaldatum_apk", "")
        if raw_apk and len(raw_apk) >= 8:
            try:
                from datetime import datetime
                apk_dt = datetime.strptime(raw_apk[:8], "%Y%m%d")
                apk_days = (apk_dt - datetime.now()).days
            except ValueError:
                pass

        vehicle_data = {
            "kenteken": clean,
            "merk": merk,
            "handelsbenaming": handelsbenaming,
            "brandstof": brandstof,
            "eerste_toelating": eerste_toelating or "Onbekend",
            "vervaldatum_apk": vervaldatum_apk or "Niet beschikbaar",
            "kleur": kleur,
        }
        if apk_days is not None:
            vehicle_data["apk_days_remaining"] = str(apk_days)

        return {"status": "success", "data": vehicle_data}
    except Exception as e:
        logger.error(f"RDW lookup error: {e}")
        return {"status": "error", "data": None, "message": str(e)}


# --- Werkorder Creation (from Dashboard Accept) ---

class WerkorderCreate(BaseModel):
    description: str
    customer_name: Optional[str] = None
    phone_number: Optional[str] = None
    kenteken: Optional[str] = None
    date_time: Optional[str] = None

@app.post("/api/werkorder")
async def create_werkorder(payload: WerkorderCreate):
    """Create a werkorder from a dashboard-accepted proposal."""
    import re
    conn = pyodbc.connect(DB_CONN_STR)
    cursor = conn.cursor()
    try:
        klant_id = None
        voertuig_id = None

        # Find or create customer
        if payload.phone_number:
            clean_phone = re.sub(r'[^0-9+]', '', payload.phone_number)
            if clean_phone.startswith("+31"):
                clean_phone = "0" + clean_phone[3:]
            cursor.execute(
                "SELECT KlantID FROM Communicatie_Relaties WHERE Telefoon LIKE ?",
                f"%{clean_phone}%"
            )
            row = cursor.fetchone()
            if row:
                klant_id = row[0]
            elif payload.customer_name:
                cursor.execute(
                    "INSERT INTO Communicatie_Relaties (KlantNaam, Telefoon) OUTPUT INSERTED.KlantID VALUES (?, ?)",
                    payload.customer_name, clean_phone
                )
                klant_id = cursor.fetchone()[0]
                conn.commit()
        elif payload.customer_name:
            cursor.execute(
                "SELECT KlantID FROM Communicatie_Relaties WHERE KlantNaam = ?",
                payload.customer_name
            )
            row = cursor.fetchone()
            if row:
                klant_id = row[0]

        # Find or create vehicle
        if payload.kenteken:
            clean_kt = re.sub(r'[^A-Z0-9]', '', payload.kenteken.upper())
            cursor.execute(
                "SELECT VoertuigID FROM Werkplaats_Voertuigen WHERE Kenteken = ?",
                clean_kt
            )
            vrow = cursor.fetchone()
            if vrow:
                voertuig_id = vrow[0]
            elif klant_id:
                cursor.execute(
                    "INSERT INTO Werkplaats_Voertuigen (Kenteken, KlantID) OUTPUT INSERTED.VoertuigID VALUES (?, ?)",
                    clean_kt, klant_id
                )
                voertuig_id = cursor.fetchone()[0]
                conn.commit()

        # Build description
        omschrijving = payload.description
        if payload.date_time:
            omschrijving += f" (Afspraak: {payload.date_time})"
        if payload.customer_name:
            omschrijving += f" (Klant: {payload.customer_name})"

        # Create werkorder
        cursor.execute(
            "INSERT INTO Werkplaats_Werkorders (VoertuigID, KlantID, Status, Omschrijving) OUTPUT INSERTED.WerkorderID VALUES (?, ?, 'Gepland', ?)",
            voertuig_id, klant_id, omschrijving
        )
        werkorder_id = cursor.fetchone()[0]
        conn.commit()

        return {"status": "success", "werkorder_id": werkorder_id}
    except Exception as e:
        logger.error(f"Werkorder creation error: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})
    finally:
        conn.close()


# --- Vapi Models ---
class VapiMessage(BaseModel):
    role: str
    content: str

class VapiCall(BaseModel):
    id: str
    
class VapiPayload(BaseModel):
    message: VapiMessage
    call: Optional[VapiCall] = None

# --- Endpoints ---

@app.get("/")
async def health_check():
    return {"status": "online", "system": "GarageAI WinCar Integration"}

@app.post("/chat")
@app.post("/chat/chat/completions")
async def vapi_chat(request: Request):
    """
    Primary endpoint for Vapi.ai interactions.
    Handles Vapi Custom LLM calls (streaming).
    """
    try:
        # Debug: Log raw payload
        payload = await request.json()
        logger.info(f"Raw Vapi Payload: {payload}")
        
        # --- Parsing Logic (Step 1079 Fix) ---
        message_data = payload.get("message", {})
        msg_type = message_data.get("type")
        call_data = payload.get("call", {})
        call_id = call_data.get("id", "default_thread")
        
        user_message = ""
        should_respond = False

        if msg_type == "assistant-request":
            # This is the start of the call - trigger greeting
            should_respond = True
            logger.info(f"Received assistant-request for call {call_id}")
            
        elif msg_type == "conversation-update" or msg_type == "add-message":
            # Check if the last message was from the user
            conversation = message_data.get("conversation", [])
            messages = message_data.get("messages", []) # Fallback
            
            # Try 'conversation' list first (standard Vapi)
            if conversation:
                last_msg = conversation[-1]
                if last_msg.get("role") == "user":
                    user_message = last_msg.get("content", "")
                    should_respond = True
            # Fallback to 'messages' list if 'conversation' is missing/empty
            elif messages: 
                 last_msg = messages[-1]
                 if last_msg.get("role") == "user":
                     user_message = last_msg.get("message", "") # Vapi sometimes uses 'message' key here
                     should_respond = True

            if should_respond:
                 logger.info(f"Processing user message for call {call_id}: {user_message}")
            else:
                 logger.info(f"Ignored conversation-update (no user turn) for call {call_id}")

        else:
            # Ignore other events (status-update, speech-update, etc.)
            logger.info(f"Ignored event type: {msg_type} for call {call_id}")
            return JSONResponse(content={"status": "ignored"})

        if not should_respond:
             return JSONResponse(content={"status": "ignored"})
             
        # --- Streaming Logic (Restored) ---
        async def response_stream(input_message: str):
            try:
                # 1. Acknowledge immediately (OpenAI Stream Start)
                chunk_Base = {
                    "id": "chatcmpl-stream",
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": "GarageAI-Local",
                    "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}]
                }
                yield f"data: {json.dumps(chunk_Base)}\n\n"

                # Handle empty input (Greeting)
                if not input_message and msg_type == "assistant-request":
                    input_message = "Hello, I am calling about my car."

                # 2. Call Agent Logic
                config = {"configurable": {"thread_id": call_id}}
                full_text = "I encountered a system error."
                
                # Check state to ensure system prompt
                if not agent_app.get_state(config).values:
                     inputs = {"messages": get_initial_messages() + [HumanMessage(content=input_message)]}
                else:
                     inputs = {"messages": [HumanMessage(content=input_message)]}

                result = agent_app.invoke(inputs, config=config)
                # Parse result
                full_content = result['messages'][-1].content
                full_text = ""
                if isinstance(full_content, list):
                    for part in full_content:
                        if isinstance(part, dict) and 'text' in part:
                            full_text += part['text']
                        elif isinstance(part, str):
                             full_text += part
                else:
                    full_text = str(full_content)
                
                logger.info(f"Agent Response: {full_text}")

                # 3. Stream the Text word by word
                words = full_text.split(" ")
                for word in words:
                    chunk = {
                        "id": "chatcmpl-stream",
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": "GarageAI-Local",
                        "choices": [{"index": 0, "delta": {"content": word + " "}, "finish_reason": None}]
                    }
                    yield f"data: {json.dumps(chunk)}\n\n"
                    time.sleep(0.02) # Tiny delay for natural flow
                
                # 4. Finish
                final_chunk = {
                     "id": "chatcmpl-stream",
                     "object": "chat.completion.chunk",
                     "created": int(time.time()),
                     "model": "GarageAI-Local",
                     "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]
                }
                yield f"data: {json.dumps(final_chunk)}\n\n"
                yield "data: [DONE]\n\n"

            except Exception as e:
                logger.error(f"Logic Error inside Stream: {e}")
                err_chunk = {
                    "id": "err", 
                    "choices": [{"index":0, "delta": {"content": "I encountered a system error."}, "finish_reason": "stop"}]
                }
                yield f"data: {json.dumps(err_chunk)}\n\n"
                yield "data: [DONE]\n\n"
        
        # Return Streaming Response
        return StreamingResponse(response_stream(user_message), media_type="text/event-stream")

    except Exception as e:
        logger.error(f"Error processing request: {e}")
        # Return JSON error if streaming hasn't started
        return JSONResponse(content={
                 "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": "Excuses, er ging iets mis met de verbinding naar het systeem."
                        },
                        "finish_reason": "stop"
                    }
                ]
            })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("bridge.api:app", host="0.0.0.0", port=8000, reload=True)
