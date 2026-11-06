"""`pantheon chronicle`: the story so far, read from the save (GAME-03: it reports, never decides)."""

from pathlib import Path
from typing import Any

import pytest

from pantheon.engine.loot import format_cp
from pantheon.ui.cli.app import main
from tests.test_session import Game


@pytest.fixture
def game(tmp_path: Path, capsys: Any) -> Game:
    return Game(tmp_path, capsys)


def run(capsys: Any, *args: str) -> tuple[int, str]:
    capsys.readouterr()
    code = main(list(args))
    return code, capsys.readouterr().out


def test_chronicle_needs_a_timeline(capsys: Any, tmp_path: Path) -> None:
    code, out = run(capsys, "chronicle", "--db", str(tmp_path / "g.db"), "--config", str(tmp_path / "x.toml"))
    assert code == 1 and "no timeline" in out


def test_chronicle_markdown_matches_the_playtest_shape(game: Game, capsys: Any) -> None:
    game.aftermath()
    code, out = run(capsys, "chronicle", "--db", str(game.db), "--config", str(game.config))
    assert code == 0, out
    assert out.startswith("# The chronicle of Wren")
    assert "Wayfinder" in out and "Hunter" in out and "sworn to" in out
    assert "### Turn 1" in out and "### Turn 2" in out
    assert "**Player:** [I swear. Narrate the aftermath.]" in out
    assert "The Ledger opened in Wren's head." in out
    assert "`▸ Oath sworn:" in out  # The engine's events, as the Ledger shows them.
    assert "## Threads" in out and "- Open: Complication:" in out
    assert "## The tally" in out and "- Turns: 2" in out and "- XP earned:" in out
    assert "## The Ledger now" in out and "Purse:" in out


def test_chronicle_tally_counts_only_recorded_events() -> None:
    from pantheon.ui.chronicle import tally

    events = [
        {
            "type": "check_resolved",
            "payload": {"outcome": "triumph", "roll": 3, "stat": "intellect", "chance": 58},
        },
        {
            "type": "check_resolved",
            "payload": {"outcome": "failure", "roll": 90, "stat": "vigor", "chance": 40},
        },
        {"type": "check_resolved", "payload": {"outcome": "success", "stat": "vigor", "automatic": True}},
        {"type": "xp_gained", "payload": {"amount": 10, "reason": "the climb"}},
        {"type": "xp_gained", "payload": {"amount": 5, "reason": "the sack"}},
        {"type": "effect_applied", "payload": {"kind": "damage", "amount": 4, "reason": "a bite"}},
        {"type": "effect_applied", "payload": {"kind": "heal", "amount": 2, "reason": "a tonic"}},
        {"type": "fight_ended", "payload": {"result": "won"}},
        {"type": "currency_changed", "payload": {"delta_cp": -14, "reason": "the toll"}},
    ]
    rows = dict(tally(events, 7))
    assert rows["Turns"] == "7" and rows["XP earned"] == "15" and rows["HP lost"] == "4"
    assert rows["Checks"] == "3 (1 triumph, 1 failure, 1 success)"
    assert rows["Best roll"] == "3 (intellect check at 58%)"
    assert rows["Fights"] == "1, 1 won" and rows["Coin"] == "-" + format_cp(14)
    assert dict(tally([], 0)) == {"Turns": "0", "XP earned": "0"}


def test_chronicle_html_is_a_page_written_to_a_file(game: Game, capsys: Any, tmp_path: Path) -> None:
    game.opening()
    out_path = tmp_path / "pages" / "chronicle.html"
    code, out = run(
        capsys,
        "chronicle",
        "--db",
        str(game.db),
        "--config",
        str(game.config),
        "--format",
        "html",
        "--out",
        str(out_path),
    )
    assert code == 0 and "1 turns of Wren" in out
    page = out_path.read_text(encoding="utf-8")
    assert page.startswith("<!doctype html>") and "<title>Wren Chronicle</title>" in page
    assert 'id="t1"' in page and "Two voices spoke out of the dark at once." in page
    assert "<script" not in page  # A reading page: nothing runs, nothing recomputes a rule (GAME-02).


def test_chronicle_escapes_prose_and_keeps_notices() -> None:
    from pantheon.ui.chronicle import _paragraphs

    page = _paragraphs("Wren <thought> of the sea.\n\n***Nothing rolled.***")
    assert page == '<p>Wren &lt;thought&gt; of the sea.</p>\n<p class="notice">Nothing rolled.</p>'
