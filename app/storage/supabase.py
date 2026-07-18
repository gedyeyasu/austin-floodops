from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from app.models import FloodEvent, IncidentDecision, OperatorFeedback


class SupabaseUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class SupabaseConfig:
    url: str = ""
    service_role_key: str = ""

    @property
    def configured(self) -> bool:
        return bool(self.url and self.service_role_key)


class SupabaseStore:
    """Small REST adapter for the server-side Supabase ledger.

    SQLite remains the source of truth for local replay. This adapter is
    intentionally additive: a remote outage never hides a locally recorded
    incident, while the probe makes the remote state observable to operators.
    """

    def __init__(self, config: SupabaseConfig):
        self.config = config

    def _headers(self) -> dict[str, str]:
        return {
            "apikey": self.config.service_role_key,
            "Authorization": f"Bearer {self.config.service_role_key}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates,return=minimal",
        }

    async def _request(self, method: str, table: str, *, payload: Any = None, params: dict[str, str] | None = None) -> httpx.Response:
        if not self.config.configured:
            raise SupabaseUnavailable("Supabase URL and service-role key are not configured.")
        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                response = await client.request(
                    method,
                    f"{self.config.url.rstrip('/')}/rest/v1/{table}",
                    headers=self._headers(),
                    json=payload,
                    params=params,
                )
                response.raise_for_status()
                return response
        except httpx.HTTPError as exc:
            raise SupabaseUnavailable(f"Supabase {table} request failed: {exc}") from exc

    async def probe(self) -> dict[str, Any]:
        response = await self._request("GET", "events", params={"select": "event_id", "limit": "1"})
        return {"status": "verified", "http_status": response.status_code}

    async def save_events(self, events: list[FloodEvent]) -> None:
        if not events:
            return
        await self._request(
            "POST",
            "events",
            payload=[
                {
                    "event_id": event.event_id,
                    "observed_at": event.observed_at.isoformat(),
                    "source": event.source,
                    "payload": event.model_dump(mode="json"),
                }
                for event in events
            ],
        )

    async def save_decision(self, decision: IncidentDecision) -> None:
        await self._request(
            "POST",
            "decisions",
            payload={
                "incident_id": decision.incident_id,
                "created_at": decision.created_at.isoformat(),
                "payload": decision.model_dump(mode="json"),
            },
        )

    async def save_feedback(self, incident_id: str, feedback: OperatorFeedback) -> None:
        await self._request(
            "POST",
            "feedback",
            payload={"incident_id": incident_id, "correction": feedback.correction, "outcome": feedback.outcome},
        )
