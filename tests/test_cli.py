"""M0 acceptance: `pantheon new` creates a timeline with a seed and the opening gods (D-017)."""

from pathlib import Path

from pantheon.storage.db import Database
from pantheon.ui.cli.app import main


def test_new_creates_timeline_with_opening_draw(tmp_path: Path, capsys: object) -> None:
    db_path = tmp_path / "pantheon.db"
    assert main(["new", "--seed", "42", "--db", str(db_path)]) == 0
    with Database.open(db_path) as db:
        (tid,) = [r[0] for r in db.conn.execute("SELECT id FROM timeline")]
        events = db.events(tid)
    assert events[0]["type"] == "opening_gods_drawn"
    assert len(events[0]["payload"]["gods"]) == 2


def test_new_is_deterministic_for_a_seed(tmp_path: Path) -> None:
    gods = []
    for name in ("a.db", "b.db"):
        main(["new", "--seed", "7", "--db", str(tmp_path / name)])
        with Database.open(tmp_path / name) as db:
            tid = db.conn.execute("SELECT id FROM timeline").fetchone()[0]
            gods.append(db.events(tid)[0]["payload"]["gods"])
    assert gods[0] == gods[1]


def test_new_honours_fixed_gods_from_config(tmp_path: Path) -> None:
    cfg = tmp_path / "config.toml"
    cfg.write_text('[gameplay]\nopening_gods = ["kaul", "hurrow"]\n', encoding="utf-8")
    main(["new", "--seed", "7", "--db", str(tmp_path / "x.db"), "--config", str(cfg)])
    with Database.open(tmp_path / "x.db") as db:
        tid = db.conn.execute("SELECT id FROM timeline").fetchone()[0]
        assert db.events(tid)[0]["payload"]["gods"] == ["kaul", "hurrow"]
