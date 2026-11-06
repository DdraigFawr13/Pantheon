"""M1f dev CLI: `pantheon roll`, `pantheon sheet` and `pantheon log`, with no LLM."""

from pathlib import Path
from typing import Any

from pantheon.ui.cli.app import main


def run(capsys: Any, *args: str) -> tuple[int, str]:
    capsys.readouterr()
    code = main(list(args))
    return code, capsys.readouterr().out


def test_roll_uses_the_engine_rules_and_is_seeded(capsys: Any) -> None:
    code, out = run(capsys, "roll", "--stat", "35", "--difficulty", "hard", "--count", "3", "--seed", "4")
    assert code == 0 and "chance 40% shown" in out and out.count("rolled") == 3
    assert (
        run(capsys, "roll", "--stat", "35", "--difficulty", "hard", "--count", "3", "--seed", "4")[1] == out
    )


def test_roll_shows_a_bonus_and_a_settled_tier_gap(capsys: Any) -> None:
    plain = run(capsys, "roll", "--stat", "35")[1]
    assert "chance 60% shown" in plain
    assert "chance 70% shown" in run(capsys, "roll", "--stat", "35", "--bonus", "10")[1]
    code, out = run(capsys, "roll", "--tier", "4", "--challenge", "1")
    assert code == 0 and "settled by the tier gap" in out and "no roll: success" in out
    assert run(capsys, "roll", "--tier", "9")[0] == 1


def test_sheet_and_log_read_a_save(capsys: Any, tmp_path: Path) -> None:
    db, config = str(tmp_path / "g.db"), str(tmp_path / "none.toml")
    session = ["session", "--db", db, "--config", config]
    assert run(capsys, "sheet", "--db", db, "--config", config)[0] == 1  # No timeline yet.
    assert (
        run(
            capsys,
            *session,
            "create",
            "--name",
            "Wren",
            "--people",
            "saltborn",
            "--origin",
            "toll_ferry_orphan",
        )[0]
        == 0
    )
    code, out = run(capsys, "sheet", "--db", db, "--config", config)
    assert code == 0 and "Wren" in out and "Purse:" in out
    code, out = run(capsys, "log", "--db", db, "--config", config)
    assert code == 0 and "opening_gods_drawn" in out and "character_created" in out
    code, out = run(
        capsys, "log", "--db", db, "--config", config, "--type", "character_created", "--last", "1"
    )
    assert code == 0 and "1 of 1 events" in out
