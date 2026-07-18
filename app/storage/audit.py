from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _compute_hash(prev_hash: str, payload: str, timestamp: str) -> str:
    # tamper-evident chain: SHA256(prev_hash + payload + timestamp)
    data = f"{prev_hash}{payload}{timestamp}".encode("utf-8")
    return hashlib.sha256(data).hexdigest()


class AuditChain:
    """Tamper-evident application hash chain for prototype audit review."""

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self) -> None:
        with self._connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS audit_chain (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    incident_id TEXT,
                    prev_hash TEXT NOT NULL,
                    hash TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    actor_role TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_audit_incident ON audit_chain(incident_id);
                CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_chain(created_at);
                """
            )

    def genesis(self) -> dict[str, Any] | None:
        with self._connect() as db:
            row = db.execute("SELECT * FROM audit_chain ORDER BY id ASC LIMIT 1").fetchone()
            return dict(row) if row else None

    def last_hash(self) -> str:
        with self._connect() as db:
            row = db.execute("SELECT hash FROM audit_chain ORDER BY id DESC LIMIT 1").fetchone()
            return str(row["hash"]) if row else "0" * 64

    def append(
        self,
        *,
        incident_id: str | None,
        event_type: str,
        actor_id: str,
        actor_role: str,
        payload: dict[str, Any] | str,
    ) -> dict[str, Any]:
        if isinstance(payload, dict):
            payload_str = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        else:
            payload_str = str(payload)
        timestamp = _now_iso()
        prev = self.last_hash()
        h = _compute_hash(prev, payload_str, timestamp)
        with self._connect() as db:
            cur = db.execute(
                """INSERT INTO audit_chain(incident_id, prev_hash, hash, event_type, actor_id, actor_role, payload, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (incident_id, prev, h, event_type, actor_id, actor_role, payload_str, timestamp),
            )
            new_id = cur.lastrowid
            row = db.execute("SELECT * FROM audit_chain WHERE id = ?", (new_id,)).fetchone()
            return dict(row) if row else {"id": new_id, "hash": h, "prev_hash": prev, "created_at": timestamp}

    def list_for_incident(self, incident_id: str, limit: int = 100) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT * FROM audit_chain WHERE incident_id = ? ORDER BY id ASC LIMIT ?",
                (incident_id, limit),
            ).fetchall()
        return [dict(r) for r in rows]

    def list_recent(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute("SELECT * FROM audit_chain ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]

    def verify_chain(self, incident_id: str | None = None) -> dict[str, Any]:
        """Verify hash chain integrity. If incident_id given, verify only that incident's sub-chain continuity against global chain? We verify global chain, but report incident slice."""
        with self._connect() as db:
            if incident_id:
                rows = db.execute(
                    "SELECT * FROM audit_chain WHERE incident_id = ? OR incident_id IS NULL ORDER BY id ASC",
                    (incident_id,),
                ).fetchall()
            else:
                rows = db.execute("SELECT * FROM audit_chain ORDER BY id ASC").fetchall()

        prev_expected = "0" * 64
        # Actually we need to verify against full chain: compute iteratively.
        # For simplicity, we re-walk full DB to verify continuity.
        # So fetch full chain if incident filter applied, we still need contiguous check.
        # We'll do two-phase: full chain verification + incident existence.
        full_ok = True
        errors: list[dict] = []

        # Re-fetch full ordered chain for true verification
        with self._connect() as db:
            full_rows = db.execute("SELECT id, prev_hash, hash, payload, created_at FROM audit_chain ORDER BY id ASC").fetchall()

        prev_hash = "0" * 64
        for r in full_rows:
            rid = r["id"]
            ph = r["prev_hash"]
            h = r["hash"]
            payload = r["payload"]
            ts = r["created_at"]
            if ph != prev_hash:
                full_ok = False
                errors.append({"id": rid, "error": "prev_hash_mismatch", "expected_prev": prev_hash, "got_prev": ph})
            computed = _compute_hash(ph, payload, ts)
            if computed != h:
                full_ok = False
                errors.append({"id": rid, "error": "hash_mismatch", "expected": computed, "got": h})
            prev_hash = h

        return {
            "verified": full_ok,
            "total_entries": len(full_rows),
            "incident_id": incident_id,
            "errors": errors,
            "last_hash": prev_hash,
        }
