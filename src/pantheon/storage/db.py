"""SQLite storage (architecture section 5). WAL mode; every write is one transaction (OPS-03).

The event table is the only source of game state (ENG-06). Saves carry a schema version;
a newer save is refused and never written to (ENG-10, GAME-05).
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pantheon.engine.version import RULES_VERSION, SCHEMA_VERSION


class SaveError(RuntimeError):
    """A save file this version of the game must not open."""


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
"""


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
        if existed:
            version = cls._read_version(conn)
            if version is not None and version > SCHEMA_VERSION:
                conn.close()
                raise SaveError(
                    f"{path} was saved by a newer version of Pantheon (schema {version} > {SCHEMA_VERSION})."
                )
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        with conn:
            conn.executescript(_SCHEMA)
            conn.execute(
                "INSERT OR IGNORE INTO meta (key, value) VALUES ('schema_version', ?)", (str(SCHEMA_VERSION),)
            )
        return cls(conn)

    @staticmethod
    def _read_version(conn: sqlite3.Connection) -> int | None:
        try:
            row = conn.execute("SELECT value FROM meta WHERE key = 'schema_version'").fetchone()
        except sqlite3.OperationalError:
            return None

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

    def events(self, timeline_id: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT seq, turn, type, payload_json FROM event WHERE timeline_id = ? ORDER BY seq",
            (timeline_id,),
        ).fetchall()
        return [{"seq": r[0], "turn": r[1], "type": r[2], "payload": json.loads(r[3])} for r in rows]
