"""
Transcript Storage
==================

Persists call transcripts to GCS (production) or local filesystem (dev).
Set TRANSCRIPT_BUCKET env var to enable GCS storage.
"""

import os
import json
import logging
from pathlib import Path

logger = logging.getLogger("TorxFlow")

TRANSCRIPT_BUCKET = os.getenv("TRANSCRIPT_BUCKET")
LOCAL_DIR = Path(__file__).resolve().parent.parent / "transcripts"

# Lazy-init GCS client
_gcs_client = None
_gcs_bucket = None


def _get_bucket():
    global _gcs_client, _gcs_bucket
    if _gcs_bucket is None:
        from google.cloud import storage
        _gcs_client = storage.Client()
        _gcs_bucket = _gcs_client.bucket(TRANSCRIPT_BUCKET)
    return _gcs_bucket


def save_transcript(filename: str, data: dict) -> None:
    """Save transcript JSON. filename should end with .json."""
    payload = json.dumps(data, ensure_ascii=False, indent=2, default=str)

    if TRANSCRIPT_BUCKET:
        blob = _get_bucket().blob(filename)
        blob.upload_from_string(payload, content_type="application/json")
        logger.info(f"Transcript saved to GCS: gs://{TRANSCRIPT_BUCKET}/{filename}")
    else:
        LOCAL_DIR.mkdir(exist_ok=True)
        (LOCAL_DIR / filename).write_text(payload)
        logger.info(f"Transcript saved locally: {filename}")


def list_transcripts() -> list[dict]:
    """List all transcripts with metadata, sorted by date descending."""
    if TRANSCRIPT_BUCKET:
        return _list_gcs()
    return _list_local()


def _list_gcs() -> list[dict]:
    results = []
    for blob in _get_bucket().list_blobs():
        if not blob.name.endswith(".json"):
            continue
        try:
            data = json.loads(blob.download_as_text())
            results.append(_summarize(blob.name.replace(".json", ""), data))
        except Exception:
            continue
    results.sort(key=lambda x: x["date"], reverse=True)
    return results


def _list_local() -> list[dict]:
    if not LOCAL_DIR.exists():
        return []
    results = []
    for f in sorted(LOCAL_DIR.glob("*.json"), reverse=True):
        try:
            data = json.loads(f.read_text())
            results.append(_summarize(f.stem, data))
        except Exception:
            continue
    return results


def _summarize(transcript_id: str, data: dict) -> dict:
    preview = ""
    for msg in data.get("transcript", []):
        if msg.get("role") == "assistant" and msg.get("type") == "speech":
            preview = msg["text"][:100]
            break
    return {
        "id": transcript_id,
        "date": data.get("date", ""),
        "channel": data.get("channel", "unknown"),
        "duration": data.get("duration", 0),
        "preview": preview,
        "message_count": data.get("message_count", 0),
    }


def get_transcript(transcript_id: str) -> dict | None:
    """Read a single transcript by ID (filename without .json)."""
    filename = f"{transcript_id}.json"

    if TRANSCRIPT_BUCKET:
        blob = _get_bucket().blob(filename)
        if not blob.exists():
            return None
        return json.loads(blob.download_as_text())
    else:
        filepath = LOCAL_DIR / filename
        if not filepath.exists():
            return None
        return json.loads(filepath.read_text())
