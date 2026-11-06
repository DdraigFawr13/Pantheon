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


# A fixed seed: `--seed 0` means "draw a random one", which made these tests roll new dice every run.
SEED = 42


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

    def create(self, seed: int = SEED) -> None:
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

    def opening(self, *, create: bool = True, seed: int = SEED) -> None:
        if create:
            self.create(seed)
        assert self("begin")[0] == 0
        assert self.narrate("The Stair gave way. Two voices spoke out of the dark at once.")[0] == 0
        assert self("tool", "suggest_actions", SUGGEST)[0] == 0
        assert self("commit")[0] == 0

    def sworn(self, seed: int = SEED) -> None:
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
        assert (
            self.narrate("The Ledger opened in Wren's head. The stair was there to climb <<ODDS 3>>.")[0] == 0
        )
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
    assert code == 0 and "Preview: Agility check, hard" in out  # A typed action shows its odds first (D-050).
    code, out = game("go")
    assert code == 0
    first_roll = json.loads(out.split("Engine check: ")[1].split("\n")[0])
    assert "Narrate exactly that result" in out
    code, out = game.narrate("Wren climbed.")
    assert "<<CHECK>>" in out  # The dice are printed where the result lands (D-036).
    code, out = game.narrate("Wren set her fingers to the stone.\n\n<<CHECK>>\n\nShe kept going.")
    assert "Prose accepted" in out
    game("tool", "grant_xp", json.dumps({"kind": "minor", "reason": "the climb"}))
    game("tool", "suggest_actions", SUGGEST)
    code, out = game("commit")
    assert code == 0
    outcome = first_roll["outcome"].replace("_", " ") + (
        " + complication" if first_roll["complication"] else ""
    )
    assert f"{outcome}***" in out
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
    assert code == 0 and "Prose replaced" in out  # Prose may be rewritten until commit (D-050).
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
    assert screen["options"] == []  # No option list outside a fight (D-050); the scene names the approaches.
    assert [o["n"] for o in screen["offers"]] == [1, 2, 3]  # Numbered from 1 with no list (D-053).
    assert screen["preview"] is None
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


FIGHT_SUGGEST = json.dumps(
    {
        "actions": [
            {"label": "Drive the hound back", "fight": {"move": "attack", "stat": "vigor", "target": "f1"}},
            {
                "label": "Brace behind the rail",
                "cost": "it may circle",
                "fight": {"move": "guard", "stat": "resolve"},
            },
            {"label": "Shout for the ferryman"},
        ]
    }
)


def _start_a_fight(game: Game, tmp_path: Path) -> None:
    game.aftermath()
    assert game("begin", "I step out to meet whatever is growling")[0] == 0
    assert game.narrate("An ash hound came up the bank, low and quiet.")[0] == 0
    foes = tmp_path / "tool.json"
    foes.write_text(
        json.dumps({"foes": [{"name": "Ash Hound", "tier": 0, "threat": "standard"}], "reason": "it lunges"}),
        encoding="utf-8",
    )
    code, out = game("tool", "start_fight", "--file", str(foes))
    assert code == 0 and "Rejected" not in out, out
    code, out = game("tool", "suggest_actions", FIGHT_SUGGEST)
    assert code == 0 and "Rejected" not in out, out
    code, out = game("commit")
    assert code == 0 and "Exchange 1" in out and "Ash Hound" in out, out


def test_session_fight_option_rolls_the_exchange_before_prose_D_039(game: Game, tmp_path: Path) -> None:
    _start_a_fight(game, tmp_path)
    code, out = game("begin", "--option", "1")
    assert code == 0, out
    assert "Engine check:" in out and "Engine fight:" in out
    replayed = game("status")[1]
    assert out.split("Engine fight:")[1].split("\n")[0] in replayed  # The same dice on every step.
    assert "request_check" not in game("tools")[1]
    assert game.narrate("Wren swung.\n<<CHECK>>\nThe hound reeled.")[0] == 0
    state, _ = game.state()
    over = "The fight is over." in replayed  # The pending turn's exchange, as the engine summed it up.
    code, out = game("tool", "suggest_actions", SUGGEST if over else FIGHT_SUGGEST)
    assert code == 0 and "Rejected" not in out, out
    assert game("commit")[0] == 0
    state, _ = game.state()
    assert state.checks_made >= 1 and (state.fight is None) == over


def test_session_in_a_fight_the_referee_offers_fight_move_not_request_check(
    game: Game, tmp_path: Path
) -> None:
    _start_a_fight(game, tmp_path)
    code, out = game("begin", "I kick sand in its eyes")
    assert code == 0 and "fight_move" in out, out
    code, out = game("tool", "request_check", CLIMB)
    assert code == 1 and "not available" in out
    move = tmp_path / "move.json"
    move.write_text(json.dumps({"move": "guard", "stat": "agility"}), encoding="utf-8")
    code, out = game("tool", "fight_move", "--file", str(move))
    assert code == 0 and "summary" in out, out


def test_session_downed_turn_runs_the_foes_exchange_on_its_own_D_039(game: Game, tmp_path: Path) -> None:
    _start_a_fight(game, tmp_path)
    with Database.open(game.db) as db:
        tid = db.latest_timeline()
        assert tid is not None
        state = db.load_state(tid)
        db.commit_events(
            tid,
            db.last_turn(tid) + 1,
            [
                (
                    "effect_applied",
                    {"kind": "damage", "amount": state.hp, "source": "exchange", "reason": "x"},
                ),
                ("downed", {"reason": "x"}),
            ],
            db.rng_state(tid),
        )
    code, out = game("begin", "I try to crawl away")
    assert code == 0, out
    assert "Last Breath 1" in out and "Downed" in out
    assert "fight_move" not in out.split("Step:")[1]


def test_session_screen_shows_the_fight_and_its_intents(game: Game, tmp_path: Path) -> None:
    _start_a_fight(game, tmp_path)
    page = tmp_path / "screen.json"
    assert game("screen", str(page))[0] == 0
    data = json.loads(page.read_text(encoding="utf-8"))
    assert data["fight"]["exchange"] == 1
    assert data["fight"]["foes"][0]["name"] == "Ash Hound" and data["fight"]["foes"][0]["intent"]
    assert {"mana", "stamina", "trait", "attunement"} <= set(data)


def test_session_gear_commands_and_the_gear_on_screen_D_045(game: Game, tmp_path: Path) -> None:
    game.aftermath()
    with Database.open(game.db) as db:
        tid = db.latest_timeline()
        assert tid is not None
        db.commit_events(
            tid,
            db.last_turn(tid) + 1,
            [("item_changed", {"item": "dagger", "quantity": 1, "reason": "found"})],
            db.rng_state(tid),
        )
    code, out = game("equip", "dagger")
    assert code == 0 and "Equipped: dagger" in out, out
    code, out = game("use", "dagger")
    assert code == 1 and "not something to use up" in out
    page = tmp_path / "screen.json"
    assert game("screen", str(page))[0] == 0
    gear = json.loads(page.read_text(encoding="utf-8"))["gear"]
    assert gear == [
        {
            "id": "dagger",
            "name": "Dagger",
            "kind": "weapon",
            "count": 1,
            "in_use": True,
            "detail": "+5 on attacks, worth 3 sp",
        }
    ]
    assert "Dagger (in use)" in game("sheet")[1]
    assert game("unequip", "weapon")[0] == 0


def test_session_screen_codex_lists_knowledge_and_foes_met(game: Game, tmp_path: Path) -> None:
    _start_a_fight(game, tmp_path)
    page = tmp_path / "screen.json"
    assert game("screen", str(page))[0] == 0
    codex = json.loads(page.read_text(encoding="utf-8"))["codex"]
    assert len(codex["classes"]) == 25 and sum(c["current"] for c in codex["classes"]) == 1
    assert {p["name"] for p in codex["peoples"]} >= {"Humans", "Saltborn"}
    assert len(codex["gods"]) == 7 and sum(g["sworn"] for g in codex["gods"]) == 1
    assert all(g["oaths"] for g in codex["gods"])
    assert codex["bestiary"] == [{"name": "Ash Hound", "tier": 0, "threat": "standard", "met": 1, "down": 0}]


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


# D-050: odds without an option menu. A typed action that rolls is previewed first; the scene's closing
# thought carries the odds of the approaches the narrator marks; nothing rolls at odds the player did not see.


def test_d050_a_typed_risky_action_shows_its_odds_before_it_rolls(game: Game) -> None:
    game.sworn()
    game("begin", "I climb the slick wall")
    code, out = game("tool", "request_check", CLIMB)
    assert code == 0
    assert "Preview" in out and "Agility check, hard" in out and "%" in out
    shown = int(out.split("Agility check, hard: ")[1].split("%")[0])
    with Database.open(game.db) as db:
        tid = db.latest_timeline()
        assert tid is not None
        assert not [e for e in db.events(tid) if e["type"] == "check_resolved"]  # Nothing rolled yet.
    code, out = game("go")
    assert code == 0
    engine = json.loads(out.split("Engine check: ")[1].split("\n")[0])
    assert engine["chance"] == shown  # The roll uses exactly the previewed odds (D-036).


def test_d050_backing_off_rolls_nothing_and_rewording_keeps_the_odds(game: Game) -> None:
    game.sworn()
    game("begin", "I climb the slick wall")
    _, first = game("tool", "request_check", CLIMB)
    assert game("abandon")[0] == 0
    game("begin", "I scale the wall, carefully this time")
    easier = json.dumps({"stat": "agility", "difficulty": "routine", "challenge_tier": 0, "stakes": "a fall"})
    _, second = game("tool", "request_check", easier)
    assert "Agility check, hard" in second  # Same stat this turn: the first preview's odds hold.
    assert first.split("Preview: ")[1].split("\n")[0] == second.split("Preview: ")[1].split("\n")[0]
    talk = json.dumps(
        {"stat": "presence", "difficulty": "routine", "challenge_tier": 0, "stakes": "a refusal"}
    )
    assert game("abandon")[0] == 0
    game("begin", "I talk the guard into lending me a rope")
    _, third = game("tool", "request_check", talk)
    assert "Preview" not in third and "Engine check" in third  # A different approach gets its own odds,
    # and a Routine one rolls at once (D-051).


def test_d050_the_closing_thought_carries_the_odds_and_there_is_no_menu(game: Game) -> None:
    game.sworn()
    game("begin", "[I swear. Narrate the aftermath.]")
    game.narrate("Wren could climb the broken stair <<ODDS 3>> or ask the voice what it wanted <<ODDS 1>>.")
    game("tool", "suggest_actions", SUGGEST)
    code, out = game("commit")
    assert code == 0
    assert "<<ODDS" not in out
    assert "climb the broken stair (Agility " in out and "% )" not in out
    assert "ask the voice what it wanted (no roll)" in out
    assert "  1. " not in out and "Climb the broken stair" not in out.split("ask the voice")[1]  # No menu.
    code, out = game("begin", "--option", "3")
    assert "Engine check" in out  # Its odds were in the scene, so it rolls at once.


def test_d050_an_approach_whose_odds_were_not_shown_is_previewed_first(game: Game) -> None:
    game.sworn()
    game("begin", "[I swear. Narrate the aftermath.]")
    game.narrate("The Ledger opened in Wren's head like a door left ajar.")  # It marks no approach.
    game("tool", "suggest_actions", SUGGEST)
    assert game("commit")[0] == 0
    code, out = game("begin", "--option", "3")
    assert code == 0
    assert "Engine check" not in out and "Preview" in out and "Agility check, hard" in out


def test_nar08_a_routine_typed_check_rolls_at_once_with_its_odds(game: Game) -> None:
    game.sworn()
    game("begin", "I step over the low fence")
    easy = json.dumps({"stat": "agility", "difficulty": "routine", "challenge_tier": 0, "stakes": "a trip"})
    code, out = game("tool", "request_check", easy)
    assert code == 0
    assert "Preview" not in out  # Only Hard checks or harder wait for the player (D-051).
    engine = json.loads(out.split("Engine check: ")[1].split("\n")[0])
    assert engine["chance"] > 0 and "roll" in engine  # The notice still shows the chance and the roll.
    code, out = game("go")
    assert code == 1 and "No preview is waiting" in out


def test_nar08_a_routine_approach_whose_odds_were_not_shown_rolls_at_once(game: Game) -> None:
    routine = json.loads(SUGGEST)
    routine["actions"][2]["check"]["difficulty"] = "routine"
    game.sworn()
    game("begin", "[I swear. Narrate the aftermath.]")
    game.narrate("The Ledger opened in Wren's head like a door left ajar.")  # It marks no approach.
    game("tool", "suggest_actions", json.dumps(routine))
    assert game("commit")[0] == 0
    code, out = game("begin", "--option", "3")
    assert code == 0
    assert "Preview" not in out and "Engine check" in out


def test_d050_a_marker_for_a_missing_approach_is_refused_at_commit(game: Game) -> None:
    game.sworn()
    game("begin", "[I swear. Narrate the aftermath.]")
    game.narrate("Wren could climb <<ODDS 9>>.")
    game("tool", "suggest_actions", SUGGEST)
    code, out = game("commit")
    assert code == 1 and "<<ODDS 9>>" in out
    game.narrate("Wren could climb the broken stair <<ODDS 3>>.")  # Prose can be replaced before commit.
    assert game("commit")[0] == 0


def test_d050_the_game_page_gets_the_preview(game: Game, tmp_path: Path) -> None:
    game.sworn()
    game("begin", "I climb the slick wall")
    game("tool", "request_check", CLIMB)
    out = tmp_path / "screen.json"
    game("screen", str(out))
    screen = json.loads(out.read_text(encoding="utf-8"))
    assert screen["preview"]["text"].startswith("Agility check, hard: ")
    assert screen["preview"]["stakes"] == "a fall"
    assert screen["options"] == []  # Outside a fight, no option list (D-050).


def _rolled_turn(game: Game) -> None:
    """A sworn turn whose Hard climb has rolled, ready for prose."""
    game.sworn()
    assert game("begin", "I climb the slick wall")[0] == 0
    assert game("tool", "request_check", CLIMB)[0] == 0
    assert game("go")[0] == 0


def _events(game: Game, kind: str) -> list[dict[str, Any]]:
    with Database.open(game.db) as db:
        tid = db.latest_timeline()
        assert tid is not None
        return [e["payload"] for e in db.events(tid) if e["type"] == kind]


def test_nar06_session_drops_a_tool_after_its_two_retries(game: Game) -> None:
    _rolled_turn(game)
    assert "Prose accepted" in game.narrate("Wren climbed.\n\n<<CHECK>>\n\nThe wall held.")[1]
    bad = json.dumps({"kind": "enormous", "reason": "the climb"})
    assert "Rejected (2 retries left)" in game("tool", "grant_xp", bad)[1]
    assert "Rejected (1 retry left)" in game("tool", "grant_xp", bad)[1]
    assert "grant_xp is dropped for this turn" in game("tool", "grant_xp", bad)[1]
    out = game("tool", "grant_xp", json.dumps({"kind": "minor", "reason": "the climb"}))[1]
    assert "dropped for this turn" in out  # Not applied after the drop, even when valid.
    game("tool", "suggest_actions", SUGGEST)
    assert game("commit")[0] == 0
    assert [p["tool"] for p in _events(game, "tool_call_dropped")] == ["grant_xp"]
    assert game.state()[0].xp == 0  # The dropped call was never applied.


def test_nar06_session_commits_without_suggestions_when_suggest_actions_is_dropped(game: Game) -> None:
    _rolled_turn(game)
    game.narrate("Wren climbed.\n\n<<CHECK>>\n\nShe could go higher <<ODDS 3>>.")
    for _ in range(3):
        game("tool", "suggest_actions", json.dumps({"actions": []}))
    code, out = game("commit")
    assert code == 0, out
    state, turn = game.state()
    assert turn == 2 and state.suggested == []
    assert [p["tool"] for p in _events(game, "tool_call_dropped")] == ["suggest_actions"]
    with Database.open(game.db) as db:
        tid = db.latest_timeline()
        assert tid is not None
        assert "<<ODDS" not in db.recent_turns(tid, 1)[0][1]


def test_nar07_session_commits_a_fallback_turn_after_three_rejected_narrations(game: Game) -> None:
    _rolled_turn(game)
    before = game.state()[0].suggested
    for attempt in range(3):
        if attempt:
            assert game("commit")[0] == 1  # Not yet: the narrator still has a retry.
        game.narrate("Wren climbed 99 feet.\n\n<<CHECK>>")
    code, out = game("commit")
    assert code == 0, out
    state, turn = game.state()
    assert state.suggested == before  # The previous suggestions stay (NAR-07).
    with Database.open(game.db) as db:
        tid = db.latest_timeline()
        assert tid is not None
        row = db.conn.execute(
            "SELECT narration, is_fallback FROM turn WHERE timeline_id = ? AND turn = ?", (tid, turn)
        ).fetchone()
    assert row[1] == 1 and "99" not in row[0] and "a fall:" in row[0]
    assert len(_events(game, "check_resolved")) == 1


def test_nar07_session_prose_accepted_after_three_refusals_still_commits_normally(game: Game) -> None:
    _rolled_turn(game)
    for _ in range(3):
        game.narrate("Wren climbed 99 feet.\n\n<<CHECK>>")
    assert "Prose accepted" in game.narrate("Wren climbed.\n\n<<CHECK>>\n\nThe wall held.")[1]
    game("tool", "suggest_actions", SUGGEST)
    assert game("commit")[0] == 0
    with Database.open(game.db) as db:
        tid = db.latest_timeline()
        assert tid is not None
        row = db.conn.execute(
            "SELECT is_fallback FROM turn WHERE timeline_id = ? ORDER BY turn DESC LIMIT 1", (tid,)
        ).fetchone()
    assert row[0] == 0


def test_nar08_session_a_refused_check_does_not_fix_its_stats_terms(game: Game) -> None:
    game.sworn()
    game("begin", "I climb the slick wall")
    bad = json.loads(CLIMB) | {"challenge_tier": 99}
    assert "Rejected" in game("tool", "request_check", json.dumps(bad))[1]
    routine = json.loads(CLIMB) | {"difficulty": "routine"}
    code, out = game("tool", "request_check", json.dumps(routine))
    assert code == 0 and "Preview:" not in out and "Engine check" in out  # Rolled at once (D-051).


def test_nar08_session_commit_waits_for_an_unanswered_preview(game: Game) -> None:
    game.sworn()
    game("begin", "I climb the slick wall")
    for _ in range(3):
        game.narrate("Wren climbed 99 feet.")
    assert "Preview:" in game("tool", "request_check", CLIMB)[1]
    code, out = game("commit")
    assert code == 1 and "session go" in out


def test_nar06_session_a_json_error_drop_keeps_the_raw_arguments(game: Game) -> None:
    _rolled_turn(game)
    game.narrate("Wren climbed.\n\n<<CHECK>>\n\nThe wall held.")
    for _ in range(3):
        game("tool", "grant_xp", "{not json")
    game("tool", "suggest_actions", SUGGEST)
    assert game("commit")[0] == 0
    assert [p["args"] for p in _events(game, "tool_call_dropped")] == [{"raw": "{not json"}]


def test_session_screen_cast_and_places(game: Game, tmp_path: Path) -> None:
    game.aftermath()
    page = tmp_path / "screen.json"
    assert game("screen", str(page))[0] == 0
    empty = json.loads(page.read_text(encoding="utf-8"))
    assert empty["cast"] == [] and empty["places"] == []
    game("begin", "I go down to the water")
    assert game.narrate("A rifter waved from the cellar door, and the stair gave onto the water.")[0] == 0
    npc = '{"name": "Tam", "role": "rifter", "tier": 1, "disposition": "wary"}'
    place = '{"name": "The Drowned Cellar", "region": "ford_reaches", "description": "A flooded cellar."}'
    code, out = game("tool", "introduce_npc", npc)
    assert code == 0, out
    assert game("tool", "introduce_location", place)[0] == 0
    assert game("tool", "suggest_actions", SUGGEST)[0] == 0
    assert game("commit")[0] == 0
    assert game("screen", str(page))[0] == 0
    screen = json.loads(page.read_text(encoding="utf-8"))
    turn = screen["turn"]
    assert screen["cast"] == [
        {"name": "Tam", "role": "rifter", "tier": 1, "disposition": "wary", "turn": turn}
    ]
    assert screen["places"] == [
        {
            "name": "The Drowned Cellar",
            "region": "The Ford Reaches",
            "description": "A flooded cellar.",
            "turn": turn,
        }
    ]
    assert any(line.startswith("Met: Tam") for line in screen["ledger"])
