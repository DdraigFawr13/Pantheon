"""Audit 2026-11-06 source findings: F4, F5, F13, F14, F16, F17, F18 (OPS-03, NAR-02, GAME-05, D-036)."""

import sqlite3
from pathlib import Path
from typing import Any

import pytest
from rich.console import Console

from pantheon.engine.state import GameState
from pantheon.narrator import assemble as assemble_module
from pantheon.narrator.assemble import assemble, prompt_lore_ids
from pantheon.narrator.notices import check_notice
from pantheon.storage.db import Database
from pantheon.ui.cli import app as app_module
from pantheon.ui.cli.app import _pick, create_timeline, inspect_option, main
from pantheon.ui.cli.session import Pending, Session, SessionError, import_db
from pantheon.world.loader import load_world
from tests.test_session import Game

WORLD = load_world(Path(__file__).resolve().parents[1] / "world")
CREATE = ("create", "--name", "Wren", "--people", "saltborn", "--origin", "toll_ferry_orphan")


@pytest.fixture
def game(tmp_path: Path, capsys: Any) -> Game:
    return Game(tmp_path, capsys)


def timeline_count(game: Game) -> int:
    with Database.open(game.db) as db:
        return int(db.conn.execute("SELECT COUNT(*) FROM timeline").fetchone()[0])


def test_audit_f4_a_failed_fresh_create_makes_no_timeline(game: Game) -> None:
    game.create()
    for bad in (("--stats", "a p"), ("--people", "nobody")):
        args = list(CREATE)
        if bad[0] == "--people":
            args[args.index("--people") + 1] = bad[1]
        else:
            args += list(bad)
        code, out = game(*args, "--fresh")
        assert code == 1 and "Traceback" not in out
        assert timeline_count(game) == 1


def test_audit_f5_d036_the_notice_shows_the_clamped_chance() -> None:
    base = {"stat": "agility", "roll": 50, "outcome": "success", "complication": False, "automatic": False}
    assert "100% chance" in check_notice({**base, "chance": 130})
    assert "5% chance" in check_notice({**base, "chance": 2})
    assert "60% chance" in check_notice({**base, "chance": 60})


def test_audit_f6_ops03_opening_gods_are_written_with_the_timeline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = app_module.load_config(tmp_path / "none.toml")
    monkeypatch.setattr(app_module, "draw_opening_gods", lambda *a, **k: ("a", {object()}))
    with Database.open(tmp_path / "g.db") as db:
        with pytest.raises(TypeError):
            create_timeline(db, WORLD, config, 5, Console())
        assert db.latest_timeline() is None


def test_audit_f13_game05_a_bad_dump_leaves_the_old_save_in_place(tmp_path: Path) -> None:
    path = tmp_path / "g.db"
    with Database.open(path) as db:
        tid = db.create_timeline(1, {})
    dump = tmp_path / "bad.sql"
    dump.write_text("CREATE TABLE x (a INTEGER); INSERT INTO nowhere VALUES (1);", encoding="utf-8")
    with pytest.raises(SessionError):
        import_db(dump, path)
    assert list(tmp_path.glob("*.bak")) == []
    with Database.open(path) as db:
        assert db.latest_timeline() == tid
    assert not list(tmp_path.glob("*.tmp"))  # The half-built file is removed.


def test_audit_f13_game05_a_good_dump_moves_the_old_save_and_its_wal_aside(tmp_path: Path) -> None:
    path = tmp_path / "g.db"
    with Database.open(path) as db:
        tid = db.create_timeline(1, {})
    conn = sqlite3.connect(path)
    dump = tmp_path / "good.sql"
    dump.write_text("\n".join(conn.iterdump()) + "\n", encoding="utf-8")
    conn.close()
    path.with_name("g.db-wal").write_text("stale", encoding="utf-8")
    backup = import_db(dump, path)
    assert backup is not None and backup.exists()
    assert not path.with_name("g.db-wal").exists()
    assert backup.with_name(backup.name + "-wal").exists()
    with Database.open(path) as db:
        assert db.latest_timeline() == tid


def make_session(tmp_path: Path) -> Session:
    config = app_module.load_config(tmp_path / "none.toml")
    db = Database.open(tmp_path / "g.db")
    return Session(db, tmp_path / "g.db", WORLD, config, Console())


def test_audit_f14_ops03_a_failed_pending_write_keeps_the_old_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    session = make_session(tmp_path)
    session.save_pending(Pending("t", 1, "I look."))
    before = session.pending_path.read_text(encoding="utf-8")
    real = Path.write_text

    def half(self: Path, data: str, *a: Any, **k: Any) -> int:
        real(self, data[: len(data) // 2], *a, **k)
        raise OSError("disk full")

    monkeypatch.setattr(Path, "write_text", half)
    with pytest.raises(OSError):
        session.save_pending(Pending("t", 1, "I look and then something else."))
    monkeypatch.undo()
    assert session.pending_path.read_text(encoding="utf-8") == before
    session.db.close()


def test_audit_f14_a_unreadable_pending_file_points_to_abandon(tmp_path: Path) -> None:
    session = make_session(tmp_path)
    session.pending_path.write_text('{"timeline": "t", "tu', encoding="utf-8")
    with pytest.raises(SessionError, match="session abandon"):
        session.load_pending()
    session.db.close()


def test_audit_f16_nar02_every_assembled_lore_id_is_public() -> None:
    for resolved in (False, True):
        state = GameState(offer_resolved=resolved)
        ids = prompt_lore_ids(state)
        assert ids
        assert all(WORLD.by_id(i).visibility == "public" for i in ids)
        assemble(state, WORLD, [], "hello")


def test_audit_f16_nar02_a_non_public_id_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    hidden = next(e.id for e in WORLD.lore if e.visibility != "public" and e.type != "sealed-lore")
    monkeypatch.setattr(assemble_module, "_LORE", (hidden,))
    with pytest.raises(AssertionError):
        assemble(GameState(), WORLD, [], "hello")


def test_audit_f17_a_unicode_digit_is_not_a_choice() -> None:
    answers = iter(["²", "1"])
    got = _pick(lambda _: next(answers), Console(), "Pick", [("a", "A"), ("b", "B")])
    assert got == "a"
    state = GameState()
    assert "no option" in inspect_option(state, WORLD, "²").lower()


def test_audit_f18_export_of_a_missing_save_creates_nothing(tmp_path: Path, capsys: Any) -> None:
    db, out = tmp_path / "typo.db", tmp_path / "out.sql"
    code = main(["session", "--db", str(db), "--config", str(tmp_path / "n.toml"), "export", str(out)])
    assert code == 1
    assert not db.exists() and not out.exists()
    assert "typo.db" in capsys.readouterr().out
