# Testing Workflow

A comprehensive testing workflow for verifying GarageAI functionality.

## Overview

```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│ PREREQ  │ → │   DB    │ → │  TOOLS  │ → │  E2E    │
└─────────┘    └─────────┘    └─────────┘    └─────────┘
```

---

## Phase 1: Prerequisites Check

**Goal**: Ensure the environment is ready for testing.

### Checklist

- [ ] **Docker Running**
  ```bash
  docker ps | grep sql
  ```

- [ ] **Environment Variables**
  ```bash
  echo $GOOGLE_API_KEY      # Should be set
  echo $PYTHONPATH          # Should include project root
  ```

- [ ] **Dependencies Installed**
  ```bash
  pip list | grep -E "fastapi|langchain|langraph|pyodbc"
  ```

- [ ] **Database Accessible**
  ```bash
  python -c "from app.tools import get_wincar_connection; c = get_wincar_connection(); print('DB OK'); c.close()"
  ```

### If Prerequisites Fail

| Issue | Solution |
|-------|----------|
| Docker not running | `docker-compose up -d` |
| Missing env vars | Check `.env` file or export manually |
| Missing packages | `pip install -r requirements.txt` |
| DB connection failed | Check Docker, wait for SQL Server startup |

---

## Phase 2: Database Testing

**Goal**: Verify database schema and data integrity.

### Step 2.1: Schema Verification

```python
# Run this to check all tables exist
from app.tools import get_wincar_connection

conn = get_wincar_connection()
cursor = conn.cursor()

cursor.execute("""
    SELECT TABLE_NAME
    FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_TYPE = 'BASE TABLE'
""")

tables = [row[0] for row in cursor.fetchall()]
print("Tables found:", tables)

expected = [
    'Communicatie_Relaties',
    'Werkplaats_Voertuigen',
    'Werkplaats_Werkorders',
    'Magazijn_Artikelen',
    'Financieel_Facturen'
]

for t in expected:
    status = "✅" if t in tables else "❌"
    print(f"{status} {t}")

conn.close()
```

### Step 2.2: Data Verification

```python
from app.tools import get_wincar_connection

conn = get_wincar_connection()
cursor = conn.cursor()

tables = [
    ('Communicatie_Relaties', 'Customers'),
    ('Werkplaats_Voertuigen', 'Vehicles'),
    ('Werkplaats_Werkorders', 'Work Orders'),
    ('Magazijn_Artikelen', 'Parts'),
]

for table, name in tables:
    cursor.execute(f"SELECT COUNT(*) FROM {table}")
    count = cursor.fetchone()[0]
    status = "✅" if count > 0 else "⚠️"
    print(f"{status} {name}: {count} records")

conn.close()
```

### Step 2.3: Sample Data Inspection

```python
from app.tools import get_wincar_connection

conn = get_wincar_connection()
cursor = conn.cursor()

# Check a sample customer
cursor.execute("SELECT TOP 3 KlantID, KlantNaam, Telefoon FROM Communicatie_Relaties")
print("\n📋 Sample Customers:")
for row in cursor.fetchall():
    print(f"  ID:{row[0]} | {row[1]} | {row[2]}")

# Check a sample vehicle
cursor.execute("SELECT TOP 3 VoertuigID, Kenteken, Merk FROM Werkplaats_Voertuigen")
print("\n🚗 Sample Vehicles:")
for row in cursor.fetchall():
    print(f"  ID:{row[0]} | {row[1]} | {row[2]}")

conn.close()
```

---

## Phase 3: Tool Testing

**Goal**: Verify each LangGraph tool works correctly.

### Step 3.1: Test Each Tool

```python
from app.tools import (
    identify_customer,
    check_werkorder_status,
    check_part_stock,
    schedule_appointment,
    generate_payment_link,
    web_search
)

print("=" * 50)
print("TOOL TESTING")
print("=" * 50)

# Test 1: Customer Lookup
print("\n🔍 Test: identify_customer")
result = identify_customer("0612345678")
print(f"   Input: '0612345678'")
print(f"   Output: {result}")
print(f"   Status: {'✅' if 'Klant' in result or 'Geen' in result else '❌'}")

# Test 2: Werkorder Status
print("\n🔍 Test: check_werkorder_status")
result = check_werkorder_status("AB-123-CD")
print(f"   Input: 'AB-123-CD'")
print(f"   Output: {result}")
print(f"   Status: {'✅' if 'Werkorder' in result or 'Geen' in result else '❌'}")

# Test 3: Part Stock
print("\n🔍 Test: check_part_stock")
result = check_part_stock("olie")
print(f"   Input: 'olie'")
print(f"   Output: {result}")
print(f"   Status: {'✅' if '€' in result or 'niet gevonden' in result.lower() else '❌'}")

# Test 4: Payment Link
print("\n🔍 Test: generate_payment_link")
result = generate_payment_link("123")
print(f"   Input: '123'")
print(f"   Output: {result}")
print(f"   Status: {'✅' if 'https://' in result else '❌'}")

print("\n" + "=" * 50)
```

### Step 3.2: Test Tool with LangGraph Agent

```python
from app.graph import app
from langchain_core.messages import HumanMessage

# Test the full agent with a tool-calling scenario
config = {"configurable": {"thread_id": "test-session-1"}}

response = app.invoke(
    {"messages": [HumanMessage(content="Wat is de status van kenteken AB-123-CD?")]},
    config
)

print("Agent Response:")
print(response["messages"][-1].content)
```

---

## Phase 4: LangSmith Visualization Setup

**Goal**: Enable tracing to visualize agent behavior.

### Step 4.1: Configure LangSmith

```bash
# Add to your environment or .env file
export LANGCHAIN_TRACING_V2=true
export LANGCHAIN_API_KEY=your_api_key_here
export LANGCHAIN_PROJECT=GarageAI-Testing
```

### Step 4.2: Verify Tracing

```python
import os

# Check if LangSmith is configured
tracing = os.getenv("LANGCHAIN_TRACING_V2")
api_key = os.getenv("LANGCHAIN_API_KEY")
project = os.getenv("LANGCHAIN_PROJECT", "default")

print("LangSmith Configuration:")
print(f"  Tracing Enabled: {'✅' if tracing == 'true' else '❌'}")
print(f"  API Key Set: {'✅' if api_key else '❌'}")
print(f"  Project: {project}")

if tracing == 'true' and api_key:
    print("\n✅ LangSmith is configured! Traces will appear at:")
    print(f"   https://smith.langchain.com/projects/{project}")
```

### Step 4.3: Run Traced Test

```python
# Run agent with tracing enabled
from app.graph import app
from langchain_core.messages import HumanMessage

test_messages = [
    "Hallo, ik ben Jan",
    "Wat is de status van mijn auto? Kenteken AB-123-CD",
    "Hebben jullie remblokken op voorraad?",
]

config = {"configurable": {"thread_id": "langsmith-test"}}

for msg in test_messages:
    print(f"\n👤 User: {msg}")
    response = app.invoke(
        {"messages": [HumanMessage(content=msg)]},
        config
    )
    print(f"🤖 Agent: {response['messages'][-1].content}")

print("\n📊 Check LangSmith dashboard for trace visualization!")
```

---

## Phase 5: API & E2E Testing

**Goal**: Test the complete system end-to-end.

### Step 5.1: Start the Server

```bash
python -m uvicorn bridge.api:app --port 8000 --reload
```

### Step 5.2: Test API Endpoints

```bash
# Health check
curl http://localhost:8000/

# Database endpoints
curl http://localhost:8000/api/db/customers
curl http://localhost:8000/api/db/werkorders
curl http://localhost:8000/api/db/stock
```

### Step 5.3: Test Web Dashboard

1. Open: http://localhost:8000/web/index.html
2. Click "Connect"
3. Verify WebSocket status shows "Online"
4. Send a test message
5. Verify AI response

### Step 5.4: Test Voice (if microphone available)

1. Click microphone button
2. Speak: "Hallo, wat kunnen jullie voor mij doen?"
3. Verify audio response plays back

---

## Test Report

Generate a report after testing:

```markdown
# GarageAI Test Report

**Date**: [TODAY]
**Tester**: Tessa (Testing Agent)

## Environment
- Python: [version]
- Docker: [running/not running]
- Database: [connected/not connected]
- LangSmith: [configured/not configured]

## Results Summary

| Category | Pass | Fail | Skip |
|----------|------|------|------|
| Prerequisites | X | X | X |
| Database | X | X | X |
| Tools | X | X | X |
| API | X | X | X |
| E2E | X | X | X |

## Detailed Results

[Fill in based on test execution]

## Issues Found

[List any issues discovered]

## Next Steps

[Recommendations for fixes or improvements]
```
