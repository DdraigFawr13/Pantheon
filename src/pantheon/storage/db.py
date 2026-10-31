"""SQLite storage (architecture section 5). WAL mode; every write is one transaction (OPS-03).

The event table is the only source of game state (ENG-06). Saves carry a schema version;
a newer save is refused and never written to (ENG-10, GAME-05).
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pantheon.engine.state import EventRecord, GameState, replay
from pantheon.engine.version import RULES_VERSION, SCHEMA_VERSION

SNAPSHOT_EVERY = 10


class SaveError(RuntimeError):
    """A save file this version of the game must not open."""


class ForkError(SaveError):
    """A fork or timeline request this save cannot honestly meet."""


@dataclass(frozen=True)
class TurnRecord:
    turn: int
    player_input: str
    narration: str
    is_fallback: bool = False
    tokens_in: int = 0
    tokens_cached: int = 0
    tokens_out: int = 0


_SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS timeline (
    id TEXT PRIMARY KEY, parent_id TEXT, fork_turn INTEGER, seed INTEGER NOT NULL,
    rng_state TEXT NOT NULL, rules_version TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS event (
    timeline_id TEXT NOT NULL REFERENCES timeline(id), seq INTEGER NOT NULL, turn INTEGER NOT NULL,
    type TEXT NOT NULL, payload_json TEXT NOT NULL, PRIMARY KEY (timeline_id, seq)
);
CREATE TABLE IF NOT EXISTS snapshot (
    timeline_id TEXT NOT NULL REFERENCES timeline(id), turn INTEGER NOT NULL, state_json TEXT NOT NULL,
    PRIMARY KEY (timeline_id, turn)
);
CREATE TABLE IF NOT EXISTS turn (
    timeline_id TEXT NOT NULL REFERENCES timeline(id), turn INTEGER NOT NULL, player_input TEXT NOT NULL,
    narration TEXT NOT NULL, is_fallback INTEGER NOT NULL DEFAULT 0, tokens_in INTEGER, tokens_cached INTEGER,
    tokens_out INTEGER, PRIMARY KEY (timeline_id, turn)
);
CREATE TABLE IF NOT EXISTS summary (
    timeline_id TEXT NOT NULL REFERENCES timeline(id),
    level TEXT NOT NULL CHECK (level IN ('scene', 'chapter')),
    span_start INTEGER NOT NULL, span_end INTEGER NOT NULL, text TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS rng_checkpoint (
    timeline_id TEXT NOT NULL REFERENCES timeline(id), turn INTEGER NOT NULL, stream TEXT NOT NULL,
    state TEXT NOT NULL, PRIMARY KEY (timeline_id, turn, stream)
);
"""


def _upgrade_1_to_2(conn: sqlite3.Connection) -> None:
    """Add per-turn RNG records for forks (ENG-08). A schema 1 save kept only its latest RNG state."""
    conn.execute(
        "CREATE TABLE rng_checkpoint (timeline_id TEXT NOT NULL REFERENCES timeline(id),"
        " turn INTEGER NOT NULL, stream TEXT NOT NULL, state TEXT NOT NULL,"
        " PRIMARY KEY (timeline_id, turn, stream))"
    )
    for tid, rng_state in conn.execute("SELECT id, rng_state FROM timeline").fetchall():
        (turn,) = conn.execute(
            "SELECT COALESCE(MAX(turn), 0) FROM event WHERE timeline_id = ?", (tid,)
        ).fetchone()
        for stream, state in json.loads(rng_state).items():
            conn.execute(
                "INSERT INTO rng_checkpoint (timeline_id, turn, stream, state) VALUES (?, ?, ?, ?)",
                (tid, turn, stream, json.dumps(state)),
            )


_FORK_COPIES = (  # Fixed names, never input: table, columns, and the column that limits the copy.
    ("event", "seq, turn, type, payload_json", "turn"),
    ("snapshot", "turn, state_json", "turn"),
    ("turn", "turn, player_input, narration, is_fallback, tokens_in, tokens_cached, tokens_out", "turn"),
    ("summary", "level, span_start, span_end, text", "span_end"),
    ("rng_checkpoint", "turn, stream, state", "turn"),
)
# One step per schema version. Each runs in one transaction, so a failure leaves the save as it was (ENG-10).
UPGRADES: dict[int, Callable[[sqlite3.Connection], None]] = {1: _upgrade_1_to_2}


class Database:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> Database:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    @classmethod
    def open(cls, path: Path) -> Database:
        path.parent.mkdir(parents=True, exist_ok=True)
        existed = path.exists()
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        try:
            if existed:
                cls._prepare_existing(conn, path)
        except (SaveError, sqlite3.Error) as exc:
            conn.close()
            if isinstance(exc, SaveError):
                raise
            raise SaveError(f"{path} cannot be read as a Pantheon save, so it was left alone: {exc}") from exc
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        with conn:
            conn.executescript(_SCHEMA)
            conn.execute(
                "INSERT OR IGNORE INTO meta (key, value) VALUES ('schema_version', ?)", (str(SCHEMA_VERSION),)
            )
        return cls(conn)

    @classmethod
    def _prepare_existing(cls, conn: sqlite3.Connection, path: Path) -> None:
        """Refuse what must not be opened and upgrade an older save one step at a time (GAME-05)."""
        (tables,) = conn.execute("SELECT COUNT(*) FROM sqlite_master").fetchone()
        version = cls._read_version(conn)
        if version is None:
            if tables:
                raise SaveError(f"{path} is not a Pantheon save, so it was left alone.")
            return
        if version > SCHEMA_VERSION:
            raise SaveError(
                f"{path} was saved by a newer version of Pantheon (schema {version} > {SCHEMA_VERSION})."
            )
        if version < SCHEMA_VERSION:
            cls._backup(conn, path, version)
        while version < SCHEMA_VERSION:
            version = cls._upgrade_step(conn, path, version)

    @staticmethod
    def _backup(conn: sqlite3.Connection, path: Path, version: int) -> None:
        """Copy the old save beside it before changing it. An earlier copy is never replaced."""
        target = path.with_name(f"{path.name}.schema{version}.bak")
        if target.exists():
            return
        copy = sqlite3.connect(target)
        try:
            conn.backup(copy)
        finally:
            copy.close()

    @staticmethod
    def _upgrade_step(conn: sqlite3.Connection, path: Path, version: int) -> int:
        step = UPGRADES.get(version)
        if step is None:
            raise SaveError(f"{path}: no upgrade from schema {version}, so it was left alone.")
        conn.execute("BEGIN IMMEDIATE")
        try:
            step(conn)
            conn.execute("UPDATE meta SET value = ? WHERE key = 'schema_version'", (str(version + 1),))
        except sqlite3.Error as exc:
            conn.rollback()
            raise SaveError(f"{path}: the upgrade from schema {version} failed: {exc}") from exc
        conn.commit()
        return version + 1

    @staticmethod
    def _read_version(conn: sqlite3.Connection) -> int | None:
        try:
            row = conn.execute("SELECT value FROM meta WHERE key = 'schema_version'").fetchone()
        except sqlite3.DatabaseError as exc:
            if "no such table" in str(exc):
                return None
            raise
        return int(row[0]) if row else None

    def schema_version(self) -> int:
        version = self._read_version(self.conn)
        assert version is not None
        return version

    def create_timeline(self, seed: int, rng_state: dict[str, Any]) -> str:
        tid = uuid.uuid4().hex
        with self.conn:
            self.conn.execute(
                "INSERT INTO timeline (id, seed, rng_state, rules_version, created_at)"
                " VALUES (?, ?, ?, ?, ?)",
                (tid, seed, json.dumps(rng_state), RULES_VERSION, datetime.now(UTC).isoformat()),
            )
            self._record_rng(tid, 0, rng_state)
        return tid

    def _record_rng(self, timeline_id: str, turn: int, moved: dict[str, Any]) -> None:
        self.conn.executemany(
            "INSERT OR REPLACE INTO rng_checkpoint (timeline_id, turn, stream, state) VALUES (?, ?, ?, ?)",
            [(timeline_id, turn, stream, json.dumps(state)) for stream, state in moved.items()],
        )

    def find_timeline(self, prefix: str) -> str:
        rows = self.conn.execute(
            "SELECT id FROM timeline WHERE id LIKE ? ORDER BY rowid", (f"{prefix}%",)
        ).fetchall()
        if len(rows) != 1:
            raise ForkError(f"{len(rows)} timelines start with {prefix!r}; give one that names exactly one.")
        return str(rows[0][0])

    def rng_state_at(self, timeline_id: str, turn: int) -> dict[str, Any]:
        """Each stream as it stood at the end of a turn, or ForkError if this save did not record that far."""
        streams = set(self.rng_state(timeline_id))
        found: dict[str, Any] = {}
        rows = self.conn.execute(
            "SELECT stream, state FROM rng_checkpoint WHERE timeline_id = ? AND turn <= ? ORDER BY turn",
            (timeline_id, turn),
        ).fetchall()
        for stream, state in rows:
            found[stream] = json.loads(state)
        if set(found) != streams:
            (first,) = self.conn.execute(
                "SELECT MIN(turn) FROM rng_checkpoint WHERE timeline_id = ?", (timeline_id,)
            ).fetchone()
            raise ForkError(
                f"This save only recorded its dice from turn {first}, so it cannot fork from turn {turn}."
            )
        return found

    def fork(self, timeline_id: str, turn: int) -> str:
        """A new timeline with everything up to the end of a turn and the RNG as it stood then (ENG-08)."""
        last = self.last_turn(timeline_id)
        if not 0 <= turn <= last:
            raise ForkError(f"There is no turn {turn} to fork from; this timeline has turns 0 to {last}.")
        rng_state = self.rng_state_at(timeline_id, turn)
        tid = uuid.uuid4().hex
        with self.conn:
            self.conn.execute(
                "INSERT INTO timeline (id, parent_id, fork_turn, seed, rng_state, rules_version, created_at)"
                " SELECT ?, id, ?, seed, ?, rules_version, ? FROM timeline WHERE id = ?",
                (tid, turn, json.dumps(rng_state), datetime.now(UTC).isoformat(), timeline_id),
            )
            for table, columns, limit in _FORK_COPIES:
                self.conn.execute(
                    f"INSERT INTO {table} (timeline_id, {columns}) SELECT ?, {columns} FROM {table}"
                    f" WHERE timeline_id = ? AND {limit} <= ?",
                    (tid, timeline_id, turn),
                )
        return tid

    def append_event(self, timeline_id: str, turn: int, type_: str, payload: dict[str, Any]) -> int:
        with self.conn:
            (seq,) = self.conn.execute(
                "SELECT COALESCE(MAX(seq) + 1, 0) FROM event WHERE timeline_id = ?", (timeline_id,)
            ).fetchone()
            self.conn.execute(
                "INSERT INTO event (timeline_id, seq, turn, type, payload_json) VALUES (?, ?, ?, ?, ?)",
                (timeline_id, seq, turn, type_, json.dumps(payload, sort_keys=True)),
            )
        return int(seq)

    def latest_timeline(self) -> str | None:
        row = self.conn.execute(
            "SELECT id FROM timeline ORDER BY created_at DESC, rowid DESC LIMIT 1"
        ).fetchone()
        return str(row[0]) if row else None

    def last_turn(self, timeline_id: str) -> int:
        (turn,) = self.conn.execute(
            "SELECT COALESCE(MAX(turn), 0) FROM turn WHERE timeline_id = ?", (timeline_id,)
        ).fetchone()
        return int(turn)

    def rng_state(self, timeline_id: str) -> dict[str, Any]:
        row = self.conn.execute("SELECT rng_state FROM timeline WHERE id = ?", (timeline_id,)).fetchone()
        state: dict[str, Any] = json.loads(row[0])
        return state

    def load_state(self, timeline_id: str) -> GameState:
        """Rebuild the state from the nearest snapshot and the events after it (ENG-06)."""
        row = self.conn.execute(
            "SELECT turn, state_json FROM snapshot WHERE timeline_id = ? ORDER BY turn DESC LIMIT 1",
            (timeline_id,),
        ).fetchone()
        start = GameState.model_validate_json(row[1]) if row else None
        after = row[0] if row else -1
        records = self.conn.execute(
            "SELECT type, payload_json FROM event WHERE timeline_id = ? AND turn > ? ORDER BY seq",
            (timeline_id, after),
        ).fetchall()
        try:
            return replay(((r[0], json.loads(r[1])) for r in records), start)
        except ValueError as exc:  # Never guess at a log this build cannot read (GAME-05).
            raise SaveError(f"Timeline {timeline_id[:8]} cannot be read by this build: {exc}") from exc

    def recent_turns(self, timeline_id: str, count: int) -> list[tuple[str, str]]:
        rows = self.conn.execute(
            "SELECT player_input, narration FROM turn WHERE timeline_id = ? ORDER BY turn DESC LIMIT ?",
            (timeline_id, count),
        ).fetchall()
        return [(r[0], r[1]) for r in reversed(rows)]

    def commit_events(
        self, timeline_id: str, turn: int, events: Iterable[EventRecord], rng_state: dict[str, Any]
    ) -> None:
        """Append player-command events and the RNG state in one transaction."""
        with self.conn:
            self._write_events(timeline_id, turn, events, rng_state)

    def commit_turn(
        self,
        timeline_id: str,
        record: TurnRecord,
        events: Iterable[EventRecord],
        rng_state: dict[str, Any],
        state: GameState,
    ) -> None:
        """Write a whole turn, or nothing (OPS-03). Every tenth turn also stores a snapshot."""
        with self.conn:
            self._write_events(timeline_id, record.turn, events, rng_state)
            self.conn.execute(
                "INSERT INTO turn (timeline_id, turn, player_input, narration, is_fallback, tokens_in,"
                " tokens_cached, tokens_out) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    timeline_id,
                    record.turn,
                    record.player_input,
                    record.narration,
                    int(record.is_fallback),
                    record.tokens_in,
                    record.tokens_cached,
                    record.tokens_out,
                ),
            )
            if record.turn % SNAPSHOT_EVERY == 0:
                self.conn.execute(
                    "INSERT INTO snapshot (timeline_id, turn, state_json) VALUES (?, ?, ?)",
                    (timeline_id, record.turn, state.model_dump_json()),
                )

    def _write_events(
        self, timeline_id: str, turn: int, events: Iterable[EventRecord], rng_state: dict[str, Any]
    ) -> None:
        (seq,) = self.conn.execute(
            "SELECT COALESCE(MAX(seq) + 1, 0) FROM event WHERE timeline_id = ?", (timeline_id,)
        ).fetchone()
        for offset, (type_, payload) in enumerate(events):
            self.conn.execute(
                "INSERT INTO event (timeline_id, seq, turn, type, payload_json) VALUES (?, ?, ?, ?, ?)",
                (timeline_id, seq + offset, turn, type_, json.dumps(payload, sort_keys=True)),
            )
        before = self.rng_state(timeline_id)
        moved = {stream: state for stream, state in rng_state.items() if before.get(stream) != state}
        self._record_rng(timeline_id, turn, moved)
        self.conn.execute(
            "UPDATE timeline SET rng_state = ? WHERE id = ?", (json.dumps(rng_state), timeline_id)
        )

    def events(self, timeline_id: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT seq, turn, type, payload_json FROM event WHERE timeline_id = ? ORDER BY seq",
            (timeline_id,),
        ).fetchall()
        return [{"seq": r[0], "turn": r[1], "type": r[2], "payload": json.loads(r[3])} for r in rows]
