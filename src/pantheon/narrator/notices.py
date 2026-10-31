"""Ledger lines placed in the story at the moment they happen (D-036)."""

from __future__ import annotations

import re
from typing import Any

from pantheon.engine.state import EventRecord

CHECK_MARKER = "<<CHECK>>"
_LEFTOVER = re.compile(r"[ \t]*" + re.escape(CHECK_MARKER) + r"[ \t]*\n*")


def check_notice(payload: dict[str, Any]) -> str:
    outcome = str(payload["outcome"]).replace("_", " ") + (
        " + complication" if payload.get("complication") else ""
    )
    stat = str(payload["stat"]).capitalize()
    if payload.get("automatic"):
        return f"***{stat} check: {outcome}, decided by the tier gap***"
    return f"***{stat} check: {payload['chance']}% chance, rolled {payload['roll']}: {outcome}***"


def place_notices(text: str, events: list[EventRecord]) -> str:
    """The engine prints the dice where the narrator marked them. The narrator never writes them itself."""
    for type_, payload in events:
        if type_ == "check_resolved" and CHECK_MARKER in text:
            text = text.replace(CHECK_MARKER, check_notice(payload), 1)
    return _LEFTOVER.sub("", text).strip()
