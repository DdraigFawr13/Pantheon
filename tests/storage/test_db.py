"""ENG-10 and GAME-05: SQLite in WAL mode with a schema version; newer saves are refused."""

import sqlite3
from pathlib import Path

import pytest

from pantheon.engine.version import RULES_VERSION, SCHEMA_VERSION
from pantheon.storage.db import Database, SaveError


def test_eng10_new_database_has_wal_and_schema_version(tmp_path: Path) -> None:
    with Database.open(tmp_path / "pantheon.db") as db:
        assert db.conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        assert db.schema_version() == SCHEMA_VERSION
        tables = {r[0] for r in db.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"meta", "timeline", "event", "snapshot", "turn", "summary"} <= tables


def test_eng10_timeline_records_seed_and_rules_version(tmp_path: Path) -> None:
    with Database.open(tmp_path / "pantheon.db") as db:
        tid = db.create_timeline(seed=123, rng_state={"checks": [3, [1], None]})
        row = db.conn.execute("SELECT seed, rules_version FROM timeline WHERE id = ?", (tid,)).fetchone()
    assert tuple(row) == (123, RULES_VERSION)


def test_eng06_events_append_in_order(tmp_path: Path) -> None:
    with Database.open(tmp_path / "pantheon.db") as db:
        tid = db.create_timeline(seed=1, rng_state={})
        db.append_event(tid, turn=0, type_="opening_gods_drawn", payload={"gods": ["kaul", "hurrow"]})
        db.append_event(tid, turn=0, type_="flag_set", payload={"key": "x"})
        assert [e["type"] for e in db.events(tid)] == ["opening_gods_drawn", "flag_set"]
        assert db.events(tid)[0]["payload"] == {"gods": ["kaul", "hurrow"]}


def test_game05_newer_schema_is_refused_and_untouched(tmp_path: Path) -> None:
    path = tmp_path / "pantheon.db"
    Database.open(path).close()
    conn = sqlite3.connect(path)
    conn.execute("UPDATE meta SET value = ? WHERE key = 'schema_version'", (str(SCHEMA_VERSION + 1),))
    conn.commit()
    conn.close()
    before = path.read_bytes()
    with pytest.raises(SaveError):
        Database.open(path)
    assert path.read_bytes() == before
