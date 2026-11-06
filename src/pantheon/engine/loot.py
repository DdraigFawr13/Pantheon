"""Rewards the engine sizes: XP by tier, XP for foes brought down, loot rolls, coin and items (ENG-09, D-046).

The narrator names the kind of a reward; every amount here comes from `world/data/rewards.yaml` and
`world/data/items.yaml`, and every roll from the `loot` stream (GAME-01).
"""

from __future__ import annotations

from typing import Any

from pantheon.engine.progression import gain_xp
from pantheon.engine.state import Foe, GameState, xp_to_next
from pantheon.engine.timeline import Rejected, Simulation
from pantheon.world.schemas import GameData

LEVELS_PER_TIER = 10


def _tier_xp(tier: int) -> int:
    first = (tier - 1) * LEVELS_PER_TIER + 1
    return sum(xp_to_next(level) for level in range(first, first + LEVELS_PER_TIER))


def tier_scale(tier: int, data: GameData) -> float:
    """How much larger rewards are at this tier, so each tier takes about `tier_time_growth` times the last.

    Tier 2 needs far more XP than Tier 1 (the canon curve); rewards grow by that ratio, divided by the growth
    in play time D-014 asks for.
    """
    if tier <= 1:
        return 1.0
    growth = data.rewards.tier_time_growth ** (tier - 1)
    return _tier_xp(tier) / _tier_xp(1) / growth


def scaled(amount: int, state: GameState, data: GameData) -> int:
    return round(amount * tier_scale(state.tier, data))


def foe_xp(state: GameState, data: GameData, foe: Foe) -> int:
    """XP for one foe brought down: more above the character's tier, very little below (power_tiers.md)."""
    table = data.rewards
    amount = scaled(table.foe_xp.get(foe.threat, 0), state, data)
    gap = foe.tier - state.tier
    if gap > 0:
        amount = amount * (100 + gap * table.foe_xp_above_percent) // 100
    for _ in range(-gap):
        amount = amount * table.foe_xp_below_percent // 100
    return amount


def foes_down_xp(sim: Simulation) -> None:
    """At a fight's end: XP for each foe brought down, outside the narrator's per-turn cap (D-046)."""
    state, data = sim.state, sim.rules.data
    if state.fight is None or state.level == 0:
        return
    down = [f for f in state.fight.foes if f.hits_left <= 0]
    amount = sum(foe_xp(state, data, f) for f in down)
    if amount:
        names = ", ".join(f.name for f in down)
        gain_xp(sim, amount, "foes", f"brought down {names}")


def roll_loot(sim: Simulation, table_name: str, source: str, affinity: str | None = None) -> dict[str, Any]:
    """Roll a loot table: each roll pays coin, an item or a shard fragment. Returns what it paid."""
    data = sim.rules.data
    table = data.rewards.loot.get(table_name)
    if table is None:
        raise Rejected(f"there is no loot table {table_name}")
    if affinity is not None and affinity not in data.affinities.basic:
        raise Rejected(f"affinity must be a basic affinity, not {affinity}")
    sim.emit("loot_granted", {"source": source})
    paid: dict[str, Any] = {"coin_cp": 0, "items": [], "fragments": []}
    total = sum(e.weight for e in table.entries)
    for _ in range(table.rolls):
        pick = sim.rng.roll("loot", total)
        entry = next(e for e in _running(table.entries) if pick <= e[0])[1]
        if entry.coin_cp is not None:
            low, high = entry.coin_cp
            amount = scaled(low + sim.rng.roll("loot", high - low + 1) - 1, sim.state, data)
            sim.emit("currency_changed", {"delta_cp": amount, "reason": source})
            paid["coin_cp"] += amount
        elif entry.item is not None:
            sim.emit("item_changed", {"item": entry.item, "quantity": 1, "reason": source})
            paid["items"].append(entry.item)
        else:
            target = affinity or sim.rng.choose_distinct("loot", tuple(data.affinities.basic), 1)[0]
            sim.emit(
                "shard_gained", {"kind": "affinity", "target": target, "rarity": "common", "fragment": True}
            )
            paid["fragments"].append(target)
    return paid


def _running(entries: tuple[Any, ...]) -> list[tuple[int, Any]]:
    running, out = 0, []
    for entry in entries:
        running += entry.weight
        out.append((running, entry))
    return out


def victory_loot(sim: Simulation) -> list[dict[str, Any]]:
    """After a won fight, each fallen foe's body is searched: one roll on its threat's table."""
    fight = sim.state.fight
    if fight is None:
        return []
    return [
        roll_loot(sim, f"foe:{f.threat}", f"{f.name}'s remains")
        for f in fight.foes
        if f.hits_left <= 0 and f"foe:{f.threat}" in sim.rules.data.rewards.loot
    ]


def format_cp(amount: int) -> str:
    """Copper as a player reads it: 1 gp 3 sp 4 cp."""
    gold, rest = divmod(amount, 240)
    silver, copper = divmod(rest, 12)
    parts = [f"{gold} gp" if gold else "", f"{silver} sp" if silver else "", f"{copper} cp" if copper else ""]
    return " ".join(p for p in parts if p) or "0 cp"
