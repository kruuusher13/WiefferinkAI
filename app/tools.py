import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

try:
    import requests
except ImportError:
    requests = None

from typing import Optional, List, Dict, Any
import re
import json
import time
from langchain_core.tools import tool
from pydantic import BaseModel, Field


# --- RDW (Dutch Vehicle Authority) Tools ---

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
        model = vehicle.get("handelsbenaming", "Onbekend")
        eerste_toelating = _format_rdw_date(vehicle.get("datum_eerste_toelating", ""))
        brandstof = vehicle.get("brandstof_omschrijving", "Onbekend")
        apk_vervaldatum = vehicle.get("vervaldatum_apk", "")
        apk_formatted = _format_rdw_date(apk_vervaldatum)
        days_left = _days_until(apk_vervaldatum)

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
            return (f"WAARSCHUWING: De APK van uw {merk} {model} is VERLOPEN "
                   f"op {apk_formatted} ({abs(days_left)} dagen geleden). "
                   f"U mag niet meer rijden op de openbare weg! "
                   f"Zal ik direct een APK-afspraak inplannen?")
        elif days_left <= 14:
            return (f"DRINGEND: Uw APK verloopt over {days_left} dagen ({apk_formatted}). "
                   f"Ik raad aan om direct een afspraak te maken. Zal ik dat doen?")
        elif days_left <= 30:
            return (f"Let op: De APK van uw {merk} {model} verloopt over {days_left} dagen "
                   f"({apk_formatted}). Dit is een goed moment om een afspraak te maken.")
        elif days_left <= 60:
            return (f"Ter info: De APK van uw {merk} {model} verloopt op {apk_formatted} "
                   f"(over {days_left} dagen). Wilt u alvast inplannen?")
        else:
            return (f"De APK van uw {merk} {model} is geldig tot {apk_formatted} "
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

        active_recalls = []
        for recall in recall_data:
            beschrijving = recall.get("code_defect_omschrijving", "Onbekend defect")
            active_recalls.append(f"• {beschrijving}")

        if active_recalls:
            result = (f"Er zijn {len(active_recalls)} terugroepactie(s) voor uw {merk} {model}:\n"
                     + "\n".join(active_recalls[:3]))
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


# --- Appointment Request Tool ---

class AppointmentRequestInput(BaseModel):
    date_time: str = Field(description="The requested date and time for the appointment (e.g., '2026-04-01 14:00').")
    description: str = Field(description="Description of the work needed (e.g., 'APK keuring', 'Grote beurt', 'Proefrit').")
    customer_name: str = Field(description="Full name of the customer.")
    phone_number: str = Field(description="Customer phone number for confirmation.")
    customer_email: str = Field(description="Customer email address for sending confirmation.")
    kenteken: str = Field(default="", description="Vehicle license plate (kenteken). Optional for test drives.")

@tool("request_appointment", args_schema=AppointmentRequestInput)
def request_appointment(
    date_time: str,
    description: str,
    customer_name: str,
    phone_number: str,
    customer_email: str,
    kenteken: str = ""
) -> str:
    """
    Request an appointment at the garage. This creates a PROPOSAL that the garage owner
    will review and accept. The customer will receive a confirmation email once accepted.
    Minimum date: 3 weeks from today. Collects name, phone, email, kenteken, date, and description.
    """
    try:
        requested = datetime.strptime(date_time, "%Y-%m-%d %H:%M")
    except ValueError:
        try:
            requested = datetime.strptime(date_time, "%Y-%m-%d")
        except ValueError:
            return "Ongeldige datum. Gebruik het formaat YYYY-MM-DD HH:MM."

    minimum_date = (datetime.now() + timedelta(weeks=3)).date()
    if requested.date() < minimum_date:
        return (f"De vroegst mogelijke datum is {minimum_date.strftime('%d-%m-%Y')}. "
                f"Kies een datum minimaal 3 weken in de toekomst.")

    details = (
        f"Afspraakverzoek ontvangen:\n"
        f"• Klant: {customer_name}\n"
        f"• Telefoon: {phone_number}\n"
        f"• E-mail: {customer_email}\n"
        f"• Datum/tijd: {date_time}\n"
        f"• Omschrijving: {description}\n"
    )
    if kenteken:
        details += f"• Kenteken: {kenteken}\n"

    details += (
        f"\nHet verzoek is geregistreerd. "
        f"De garage eigenaar beoordeelt dit en u ontvangt een bevestigingsmail zodra de afspraak is bevestigd."
    )
    return details


# --- Occasions (Car Sales) Tools ---

_occasions_cache: Dict[str, Any] = {"data": None, "timestamp": 0}
_CACHE_TTL = 600  # 10 minutes

def _parse_cars_from_html(html: str) -> List[Dict[str, Any]]:
    """Extract car objects from JSON-LD in an HTML page."""
    pattern = r'<script\s+type=["\']application/ld\+json["\']\s*>(.*?)</script>'
    matches = re.findall(pattern, html, re.DOTALL)
    cars = []
    for block in matches:
        try:
            data = json.loads(block)
        except json.JSONDecodeError:
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            item_type = item.get("@type", "")
            if item_type in ("Car", "Vehicle", "Product"):
                cars.append(item)
            elif item_type == "ItemList":
                for elem in item.get("itemListElement", []):
                    inner = elem.get("item", elem)
                    cars.append(inner)
            elif item_type == "SearchResultsPage":
                main_entity = item.get("mainEntity", {})
                if main_entity.get("@type") == "ItemList":
                    for elem in main_entity.get("itemListElement", []):
                        inner = elem.get("item", elem)
                        if inner.get("@type") in ("Car", "Vehicle", "Product"):
                            cars.append(inner)
    return cars


def _fetch_occasions() -> List[Dict[str, Any]]:
    """Fetch and cache ALL car listings from wiefferink.com/occasions/ (all pages)."""
    now = time.time()
    if _occasions_cache["data"] is not None and (now - _occasions_cache["timestamp"]) < _CACHE_TTL:
        return _occasions_cache["data"]

    if requests is None:
        return []

    try:
        resp = requests.get("https://www.wiefferink.com/occasions/", timeout=8)
        resp.raise_for_status()
        html = resp.text

        cars = _parse_cars_from_html(html)

        total_match = re.search(r'<meta\s+name="total-count"\s+content="(\d+)"', html)
        result_match = re.search(r'<meta\s+name="result-count"\s+content="(\d+)"', html)

        if total_match and result_match:
            total = int(total_match.group(1))
            per_page = int(result_match.group(1))

            if total > per_page:
                pages_needed = (total + per_page - 1) // per_page
                for page_num in range(2, pages_needed + 1):
                    try:
                        page_resp = requests.get(
                            f"https://www.wiefferink.com/occasions/?page={page_num}",
                            timeout=8
                        )
                        page_resp.raise_for_status()
                        cars.extend(_parse_cars_from_html(page_resp.text))
                    except Exception:
                        break

        _occasions_cache["data"] = cars
        _occasions_cache["timestamp"] = now
        return cars

    except Exception:
        if _occasions_cache["data"] is not None:
            return _occasions_cache["data"]
        return []


def _extract_car_field(car: Dict, keys: List[str], default: str = "") -> str:
    """Extract a field from a JSON-LD car object, trying multiple key paths."""
    for key in keys:
        val = car.get(key)
        if val:
            return str(val) if not isinstance(val, dict) else val.get("name", str(val))
    return default


class SearchCarsInput(BaseModel):
    budget: Optional[str] = Field(default=None, description="Maximum price in euros (e.g., '15000').")
    fuel_type: Optional[str] = Field(default=None, description="Fuel type: benzine, diesel, elektrisch, hybride.")
    brand: Optional[str] = Field(default=None, description="Car brand/make (e.g., 'Volkswagen', 'Toyota').")
    body_type: Optional[str] = Field(default=None, description="Body type (e.g., 'SUV', 'sedan', 'hatchback').")


@tool("search_available_cars", args_schema=SearchCarsInput)
def search_available_cars(
    budget: Optional[str] = None,
    fuel_type: Optional[str] = None,
    brand: Optional[str] = None,
    body_type: Optional[str] = None
) -> str:
    """
    Search available used cars (occasions) for sale at Garage Wiefferink.
    Returns matching cars with brand, model, year, mileage, price, fuel type, and link.
    Use when customers ask about buying a car, available occasions, or car recommendations.
    """
    cars = _fetch_occasions()

    if not cars:
        return ("Op dit moment kan ik de voorraad niet ophalen. "
                "Bekijk onze occasions op https://www.wiefferink.com/occasions/ "
                "of bel ons voor actuele beschikbaarheid.")

    results = []
    for car in cars:
        car_name = _extract_car_field(car, ["name", "headline", "description"], "Onbekend")
        car_brand = _extract_car_field(car, ["brand", "manufacturer"], "")
        car_model = _extract_car_field(car, ["model", "vehicleModelDate"], "")

        price_val = None
        offers = car.get("offers", car.get("offer", {}))
        if isinstance(offers, dict):
            price_str = offers.get("price", offers.get("lowPrice", ""))
            if price_str:
                try:
                    price_val = float(re.sub(r'[^\d.]', '', str(price_str)))
                except ValueError:
                    pass
        elif isinstance(offers, list) and offers:
            price_str = offers[0].get("price", "")
            if price_str:
                try:
                    price_val = float(re.sub(r'[^\d.]', '', str(price_str)))
                except ValueError:
                    pass
        if price_val is None:
            price_str = car.get("price", car.get("priceSpecification", {}).get("price", ""))
            if price_str:
                try:
                    price_val = float(re.sub(r'[^\d.]', '', str(price_str)))
                except ValueError:
                    pass

        car_fuel = _extract_car_field(car, ["fuelType", "fuel"], "").lower()
        car_body = _extract_car_field(car, ["bodyType", "vehicleBodyType"], "").lower()
        car_year = _extract_car_field(car, ["vehicleModelDate", "modelDate", "dateVehicleFirstRegistered"], "")
        if car_year and len(car_year) >= 4:
            car_year = car_year[:4]

        car_km_raw = car.get("mileageFromOdometer", "")
        if isinstance(car_km_raw, dict):
            car_km = str(car_km_raw.get("value", ""))
        else:
            car_km = str(car_km_raw) if car_km_raw else ""
        if car_km:
            km_match = re.search(r'[\d]+', car_km.replace(',', '').replace('.', ''))
            car_km = km_match.group() if km_match else car_km

        car_url = _extract_car_field(car, ["url", "@id"], "https://www.wiefferink.com/occasions/")

        if budget:
            try:
                max_price = float(re.sub(r'[^\d.]', '', budget))
                if price_val is not None and price_val > max_price:
                    continue
            except ValueError:
                pass

        if fuel_type and car_fuel and fuel_type.lower() not in car_fuel:
            continue

        if brand and car_brand and brand.lower() not in car_brand.lower() and brand.lower() not in car_name.lower():
            continue

        if body_type and car_body and body_type.lower() not in car_body:
            continue

        display_name = car_name if car_name != "Onbekend" else f"{car_brand} {car_model}".strip()
        line = f"• {display_name}"
        if car_year:
            line += f" ({car_year})"
        if price_val is not None:
            line += f" - €{price_val:,.0f}"
        if car_km:
            line += f" - {car_km} km"
        if car_fuel:
            line += f" - {car_fuel}"
        if car_url:
            line += f"\n  Link: {car_url}"

        results.append(line)

    if not results:
        filter_desc = []
        if budget:
            filter_desc.append(f"budget €{budget}")
        if fuel_type:
            filter_desc.append(fuel_type)
        if brand:
            filter_desc.append(brand)
        if body_type:
            filter_desc.append(body_type)
        filter_str = ", ".join(filter_desc) if filter_desc else "deze criteria"
        return (f"Geen occasions gevonden voor {filter_str}. "
                f"Bekijk al onze auto's op https://www.wiefferink.com/occasions/ "
                f"of vraag naar andere opties.")

    header = f"Beschikbare occasions ({len(results)} gevonden):\n\n"
    return header + "\n\n".join(results[:10])
