# GarageAI - Voice AI for Dutch Garages

**Slimme klantservice die nooit slaapt**

---

## What is GarageAI?

GarageAI is a voice-enabled AI assistant that answers phone calls for Dutch automotive garages. Powered by Google Gemini, it handles customer inquiries 24/7 with sub-second response times.

**Meet Harry** - Your AI receptionist who speaks fluent Dutch and knows your garage inside out.

---

## Key Features

### 1. Instant Vehicle Recognition
**When a customer provides their kenteken (license plate), Harry instantly knows:**
- Vehicle make and model (e.g., "Volkswagen Golf 2019")
- APK expiry date and status
- Any open manufacturer recalls

**Demo:** Say "Mijn kenteken is 1-KBB-49" and watch Harry identify the vehicle.

---

### 2. Smart APK Reminders
Harry proactively alerts customers about upcoming APK requirements:

| Status | Harry's Response |
|--------|------------------|
| Expired | "⚠️ Uw APK is verlopen! U mag niet meer rijden. Zal ik direct een afspraak maken?" |
| < 14 days | "🔴 Uw APK verloopt over X dagen. Ik raad aan direct een afspraak te maken." |
| < 30 days | "🟠 Uw APK verloopt binnenkort. Dit is een goed moment om in te plannen." |
| < 60 days | "🟡 Ter info: uw APK verloopt op [datum]. Wilt u alvast inplannen?" |

**Demo:** Use kenteken with APK expiring soon to see proactive reminders.

---

### 3. Work Order Status Check
Customers can check their repair status by providing their license plate.

**Demo:** Say "Wat is de status van mijn auto met kenteken AB-123-CD?"

---

### 4. Parts Availability & Pricing
Harry can check if specific parts are in stock and provide pricing.

**Demo:** Ask "Hebben jullie remblokken op voorraad?" or "Wat kost een oliefilter?"

---

### 5. Appointment Scheduling
Harry can book workshop appointments directly into the system.

**Demo:** Say "Ik wil een afspraak maken voor een APK keuring volgende week dinsdag."

---

### 6. Customer Recognition
When integrated with phone system, Harry recognizes returning customers by their phone number.

**Demo:** Provide phone number "0612345678" to see customer lookup.

---

### 7. Safety-First Design
Harry detects emergencies and responds appropriately:
- Burning smell → "Stop direct! Dit klinkt als een noodgeval."
- Brake failure → "Rijd niet verder. Bel pechhulp of 112."
- Red warning lights → Escalates to urgent advice

---

## Live Demo Guide

### Prerequisites
1. Start the server: `python -m uvicorn bridge.api:app --port 8000`
2. Open dashboard: http://localhost:8000/web/index.html
3. Allow microphone access

### Demo Script

#### Scene 1: Basic Greeting
1. Click microphone button
2. Wait for Harry's greeting: "Moin! Ik ben Harry..."
3. Respond naturally in Dutch or English

#### Scene 2: Vehicle Lookup (RDW Integration)
1. Say: "Mijn kenteken is 1-KBB-49"
2. Harry will look up the vehicle in the RDW database
3. Observe: Make, model, APK status displayed

#### Scene 3: Parts Inquiry
1. Say: "Hebben jullie remblokken?"
2. Harry checks the inventory database
3. Returns: Stock status and pricing

#### Scene 4: Appointment Booking
1. Say: "Ik wil een afspraak maken voor een APK"
2. Provide a date when asked
3. Observe: Werkorder created in system

#### Scene 5: Database Visualization
1. Click on "Database" tab in dashboard
2. View live data: Customers, Vehicles, Work Orders, Parts
3. Watch updates in real-time as Harry creates records

---

## Technical Highlights

| Metric | Value |
|--------|-------|
| Response Latency | < 800ms end-to-end |
| Voice Model | Google Gemini 2.0 Flash (Native Audio) |
| Languages | Dutch (primary), English |
| Database | WinCar DMS Integration (SQL Server) |
| Phone Integration | Twilio Media Streams |

---

## Architecture Overview

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Phone/Web     │────▶│  GarageAI       │────▶│  Google Gemini  │
│   Customer      │◀────│  Bridge         │◀────│  Live API       │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                    ┌────────────┼────────────┐
                    ▼            ▼            ▼
              ┌──────────┐ ┌──────────┐ ┌──────────┐
              │ WinCar   │ │ RDW API  │ │ Web      │
              │ Database │ │ (Dutch   │ │ Search   │
              │          │ │ Vehicle) │ │          │
              └──────────┘ └──────────┘ └──────────┘
```

---

## Supported Tools

| Tool | Function | Data Source |
|------|----------|-------------|
| `lookup_vehicle_rdw` | Vehicle info by kenteken | RDW Open Data |
| `check_apk_status` | APK expiry check | RDW Open Data |
| `get_vehicle_recalls` | Recall/safety notices | RDW Open Data |
| `identify_customer` | Customer lookup | WinCar CRM |
| `check_werkorder_status` | Repair status | WinCar Workshop |
| `check_part_stock` | Parts inventory | WinCar Warehouse |
| `schedule_appointment` | Book appointment | WinCar Planning |
| `web_search` | General questions | DuckDuckGo |

---

## Sample Conversations

### Conversation 1: APK Check
```
Customer: "Hoi, ik wil weten wanneer mijn APK verloopt.
          Mijn kenteken is 1-KBB-49."

Harry:    "Ik zie dat u een Volvo V40 uit 2013 rijdt.
          Uw APK is geldig tot 8 december 2026, nog 311 dagen.
          Geen actie nodig op dit moment!"
```

### Conversation 2: Parts Inquiry
```
Customer: "Hebben jullie remblokken voor een Golf?"

Harry:    "Ja, we hebben remblokken op voorraad.
          De prijs is €45,99 per set.
          Zal ik een afspraak maken voor montage?"
```

### Conversation 3: Emergency
```
Customer: "Er komt rook uit mijn motorkap!"

Harry:    "Stop direct en zet uw auto veilig aan de kant!
          Dit kan een ernstig probleem zijn.
          Bel 112 als er brand is, of pechhulp voor assistentie.
          Rijd niet verder totdat het is onderzocht."
```

---

## Contact

**Garage Wiefferink**
Powered by GarageAI v2.0

*"Slimme service, 24/7 bereikbaar"*
