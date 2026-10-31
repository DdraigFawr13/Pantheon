"""One uncommitted turn of play: a copy of the state, the RNG and the events it produced (architecture 3)."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any

from pantheon.engine.checks import Outcome
from pantheon.engine.rng import RngStreams
from pantheon.engine.state import STANDING_MAX, STANDING_MIN, EventRecord, GameState, apply_event
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
        self.rested = False
        self.exempt_from_limits = False
        self.call_counts: Counter[str] = Counter()

    def count_call(self, name: str, limit: int) -> None:
        """Refuse a narrator call past its per-turn limit (D-031)."""
        if self.exempt_from_limits:
            return
        if self.call_counts[name] >= limit:
            raise Rejected(f"{name} has reached its limit this turn")
        self.call_counts[name] += 1

    def emit(self, type_: str, payload: dict[str, Any]) -> None:
        apply_event(self.state, type_, payload)
        self.events.append((type_, payload))


def change_standing(sim: Simulation, entity: str, delta: int, reason: str) -> None:
    current = sim.state.standing.get(entity, 0)
    value = max(STANDING_MIN, min(STANDING_MAX, current + delta))
    sim.emit(
        "standing_changed", {"entity": entity, "delta": value - current, "value": value, "reason": reason}
    )
