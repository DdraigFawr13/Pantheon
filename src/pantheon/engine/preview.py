"""Odds without an option menu (D-050, D-051): one home for both play paths (GAME-02).

Which checks wait for the player, how a stat's first preview fixes its terms for the turn, and how the
closing thought's `<<ODDS n>>` markers become the engine's odds. Session play and `pantheon play` both
call these, so the rule cannot drift between them.
"""

from __future__ import annotations

import re
from typing import Any

from pantheon.engine.checks import Outcome
from pantheon.engine.state import GameState
from pantheon.engine.tools import check_preview
from pantheon.world.schemas import GameData

ODDS_MARKER = re.compile(r"<<ODDS (\d+)>>")  # Where the engine prints an approach's odds (D-050).
_MARKER_AND_SPACE = re.compile(r"(\s*)<<ODDS (\d+)>>")
_LOCKED = ("difficulty", "challenge_tier")


def needs_preview(check: dict[str, Any]) -> bool:
    """Only Hard checks or harder wait for the player to go ahead; Routine ones roll at once (D-051)."""
    return check.get("difficulty") != "routine"


def lock(seen: dict[str, dict[str, Any]], check: dict[str, Any]) -> dict[str, Any]:
    """A stat's first preview this turn fixes its difficulty and tier, so rewording cannot reshop them.

    `seen` is the turn's record and gains the stat when it is new. Validate the check first: a refused
    check must not fix anything.
    """
    stat = str(check.get("stat", ""))
    if stat in seen:
        return {**check, **{k: seen[stat][k] for k in _LOCKED if k in seen[stat]}}
    seen[stat] = check
    return check


def chance(state: GameState, data: GameData, check: dict[str, Any]) -> str:
    """The odds as the player sees them, from the same calculation as the roll (D-036)."""
    odds = check_preview(state, data, check)
    if odds.shown is not None:
        return f"{odds.shown}%"
    return "sure" if odds.outcome is Outcome.SUCCESS else "no chance"


def preview_text(state: GameState, data: GameData, check: dict[str, Any]) -> str:
    return f"{str(check['stat']).capitalize()} check, {check['difficulty']}: {chance(state, data, check)}"


def strip_markers(narration: str) -> str:
    """Remove every marker and the space before it, for a turn with no actions to give odds for."""
    return _MARKER_AND_SPACE.sub("", narration)


def stamp_odds(narration: str, state: GameState, data: GameData) -> tuple[str, list[int], list[int]]:
    """Print each marked approach's odds where the narrator put it.

    Returns the text, the action numbers shown, and the numbers with no such action, which are removed.
    """
    suggested = state.suggested
    shown: list[int] = []
    missing: list[int] = []

    def odds(match: re.Match[str]) -> str:
        lead, number = match.group(1), int(match.group(2))
        if not 1 <= number <= len(suggested):
            missing.append(number)
            return ""
        shown.append(number)
        check = suggested[number - 1].check
        if check is None:
            return f"{lead}(no roll)"
        return f"{lead}({str(check['stat']).capitalize()} {chance(state, data, check)})"

    return _MARKER_AND_SPACE.sub(odds, narration), sorted(set(shown)), sorted(set(missing))
