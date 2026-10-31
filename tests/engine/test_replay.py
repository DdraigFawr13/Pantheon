"""ENG-06, D-022: any sequence of tool calls replays to the live state, within bounds, through a real save."""

import tempfile
from pathlib import Path
from typing import Any

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from pantheon.engine.calendar import clock_value
from pantheon.engine.commands import CharacterChoices, choose_class, choose_profession, create_character
from pantheon.engine.rng import RngStreams
from pantheon.engine.state import STANDING_MAX, STANDING_MIN, GameState, replay
from pantheon.engine.timeline import Rules, Simulation
from pantheon.engine.tools import apply_tool, resolve_offer
from pantheon.storage.db import Database, TurnRecord
from pantheon.world.loader import load_world

WORLD = load_world(Path(__file__).resolve().parents[2] / "world")
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
GODS = st.sampled_from(["drovash", "veshra", "kaul"])
CALLS = st.one_of(
    st.fixed_dictionaries(
        {
            "stat": st.sampled_from(["vigor", "presence"]),
            "difficulty": st.sampled_from(["routine", "heroic"]),
        },
        optional={"challenge_tier": st.integers(-1, 9)},
    ).map(lambda a: ("request_check", a)),
    st.sampled_from(["minor", "major", "milestone", "huge"]).map(
        lambda k: ("grant_xp", {"kind": k, "reason": "x"})
    ),
    st.sampled_from(["hazard:fall", "c1", "nonsense"]).map(
        lambda s: ("apply_effect", {"kind": "damage", "source": s, "reason": "x"})
    ),
    st.sampled_from(["rest", "aid:a friend", "nonsense"]).map(
        lambda s: ("apply_effect", {"kind": "heal", "source": s, "reason": "x"})
    ),
    st.tuples(st.sampled_from(["minutes", "hours", "rest", "day", "days", "weeks"]), st.integers(0, 120)).map(
        lambda v: ("advance_time", {"span": v[0], "count": v[1], "reason": "x"})
    ),
    GODS.map(lambda g: ("send_petition", {"god": g, "ask": "an offering", "due_condition": "soon"})),
    st.tuples(st.integers(0, 12), st.booleans()).map(
        lambda v: ("resolve_petition", {"hook_id": v[0], "granted": v[1], "reason": "x"})
    ),
    st.sampled_from(["rift_tide", "lanterns_price", "nonsense"]).map(
        lambda c: ("engage_clock", {"clock_id": c, "reason": "x"})
    ),
    st.tuples(GODS, st.sampled_from(["slight", "grave"]), st.sampled_from(["+", "-"])).map(
        lambda v: (
            "adjust_standing",
            {"entity": v[0], "kind": v[1], "direction": v[2], "witness": "npc:a", "reason": "x"},
        )
    ),
    st.just(("register_hook", {"description": "a debt", "due_condition": "later"})),
    st.just(("not_a_tool", {})),
)
SCRIPT = st.lists(st.lists(CALLS, max_size=4), min_size=11, max_size=14)


def opening() -> Simulation:
    sim = Simulation(GameState(), RngStreams.from_seed(1), RULES, 0)
    sim.emit("opening_gods_drawn", {"gods": ["drovash", "veshra"]})
    create_character(sim, CHOICES)
    resolve_offer(sim, "drovash")
    choose_class(sim, "wager_bound")
    choose_profession(sim, "merchant")
    return sim


def run_script(
    db: Database, tid: str, opened: Simulation, script: list[list[tuple[str, dict[str, Any]]]]
) -> GameState:
    """Play each list of calls as a turn. A rejected call must leave no trace (D-022)."""
    state, rng = opened.state, opened.rng
    db.commit_events(tid, 0, opened.events, rng.state())
    for number, calls in enumerate(script, 1):
        sim = Simulation(state, rng, RULES, number)
        for name, args in calls:
            before_rng, before_events = rng.state(), len(sim.events)
            before_state = sim.state.model_dump()
            if not apply_tool(sim, name, args).accepted:
                assert rng.state() == before_rng
                assert len(sim.events) == before_events
                assert sim.state.model_dump() == before_state
        assert_bounds(sim.state)
        db.commit_turn(tid, TurnRecord(number, "act", "prose"), sim.events, rng.state(), sim.state)
        state = sim.state
    return state


def assert_bounds(state: GameState) -> None:
    assert 0 <= state.hp <= state.max_hp
    assert state.xp >= 0
    assert state.minutes >= 0
    assert all(STANDING_MIN <= v <= STANDING_MAX for v in state.standing.values())
    for clock in DATA.clocks:
        assert 0 <= clock_value(state, DATA, clock.id) <= clock.segments
    assert len({h.id for h in state.hooks}) == len(state.hooks)


@given(SCRIPT)
@settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_eng06_replay_equals_live_state_through_a_real_save(
    script: list[list[tuple[str, dict[str, Any]]]],
) -> None:
    with tempfile.TemporaryDirectory() as folder, Database.open(Path(folder) / "p.db") as db:
        tid = db.create_timeline(seed=1, rng_state=RngStreams.from_seed(1).state())
        live = run_script(db, tid, opening(), script)
        records = [(e["type"], e["payload"]) for e in db.events(tid)]
        assert db.last_turn(tid) == len(script) >= 10
        assert db.conn.execute("SELECT COUNT(*) FROM snapshot").fetchone()[0] >= 1
        assert db.load_state(tid).model_dump() == live.model_dump()  # From the snapshot.
        assert replay(records).model_dump() == live.model_dump()  # From the origin.


@given(SCRIPT)
@settings(max_examples=15, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_eng08_a_fork_replayed_with_the_same_calls_ends_the_same(
    script: list[list[tuple[str, dict[str, Any]]]],
) -> None:
    """ENG-03 and ENG-08 together: the RNG restored at a turn gives the parent's later rolls."""
    with tempfile.TemporaryDirectory() as folder, Database.open(Path(folder) / "p.db") as db:
        tid = db.create_timeline(seed=1, rng_state=RngStreams.from_seed(1).state())
        live = run_script(db, tid, opening(), script)
        fork = db.fork(tid, 5)
        state, rng = db.load_state(fork), RngStreams.from_state(db.rng_state(fork))
        for number, calls in enumerate(script[5:], 6):
            sim = Simulation(state, rng, RULES, number)
            for name, args in calls:
                apply_tool(sim, name, args)
            db.commit_turn(fork, TurnRecord(number, "act", "prose"), sim.events, rng.state(), sim.state)
            state = sim.state
        assert db.load_state(fork).model_dump() == live.model_dump()
