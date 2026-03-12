# CLAUDE.md - TorxFlow

## Overview

Voice-enabled AI receptionist (Harry) for Dutch automotive garages. Real-time phone + web conversations via Gemini Live API (STT + reasoning) + ElevenLabs (TTS) with background office ambience.

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12, FastAPI, LangGraph, LangChain |
| AI | Google Gemini 2.5 Flash Live API (STT + reasoning) |
| Voice | ElevenLabs WebSocket Streaming TTS (eleven_multilingual_v2) |
| Calendar | Google Calendar API (service account) |
| Email | Resend |
| Vehicle Data | RDW Open Data API |
| Telephony | Twilio Media Streams, WebSockets |
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS, Zustand |
| Deployment | Google Cloud Run, Docker |

## Structure

```
app/graph.py          # LangGraph state machine + Harry system prompt
app/tools.py          # 6 tools (RDW, appointments, cars, web search)
bridge/api.py         # FastAPI REST endpoints + CORS
bridge/telephony.py   # WebSocket handlers (Twilio + Web) + Gemini Live + ElevenLabs TTS + takeover
bridge/audio.py       # Audio codec conversion (µ-law ↔ PCM)
bridge/elevenlabs.py  # ElevenLabs WebSocket streaming TTS client
bridge/noise.py       # Background office noise generator + mixer
bridge/calendar.py    # Google Calendar integration
bridge/email.py       # Resend email notifications
bridge/state.py       # Persistent custom instructions
bridge/transcripts.py # Transcript storage (GCS or local fallback)
garage-ai-command-center/
  app/page.tsx        # Single route: Command Center
  components/command-center/  # 8 panel components
  lib/store.ts        # Zustand store (WebSocket, audio, takeover)
  lib/audio-engine.ts # Browser audio capture + playback
```

## Commands

```bash
./start_all.sh                                        # Start everything
python -m uvicorn bridge.api:app --port 8000 --reload  # Backend only
cd garage-ai-command-center && pnpm dev                # Frontend only
```

## Code Patterns

### New Tool (app/tools.py)

```python
class NewToolInput(BaseModel):
    param: str = Field(description="Description for AI")

@tool("tool_name", args_schema=NewToolInput)
def tool_name(param: str) -> str:
    """What this tool does."""
    # implementation
    return "Result"
```

Then add to the tools list in `app/graph.py` and add to `TOOLS_SCHEMA` + `_execute_tool()` in `bridge/telephony.py`.

### New API Endpoint (bridge/api.py)

```python
@app.get("/api/new_endpoint/{param}")
async def new_endpoint(param: str):
    try:
        return {"status": "success", "data": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}
```

## Changelog

### 2026-03-11
- **ElevenLabs TTS**: Replaced Gemini's built-in voice ("Orus") with ElevenLabs WebSocket streaming TTS. Gemini now runs in TEXT output mode (STT + reasoning only). Voice synthesis handled by ElevenLabs `eleven_multilingual_v2` model.
- **Background office noise**: Added synthetic office ambience (pink noise + low-pass filter) mixed into all outgoing audio at 12% volume. Makes AI calls feel like calling a real office (similar to Retell AI).
- **New audio pipeline**: Twilio audio → Gemini (STT) → text → ElevenLabs (TTS) → mix noise → Twilio. Both Twilio (16kHz PCM → µ-law) and Web (24kHz PCM) paths supported.
- **New files**: `bridge/elevenlabs.py` (TTS client), `bridge/noise.py` (noise generator/mixer).
- **Env vars**: `ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID`, `ELEVENLABS_MODEL_ID`, `OFFICE_NOISE_VOLUME`.

### 2026-03-04
- **Dashboard live monitoring**: Dashboard auto-connects in monitor mode on page load. All Twilio call data (transcripts, tool calls, vehicle data, sentiment) streams to the dashboard in real time.
- **Takeover from dashboard**: Owner can take over a live Twilio call from the dashboard (Take Over / Return to Harry).
- **Harry answers immediately**: Removed 15s ringing window — Harry picks up Twilio calls instantly with a greeting.
- **Async tool execution**: Tools run in `asyncio.to_thread()` to prevent blocking the WebSocket event loop (fixes call drops during tool use like `search_available_cars`).
- **Greeting trigger for Twilio**: Added explicit greeting trigger so Harry greets callers immediately instead of waiting for audio input.

## Constraints

1. **Latency**: ~800ms total (200ms network + 200ms Gemini text + 300ms ElevenLabs first byte + 100ms code)
2. **Audio pipeline**: Twilio 8kHz µ-law → 16kHz PCM → Gemini (TEXT mode) → ElevenLabs TTS → mix noise → µ-law/PCM
3. **Voice**: ElevenLabs (non-negotiable) · Background office noise at 12% volume
4. **Language**: Code/docs English · Customer-facing responses Dutch
5. **Appointments**: Minimum 3 weeks out · Creates proposals (not confirmed) · Owner accepts from dashboard
