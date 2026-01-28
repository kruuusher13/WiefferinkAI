# Product Requirements Document (PRD): Project "GarageAI: Gemini Live Migration"

| Metadata | Details |
| :--- | :--- |
| **Project Name** | GarageAI - Vapi to Gemini Live Migration |
| **Document Status** | Draft |
| **Owner** | Product Management (BMAD) |
| **Last Updated** | 2026-01-28 |

---

## 1. Executive Summary
The goal of this project is to migrate the existing GarageAI voice assistant from a **Vapi.ai (Webhook + SSE)** architecture to a **Native Gemini Live (WebSocket)** architecture. This shift leverages Google's Multimodal Live API to achieve ultra-low latency (<800ms) and more natural, interruptible conversations. The system must retain full integration with the **WinCar DMS**, support specific Dutch garage jargon, and adhere to strict safety protocols.

## 2. Problem Statement
The current Vapi implementation relies on a chain of distinct services (Vapi STT -> logic -> LLM -> Vapi TTS). Even with streaming, this introduces latency "hops" that can exceed 1-2 seconds, creating a disjointed user experience. Additionally, handling complex Dutch automotive jargon ("grote beurt", "APK") via a generic STT provider often leads to transcription errors before the LLM even sees the text.

## 3. Goals & Success Metrics

### 3.1 Primary Goals
1.  **Migrate Architecture**: Replace `POST /chat` webhook logic with a bidirectional `WebSocket` server connecting Telephony (e.g., Twilio Media Streams) directly to Gemini Live API.
2.  **Latency Reduction**: Achieve Audio-to-Audio latency of **<800ms**.
3.  **Domain Precision**: Accurately recognize and handle Dutch garage terminology.

### 3.2 Success Metrics
| Metric | Target | Measurement Method |
| :--- | :--- | :--- |
| **Latency (Audio-to-Audio)** | < 800ms | Time from end of user speech to start of assistant audio buffer. |
| **Jargon Recognition Rate** | > 95% | Test set of 50 common garage phrases (e.g., "APK keuren", "remblokken vervangen"). |
| **Tool Execution Success** | 100% | Valid SQL generation for `check_werkorder_status` and `identify_customer`. |
| **Safety Compliance** | 100% | Immediate termination/handover on "emergency" keywords (smoke, brake failure). |

---

## 4. Functional Requirements

### 4.1 Native Gemini Live Integration
*   **Protocol**: the application must host a WebSocket server (FastAPI) to bridge the Telephony Audio Stream (User Audio) and the Gemini Multimodal Live API.
*   **Session Config**:
    *   Model: `gemini-2.0-flash-exp` (or latest stable Live version).
    *   Voice: Configurable Dutch voice tone.
    *   System Instruction: Must be injected at session start (see 4.2).

### 4.2 Dutch Automotive Domain & Jargon
The system must be contextually primed to understand and use the following terms correctly:

| Term | Context/Meaning | Action/Data Mapping |
| :--- | :--- | :--- |
| **APK** | Algemene Periodieke Keuring (MOT) | Service Type: `Keuring` |
| **Grote Beurt** | Major Maintenance Service | Service Type: `Onderhoud_Groot` |
| **Kleine Beurt** | Minor Maintenance Service | Service Type: `Onderhoud_Klein` |
| **Remschijven/blokken** | Brake discs/pads | Part Category: `Remmen` |
| **Distributieriem** | Timing belt | Critical Maintenance Item |
| **Winterbandenwissel** | Winter tire change | Seasonal Service |
| **Kenteken** | License Plate | Format: `XX-XX-XX` (handling variations) |

**Requirement**: The System Instruction must explicitly map these terms to their expected context to prevent STT hallucinations (e.g., hearing "APK" as "A P K" or "Okay").

### 4.3 Tooling Integration (Function Calling)
The Gemini Live session must define the following tools (migrated from `tools.py`):
1.  `identify_customer(phone_number)`
2.  `check_werkorder_status(license_plate)`
3.  `check_part_stock(part_name)`
4.  `schedule_appointment(date, description)`
5.  `generate_payment_link(werkorder_id)` - *Requires Human-in-the-loop logic or confirmation flow.*

### 4.4 Safety & Emergency Protocols
*   **Interruptiblity**: The user must be able to interrupt the AI instantly (native feature of Gemini Live).
*   **Emergency Overrides**: If the user mentions fire, smoke, or total brake failure, the AI must:
    1.  Stop all tool calls.
    2.  State: *"Dit klinkt gevaarlijk. Stop onmiddellijk op een veilige plek en bel 112 of de wegenwacht."*
    3.  Terminate the session or forward to a human line.

---

## 5. Technical Architecture Plan

### 5.1 Current vs. New Architecture
*   **Old**: `Phone -> Vapi (STT) -> Webhook (FastAPI) -> LangGraph (Logic) -> Gemini (Text) -> Vapi (TTS) -> Phone`
*   **New**: `Phone -> Telephony Bridge (e.g., Twilio Stream) -> FastAPI WebSocket -> Gemini Live API (Audio+Logic) -> FastAPI WebSocket -> Phone`

### 5.2 Migration Steps
1.  **Infrastructure**: Set up a FastAPI WebSocket endpoint (e.g., `/ws/audio`).
2.  **Tool Definition**: Convert `langchain` tools to Gemini Live `FunctionDeclaration` schema.
3.  **Prompt Porting**: Rewrite `SYSTEM_PROMPT` from `graph.py` to be optimized for the Gemini Live `system_instruction` parameter, including the Jargon Glossary.
4.  **Testing**: Use a localized script to simulate audio streams and verify "APK" recognition and latency.

---

## 6. Risks & Mitigation
*   **Risk**: Loss of detailed conversation history (Memory) between calls.
    *   *Mitigation*: Persist summary to `Communicatie_Relaties` table after session close.
*   **Risk**: High Audio Latency on mobile networks.
    *   *Mitigation*: Use aggressive audio compression (G.711 PCMU or Opus) supported by the Telephony provider.
*   **Risk**: Halluncination of SQL queries.
    *   *Mitigation*: Keep the "Read Only" constraint on DB tools enforced at the connection level (`get_wincar_connection`).

---
