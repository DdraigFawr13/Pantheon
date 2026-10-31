"""The whole game through the CLI, with scripted input and MockClient (D-029): the owner's path."""

import itertools
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from pantheon.config import load_env_file
from pantheon.engine.state import GameState
from pantheon.llm.client import LLMReply, ToolCall
from pantheon.llm.mock import MockClient
from pantheon.storage.db import Database
from pantheon.ui.cli.app import main, spoken_choice
from pantheon.world.loader import load_world

WORLD = load_world(Path(__file__).resolve().parents[1] / "world")
PROSE = "The dark presses close."
ACTIONS = [
    {"label": "Ask what it wants"},
    {"label": "Bargain", "cost": "it may remember"},
    {"label": "Lash out", "violent": True},
]


def scripted(lines: list[str]) -> Callable[[str], str]:
    remaining = list(lines)

    def ask(_: str) -> str:
        if not remaining:
            raise EOFError
        return remaining.pop(0)

    return ask


_WORDS = itertools.cycle(("first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth"))


def narration(*calls: ToolCall, check: ToolCall | None = None) -> list[LLMReply | None]:
    """A turn after the Dual Offer: referee, prose, scribe."""
    suggest = ToolCall("s", "suggest_actions", {"actions": ACTIONS})
    referee = LLMReply(tool_calls=(check,)) if check else LLMReply(text="NONE")
    prose = f"{PROSE} The {next(_WORDS)} stair groans under you, and the dust has not yet settled."
    return [referee, LLMReply(text=prose), LLMReply(tool_calls=(*calls, suggest))]


def talk() -> list[LLMReply | None]:
    """A turn before the Dual Offer is answered: prose, then actions."""
    return narration()[1:]


def play(
    tmp_path: Path, lines: list[str], script: list[LLMReply | None], *flags: str
) -> tuple[int, GameState, str]:
    db_path = tmp_path / "game.db"
    code = main(
        ["play", "--seed", "42", "--db", str(db_path), "--config", str(tmp_path / "none.toml"), *flags],
        ask=scripted(lines),
        client=MockClient(script),
    )
    with Database.open(db_path) as db:
        tid = db.latest_timeline()
        assert tid is not None
        return code, db.load_state(tid), tid


# Humans ask two extra questions; Saltborn (4) have one fixed affinity and stat.
NEW_GAME = ["Wren", "21", "4", "2", "a p v i r", "Cannot refuse a dare", "Forty silver"]


def test_new_game_creates_a_character_and_plays_the_opening(tmp_path: Path, capsys: Any) -> None:
    code, state, _ = play(tmp_path, [*NEW_GAME, "/quit"], talk())
    assert code == 0
    assert state.name == "Wren" and state.people == "saltborn" and state.origin == "toll_ferry_orphan"
    assert state.stats["agility"] == 32 and state.stats["presence"] == 30
    out = capsys.readouterr().out
    assert PROSE[:20] in out
    assert "Refuse both gods" in out
    assert "Swear the" in out


def test_swearing_from_the_menu_then_choosing_class_and_profession(tmp_path: Path, capsys: Any) -> None:
    lines = [*NEW_GAME, "4", "1", "1", "/sheet", "/hooks", "/help", "/quit"]
    _code, state, _ = play(tmp_path, lines, [*talk(), *narration()])
    assert state.level == 1 and len(state.oaths) == 1
    assert state.class_id == "blade_sworn"
    assert state.profession == "herbalist"
    out = capsys.readouterr().out
    assert "The Ledger" in out
    assert "Commands:" in out


def test_refusing_from_the_menu_stays_unwritten(tmp_path: Path) -> None:
    _code, state, _ = play(tmp_path, [*NEW_GAME, "6", "/quit"], [*talk(), *narration()])
    assert state.level == 0 and state.flags["unwritten_path"] is True


def test_a_suggested_action_becomes_the_players_turn_and_the_ledger_shows_results(
    tmp_path: Path, capsys: Any
) -> None:
    check = ToolCall(
        "c",
        "request_check",
        {"stat": "agility", "difficulty": "routine", "challenge_tier": 0, "stakes": "x"},
    )
    calls = (
        ToolCall(
            "h", "apply_effect", {"kind": "damage", "source": "hazard:rocks", "reason": "falling rocks"}
        ),
        ToolCall(
            "g",
            "adjust_standing",
            {"entity": "kaul", "kind": "slight", "direction": "+", "witness": "npc:a", "reason": "seen"},
        ),
        ToolCall(
            "r", "adjust_standing", {"entity": "kaul", "kind": "slight", "direction": "+", "reason": "unseen"}
        ),
        ToolCall("k", "register_hook", {"description": "The stones remember", "due_condition": "later"}),
    )
    lines = [*NEW_GAME, "4", "1", "1", "1", "/quit"]
    _code, state, tid = play(tmp_path, lines, [*talk(), *narration(), *narration(*calls, check=check)])
    with Database.open(tmp_path / "game.db") as db:
        assert db.recent_turns(tid, 1)[0][0] == "Ask what it wants"
    assert state.wounds > 0
    out = capsys.readouterr().out
    for expected in ("Agility check", "falling rocks", "Standing with kaul", "Rumour", "The stones remember"):
        assert expected in out


def test_d033_the_oath_menu_states_its_terms_plainly(tmp_path: Path, capsys: Any) -> None:
    code, state, _ = play(tmp_path, [*NEW_GAME, "/quit"], talk())
    assert code == 0
    out = " ".join(capsys.readouterr().out.split())
    oaths = {o.id: o for o in WORLD.data.oaths} if WORLD.data else {}
    gods = {g.id: g for g in WORLD.data.gods} if WORLD.data else {}
    for god in state.opening_gods:
        oath = oaths[gods[god].first_oath]
        assert oath.perk in out and oath.burden in out
    assert "No class or level" in out


ROLL = {"stat": "presence", "difficulty": "routine", "challenge_tier": 0, "stakes": "its patience"}
TAGGED = [
    {"label": "Ask what it wants", "check": ROLL, "cost": "it may remember"},
    {"label": "Speak the Oath", "tag": "Held Line"},
    {"label": "Back away"},
]


def tagged_turn(actions: list[dict[str, Any]]) -> list[LLMReply | None]:
    reply = LLMReply(tool_calls=(ToolCall("s", "suggest_actions", {"actions": actions}),))
    return [LLMReply(text=f"{PROSE} The stair shifts under you."), reply]


def sworn_game(god: str = "4") -> list[str]:
    return [*NEW_GAME, god, "1", "1"]


def test_d036_options_show_real_odds_and_hide_the_cost_hint(tmp_path: Path, capsys: Any) -> None:
    code, state, _ = play(tmp_path, [*NEW_GAME, "/quit"], talk())
    assert code == 0
    first_oath = {g.id: g.first_oath for g in WORLD.data.gods}[state.opening_gods[0]] if WORLD.data else ""
    name = {o.id: o.name for o in WORLD.data.oaths}[first_oath] if WORLD.data else ""
    actions = [TAGGED[0], {"label": "Speak the Oath", "tag": name}, TAGGED[2]]
    capsys.readouterr()
    lines = ["4", "1", "1", "/quit"]
    _code, _state, _ = play(tmp_path, lines, tagged_turn(actions))
    out = capsys.readouterr().out
    # An Oath means Tier 1: routine 60, (30 - 35) // 5 for Presence 30, and +20 against a Tier 0 obstacle.
    assert "[PRESENCE 79%] Ask what it wants" in out
    assert f"[{name.upper()}] Speak the Oath" in out
    assert "Or type your own" in out
    assert "it may remember" not in out


def test_d036_picking_an_option_rolls_exactly_what_it_showed(tmp_path: Path) -> None:
    script = [*talk(), *tagged_turn([TAGGED[0], TAGGED[2], {"label": "Wait"}]), *narration()[1:]]
    _code, _state, tid = play(tmp_path, [*sworn_game(), "1", "/quit"], script)
    with Database.open(tmp_path / "game.db") as db:
        assert db.recent_turns(tid, 1)[0][0] == "Ask what it wants"
        rolled = [e["payload"] for e in db.events(tid) if e["type"] == "check_resolved"]
    assert len(rolled) == 1 and rolled[0]["stat"] == "presence" and rolled[0]["chance"] == 79


def test_d036_a_check_shown_in_the_story_does_not_print_again(tmp_path: Path, capsys: Any) -> None:
    marked = f"{PROSE} She tried it.\n\n<<CHECK>>\n\nThe stair held under her, and the dust settled."
    reply = LLMReply(tool_calls=(ToolCall("s", "suggest_actions", {"actions": ACTIONS}),))
    script = [*talk(), *tagged_turn([TAGGED[0], TAGGED[2], {"label": "Wait"}]), LLMReply(text=marked), reply]
    play(tmp_path, [*sworn_game(), "1", "/quit"], script)
    out = capsys.readouterr().out
    assert out.count("Presence check") == 1
    assert "<<CHECK>>" not in out


def test_d036_inspect_describes_an_option_and_costs_no_turn(tmp_path: Path, capsys: Any) -> None:
    script = [*talk(), *tagged_turn([TAGGED[0], TAGGED[2], {"label": "Wait"}])]
    lines = [*sworn_game(), "inspect 1", "/inspect 3", "inspect 9", "inspect", "/quit"]
    _code, _state, tid = play(tmp_path, lines, script)
    out = " ".join(capsys.readouterr().out.split())
    assert "Presence 30" in out and "routine" in out and "79%" in out
    assert "its patience" in out and "it may remember" in out
    assert "No roll" in out
    assert "There is no option 9" in out
    assert "inspect 2" in out
    with Database.open(tmp_path / "game.db") as db:
        assert db.last_turn(tid) == 2


def test_d033_swearing_and_levelling_show_the_full_sheet(tmp_path: Path, capsys: Any) -> None:
    grant = ToolCall("g", "grant_xp", {"kind": "milestone", "reason": "a great deed"})
    check = ToolCall("c", "request_check", {"stat": "agility", "difficulty": "routine", "challenge_tier": 0})
    lines = [*NEW_GAME, "4", "1", "1", "Do the deed", "2", "/quit"]
    play(tmp_path, lines, [*talk(), *narration(), *narration(grant, check=check)])
    out = capsys.readouterr().out
    assert out.count("The Ledger") >= 2
    assert "█" in out


def test_d035_commands_work_without_a_slash_and_are_on_screen(tmp_path: Path, capsys: Any) -> None:
    code, state, _ = play(tmp_path, [*NEW_GAME, "sheet", "hooks", "help", "?", "QUIT"], talk())
    assert code == 0 and state.name == "Wren"
    out = capsys.readouterr().out
    assert "Unwritten" in out  # The sheet's title before an Oath.
    assert "Debt:" in out  # A hook from character creation.
    assert "sheet" in out and "quit" in out
    assert out.count("Commands:") >= 2


def test_d035_a_word_inside_a_sentence_is_still_an_action(tmp_path: Path) -> None:
    lines = [*NEW_GAME, "4", "1", "1", "help the dying man", "/quit"]
    _code, _state, tid = play(tmp_path, lines, [*talk(), *narration(), *narration()])
    with Database.open(tmp_path / "game.db") as db:
        assert db.recent_turns(tid, 1)[0][0] == "help the dying man"


def test_d035_swear_with_no_god_lists_the_choices(tmp_path: Path, capsys: Any) -> None:
    _code, state, _ = play(tmp_path, [*NEW_GAME, "/swear", "/quit"], talk())
    assert state.level == 0
    assert "Use the numbers" in capsys.readouterr().out


def test_typed_oath_asks_first_and_a_no_keeps_the_turn(tmp_path: Path) -> None:
    lines = [*NEW_GAME, "I swear to no one", "/quit"]
    _code, state, _ = play(tmp_path, lines, [*talk(), *narration()])
    assert state.level == 0 and not state.offer_resolved


def test_xp_level_up_prompts_for_the_free_point(tmp_path: Path, capsys: Any) -> None:
    grant = ToolCall("g", "grant_xp", {"kind": "milestone", "reason": "a great deed"})
    lines = [*NEW_GAME, "4", "1", "1", "Do the deed", "2", "/quit"]
    check = ToolCall("c", "request_check", {"stat": "agility", "difficulty": "routine", "challenge_tier": 0})
    _code, state, _ = play(tmp_path, lines, [*talk(), *narration(), *narration(grant, check=check)])
    assert state.level == 2 and state.free_points == 0
    out = capsys.readouterr().out
    assert "Level 2!" in out and "Place your free point" in out


def test_resume_shows_the_last_turn_and_a_downed_character(tmp_path: Path, capsys: Any) -> None:
    play(tmp_path, [*NEW_GAME, "/quit"], talk())
    capsys.readouterr()
    code, state, _ = play(tmp_path, ["/quit"], [])
    assert code == 0 and state.name == "Wren"
    assert PROSE[:20] in capsys.readouterr().out


def test_end_of_input_saves_and_exits(tmp_path: Path, capsys: Any) -> None:
    code, _state, _ = play(tmp_path, NEW_GAME, talk())
    assert code == 0
    assert "Saved" in capsys.readouterr().out


def test_no_model_configured_says_what_to_do(tmp_path: Path, capsys: Any) -> None:
    code = main(
        ["play", "--db", str(tmp_path / "x.db"), "--config", str(tmp_path / "none.toml")], ask=scripted([])
    )
    assert code == 1
    assert "config.toml" in capsys.readouterr().out


def test_fresh_starts_a_new_timeline(tmp_path: Path) -> None:
    _c, _s, first = play(tmp_path, [*NEW_GAME, "/quit"], talk())
    _c, _s, second = play(tmp_path, [*NEW_GAME, "/quit"], talk(), "--fresh")
    assert first != second


def test_humans_choose_their_stat_and_affinity(tmp_path: Path) -> None:
    lines = ["Ana", "", "1", "1", "1", "1", "nonsense", "a p v i r", "", "", "/quit"]
    _code, state, _ = play(tmp_path, lines, talk())
    assert state.age == 22
    assert state.stats["vigor"] == 24 + 3 + 0
    assert state.affinities == {"flame": 1}
    assert state.flaw and state.debt


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("I swear to Veshra", "veshra"),
        ("I accept the Open Hand", "veshra"),
        ("I refuse you both", "refuse"),
        ("Should I swear to Veshra?", None),
        ("I swear to no one", None),
        ("I swear to Kaul", None),
        ("I swear to Veshra and Ilvane", None),
        ("I walk away", None),
    ],
)
def test_spoken_choice_is_only_ever_a_clear_one(line: str, expected: str | None) -> None:
    state = GameState(opening_gods=["veshra", "ilvane"])
    assert spoken_choice(line, state, WORLD) == expected


def test_d032_a_missing_api_key_says_what_to_do(tmp_path: Path, capsys: Any, monkeypatch: Any) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr("pantheon.config.load_env_file", lambda _: None)  # A real .env must not change this.
    config = tmp_path / "c.toml"
    config.write_text('[models]\nnarrator = "a-model"\n', encoding="utf-8")
    code = main(["play", "--db", str(tmp_path / "x.db"), "--config", str(config)], ask=scripted([]))
    assert code == 1
    assert ".env" in capsys.readouterr().out


def test_d032_env_file_supplies_settings_but_a_real_variable_wins(tmp_path: Path, monkeypatch: Any) -> None:
    env = tmp_path / ".env"
    env.write_text(
        '# note\nPANTHEON_A="from file"\nPANTHEON_B=from file\nPANTHEON_EMPTY=\nno separator\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("PANTHEON_B", "real")
    monkeypatch.delenv("PANTHEON_A", raising=False)
    monkeypatch.delenv("PANTHEON_EMPTY", raising=False)
    load_env_file(env)
    assert os.environ["PANTHEON_A"] == "from file"
    assert os.environ["PANTHEON_B"] == "real"
    assert "PANTHEON_EMPTY" not in os.environ
    monkeypatch.delenv("PANTHEON_A")
    load_env_file(tmp_path / "missing")
