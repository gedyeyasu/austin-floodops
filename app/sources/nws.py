from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from app.models import FloodEvent


NWS_ALERTS_URL = "https://api.weather.gov/alerts/active?area=TX"


def _parse_datetime(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


async def fetch_nws_alerts(user_agent: str, limit: int = 20) -> list[FloodEvent]:
    headers = {"User-Agent": user_agent, "Accept": "application/geo+json"}
    async with httpx.AsyncClient(timeout=20, headers=headers, follow_redirects=True) as client:
        response = await client.get(NWS_ALERTS_URL)
        response.raise_for_status()
        payload: dict[str, Any] = response.json()

    events: list[FloodEvent] = []
    for feature in payload.get("features", [])[:limit]:
        properties = feature.get("properties", {})
        event_name = str(properties.get("event") or "Weather alert")
        if "flood" not in event_name.lower() and "flash" not in event_name.lower():
            continue
        geometry = feature.get("geometry") or {}
        coords = geometry.get("coordinates") if geometry else None
        longitude = latitude = None
        if geometry.get("type") == "Point" and isinstance(coords, list) and len(coords) >= 2:
            longitude, latitude = coords[:2]
        events.append(
            FloodEvent(
                source="nws",
                observed_at=_parse_datetime(properties.get("sent") or properties.get("effective")),
                kind="weather_alert",
                title=event_name,
                severity=str(properties.get("severity") or "unknown").lower(),
                location=properties.get("areaDesc"),
                latitude=latitude,
                longitude=longitude,
                provenance_url=properties.get("id") or NWS_ALERTS_URL,
                raw=feature,
                mode="live",
            )
        )
    return events
