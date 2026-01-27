# API Reference

## Overview
The GarageAI integration exposes a localized HTTP API using **FastAPI**. It is designed to act as a webhook receiver for voice agents (specifically **Vapi.ai**).

## Base URL
`http://localhost:8000` (Local Development)

---

## Endpoints

### 1. Health Check
**GET** `/`

Returns the operational status of the service. Useful for uptime monitoring or connectivity checks.

**Response:**
```json
{
  "status": "online",
  "system": "GarageAI WinCar Integration"
}
```

### 2. Chat Webhook (Vapi.ai)
**POST** `/chat`

The primary endpoint for processing voice user input. It accepts a simplified Vapi.ai payload, processes the text through the LangGraph agent, and returns the text to be spoken back.

**Request Body (`application/json`):**
```json
{
  "message": {
    "role": "user",
    "content": "Is mijn auto al klaar?"
  },
  "call": {
    "id": "unique-call-id-12345"
  }
}
```

- `message.content`: The transcribed text from the user.
- `call.id`: Used as the `thread_id` for conversation persistence (memory).

### Response (Streaming)

The endpoint returns a **Server-Sent Events (SSE)** stream compatible with the OpenAI Chat Completion Chunk format. This is required for Vapi's "Custom LLM" mode to minimize latency.

**Event Stream Structure:**
```text
data: {"id": "...", "choices": [{"delta": {"content": "Hello"}}]}

data: {"id": "...", "choices": [{"delta": {"content": " "}}]}

data: {"id": "...", "choices": [{"delta": {"content": "World"}}]}

data: [DONE]
```

**Content-Type**: `text/event-stream`

## Error Handling
If an internal error occurs (e.g., Database connection failure, LLM timeout), the API returns a 'safe' fallback response in Dutch to maintain the conversation flow.

```json
{
    "message": {
        "role": "assistant",
        "content": "Excuses, er ging iets mis met de verbinding naar het systeem."
    }
}
```
