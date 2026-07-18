from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from typing import Any

import httpx

from app.models import FloodEvent


TXDOT_CLOSURES_URL = "https://api.drivetexas.org/closures"
TXDOT_PROVENANCE_URL = "https://www.drivetexas.org"
AUSTIN_311_URL = "https://data.austintexas.gov/resource/ge9s-5vkx.json"


def _fingerprint(item: dict[str, Any]) -> str:
    payload = json.dumps(item, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


def _parse_observed(value: Any) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return datetime.now(timezone.utc)


def parse_txdot_closures(data: Any, *, limit: int = 30, mode: str = "live") -> list[FloodEvent]:
    if isinstance(data, dict):
        items = data.get("closures") or data.get("features") or []
    else:
        items = data
    if not isinstance(items, list):
        raise RuntimeError("DriveTexas returned an unsupported payload")

    events: list[FloodEvent] = []
    for item in items[:limit]:
        if not isinstance(item, dict):
            continue
        properties = item.get("properties", item)
        if not isinstance(properties, dict):
            continue
        road = properties.get("road") or properties.get("route") or "Unknown Texas road"
        reason = properties.get("reason") or properties.get("closureReason") or "Road closure"
        observed = _parse_observed(properties.get("updatedAt") or properties.get("timestamp"))
        latitude = properties.get("latitude") or properties.get("lat")
        longitude = properties.get("longitude") or properties.get("lon")
        try:
            numeric_latitude = float(latitude) if latitude is not None else None
            numeric_longitude = float(longitude) if longitude is not None else None
        except (TypeError, ValueError):
            numeric_latitude = None
            numeric_longitude = None
        events.append(
            FloodEvent(
                event_id=f"txdot-{properties.get('id') or road}-{_fingerprint(item)}".replace(" ", "_")[:140],
                source="txdot",
                observed_at=observed,
                kind="road_closure",
                title=f"TxDOT closure: {road} - {reason}",
                severity="severe" if "flood" in str(reason).lower() else "moderate",
                location=str(road),
                latitude=numeric_latitude,
                longitude=numeric_longitude,
                freshness_seconds=max(0.0, (datetime.now(timezone.utc) - observed).total_seconds()),
                provenance_url=TXDOT_PROVENANCE_URL,
                raw=item,
                mode=mode,
            )
        )
    return events


async def fetch_txdot_closures(*, limit: int = 30, mode: str = "live") -> list[FloodEvent]:
    """Fetch DriveTexas closure data or expose degradation; never synthesize live closures."""
    try:
        async with httpx.AsyncClient(
            timeout=20,
            follow_redirects=True,
            headers={"User-Agent": "AustinFloodOps/0.3"},
        ) as client:
            response = await client.get(TXDOT_CLOSURES_URL, params={"limit": limit, "type": "flood"})
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise RuntimeError(f"DriveTexas feed unavailable: {type(exc).__name__}") from exc

    return parse_txdot_closures(data, limit=limit, mode=mode)


async def fetch_austin_311(*, limit: int = 20, mode: str = "live") -> list[FloodEvent]:
    params = {"$limit": str(limit), "$where": "sr_type like '%flood%' or sr_type like '%water%'"}
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            response = await client.get(AUSTIN_311_URL, params=params)
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise RuntimeError(f"Austin 311 feed unavailable: {type(exc).__name__}") from exc
    if not isinstance(data, list):
        raise RuntimeError("Austin 311 returned an unsupported payload")

    events: list[FloodEvent] = []
    for item in data[:limit]:
        observed = _parse_observed(item.get("created_date") or item.get("status_date"))
        request_id = item.get("sr_number") or item.get("id") or _fingerprint(item)
        events.append(
            FloodEvent(
                event_id=f"austin311-{request_id}-{_fingerprint(item)}",
                source="austin_311",
                observed_at=observed,
                kind="311_report",
                title=f"Austin 311 report: {item.get('sr_type', 'Flooding')}",
                severity="moderate",
                location=item.get("location", "Austin, Texas"),
                freshness_seconds=max(0.0, (datetime.now(timezone.utc) - observed).total_seconds()),
                provenance_url="https://data.austintexas.gov/d/ge9s-5vkx",
                raw=item,
                mode=mode,
            )
        )
    return events
