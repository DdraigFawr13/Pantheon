"""One uncommitted turn of play: a copy of the state, the RNG and the events it produced (architecture 3)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pantheon.engine.checks import Outcome
from pantheon.engine.rng import RngStreams
from pantheon.engine.state import EventRecord, GameState, apply_event
from pantheon.world.schemas import GameData


class Rejected(ValueError):
    """The engine refuses a request. Raised at validate, before any roll or event (D-022)."""


@dataclass(frozen=True)
class Rules:
    data: GameData
    flag_setters: dict[str, str]


class Simulation:
    def __init__(self, state: GameState, rng: RngStreams, rules: Rules, turn: int) -> None:
        self.state = state.model_copy(deep=True)
        self.rng = rng
        self.rules = rules
        self.turn = turn
        self.events: list[EventRecord] = []
        self.checks: dict[str, Outcome] = {}
        self.damaged_by: set[str] = set()
        self.xp_this_turn = 0
        self.suggested = False

    def emit(self, type_: str, payload: dict[str, Any]) -> None:
        apply_event(self.state, type_, payload)
        self.events.append((type_, payload))
