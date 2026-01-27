import os
import logging
import time
import json
from typing import Dict, Any, Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from langchain_core.messages import HumanMessage
from graph import app as agent_app, get_initial_messages

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GarageAI")

# --- FastAPI App ---
app = FastAPI(title="GarageAI WinCar Integration", version="1.0.0")

# --- Vapi Models ---
# Simplified model to capture the structure Vapi sends
class VapiMessage(BaseModel):
    role: str
    content: str

class VapiCall(BaseModel):
    id: str  # We'll use this as the thread_id
    # Add other fields as needed

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
    Receives the user message, processes it via LangGraph, and returns the response.
    """
    try:
        # Debug: Log raw payload to identify schema mismatches
        payload = await request.json()
        logger.info(f"Raw Vapi Payload: {payload}")
        
        # Extract fields safely using .get() to avoid 422 errors
        message_data = payload.get("message", {})
        user_message = message_data.get("content", "")
        call_data = payload.get("call", {})
        call_id = call_data.get("id", "default_thread")

        logger.info(f"Processing message for call {call_id}: {user_message}")

        # Streaming Generator for Vapi
        async def response_stream(input_message: str):
            try:
                # 1. Acknowledge immediately (Keep Connection Alive)
                # Vapi expects "data: [DONE]" or JSON chunks.
                
                chunk_Base = {
                    "id": "chatcmpl-stream",
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": "GarageAI-Local",
                    "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}]
                }
                yield f"data: {json.dumps(chunk_Base)}\n\n"

                # Handle empty input
                if not input_message:
                    # Treat empty message as a start signal (Vapi 'assistant-request')
                    input_message = "Hello, I am calling about my car."

                # 2. Call Logic (Synchronous for safety)
                # call_id = payload.get("call", {}).get("id", "default") # Already extracted above
                config = {"configurable": {"thread_id": call_id}}
                full_text = "I encountered a system error." # Default fallback
                
                # Check state to ensure system prompt
                if not agent_app.get_state(config).values:
                     inputs = {"messages": get_initial_messages() + [HumanMessage(content=input_message)]}
                else:
                     inputs = {"messages": [HumanMessage(content=input_message)]}

                result = agent_app.invoke(inputs, config=config)
                full_content = result['messages'][-1].content
                
                # Gemini/LangChain sometimes returns a list of content blocks (e.g. text + signature)
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

                # 3. Stream the Text
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
                    # Tiny sleep to ensure chunks are sent distinctively
                    time.sleep(0.02)
                
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
        
        return StreamingResponse(response_stream(user_message), media_type="text/event-stream")

    except Exception as e:
        logger.error(f"Error processing request before streaming: {e}")
        # If an error occurs before the stream can even start (e.g., bad JSON payload)
        # we return a non-streaming error response.
        return {
            "message": {
                "role": "assistant",
                "content": "Excuses, er ging iets mis met de verbinding naar het systeem."
            }
        }

if __name__ == "__main__":
    import uvicorn
    # In production, run with: uvicorn main:app --host 0.0.0.0 --port 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)
