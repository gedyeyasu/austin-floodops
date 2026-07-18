from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from app.models import FloodEvent, IncidentDecision, OperatorFeedback, PlaybookRule


class Store:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init(self) -> None:
        with self._connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY,
                    observed_at TEXT NOT NULL,
                    source TEXT NOT NULL,
                    payload TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS decisions (
                    incident_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    payload TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    incident_id TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    correction TEXT NOT NULL,
                    outcome TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rule TEXT NOT NULL,
                    source_incident_id TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    trigger TEXT NOT NULL DEFAULT '',
                    action TEXT NOT NULL DEFAULT '',
                    rationale TEXT NOT NULL DEFAULT '',
                    confidence REAL NOT NULL DEFAULT 0.5,
                    context_tags TEXT NOT NULL DEFAULT '[]',
                    version INTEGER NOT NULL DEFAULT 1,
                    retired_at TEXT
                );
                CREATE TABLE IF NOT EXISTS heartbeat_state (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS deliveries (
                    incident_id TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    delivered_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    response_status INTEGER NOT NULL,
                    PRIMARY KEY (incident_id, channel)
                );
                """
            )
            columns = {row["name"] for row in db.execute("PRAGMA table_info(memories)").fetchall()}
            additions = {
                "trigger": "TEXT NOT NULL DEFAULT ''",
                "action": "TEXT NOT NULL DEFAULT ''",
                "rationale": "TEXT NOT NULL DEFAULT ''",
                "confidence": "REAL NOT NULL DEFAULT 0.5",
                "context_tags": "TEXT NOT NULL DEFAULT '[]'",
                "version": "INTEGER NOT NULL DEFAULT 1",
                "retired_at": "TEXT",
            }
            for name, definition in additions.items():
                if name not in columns:
                    db.execute(f"ALTER TABLE memories ADD COLUMN {name} {definition}")

    def save_events(self, events: list[FloodEvent]) -> int:
        with self._connect() as db:
            for event in events:
                db.execute(
                    "INSERT OR IGNORE INTO events(event_id, observed_at, source, payload) VALUES (?, ?, ?, ?)",
                    (event.event_id, event.observed_at.isoformat(), event.source, event.model_dump_json()),
                )
        return len(events)

    def filter_new_events(self, events: list[FloodEvent]) -> list[FloodEvent]:
        if not events:
            return []
        placeholders = ",".join("?" for _ in events)
        with self._connect() as db:
            rows = db.execute(
                f"SELECT event_id FROM events WHERE event_id IN ({placeholders})",
                tuple(event.event_id for event in events),
            ).fetchall()
        existing = {str(row["event_id"]) for row in rows}
        seen: set[str] = set()
        new_events: list[FloodEvent] = []
        for event in events:
            if event.event_id in existing or event.event_id in seen:
                continue
            seen.add(event.event_id)
            new_events.append(event)
        return new_events

    def save_decision(self, decision: IncidentDecision) -> None:
        with self._connect() as db:
            db.execute(
                "INSERT OR REPLACE INTO decisions(incident_id, created_at, payload) VALUES (?, ?, ?)",
                (decision.incident_id, decision.created_at.isoformat(), decision.model_dump_json()),
            )

    def list_events(self, limit: int = 50) -> list[FloodEvent]:
        with self._connect() as db:
            rows = db.execute("SELECT payload FROM events ORDER BY observed_at DESC LIMIT ?", (limit,)).fetchall()
        return [FloodEvent.model_validate(json.loads(row["payload"])) for row in rows]

    def list_decisions(self, limit: int = 20) -> list[IncidentDecision]:
        with self._connect() as db:
            rows = db.execute("SELECT payload FROM decisions ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [IncidentDecision.model_validate(json.loads(row["payload"])) for row in rows]

    def get_decision(self, incident_id: str) -> IncidentDecision | None:
        with self._connect() as db:
            row = db.execute("SELECT payload FROM decisions WHERE incident_id = ?", (incident_id,)).fetchone()
        return IncidentDecision.model_validate(json.loads(row["payload"])) if row else None

    def events_by_id(self, event_ids: list[str]) -> list[FloodEvent]:
        if not event_ids:
            return []
        placeholders = ",".join("?" for _ in event_ids)
        with self._connect() as db:
            rows = db.execute(
                f"SELECT payload FROM events WHERE event_id IN ({placeholders})",
                tuple(event_ids),
            ).fetchall()
        return [FloodEvent.model_validate(json.loads(row["payload"])) for row in rows]

    def add_feedback(self, incident_id: str, feedback: OperatorFeedback) -> int:
        with self._connect() as db:
            cursor = db.execute(
                "INSERT INTO feedback(incident_id, correction, outcome) VALUES (?, ?, ?)",
                (incident_id, feedback.correction, feedback.outcome),
            )
            return int(cursor.lastrowid)

    def list_feedback(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT id, incident_id, created_at, correction, outcome FROM feedback ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def add_memory(self, rule: PlaybookRule, source_incident_id: str) -> int:
        with self._connect() as db:
            row = db.execute(
                "SELECT COALESCE(MAX(version), 0) AS version FROM memories WHERE source_incident_id = ?",
                (source_incident_id,),
            ).fetchone()
            version = int(row["version"]) + 1
            cursor = db.execute(
                """INSERT INTO memories(
                    rule, source_incident_id, trigger, action, rationale,
                    confidence, context_tags, version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    f"IF {rule.trigger} THEN {rule.action}",
                    source_incident_id,
                    rule.trigger,
                    rule.action,
                    rule.rationale,
                    rule.confidence,
                    json.dumps(rule.context_tags),
                    version,
                ),
            )
            return int(cursor.lastrowid)

    def list_memories(self, limit: int = 50, *, active_only: bool = False) -> list[dict[str, Any]]:
        where = "WHERE active = 1" if active_only else ""
        with self._connect() as db:
            rows = db.execute(
                f"""SELECT id, rule, source_incident_id, active, created_at, trigger,
                    action, rationale, confidence, context_tags, version, retired_at
                    FROM memories {where} ORDER BY id DESC LIMIT ?""",
                (limit,),
            ).fetchall()
        memories = [dict(row) for row in rows]
        for memory in memories:
            memory["active"] = bool(memory["active"])
            try:
                memory["context_tags"] = json.loads(memory["context_tags"] or "[]")
            except json.JSONDecodeError:
                memory["context_tags"] = []
        return memories

    def active_memories(self, limit: int = 20) -> list[dict[str, Any]]:
        return self.list_memories(limit, active_only=True)

    def retire_memory(self, memory_id: int) -> bool:
        with self._connect() as db:
            cursor = db.execute(
                "UPDATE memories SET active = 0, retired_at = CURRENT_TIMESTAMP WHERE id = ? AND active = 1",
                (memory_id,),
            )
            return cursor.rowcount == 1

    def retire_memories_by_source(self, source_incident_id: str) -> int:
        with self._connect() as db:
            cursor = db.execute(
                "UPDATE memories SET active = 0, retired_at = CURRENT_TIMESTAMP WHERE source_incident_id = ? AND active = 1",
                (source_incident_id,),
            )
            return cursor.rowcount

    def heartbeat_state(self) -> dict[str, Any]:
        with self._connect() as db:
            rows = db.execute("SELECT key, value FROM heartbeat_state").fetchall()
        result: dict[str, Any] = {}
        for row in rows:
            try:
                result[str(row["key"])] = json.loads(row["value"])
            except json.JSONDecodeError:
                result[str(row["key"])] = row["value"]
        return result

    def save_heartbeat_state(self, state: dict[str, Any]) -> None:
        with self._connect() as db:
            for key, value in state.items():
                db.execute(
                    """INSERT INTO heartbeat_state(key, value, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP""",
                    (key, json.dumps(value)),
                )

    def delivery_exists(self, incident_id: str, channel: str) -> bool:
        with self._connect() as db:
            row = db.execute(
                "SELECT 1 FROM deliveries WHERE incident_id = ? AND channel = ?",
                (incident_id, channel),
            ).fetchone()
        return row is not None

    def record_delivery(self, incident_id: str, channel: str, response_status: int) -> None:
        with self._connect() as db:
            db.execute(
                "INSERT OR IGNORE INTO deliveries(incident_id, channel, response_status) VALUES (?, ?, ?)",
                (incident_id, channel, response_status),
            )
