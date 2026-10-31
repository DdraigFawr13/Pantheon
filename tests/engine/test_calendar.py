"""ENG-11: in-world time is engine state. Calendar, clocks and petitions (D-038)."""

import re
from pathlib import Path

import pytest

from pantheon.engine.calendar import (
    DAYS_PER_MONTH,
    MONTHS,
    clock_value,
    counted_days,
    date_of,
    format_date,
)
from pantheon.engine.commands import CharacterChoices, choose_class, choose_profession, create_character
from pantheon.engine.rng import RngStreams
from pantheon.engine.state import GameState, replay
from pantheon.engine.timeline import Rules, Simulation
from pantheon.engine.tools import apply_tool, resolve_offer
from pantheon.world.loader import load_world
from pantheon.world.schemas import Clock

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


def sworn() -> Simulation:
    sim = Simulation(GameState(), RngStreams.from_seed(1), RULES, 1)
    sim.emit("opening_gods_drawn", {"gods": ["drovash", "veshra"]})
    create_character(sim, CHOICES)
    resolve_offer(sim, "drovash")
    choose_class(sim, "wager_bound")
    choose_profession(sim, "merchant")
    return sim


def next_turn(sim: Simulation) -> Simulation:
    return Simulation(sim.state, sim.rng, sim.rules, sim.turn + 1)


def advance(sim: Simulation, span: str, count: int = 1) -> dict[str, object]:
    result = apply_tool(sim, "advance_time", {"span": span, "count": count, "reason": "the road"})
    assert result.accepted, result.reason
    return result.data


def pass_days(sim: Simulation, days: int) -> Simulation:
    """Advance a long way across several turns, since one call has a limit."""
    while days > 0:
        step = min(days, 90)
        advance(sim, "days", step)
        days -= step
        sim = next_turn(sim)
    return sim


def test_eng11_play_begins_on_1_seedtide_1140() -> None:
    assert format_date(date_of(0)) == "1 Seedtide 1,140 AS"
    assert sworn().state.day == 0


@pytest.mark.parametrize(
    ("days", "expected"),
    [
        (29, "30 Seedtide 1,140 AS"),
        (30, "1 Greenmonth 1,140 AS"),
        (299, "30 Lastdark 1,140 AS"),
        (300, "Blank Day 1, 1,140 AS"),
        (304, "Blank Day 5, 1,140 AS"),
        (305, "1 Firstthaw 1,141 AS"),
        (365 + 305, "1 Firstthaw 1,142 AS"),
    ],
)
def test_eng11_dates_at_month_and_year_edges(days: int, expected: str) -> None:
    assert format_date(date_of(days)) == expected


def test_eng11_blank_days_are_not_counted() -> None:
    assert counted_days(299) == 299
    assert [counted_days(d) for d in range(300, 305)] == [300] * 5
    assert counted_days(305) == 300
    assert counted_days(306) == 301


def test_calendar_constants_agree_with_canon() -> None:
    overview = (WORLD_DIR / "00_overview.md").read_text(encoding="utf-8")
    assert all(month in overview for month in MONTHS)
    assert len(MONTHS) == 12
    assert f"twelve months of {DAYS_PER_MONTH} days" in overview
    assert "1 Seedtide 1,140 AS" in overview


def test_clock_table_agrees_with_canon() -> None:
    text = (WORLD_DIR / "factions.md").read_text(encoding="utf-8")
    rows = dict(re.findall(r"^\| \*\*(.+?)\*\* \| (\d+) \|", text, re.M))
    assert {c.name: str(c.segments) for c in DATA.clocks} == rows
    start = re.search(r"Start state: (.+)\.", text)
    assert start is not None
    assert start.group(1) == ", ".join(f"{c.name.removeprefix('The ')} {c.start}" for c in DATA.clocks)


def test_eng11_time_moves_only_through_events() -> None:
    sim = sworn()
    data = advance(sim, "hours", 24)
    assert sim.state.day == 1
    assert data["date"] == {"day": 2, "month": "Seedtide", "year": 1140}
    assert ("time_advanced", {"minutes": 1440, "span": "hours", "reason": "the road"}) in sim.events
    assert replay(sim.events).minutes == sim.state.minutes


@pytest.mark.parametrize(
    ("span", "count"), [("days", 91), ("hours", 25), ("minutes", 241), ("days", 0), ("rest", 2), ("day", 2)]
)
def test_eng02_time_spans_have_bounds(span: str, count: int) -> None:
    sim = sworn()
    assert not apply_tool(sim, "advance_time", {"span": span, "count": count, "reason": "x"}).accepted
    assert sim.state.minutes == 0


def test_eng02_a_turn_limits_time_calls() -> None:
    sim = sworn()
    advance(sim, "hours")
    advance(sim, "hours")
    assert not apply_tool(sim, "advance_time", {"span": "hours", "reason": "again"}).accepted


def test_rest_takes_time_and_heals() -> None:
    sim = sworn()
    assert apply_tool(
        sim, "apply_effect", {"kind": "damage", "source": "hazard:fall", "reason": "x"}
    ).accepted
    assert sim.state.wounds > 0
    advance(sim, "rest")
    assert sim.state.wounds == 0
    assert sim.state.minutes == 8 * 60


def test_healing_by_rest_takes_the_same_time_and_cannot_repeat() -> None:
    sim = sworn()
    apply_tool(sim, "apply_effect", {"kind": "damage", "source": "hazard:fall", "reason": "x"})
    assert apply_tool(sim, "apply_effect", {"kind": "heal", "source": "rest", "reason": "slept"}).accepted
    assert sim.state.minutes == 8 * 60
    assert not apply_tool(sim, "advance_time", {"span": "rest", "reason": "again"}).accepted
    assert sim.state.minutes == 8 * 60


def test_rest_without_wounds_only_passes_time() -> None:
    sim = sworn()
    advance(sim, "rest")
    assert sim.state.minutes == 8 * 60
    assert not any(type_ == "effect_applied" for type_, _ in sim.events)


def test_clocks_start_from_canon_without_any_event() -> None:
    state = GameState()
    assert {c.id: clock_value(state, DATA, c.id) for c in DATA.clocks} == {
        "seat_vote": 1,
        "rift_tide": 2,
        "grain_war": 2,
        "ember_fever": 0,
        "lanterns_price": 0,
    }


def test_neglected_clock_gains_one_extra_segment_each_season() -> None:
    sim = sworn()
    pass_days(sim, 89)
    assert clock_value(sim.state, DATA, "rift_tide") == 2
    sim = next_turn(sim)
    advance(sim, "day")
    assert clock_value(sim.state, DATA, "rift_tide") == 2 + 2


def engage(sim: Simulation, clock: str = "rift_tide") -> None:
    args = {"stat": "agility", "difficulty": "routine", "challenge_tier": 1}
    assert apply_tool(sim, "request_check", args).accepted
    result = apply_tool(sim, "engage_clock", {"clock_id": clock, "reason": "closed a rift"})
    assert result.accepted, result.reason


def test_engaged_clock_gains_only_the_seasonal_segment() -> None:
    sim = sworn()
    sim = pass_days(sim, 45)
    engage(sim)
    sim = pass_days(sim, 45)
    assert clock_value(sim.state, DATA, "rift_tide") == 2 + 1
    assert clock_value(sim.state, DATA, "grain_war") == 2 + 2


def test_engaging_needs_a_tested_deed_and_counts_once_a_day() -> None:
    sim = sworn()
    assert not apply_tool(sim, "engage_clock", {"clock_id": "rift_tide", "reason": "talked"}).accepted
    engage(sim)
    assert not apply_tool(sim, "engage_clock", {"clock_id": "rift_tide", "reason": "again"}).accepted
    assert not apply_tool(sim, "engage_clock", {"clock_id": "nonsense", "reason": "x"}).accepted


def test_blank_days_do_not_bring_a_season_closer() -> None:
    """The fourth season ends after 360 counted days: day 365 of play, not day 360."""
    long_clock = Clock(id="long", name="Long", segments=99, start=0, filled="x")
    rules = Rules(DATA.model_copy(update={"clocks": (long_clock,)}), RULES.flag_setters)
    state = GameState()
    state.minutes = 299 * 1440
    state.clocks["long"] = 0
    state.clocks_engaged["long"] = 299
    sim = Simulation(state, RngStreams.from_seed(1), rules, 1)
    advance(sim, "days", 61)
    assert sim.state.day == 360
    assert sim.state.clocks["long"] == 0
    sim = next_turn(sim)
    advance(sim, "days", 5)
    assert sim.state.clocks["long"] == 1


def test_a_filled_clock_stops_and_says_so() -> None:
    sim = pass_days(sworn(), 90)  # Lantern's Price: 4 segments, 2 a season while neglected.
    advance(sim, "days", 90)
    assert clock_value(sim.state, DATA, "lanterns_price") == 4
    filled = [p for t, p in sim.events if t == "clock_advanced" and p["clock"] == "lanterns_price"]
    assert filled[-1]["filled"] is True
    check = {"stat": "agility", "difficulty": "routine", "challenge_tier": 1}
    assert apply_tool(sim, "request_check", check).accepted
    result = apply_tool(sim, "engage_clock", {"clock_id": "lanterns_price", "reason": "x"})
    assert not result.accepted
    assert "filled" in result.reason
    sim = next_turn(sim)
    advance(sim, "days", 90)
    assert clock_value(sim.state, DATA, "lanterns_price") == 4
    assert not [p for t, p in sim.events if t == "clock_advanced" and p["clock"] == "lanterns_price"]


def send(sim: Simulation, god: str = "drovash") -> dict[str, object]:
    args = {"god": god, "ask": "leave an offering", "due_condition": "at the next shrine"}
    result = apply_tool(sim, "send_petition", args)
    assert result.accepted, result.reason
    return result.data


def test_petition_registers_as_a_hook_for_a_sworn_god_only() -> None:
    sim = sworn()
    data = send(sim)
    hook = sim.state.hooks[-1]
    assert hook.id == data["hook_id"]
    assert hook.petition_god == "drovash"
    assert hook.deadline_day == DATA.rewards.petition.days
    args = {"god": "veshra", "ask": "x", "due_condition": "y"}
    assert not apply_tool(sim, "send_petition", args).accepted


def test_one_open_petition_per_god() -> None:
    sim = sworn()
    send(sim)
    sim = next_turn(sim)
    args = {"god": "drovash", "ask": "another", "due_condition": "y"}
    assert not apply_tool(sim, "send_petition", args).accepted


def test_granting_a_petition_raises_standing_once_and_not_in_the_turn_it_came() -> None:
    sim = sworn()
    hook_id = send(sim)["hook_id"]
    args = {"hook_id": hook_id, "granted": True, "reason": "left the offering"}
    assert not apply_tool(sim, "resolve_petition", args).accepted
    before = sim.state.standing.get("drovash", 0)
    sim = next_turn(sim)
    assert apply_tool(sim, "resolve_petition", args).accepted
    assert sim.state.standing["drovash"] == before + DATA.rewards.petition.granted
    assert sim.state.hooks[-1].resolved
    sim = next_turn(sim)
    assert not apply_tool(sim, "resolve_petition", args).accepted


def test_resolving_only_applies_to_an_open_petition() -> None:
    sim = sworn()
    plain = sim.state.hooks[0].id
    args = {"hook_id": plain, "granted": True, "reason": "x"}
    assert not apply_tool(next_turn(sim), "resolve_petition", args).accepted
    args = {"hook_id": 9999, "granted": True, "reason": "x"}
    assert not apply_tool(next_turn(sim), "resolve_petition", args).accepted


def test_an_ignored_petition_lapses_with_time_and_lowers_standing() -> None:
    sim = sworn()
    send(sim)
    before = sim.state.standing.get("drovash", 0)
    days = DATA.rewards.petition.days
    sim = next_turn(sim)
    advance(sim, "days", days)
    assert not sim.state.hooks[-1].resolved
    sim = next_turn(sim)
    advance(sim, "day")
    assert sim.state.hooks[-1].resolved
    assert sim.state.standing["drovash"] == before - DATA.rewards.petition.ignored
