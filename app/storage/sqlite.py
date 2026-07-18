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
                CREATE TABLE IF NOT EXISTS resources (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    name TEXT NOT NULL,
                    location TEXT,
                    latitude REAL,
                    longitude REAL,
                    capacity INTEGER DEFAULT 0,
                    assigned_incident_id TEXT,
                    assigned_at TEXT,
                    last_maintenance TEXT,
                    notes TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS resource_assignments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    resource_id TEXT NOT NULL,
                    incident_id TEXT NOT NULL,
                    assigned_by TEXT NOT NULL,
                    assigned_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    released_at TEXT,
                    distance_m REAL,
                    eta_minutes INTEGER,
                    FOREIGN KEY(resource_id) REFERENCES resources(id)
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

    # --- Texas Gov Resource Management ---
    def _seed_texas_resources(self):
        """Seed default Texas resources if table empty — barricades, high-water vehicles, shelters, personnel for Travis County / Austin EOC"""
        with self._connect() as db:
            count = db.execute("SELECT COUNT(*) as c FROM resources").fetchone()["c"]
            if count > 0:
                return
            # Texas resources: Austin area
            default_resources = [
                # Barricades
                ("barricade-001", "barricade", "available", "Barricade Unit 1 - Onion Creek Crossing", "Onion Creek Blvd & E Stassney", 30.185, -97.750, 0, None, None, None, "Standard flood barricade, reflective, TXDOT compliant"),
                ("barricade-002", "barricade", "available", "Barricade Unit 2 - Shoal Creek", "Shoal Creek Blvd & Steck", 30.380, -97.738, 0, None, None, None, "High-visibility barricade"),
                ("barricade-003", "barricade", "available", "Barricade Unit 3 - Barton Springs", "Barton Springs Rd & Zilker", 30.264, -97.768, 0, None, None, None, "Water-filled barricade"),
                ("barricade-004", "barricade", "deployed", "Barricade Unit 4 - East 12th", "E 12th St @ Onion Creek", 30.270, -97.700, 0, "demo-incident", None, None, "Deployed during night market scenario"),
                # High-water vehicles
                ("hwv-001", "high_water_vehicle", "available", "High-Water Vehicle 1", "Austin EOC", 30.2672, -97.7431, 6, None, None, None, "LMTV 6-person, high-water rescue"),
                ("hwv-002", "high_water_vehicle", "available", "High-Water Vehicle 2", "Travis County Yard", 30.300, -97.700, 6, None, None, None, "High-water rescue, swiftwater certified crew"),
                # Shelters
                ("shelter-austin-se", "shelter", "available", "Austin SE Shelter - Travis Co", "Austin SE, 30.25,-97.70", 30.25, -97.70, 200, None, None, None, "200-person capacity, pet-friendly, ADA compliant"),
                ("shelter-dripping", "shelter", "available", "Dripping Springs Shelter", "Dripping Springs, TX", 30.190, -98.086, 150, None, None, None, "150-person, backup generator"),
                # Personnel
                ("crew-001", "personnel", "available", "Swiftwater Rescue Crew Alpha", "Austin Fire Dept", 30.2672, -97.7431, 4, None, None, None, "4-person swiftwater rescue, certified"),
                ("crew-002", "personnel", "available", "Traffic Control Crew Bravo", "Austin Transportation", 30.2672, -97.7431, 2, None, None, None, "2-person traffic control, barricade trained"),
                # Gates
                ("gate-onion-1", "gate", "available", "Onion Creek Low-Water Gate", "Onion Creek, Austin", 30.185, -97.750, 0, None, None, None, "Automated gate, remote close capable"),
                # Pumps
                ("pump-001", "pump", "available", "High-Volume Pump 1", "Austin Water", 30.2672, -97.7431, 0, None, None, None, "1000 GPM, trailer mounted"),
            ]
            for r in default_resources:
                db.execute(
                    """INSERT OR IGNORE INTO resources(id, type, status, name, location, latitude, longitude, capacity, assigned_incident_id, assigned_at, last_maintenance, notes)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    r,
                )

    def list_resources(self, type_filter: str | None = None, status_filter: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        self._seed_texas_resources()
        with self._connect() as db:
            query = "SELECT * FROM resources WHERE 1=1"
            params = []
            if type_filter:
                query += " AND type = ?"
                params.append(type_filter)
            if status_filter:
                query += " AND status = ?"
                params.append(status_filter)
            query += " ORDER BY type, status, name LIMIT ?"
            params.append(limit)
            rows = db.execute(query, tuple(params)).fetchall()
        return [dict(row) for row in rows]

    def get_resource(self, resource_id: str) -> dict[str, Any] | None:
        with self._connect() as db:
            row = db.execute("SELECT * FROM resources WHERE id = ?", (resource_id,)).fetchone()
        return dict(row) if row else None

    def assign_resource(self, resource_id: str, incident_id: str, assigned_by: str, distance_m: float | None = None, eta_minutes: int | None = None) -> bool:
        with self._connect() as db:
            res = db.execute("SELECT status FROM resources WHERE id = ?", (resource_id,)).fetchone()
            if not res or res["status"] not in {"available", "staged"}:
                return False
            db.execute(
                "UPDATE resources SET status='deployed', assigned_incident_id=?, assigned_at=CURRENT_TIMESTAMP, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (incident_id, resource_id),
            )
            db.execute(
                "INSERT INTO resource_assignments(resource_id, incident_id, assigned_by, distance_m, eta_minutes) VALUES (?, ?, ?, ?, ?)",
                (resource_id, incident_id, assigned_by, distance_m, eta_minutes),
            )
            return db.total_changes > 0

    def release_resource(self, resource_id: str) -> bool:
        with self._connect() as db:
            cursor = db.execute(
                "UPDATE resources SET status='available', assigned_incident_id=NULL, assigned_at=NULL, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (resource_id,),
            )
            db.execute("UPDATE resource_assignments SET released_at=CURRENT_TIMESTAMP WHERE resource_id=? AND released_at IS NULL", (resource_id,))
            return cursor.rowcount > 0

    def create_resource(self, resource: dict[str, Any]) -> str:
        with self._connect() as db:
            db.execute(
                """INSERT INTO resources(id, type, status, name, location, latitude, longitude, capacity, notes)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    resource.get("id"),
                    resource.get("type"),
                    resource.get("status", "available"),
                    resource.get("name"),
                    resource.get("location"),
                    resource.get("latitude"),
                    resource.get("longitude"),
                    resource.get("capacity", 0),
                    resource.get("notes", ""),
                ),
            )
            return resource.get("id")

    def list_assignments(self, incident_id: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        with self._connect() as db:
            if incident_id:
                rows = db.execute(
                    "SELECT * FROM resource_assignments WHERE incident_id=? ORDER BY assigned_at DESC LIMIT ?",
                    (incident_id, limit),
                ).fetchall()
            else:
                rows = db.execute("SELECT * FROM resource_assignments ORDER BY assigned_at DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]
