"""Pydantic models for the tables in world/data/ (GAME-04: content is data)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Stat = Literal["vigor", "agility", "intellect", "resolve", "presence"]
Rarity = Literal["common", "uncommon", "rare", "epic", "legendary", "mythic", "divine"]
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
    perk: str
    burden: str


class BaseClass(_Strict):
    id: str = Field(pattern=_ID)
    name: str
    primary: Stat
    secondary: Stat
    fragments_to_fuse: int = Field(default=3, ge=1)
    trait: str = ""  # The signature trait, as worded in world/power_tiers.md.
    blurb: str = ""  # One line on how the class feels to play, for the character page.


class Skill(_Strict):
    id: str = Field(pattern=_ID)
    name: str
    affinity: str | None = None
    rarity: Rarity
    classes: tuple[str, ...] = ()
    pool: Literal["mana", "stamina"] | None = None
    cost: int = Field(default=0, ge=0)
    cooldown: int = Field(default=0, ge=0)


class Title(_Strict):
    id: str = Field(pattern=_ID)
    name: str
    stat: Stat | None = None
    stat_bonus: int = Field(default=0, ge=0)
    check_kind: str | None = None
    check_bonus: int = Field(default=0, ge=0)
    needs_witness: bool = True


class Evolution(_Strict):
    id: str = Field(pattern=_ID)
    name: str
    from_class: str
    primary: Stat
    secondary: Stat
    fragments_to_fuse: int = Field(default=3, ge=1)
    trait: str = ""  # The signature trait, as worded in world/power_tiers.md.
    blurb: str = ""  # One line on how the class feels to play, for the character page.
    needs_affinity: dict[str, int] = Field(default_factory=dict)
    needs_stat: dict[str, int] = Field(default_factory=dict)
    needs_oath: str | None = None
    needs_skill: str | None = None
    needs_title: str | None = None


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


class PetitionTerms(_Strict):
    granted: int = Field(ge=0)
    ignored: int = Field(ge=0)
    days: int = Field(gt=0)


class Rewards(_Strict):
    xp: dict[str, int]
    xp_per_turn_cap: int = Field(gt=0)
    level_gains: LevelGains
    standing: dict[str, int]
    damage_percent: dict[str, int]
    heal_percent: dict[str, int]
    petition: PetitionTerms


class Clock(_Strict):
    id: str = Field(pattern=_ID)
    name: str
    segments: int = Field(gt=0)
    start: int = Field(ge=0)
    filled: str

    @model_validator(mode="after")
    def _starts_within_its_segments(self) -> Clock:
        if self.start > self.segments:
            raise ValueError(f"clock {self.id}: start is above its segments")
        return self


CheckDifficulty = Literal["routine", "hard", "severe", "heroic"]


class Threat(_Strict):
    hits: int = Field(gt=0)
    difficulty: CheckDifficulty


class Intent(_Strict):
    id: str = Field(pattern=_ID)
    label: str
    weight: int = Field(gt=0)
    damage_percent: int = Field(ge=0)
    guards: bool = False


class Trait(_Strict):
    """A class trait the engine runs in fights, as plain effects a class can combine (D-043)."""

    name: str
    attack_bonus_per_success: int = Field(default=0, ge=0)
    attack_bonus_cap: int = Field(default=0, ge=0)
    low_hp_attack_bonus: int = 0
    low_hp_defence_bonus: int = 0
    defence_stats: tuple[Stat, ...] = ()
    pool_discount_percent: dict[Literal["mana", "stamina"], int] = Field(default_factory=dict)
    ambush_attack_bonus: int = Field(default=0, ge=0)
    ambush_hit_multiplier: int = Field(default=1, ge=1)
    studied_attack_bonus: int = Field(default=0, ge=0)
    studied_from_exchange: int = Field(default=2, ge=1)
    attunements: tuple[str, ...] = ()
    attuned_discount_percent: int = Field(default=0, ge=0, le=100)
    attuned_bonus: int = Field(default=0, ge=0)
    hp_for_mana: bool = False
    curse_attack_bonus: int = Field(default=0, ge=0)
    curse_damage_percent: int = Field(default=0, ge=0)
    form_bonus: int = Field(default=0, ge=0)
    form_stats: tuple[Stat, ...] = ()
    form_blocks_skills: bool = False

    @property
    def once_per_fight(self) -> str | None:
        """What `trait: true` on a move does: curse a foe, take a form, or nothing."""
        if self.curse_attack_bonus or self.curse_damage_percent:
            return "curse"
        if self.form_bonus:
            return "form"
        return None


class Combat(_Strict):
    threats: dict[str, Threat]
    intents: tuple[Intent, ...]
    tier_gap_damage_percent: int = Field(ge=0)
    max_foes: int = Field(gt=0)
    max_tier_above: int = Field(ge=0)
    attack_hits: dict[str, int]
    block_percent: dict[str, int]
    guard_difficulty: CheckDifficulty
    flee_difficulty: CheckDifficulty
    pool_regen_percent: int = Field(ge=0)
    overspend_limit_percent: int = Field(ge=0)
    injury_chance_per_percent: int = Field(ge=0)
    last_breath_marks: int = Field(gt=0)
    final_reckoning: int = Field(gt=0)
    traits: dict[str, Trait] = Field(default_factory=dict)


class GameData(_Strict):
    gods: tuple[God, ...]
    affinities: Affinities
    oaths: tuple[Oath, ...]
    classes: tuple[BaseClass, ...]
    peoples: tuple[People, ...]
    professions: Professions
    origins: Origins
    rewards: Rewards
    clocks: tuple[Clock, ...]
    combat: Combat
    skills: tuple[Skill, ...] = ()
    titles: tuple[Title, ...] = ()
    evolutions: tuple[Evolution, ...] = ()

    def god_ids(self) -> tuple[str, ...]:
        return tuple(g.id for g in self.gods)

    def class_of(self, class_id: str | None) -> BaseClass | Evolution | None:
        """A base class or an evolved one, by id. The engine treats both the same after evolving."""
        return next((c for c in (*self.classes, *self.evolutions) if c.id == class_id), None)
