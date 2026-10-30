"""Pydantic models for the tables in world/data/ (GAME-04: content is data)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Stat = Literal["vigor", "agility", "intellect", "resolve", "presence"]
_ID = r"^[a-z][a-z0-9_]*$"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class God(_Strict):
    id: str = Field(pattern=_ID)
    name: str
    affinities: tuple[str, str]
    favoured_classes: tuple[str, ...]
    first_oath: str


class Affinities(_Strict):
    basic: tuple[str, ...]
    rare: tuple[str, ...]
    sealed_rare_slots: int = Field(ge=0)

    def all_named(self) -> tuple[str, ...]:
        return self.basic + self.rare


class Oath(_Strict):
    id: str = Field(pattern=_ID)
    name: str
    god: str
    affinity: str


class BaseClass(_Strict):
    id: str = Field(pattern=_ID)
    name: str
    primary: Stat
    secondary: Stat


class People(_Strict):
    id: str = Field(pattern=_ID)
    name: str
    innate_affinity: tuple[str, ...]
    stat: Stat | Literal["any"]


class Professions(_Strict):
    gathering: tuple[str, ...]
    crafting: tuple[str, ...]
    service: tuple[str, ...]

    def all(self) -> tuple[str, ...]:
        return self.gathering + self.crafting + self.service


class Flag(_Strict):
    """One entry of the flag registry (world/data/flags.yaml, world/sealed/data/flags.yaml; D-024)."""

    key: str = Field(pattern=r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*$")
    kind: Literal["bool", "counter"]
    set_by: Literal["engine", "beat", "narrator"]
    when: str = Field(min_length=1)
    accept: str | None = None

    @model_validator(mode="after")
    def _narrator_flags_need_a_rule(self) -> Flag:
        if self.set_by == "narrator" and not self.accept:
            raise ValueError(f"flag {self.key}: set_by narrator needs an accept rule the engine checks")
        return self


class FlagRegistry(_Strict):
    flags: tuple[Flag, ...]


class Origin(_Strict):
    id: str = Field(pattern=_ID)
    name: str
    stat: Stat
    skill: str
    standing: dict[str, int]
    complication: str


class Origins(_Strict):
    start_coin_silver: int = Field(ge=0)
    stat_array: tuple[int, int, int, int, int]
    flaws: tuple[str, ...]
    origins: tuple[Origin, ...]


class LevelGains(_Strict):
    primary: int = Field(ge=0)
    secondary: int = Field(ge=0)
    free_points: int = Field(ge=0)


class Rewards(_Strict):
    xp: dict[str, int]
    xp_per_turn_cap: int = Field(gt=0)
    level_gains: LevelGains
    standing: dict[str, int]
    damage_percent: dict[str, int]
    heal_percent: dict[str, int]


class GameData(_Strict):
    gods: tuple[God, ...]
    affinities: Affinities
    oaths: tuple[Oath, ...]
    classes: tuple[BaseClass, ...]
    peoples: tuple[People, ...]
    professions: Professions
    origins: Origins
    rewards: Rewards

    def god_ids(self) -> tuple[str, ...]:
        return tuple(g.id for g in self.gods)
