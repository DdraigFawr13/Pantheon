"""Class traits that run in fights (D-043): each bonus shows in the odds and is the one the roll uses."""

from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from pantheon.engine.checks import Outcome
from pantheon.engine.combat import resolve_exchange
from pantheon.engine.commands import (
    CharacterChoices,
    choose_attunement,
    choose_class,
    choose_profession,
    create_character,
)
from pantheon.engine.rng import RngStreams
from pantheon.engine.state import GameState, replay
from pantheon.engine.timeline import Rejected, Rules, Simulation
from pantheon.engine.tools import apply_tool, check_preview, resolve_offer
from pantheon.engine.traits import needs_attunement, skill_cost, trait_of
from pantheon.world.loader import load_world
from pantheon.world.schemas import Evolution, Skill

WORLD = load_world(Path(__file__).resolve().parents[2] / "world")
assert WORLD.data is not None
DATA = WORLD.data
STORM_BOLT = Skill(
    id="storm_bolt", name="Storm Bolt", rarity="common", affinity="storm", pool="mana", cost=20
)
FIRE_BOLT = Skill(id="fire_bolt", name="Fire Bolt", rarity="common", affinity="flame", pool="mana", cost=20)
KICK = Skill(id="kick", name="Kick", rarity="common", pool="stamina", cost=10)
RULES = replace(
    Rules(DATA, {k: f.set_by for k, f in WORLD.flags.items()}),
    data=DATA.model_copy(update={"skills": (STORM_BOLT, FIRE_BOLT, KICK)}),
)
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
ATTACK = {"move": "attack", "stat": "vigor", "target": "f1"}


def of_class(class_id: str, *skills: str) -> Simulation:
    sim = Simulation(GameState(), RngStreams.from_seed(3), RULES, 1)
    sim.emit("opening_gods_drawn", {"gods": ["drovash", "veshra"]})
    create_character(sim, CHOICES)
    resolve_offer(sim, "drovash")
    choose_class(sim, class_id)
    choose_profession(sim, "merchant")
    for skill in skills:
        sim.emit("skill_gained", {"skill": skill, "rank": 1, "rarity": "common"})
    return sim


def fight(sim: Simulation, **extra: Any) -> Simulation:
    result = apply_tool(sim, "start_fight", {"foes": [HOUND, HOUND], "reason": "they come", **extra})
    assert result.accepted, result.reason
    return sim


def steady(sim: Simulation, hits: int | None = None) -> Simulation:
    """Every foe shows a plain strike, so no guarding foe shaves a hit; optionally lasts many hits."""
    assert sim.state.fight is not None
    for foe in sim.state.fight.foes:
        foe.intent = "strike"
        foe.hits_left = hits or foe.hits_left
    return sim


def chance(sim: Simulation, check: dict[str, Any]) -> int:
    odds = check_preview(sim.state, sim.rules.data, {**check, "difficulty": "routine", "challenge_tier": 1})
    assert odds.chance is not None
    return odds.chance


def without_trait(sim: Simulation, check: dict[str, Any]) -> int:
    """The same check for a class whose trait does not run in fights (Warden's Bulwark needs allies)."""
    plain = fight(of_class("warden", *sim.state.skills))
    plain.state.fight = sim.state.fight.model_copy(deep=True) if sim.state.fight else None
    plain.state.wounds = sim.state.wounds
    return chance(plain, check)


def test_only_the_nine_solo_fight_traits_run() -> None:
    assert set(DATA.combat.traits) == {
        "sellsword",
        "reaver",
        "fistsworn",
        "cutpurse",
        "inquisitor",
        "elementalist",
        "wildblood",
        "hexer",
        "skinchanger",
    }
    names = {c.id: c.trait.split(":")[0] for c in DATA.classes}
    assert all(names[k] == t.name for k, t in DATA.combat.traits.items())


def test_momentum_builds_on_clean_attacks_to_its_cap_and_resets_on_a_miss() -> None:
    sim = steady(fight(of_class("sellsword")), hits=99)
    for expected in (5, 10, 15, 15):
        sim.state.wounds = 0
        resolve_exchange(sim, "attack", "f1", Outcome.SUCCESS)
        assert sim.state.fight is not None and sim.state.fight.momentum == expected
        steady(sim)
    sim.state.wounds = 0
    resolve_exchange(sim, "attack", "f1", Outcome.SUCCESS_AT_COST)
    assert sim.state.fight is not None and sim.state.fight.momentum == 0


def test_momentum_shows_in_the_odds_of_the_next_attack() -> None:
    sim = fight(of_class("sellsword"))
    base = chance(sim, ATTACK)
    assert sim.state.fight is not None
    sim.state.fight.momentum = 10
    assert chance(sim, ATTACK) == base + 10
    assert chance(sim, {"move": "guard", "stat": "vigor"}) == without_trait(
        sim, {"move": "guard", "stat": "vigor"}
    )


def test_blood_up_below_half_hp() -> None:
    sim = fight(of_class("reaver"))
    attack, guard = chance(sim, ATTACK), chance(sim, {"move": "guard", "stat": "vigor"})
    sim.state.wounds = sim.state.max_hp // 2 + 1
    assert chance(sim, ATTACK) == attack + 10
    assert chance(sim, {"move": "guard", "stat": "vigor"}) == guard - 10


def test_still_centre_guards_with_the_better_of_agility_and_resolve_and_saves_stamina() -> None:
    sim = fight(of_class("fistsworn", "kick"))
    guard = {"move": "guard", "stat": "presence"}
    assert chance(sim, guard) == chance(sim, {"move": "guard", "stat": "agility"})
    assert skill_cost(sim.state, DATA.model_copy(update={"skills": (KICK,)}), KICK) == 8
    assert skill_cost(sim.state, sim.rules.data, STORM_BOLT) == 20  # Mana is not discounted.


def test_opening_doubles_the_first_unseen_strike_only() -> None:
    sim = steady(fight(of_class("cutpurse"), ambush=True))
    plain = without_trait(sim, ATTACK)
    assert chance(sim, ATTACK) == plain + 10
    result = resolve_exchange(sim, "attack", "f1", Outcome.SUCCESS)
    assert result["hits"] == 2  # One hit doubled, and a standard foe has two.
    assert sim.state.fight is not None and sim.state.fight.opened
    assert chance(sim, {**ATTACK, "target": "f2"}) == without_trait(sim, {**ATTACK, "target": "f2"})


def test_no_opening_without_an_ambush() -> None:
    sim = steady(fight(of_class("cutpurse")))
    assert resolve_exchange(sim, "attack", "f1", Outcome.SUCCESS)["hits"] == 1


def test_studied_mark_from_the_second_exchange() -> None:
    sim = fight(of_class("inquisitor"))
    first = chance(sim, ATTACK)
    resolve_exchange(sim, "guard", None, Outcome.SUCCESS)
    assert chance(sim, ATTACK) == first + 10


def test_attunement_is_a_choice_due_for_an_elementalist_only() -> None:
    sim = of_class("elementalist")
    assert needs_attunement(sim.state, DATA)
    with pytest.raises(Rejected):
        choose_attunement(sim, "shadow")
    choose_attunement(sim, "storm")
    assert sim.state.attunement == "storm" and not needs_attunement(sim.state, DATA)
    with pytest.raises(Rejected):
        choose_attunement(sim, "frost")
    with pytest.raises(Rejected):
        choose_attunement(of_class("warden"), "storm")
    assert replay(sim.events).attunement == "storm"


def test_attuned_spells_cost_less_and_land_surer_in_and_out_of_fights() -> None:
    sim = of_class("elementalist", "storm_bolt", "fire_bolt")
    choose_attunement(sim, "storm")
    outside = {"stat": "intellect", "difficulty": "routine", "challenge_tier": 1}
    plain = check_preview(sim.state, sim.rules.data, {**outside, "skill": "fire_bolt"}).chance
    storm = check_preview(sim.state, sim.rules.data, {**outside, "skill": "storm_bolt"}).chance
    assert plain is not None and storm == plain + 5
    assert skill_cost(sim.state, sim.rules.data, STORM_BOLT) == 16
    assert skill_cost(sim.state, sim.rules.data, FIRE_BOLT) == 20
    fight(sim)
    mana = sim.state.mana
    assert apply_tool(sim, "fight_move", {**ATTACK, "stat": "intellect", "skill": "storm_bolt"}).accepted
    spent = next(p for t, p in sim.events if t == "skill_spent")
    assert spent["cost"] == 16 and sim.state.mana >= mana - 16
    rolled = [p for t, p in sim.events if t == "check_resolved"][-1]
    assert rolled["bonuses"] == [["Attuned", 5]]


def test_surge_pays_mana_in_hp_but_never_to_zero() -> None:
    sim = fight(of_class("wildblood", "storm_bolt"))
    hp, mana = sim.state.hp, sim.state.mana
    move = {"move": "guard", "stat": "intellect", "skill": "storm_bolt", "pay_with_hp": True}
    assert apply_tool(sim, "fight_move", move).accepted
    assert sim.state.mana == mana
    surge = next(p for t, p in sim.events if t == "effect_applied" and p["source"] == "surge")
    assert surge["amount"] == 20 and sim.state.hp <= hp - 20
    sim.state.wounds = sim.state.max_hp - 20
    before = len(sim.events)
    sim.state.cooldowns = {}
    assert not apply_tool(sim, "fight_move", move).accepted
    assert len(sim.events) == before
    assert not apply_tool(fight(of_class("warden", "storm_bolt")), "fight_move", move).accepted


def test_malediction_curses_one_foe_once_per_fight() -> None:
    sim = fight(of_class("hexer"))
    plain = chance(sim, ATTACK)
    cursing = {**ATTACK, "trait": True}
    assert chance(sim, cursing) == plain + 10
    assert not apply_tool(sim, "fight_move", {"move": "guard", "stat": "vigor", "trait": True}).accepted
    assert apply_tool(sim, "fight_move", cursing).accepted
    assert sim.state.fight is not None and sim.state.fight.cursed == "f1"
    if sim.state.fight.standing and sim.state.fight.standing[0].id == "f1":
        assert chance(sim, ATTACK) == plain + 10
    assert chance(sim, {**ATTACK, "target": "f2"}) == plain
    assert not apply_tool(sim, "fight_move", {**ATTACK, "target": "f2", "trait": True}).accepted


def test_a_cursed_foe_hits_softer() -> None:
    sim = fight(of_class("hexer"))
    assert sim.state.fight is not None
    for foe in sim.state.fight.foes:
        foe.intent = "strike"
    resolve_exchange(sim, "guard", None, Outcome.FAILURE)
    plain = sim.state.wounds
    cursed = fight(of_class("hexer"))
    assert cursed.state.fight is not None
    for foe in cursed.state.fight.foes:
        foe.intent = "strike"
    cursed.state.fight.cursed = "f1"
    resolve_exchange(cursed, "guard", None, Outcome.FAILURE)
    assert cursed.state.wounds < plain


def test_beast_form_lasts_the_fight_and_bars_skills() -> None:
    sim = fight(of_class("skinchanger", "kick"))
    guard = {"move": "guard", "stat": "agility"}
    plain = chance(sim, guard)
    assert chance(sim, {**guard, "trait": True}) == plain + 10
    assert chance(sim, {**guard, "stat": "intellect", "trait": True}) == chance(
        sim, {**guard, "stat": "intellect"}
    )
    assert not apply_tool(sim, "fight_move", {**guard, "trait": True, "skill": "kick"}).accepted
    assert apply_tool(sim, "fight_move", {**guard, "trait": True}).accepted
    assert sim.state.fight is not None and sim.state.fight.form
    assert chance(sim, guard) == plain + 10
    assert not apply_tool(sim, "fight_move", {**guard, "skill": "kick"}).accepted
    assert not apply_tool(sim, "fight_move", {**guard, "trait": True}).accepted


def test_a_class_without_a_fight_trait_cannot_call_one() -> None:
    sim = fight(of_class("warden"))
    assert not apply_tool(sim, "fight_move", {**ATTACK, "trait": True}).accepted


def test_an_evolved_class_keeps_its_base_trait() -> None:
    sim = of_class("sellsword")
    blademaster = Evolution(
        id="blademaster", name="Blademaster", from_class="sellsword", primary="vigor", secondary="agility"
    )
    data = DATA.model_copy(update={"evolutions": (*DATA.evolutions, blademaster)})
    sim.state.class_id = "blademaster"
    trait = trait_of(sim.state, data)
    assert trait is not None and trait.name == "Momentum"
