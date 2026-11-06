"""M2b acceptance: ten scripted turns on each play path, checking NAR-04, NAR-06 and NAR-07 (D-052 (8)).

`pantheon play` runs against `MockClient` with scripted player input; session play runs the narrator's
commands one by one, as Claude Code does. Both cover closing-thought odds, a Hard preview backed off
and one taken, a Routine roll, a tool dropped after its retries, prose refused once, a fallback turn
and a fight. Run with `-s` to print each saved turn (docs/playtests/2026-11-06-m2b-scripted-run.md).
"""

import itertools
import json
import re
from pathlib import Path
from typing import Any

from pantheon.llm.client import LLMReply, ToolCall
from pantheon.narrator.notices import check_notice
from pantheon.storage.db import Database
from tests.test_fights import FIGHT_ACTIONS, HOUND
from tests.test_play import ACTIONS, NEW_GAME, play, talk
from tests.test_session import CLIMB, SUGGEST, Game

HARD = json.loads(CLIMB)
ROUTINE = {**HARD, "difficulty": "routine", "stakes": "a slip"}
BAD_STANDING = {"entity": "kaul", "kind": "enormous", "direction": "+", "reason": "seen"}
BAD_PROSE = "Wren counted 12 coins in the dark."  # A number the engine never returned (NAR-04).
_NOTICE = re.compile(r"\*\*\*.*?\*\*\*")
_ODDS = re.compile(r"\((?:\w+ (?:\d+%|sure|no chance)|no roll)\)")
_SCENES = itertools.cycle(
    (
        "The rail was wet, and the wind off the ford pulled at her coat.",
        "Somewhere below, the ferry chain clanked against its post.",
        "The guard looked at her the way men look at weather.",
        "Lamplight moved along the wall and found nothing worth keeping.",
        "The hound came out of the reeds low and fast, already sure of her.",
        "Teeth closed on air where her wrist had been a breath before.",
        "Her boots found the stone, and the stone held.",
        "The river kept its own counsel and its own slow noise.",
    )
)


def scene(extra: str = "") -> str:
    return f"{next(_SCENES)} {extra}".strip()


def saved_turns(db_path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    with Database.open(db_path) as db:
        tid = db.latest_timeline()
        assert tid is not None
        rows = db.conn.execute(
            "SELECT turn, player_input, narration, is_fallback FROM turn WHERE timeline_id = ? ORDER BY turn",
            (tid,),
        ).fetchall()
        events = db.events(tid)
    turns = [{"turn": r[0], "input": r[1], "narration": r[2], "fallback": bool(r[3])} for r in rows]
    return turns, events


def assert_reliable(db_path: Path, *, dropped: set[str]) -> list[dict[str, Any]]:
    """The acceptance checks shared by both paths. Returns the saved turns."""
    turns, events = saved_turns(db_path)
    assert len(turns) == 10
    for turn in turns:
        mine = [e["payload"] for e in events if e["turn"] == turn["turn"] and e["type"] == "check_resolved"]
        text = turn["narration"]
        for notice in _NOTICE.findall(text):  # Every printed roll is one the engine made that turn.
            assert notice in {f"{check_notice(p)}" for p in mine}, notice
        engine_free = _ODDS.sub("", _NOTICE.sub("", text))
        if not turn["fallback"]:
            assert not re.search(r"\d", engine_free), turn  # NAR-04: no invented number survived.
        assert "12 coins" not in text and "<<" not in text
    assert {e["payload"]["tool"] for e in events if e["type"] == "tool_call_dropped"} == dropped  # NAR-06
    assert [t["turn"] for t in turns if t["fallback"]] == [7]  # NAR-07
    assert any(_ODDS.search(t["narration"]) for t in turns)  # D-050: odds in a closing thought.
    taken = [e for e in events if e["turn"] == 3 and e["type"] == "check_resolved"]
    assert len(taken) == 1 and taken[0]["payload"]["difficulty"] == "hard"  # One roll, after the yes.
    for turn in turns:
        print(f"\n--- Turn {turn['turn']}{' (fallback)' if turn['fallback'] else ''}: {turn['input']}")
        print(turn["narration"])
    return turns


def reply(*calls: ToolCall) -> LLMReply:
    return LLMReply(tool_calls=calls)


def call(name: str, **args: Any) -> ToolCall:
    return ToolCall(f"c_{name}", name, args)


def test_m2b_scripted_ten_turns_on_pantheon_play(tmp_path: Path, capsys: Any) -> None:
    suggest = call("suggest_actions", actions=ACTIONS)
    marked = [*ACTIONS[:2], {"label": "Climb the rail", "cost": "a fall", "check": HARD}]
    script: list[LLMReply | None] = [
        *talk(),  # 1: the opening and the Dual Offer.
        LLMReply(text=scene("She could climb the rail <<ODDS 3>>, or ask who is there <<ODDS 1>>.")),
        reply(call("suggest_actions", actions=marked)),  # 2: the aftermath, with closing-thought odds.
        reply(call("request_check", **HARD)),  # 3a: previewed, then backed off.
        reply(call("request_check", **HARD)),  # 3b: previewed again, taken.
        LLMReply(text=scene("\n\n<<CHECK>>")),
        reply(call("grant_xp", kind="minor", reason="the climb"), suggest),
        LLMReply(text="NONE"),  # 4: a tool refused on its try and both retries.
        LLMReply(text=scene()),
        reply(call("adjust_standing", **BAD_STANDING)),
        reply(call("adjust_standing", **BAD_STANDING)),
        reply(call("adjust_standing", **BAD_STANDING)),
        reply(suggest),
        LLMReply(text="NONE"),  # 5: prose refused once for a stray number.
        LLMReply(text=BAD_PROSE),
        LLMReply(text=scene()),
        reply(suggest),
        reply(call("request_check", **ROUTINE)),  # 6: a Routine check rolls at once.
        LLMReply(text=scene("\n\n<<CHECK>>")),
        reply(suggest),
        LLMReply(text="NONE"),  # 7: prose refused three times, so the engine writes the turn.
        LLMReply(text=BAD_PROSE),
        LLMReply(text=BAD_PROSE),
        LLMReply(text=BAD_PROSE),
        LLMReply(text="NONE"),  # 8: a quiet turn.
        LLMReply(text=scene()),
        reply(suggest),
        LLMReply(text="NONE"),  # 9: the fight starts.
        LLMReply(text=scene()),
        reply(
            call("start_fight", foes=[HOUND], reason="it lunges"),
            call("suggest_actions", actions=FIGHT_ACTIONS),
        ),
        LLMReply(text=scene("\n\n<<CHECK>>")),  # 10: a picked fight move rolls without a referee.
        reply(call("suggest_actions", actions=FIGHT_ACTIONS)),
    ]
    lines = [
        *NEW_GAME,
        "1",  # Swear to the first god.
        "1",
        "1",
        "I climb the wall",
        "n",
        "I climb the wall, slowly this time",
        "y",
        "I ask the guard who keeps this ford",
        "I look around the toll house",
        "I hop the low rail",
        "I listen at the door",
        "I wait for the lamp to pass",
        "I draw on the hound",
        "2",  # Hold your guard: a fight move, from the numbered list.
        "/quit",
    ]
    code, _state, _ = play(tmp_path, lines, script)
    assert code == 0
    out = capsys.readouterr().out
    assert out.count("Preview: Agility check, hard:") == 2 and "You back off" in out
    turns = assert_reliable(tmp_path / "game.db", dropped={"adjust_standing"})
    assert "(Agility " in turns[1]["narration"] and "(no roll)" in turns[1]["narration"]


def test_m2b_scripted_ten_turns_in_session_play(tmp_path: Path, capsys: Any) -> None:
    game = Game(tmp_path, capsys)
    game.aftermath()  # 1 and 2: the opening, the Oath, and closing-thought odds.

    def step(*args: str) -> str:
        code, out = game(*args)
        assert code == 0, out
        return out

    step("begin", "I climb the slick wall")  # 3: previewed, backed off, then taken.
    assert "Preview: Agility check, hard" in step("tool", "request_check", CLIMB)
    step("abandon")
    step("begin", "I climb the slick wall, slowly this time")
    assert "Preview: Agility check, hard" in step("tool", "request_check", CLIMB)
    step("go")
    game.narrate(scene("\n\n<<CHECK>>"))
    step("tool", "grant_xp", json.dumps({"kind": "minor", "reason": "the climb"}))
    step("tool", "suggest_actions", SUGGEST)
    step("commit")

    step("begin", "I ask the guard who keeps this ford")  # 4: a tool dropped after its retries.
    game.narrate(scene())
    for _ in range(3):
        step("tool", "adjust_standing", json.dumps(BAD_STANDING))
    step("tool", "suggest_actions", SUGGEST)
    step("commit")

    step("begin", "I look around the toll house")  # 5: prose refused once.
    assert "Not accepted" in game.narrate(BAD_PROSE)[1]
    game.narrate(scene())
    step("tool", "suggest_actions", SUGGEST)
    step("commit")

    step("begin", "I hop the low rail")  # 6: a Routine check rolls at once.
    assert "Engine check" in step("tool", "request_check", json.dumps(ROUTINE))
    game.narrate(scene("\n\n<<CHECK>>"))
    step("tool", "suggest_actions", SUGGEST)
    step("commit")

    step("begin", "I listen at the door")  # 7: three refused narrations, so a fallback turn.
    for _ in range(3):
        game.narrate(BAD_PROSE)
    step("commit")

    step("begin", "I wait for the lamp to pass")  # 8: suggest_actions dropped, so no new options.
    game.narrate(scene("She could follow the light <<ODDS 2>>."))
    for _ in range(3):
        game("tool", "suggest_actions", json.dumps({"actions": []}))
    step("commit")
    assert game.state()[0].suggested == []

    step("begin", "I draw on the hound")  # 9: the fight starts.
    game.narrate(scene())
    step("tool", "start_fight", json.dumps({"foes": [HOUND], "reason": "it lunges"}))
    step("tool", "suggest_actions", json.dumps({"actions": FIGHT_ACTIONS}))
    step("commit")

    assert "Engine fight" in step("begin", "--option", "2")  # 10: a picked fight move rolls first.
    game.narrate(scene("\n\n<<CHECK>>"))
    step("tool", "suggest_actions", json.dumps({"actions": FIGHT_ACTIONS}))
    step("commit")

    turns = assert_reliable(game.db, dropped={"adjust_standing", "suggest_actions"})
    assert turns[7]["narration"].endswith("She could follow the light.")  # Marker and its space gone.
    assert "(Agility " in turns[1]["narration"]
    assert "The Ledger records only this" in turns[6]["narration"]
