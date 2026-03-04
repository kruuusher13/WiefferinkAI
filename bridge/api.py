import os
import json
import logging
import httpx
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response, FileResponse, HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TorxFlow")

from bridge.telephony import router as telephony_router
from bridge.state import get_custom_instructions, set_custom_instructions
from bridge.calendar_auth import CalendarNotConnectedError

app = FastAPI(title="TorxFlow Integration", version="2.0.0")

_cors_origins = ["http://localhost:3000", "http://localhost:8000"]
_extra_origin = os.getenv("CORS_ORIGIN")
if _extra_origin:
    _cors_origins.append(_extra_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(telephony_router)


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


# --- Google Calendar OAuth ---

def _calendar_redirect_uri(request: Request) -> str:
    """Build the OAuth callback URL from request headers (works localhost + production)."""
    host = request.headers.get("x-forwarded-host") or request.headers.get("host", "localhost:8000")
    scheme = request.headers.get("x-forwarded-proto", "http")
    return f"{scheme}://{host}/api/calendar/callback"


@app.get("/api/calendar/status")
async def calendar_status():
    """Check if Google Calendar is connected."""
    from bridge.calendar_auth import is_connected
    return {"connected": is_connected()}


@app.get("/api/calendar/auth")
async def calendar_auth(request: Request):
    """Redirect to Google consent screen."""
    from bridge.calendar_auth import get_auth_url
    auth_url = get_auth_url(redirect_uri=_calendar_redirect_uri(request))
    return RedirectResponse(auth_url)


def _frontend_url(request: Request) -> str:
    """Determine the frontend URL for redirects."""
    url = os.getenv("CORS_ORIGIN", "")
    if url:
        return url
    # In local dev, frontend is on :3000
    return "http://localhost:3000"


@app.get("/api/calendar/callback")
async def calendar_callback(request: Request, code: str):
    """Exchange auth code for tokens, redirect to frontend."""
    from bridge.calendar_auth import exchange_code
    base = _frontend_url(request)
    try:
        exchange_code(code, redirect_uri=_calendar_redirect_uri(request))
    except Exception as e:
        logger.error(f"Calendar OAuth callback error: {e}")
        return RedirectResponse(f"{base}/?calendar=error")

    return RedirectResponse(f"{base}/?calendar=connected")


@app.post("/api/calendar/disconnect")
async def calendar_disconnect():
    """Delete stored OAuth tokens."""
    from bridge.calendar_auth import delete_tokens
    delete_tokens()
    return {"status": "success"}


# --- Google Calendar Endpoints ---

@app.get("/api/calendar/events")
async def get_calendar_events(days: int = 30):
    """List upcoming Google Calendar events."""
    try:
        from bridge.calendar import list_events
        events = list_events(days_ahead=days)
        return {"status": "success", "events": events}
    except CalendarNotConnectedError:
        return JSONResponse(status_code=401, content={"status": "not_connected", "message": "Google Calendar is not connected"})
    except Exception as e:
        logger.error(f"Calendar events error: {e}")
        return {"status": "error", "message": str(e)}


# --- Appointment Acceptance ---

class AppointmentAccept(BaseModel):
    description: str
    date_time: str
    customer_name: str
    customer_phone: Optional[str] = None
    customer_email: str
    kenteken: Optional[str] = ""
    duration_minutes: Optional[int] = 60

@app.post("/api/appointment/accept")
async def accept_appointment(payload: AppointmentAccept):
    """Accept an appointment proposal: create Google Calendar event + send confirmation email."""
    try:
        from bridge.calendar import create_event
        from bridge.email import send_customer_confirmation

        event = create_event(
            summary=f"{payload.description} - {payload.customer_name}",
            start_datetime=payload.date_time,
            duration_minutes=payload.duration_minutes or 60,
            customer_name=payload.customer_name,
            customer_phone=payload.customer_phone or "",
            customer_email=payload.customer_email,
            kenteken=payload.kenteken or "",
            description=payload.description,
        )

        send_customer_confirmation(
            to_email=payload.customer_email,
            customer_name=payload.customer_name,
            date_time=payload.date_time,
            description=payload.description,
        )

        return {
            "status": "success",
            "calendar_event_id": event.get("id", ""),
            "calendar_link": event.get("htmlLink", ""),
        }
    except CalendarNotConnectedError:
        return JSONResponse(status_code=401, content={"status": "not_connected", "message": "Google Calendar is not connected"})
    except Exception as e:
        logger.error(f"Appointment acceptance error: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


# --- Custom Instructions ---

class CustomInstructionsPayload(BaseModel):
    instructions: str

@app.get("/api/custom-instructions")
async def get_instructions():
    return {"instructions": get_custom_instructions()}

@app.post("/api/custom-instructions")
async def save_instructions(payload: CustomInstructionsPayload):
    set_custom_instructions(payload.instructions)
    return {"status": "success"}

# --- Transcript History ---

from bridge.transcripts import list_transcripts as _list_transcripts, get_transcript as _get_transcript

@app.get("/api/transcripts")
async def list_transcripts():
    """List all saved transcripts, sorted by date descending."""
    return _list_transcripts()

@app.get("/api/transcripts/{transcript_id}")
async def get_transcript(transcript_id: str):
    """Return a full transcript by ID (filename stem)."""
    data = _get_transcript(transcript_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Transcript not found")
    return data


# --- Twilio Incoming Call Webhook ---

@app.post("/twilio/voice")
@app.get("/twilio/voice")
async def twilio_voice_webhook(request: Request):
    """TwiML webhook for incoming Twilio calls."""
    host = request.headers.get("x-forwarded-host") or request.headers.get("host", "localhost:8000")
    scheme = "wss" if request.headers.get("x-forwarded-proto") == "https" else "ws"
    ws_url = f"{scheme}://{host}/ws/twilio"

    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Connect>
        <Stream url="{ws_url}" />
    </Connect>
</Response>"""

    return Response(content=twiml, media_type="application/xml")


@app.get("/api/health")
async def health_check():
    return {"status": "online", "system": "TorxFlow"}


# --- Static Frontend Serving ---

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "static_frontend"

if FRONTEND_DIR.exists():
    app.mount("/_next", StaticFiles(directory=FRONTEND_DIR / "_next"), name="next-static")

    @app.get("/audio-worklet-processor.js")
    async def audio_worklet():
        return FileResponse(FRONTEND_DIR / "audio-worklet-processor.js")

    @app.get("/basic")
    async def serve_basic():
        return FileResponse(FRONTEND_DIR / "basic.html", media_type="text/html")

    @app.get("/dashboard")
    async def serve_dashboard():
        return FileResponse(FRONTEND_DIR / "dashboard.html", media_type="text/html")

    @app.get("/history")
    async def serve_history():
        return FileResponse(FRONTEND_DIR / "history.html", media_type="text/html")

    @app.get("/calendar")
    async def serve_calendar():
        return FileResponse(FRONTEND_DIR / "calendar.html", media_type="text/html")

    @app.get("/")
    async def serve_index():
        return FileResponse(FRONTEND_DIR / "index.html", media_type="text/html")
else:
    @app.get("/")
    async def health_fallback():
        return {"status": "online", "system": "TorxFlow", "frontend": "not built"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("bridge.api:app", host="0.0.0.0", port=8000, reload=True)
