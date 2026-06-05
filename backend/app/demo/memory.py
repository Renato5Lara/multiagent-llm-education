from __future__ import annotations

import json
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class DemoMemoryRecord:
    id: int
    session_id: str
    agent: str
    key: str
    value: dict[str, Any]
    confidence: float
    created_at: str


class SQLiteSharedMemoryStore:
    """SQLite-backed shared memory plus replay event log for demo sessions."""

    def __init__(self, path: str | Path | None = None):
        default_path = Path(__file__).resolve().parents[2] / "demo_sessions.sqlite3"
        self.path = str(path or default_path)
        self._lock = threading.Lock()
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS demo_sessions (
                    session_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    seed INTEGER NOT NULL,
                    student_json TEXT NOT NULL,
                    module_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    completed_at TEXT
                );

                CREATE TABLE IF NOT EXISTS demo_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS demo_memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    agent TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value_json TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS ix_demo_events_session_id
                    ON demo_events(session_id, id);
                CREATE INDEX IF NOT EXISTS ix_demo_memory_session_id
                    ON demo_memory(session_id, id);
                """
            )

    def create_session(self, session_id: str, seed: int, student: dict, module: dict) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO demo_sessions
                    (session_id, status, seed, student_json, module_json, created_at, completed_at)
                VALUES (?, ?, ?, ?, ?, ?, NULL)
                """,
                (
                    session_id,
                    "running",
                    seed,
                    json.dumps(student, ensure_ascii=False),
                    json.dumps(module, ensure_ascii=False),
                    utc_now(),
                ),
            )

    def complete_session(self, session_id: str) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                "UPDATE demo_sessions SET status = ?, completed_at = ? WHERE session_id = ?",
                ("completed", utc_now(), session_id),
            )

    def append_event(self, session_id: str, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        created_at = utc_now()
        with self._lock, self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO demo_events (session_id, event_type, payload_json, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (session_id, event_type, json.dumps(payload, ensure_ascii=False), created_at),
            )
            event_id = int(cur.lastrowid)
        return {
            "id": event_id,
            "session_id": session_id,
            "type": event_type,
            "payload": payload,
            "created_at": created_at,
        }

    def publish_memory(
        self,
        session_id: str,
        agent: str,
        key: str,
        value: dict[str, Any],
        confidence: float,
    ) -> DemoMemoryRecord:
        created_at = utc_now()
        with self._lock, self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO demo_memory (session_id, agent, key, value_json, confidence, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    agent,
                    key,
                    json.dumps(value, ensure_ascii=False),
                    max(0.0, min(1.0, confidence)),
                    created_at,
                ),
            )
            record_id = int(cur.lastrowid)
        return DemoMemoryRecord(record_id, session_id, agent, key, value, confidence, created_at)

    def events(self, session_id: str, after_id: int = 0) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, session_id, event_type, payload_json, created_at
                FROM demo_events
                WHERE session_id = ? AND id > ?
                ORDER BY id ASC
                """,
                (session_id, after_id),
            ).fetchall()
        return [
            {
                "id": int(row["id"]),
                "session_id": row["session_id"],
                "type": row["event_type"],
                "payload": json.loads(row["payload_json"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def replay(self, session_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            session = conn.execute(
                "SELECT * FROM demo_sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        if session is None:
            return None
        return {
            "session": {
                "session_id": session["session_id"],
                "status": session["status"],
                "seed": session["seed"],
                "student": json.loads(session["student_json"]),
                "module": json.loads(session["module_json"]),
                "created_at": session["created_at"],
                "completed_at": session["completed_at"],
            },
            "events": self.events(session_id),
        }

    def latest_session_id(self) -> str | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT session_id FROM demo_sessions ORDER BY created_at DESC LIMIT 1"
            ).fetchone()
        return row["session_id"] if row else None
