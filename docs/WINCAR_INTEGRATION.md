# WinCar Integration Strategy

## Official Module Mapping
This document details how GarageAI tools map to the official **WinCar 2026** software modules defined in the `WinCar-informatiepakket-2026.pdf`.

### 1. Module: COMMUNICATIE (CRM)
**Description**: Centralized customer data, telephony integration, and history.  
**PDF Reference**: Page 10 ("Klantbeheer bundelt alle klantgegevens...").  
**GarageAI Implementation**:
- **Tool**: `identify_customer`
- **Function**: Queries the `Communicatie_Relaties` table.
- **Purpose**: Identifies the caller by phone number immediately upon connection, simulating the "Telefonie-integratie" mentioned in the PDF.

### 2. Module: WERKPLAATS
**Description**: Work order management, planning, and status tracking.  
**PDF Reference**: Page 7 ("Digitale Werkorder", "Realtime statusupdates").  
**GarageAI Implementation**:
- **Tool**: `check_werkorder_status`
- **Function**: Queries `Werkplaats_Werkorders` via `Werkplaats_Voertuigen`.
- **Purpose**: Provides real-time status updates (e.g., "Waiting for parts") to customers, aligning with the "Digitale Werkorder" efficiency goals.

### 3. Module: MAGAZIJN
**Description**: Parts inventory, stock levels, and pricing.  
**PDF Reference**: Page 8 ("Realtime inzicht in de voorraad en beschikbaarheid").  
**GarageAI Implementation**:
- **Tool**: `check_part_stock`
- **Function**: Queries `Magazijn_Artikelen`.
- **Purpose**: Allows the agent to instantly answer questions about part availability and pricing ("Do you have an oil filter for my Golf?").

### 4. Module: FINANCIEEL
**Description**: Invoicing and payment processing, specifically iDeal links.  
**PDF Reference**: Page 9 ("WinCar Betaallink", "iDeal betalingen").  
**GarageAI Implementation**:
- **Tool**: `generate_payment_link`
- **Function**: Generates a URL pointing to `pay.wincar.nl`.
- **Purpose**: Automates the "Betaallink" feature described in the PDF.
- **Safety**: Flagged as a sensitive action requiring user confirmation.

## Database Schema (Mock)
The integration is currently built against a Mock SQL Server schema (`mock_wincar_db.sql`) that strictly mirrors these modules:

```sql
-- Communicatie
CREATE TABLE Communicatie_Relaties (...)

-- Werkplaats
CREATE TABLE Werkplaats_Voertuigen (...)
CREATE TABLE Werkplaats_Werkorders (...)

-- Magazijn
CREATE TABLE Magazijn_Artikelen (...)

-- Financieel
CREATE TABLE Financieel_Facturen (...)
```
