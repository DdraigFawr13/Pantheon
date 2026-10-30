"""NAR-01 to NAR-07, OPS-03: the turn loop against MockClient, and the prompt it assembles."""

from pathlib import Path
from typing import Any

import pytest

from pantheon.engine.commands import CharacterChoices, choose_class, choose_profession, create_character
from pantheon.engine.rng import RngStreams
from pantheon.engine.state import GameState
from pantheon.engine.timeline import Rules, Simulation
from pantheon.engine.tools import resolve_offer
from pantheon.llm.client import LLMReply, ToolCall
from pantheon.llm.mock import MockClient
from pantheon.narrator.assemble import assemble
from pantheon.narrator.loop import TurnOutcome, take_turn
from pantheon.narrator.validators import prose_problems, strip_action_list
from pantheon.storage.db import Database, TurnRecord
from pantheon.world.loader import load_world

WORLD = load_world(Path(__file__).resolve().parents[2] / "world")
assert WORLD.data is not None
RULES = Rules(WORLD.data, {k: f.set_by for k, f in WORLD.flags.items()})
PROSE = "You haul yourself up the broken steps, and the dark gives way to grey light."
ACTIONS = [
    {"label": "Ask who else survived"},
    {"label": "Search the rubble", "cost": "the stones may shift"},
    {"label": "Draw your knife", "violent": True},
]


def sworn_state() -> tuple[GameState, dict[str, Any]]:
    rng = RngStreams.from_seed(11)
    sim = Simulation(GameState(), rng, RULES, 0)
    sim.emit("opening_gods_drawn", {"gods": ["drovash", "veshra"]})
    stats = {"vigor": 30, "agility": 27, "intellect": 24, "resolve": 20, "presence": 18}
    create_character(
        sim,
        CharacterChoices(
            name="Wren",
            people="saltborn",
            origin="toll_ferry_orphan",
            age=20,
            flaw="Hoards small objects",
            debt="A name owed",
            stats=stats,
        ),
    )
    resolve_offer(sim, "drovash")
    choose_class(sim, "wayfinder")
    choose_profession(sim, "merchant")
    return sim.state, rng.state()


def call(name: str, turn: int = 0, **args: Any) -> ToolCall:
    return ToolCall(f"call_{name}_{turn}", name, args)


def tools(*calls: ToolCall) -> LLMReply:
    return LLMReply(tool_calls=calls, tokens_in=10, tokens_cached=5, tokens_out=2)


SUGGEST = tools(call("suggest_actions", actions=ACTIONS))


def run(script: list[LLMReply | None], **kwargs: Any) -> tuple[TurnOutcome, MockClient]:
    state, rng = sworn_state()
    client = MockClient(script)
    return take_turn(client, WORLD, RULES, state, rng, [], "I climb.", 1, **kwargs), client


def test_eng02_a_turn_runs_tools_then_records_prose_and_actions() -> None:
    check = tools(call("request_check", stat="agility", difficulty="routine", challenge_tier=1))
    outcome, client = run([check, SUGGEST, LLMReply(text=PROSE)])
    assert outcome.narration == PROSE and not outcome.is_fallback
    assert [t for t, _ in outcome.events] == ["check_resolved", "actions_suggested"]
    assert outcome.state.checks_made == 1
    assert len(outcome.state.suggested) == 3
    assert (outcome.tokens_in, outcome.tokens_cached, outcome.tokens_out) == (20, 10, 4)
    sent = client.calls[1]["messages"]
    assert sent[-1]["content"][0]["type"] == "tool_result"
    assert '"status": "accepted"' in sent[-1]["content"][0]["content"]


def test_prose_written_beside_a_tool_call_is_kept() -> None:
    outcome, _ = run([LLMReply(text=PROSE, tool_calls=SUGGEST.tool_calls), LLMReply()])
    assert outcome.narration == PROSE


def test_d030_actions_are_requested_when_the_model_skips_them() -> None:
    outcome, client = run([LLMReply(text=PROSE), SUGGEST])
    assert outcome.narration == PROSE
    assert outcome.state.suggested
    assert [t["name"] for t in client.calls[1]["tools"]] == ["suggest_actions"]


def test_d030_a_refusal_to_suggest_leaves_the_prose_standing() -> None:
    outcome, _ = run([LLMReply(text=PROSE), LLMReply(text="No.")])
    assert outcome.narration == PROSE and not outcome.is_fallback


def test_nar06_rejections_retry_at_most_twice_then_drop_and_log() -> None:
    bad = tools(call("grant_xp", kind="enormous", reason="x"))
    outcome, client = run([bad, bad, bad, SUGGEST, LLMReply(text=PROSE)])
    assert outcome.narration == PROSE
    dropped = [p for t, p in outcome.events if t == "tool_call_dropped"]
    assert [d["tool"] for d in dropped] == ["grant_xp"]
    results = [c["messages"][-1]["content"][0]["content"] for c in client.calls[1:4]]
    assert '"rejected"' in results[0] and '"rejected"' in results[1] and '"dropped"' in results[2]


def test_nar04_bad_prose_is_retried_with_the_reason_and_never_recorded() -> None:
    outcome, client = run([LLMReply(text="You take 12 damage."), SUGGEST, LLMReply(text=PROSE)])
    assert outcome.narration == PROSE
    assert any("12" in str(m["content"]) and m["role"] == "user" for m in client.calls[1]["messages"])


def test_nar07_prose_that_keeps_failing_becomes_the_fallback_turn() -> None:
    bad = LLMReply(text="You take 12 damage.")
    outcome, _ = run([bad, bad, bad])
    assert outcome.is_fallback
    assert "12" not in outcome.narration


def test_nar07_outage_gives_a_fallback_and_keeps_resolved_events() -> None:
    check = tools(
        call("request_check", stat="agility", difficulty="routine", challenge_tier=1, stakes="the climb")
    )
    outcome, _ = run([check, None])
    assert outcome.is_fallback
    assert "the climb:" in outcome.narration
    assert [t for t, _ in outcome.events] == ["check_resolved"]


def test_nar07_outage_with_nothing_resolved_still_has_text() -> None:
    outcome, _ = run([None])
    assert outcome.is_fallback and "Nothing has changed" in outcome.narration
    assert outcome.events == []


def test_nar06_round_cap_forces_prose_with_no_tools() -> None:
    hook = [tools(call("register_hook", i, description=f"hook {i}", due_condition="later")) for i in range(2)]
    outcome, client = run([*hook, LLMReply(text=PROSE), SUGGEST], max_rounds=2)
    assert outcome.narration == PROSE
    assert client.calls[2]["tools"] is None


def test_round_cap_accepts_valid_prose_already_written() -> None:
    reply = LLMReply(text=PROSE, tool_calls=(call("register_hook", description="h", due_condition="later"),))
    outcome, _ = run([reply, SUGGEST], max_rounds=1)
    assert outcome.narration == PROSE


def test_round_cap_forced_prose_is_checked_too() -> None:
    hook = tools(call("register_hook", description="h", due_condition="later"))
    outcome, _ = run([hook, LLMReply(text="You gain 50 XP.")], max_rounds=1)
    assert outcome.is_fallback


def test_nar04_numbers_returned_by_the_engine_are_allowed() -> None:
    grant = tools(call("grant_xp", kind="major", reason="x"))
    outcome, _ = run([grant, SUGGEST, LLMReply(text="Level 1 still, you think.")])
    assert not outcome.is_fallback


@pytest.mark.parametrize(
    "text",
    [
        "You lose 12 of your strength.",
        "Roll a d20 for it.",
        "You rolled a seven.",
        "That is a skill check.",
        "Your HP drops.",
        "You gain ten points of renown.",
        "She calls request_check.",
    ],
)
def test_nar04_prose_problems_are_caught(text: str) -> None:
    assert prose_problems(text, set())


@pytest.mark.parametrize(
    "text",
    [
        "Two voices answer in the dark.",
        "The boulder rolled down the stair.",
        "Seven Hands remain, and one Seat stands empty.",
        "The chance of rain seemed small.",
    ],
)
def test_nar04_ordinary_prose_passes(text: str) -> None:
    assert prose_problems(text, set()) == []


@pytest.mark.parametrize(
    "tail",
    [
        "\n\n**Actions:**\n1. **Use the lantern** (cost: 1 stamina)\n2. **Run**",
        "\n\nChoose:\n- **Swear** the Oath\n- **Refuse** both",
        "\n\n---\n**Your next action must be:**\n- **Swear**\n- **Refuse**\n\nWhat will you do?",
        "\n1. Run\n2. Hide",
    ],
)
def test_d030_action_lists_are_cut_from_prose(tail: str) -> None:
    assert strip_action_list(PROSE + tail).startswith(PROSE)
    assert "Swear" not in strip_action_list(PROSE + tail)
    assert "Run" not in strip_action_list(PROSE + tail)


def test_d030_a_list_in_mid_prose_is_cut_and_the_prose_after_it_stays() -> None:
    text = "The voices wait.\n\nChoose:\n- **Swear**\n- **Refuse**\n\nHale's grip tightens."
    assert strip_action_list(text) == "The voices wait.\n\nHale's grip tightens."


def test_nar01_layers_are_in_fixed_order_with_a_stable_cached_prefix() -> None:
    state, _ = sworn_state()
    system, messages = assemble(state, WORLD, [("I run.", "You run.")], "I hide.")
    assert system[0]["cache_control"] == {"type": "ephemeral"}
    assert "Narrator system prompt" not in system[0]["text"]
    assert "The Ledger is the System" in system[0]["text"]
    assert "{{" not in system[0]["text"] + system[1]["text"]
    assert system[1]["text"].index("Character state") < system[1]["text"].index("Due material")
    assert '"name": "Wren"' in system[1]["text"]
    assert [m["role"] for m in messages] == ["user", "assistant", "user"]
    assert messages[-1]["content"].startswith("I hide.")
    other, _ = assemble(state.model_copy(update={"xp": 99}), WORLD, [], "I hide.")
    assert other[0] == system[0]


def test_opening_lore_and_offer_appear_only_until_resolved() -> None:
    unresolved = GameState(opening_gods=["kaul", "hurrow"], stats={"vigor": 20})
    system, _ = assemble(unresolved, WORLD, [], "start")
    assert "The Dual Offer is unresolved" in system[1]["text"]
    assert "Kaul (id kaul) offers the Held Line" in system[1]["text"]
    state, _ = sworn_state()
    assert "Dual Offer is unresolved" not in assemble(state, WORLD, [], "x")[0][1]["text"]


def test_nar02_no_secret_or_sealed_text_reaches_a_prompt() -> None:
    state, _ = sworn_state()
    unresolved = GameState(opening_gods=["kaul", "hurrow"], stats={"vigor": 20})
    prompts = [str(assemble(s, WORLD, [], "x")) for s in (state, unresolved)]
    gated = [e for e in WORLD.lore if e.visibility == "secret" or e.type == "sealed-lore"]
    assert gated
    leaks = [
        entry.id
        for entry in gated
        for line in entry.body.splitlines()
        if len(line) >= 40 and any(line in prompt for prompt in prompts)
    ]
    assert leaks == []  # Ids only: sealed text must not appear in a test report (WLD-04).


def test_nar_ten_turn_scripted_playtest_commits_and_replays(tmp_path: Path) -> None:
    """Roadmap M2 acceptance, with an outage on turn 7: no lost events, no unsupplied numbers."""
    state, rng = sworn_state()
    with Database.open(tmp_path / "play.db") as db:
        tid = db.create_timeline(seed=11, rng_state=rng)
        sim = Simulation(GameState(), RngStreams.from_seed(11), RULES, 0)
        sim.emit("opening_gods_drawn", {"gods": ["drovash", "veshra"]})
        create_character(
            sim,
            CharacterChoices(
                name="Wren",
                people="saltborn",
                origin="toll_ferry_orphan",
                age=20,
                flaw="Hoards small objects",
                debt="A name owed",
                stats={"vigor": 30, "agility": 27, "intellect": 24, "resolve": 20, "presence": 18},
            ),
        )
        resolve_offer(sim, "drovash")
        choose_class(sim, "wayfinder")
        choose_profession(sim, "merchant")
        db.commit_events(tid, 0, sim.events, sim.rng.state())
        for turn in range(1, 11):
            turn_calls = (
                call("request_check", turn, stat="agility", difficulty="hard", challenge_tier=1),
                call("grant_xp", turn, kind="minor", reason="progress"),
                call("register_hook", turn, description=f"Consequence {turn}", due_condition="later"),
                call("suggest_actions", turn, actions=ACTIONS),
            )
            script: list[LLMReply | None] = (
                [None] if turn == 7 else [tools(*turn_calls), LLMReply(text=PROSE)]
            )
            current = db.load_state(tid)
            outcome = take_turn(
                MockClient(script),
                WORLD,
                RULES,
                current,
                db.rng_state(tid),
                db.recent_turns(tid, 6),
                f"Action {turn}",
                turn,
            )
            assert outcome.is_fallback is (turn == 7)
            assert prose_problems(outcome.narration, set()) == []
            db.commit_turn(
                tid,
                TurnRecord(turn, f"Action {turn}", outcome.narration),
                outcome.events,
                outcome.rng_state,
                outcome.state,
            )
            assert 0 <= outcome.state.wounds <= outcome.state.max_hp
        final = outcome.state
        assert db.load_state(tid) == final  # From the turn-10 snapshot.
        with db.conn:
            db.conn.execute("DELETE FROM snapshot")
        assert db.load_state(tid) == final  # From the whole log (ENG-06).
        assert db.last_turn(tid) == 10
        assert final.xp + 100 * 1 >= 25 * 9
        assert len(final.hooks) >= 9
    assert state.level == 1
