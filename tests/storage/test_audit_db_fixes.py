"""Audit 2026-11-06 findings in storage: F6, F15, F19, F20 (OPS-03, GAME-05, ENG-08)."""

import sqlite3
from pathlib import Path

import pytest

from pantheon.engine.rng import STREAMS, RngStreams
from pantheon.storage.db import Database, ForkError, SaveError
from tests.storage.test_upgrade_and_fork import v1_save


def test_audit_f6_ops03_a_timeline_and_its_first_events_are_one_transaction(tmp_path: Path) -> None:
    with Database.open(tmp_path / "pantheon.db") as db:
        with pytest.raises(TypeError):
            db.create_timeline(1, {}, events=[("opening_gods_drawn", {"gods": {object()}})])
        assert db.conn.execute("SELECT COUNT(*) FROM timeline").fetchone()[0] == 0
        tid = db.create_timeline(1, {}, events=[("opening_gods_drawn", {"gods": ["a", "b"]})])
        assert [e["type"] for e in db.events(tid)] == ["opening_gods_drawn"]


def test_audit_f15_game05_bad_rng_json_in_an_upgrade_leaves_the_save_alone(tmp_path: Path) -> None:
    path = tmp_path / "pantheon.db"
    v1_save(path, {})
    conn = sqlite3.connect(path)
    with conn:
        conn.execute("UPDATE timeline SET rng_state = 'not json'")
    conn.close()
    with pytest.raises(SaveError, match=r"left alone|failed"):
        Database.open(path)
    conn = sqlite3.connect(path)
    assert conn.execute("SELECT value FROM meta WHERE key = 'schema_version'").fetchone()[0] == "1"
    conn.close()


def test_audit_f19_find_timeline_prefix_has_no_wildcards(tmp_path: Path) -> None:
    with Database.open(tmp_path / "pantheon.db") as db:
        tid = db.create_timeline(1, {})
        assert db.find_timeline(tid[:6]) == tid
        for prefix in ("%", "_", tid[:3] + "_"):
            with pytest.raises(ForkError):
                db.find_timeline(prefix)


def test_audit_f20_eng08_a_stream_missing_from_an_old_save_is_seeded_from_its_seed() -> None:
    state = RngStreams.from_seed(9).state()
    del state["world"]
    restored = RngStreams.from_state(state, seed=9)
    assert restored.state() == RngStreams.from_seed(9).state()
    assert set(restored.state()) == set(STREAMS)
    with pytest.raises(KeyError):
        RngStreams.from_state(state)
