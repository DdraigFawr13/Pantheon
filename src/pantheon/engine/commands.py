"""Player commands: choices that go from the UI to the engine with no narrator (architecture section 6)."""

from __future__ import annotations

from pydantic import BaseModel

from pantheon.engine.progression import offer_skills
from pantheon.engine.state import STATS
from pantheon.engine.timeline import Rejected, Simulation


class CharacterChoices(BaseModel):
    name: str
    people: str
    origin: str
    age: int
    flaw: str
    debt: str
    stats: dict[str, int]
    people_stat: str | None = None
    innate_affinity: str | None = None


def innate_affinity_options(sim: Simulation, people_id: str) -> tuple[str, ...]:
    data = sim.rules.data
    people = next((p for p in data.peoples if p.id == people_id), None)
    if people is None:
        raise Rejected(f"unknown people: {people_id}")
    if people.innate_affinity[0] in ("any_basic", "birth_rift"):
        return data.affinities.basic
    return people.innate_affinity


def create_character(sim: Simulation, choices: CharacterChoices) -> None:
    """Build the character from `world/protagonist_seed.md` and offer the two drawn gods' Oaths."""
    data = sim.rules.data
    if sim.state.created:
        raise Rejected("the character already exists")
    if not choices.name.strip():
        raise Rejected("a character needs a name")
    if not 16 <= choices.age <= 30:
        raise Rejected("age must be 16 to 30")
    if set(choices.stats) != set(STATS) or sorted(choices.stats.values()) != sorted(data.origins.stat_array):
        raise Rejected(f"stats must assign {list(data.origins.stat_array)} across {list(STATS)}")
    options = innate_affinity_options(sim, choices.people)
    people = next(p for p in data.peoples if p.id == choices.people)
    origin = next((o for o in data.origins.origins if o.id == choices.origin), None)
    if origin is None:
        raise Rejected(f"unknown origin: {choices.origin}")
    people_stat = choices.people_stat if people.stat == "any" else people.stat
    if people_stat not in STATS:
        raise Rejected(f"{people.name} choose one stat for their +3")
    innate = choices.innate_affinity or (options[0] if len(options) == 1 else None)
    if innate not in options:
        raise Rejected(f"innate affinity must be one of {list(options)}")

    stats = dict(choices.stats)
    stats[people_stat] += 3
    stats[origin.stat] += 2
    sim.emit(
        "character_created",
        {
            "name": choices.name.strip(),
            "people": people.id,
            "origin": origin.id,
            "age": choices.age,
            "flaw": choices.flaw,
            "debt": choices.debt,
            "coin": data.origins.start_coin_silver,
            "stats": stats,
            "affinities": {innate: 1},
            "skills": {origin.skill: 1},
            "standing": dict(origin.standing),
        },
    )
    for description in (f"Debt: {choices.debt}", f"Complication: {origin.complication}"):
        sim.emit(
            "hook_registered",
            {
                "id": len(sim.state.hooks) + 1,
                "turn": sim.turn,
                "description": description,
                "due_condition": "when the story has room for it",
                "source_choice": "character creation",
            },
        )
    gods = {g.id: g for g in data.gods}
    for god_id in sim.state.opening_gods:
        sim.emit("oath_offered", {"god": god_id, "oath": gods[god_id].first_oath})


def choose_class(sim: Simulation, class_id: str) -> None:
    if not sim.state.needs_class:
        raise Rejected("no class choice is due")
    if class_id not in {c.id for c in sim.rules.data.classes}:
        raise Rejected(f"unknown class: {class_id}")
    sim.emit("class_chosen", {"class_id": class_id})
    offer_skills(sim)


def choose_profession(sim: Simulation, profession: str) -> None:
    if not sim.state.needs_profession:
        raise Rejected("no profession choice is due")
    if profession not in sim.rules.data.professions.all():
        raise Rejected(f"unknown profession: {profession}")
    sim.emit("profession_chosen", {"profession": profession})


def allocate_point(sim: Simulation, stat: str) -> None:
    if sim.state.free_points < 1:
        raise Rejected("no free points to place")
    if stat not in STATS:
        raise Rejected(f"unknown stat: {stat}")
    sim.emit("stat_point_allocated", {"stat": stat})
