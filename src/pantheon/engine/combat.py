"""Fights in exchanges, Downed, Last Breath and Reckonings (`world/power_tiers.md`; assumptions in D-039).

Each exchange the player moves, the engine rolls, and the foes' shown intents land. Every number is engine
data; the narrator only describes the result (ENG-01, GAME-03).
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from typing import Any

from pantheon.engine.checks import Outcome
from pantheon.engine.state import STATS, Fight, Foe
from pantheon.engine.timeline import Rejected, Simulation
from pantheon.world.schemas import GameData

_INJURY_AMOUNT = 10
_LANDED = {Outcome.SUCCESS_AT_COST, Outcome.FAILURE}


def _draw_intent(sim: Simulation) -> str:
    intents = sim.rules.data.combat.intents
    roll = sim.rng.roll("combat", sum(i.weight for i in intents))
    for intent in intents:
        roll -= intent.weight
        if roll <= 0:
            return intent.id
    raise AssertionError("weights add up to the roll's range")  # pragma: no cover


def intent_label(data: GameData, intent_id: str) -> str:
    return next(i.label for i in data.combat.intents if i.id == intent_id)


def start_fight(sim: Simulation, foes: Iterable[tuple[str, int, str]]) -> dict[str, Any]:
    state, table = sim.state, sim.rules.data.combat
    listed = list(foes)
    if state.fight is not None:
        raise Rejected("a fight is already on")
    if not 1 <= len(listed) <= table.max_foes:
        raise Rejected(f"a fight has 1 to {table.max_foes} foes")
    for name, tier, threat in listed:
        if threat not in table.threats:
            raise Rejected(f"threat must be one of {sorted(table.threats)}")
        if tier > state.tier + table.max_tier_above:
            raise Rejected(f"{name} is too far above this character's tier to fight in exchanges")
    drawn = [
        {
            "id": f"f{number}",
            "name": name,
            "tier": tier,
            "threat": threat,
            "hits_left": table.threats[threat].hits,
            "intent": _draw_intent(sim),
        }
        for number, (name, tier, threat) in enumerate(listed, 1)
    ]
    sim.emit("fight_started", {"foes": drawn})
    return {"foes": len(drawn)}


def foe_of(fight: Fight, target: str | None) -> Foe:
    foe = next((f for f in fight.standing if f.id == target), None)
    if foe is None:
        raise Rejected(f"target must be one of {[f.id for f in fight.standing]}")
    return foe


def move_terms(sim: Simulation, move: str, target: str | None) -> tuple[str, int]:
    """The difficulty and challenge tier of a move. The engine sets both, never the narrator (ENG-02)."""
    fight, table = sim.state.fight, sim.rules.data.combat
    if fight is None:
        raise Rejected("there is no fight")
    if move == "attack":
        foe = foe_of(fight, target)
        return table.threats[foe.threat].difficulty, foe.tier
    highest = max(f.tier for f in fight.standing)
    return (table.guard_difficulty if move == "guard" else table.flee_difficulty), highest


def _blow_percent(sim: Simulation, foe: Foe) -> int:
    table = sim.rules.data.combat
    intent = next(i for i in table.intents if i.id == foe.intent)
    if intent.damage_percent == 0:
        return 0
    gap = foe.tier - sim.state.tier
    return max(table.tier_gap_damage_percent, intent.damage_percent + gap * table.tier_gap_damage_percent)


def _hurt(sim: Simulation, percent: int, reason: str) -> int:
    state = sim.state
    amount = min(math.ceil(state.max_hp * percent / 100), state.hp)
    if amount:
        sim.emit(
            "effect_applied", {"kind": "damage", "amount": amount, "source": "exchange", "reason": reason}
        )
    if amount and state.hp == 0:
        sim.emit("downed", {"reason": reason})
    return amount


def _regen(spent: int, maximum: int, percent: int) -> int:
    return min(spent, math.ceil(maximum * percent / 100))


def _end_exchange(sim: Simulation, ended: str | None) -> None:
    state = sim.state
    table = sim.rules.data.combat
    assert state.fight is not None
    result = ended or ("victory" if not state.fight.standing else None)
    intents = {} if result else {f.id: _draw_intent(sim) for f in state.fight.standing}
    sim.emit(
        "exchange_ended",
        {
            "mana_regen": _regen(state.mana_spent, state.max_mana, table.pool_regen_percent),
            "stamina_regen": _regen(state.stamina_spent, state.max_stamina, table.pool_regen_percent),
            "intents": intents,
        },
    )
    if result:
        sim.emit("fight_ended", {"result": result})


def _next_intents(sim: Simulation) -> str:
    fight = sim.state.fight
    if fight is None:
        return "The fight is over."
    data = sim.rules.data
    shown = "; ".join(f"{f.name} now shows {intent_label(data, f.intent)}" for f in fight.standing)
    return f"{shown}. Show this at the end of the scene."


def resolve_exchange(sim: Simulation, move: str, target: str | None, outcome: Outcome) -> dict[str, Any]:
    """Apply one exchange after its check has rolled: the player's move, then the foes' intents."""
    state, table = sim.state, sim.rules.data.combat
    assert state.fight is not None
    acting = list(state.fight.standing)
    words, hits, left = [], 0, 0
    block = 0
    ended = None
    if move == "attack":
        foe = foe_of(state.fight, target)
        hits = table.attack_hits[outcome.value]
        if next(i for i in table.intents if i.id == foe.intent).guards:
            hits = max(0, hits - 1)
        hits = min(hits, foe.hits_left)
        if hits:
            sim.emit("foe_hit", {"foe": foe.id, "name": foe.name, "hits": hits})
        left = foe.hits_left
        words.append(f"{foe.name} takes {hits} hit and has {left} left." if left else f"{foe.name} is down.")
        if outcome not in _LANDED:
            acting = [f for f in acting if f.id != foe.id]
    else:
        block = table.block_percent[outcome.value]
        if move == "flee" and outcome is not Outcome.FAILURE:
            ended = "fled"
            words.append("The character gets away.")
        elif move == "guard":
            words.append(f"The guard stops {block} percent of what comes.")
        else:
            words.append("The escape fails.")
    percent = sum(_blow_percent(sim, f) for f in acting) * (100 - block) // 100
    damage = _hurt(sim, percent, "blows in the exchange")
    if damage:
        words.append(f"Blows land for {damage} HP, leaving {state.hp}.")
    else:
        words.append("No blow lands.")
    _end_exchange(sim, ended)
    if state.downed:
        words.append("The character falls Downed.")
    words.append(_next_intents(sim))
    return {
        "hits": hits,
        "foe_hits_left": left,
        "block_percent": block,
        "damage": damage,
        "hp": state.hp,
        "max_hp": state.max_hp,
        "fight_over": state.fight is None,
        "summary": " ".join(words),
    }


def injure(sim: Simulation, reason: str) -> None:
    state = sim.state
    stat = sim.rng.choose_distinct("combat", STATS, 1)[0]
    amount = min(_INJURY_AMOUNT, state.stats[stat])
    sim.emit("injury_gained", {"stat": stat, "amount": amount, "reason": reason})


def _die(sim: Simulation) -> None:
    state, table = sim.state, sim.rules.data.combat
    count = state.reckonings + 1
    if sim.rules.permadeath or count >= table.final_reckoning:
        sim.emit("died", {"reckonings": state.reckonings})
        if state.fight is not None:
            sim.emit("fight_ended", {"result": "death"})
        return
    if state.xp:
        sim.emit("xp_lost", {"amount": state.xp, "reason": f"Reckoning {count}"})
    if count >= 3:
        if state.level > 1:
            cls = sim.rules.data.class_of(state.class_id)
            gains = sim.rules.data.rewards.level_gains
            wanted = {cls.primary: gains.primary, cls.secondary: gains.secondary} if cls else {}
            losses = {s: min(amount, state.stats[s]) for s, amount in wanted.items()}
            sim.emit("level_lost", {"level": state.level - 1, "losses": losses})
        injure(sim, f"Reckoning {count}")
    sim.emit("reckoning", {"count": count})
    if state.fight is not None:
        sim.emit("fight_ended", {"result": "reckoning"})


def downed_exchange(sim: Simulation) -> dict[str, Any]:
    """A hostile exchange while Downed: the player cannot act, and a Last Breath mark is added."""
    state, table = sim.state, sim.rules.data.combat
    marks = state.last_breath + 1
    sim.emit("last_breath", {"marks": marks})
    if marks < table.last_breath_marks:
        _end_exchange(sim, None)
        return {
            "marks": marks,
            "summary": f"The character lies Downed as the foes press on: Last Breath {marks}. "
            + _next_intents(sim),
        }
    count = state.reckonings + 1
    _die(sim)
    if state.dead:
        return {"marks": marks, "summary": "Three Last Breaths: the character dies, and this death is final."}
    return {
        "marks": marks,
        "reckoning": count,
        "summary": "Three Last Breaths: the character dies, and wakes at the last shrine, alive and whole. "
        "Their Ledger shows what the Reckoning took. The fight is over.",
    }
