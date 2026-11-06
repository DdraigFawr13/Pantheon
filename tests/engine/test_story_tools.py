"""ENG-02, ENG-06, D-024, D-031: the narrator's story tools (spec m2c-story-tools, S1: people and places)."""

from typing import Any

import pytest

from pantheon.engine.commands import CharacterChoices, choose_class, choose_profession, create_character
from pantheon.engine.rng import RngStreams
from pantheon.engine.state import Fight, Foe, GameState, replay
from pantheon.engine.timeline import Rules, Simulation
from pantheon.engine.tools import (
    MAX_LOCATIONS_PER_TURN,
    MAX_NPCS_PER_TURN,
    apply_tool,
    resolve_offer,
    tool_definitions,
)
from pantheon.narrator.loop import SCRIBE_TOOLS, turn_tools
from pantheon.ui.cli.app import ledger_lines
from tests.conftest import WORLD

assert WORLD.data is not None
DATA = WORLD.data
RULES = Rules(
    DATA,
    {k: f.set_by for k, f in WORLD.flags.items() if not f.needs_npc_role},
    flag_roles={k: f.needs_npc_role for k, f in WORLD.flags.items() if f.needs_npc_role},
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
TAM = {"name": "Tam", "role": "rifter", "tier": 1, "disposition": "wary"}
CELLAR = {
    "name": "The Drowned Cellar",
    "region": "ford_reaches",
    "description": "A flooded cellar under the old toll house, reached by a rope.",
}


def sworn() -> Simulation:
    sim = Simulation(GameState(), RngStreams.from_seed(1), RULES, 0)
    sim.emit("opening_gods_drawn", {"gods": ["drovash", "veshra"]})
    create_character(sim, CHOICES)
    resolve_offer(sim, "drovash")
    choose_class(sim, "cutpurse")
    choose_profession(sim, "merchant")
    return sim


def next_turn(sim: Simulation) -> Simulation:
    return Simulation(sim.state, sim.rng, sim.rules, sim.turn + 1)


def with_tam() -> Simulation:
    sim = sworn()
    assert apply_tool(sim, "introduce_npc", TAM).accepted
    return next_turn(sim)


def reason(sim: Simulation, tool: str, args: dict[str, Any]) -> str:
    result = apply_tool(sim, tool, args)
    assert not result.accepted, result
    return result.reason


def test_eng02_introduce_npc_records_and_shows_the_person() -> None:
    sim = sworn()
    sim.turn = 3
    before = len(sim.events)
    result = apply_tool(sim, "introduce_npc", TAM)
    assert result.accepted, result.reason
    assert [t for t, _ in sim.events[before:]] == ["npc_introduced"]
    npc = sim.state.npcs[0]
    assert (npc.id, npc.name, npc.role, npc.tier, npc.disposition, npc.turn) == (
        "tam",
        "Tam",
        "rifter",
        1,
        "wary",
        3,
    )
    assert ledger_lines(sim.events[before:]) == ["Met: Tam, rifter (Tier 1, wary)"]
    assert replay(sim.events).npcs == sim.state.npcs  # The fold alone rebuilds the cast (ENG-06).


def test_eng02_introduce_npc_rejects_duplicates_tier_above_the_cap_and_a_third_a_turn() -> None:
    sim = with_tam()
    assert reason(sim, "introduce_npc", {**TAM, "name": "tam"}) == "Tam is already known"
    assert reason(sim, "introduce_npc", {**TAM, "name": "Tam the Rifter"}) == "Tam is already known"
    assert (
        reason(sim, "introduce_npc", {**TAM, "name": "Dunmore"})
        == "Hale Dunmore is already known (regions.yaml notables)"
    )
    assert (
        reason(sim, "introduce_npc", {**TAM, "name": "Stranger", "tier": 4})
        == "nobody above Tier 3 can be met yet (regions.yaml, home region cap)"
    )
    assert reason(sim, "introduce_npc", {**TAM, "name": "...", "role": "rifter"}) == "a name needs letters"
    assert "vessel:nobody" in reason(sim, "introduce_npc", {**TAM, "name": "Odd", "role": "vessel:nobody"})
    assert (
        sim.events == [] and sim.call_counts["introduce_npc"] == 0
    )  # Rejected calls spent none of the count.
    assert MAX_NPCS_PER_TURN == 2
    assert apply_tool(sim, "introduce_npc", {**TAM, "name": "Ilse"}).accepted
    assert apply_tool(sim, "introduce_npc", {**TAM, "name": "Odo"}).accepted
    assert reason(sim, "introduce_npc", {**TAM, "name": "Pell"}) == "at most 2 people a turn"
    assert [n.name for n in sim.state.npcs] == ["Tam", "Ilse", "Odo"]


def test_eng02_introduce_location_records_once_and_knows_the_map() -> None:
    sim = with_tam()
    result = apply_tool(sim, "introduce_location", CELLAR)
    assert result.accepted, result.reason
    place = sim.state.locations[0]
    assert (place.id, place.region, place.region_name) == (
        "drowned_cellar",
        "ford_reaches",
        "The Ford Reaches",
    )
    assert ledger_lines(sim.events) == ["Found: The Drowned Cellar (The Ford Reaches)"]
    assert replay(sim.events, None).locations == sim.state.locations
    assert (
        reason(sim, "introduce_location", {**CELLAR, "name": "Cinder Ford"})
        == "Cinder Ford is already on the map (regions.yaml)"
    )
    assert reason(sim, "introduce_location", {**CELLAR, "name": "Elsewhere", "region": "nowhere"}) == (
        "there is no region nowhere"
    )
    assert reason(sim, "introduce_location", {**CELLAR, "name": "The Drowned Cellar"}) == (
        "The Drowned Cellar is already on the map"
    )
    assert MAX_LOCATIONS_PER_TURN == 1
    assert reason(sim, "introduce_location", {**CELLAR, "name": "The Salt Pans"}) == "at most 1 place a turn"
    assert len(sim.state.locations) == 1


def test_d031_people_and_places_are_scribe_tools_only() -> None:
    state = sworn().state
    names = {"introduce_npc", "introduce_location"}
    assert names <= set(SCRIBE_TOOLS) and names <= {d["name"] for d in tool_definitions()}
    assert not names & set(turn_tools(state, "I look around"))  # Before the prose.
    assert names <= set(turn_tools(state, "I look around", narrated=True, checked=True))
    unanswered = GameState(offers=["fair_wager", "open_hand"], created=True)
    assert not names & set(turn_tools(unanswered, "I listen", narrated=True))
    foe = Foe(id="f1", name="Ash Hound", tier=0, threat="standard", hits_left=2, intent="strike")
    downed = state.model_copy(update={"downed": True, "fight": Fight(foes=[foe])})
    assert turn_tools(downed, "I hold on") == ()


def test_d024_met_drovash_vessel_opens_after_the_vessel_is_introduced() -> None:
    sim = sworn()
    assert "met_drovash_vessel" not in RULES.flag_setters
    key = {"key": "met_drovash_vessel", "value": True}
    assert reason(sim, "set_flag", key) == "needs a known person with role vessel:drovash"
    assert apply_tool(
        sim, "introduce_npc", {**TAM, "name": "Sister Ember", "role": "vessel:drovash"}
    ).accepted
    assert apply_tool(sim, "set_flag", key).accepted
    assert apply_tool(sim, "set_flag", {**key, "value": False}).accepted
    assert sim.state.flags["met_drovash_vessel"] is False
    assert reason(sim, "set_flag", {"key": "prophecy_bought", "value": True}) == (
        "prophecy_bought cannot be set by the narrator in this build"
    )


@pytest.mark.parametrize("bad", [{"disposition": "furious"}, {"tier": 9}, {"name": "A"}, {"role": ""}])
def test_eng02_introduce_npc_rejects_malformed_arguments(bad: dict[str, Any]) -> None:
    sim = sworn()
    assert not apply_tool(sim, "introduce_npc", {**TAM, **bad}).accepted
    assert not sim.state.npcs
