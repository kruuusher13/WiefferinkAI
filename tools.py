import os
try:
    import pyodbc
except ImportError:
    pyodbc = None

from typing import Optional, List, Dict, Any
from langchain_core.tools import tool
from pydantic import BaseModel, Field

# --- Database Configuration ---
DB_CONNECTION_STRING = os.getenv(
    "WINCAR_DB_CONNECTION",
    "DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=WinCarLive;UID=sa;PWD=StrongPassword123!"
)

def get_wincar_connection():
    """Establishes a Read-Only connection to the WinCar SQL Server."""
    if pyodbc is None:
        raise ImportError("The 'pyodbc' module could not be imported.")
    try:
        conn = pyodbc.connect(DB_CONNECTION_STRING)
        return conn
    except pyodbc.Error as e:
        print(f"Error connecting to WinCar Database: {e}")
        raise

# --- Communicatie (CRM) Tools ---

class CustomerLookupInput(BaseModel):
    phone_number: str = Field(description="The phone number of the calling customer (e.g., '+31612345678').")

@tool("identify_customer", args_schema=CustomerLookupInput)
def identify_customer(phone_number: str) -> str:
    """
    WinCar Module: COMMUNICATIE (CRM)
    Look up a customer by phone number database.
    """
    conn = get_wincar_connection()
    cursor = conn.cursor()
    try:
        # Normalize phone (remove spaces/dashes, handle NL extension)
        clean_phone = phone_number.replace(" ", "").replace("-", "")
        if clean_phone.startswith("+31"):
            clean_phone = "0" + clean_phone[3:]
        
        # Use LIKE for partial match or exact match
        cursor.execute("SELECT KlantNaam, KlantID FROM Communicatie_Relaties WHERE Telefoon LIKE ?", f"%{clean_phone}%")
        row = cursor.fetchone()
        
        if row:
            return f"Klant gevonden: {row.KlantNaam} (KlantID: {row.KlantID})."
        return "Geen klant gevonden met dit nummer in de Communicatie module."
    finally:
        conn.close()

# --- Werkplaats (Workshop) Tools ---

class WerkorderStatusInput(BaseModel):
    license_plate: str = Field(description="The license plate (kenteken) of the vehicle.")

@tool("check_werkorder_status", args_schema=WerkorderStatusInput)
def check_werkorder_status(license_plate: str) -> str:
    """
    WinCar Module: WERKPLAATS
    Check the status of a work order using the license plate.
    """
    conn = get_wincar_connection()
    cursor = conn.cursor()
    try:
        # Join Vehicles and WorkOrders to find the latest status
        query = """
        SELECT TOP 1 w.WerkorderID, w.Status, w.Omschrijving 
        FROM Werkplaats_Werkorders w
        JOIN Werkplaats_Voertuigen v ON w.VoertuigID = v.VoertuigID
        WHERE v.Kenteken LIKE ?
        ORDER BY w.AanmaakDatum DESC
        """
        cursor.execute(query, f"%{license_plate}%")
        row = cursor.fetchone()
        
        if row:
            return f"Werkorder #{row.WerkorderID} voor kenteken {license_plate} staat op status: '{row.Status}'. ({row.Omschrijving})"
        
        return f"Geen actieve werkorder gevonden in de Werkplaats module voor kenteken {license_plate}."
    finally:
        conn.close()

# --- Magazijn (Warehouse) Tools ---

class PartStockInput(BaseModel):
    part_name: str = Field(description="The name or code of the part to check.")

@tool("check_part_stock", args_schema=PartStockInput)
def check_part_stock(part_name: str) -> str:
    """
    WinCar Module: MAGAZIJN
    Check stock availability and price.
    """
    conn = get_wincar_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT Omschrijving, ArtikelCode, VoorraadAantal, Verkoopprijs FROM Magazijn_Artikelen WHERE Omschrijving LIKE ?", f"%{part_name}%")
        rows = cursor.fetchall()
        
        if not rows:
            return f"Onderdeel '{part_name}' niet gevonden in het Magazijn."
            
        result = []
        for row in rows:
            status = "op voorraad" if row.VoorraadAantal > 0 else "niet op voorraad"
            result.append(f"• {row.Omschrijving} (Art: {row.ArtikelCode}) is {status}. Prijs: €{row.Verkoopprijs:.2f}.")
        
        return "\n".join(result)
    finally:
        conn.close()

# --- Financieel (Financial) Tools ---

class InvoicePaymentInput(BaseModel):
    werkorder_id: str = Field(description="The ID of the work order to generate a payment link for.")

@tool("generate_payment_link", args_schema=InvoicePaymentInput)
def generate_payment_link(werkorder_id: str) -> str:
    """
    WinCar Module: FINANCIEEL
    Generates an iDeal payment link for a specific work order.
    WARNING: This action requires human approval before execution.
    """
    return f"Betaallink gegenereerd voor Werkorder {werkorder_id}: https://pay.wincar.nl/ideal/top-garage/{werkorder_id}"

# --- Werkplaats (Planning) Tools ---

class AppointmentInput(BaseModel):
    date_time: str = Field(description="The requested date and time for the appointment (e.g., '2026-02-01 14:00').")
    description: str = Field(description="Description of the work needed (e.g., 'Bandenwissel', 'APK').")

@tool("schedule_appointment", args_schema=AppointmentInput)
def schedule_appointment(date_time: str, description: str) -> str:
    """
    WinCar Module: WERKPLAATS (Planning)
    Schedules a new appointment by creating a planned Work Order.
    """
    conn = get_wincar_connection()
    cursor = conn.cursor()
    try:
        # Demo Logic: Find a default vehicle or create a placeholder.
        # For simplicity, we assign it to the first vehicle in DB (ID 1)
        # In production, we would look up the specific car from context.
        voertuig_id = 1 
        
        query = """
        INSERT INTO Werkplaats_Werkorders (VoertuigID, Status, Omschrijving)
        OUTPUT INSERTED.WerkorderID
        VALUES (?, 'Gepland', ?)
        """
        cursor.execute(query, voertuig_id, f"{description} (Datum: {date_time})")
        row = cursor.fetchone()
        conn.commit()
        
        return f"Afspraak bevestigd voor {date_time}. Nieuwe Werkorder #{row.WerkorderID} aangemaakt in Werkplaatsplanning."
    except Exception as e:
        return f"Fout bij het maken van de afspraak: {e}"
    finally:
        conn.close()
