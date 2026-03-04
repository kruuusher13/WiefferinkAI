"""
Email notifications for TorxFlow using Resend.

Env vars:
  RESEND_API_KEY      — Resend API key (re_xxx)
  FROM_EMAIL          — Sender address (e.g. harry@torxflow.nl)
  GARAGE_OWNER_EMAIL  — Owner's email for notifications
  GARAGE_NAME         — Display name (e.g. Garage Wiefferink)
  GARAGE_ADDRESS      — Physical address
  GARAGE_PHONE        — Garage phone number
"""

import os
import logging

import resend

logger = logging.getLogger("TorxFlow.email")

resend.api_key = os.getenv("RESEND_API_KEY", "")

FROM_EMAIL = os.getenv("FROM_EMAIL", "harry@torxflow.nl")
GARAGE_OWNER_EMAIL = os.getenv("GARAGE_OWNER_EMAIL", "info@wiefferink.com")
GARAGE_NAME = os.getenv("GARAGE_NAME", "Garage Wiefferink")
GARAGE_ADDRESS = os.getenv("GARAGE_ADDRESS", "Industriestraat 12, 7461 PA Rijssen")
GARAGE_PHONE = os.getenv("GARAGE_PHONE", "0546-577766")


def send_owner_notification(
    customer_name: str,
    phone_number: str,
    customer_email: str,
    date_time: str,
    description: str,
    kenteken: str = "",
) -> None:
    """Notify the garage owner about a new appointment request."""
    subject = f"Nieuw afspraakverzoek: {customer_name} - {description}"

    body = (
        f"Er is een nieuw afspraakverzoek binnengekomen via TorxFlow.\n\n"
        f"KLANTGEGEVENS:\n"
        f"  Naam:        {customer_name}\n"
        f"  Telefoon:    {phone_number}\n"
        f"  E-mail:      {customer_email}\n"
    )
    if kenteken:
        body += f"  Kenteken:    {kenteken}\n"
    body += (
        f"\nAFSPRAAK:\n"
        f"  Datum/tijd:  {date_time}\n"
        f"  Omschrijving: {description}\n"
        f"\nGa naar het TorxFlow dashboard om het verzoek te accepteren.\n"
    )

    try:
        resend.Emails.send({
            "from": f"TorxFlow <{FROM_EMAIL}>",
            "to": [GARAGE_OWNER_EMAIL],
            "subject": subject,
            "text": body,
        })
        logger.info(f"Owner notification sent for {customer_name}")
    except Exception as e:
        logger.error(f"Failed to send owner notification: {e}")


def send_customer_confirmation(
    to_email: str,
    customer_name: str,
    date_time: str,
    description: str,
) -> None:
    """Send appointment confirmation email to the customer."""
    subject = f"Bevestiging afspraak - {GARAGE_NAME}"

    body = (
        f"Beste {customer_name},\n\n"
        f"Uw afspraak bij {GARAGE_NAME} is bevestigd.\n\n"
        f"AFSPRAAK DETAILS:\n"
        f"  Datum/tijd:   {date_time}\n"
        f"  Omschrijving: {description}\n\n"
        f"LOCATIE:\n"
        f"  {GARAGE_NAME}\n"
        f"  {GARAGE_ADDRESS}\n"
        f"  Tel: {GARAGE_PHONE}\n\n"
        f"Heeft u vragen of wilt u de afspraak wijzigen? "
        f"Neem gerust contact met ons op via {GARAGE_PHONE}.\n\n"
        f"Met vriendelijke groet,\n"
        f"Harry — {GARAGE_NAME}\n"
    )

    try:
        resend.Emails.send({
            "from": f"{GARAGE_NAME} <{FROM_EMAIL}>",
            "to": [to_email],
            "subject": subject,
            "text": body,
        })
        logger.info(f"Confirmation email sent to {to_email}")
    except Exception as e:
        logger.error(f"Failed to send customer confirmation: {e}")
