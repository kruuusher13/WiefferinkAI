# GarageAI Architecture Documentation

## 1. System Overview
GarageAI Integration is a voice-enabled assistant designed for Dutch automotive garages using the **WinCar DMS**. Ideally, it intercepts voice calls (via Vapi.ai), queries the WinCar database for real-time information, and performs actions like generating payment links.

**Core Goal**: Automate customer service interactions (status checks, price checks, payment requests) using natural language, strictly in Dutch.

## 2. Component Architecture

### 2.1 API Layer (`main.py`)
- **Technology**: FastAPI
- **Responsibility**: Exposes a `/chat` endpoint for webhook integration (Vapi.ai).
- **Flow**:
    1. Receives JSON payload with user message and call ID.
    2. Initializes/Retrieves LangGraph state.
    3. Invokes the Agent Graph.
    4. Returns a JSON response with the Assistant's spoken text.

### 2.2 Agent Logic (`graph.py`)
- **Technology**: LangGraph + LangChain + Gemini Flash 1.5
- **Structure**:
    - **Agent Node**: Decides whether to reply or call a tool based on the System Prompt.
    - **Tools Node**: Executes specific WinCar functions.
    - **Persistence**: Uses `MemorySaver` to maintain conversation context across turns.
- **System Prompt**: Enforces strict "Dutch Only" and "Max 2 Sentences" rules, mimicking a professional garage assistant.

### 2.3 Integration Layer (`tools.py`)
- **Technology**: `pyodbc` (SQL Server)
- **Responsibility**: Maps abstract intent (e.g., "Is my car ready?") to specific SQL queries.
- **Security**:
    - Read-Only connection for most tools.
    - Sensitive actions (Financial) require explicit "interrupt" approval (modeled in logic).

### 2.4 Data Layer (`mock_wincar_db.sql`)
- **Technology**: MS SQL Server (Mock Schema)
- **Schema**:
    - `Communicatie_Relaties`: Customers (CRM)
    - `Werkplaats_Voertuigen` & `Werkplaats_Werkorders`: Vehicles and repair status.
    - `Magazijn_Artikelen`: Parts stock and pricing.
    - `Financieel_Facturen`: Invoicing and payment links.

---

## 3. WinCar Module Mapping
Based on the **WinCar Informatiepakket 2026** (Official PDF), the system maps specific modules to AI tools as follows:

| GarageAI Tool | WinCar Module (PDF) | Description & Justification |
| :--- | :--- | :--- |
| **`identify_customer`** | **COMMUNICATIE (CRM)** | **PDF (Pg 10)**: Describes "Klantbeheer" bundling all data. "Telefonie-integratie" shows who calls. <br> **Mapping**: Tool queries `Communicatie_Relaties` by phone number to identify the caller immediately. |
| **`check_werkorder_status`** | **WERKPLAATS** | **PDF (Pg 5, 7)**: "Werkplaatsmodule... realtime statusupdates". Mentions "Digitale Werkorder" for tracking progress.<br> **Mapping**: Tool queries `Werkplaats_Werkorders` to report if a car is 'Planned', 'Waiting', or 'Ready'. |
| **`check_part_stock`** | **MAGAZIJN** | **PDF (Pg 8)**: "Realtime inzicht in de voorraad...".<br> **Mapping**: Tool checks availability and price in `Magazijn_Artikelen` before quoting a customer. |
| **`generate_payment_link`** | **FINANCIEEL** | **PDF (Pg 9)**: Mentions "WinCar Betaallink" via **Bluem / iDeal**. <br> **Mapping**: Tool mimics this by generating a payment URL for a Work Order. **Critical**: This is a write/sensitive action matching the PDF's description of financial transactions. |

## 4. Future Roadmap
- **Human-in-the-Loop**: Implement the `interrupt_before` logic in `graph.py` for the Financial tool to fully satisfy the safety requirement.
- **Real DB Connection**: Replace mock `pyodbc` string with actual WinCar SQL credentials.
- **Vapi Integration**: Test full streaming audio loop with Vapi.ai.
