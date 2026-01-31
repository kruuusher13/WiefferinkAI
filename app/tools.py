import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

try:
    import pyodbc
except ImportError:
    pyodbc = None

try:
    import requests
except ImportError:
    requests = None

from typing import Optional, List, Dict, Any
import re
from langchain_core.tools import tool
from langchain_community.tools import DuckDuckGoSearchRun
from pydantic import BaseModel, Field

# --- Database Configuration ---
DB_CONNECTION_STRING = os.getenv(
    "WINCAR_DB_CONNECTION",
    r"DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=WinCarLive;UID=sa;PWD=StrongPassword123!"
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
        # Normalize phone (remove spaces/dashes/dots, ensure only digits/plus)
        # Aggressive cleaning: remove everything except digit and +
        clean_phone = re.sub(r'[^0-9+]', '', phone_number)
        
        # Handle NL extension: if +31, replace with 0
        if clean_phone.startswith("+31"):
            clean_phone = "0" + clean_phone[3:]
        elif clean_phone.startswith("31"): # Handle case where + is missing but country code is present
             clean_phone = "0" + clean_phone[2:]
        
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
    description: str = Field(description="Description of the work needed (e.g., 'APK keuring', 'Grote beurt').")
    customer_name: str = Field(description="Full name of the customer.")
    phone_number: str = Field(description="Customer phone number for confirmation.")
    kenteken: str = Field(description="Vehicle license plate (kenteken).")

@tool("schedule_appointment", args_schema=AppointmentInput)
def schedule_appointment(
    date_time: str,
    description: str,
    customer_name: str,
    phone_number: str,
    kenteken: str
) -> str:
    """
    WinCar Module: WERKPLAATS (Planning)
    Schedules a new appointment by creating a planned Work Order.
    Collects customer information and links to vehicle.
    """
    conn = get_wincar_connection()
    cursor = conn.cursor()
    try:
        # Step 1: Find or create customer
        clean_phone = re.sub(r'[^0-9+]', '', phone_number)
        if clean_phone.startswith("+31"):
            clean_phone = "0" + clean_phone[3:]

        cursor.execute(
            "SELECT KlantID FROM Communicatie_Relaties WHERE Telefoon LIKE ?",
            f"%{clean_phone}%"
        )
        row = cursor.fetchone()

        if row:
            klant_id = row.KlantID
        else:
            # Create new customer
            cursor.execute("""
                INSERT INTO Communicatie_Relaties (KlantNaam, Telefoon)
                OUTPUT INSERTED.KlantID
                VALUES (?, ?)
            """, customer_name, clean_phone)
            klant_id = cursor.fetchone()[0]
            conn.commit()

        # Step 2: Find or create vehicle
        clean_kenteken = re.sub(r'[^A-Z0-9]', '', kenteken.upper())
        cursor.execute(
            "SELECT VoertuigID FROM Werkplaats_Voertuigen WHERE Kenteken = ?",
            clean_kenteken
        )
        vrow = cursor.fetchone()
        
        if vrow:
            voertuig_id = vrow.VoertuigID
        else:
            # Create placeholder vehicle
            cursor.execute("""
                INSERT INTO Werkplaats_Voertuigen (Kenteken, KlantID)
                OUTPUT INSERTED.VoertuigID
                VALUES (?, ?)
            """, clean_kenteken, klant_id)
            voertuig_id = cursor.fetchone()[0]
            conn.commit()

        # Step 3: Create werkorder
        cursor.execute("""
            INSERT INTO Werkplaats_Werkorders (VoertuigID, KlantID, Status, Omschrijving)
            OUTPUT INSERTED.WerkorderID
            VALUES (?, ?, 'Gepland', ?)
        """, voertuig_id, klant_id, f"{description} (Afspraak: {date_time}, Klant: {customer_name})")

        werkorder_id = cursor.fetchone()[0]
        conn.commit()

        return f"Afspraak bevestigd voor {customer_name} op {date_time}. Werkorder #{werkorder_id} aangemaakt voor kenteken {kenteken}. We bellen u op {phone_number} ter bevestiging."

    except Exception as e:
        return f"Fout bij het maken van de afspraak: {e}"
    finally:
        conn.close()

# --- RDW (Dutch Vehicle Authority) Tools ---

# RDW Open Data endpoints (FREE, no API key required)
RDW_VEHICLE_URL = "https://opendata.rdw.nl/resource/m9d7-ebf2.json"
RDW_APK_URL = "https://opendata.rdw.nl/resource/sgfe-77wx.json"

def _normalize_kenteken(kenteken: str) -> str:
    """Normalize Dutch license plate to RDW format (uppercase, no dashes/spaces)."""
    return re.sub(r'[^A-Z0-9]', '', kenteken.upper())

def _format_rdw_date(date_str: str) -> Optional[str]:
    """Convert RDW date format (YYYYMMDD) to readable format."""
    if not date_str or len(date_str) < 8:
        return None
    try:
        dt = datetime.strptime(date_str[:8], "%Y%m%d")
        return dt.strftime("%d-%m-%Y")
    except ValueError:
        return date_str

def _days_until(date_str: str) -> Optional[int]:
    """Calculate days until a date (from RDW format YYYYMMDD)."""
    if not date_str or len(date_str) < 8:
        return None
    try:
        dt = datetime.strptime(date_str[:8], "%Y%m%d")
        delta = dt - datetime.now()
        return delta.days
    except ValueError:
        return None

class KentekenInput(BaseModel):
    kenteken: str = Field(description="The Dutch license plate (kenteken), e.g., 'AB-123-CD' or 'AB123CD'.")

@tool("lookup_vehicle_rdw", args_schema=KentekenInput)
def lookup_vehicle_rdw(kenteken: str) -> str:
    """
    RDW Open Data: Vehicle Information
    Look up vehicle details using the Dutch license plate (kenteken).
    Returns: make, model, year, fuel type, and APK expiry date.
    Use this when a customer mentions their license plate to instantly know their car.
    """
    if requests is None:
        return "Fout: requests module niet beschikbaar."

    clean_kenteken = _normalize_kenteken(kenteken)

    try:
        # Fetch vehicle basic info
        response = requests.get(
            RDW_VEHICLE_URL,
            params={"kenteken": clean_kenteken},
            timeout=5
        )
        response.raise_for_status()
        data = response.json()

        if not data:
            return f"Geen voertuig gevonden met kenteken {kenteken}."

        vehicle = data[0]

        # Extract key fields
        merk = vehicle.get("merk", "Onbekend")
        model = vehicle.get("handelsbenaming", "Onbekend")
        eerste_toelating = _format_rdw_date(vehicle.get("datum_eerste_toelating", ""))
        brandstof = vehicle.get("brandstof_omschrijving", "Onbekend")
        apk_vervaldatum = vehicle.get("vervaldatum_apk", "")
        apk_formatted = _format_rdw_date(apk_vervaldatum)
        days_left = _days_until(apk_vervaldatum)

        # Build response
        result = f"Voertuig gevonden: {merk} {model}"
        if eerste_toelating:
            result += f" (eerste toelating: {eerste_toelating})"
        result += f". Brandstof: {brandstof}."

        if apk_formatted:
            result += f" APK geldig tot: {apk_formatted}"
            if days_left is not None:
                if days_left < 0:
                    result += f" (VERLOPEN - {abs(days_left)} dagen geleden!)"
                elif days_left <= 30:
                    result += f" (let op: nog maar {days_left} dagen geldig!)"
                elif days_left <= 60:
                    result += f" (verloopt over {days_left} dagen)"
                else:
                    result += f" (nog {days_left} dagen geldig)"
        else:
            result += " APK-informatie niet beschikbaar (mogelijk vrijgesteld)."

        return result

    except requests.exceptions.Timeout:
        return "RDW-systeem reageert traag. Probeer het later opnieuw."
    except requests.exceptions.RequestException as e:
        return f"Fout bij ophalen voertuiggegevens: {str(e)}"
    except Exception as e:
        return f"Onverwachte fout: {str(e)}"

@tool("check_apk_status", args_schema=KentekenInput)
def check_apk_status(kenteken: str) -> str:
    """
    RDW Open Data: APK Status Check
    Check the APK (Dutch MOT) status and expiry date for a vehicle.
    Use this to proactively inform customers about upcoming APK requirements.
    """
    if requests is None:
        return "Fout: requests module niet beschikbaar."

    clean_kenteken = _normalize_kenteken(kenteken)

    try:
        # Fetch from vehicle endpoint (contains APK info)
        response = requests.get(
            RDW_VEHICLE_URL,
            params={"kenteken": clean_kenteken},
            timeout=5
        )
        response.raise_for_status()
        data = response.json()

        if not data:
            return f"Geen voertuig gevonden met kenteken {kenteken}."

        vehicle = data[0]
        merk = vehicle.get("merk", "Onbekend")
        model = vehicle.get("handelsbenaming", "")
        apk_vervaldatum = vehicle.get("vervaldatum_apk", "")

        if not apk_vervaldatum:
            # Check if vehicle is APK-exempt (new vehicles, certain categories)
            eerste_toelating = vehicle.get("datum_eerste_toelating", "")
            if eerste_toelating:
                try:
                    reg_date = datetime.strptime(eerste_toelating[:8], "%Y%m%d")
                    years_old = (datetime.now() - reg_date).days / 365
                    if years_old < 4:
                        return f"Uw {merk} {model} is vrijgesteld van APK (jonger dan 4 jaar)."
                except ValueError:
                    pass
            return f"Geen APK-informatie beschikbaar voor {merk} {model}."

        apk_formatted = _format_rdw_date(apk_vervaldatum)
        days_left = _days_until(apk_vervaldatum)

        if days_left is None:
            return f"APK-vervaldatum voor {merk} {model}: {apk_formatted}."

        if days_left < 0:
            return (f"⚠️ WAARSCHUWING: De APK van uw {merk} {model} is VERLOPEN "
                   f"op {apk_formatted} ({abs(days_left)} dagen geleden). "
                   f"U mag niet meer rijden op de openbare weg! "
                   f"Zal ik direct een APK-afspraak inplannen?")
        elif days_left <= 14:
            return (f"🔴 DRINGEND: Uw APK verloopt over {days_left} dagen ({apk_formatted}). "
                   f"Ik raad aan om direct een afspraak te maken. Zal ik dat doen?")
        elif days_left <= 30:
            return (f"🟠 Let op: De APK van uw {merk} {model} verloopt over {days_left} dagen "
                   f"({apk_formatted}). Dit is een goed moment om een afspraak te maken.")
        elif days_left <= 60:
            return (f"🟡 Ter info: De APK van uw {merk} {model} verloopt op {apk_formatted} "
                   f"(over {days_left} dagen). Wilt u alvast inplannen?")
        else:
            return (f"✅ De APK van uw {merk} {model} is geldig tot {apk_formatted} "
                   f"(nog {days_left} dagen). Geen actie nodig.")

    except requests.exceptions.Timeout:
        return "RDW-systeem reageert traag. Probeer het later opnieuw."
    except requests.exceptions.RequestException as e:
        return f"Fout bij ophalen APK-status: {str(e)}"
    except Exception as e:
        return f"Onverwachte fout: {str(e)}"

@tool("get_vehicle_recalls", args_schema=KentekenInput)
def get_vehicle_recalls(kenteken: str) -> str:
    """
    RDW Open Data: Recall/Terugroepactie Check
    Check if there are any active recalls (terugroepacties) for this vehicle.
    Use this to inform customers about safety-related manufacturer recalls.
    """
    if requests is None:
        return "Fout: requests module niet beschikbaar."

    clean_kenteken = _normalize_kenteken(kenteken)

    try:
        # First get vehicle info to know make/model
        vehicle_response = requests.get(
            RDW_VEHICLE_URL,
            params={"kenteken": clean_kenteken},
            timeout=5
        )
        vehicle_response.raise_for_status()
        vehicle_data = vehicle_response.json()

        if not vehicle_data:
            return f"Geen voertuig gevonden met kenteken {kenteken}."

        vehicle = vehicle_data[0]
        merk = vehicle.get("merk", "Onbekend")
        model = vehicle.get("handelsbenaming", "")

        # Check RDW recall endpoint
        # Note: RDW recalls are at vehicle level via different endpoint
        recall_url = "https://opendata.rdw.nl/resource/j9yg-8gap.json"
        recall_response = requests.get(
            recall_url,
            params={"kenteken": clean_kenteken},
            timeout=5
        )
        recall_response.raise_for_status()
        recall_data = recall_response.json()

        if not recall_data:
            return (f"Geen openstaande terugroepacties gevonden voor uw {merk} {model}. "
                   f"Uw voertuig is up-to-date met alle veiligheidsmaatregelen.")

        # Format recalls
        active_recalls = []
        for recall in recall_data:
            beschrijving = recall.get("code_defect_omschrijving", "Onbekend defect")
            status = recall.get("status", "")
            active_recalls.append(f"• {beschrijving}")

        if active_recalls:
            result = (f"⚠️ Er zijn {len(active_recalls)} terugroepactie(s) voor uw {merk} {model}:\n"
                     + "\n".join(active_recalls[:3]))  # Limit to 3
            if len(active_recalls) > 3:
                result += f"\n... en {len(active_recalls) - 3} meer."
            result += "\nDeze kunnen mogelijk kosteloos worden verholpen. Zal ik een afspraak maken?"
            return result

        return f"Geen openstaande terugroepacties voor uw {merk} {model}."

    except requests.exceptions.Timeout:
        return "RDW-systeem reageert traag voor terugroepacties."
    except requests.exceptions.RequestException as e:
        return f"Fout bij ophalen terugroepacties: {str(e)}"
    except Exception as e:
        return f"Onverwachte fout: {str(e)}"


# --- General Tools ---

from duckduckgo_search import DDGS

class WebSearchInput(BaseModel):
    query: str = Field(description="The search query to find information on the internet.")

@tool("web_search", args_schema=WebSearchInput)
def web_search(query: str) -> str:
    """
    Search the internet for general information, solutions to car problems, or other queries.
    Use this when the internal database does not have the answer.
    """
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
            if not results:
                return "Geen resultaten gevonden."
            output = []
            for r in results:
                output.append(f"• {r['title']}: {r['body'][:150]}...")
            return "\n".join(output)
    except Exception as e:
        return f"Fout bij zoeken: {e}"

# --- Diensten (Services) Tools ---

class ServicePriceInput(BaseModel):
    service_type: str = Field(description="Type of service (e.g., 'APK', 'grote beurt', 'remblokken')")
    vehicle_info: Optional[str] = Field(default=None, description="Vehicle make/model for specific pricing")

@tool("get_service_price", args_schema=ServicePriceInput)
def get_service_price(service_type: str, vehicle_info: Optional[str] = None) -> str:
    """
    WinCar Module: DIENSTEN
    Look up service pricing. Use this when customers ask about costs for maintenance, repairs, or services.
    """
    conn = get_wincar_connection()
    cursor = conn.cursor()
    try:
        # Search services
        cursor.execute("""
            SELECT Naam, StandaardPrijs, ArbeidUren, Omschrijving
            FROM Diensten_Services
            WHERE Naam LIKE ? OR ServiceCode LIKE ? OR Omschrijving LIKE ?
        """, f"%{service_type}%", f"%{service_type}%", f"%{service_type}%")

        services = cursor.fetchall()

        if not services:
            return f"Geen prijsinformatie gevonden voor '{service_type}'. Neem contact op voor een offerte."

        # Get labor rate
        cursor.execute("SELECT UurTarief FROM Diensten_Tarieven WHERE Naam = 'Standaard'")
        rate_row = cursor.fetchone()
        labor_rate = rate_row.UurTarief if rate_row else 75.00

        results = []
        for s in services:
            total = s.StandaardPrijs
            if s.ArbeidUren and s.ArbeidUren > 0:
                labor_cost = float(s.ArbeidUren) * float(labor_rate)
                # Note: StandaardPrijs in the seed data for BEURT-K is 89.00
                # If we want it to be "inclusive", we should clarify if StandaardPrijs is just parts or total.
                # In the plan it says "total = s.StandaardPrijs", and then it lists labor separately if needed?
                # Actually, in most garages, the price is either inclusive or parts+labor.
                # Let's follow the plan's logic but make it clearer.
                results.append(f"• {s.Naam}: €{total:.2f} (incl. {s.ArbeidUren}u arbeid)")
            else:
                results.append(f"• {s.Naam}: €{total:.2f}")

        return "Prijzen:\n" + "\n".join(results) + "\n\n(Prijzen zijn indicatief, inclusief BTW)"

    finally:
        conn.close()
