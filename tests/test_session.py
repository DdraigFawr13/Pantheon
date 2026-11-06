"""`pantheon session`: Claude Code as narrator, one step per command (D-041)."""

import json
from pathlib import Path
from typing import Any

import pytest

from pantheon.engine.state import xp_to_next
from pantheon.storage.db import Database, EventRecord
from pantheon.ui.cli.app import main

SUGGEST = json.dumps(
    {
        "actions": [
            {"label": "Ask the voice what it wants"},
            {"label": "Bargain for time", "cost": "it may remember"},
            {
                "label": "Climb the broken stair",
                "check": {"stat": "agility", "difficulty": "hard", "challenge_tier": 0, "stakes": "a fall"},
            },
        ]
    }
)
CLIMB = json.dumps({"stat": "agility", "difficulty": "hard", "challenge_tier": 0, "stakes": "a fall"})


class Game:
    def __init__(self, tmp_path: Path, capsys: Any) -> None:
        self.db = tmp_path / "game.db"
        self.config = tmp_path / "none.toml"
        self.prose = tmp_path / "narration.md"
        self.capsys = capsys

    def __call__(self, *args: str) -> tuple[int, str]:
        self.capsys.readouterr()
        code = main(["session", "--db", str(self.db), "--config", str(self.config), *args])
        return code, self.capsys.readouterr().out

    def narrate(self, text: str) -> tuple[int, str]:
        self.prose.write_text(text, encoding="utf-8")
        return self("narrate", str(self.prose))

    def state(self) -> Any:
        with Database.open(self.db) as db:
            tid = db.latest_timeline()
            assert tid is not None
            return db.load_state(tid), db.last_turn(tid)

    def create(self, seed: int = 0) -> None:
        code, out = self(
            "create",
            "--name",
            "Wren",
            "--people",
            "saltborn",
            "--origin",
            "toll_ferry_orphan",
            "--seed",
            str(seed),
        )
        assert code == 0, out
        assert "Next: `session begin`" in out

    def opening(self, *, create: bool = True, seed: int = 0) -> None:
        if create:
            self.create(seed)
        assert self("begin")[0] == 0
        assert self.narrate("The Stair gave way. Two voices spoke out of the dark at once.")[0] == 0
        assert self("tool", "suggest_actions", SUGGEST)[0] == 0
        assert self("commit")[0] == 0

    def sworn(self, seed: int = 0) -> None:
        self.opening(seed=seed)
        state, _ = self.state()
        code, out = self("choose", "offer", state.opening_gods[0])
        assert code == 0, out
        assert "Next: `session begin" in out
        assert self("choose", "class", "wayfinder")[0] == 0
        assert self("choose", "profession", "hunter")[0] == 0

    def aftermath(self) -> None:
        """A talking turn after the Oath, whose options can carry checks."""
        self.sworn()
        assert self("begin", "[I swear. Narrate the aftermath.]")[0] == 0
        assert self.narrate("The Ledger opened in Wren's head like a door left ajar.")[0] == 0
        assert self("tool", "suggest_actions", SUGGEST)[0] == 0
        assert self("commit")[0] == 0


@pytest.fixture
def game(tmp_path: Path, capsys: Any) -> Game:
    return Game(tmp_path, capsys)


def test_session_plays_the_opening_and_saves_only_on_commit(game: Game) -> None:
    game.create()
    code, out = game("begin")
    assert code == 0
    assert "Open with The Dual Offer" in out and "write the prose" in out.lower()
    assert game.state()[1] == 0  # Nothing is saved before commit (OPS-03).
    assert game.narrate("The Stair fell. Two voices spoke out of the dark at once.")[0] == 0
    code, out = game("commit")
    assert code == 1 and "suggest_actions" in out  # The player always gets options (NAR-03).
    code, out = game("tool", "suggest_actions", SUGGEST)
    assert "Options recorded" in out
    code, out = game("commit")
    assert code == 0
    assert "Swear the" in out and "session choose offer" in out and "Refuse both gods" in out
    state, turn = game.state()
    assert turn == 1 and len(state.suggested) == 3


def test_session_prose_with_an_invented_number_is_not_accepted_NAR_04(game: Game) -> None:
    game.create()
    game("begin")
    code, out = game.narrate("The Stair gave way with a sound like 99 bells.")
    assert "Not accepted: the number 99 did not come from the engine" in out
    code, out = game("tool", "suggest_actions", SUGGEST)
    assert code == 1 and "not available now" in out  # Prose comes first (D-031).


def test_session_check_rolls_before_prose_and_replays_the_same_dice_ENG_04(game: Game) -> None:
    game.sworn()
    code, out = game("begin", "I climb the slick wall")
    assert "request_check" in out
    code, out = game("tool", "request_check", CLIMB)
    assert code == 0
    first_roll = json.loads(out.split("\n")[0])
    assert first_roll["status"] == "accepted"
    assert "Narrate exactly that result" in out
    code, out = game.narrate("Wren climbed.")
    assert "<<CHECK>>" in out  # The dice are printed where the result lands (D-036).
    code, out = game.narrate("Wren set her fingers to the stone.\n\n<<CHECK>>\n\nShe kept going.")
    assert "Prose accepted" in out
    game("tool", "grant_xp", json.dumps({"kind": "minor", "reason": "the climb"}))
    game("tool", "suggest_actions", SUGGEST)
    code, out = game("commit")
    assert code == 0
    assert f"{first_roll['outcome'].replace('_', ' ')}***" in out
    with Database.open(game.db) as db:
        tid = db.latest_timeline()
        assert tid is not None
        checks = [e for e in db.events(tid) if e["type"] == "check_resolved"]
    assert len(checks) == 1 and checks[0]["payload"]["outcome"] == first_roll["outcome"]


def test_session_option_rolls_the_check_the_player_saw_D_036(game: Game) -> None:
    game.aftermath()
    code, out = game("begin", "--option", "3")
    assert code == 0
    assert "Engine check" in out and "Climb the broken stair" in out
    code, out = game("tool", "request_check", CLIMB)
    assert code == 1  # The chosen option already rolled; the referee step is over.
    assert game("begin", "again")[0] == 1  # One turn at a time.
    assert "dropped" in game("abandon")[1]
    assert game("begin", "--option", "9")[0] == 1


def test_session_tool_rejections_change_nothing_NAR_06(game: Game) -> None:
    game.create()
    game("begin")
    game.narrate("The Stair gave way, and the dark answered with two voices.")
    code, out = game("tool", "suggest_actions", "{not json")
    assert code == 1 and "not JSON" in out
    code, out = game("tool", "suggest_actions", json.dumps({"actions": []}))
    assert "Rejected" in out
    code, out = game.narrate("Again.")
    assert code == 1 and "already has its prose" in out
    assert game.state()[1] == 0  # Nothing was saved (NAR-06).
    assert game.state()[0].suggested == []


def test_session_waits_for_the_players_own_choices(game: Game) -> None:
    game.opening()
    state, _ = game.state()
    game("choose", "offer", state.opening_gods[0])
    code, out = game("begin", "I look around")
    assert code == 1 and "must choose first" in out
    code, out = game("status")
    assert "must choose first" in out and "class:" in out
    assert game("choose", "class", "nonsense")[0] == 1
    assert game("choose", "colour", "red")[0] == 1


def test_session_status_sheet_hooks_inspect_prompt_tools_and_setup(game: Game) -> None:
    assert "No character yet" in game("status")[1]
    assert "origin toll_ferry_orphan" in game("setup")[1]
    game.create()
    assert "opening has not been played" in game("status")[1]
    game("begin")
    code, out = game("status")
    assert "Turn 1 is in progress" in out
    game("abandon")
    game.opening(create=False)
    assert "Swear the" in game("status")[1]
    assert "Wren" in game("sheet")[1]
    assert "Debt" in game("hooks")[1]
    assert "Climb the broken stair" in game("inspect", "3")[1]
    code, out = game("prompt")
    assert code == 0 and "narrator" in out.lower()
    code, out = game("tools")
    assert '"request_check"' in out
    assert game("trial")[0] == 1  # No Trial is due.
    code, out = game("create", "--name", "Ash", "--people", "saltborn", "--origin", "toll_ferry_orphan")
    assert code == 1 and "--fresh" in out


def test_session_create_validates_its_arguments(game: Game) -> None:
    args = ["create", "--name", "Wren", "--people", "saltborn", "--origin", "toll_ferry_orphan"]
    assert game(*args, "--stats", "a a a a a")[0] == 1
    code, _out = game("create", "--name", "Wren", "--people", "humans", "--origin", "nowhere")
    assert code == 1


def test_session_turn_is_dropped_when_the_save_moves_on(game: Game) -> None:
    game.create()
    game("begin")
    pending = game.db.with_name("game.turn.json")
    data = json.loads(pending.read_text(encoding="utf-8"))
    pending.write_text(json.dumps({**data, "turn": 5}), encoding="utf-8")
    code, out = game("commit")
    assert code == 1 and "abandon" in out


def test_session_export_and_import_keep_the_old_save_GAME_05(game: Game, tmp_path: Path) -> None:
    game.opening()
    dump = tmp_path / "save.sql"
    assert game("export", str(dump))[0] == 0
    before = game.state()
    code, out = game("import", str(dump))
    assert code == 0 and ".bak" in out
    assert game.state()[1] == before[1]
    assert list(tmp_path.glob("game.db.*.bak"))


def test_session_start_and_stop_switch_the_play_guard(game: Game) -> None:
    marker = game.db.parent / ".playing"
    assert game("start")[0] == 0
    assert marker.exists()
    assert game("stop")[0] == 0
    assert not marker.exists()


def test_session_screen_is_plain_data_for_the_game_page(game: Game, tmp_path: Path) -> None:
    game.opening()
    out = tmp_path / "screen.json"
    assert game("screen", str(out))[0] == 0
    screen = json.loads(out.read_text(encoding="utf-8"))
    assert screen["turn"] == 1 and screen["name"] == "Wren"
    assert screen["prose"] and not screen["in_progress"]
    assert [o["n"] for o in screen["options"]] == [1, 2, 3]
    assert [o["n"] for o in screen["offers"]] == [4, 5, 6]
    assert all("[" not in line for line in screen["ledger"])  # No terminal markup reaches the page.


def test_session_screen_offers_creation_and_then_a_full_sheet(game: Game, tmp_path: Path) -> None:
    out = tmp_path / "screen.json"
    game("screen", str(out))
    setup = json.loads(out.read_text(encoding="utf-8"))
    assert setup["created"] is False
    assert {p["id"] for p in setup["setup"]["peoples"]} >= {"saltborn", "humans"}
    assert setup["setup"]["stat_array"] and setup["setup"]["origins"]
    game.sworn()
    game("screen", str(out))
    screen = json.loads(out.read_text(encoding="utf-8"))
    assert screen["created"] is True and screen["origin_name"] == "Toll-ferry orphan"
    assert screen["oath_list"][0]["burden"] and screen["skill_list"][0]["name"] == "Streetwise"
    assert screen["class_stats"]


def test_session_screen_uses_names_a_player_reads(game: Game, tmp_path: Path) -> None:
    game.opening()
    state, _ = game.state()
    game("choose", "offer", state.opening_gods[0])
    out = tmp_path / "screen.json"
    game("screen", str(out))
    screen = json.loads(out.read_text(encoding="utf-8"))
    kinds = [g["kind"] for g in screen["choice_groups"]]
    assert kinds == ["class", "profession"]  # Both asked at once.
    assert screen["choice_groups"][0]["options"][0]["name"][0].isupper()
    assert all(o["blurb"] and o["trait"] for o in screen["choice_groups"][0]["options"])
    assert len(screen["class_catalogue"]) == len(screen["choice_groups"][0]["options"])
    assert not any("_" in line for line in screen["ledger"])
    assert any("Oath sworn" in line for line in screen["ledger"])


TRIAL_SEED = 1  # A seed whose Trial roll ascends, so the free-point path runs.


def ready_for_trial(game: Game) -> None:
    """Level 10 with full XP, committed to the save as the engine would (as in test_play)."""
    game.sworn(TRIAL_SEED)
    events: list[EventRecord] = [
        ("level_up", {"level": 10, "xp_spent": 0, "gains": {}, "free_points": 0}),
        ("xp_gained", {"amount": xp_to_next(10), "kind": "milestone", "reason": "a long road"}),
    ]
    with Database.open(game.db) as db:
        tid = db.latest_timeline()
        assert tid is not None
        db.commit_events(tid, db.last_turn(tid) + 1, events, db.rng_state(tid))


def test_d031_session_trial_is_saved_before_any_prose_and_then_the_point_is_placed(game: Game) -> None:
    ready_for_trial(game)
    turn_before = game.state()[1]
    code, out = game("trial")
    assert code == 0, out
    state, turn = game.state()
    assert state.checks_made == 1  # The roll stands, saved before the narrator wrote a word.
    assert turn == turn_before  # A command spends no narrated turn.
    assert not game.db.with_name("game.turn.json").exists()
    assert "Ascension Trial" in out and "Next: `session begin" in out
    assert state.level == 11 and state.free_points > 0
    assert "point" in game("status")[1]  # The free point waits for the player.
    stat = "resolve"
    before = state.stats[stat]
    code, out = game("choose", "point", stat)
    assert code == 0, out
    assert game.state()[0].stats[stat] == before + 1
    assert game("choose", "point", "luck")[0] == 1


def test_d031_session_trial_is_refused_when_none_is_due(game: Game) -> None:
    game.sworn()
    code, out = game("trial")
    assert code == 1 and "no Ascension Trial is due" in out
    assert game.state()[0].checks_made == 0


def _create_args(**overrides: str) -> list[str]:
    args = {"name": "Wren", "people": "saltborn", "origin": "toll_ferry_orphan", **overrides}
    return ["create", *(x for k, v in args.items() for x in (f"--{k}", v))]


def _prep_nothing(game: Game) -> None:
    pass


def _prep_bad_create(game: Game) -> None:
    assert game(*_create_args(age="15"))[0] == 1


def _prep_begun(game: Game) -> None:
    game.create()
    assert game("begin")[0] == 0


def _prep_played_opening(game: Game) -> None:
    game.opening()


@pytest.mark.parametrize(
    ("prep", "step", "message"),
    [
        (_prep_nothing, ["commit"], "No turn is in progress"),
        (_prep_nothing, ["begin"], "There is no game yet"),
        (_prep_bad_create, ["begin"], "Create the character first"),
        (_prep_begun, ["commit"], "Write and `narrate` the prose before committing"),
        (_prep_played_opening, ["begin"], "Say what the player does"),
    ],
)
def test_session_step_errors_guide_the_narrator(game: Game, prep: Any, step: list[str], message: str) -> None:
    prep(game)
    code, out = game(*step)
    assert code == 1
    assert message in " ".join(out.split())


def test_session_an_invalid_create_says_why_and_saves_no_character(game: Game) -> None:
    code, out = game(*_create_args(age="15"))
    assert code == 1 and "Character not created" in " ".join(out.split())
    assert "No character yet" in game("status")[1]


def test_wld02_playing_never_writes_to_world(game: Game) -> None:
    world = Path(__file__).resolve().parents[1] / "world"
    public = [p for p in world.rglob("*") if p.is_file() and not {"secret", "sealed"} & set(p.parts)]

    def fingerprint() -> dict[str, tuple[int, bytes]]:
        return {str(p): (p.stat().st_mtime_ns, p.read_bytes()) for p in public}

    before = fingerprint()
    game.sworn()
    state, _ = game.state()
    assert state.oaths  # A real turn ran: an Oath was sworn and saved.
    assert fingerprint() == before
