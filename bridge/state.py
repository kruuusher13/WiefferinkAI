"""
Shared state module for TorxFlow.
Provides persistent custom instructions that survive restarts.
"""

import json
import os
import logging

logger = logging.getLogger("TorxFlow")

_STATE_FILE = os.path.join(os.path.dirname(__file__), "..", "custom_instructions.json")

_custom_instructions: str = ""


def _load():
    global _custom_instructions
    try:
        with open(_STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            _custom_instructions = data.get("instructions", "")
    except (FileNotFoundError, json.JSONDecodeError):
        _custom_instructions = ""


def get_custom_instructions() -> str:
    return _custom_instructions


def set_custom_instructions(text: str) -> None:
    global _custom_instructions
    _custom_instructions = text
    try:
        with open(_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump({"instructions": text}, f, ensure_ascii=False, indent=2)
    except OSError as e:
        logger.error(f"Failed to persist custom instructions: {e}")


# Load on import
_load()
