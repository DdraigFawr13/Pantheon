"""Rewards the engine sizes (ENG-09, D-047): tier-scaled XP, foes brought down, loot, coin, items and gear."""

from pathlib import Path
from typing import Any

import pytest

from pantheon.engine.checks import Outcome
from pantheon.engine.combat import downed_exchange, resolve_exchange
from pantheon.engine.commands import CharacterChoices, choose_class, choose_profession, create_character
from pantheon.engine.loot import _tier_xp, foe_xp, format_cp, tier_scale
from pantheon.engine.rng import RngStreams
from pantheon.engine.state import Foe, GameState, replay
from pantheon.engine.timeline import Rejected, Rules, Simulation
from pantheon.engine.tools import apply_tool, check_preview, equip_item, resolve_offer, unequip_item, use_item
from pantheon.world.loader import CanonError, load_data, load_world

WORLD_DIR = Path(__file__).resolve().parents[2] / "world"
WORLD = load_world(WORLD_DIR)
assert WORLD.data is not None
DATA = WORLD.data
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
RAT = {"name": "Rift Rat", "tier": 1, "threat": "minion"}


def sworn(class_id: str = "warden", seed: int = 5) -> Simulation:
    sim = Simulation(GameState(), RngStreams.from_seed(seed), RULES, 1)
    sim.emit("opening_gods_drawn", {"gods": ["drovash", "veshra"]})
    create_character(sim, CHOICES)
    resolve_offer(sim, "drovash")
    choose_class(sim, class_id)
    choose_profession(sim, "merchant")
    return sim


def give(sim: Simulation, item: str, count: int = 1) -> None:
    sim.emit("item_changed", {"item": item, "quantity": count, "reason": "test"})


def passed_check(sim: Simulation) -> None:
    sim.checks["c0"] = Outcome.SUCCESS


def events(sim: Simulation, kind: str) -> list[dict[str, Any]]:
    return [p for t, p in sim.events if t == kind]


def test_eng09_rewards_grow_so_each_tier_takes_about_one_and_a_half_times_the_last() -> None:
    assert tier_scale(1, DATA) == 1.0
    for tier in (2, 3, 5):
        turns_this = _tier_xp(tier) / tier_scale(tier, DATA)
        turns_before = _tier_xp(tier - 1) / tier_scale(tier - 1, DATA)
        assert turns_this / turns_before == pytest.approx(DATA.rewards.tier_time_growth)


def test_eng09_grant_xp_is_scaled_by_tier() -> None:
    sim = sworn()
    assert apply_tool(sim, "grant_xp", {"kind": "minor", "reason": "a climb"}).accepted
    assert events(sim, "xp_gained")[-1]["amount"] == DATA.rewards.xp["minor"]


def test_eng09_foe_xp_is_more_above_the_characters_tier_and_very_little_below() -> None:
    state = sworn().state
    base = DATA.rewards.foe_xp["standard"]
    at = Foe(id="f1", name="Hound", tier=1, threat="standard", hits_left=0, intent="strike")
    assert foe_xp(state, DATA, at) == base
    assert foe_xp(state, DATA, at.model_copy(update={"tier": 2})) == base * 150 // 100
    assert foe_xp(state, DATA, at.model_copy(update={"tier": 0})) == base * 25 // 100


def test_eng09_a_won_fight_pays_xp_for_each_foe_and_searches_the_bodies() -> None:
    sim = sworn()
    assert apply_tool(sim, "start_fight", {"foes": [RAT], "reason": "it bites"}).accepted
    resolve_exchange(sim, "attack", "f1", Outcome.SUCCESS)
    assert sim.state.fight is None
    gained = events(sim, "xp_gained")[-1]
    assert gained["kind"] == "foes" and gained["amount"] == DATA.rewards.foe_xp["minion"]
    assert events(sim, "loot_granted")[-1]["source"] == "Rift Rat's remains"
    assert sim.state.level >= 1 and sim.state.xp + 100 * (sim.state.level - 1) >= 0


def test_eng09_fleeing_pays_for_foes_already_down_but_no_loot() -> None:
    sim = sworn()
    assert apply_tool(sim, "start_fight", {"foes": [RAT, RAT], "reason": "they bite"}).accepted
    resolve_exchange(sim, "attack", "f1", Outcome.SUCCESS)
    assert sim.state.fight is not None
    resolve_exchange(sim, "flee", None, Outcome.SUCCESS)
    assert sim.state.fight is None and not events(sim, "loot_granted")
    assert events(sim, "xp_gained")[-1]["amount"] == DATA.rewards.foe_xp["minion"]


def test_eng09_a_fight_ended_for_story_reasons_pays_for_foes_down() -> None:
    sim = sworn()
    assert apply_tool(sim, "start_fight", {"foes": [RAT, RAT], "reason": "they bite"}).accepted
    resolve_exchange(sim, "attack", "f1", Outcome.SUCCESS)
    assert apply_tool(sim, "end_fight", {"reason": "the other flees"}).accepted
    assert events(sim, "xp_gained")[-1]["kind"] == "foes"


def test_eng09_grant_loot_needs_a_paid_off_check_and_comes_once_a_turn() -> None:
    sim = sworn()
    args = {"source": "cache:a smuggler's tin", "reason": "under the boards"}
    assert not apply_tool(sim, "grant_loot", args).accepted
    sim.checks["c1"] = Outcome.FAILURE
    assert not apply_tool(sim, "grant_loot", args).accepted
    passed_check(sim)
    before = sim.rng.state()
    assert not apply_tool(sim, "grant_loot", {**args, "source": "rift_core:x"}).accepted
    assert not apply_tool(sim, "grant_loot", {**args, "affinity": "space"}).accepted
    assert sim.rng.state() == before  # A refused call uses no dice (D-022).
    result = apply_tool(sim, "grant_loot", {**args, "affinity": "flame"})
    assert result.accepted, result.reason
    assert not apply_tool(sim, "grant_loot", args).accepted


def test_eng09_loot_is_deterministic_for_a_seed() -> None:
    def run() -> list[Any]:
        sim = sworn(seed=9)
        passed_check(sim)
        apply_tool(sim, "grant_loot", {"source": "bounty:the Tallyhouse", "reason": "the rats"})
        return sim.events

    assert run() == run()


def test_a_bounty_pays_five_to_thirty_silver_at_tier_one() -> None:
    for seed in range(20):
        sim = sworn(seed=seed)
        passed_check(sim)
        apply_tool(sim, "grant_loot", {"source": "bounty:the Tallyhouse", "reason": "the rats"})
        paid = events(sim, "currency_changed")[-1]["delta_cp"]
        assert 60 <= paid <= 360


def test_loot_fragments_take_the_places_affinity_or_a_drawn_basic_one() -> None:
    for seed in range(40):
        sim = sworn(seed=seed)
        passed_check(sim)
        apply_tool(sim, "grant_loot", {"source": "cache:ash", "affinity": "flame", "reason": "x"})
        for shard in events(sim, "shard_gained"):
            assert shard["fragment"] and shard["target"] == "flame"


def test_eng09_adjust_inventory_bounds() -> None:
    sim = sworn()
    assert not apply_tool(
        sim, "adjust_inventory", {"item": "moonblade", "quantity": 1, "reason": "x"}
    ).accepted
    assert not apply_tool(sim, "adjust_inventory", {"item": "rope", "quantity": 0, "reason": "x"}).accepted
    assert not apply_tool(sim, "adjust_inventory", {"item": "rope", "quantity": -1, "reason": "x"}).accepted
    assert apply_tool(sim, "adjust_inventory", {"item": "rope", "quantity": 2, "reason": "bought"}).accepted
    limit = DATA.rewards.items_per_turn
    assert not apply_tool(
        sim, "adjust_inventory", {"item": "dagger", "quantity": limit, "reason": "x"}
    ).accepted
    assert apply_tool(sim, "adjust_inventory", {"item": "rope", "quantity": -1, "reason": "lost"}).accepted
    assert sim.state.inventory == {"rope": 1}


def test_eng09_adjust_currency_bounds() -> None:
    sim = sworn()
    purse = sim.state.purse_cp
    assert not apply_tool(sim, "adjust_currency", {"amount_cp": -(purse + 1), "reason": "x"}).accepted
    assert not apply_tool(sim, "adjust_currency", {"amount_cp": 0, "reason": "x"}).accepted
    assert apply_tool(sim, "adjust_currency", {"amount_cp": -7, "reason": "a meal and ale"}).accepted
    assert sim.state.purse_cp == purse - 7
    bound = DATA.rewards.coin_gain_cp_per_turn
    assert apply_tool(sim, "adjust_currency", {"amount_cp": bound, "reason": "wages"}).accepted
    assert not apply_tool(sim, "adjust_currency", {"amount_cp": 1, "reason": "more"}).accepted


def test_coin_folds_copper_into_silver() -> None:
    sim = sworn()
    sim.emit("currency_changed", {"delta_cp": 13, "reason": "x"})
    start = DATA.origins.start_coin_silver
    assert (sim.state.coin, sim.state.coin_cp) == (start + 1, 1)
    sim.emit("currency_changed", {"delta_cp": -2, "reason": "x"})
    assert (sim.state.coin, sim.state.coin_cp) == (start, 11)
    assert replay(sim.events).purse_cp == sim.state.purse_cp
    assert format_cp(253) == "1 gp 1 sp 1 cp" and format_cp(0) == "0 cp"


def test_a_weapon_adds_to_attacks_and_armour_softens_blows() -> None:
    sim = sworn()
    give(sim, "sword")
    give(sim, "chain_shirt")
    assert apply_tool(sim, "start_fight", {"foes": [RAT], "reason": "x"}).accepted
    attack = {"move": "attack", "stat": "vigor", "target": "f1", "difficulty": "routine", "challenge_tier": 1}
    bare = check_preview(sim.state, DATA, attack).chance
    with pytest.raises(Rejected):
        equip_item(sim, "sword")  # No changing gear in a fight.
    sim.state.fight = None
    equip_item(sim, "sword")
    equip_item(sim, "chain_shirt")
    with pytest.raises(Rejected):
        equip_item(sim, "sword")
    with pytest.raises(Rejected):
        equip_item(sim, "rope")
    assert apply_tool(sim, "start_fight", {"foes": [RAT], "reason": "x"}).accepted
    armed = check_preview(sim.state, DATA, attack).chance
    assert bare is not None and armed == bare + 10
    assert sim.state.fight is not None
    sim.state.fight.foes[0].intent = "strike"
    resolve_exchange(sim, "guard", None, Outcome.FAILURE)
    struck = events(sim, "effect_applied")[-1]["amount"]
    assert struck == -(-sim.state.max_hp * 10 // 100)  # A plain strike is 15 %, the shirt takes 5 off.


def test_still_centre_needs_the_character_unarmoured() -> None:
    sim = sworn("fistsworn")
    give(sim, "chain_shirt")
    equip_item(sim, "chain_shirt")
    assert apply_tool(sim, "start_fight", {"foes": [RAT], "reason": "x"}).accepted
    guard = {"move": "guard", "stat": "presence", "difficulty": "routine", "challenge_tier": 1}
    armoured = check_preview(sim.state, DATA, guard).chance
    sim.state.equipped = {}
    assert check_preview(sim.state, DATA, guard).chance != armoured


def test_unequip_takes_a_slot_off() -> None:
    sim = sworn()
    give(sim, "dagger")
    equip_item(sim, "dagger")
    unequip_item(sim, "weapon")
    assert sim.state.equipped == {}
    with pytest.raises(Rejected):
        unequip_item(sim, "weapon")


def test_a_tonic_heals_outside_a_fight_and_is_the_whole_exchange_inside_one() -> None:
    sim = sworn()
    give(sim, "healing_tonic", 2)
    with pytest.raises(Rejected):
        use_item(sim, "healing_tonic")  # No wounds.
    sim.state.wounds = 30
    use_item(sim, "healing_tonic")
    assert sim.state.inventory == {"healing_tonic": 1}
    assert sim.state.wounds == 30 - -(-sim.state.max_hp * 25 // 100)
    assert apply_tool(sim, "start_fight", {"foes": [RAT], "reason": "x"}).accepted
    with pytest.raises(Rejected):
        use_item(sim, "healing_tonic")
    rolls = len(events(sim, "check_resolved"))
    result = apply_tool(sim, "fight_move", {"move": "item", "stat": "vigor", "item": "healing_tonic"})
    assert result.accepted, result.reason
    assert len(events(sim, "check_resolved")) == rolls and not sim.state.inventory
    assert not apply_tool(sim, "fight_move", {"move": "item", "stat": "vigor", "item": "dagger"}).accepted


def test_an_item_move_in_the_options_carries_no_odds() -> None:
    sim = sworn()
    give(sim, "healing_tonic")
    assert apply_tool(sim, "start_fight", {"foes": [RAT], "reason": "x"}).accepted
    actions = [
        {"label": "Drink the tonic", "fight": {"move": "item", "stat": "vigor", "item": "healing_tonic"}},
        {"label": "Strike", "cost": "it bites", "fight": {"move": "attack", "stat": "vigor", "target": "f1"}},
        {"label": "Shout for help"},
    ]
    assert apply_tool(sim, "suggest_actions", {"actions": actions}).accepted
    assert sim.state.suggested[0].check is None and sim.state.suggested[1].check is not None


def test_the_second_reckoning_takes_carried_gear_but_not_what_is_worn() -> None:
    sim = sworn()
    give(sim, "sword", 2)
    give(sim, "rope")
    equip_item(sim, "sword")
    sim.state.reckonings = 1
    assert apply_tool(sim, "start_fight", {"foes": [RAT], "reason": "x"}).accepted
    sim.state.wounds, sim.state.downed = sim.state.max_hp, True
    for _ in range(DATA.combat.last_breath_marks):
        downed_exchange(sim)
    assert sim.state.reckonings == 2 and sim.state.inventory == {"sword": 1}


def test_the_loader_refuses_a_loot_table_naming_an_unknown_item(tmp_path: Path) -> None:
    for source in (WORLD_DIR / "data").iterdir():
        (tmp_path / source.name).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    rewards = tmp_path / "rewards.yaml"
    rewards.write_text(rewards.read_text(encoding="utf-8").replace("item: rope", "item: moonblade"), "utf-8")
    with pytest.raises(CanonError, match="moonblade"):
        load_data(tmp_path)
