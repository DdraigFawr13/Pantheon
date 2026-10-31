"""ENG-08, ENG-10, ENG-11 through the CLI, with scripted input and MockClient: the owner's path (D-038)."""

from pathlib import Path
from typing import Any

from pantheon.engine.state import GameState, Hook
from pantheon.llm.client import ToolCall
from pantheon.llm.mock import MockClient
from pantheon.narrator.assemble import _due_material, state_view
from pantheon.narrator.loop import _numbers_in
from pantheon.narrator.validators import prose_problems
from pantheon.storage.db import Database
from pantheon.ui.cli.app import ledger_lines, main
from tests.test_play import NEW_GAME, WORLD, narration, play, scripted, talk


def run(tmp_path: Path, *args: str) -> int:
    return main([*args, "--db", str(tmp_path / "game.db"), "--config", str(tmp_path / "none.toml")])


def two_talking_turns(tmp_path: Path) -> str:
    _, _, tid = play(tmp_path, [*NEW_GAME, "Who speaks?", "/quit"], [*talk(), *talk()])
    return tid


def test_eng08_fork_command_branches_and_play_continues_the_branch(tmp_path: Path, capsys: Any) -> None:
    parent = two_talking_turns(tmp_path)
    assert run(tmp_path, "fork", "1") == 0
    assert "from turn 1" in capsys.readouterr().out
    _, _, tid = play(tmp_path, ["/quit"], [])
    assert tid != parent
    with Database.open(tmp_path / "game.db") as db:
        assert db.last_turn(tid) == 1
        assert db.last_turn(parent) == 2


def test_eng08_play_can_return_to_the_original_timeline(tmp_path: Path) -> None:
    parent = two_talking_turns(tmp_path)
    assert run(tmp_path, "fork", "1") == 0
    state_path = str(tmp_path / "game.db")
    code = main(
        ["play", "--timeline", parent[:8], "--db", state_path, "--config", str(tmp_path / "none.toml")],
        ask=scripted(["Once more", "/quit"]),
        client=MockClient(talk()),
    )
    assert code == 0
    with Database.open(tmp_path / "game.db") as db:
        assert db.last_turn(parent) == 3


def test_eng08_fork_command_names_what_it_cannot_do(tmp_path: Path, capsys: Any) -> None:
    assert run(tmp_path, "fork", "1") == 1
    assert "no timeline" in capsys.readouterr().out
    two_talking_turns(tmp_path)
    assert run(tmp_path, "fork", "99") == 1
    assert "no turn 99" in capsys.readouterr().out
    assert run(tmp_path, "fork", "1", "--timeline", "zzzz") == 1


def test_game05_a_bad_save_gives_a_message_and_stays_untouched(tmp_path: Path, capsys: Any) -> None:
    path = tmp_path / "game.db"
    path.write_bytes(b"not a database, and long enough that SQLite reads it as one" * 20)
    before = path.read_bytes()
    assert run(tmp_path, "new") == 1
    assert "left alone" in capsys.readouterr().out
    assert path.read_bytes() == before


def test_resuming_asks_a_choice_left_open_when_the_game_closed(tmp_path: Path) -> None:
    play(tmp_path, [*NEW_GAME, "4"], [*talk()])  # Input ends at the class prompt, right after swearing.
    _, state, _ = play(tmp_path, ["1", "1", "/quit"], [])
    assert state.class_id is not None
    assert state.profession is not None


def test_eng11_narrator_moves_the_calendar_and_the_player_sees_it(tmp_path: Path, capsys: Any) -> None:
    walk = ToolCall("t", "advance_time", {"span": "days", "count": 3, "reason": "the road north"})
    script = [*talk(), *narration()[1:], *narration(walk)]
    _, state, _ = play(tmp_path, [*NEW_GAME, "4", "1", "1", "I walk north", "/quit"], script)
    assert state.day == 3
    out = capsys.readouterr().out
    assert "Time passes (the road north)." in out
    assert "4 Seedtide 1,140 AS" in out


def test_ledger_shows_clocks_and_petitions() -> None:
    base = {"clock": "x", "name": "The Rift Tide", "segments": 8, "neglected": True}
    lines = ledger_lines(
        [
            ("clock_advanced", {**base, "value": 4, "filled": False}),
            ("clock_advanced", {**base, "value": 8, "filled": True}),
            ("petition_resolved", {"hook_id": 1, "granted": True, "reason": "paid"}),
            ("petition_resolved", {"hook_id": 1, "granted": False, "reason": "left too long"}),
        ]
    )
    assert lines == [
        "The Rift Tide moves: 4 of 8",
        "The Rift Tide [bold]has filled[/bold]: 8 of 8",
        "Petition granted (paid)",
        "Petition not granted (left too long)",
    ]


def test_narrator_is_told_of_moved_and_filled_clocks_and_only_open_hooks() -> None:
    state = GameState(
        clocks={"rift_tide": 3, "lanterns_price": 4},
        hooks=[
            Hook(id=1, turn=1, description="Open debt", due_condition="soon"),
            Hook(id=2, turn=1, description="Closed debt", due_condition="soon", resolved=True),
        ],
    )
    due = _due_material(state, WORLD)
    assert "The Rift Tide has moved: 3 of 8" in due
    assert "The Lantern's Price has filled: A prophecy comes due" in due
    assert "Open debt" in due
    assert "Closed debt" not in due
    assert "Grain War" not in due  # A clock at its canon start is only lore.


def test_nar04_prose_may_state_the_date_on_the_sheet() -> None:
    allowed = _numbers_in(state_view(GameState()))
    assert prose_problems("It was 1 Seedtide, 1,140 years after the Severance.", allowed) == []
    assert prose_problems("It was 9 Seedtide.", allowed) != []
