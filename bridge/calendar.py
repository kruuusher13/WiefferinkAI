"""
Google Calendar integration for TorxFlow.

Uses OAuth2 credentials (managed by calendar_auth) to access the garage's calendar.

Env vars:
  GOOGLE_CALENDAR_ID — calendar ID (default: "primary")
"""

import os
import logging
from datetime import datetime, timedelta

from googleapiclient.discovery import build

from bridge.calendar_auth import get_credentials, CalendarNotConnectedError

logger = logging.getLogger("TorxFlow.calendar")

TIMEZONE = "Europe/Amsterdam"
CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID", "primary")


def _get_service():
    """Build an authenticated Calendar API service using OAuth2."""
    credentials = get_credentials()
    return build("calendar", "v3", credentials=credentials, cache_discovery=False)


def get_minimum_date() -> str:
    """Return the minimum appointment date (3 weeks from now) as YYYY-MM-DD."""
    return (datetime.now() + timedelta(weeks=3)).strftime("%Y-%m-%d")


def list_events(days_ahead: int = 30) -> list[dict]:
    """List upcoming events from the garage calendar."""
    service = _get_service()
    now = datetime.utcnow().isoformat() + "Z"
    end = (datetime.utcnow() + timedelta(days=days_ahead)).isoformat() + "Z"

    result = service.events().list(
        calendarId=CALENDAR_ID,
        timeMin=now,
        timeMax=end,
        maxResults=50,
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    events = []
    for item in result.get("items", []):
        start = item.get("start", {}).get("dateTime") or item.get("start", {}).get("date", "")
        end_time = item.get("end", {}).get("dateTime") or item.get("end", {}).get("date", "")
        events.append({
            "id": item.get("id", ""),
            "summary": item.get("summary", ""),
            "start": start,
            "end": end_time,
            "description": item.get("description", ""),
            "htmlLink": item.get("htmlLink", ""),
        })
    return events


def create_event(
    summary: str,
    start_datetime: str,
    duration_minutes: int,
    customer_name: str,
    customer_phone: str,
    customer_email: str,
    kenteken: str,
    description: str,
) -> dict:
    """Create a Google Calendar event and return {id, summary, start, htmlLink}."""
    service = _get_service()

    # Parse the start time
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            start_dt = datetime.strptime(start_datetime, fmt)
            break
        except ValueError:
            continue
    else:
        raise ValueError(f"Cannot parse date: {start_datetime}")

    end_dt = start_dt + timedelta(minutes=duration_minutes)

    event_description = (
        f"Klant: {customer_name}\n"
        f"Telefoon: {customer_phone}\n"
        f"E-mail: {customer_email}\n"
        f"Kenteken: {kenteken}\n"
        f"Omschrijving: {description}\n"
        f"\nAangemaakt via TorxFlow"
    )

    event_body = {
        "summary": summary,
        "description": event_description,
        "start": {
            "dateTime": start_dt.isoformat(),
            "timeZone": TIMEZONE,
        },
        "end": {
            "dateTime": end_dt.isoformat(),
            "timeZone": TIMEZONE,
        },
    }

    created = service.events().insert(calendarId=CALENDAR_ID, body=event_body).execute()
    logger.info(f"Calendar event created: {created.get('id')} - {summary}")

    return {
        "id": created.get("id", ""),
        "summary": created.get("summary", ""),
        "start": created.get("start", {}).get("dateTime", ""),
        "htmlLink": created.get("htmlLink", ""),
    }
