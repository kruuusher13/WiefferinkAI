"""
Google Calendar OAuth2 token storage and helpers.

Follows the same file-based persistence pattern as bridge/state.py.

Env vars:
  GOOGLE_OAUTH_CLIENT_ID     — OAuth2 client ID
  GOOGLE_OAUTH_CLIENT_SECRET — OAuth2 client secret
"""

import json
import os
import logging

from google.oauth2.credentials import Credentials

logger = logging.getLogger("TorxFlow.calendar_auth")

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]

_TOKEN_FILE = os.path.join(os.path.dirname(__file__), "..", "google_calendar_tokens.json")


def _load_tokens() -> dict:
    try:
        with open(_TOKEN_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_tokens(tokens: dict) -> None:
    try:
        with open(_TOKEN_FILE, "w", encoding="utf-8") as f:
            json.dump(tokens, f, ensure_ascii=False, indent=2)
    except OSError as e:
        logger.error(f"Failed to persist calendar tokens: {e}")


def delete_tokens() -> None:
    try:
        os.remove(_TOKEN_FILE)
    except FileNotFoundError:
        pass


def is_connected() -> bool:
    tokens = _load_tokens()
    return bool(tokens.get("refresh_token"))


def get_credentials() -> Credentials:
    """Build Credentials from stored tokens. Raises if not connected."""
    tokens = _load_tokens()
    if not tokens.get("refresh_token"):
        raise CalendarNotConnectedError("Google Calendar is not connected")

    creds = Credentials(
        token=tokens.get("access_token"),
        refresh_token=tokens["refresh_token"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["GOOGLE_OAUTH_CLIENT_ID"],
        client_secret=os.environ["GOOGLE_OAUTH_CLIENT_SECRET"],
        scopes=SCOPES,
    )

    if creds.expired and creds.refresh_token:
        from google.auth.transport.requests import Request
        creds.refresh(Request())
        _save_tokens({
            "access_token": creds.token,
            "refresh_token": creds.refresh_token,
        })

    return creds


def get_auth_url(redirect_uri: str) -> str:
    """Build the Google OAuth2 consent URL (no PKCE — stateless)."""
    from urllib.parse import urlencode
    params = {
        "client_id": os.environ["GOOGLE_OAUTH_CLIENT_ID"],
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
    }
    return f"https://accounts.google.com/o/oauth2/auth?{urlencode(params)}"


def exchange_code(code: str, redirect_uri: str) -> None:
    """Exchange an authorization code for tokens and persist them."""
    import requests as req
    resp = req.post("https://oauth2.googleapis.com/token", data={
        "code": code,
        "client_id": os.environ["GOOGLE_OAUTH_CLIENT_ID"],
        "client_secret": os.environ["GOOGLE_OAUTH_CLIENT_SECRET"],
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    })
    resp.raise_for_status()
    data = resp.json()
    _save_tokens({
        "access_token": data["access_token"],
        "refresh_token": data.get("refresh_token", ""),
    })


class CalendarNotConnectedError(Exception):
    """Raised when calendar operations are attempted without OAuth2 tokens."""
    pass
