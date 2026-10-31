"""Skills, caps, shards, titles and evolution (ENG-07, `world/power_tiers.md`; assumptions in D-037).

Each command validates first, then emits events. A refusal changes nothing and uses no randomness (D-022).
"""

from __future__ import annotations

from pantheon.engine.state import GameState
from pantheon.engine.timeline import Rejected, Simulation
from pantheon.world.schemas import Evolution, GameData, Skill

RARITIES = ("common", "uncommon", "rare", "epic", "legendary", "mythic", "divine")
_MIN_TIER_FOR_RARITY = {"mythic": 6, "divine": 8}
_SKILL_CAP_BY_TIER = {0: 1, 1: 2, 2: 3, 3: 4}
MAX_SKILL_RANK = 5
_UNWRITTEN_AFFINITY_CAP = 3
_OFFER_SIZE = 3
_OFFER_LEVELS = {1, 3, 5, 7, 9}
_DEFAULT_FRAGMENTS = 3
_EVOLUTION_BONUS = 5


def affinity_cap(state: GameState) -> int:
    return _UNWRITTEN_AFFINITY_CAP if state.level == 0 else state.tier + 1


def skill_rank_cap(state: GameState, affinity: str | None) -> int:
    """Capped by tier, and by the affinity's rank for a skill that has one (D-013 for the Unwritten)."""
    if state.level == 0:
        cap = max(1, max(state.affinities.values(), default=1))
    else:
        cap = _SKILL_CAP_BY_TIER.get(state.tier, MAX_SKILL_RANK)
    return cap if affinity is None else min(cap, state.affinities.get(affinity, 0))


def _skill(data: GameData, skill_id: str) -> Skill:
    skill = next((s for s in data.skills if s.id == skill_id), None)
    if skill is None:
        raise Rejected(f"unknown skill: {skill_id}")
    return skill


def offer_skills(sim: Simulation) -> None:
    """The class offers 3 skills at levels 1, 3, 5, 7 and 9 of a tier. No content: no offer, no roll."""
    state = sim.state
    if state.level % 10 not in _OFFER_LEVELS or state.class_id is None:
        return
    pool = [
        s.id
        for s in sim.rules.data.skills
        if state.class_id in s.classes
        and s.id not in state.skills
        and (s.affinity is None or state.affinities.get(s.affinity, 0) >= 1)
    ]
    if pool:
        options = sim.rng.choose_distinct("world", tuple(sorted(pool)), min(_OFFER_SIZE, len(pool)))
        sim.emit("skill_offered", {"level": state.level, "options": list(options)})


def pick_skill(sim: Simulation, skill_id: str) -> None:
    if not sim.state.skill_offers or skill_id not in sim.state.skill_offers[0]:
        raise Rejected(f"{skill_id} is not on offer")
    skill = _skill(sim.rules.data, skill_id)
    sim.emit("skill_gained", {"skill": skill.id, "rank": 1, "rarity": skill.rarity, "from_offer": True})


def _absorb_affinity(sim: Simulation, target: str) -> None:
    rank = sim.state.affinities.get(target, 0)
    if rank >= affinity_cap(sim.state):
        raise Rejected(f"{target} is at its cap of {affinity_cap(sim.state)}")
    sim.emit("affinity_raised", {"affinity": target, "rank": rank + 1})


def _absorb_skill(sim: Simulation, target: str, rarity: str) -> None:
    state = sim.state
    skill = _skill(sim.rules.data, target)
    if skill.affinity is not None and state.affinities.get(skill.affinity, 0) < 1:
        raise Rejected(f"this needs rank 1 in the affinity {skill.affinity}")
    rank = state.skills.get(target)
    if rank is None:
        sim.emit("skill_gained", {"skill": target, "rank": 1, "rarity": rarity})
        return
    if state.skill_rarity.get(target, skill.rarity) != rarity:
        raise Rejected("the shard's rarity does not match the skill")
    if rank >= MAX_SKILL_RANK:
        next_rarity = RARITIES[RARITIES.index(rarity) + 1] if rarity != RARITIES[-1] else None
        if next_rarity is None:
            raise Rejected(f"{target} cannot evolve further")
        if state.tier < _MIN_TIER_FOR_RARITY.get(next_rarity, 0):
            raise Rejected(f"{next_rarity} needs Tier {_MIN_TIER_FOR_RARITY[next_rarity]}")
        sim.emit("skill_gained", {"skill": target, "rank": 1, "rarity": next_rarity})
        return
    if rank >= skill_rank_cap(state, skill.affinity):
        raise Rejected(f"{target} is at its cap of {skill_rank_cap(state, skill.affinity)}")
    sim.emit("skill_gained", {"skill": target, "rank": rank + 1, "rarity": rarity})


def absorb_shard(sim: Simulation, index: int) -> None:
    """Absorb one held shard by its place in the list. The Unwritten can do this too."""
    shards = sim.state.shards
    if not 0 <= index < len(shards):
        raise Rejected("there is no such shard")
    shard = shards[index]
    if shard.fragment:
        raise Rejected("a fragment must be fused before it can be absorbed")
    if shard.kind == "affinity":
        _absorb_affinity(sim, shard.target)
    else:
        _absorb_skill(sim, shard.target, shard.rarity)
    sim.emit("shard_used", {"index": index})


def fuse_fragments(sim: Simulation, kind: str, target: str) -> None:
    state = sim.state
    current = sim.rules.data.class_of(state.class_id)
    needed = current.fragments_to_fuse if current else _DEFAULT_FRAGMENTS
    matches = [i for i, s in enumerate(state.shards) if s.fragment and s.kind == kind and s.target == target]
    if len(matches) < needed:
        raise Rejected(f"fusing takes {needed} fragments of a kind")
    rarity = state.shards[matches[0]].rarity
    for index in reversed(matches[:needed]):  # From the end, so earlier places stay valid.
        sim.emit("shard_used", {"index": index})
    sim.emit("shard_gained", {"kind": kind, "target": target, "rarity": rarity, "fragment": False})


def grant_title(sim: Simulation, title_id: str, witness: str) -> None:
    title = next((t for t in sim.rules.data.titles if t.id == title_id), None)
    if title is None:
        raise Rejected(f"unknown title: {title_id}")
    if title_id in sim.state.titles:
        raise Rejected(f"{title.name} is already earned")
    if title.needs_witness and witness == "none":
        raise Rejected(f"{title.name} needs a witness")
    sim.emit("title_earned", {"title": title.id, "stat": title.stat, "bonus": title.stat_bonus})


def _unlocked(evolution: Evolution, state: GameState) -> bool:
    return (
        all(state.affinities.get(a, 0) >= rank for a, rank in evolution.needs_affinity.items())
        and all(state.stats.get(s, 0) >= value for s, value in evolution.needs_stat.items())
        and (evolution.needs_oath is None or evolution.needs_oath in state.oaths)
        and (evolution.needs_skill is None or evolution.needs_skill in state.skills)
        and (evolution.needs_title is None or evolution.needs_title in state.titles)
    )


def evolution_options(state: GameState, data: GameData) -> list[Evolution]:
    return [e for e in data.evolutions if e.from_class == state.class_id and _unlocked(e, state)]


def choose_evolution(sim: Simulation, evolution_id: str) -> None:
    options = evolution_options(sim.state, sim.rules.data)
    chosen = next((e for e in options if e.id == evolution_id), None)
    if not sim.state.needs_evolution or chosen is None:
        raise Rejected(f"{evolution_id} is not an option right now")
    sim.emit("class_evolved", {"class_id": chosen.id, "stat": chosen.primary, "bonus": _EVOLUTION_BONUS})
