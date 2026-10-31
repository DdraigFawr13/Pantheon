"""ENG-08, ENG-10, GAME-05: saves upgrade step by step, bad saves are refused, timelines fork."""

import json
import sqlite3
from pathlib import Path
from typing import Any

import pytest

from pantheon.engine.rng import RngStreams
from pantheon.engine.state import GameState
from pantheon.engine.version import RULES_VERSION, SCHEMA_VERSION
from pantheon.storage import db as db_module
from pantheon.storage.db import Database, ForkError, SaveError, TurnRecord

_V1_SCHEMA = """
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE timeline (
    id TEXT PRIMARY KEY, parent_id TEXT, fork_turn INTEGER, seed INTEGER NOT NULL,
    rng_state TEXT NOT NULL, rules_version TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE event (
    timeline_id TEXT NOT NULL REFERENCES timeline(id), seq INTEGER NOT NULL, turn INTEGER NOT NULL,
    type TEXT NOT NULL, payload_json TEXT NOT NULL, PRIMARY KEY (timeline_id, seq)
);
CREATE TABLE snapshot (
    timeline_id TEXT NOT NULL REFERENCES timeline(id), turn INTEGER NOT NULL, state_json TEXT NOT NULL,
    PRIMARY KEY (timeline_id, turn)
);
CREATE TABLE turn (
    timeline_id TEXT NOT NULL REFERENCES timeline(id), turn INTEGER NOT NULL, player_input TEXT NOT NULL,
    narration TEXT NOT NULL, is_fallback INTEGER NOT NULL DEFAULT 0, tokens_in INTEGER, tokens_cached INTEGER,
    tokens_out INTEGER, PRIMARY KEY (timeline_id, turn)
);
CREATE TABLE summary (
    timeline_id TEXT NOT NULL REFERENCES timeline(id),
    level TEXT NOT NULL CHECK (level IN ('scene', 'chapter')),
    span_start INTEGER NOT NULL, span_end INTEGER NOT NULL, text TEXT NOT NULL
);
"""


def v1_save(path: Path, rng_state: dict[str, Any]) -> None:
    conn = sqlite3.connect(path)
    conn.executescript(_V1_SCHEMA)
    with conn:
        conn.execute("INSERT INTO meta VALUES ('schema_version', '1')")
        conn.execute(
            "INSERT INTO timeline (id, seed, rng_state, rules_version, created_at)"
            " VALUES ('old', 7, ?, '2026.10.0', '2026-10-30')",
            (json.dumps(rng_state),),
        )
        conn.execute(
            "INSERT INTO event VALUES ('old', 0, 1, 'flag_set', ?)",
            (json.dumps({"key": "story.kept", "value": True, "reason": "x"}),),
        )
        conn.execute("INSERT INTO turn VALUES ('old', 1, 'hello', 'prose', 0, 1, 0, 1)")
    conn.close()


def play(db: Database, tid: str, rng: RngStreams, turns: range) -> None:
    """Commit one flag and one roll per turn, so each turn has its own events and RNG state."""
    for number in turns:
        roll = rng.roll("checks", 100)
        events = [("flag_set", {"key": f"story.t{number}", "value": True, "reason": str(roll)})]
        state = db.load_state(tid).model_copy(deep=True)
        state.flags[f"story.t{number}"] = True
        record = TurnRecord(number, f"input {number}", f"prose {number}")
        db.commit_turn(tid, record, events, rng.state(), state)


def test_eng10_v1_save_upgrades_and_keeps_its_play(tmp_path: Path) -> None:
    path = tmp_path / "pantheon.db"
    rng = RngStreams.from_seed(7)
    v1_save(path, rng.state())
    with Database.open(path) as db:
        assert db.schema_version() == SCHEMA_VERSION
        assert db.load_state("old").flags == {"story.kept": True}
        assert db.last_turn("old") == 1
        assert db.rng_state("old") == rng.state()
        fork = db.fork("old", 1)
        assert db.rng_state(fork) == rng.state()


def test_eng10_upgrade_keeps_a_readable_backup_of_the_old_save(tmp_path: Path) -> None:
    path = tmp_path / "pantheon.db"
    v1_save(path, RngStreams.from_seed(7).state())
    Database.open(path).close()
    backup = sqlite3.connect(tmp_path / "pantheon.db.schema1.bak")
    assert backup.execute("SELECT value FROM meta").fetchone()[0] == "1"
    assert backup.execute("SELECT COUNT(*) FROM turn").fetchone()[0] == 1
    backup.close()


def test_eng10_upgrade_never_replaces_an_earlier_backup(tmp_path: Path) -> None:
    path = tmp_path / "pantheon.db"
    v1_save(path, RngStreams.from_seed(7).state())
    backup = tmp_path / "pantheon.db.schema1.bak"
    backup.write_text("earlier", encoding="utf-8")
    Database.open(path).close()
    assert backup.read_text(encoding="utf-8") == "earlier"


def test_game05_failed_upgrade_changes_nothing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "pantheon.db"
    v1_save(path, RngStreams.from_seed(7).state())

    def broken(conn: sqlite3.Connection) -> None:
        conn.execute("CREATE TABLE half_done (x)")
        raise sqlite3.OperationalError("disk trouble")

    monkeypatch.setitem(db_module.UPGRADES, 1, broken)
    with pytest.raises(SaveError, match="upgrade"):
        Database.open(path)
    conn = sqlite3.connect(path)
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    version = conn.execute("SELECT value FROM meta").fetchone()[0]
    conn.close()
    assert "half_done" not in tables
    assert version == "1"


def test_game05_save_with_no_upgrade_path_is_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "pantheon.db"
    v1_save(path, RngStreams.from_seed(7).state())
    monkeypatch.delitem(db_module.UPGRADES, 1)
    with pytest.raises(SaveError, match="upgrade"):
        Database.open(path)


def test_game05_unreadable_file_is_refused_and_untouched(tmp_path: Path) -> None:
    path = tmp_path / "pantheon.db"
    path.write_bytes(b"this is not a database, and it is long enough to be read as one" * 20)
    before = path.read_bytes()
    with pytest.raises(SaveError):
        Database.open(path)
    assert path.read_bytes() == before


def test_game05_someone_elses_database_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "pantheon.db"
    conn = sqlite3.connect(path)
    with conn:
        conn.execute("CREATE TABLE recipes (name TEXT)")
    conn.close()
    with pytest.raises(SaveError):
        Database.open(path)


def test_game05_an_empty_file_is_a_new_save(tmp_path: Path) -> None:
    path = tmp_path / "pantheon.db"
    path.touch()
    with Database.open(path) as db:
        assert db.schema_version() == SCHEMA_VERSION


def test_game05_event_this_build_cannot_read_is_a_save_error(tmp_path: Path) -> None:
    with Database.open(tmp_path / "pantheon.db") as db:
        tid = db.create_timeline(seed=1, rng_state={})
        db.append_event(tid, 1, "from_the_future", {})
        with pytest.raises(SaveError, match="from_the_future"):
            db.load_state(tid)


def setup_timeline(db: Database, turns: int) -> tuple[str, RngStreams]:
    rng = RngStreams.from_seed(5)
    tid = db.create_timeline(seed=5, rng_state=rng.state())
    play(db, tid, rng, range(1, turns + 1))
    return tid, rng


def test_eng08_fork_copies_up_to_the_turn_and_links_the_parent(tmp_path: Path) -> None:
    with Database.open(tmp_path / "pantheon.db") as db:
        tid, _ = setup_timeline(db, 12)
        with db.conn:
            db.conn.execute("INSERT INTO summary VALUES (?, 'scene', 1, 4, 'early')", (tid,))
            db.conn.execute("INSERT INTO summary VALUES (?, 'scene', 5, 9, 'late')", (tid,))
        fork = db.fork(tid, 4)
        row = db.conn.execute(
            "SELECT parent_id, fork_turn, seed FROM timeline WHERE id = ?", (fork,)
        ).fetchone()
        assert tuple(row) == (tid, 4, 5)
        assert db.last_turn(fork) == 4
        assert [e["turn"] for e in db.events(fork)] == [1, 2, 3, 4]
        assert set(db.load_state(fork).flags) == {f"story.t{n}" for n in range(1, 5)}
        texts = db.conn.execute("SELECT text FROM summary WHERE timeline_id = ?", (fork,)).fetchall()
        assert [r[0] for r in texts] == ["early"]
        assert db.last_turn(tid) == 12
        assert db.latest_timeline() == fork


def test_eng08_fork_keeps_snapshots_at_or_before_the_turn(tmp_path: Path) -> None:
    with Database.open(tmp_path / "pantheon.db") as db:
        tid, _ = setup_timeline(db, 25)
        fork = db.fork(tid, 15)
        rows = db.conn.execute("SELECT turn FROM snapshot WHERE timeline_id = ?", (fork,)).fetchall()
        assert [r[0] for r in rows] == [10]
        assert set(db.load_state(fork).flags) == {f"story.t{n}" for n in range(1, 16)}


def test_eng08_fork_restores_the_rng_so_the_same_rolls_come_back(tmp_path: Path) -> None:
    with Database.open(tmp_path / "pantheon.db") as db:
        tid, _ = setup_timeline(db, 8)
        rolls = [e["payload"]["reason"] for e in db.events(tid)]
        fork = db.fork(tid, 3)
        rng = RngStreams.from_state(db.rng_state(fork))
        play(db, fork, rng, range(4, 9))
        assert [e["payload"]["reason"] for e in db.events(fork)] == rolls
        assert db.load_state(fork).model_dump() == db.load_state(tid).model_dump()


def test_eng08_forks_from_one_turn_can_each_go_their_own_way(tmp_path: Path) -> None:
    with Database.open(tmp_path / "pantheon.db") as db:
        tid, _ = setup_timeline(db, 3)
        left, right = db.fork(tid, 2), db.fork(tid, 2)
        record = TurnRecord(3, "left", "prose")
        db.commit_turn(
            left, record, [("flag_set", {"key": "story.left", "value": True, "reason": ""})], {}, GameState()
        )
        assert "story.left" in db.load_state(left).flags
        assert "story.left" not in db.load_state(right).flags


def test_eng08_fork_at_turn_zero_replays_the_opening(tmp_path: Path) -> None:
    with Database.open(tmp_path / "pantheon.db") as db:
        rng = RngStreams.from_seed(5)
        tid = db.create_timeline(seed=5, rng_state=rng.state())
        db.append_event(tid, 0, "opening_gods_drawn", {"gods": ["a", "b"]})
        play(db, tid, rng, range(1, 3))
        fork = db.fork(tid, 0)
        assert db.last_turn(fork) == 0
        assert db.load_state(fork).opening_gods == ["a", "b"]
        assert db.rng_state(fork) == RngStreams.from_seed(5).state()


def test_eng08_commands_after_the_fork_turn_are_not_copied(tmp_path: Path) -> None:
    """A command made after turn N is stamped N + 1, along with its rolls, so a fork at N redoes it."""
    with Database.open(tmp_path / "pantheon.db") as db:
        tid, rng = setup_timeline(db, 2)
        at_two = rng.state()
        rng.roll("checks", 100)
        db.commit_events(
            tid, 3, [("flag_set", {"key": "story.cmd", "value": True, "reason": ""})], rng.state()
        )
        fork = db.fork(tid, 2)
        assert "story.cmd" not in db.load_state(fork).flags
        assert db.rng_state(fork) == at_two


@pytest.mark.parametrize("turn", [-1, 4])
def test_eng08_fork_refuses_a_turn_that_does_not_exist(tmp_path: Path, turn: int) -> None:
    with Database.open(tmp_path / "pantheon.db") as db:
        tid, _ = setup_timeline(db, 3)
        before = db.conn.execute("SELECT COUNT(*) FROM timeline").fetchone()[0]
        with pytest.raises(ForkError):
            db.fork(tid, turn)
        assert db.conn.execute("SELECT COUNT(*) FROM timeline").fetchone()[0] == before


def test_eng08_fork_before_an_upgraded_saves_first_record_is_refused(tmp_path: Path) -> None:
    """A schema 1 save kept only its latest RNG state, so its earlier turns cannot restore one honestly."""
    path = tmp_path / "pantheon.db"
    v1_save(path, RngStreams.from_seed(7).state())
    with Database.open(path) as db, pytest.raises(ForkError, match="turn 1"):
        db.fork("old", 0)


def test_eng08_find_timeline_by_prefix(tmp_path: Path) -> None:
    with Database.open(tmp_path / "pantheon.db") as db:
        tid, _ = setup_timeline(db, 1)
        assert db.find_timeline(tid[:8]) == tid
        with pytest.raises(ForkError):
            db.find_timeline("zzzz")


def test_eng08_rng_records_only_the_streams_that_moved(tmp_path: Path) -> None:
    with Database.open(tmp_path / "pantheon.db") as db:
        tid, _ = setup_timeline(db, 3)
        rows = db.conn.execute(
            "SELECT turn, stream FROM rng_checkpoint WHERE timeline_id = ? AND turn > 0", (tid,)
        ).fetchall()
        assert {tuple(r) for r in rows} == {(1, "checks"), (2, "checks"), (3, "checks")}


def test_eng10_fork_keeps_the_rules_version_of_its_parent(tmp_path: Path) -> None:
    with Database.open(tmp_path / "pantheon.db") as db:
        tid, _ = setup_timeline(db, 1)
        fork = db.fork(tid, 1)
        row = db.conn.execute("SELECT rules_version FROM timeline WHERE id = ?", (fork,)).fetchone()
        assert row[0] == RULES_VERSION
