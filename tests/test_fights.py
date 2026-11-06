"""A fight through the CLI, with scripted input and MockClient: the owner's path (D-039)."""

from pathlib import Path
from typing import Any

from pantheon.engine.state import GameState
from pantheon.llm.client import LLMReply, ToolCall
from pantheon.narrator.assemble import _due_material, state_view
from pantheon.storage.db import Database
from pantheon.ui.cli.app import _bar, ledger_lines
from tests.test_play import NEW_GAME, PROSE, WORLD, narration, play, talk

SWORN = [*NEW_GAME, "4", "1", "1"]
HOUND = {"name": "Ash Hound", "tier": 1, "threat": "minion"}
START = ToolCall("f", "start_fight", {"foes": [HOUND], "reason": "it lunges"})
FIGHT_ACTIONS = [
    {"label": "Go for the throat", "fight": {"move": "attack", "target": "f1", "stat": "agility"}},
    {"label": "Hold your guard", "fight": {"move": "guard", "stat": "vigor"}, "cost": "ground"},
    {"label": "Run", "fight": {"move": "flee", "stat": "agility"}},
]
ATTACK = ToolCall("m", "fight_move", {"move": "attack", "target": "f1", "stat": "agility"})


def opened(*script: list[LLMReply | None]) -> list[LLMReply | None]:
    """The opening, then the turn after swearing, then the given turns."""
    return [*talk(), *narration()[1:], *[reply for turn in script for reply in turn]]


def fight_turn(*calls: ToolCall, check: ToolCall | None = None) -> list[LLMReply | None]:
    referee = LLMReply(tool_calls=(check,)) if check else LLMReply(text="NONE")
    suggest = ToolCall("s", "suggest_actions", {"actions": FIGHT_ACTIONS})
    return [referee, narration()[1], LLMReply(tool_calls=(*calls, suggest))]


def test_a_fight_shows_intents_and_an_attack_runs_one_exchange(tmp_path: Path, capsys: Any) -> None:
    script = opened(narration(START), fight_turn(check=ATTACK))
    _, state, tid = play(tmp_path, [*SWORN, "I draw on it", "I strike", "/quit"], script)
    out = capsys.readouterr().out
    assert "A fight begins" in out
    assert "Exchange 1" in out
    assert "Ash Hound (Tier 1, 1 hit left) shows" in out
    with Database.open(tmp_path / "game.db") as db:
        types = [e["type"] for e in db.events(tid)]
    assert "check_resolved" in types
    assert types.count("exchange_ended") == 1
    assert state.checks_made == 1


def test_talk_in_a_fight_runs_no_exchange(tmp_path: Path) -> None:
    script = opened(narration(START), fight_turn())
    _, state, tid = play(tmp_path, [*SWORN, "I draw on it", "Who sent you?", "/quit"], script)
    assert state.fight is not None
    assert state.fight.exchange == 1
    with Database.open(tmp_path / "game.db") as db:
        assert "exchange_ended" not in [e["type"] for e in db.events(tid)]


def test_picking_a_suggested_move_rolls_it_without_a_referee(tmp_path: Path, capsys: Any) -> None:
    prose = LLMReply(text=f"{PROSE} The hound and the blade meet in the dust of the ford.")
    suggest = ToolCall("s", "suggest_actions", {"actions": FIGHT_ACTIONS})
    script = opened(fight_turn(START), [prose, LLMReply(tool_calls=(suggest,))])
    _, state, tid = play(tmp_path, [*SWORN, "I draw on it", "2", "/quit"], script)
    out = capsys.readouterr().out
    assert "[VIGOR" in out
    assert state.checks_made == 1
    with Database.open(tmp_path / "game.db") as db:
        check = next(e for e in db.events(tid) if e["type"] == "check_resolved")
    assert check["payload"]["stat"] == "vigor"


def downed_in_a_fight(tmp_path: Path) -> None:
    """Play into a fight, then put the blow that drops the character straight into the save."""
    _, state, tid = play(tmp_path, [*SWORN, "I draw on it", "/quit"], opened(narration(START)))
    with Database.open(tmp_path / "game.db") as db:
        blow = {"kind": "damage", "amount": state.hp, "source": "exchange", "reason": "a blow"}
        events = [("effect_applied", blow), ("downed", {"reason": "a blow"})]
        db.commit_events(tid, db.last_turn(tid) + 1, events, db.rng_state(tid))


def downed_turn() -> list[LLMReply | None]:
    """Prose, then actions: a Downed character's turn has no referee."""
    return narration()[1:]


def test_while_downed_any_input_runs_a_hostile_exchange_up_to_a_reckoning(
    tmp_path: Path, capsys: Any
) -> None:
    downed_in_a_fight(tmp_path)
    script = [*downed_turn(), *downed_turn(), *downed_turn()]
    _, state, _ = play(tmp_path, ["help!", "help!", "help!", "/quit"], script)
    out = capsys.readouterr().out
    assert "You are Downed" in out
    assert "Last Breath 1" in out
    assert "Reckoning 1" in out
    assert state.reckonings == 1
    assert state.hp == state.max_hp
    assert state.fight is None


def test_a_downed_characters_suggested_moves_become_plain_options(tmp_path: Path) -> None:
    downed_in_a_fight(tmp_path)
    prose = narration()[1]
    suggest = LLMReply(tool_calls=(ToolCall("s", "suggest_actions", {"actions": FIGHT_ACTIONS}),))
    _, state, _ = play(tmp_path, ["help!", "/quit"], [prose, suggest])
    assert len(state.suggested) == 3
    assert all(a.check is None for a in state.suggested)


def test_a_final_death_ends_the_session_and_the_narrator_records_nothing(tmp_path: Path, capsys: Any) -> None:
    (tmp_path / "none.toml").write_text("[gameplay]\npermadeath = true\n", encoding="utf-8")
    downed_in_a_fight(tmp_path)
    last = LLMReply(text=f"{PROSE} The light went out of the world and did not come back.")
    script = [*downed_turn(), *downed_turn(), last]
    lines = ["help!", "help!", "help!", "typed after death"]
    _, state, _ = play(tmp_path, lines, script)
    out = capsys.readouterr().out
    assert state.dead
    assert "This death is final" in out
    assert "This character is dead" in out
    _, state, _ = play(tmp_path, ["never asked"], [])
    assert state.dead
    assert "This character is dead" in capsys.readouterr().out


def test_narrator_sees_pools_and_the_fight() -> None:
    state = GameState(mana_spent=3, stats={"intellect": 10})
    assert state_view(state)["mana"] == 17
    state.fight = None
    assert "fight" not in _due_material(state, WORLD)
    state = GameState.model_validate(
        {
            "fight": {
                "foes": [
                    {
                        "id": "f1",
                        "name": "Ash Hound",
                        "tier": 1,
                        "threat": "minion",
                        "hits_left": 1,
                        "intent": "heavy",
                    },
                    {
                        "id": "f2",
                        "name": "Gone",
                        "tier": 1,
                        "threat": "minion",
                        "hits_left": 0,
                        "intent": "heavy",
                    },
                ],
                "exchange": 2,
            }
        }
    )
    due = _due_material(state, WORLD)
    assert "A fight is on, exchange 2" in due
    assert "f1: Ash Hound, Tier 1, minion, shows a heavy blow, plain to see" in due
    assert "Gone" not in due


def test_an_overspent_pool_draws_an_empty_bar() -> None:
    assert _bar("Mana", -5, 20).count("█") == 0
    assert "-5/20" in _bar("Mana", -5, 20)


def test_ledger_shows_the_fight() -> None:
    lines = ledger_lines(
        [
            ("foe_hit", {"foe": "f1", "name": "Hound", "hits": 2}),
            ("foe_hit", {"foe": "f1", "name": "Hound", "hits": 1}),
            ("overspend_rolled", {"skill": "bolt", "percent": 10, "chance": 20, "roll": 7}),
            ("fight_ended", {"result": "fled"}),
            ("level_lost", {"level": 2, "losses": {}}),
        ]
    )
    assert lines == [
        "Hound takes 2 hits",
        "Hound takes 1 hit",
        "Overspent bolt: 20% Injury risk, rolled 7",
        "[bold]The fight ends:[/bold] you got away",
        "[red]Level lost: now Level 2[/red]",
    ]
