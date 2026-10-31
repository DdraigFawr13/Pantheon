"""Fights in exchanges, pools and overspending, Downed, Last Breath and Reckonings (D-009, D-014, D-039)."""

import math
import re
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from pantheon.engine.checks import Outcome
from pantheon.engine.combat import downed_exchange, resolve_exchange
from pantheon.engine.commands import CharacterChoices, choose_class, choose_profession, create_character
from pantheon.engine.rng import RngStreams
from pantheon.engine.state import GameState, replay
from pantheon.engine.timeline import Rules, Simulation
from pantheon.engine.tools import apply_tool, attempt_trial, resolve_offer
from pantheon.world.loader import load_world
from pantheon.world.schemas import Skill

WORLD_DIR = Path(__file__).resolve().parents[2] / "world"
WORLD = load_world(WORLD_DIR)
assert WORLD.data is not None
DATA = WORLD.data
COMBAT = DATA.combat
RULES = Rules(DATA, {k: f.set_by for k, f in WORLD.flags.items()})
CHOICES = CharacterChoices(
    name="Wren",
    people="saltborn",
    origin="toll_ferry_orphan",
    age=20,
    flaw="Hoards small objects",
    debt="A name owed",
    stats={"vigor": 30, "agility": 27, "intellect": 24, "resolve": 20, "presence": 18},
)
HOUND = {"name": "Ash Hound", "tier": 1, "threat": "standard"}
RAT = {"name": "Rift Rat", "tier": 1, "threat": "minion"}
FIRE_BOLT = Skill(id="fire_bolt", name="Fire Bolt", rarity="common", pool="mana", cost=20, cooldown=2)


def sworn(rules: Rules = RULES, seed: int = 1) -> Simulation:
    sim = Simulation(GameState(), RngStreams.from_seed(seed), rules, 1)
    sim.emit("opening_gods_drawn", {"gods": ["drovash", "veshra"]})
    create_character(sim, CHOICES)
    resolve_offer(sim, "drovash")
    choose_class(sim, "wager_bound")
    choose_profession(sim, "merchant")
    return sim


def fighting(*foes: dict[str, Any], rules: Rules = RULES) -> Simulation:
    sim = sworn(rules)
    result = apply_tool(sim, "start_fight", {"foes": list(foes or [HOUND]), "reason": "they come"})
    assert result.accepted, result.reason
    return sim


def set_intents(sim: Simulation, intent: str) -> None:
    assert sim.state.fight is not None
    for foe in sim.state.fight.foes:
        foe.intent = intent


def percent_of_hp(sim: Simulation, percent: int) -> int:
    return math.ceil(sim.state.max_hp * percent / 100)


def intent_damage(intent_id: str) -> int:
    return next(i.damage_percent for i in COMBAT.intents if i.id == intent_id)


def test_combat_table_agrees_with_canon() -> None:
    text = (WORLD_DIR / "power_tiers.md").read_text(encoding="utf-8")
    assert f"by {COMBAT.pool_regen_percent} % of their maximum each combat exchange" in text
    assert f"up to {COMBAT.overspend_limit_percent} % of a pool's maximum below zero" in text
    assert f"the chance is {COMBAT.injury_chance_per_percent} % for each 1 %" in text
    assert re.search(r"three marks is death", text) and COMBAT.last_breath_marks == 3
    assert "The fourth death is final" in text and COMBAT.final_reckoning == 4


def test_start_fight_sets_foes_and_shows_an_intent_for_each() -> None:
    sim = fighting(HOUND, RAT)
    fight = sim.state.fight
    assert fight is not None
    assert fight.exchange == 1
    assert [(f.id, f.name, f.hits_left) for f in fight.foes] == [
        ("f1", "Ash Hound", 2),
        ("f2", "Rift Rat", 1),
    ]
    known = {i.id for i in COMBAT.intents}
    assert all(f.intent in known for f in fight.foes)


@pytest.mark.parametrize(
    "foes",
    [
        [],
        [HOUND] * (COMBAT.max_foes + 1),
        [{**HOUND, "threat": "nonsense"}],
        [{**HOUND, "tier": 1 + COMBAT.max_tier_above + 1}],
    ],
)
def test_eng02_start_fight_refuses_bad_foes_and_uses_no_dice(foes: list[dict[str, Any]]) -> None:
    sim = sworn()
    before = sim.rng.state()
    assert not apply_tool(sim, "start_fight", {"foes": foes, "reason": "x"}).accepted
    assert sim.state.fight is None
    assert sim.rng.state() == before


def test_eng02_only_one_fight_at_a_time() -> None:
    sim = fighting()
    assert not apply_tool(sim, "start_fight", {"foes": [RAT], "reason": "x"}).accepted


def test_a_success_hits_and_stops_that_foes_blow() -> None:
    sim = fighting()
    set_intents(sim, "strike")
    data = resolve_exchange(sim, "attack", "f1", Outcome.SUCCESS)
    assert sim.state.fight is not None
    assert sim.state.fight.foes[0].hits_left == 1
    assert sim.state.wounds == 0
    assert data["damage"] == 0


def test_a_triumph_lands_two_hits() -> None:
    sim = fighting(HOUND)
    set_intents(sim, "strike")
    resolve_exchange(sim, "attack", "f1", Outcome.TRIUMPH)
    assert sim.state.fight is None
    assert ("fight_ended", {"result": "victory"}) in sim.events


def test_success_at_a_cost_hits_but_the_blow_lands() -> None:
    sim = fighting()
    set_intents(sim, "heavy")
    resolve_exchange(sim, "attack", "f1", Outcome.SUCCESS_AT_COST)
    assert sim.state.fight is not None
    assert sim.state.fight.foes[0].hits_left == 1
    assert sim.state.wounds == percent_of_hp(sim, intent_damage("heavy"))


def test_a_failure_misses_and_the_blow_lands() -> None:
    sim = fighting()
    set_intents(sim, "strike")
    resolve_exchange(sim, "attack", "f1", Outcome.FAILURE)
    assert sim.state.fight is not None
    assert sim.state.fight.foes[0].hits_left == 2
    assert sim.state.wounds == percent_of_hp(sim, intent_damage("strike"))


def test_every_other_foes_intent_still_lands() -> None:
    sim = fighting(HOUND, HOUND)
    set_intents(sim, "strike")
    resolve_exchange(sim, "attack", "f1", Outcome.SUCCESS)
    assert sim.state.wounds == percent_of_hp(sim, intent_damage("strike"))


def test_a_guarding_foe_takes_one_hit_fewer_and_deals_nothing() -> None:
    sim = fighting()
    set_intents(sim, "guard")
    resolve_exchange(sim, "attack", "f1", Outcome.SUCCESS_AT_COST)
    assert sim.state.fight is not None
    assert sim.state.fight.foes[0].hits_left == 2
    assert sim.state.wounds == 0


@pytest.mark.parametrize(
    ("outcome", "block"),
    [(Outcome.TRIUMPH, 100), (Outcome.SUCCESS, 100), (Outcome.SUCCESS_AT_COST, 50), (Outcome.FAILURE, 0)],
)
def test_guarding_blocks_by_outcome(outcome: Outcome, block: int) -> None:
    sim = fighting(HOUND, HOUND)
    set_intents(sim, "heavy")
    resolve_exchange(sim, "guard", None, outcome)
    total = 2 * intent_damage("heavy")
    assert sim.state.wounds == percent_of_hp(sim, total * (100 - block) // 100)
    assert sim.state.fight is not None


@pytest.mark.parametrize(
    ("outcome", "escaped", "hurt"),
    [
        (Outcome.TRIUMPH, True, False),
        (Outcome.SUCCESS, True, False),
        (Outcome.SUCCESS_AT_COST, True, True),
        (Outcome.FAILURE, False, True),
    ],
)
def test_fleeing_by_outcome(outcome: Outcome, escaped: bool, hurt: bool) -> None:
    sim = fighting()
    set_intents(sim, "strike")
    resolve_exchange(sim, "flee", None, outcome)
    assert (sim.state.fight is None) == escaped
    assert (sim.state.wounds > 0) == hurt


def test_stronger_foes_hit_harder_and_weaker_ones_softer() -> None:
    gap = COMBAT.tier_gap_damage_percent
    strike = intent_damage("strike")
    for tier, percent in ((2, strike + gap), (0, strike - gap)):
        sim = fighting({**HOUND, "tier": tier})
        set_intents(sim, "strike")
        resolve_exchange(sim, "attack", "f1", Outcome.FAILURE)
        assert sim.state.wounds == percent_of_hp(sim, percent)


def test_new_intents_are_drawn_each_exchange_from_the_combat_stream_only() -> None:
    sim = fighting(HOUND, HOUND)
    checks, world = sim.rng.state()["checks"], sim.rng.state()["world"]
    combat = sim.rng.state()["combat"]
    resolve_exchange(sim, "guard", None, Outcome.SUCCESS)
    assert sim.state.fight is not None
    assert sim.state.fight.exchange == 2
    assert sim.rng.state()["checks"] == checks
    assert sim.rng.state()["world"] == world
    assert sim.rng.state()["combat"] != combat


def test_fight_move_rolls_with_difficulty_and_tier_set_by_the_engine() -> None:
    sim = fighting({**RAT, "tier": 2})
    args = {"move": "attack", "target": "f1", "stat": "agility", "difficulty": "heroic", "challenge_tier": 0}
    result = apply_tool(sim, "fight_move", args)
    assert result.accepted, result.reason
    check = next(p for t, p in sim.events if t == "check_resolved")
    assert check["difficulty"] == COMBAT.threats["minion"].difficulty
    assert check["challenge_tier"] == 2
    assert check["approach"] == "force"
    assert result.data["outcome"] == check["outcome"]
    assert result.data["summary"]


@pytest.mark.parametrize(
    "args",
    [
        {"move": "attack", "stat": "agility"},
        {"move": "attack", "target": "f9", "stat": "agility"},
        {"move": "dance", "stat": "agility"},
        {"move": "attack", "target": "f1", "stat": "agility", "skill": "fire_bolt"},
    ],
)
def test_eng02_a_bad_move_uses_no_dice(args: dict[str, Any]) -> None:
    sim = fighting()
    before = sim.rng.state()
    assert not apply_tool(sim, "fight_move", args).accepted
    assert sim.rng.state() == before


def test_eng02_a_move_needs_a_fight() -> None:
    assert not apply_tool(sworn(), "fight_move", {"move": "guard", "stat": "agility"}).accepted


def test_eng02_during_a_fight_other_rolls_and_damage_are_refused() -> None:
    sim = fighting()
    check = {"stat": "agility", "difficulty": "routine", "challenge_tier": 1}
    assert not apply_tool(sim, "request_check", check).accepted
    hazard = {"kind": "damage", "source": "hazard:fall", "reason": "x"}
    assert not apply_tool(sim, "apply_effect", hazard).accepted
    assert not apply_tool(sim, "advance_time", {"span": "rest", "reason": "x"}).accepted
    assert not apply_tool(sim, "advance_time", {"span": "days", "count": 2, "reason": "x"}).accepted
    assert apply_tool(sim, "advance_time", {"span": "minutes", "count": 2, "reason": "x"}).accepted
    rest = {"kind": "heal", "source": "rest", "reason": "x"}
    sim.state.wounds = 5
    assert not apply_tool(sim, "apply_effect", rest).accepted


def test_a_trial_cannot_start_in_a_fight() -> None:
    sim = fighting()
    sim.state.level, sim.state.xp = 10, 99999
    with pytest.raises(ValueError, match="fight"):
        attempt_trial(sim)


def test_end_fight_is_for_the_story_but_never_saves_the_downed() -> None:
    sim = fighting()
    assert apply_tool(sim, "end_fight", {"reason": "the hound bolts"}).accepted
    assert sim.state.fight is None
    assert not apply_tool(sim, "end_fight", {"reason": "again"}).accepted
    sim = fighting()
    sim.state.wounds, sim.state.downed = sim.state.max_hp, True
    assert not apply_tool(sim, "end_fight", {"reason": "mercy"}).accepted


def skill_rules() -> Rules:
    return replace(RULES, data=DATA.model_copy(update={"skills": (FIRE_BOLT,)}))


def with_skill(*foes: dict[str, Any]) -> Simulation:
    sim = fighting(*foes, rules=skill_rules())
    sim.emit("skill_gained", {"skill": "fire_bolt", "rank": 1, "rarity": "common"})
    return sim


def test_a_skill_costs_its_pool_and_then_cools_down() -> None:
    sim = with_skill()
    mana = sim.state.mana
    args = {"move": "guard", "stat": "intellect", "skill": "fire_bolt"}
    assert apply_tool(sim, "fight_move", args).accepted
    regen = math.ceil(sim.state.max_mana * COMBAT.pool_regen_percent / 100)
    assert sim.state.mana == mana - FIRE_BOLT.cost + regen
    assert sim.state.cooldowns["fire_bolt"] == FIRE_BOLT.cooldown
    assert not apply_tool(sim, "fight_move", args).accepted
    resolve_exchange(sim, "guard", None, Outcome.SUCCESS)
    assert not apply_tool(sim, "fight_move", args).accepted
    resolve_exchange(sim, "guard", None, Outcome.SUCCESS)
    assert apply_tool(sim, "fight_move", args).accepted


def test_cooldowns_count_down_by_exchange() -> None:
    sim = fighting()
    sim.emit("skill_spent", {"skill": "x", "pool": "mana", "cost": 0, "cooldown": 2})
    resolve_exchange(sim, "guard", None, Outcome.SUCCESS)
    assert sim.state.cooldowns == {"x": 1}
    resolve_exchange(sim, "guard", None, Outcome.SUCCESS)
    assert sim.state.cooldowns == {}


def test_regen_never_passes_the_pool_maximum() -> None:
    sim = fighting()
    resolve_exchange(sim, "guard", None, Outcome.SUCCESS)
    assert sim.state.mana == sim.state.max_mana
    assert sim.state.stamina == sim.state.max_stamina


def test_d009_overspending_needs_consent_and_stops_at_half_the_pool() -> None:
    sim = with_skill()
    args = {"move": "guard", "stat": "intellect", "skill": "fire_bolt"}
    sim.state.mana_spent = sim.state.max_mana
    before = sim.rng.state()
    assert not apply_tool(sim, "fight_move", args).accepted
    assert sim.rng.state() == before
    sim.state.mana_spent = sim.state.max_mana + sim.state.max_mana // 2
    assert not apply_tool(sim, "fight_move", {**args, "overspend": True}).accepted
    sim.state.mana_spent = sim.state.max_mana
    assert apply_tool(sim, "fight_move", {**args, "overspend": True}).accepted


def test_d009_overspending_rolls_for_injury_at_two_percent_per_percent() -> None:
    injured = 0
    runs = 200
    for seed in range(runs):
        sim = fighting(rules=skill_rules())
        sim.rng = RngStreams.from_seed(seed)
        sim.emit("skill_gained", {"skill": "fire_bolt", "rank": 1, "rarity": "common"})
        maximum = sim.state.max_mana  # An Injury may lower it during the move.
        over = maximum * 30 // 100
        sim.state.mana_spent = maximum + over - FIRE_BOLT.cost
        args = {"move": "guard", "stat": "intellect", "skill": "fire_bolt", "overspend": True}
        assert apply_tool(sim, "fight_move", args).accepted
        rolls = [p for t, p in sim.events if t == "overspend_rolled"]
        assert rolls[0]["chance"] == 2 * math.ceil(over * 100 / maximum)
        injured += any(t == "injury_gained" for t, _ in sim.events)
    assert 90 <= injured <= 150  # About 58 % of 200, with room for the seeds used.


def test_an_injury_never_leaves_more_wounds_than_hit_points() -> None:
    sim = sworn()
    sim.emit(
        "effect_applied", {"kind": "damage", "amount": sim.state.max_hp - 1, "source": "x", "reason": "x"}
    )
    sim.emit("injury_gained", {"stat": "vigor", "amount": 10, "reason": "x"})
    assert 0 <= sim.state.hp <= sim.state.max_hp


def test_rest_refills_the_pools() -> None:
    sim = sworn()
    sim.state.mana_spent, sim.state.stamina_spent = 5, 7
    assert apply_tool(sim, "advance_time", {"span": "rest", "reason": "slept"}).accepted
    assert sim.state.mana == sim.state.max_mana
    assert sim.state.stamina == sim.state.max_stamina


def downed(sim: Simulation) -> Simulation:
    set_intents(sim, "heavy")
    sim.emit("effect_applied", {"kind": "damage", "amount": sim.state.hp - 1, "source": "x", "reason": "x"})
    resolve_exchange(sim, "attack", "f1", Outcome.FAILURE)
    assert sim.state.downed
    return sim


def test_zero_hp_is_downed_and_no_mark_comes_from_that_exchange() -> None:
    sim = downed(fighting())
    assert sim.state.hp == 0
    assert sim.state.last_breath == 0
    assert not apply_tool(sim, "fight_move", {"move": "guard", "stat": "vigor"}).accepted


def test_each_hostile_exchange_while_downed_adds_a_mark() -> None:
    sim = downed(fighting())
    downed_exchange(sim)
    assert sim.state.last_breath == 1
    downed_exchange(sim)
    assert sim.state.last_breath == 2
    assert sim.state.fight is not None


def test_aid_lifts_a_downed_character_and_clears_the_marks() -> None:
    sim = downed(fighting())
    downed_exchange(sim)
    heal = {"kind": "heal", "source": "aid:a stranger", "reason": "dragged clear"}
    assert apply_tool(sim, "apply_effect", heal).accepted
    assert not sim.state.downed
    assert sim.state.last_breath == 0


def die(sim: Simulation) -> Simulation:
    """Take the character from fighting to their death in this fight."""
    sim = downed(sim)
    for _ in range(COMBAT.last_breath_marks):
        downed_exchange(sim)
    return sim


def test_first_reckoning_costs_the_current_levels_xp_and_returns_the_character() -> None:
    sim = fighting()
    sim.emit("xp_gained", {"amount": 40, "kind": "minor", "reason": "x"})
    die(sim)
    state = sim.state
    assert state.reckonings == 1
    assert state.xp == 0
    assert state.level == 1
    assert not state.dead
    assert state.fight is None
    assert not state.downed
    assert state.last_breath == 0
    assert state.hp == state.max_hp


def test_second_reckoning_is_also_xp_only_until_there_is_gear() -> None:
    sim = fighting()
    sim.state.reckonings = 1
    die(sim)
    assert sim.state.reckonings == 2
    assert sim.state.level == 1
    assert not sim.state.injuries


def test_third_reckoning_also_costs_a_level_and_an_injury() -> None:
    sim = fighting()
    sim.state.reckonings = 2
    sim.state.level = 3
    stats = dict(sim.state.stats)
    die(sim)
    assert sim.state.reckonings == 3
    assert sim.state.level == 2
    assert len(sim.state.injuries) == 1
    gains = DATA.rewards.level_gains
    lost = sum(stats.values()) - sum(sim.state.stats.values())
    assert lost == gains.primary + gains.secondary + sim.state.injuries[0].amount


def test_third_reckoning_never_goes_below_level_one() -> None:
    sim = fighting()
    sim.state.reckonings = 2
    die(sim)
    assert sim.state.level == 1
    assert len(sim.state.injuries) == 1


def test_the_fourth_death_is_final() -> None:
    sim = fighting()
    sim.state.reckonings = 3
    die(sim)
    assert sim.state.dead
    assert sim.state.reckonings == 3
    assert sim.state.fight is None


def test_permadeath_makes_the_first_death_final() -> None:
    sim = die(fighting(rules=replace(RULES, permadeath=True)))
    assert sim.state.dead
    assert sim.state.reckonings == 0


def test_eng06_a_whole_fight_replays_to_the_same_state() -> None:
    sim = die(fighting(HOUND, RAT))
    assert replay(sim.events).model_dump() == sim.state.model_dump()
    assert sim.state.reckonings == 1


def test_a_suggested_move_shows_real_odds_and_is_stored_to_roll_exactly_that() -> None:
    sim = fighting(RAT)
    args = {
        "actions": [
            {"label": "Go for the throat", "fight": {"move": "attack", "target": "f1", "stat": "agility"}},
            {"label": "Hold your guard", "fight": {"move": "guard", "stat": "vigor"}, "cost": "ground lost"},
            {"label": "Run for the stair", "fight": {"move": "flee", "stat": "agility"}},
        ]
    }
    result = apply_tool(sim, "suggest_actions", args)
    assert result.accepted, result.reason
    attack, guard, flee = sim.state.suggested
    assert attack.check is not None and guard.check is not None and flee.check is not None
    assert attack.tag == "agility"
    assert attack.check["move"] == "attack"
    assert attack.check["target"] == "f1"
    assert attack.check["difficulty"] == COMBAT.threats["minion"].difficulty
    assert guard.check["difficulty"] == COMBAT.guard_difficulty
    assert flee.check["difficulty"] == COMBAT.flee_difficulty
    assert apply_tool(sim, "fight_move", attack.check).accepted


def test_a_suggested_move_with_a_bad_target_is_refused() -> None:
    sim = fighting(RAT)
    args = {
        "actions": [
            {"label": "Strike", "fight": {"move": "attack", "target": "f9", "stat": "agility"}},
            {"label": "Hold", "fight": {"move": "guard", "stat": "vigor"}, "cost": "ground"},
            {"label": "Run", "fight": {"move": "flee", "stat": "agility"}},
        ]
    }
    assert not apply_tool(sim, "suggest_actions", args).accepted
