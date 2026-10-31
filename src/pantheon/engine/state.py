"""Game state as a pure fold over events (ENG-06). Replay never rolls and never reads the clock."""

from __future__ import annotations

import math
from collections.abc import Iterable
from typing import Any

from pydantic import BaseModel, Field

STATS = ("vigor", "agility", "intellect", "resolve", "presence")
STANDING_MIN, STANDING_MAX = -100, 100

type EventRecord = tuple[str, dict[str, Any]]


def xp_to_next(level: int) -> int:
    cost: float = 100 * float(level) ** 1.5
    return round(cost)


class Hook(BaseModel):
    id: int
    turn: int
    description: str
    due_condition: str
    source_choice: str = ""


class Action(BaseModel):
    label: str
    violent: bool = False
    cost: str | None = None
    tag: str | None = None
    check: dict[str, Any] | None = None


class Shard(BaseModel):
    kind: str  # "skill" or "affinity".
    target: str
    rarity: str = "common"
    fragment: bool = False


class Injury(BaseModel):
    stat: str
    amount: int
    reason: str = ""


class GameState(BaseModel):
    created: bool = False
    name: str = ""
    people: str = ""
    origin: str = ""
    age: int = 0
    flaw: str = ""
    debt: str = ""
    stats: dict[str, int] = Field(default_factory=dict)
    level: int = 0
    xp: int = 0
    class_id: str | None = None
    profession: str | None = None
    free_points: int = 0
    affinities: dict[str, int] = Field(default_factory=dict)
    skills: dict[str, int] = Field(default_factory=dict)
    skill_rarity: dict[str, str] = Field(default_factory=dict)
    skill_offers: list[list[str]] = Field(default_factory=list)
    shards: list[Shard] = Field(default_factory=list)
    titles: list[str] = Field(default_factory=list)
    injuries: list[Injury] = Field(default_factory=list)
    needs_evolution: bool = False
    trial_recovery: bool = False
    oaths: list[str] = Field(default_factory=list)
    standing: dict[str, int] = Field(default_factory=dict)
    coin: int = 0
    wounds: int = 0
    downed: bool = False
    opening_gods: list[str] = Field(default_factory=list)
    offers: list[str] = Field(default_factory=list)
    flags: dict[str, bool | int] = Field(default_factory=dict)
    hooks: list[Hook] = Field(default_factory=list)
    rumours: list[str] = Field(default_factory=list)
    suggested: list[Action] = Field(default_factory=list)
    checks_made: int = 0

    @property
    def tier(self) -> int:
        return math.ceil(self.level / 10)

    @property
    def max_hp(self) -> int:
        return 2 * self.stats.get("vigor", 0) + 10 * self.level

    @property
    def max_mana(self) -> int:
        return 2 * self.stats.get("intellect", 0) + 5 * self.level

    @property
    def max_stamina(self) -> int:
        return 2 * self.stats.get("agility", 0) + 5 * self.level

    @property
    def hp(self) -> int:
        return self.max_hp - self.wounds

    @property
    def offer_resolved(self) -> bool:
        return bool(self.flags.get("opening.dual_offer_resolved"))

    @property
    def needs_class(self) -> bool:
        return self.level >= 1 and self.class_id is None

    @property
    def needs_profession(self) -> bool:
        return self.level >= 1 and self.profession is None

    @property
    def trial_ready(self) -> bool:
        """Level 10, 20 and so on with XP full: the next level takes an Ascension Trial."""
        return self.level > 0 and self.level % 10 == 0 and self.xp >= xp_to_next(self.level)


def apply_event(state: GameState, type_: str, payload: dict[str, Any]) -> None:
    """Apply one resolved event in place. An unknown event is an error, never a silent skip (GAME-05)."""
    match type_:
        case "opening_gods_drawn":
            state.opening_gods = list(payload["gods"])
        case "character_created":
            state.created = True
            for key in ("name", "people", "origin", "age", "flaw", "debt", "coin"):
                setattr(state, key, payload[key])
            state.stats = dict(payload["stats"])
            state.affinities = dict(payload["affinities"])
            state.skills = dict(payload["skills"])
            state.standing = dict(payload["standing"])
        case "oath_offered":
            state.offers.append(payload["oath"])
        case "oath_sworn":
            state.oaths.append(payload["oath"])
            state.affinities[payload["affinity"]] = payload["affinity_rank"]
            state.level = max(state.level, payload["level"])
        case "class_chosen":
            state.class_id = payload["class_id"]
        case "profession_chosen":
            state.profession = payload["profession"]
        case "stat_point_allocated":
            state.stats[payload["stat"]] += 1
            state.free_points -= 1
        case "check_resolved":
            state.checks_made += 1
        case "effect_applied":
            if payload["kind"] == "damage":
                state.wounds += payload["amount"]
            else:
                state.wounds -= payload["amount"]
                state.downed = False
                if payload["source"] == "rest":
                    state.trial_recovery = False
        case "skill_offered":
            state.skill_offers.append(list(payload["options"]))
        case "skill_offers_cleared":
            state.skill_offers = []
        case "skill_gained":
            state.skills[payload["skill"]] = payload["rank"]
            state.skill_rarity[payload["skill"]] = payload["rarity"]
            if payload.get("from_offer"):
                state.skill_offers.pop(0)
        case "affinity_raised":
            state.affinities[payload["affinity"]] = payload["rank"]
        case "shard_gained":
            state.shards.append(Shard(**payload))
        case "shard_used":
            del state.shards[payload["index"]]
        case "title_earned":
            state.titles.append(payload["title"])
            if payload.get("stat"):
                state.stats[payload["stat"]] += payload["bonus"]
        case "injury_gained":
            state.injuries.append(Injury(**payload))
            state.stats[payload["stat"]] -= payload["amount"]
        case "xp_lost":
            state.xp -= payload["amount"]
        case "trial_resolved":
            state.trial_recovery = payload["result"] != "ascend"
            state.needs_evolution = bool(payload.get("evolution_due"))
        case "class_evolved":
            state.class_id = payload["class_id"]
            state.stats[payload["stat"]] += payload["bonus"]
            state.needs_evolution = False
        case "downed":
            state.downed = True
        case "xp_gained":
            state.xp += payload["amount"]
        case "level_up":
            state.xp -= payload["xp_spent"]
            state.level = payload["level"]
            state.free_points += payload["free_points"]
            for stat, gain in payload["gains"].items():
                state.stats[stat] += gain
        case "standing_changed":
            state.standing[payload["entity"]] = payload["value"]
        case "rumour_recorded":
            state.rumours.append(payload["text"])
        case "flag_set":
            state.flags[payload["key"]] = payload["value"]
        case "hook_registered":
            state.hooks.append(Hook(**payload))
        case "actions_suggested":
            state.suggested = [Action(**a) for a in payload["actions"]]
        case "tool_call_dropped":
            pass
        case _:
            raise ValueError(f"unknown event type: {type_}")


def replay(events: Iterable[EventRecord], start: GameState | None = None) -> GameState:
    state = start.model_copy(deep=True) if start else GameState()
    for type_, payload in events:
        apply_event(state, type_, payload)
    return state
