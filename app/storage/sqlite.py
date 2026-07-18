from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from app.models import FloodEvent, IncidentDecision, OperatorFeedback


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
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
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

    def save_events(self, events: list[FloodEvent]) -> int:
        with self._connect() as db:
            for event in events:
                db.execute(
                    "INSERT OR IGNORE INTO events(event_id, observed_at, source, payload) VALUES (?, ?, ?, ?)",
                    (event.event_id, event.observed_at.isoformat(), event.source, event.model_dump_json()),
                )
        return len(events)

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

    def add_feedback(self, incident_id: str, feedback: OperatorFeedback) -> int:
        with self._connect() as db:
            cursor = db.execute(
                "INSERT INTO feedback(incident_id, correction, outcome) VALUES (?, ?, ?)",
                (incident_id, feedback.correction, feedback.outcome),
            )
            db.execute(
                "INSERT INTO memories(rule, source_incident_id) VALUES (?, ?)",
                (feedback.correction, incident_id),
            )
            return int(cursor.lastrowid)

    def active_memories(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT id, rule, source_incident_id, created_at FROM memories WHERE active = 1 ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

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
