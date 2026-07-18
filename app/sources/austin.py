from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from typing import Any

import httpx

from app.models import FloodEvent

AUSTIN_CROSSINGS_URL = "https://data.austintexas.gov/resource/q6kt-v2zm.json"
AUSTIN_ROAD_CLOSURES_URL = "https://data.austintexas.gov/resource/fw5i-n4te.json"  # may change; failure is surfaced


def _parse_dt(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return datetime.now(timezone.utc)


def _content_fingerprint(item: dict[str, Any]) -> str:
    payload = json.dumps(item, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


def _map_crossing_to_event(item: dict[str, Any]) -> FloodEvent | None:
    name = item.get("crossing_description") or item.get("location_name") or item.get("crossing_name") or item.get("address") or "Low-water crossing"
    crossing_type = item.get("crossing_type") or "Unknown"
    gage_number = item.get("gage_number") or ""
    raw_status = item.get("status") or item.get("crossing_status") or item.get("closure_status")
    status = str(raw_status or "reference only").lower()
    lat = None
    lon = None
    try:
        if item.get("latitude"):
            lat = float(item["latitude"])
    except Exception:
        pass
    geom = item.get("the_geom") or {}
    coords = geom.get("coordinates", []) if isinstance(geom, dict) else []
    if lat is None and len(coords) >= 2:
        lon, lat = coords[0], coords[1]
    elif lat is None:
        try:
            if item.get("latitude"):
                lat = float(item["latitude"])
        except Exception:
            pass
    if lon is None:
        try:
            if item.get("longitude"):
                lon = float(item["longitude"])
        except Exception:
            pass
    if lon is None and len(coords) >= 2:
        lon = coords[0]

    severity = "unknown"
    if "closed" in status or "blocked" in status or "impassable" in status:
        severity = "severe"
    elif "open" in status:
        severity = "minor"

    object_id = item.get("objectid") or item.get("unique_gis_id") or name
    observed = _parse_dt(item.get("updated_at") or item.get("status_updated") or item.get("modified_date"))
    event_id = f"austin-crossing-{object_id}-{_content_fingerprint(item)}"

    return FloodEvent(
        event_id=event_id,
        source="austin",
        observed_at=observed,
        kind="crossing_status" if raw_status is not None else "crossing_reference",
        title=f"Crossing reference: {name} ({crossing_type})" if raw_status is None else f"Crossing status: {name} ({status})",
        severity=severity,
        location=name,
        latitude=lat,
        longitude=lon,
        value=None,
        unit=None,
        freshness_seconds=max(0.0, (datetime.now(timezone.utc) - observed).total_seconds()) if any(item.get(key) for key in ("updated_at", "status_updated", "modified_date")) else None,
        provenance_url=AUSTIN_CROSSINGS_URL,
        raw=item,
        mode="live",
    )


def _map_road_closure_to_event(item: dict[str, Any]) -> FloodEvent | None:
    name = item.get("location") or item.get("street_name") or item.get("address") or "Road closure"
    status = str(item.get("status") or item.get("closure_status") or "closed").lower()
    observed = _parse_dt(item.get("closure_start") or item.get("updated_at") or item.get("reported"))
    lat = None
    lon = None
    try:
        if item.get("latitude"):
            lat = float(item["latitude"])
        if item.get("longitude"):
            lon = float(item["longitude"])
    except Exception:
        pass
    loc = item.get("location_1") or item.get("geolocation") or {}
    if isinstance(loc, dict):
        try:
            if loc.get("latitude"):
                lat = float(loc["latitude"])
            if loc.get("longitude"):
                lon = float(loc["longitude"])
        except Exception:
            pass

    event_id = f"austin-road-{item.get('id') or name}-{_content_fingerprint(item)}".replace(" ", "_")[:120]

    return FloodEvent(
        event_id=event_id,
        source="austin",
        observed_at=observed,
        kind="road_closure",
        title=f"Austin road closure: {name} ({status})",
        severity="severe" if "closed" in status else "moderate",
        location=name,
        latitude=lat,
        longitude=lon,
        freshness_seconds=max(0.0, (datetime.now(timezone.utc) - observed).total_seconds()),
        provenance_url=AUSTIN_ROAD_CLOSURES_URL,
        raw=item,
        mode="live",
    )


def parse_austin_crossings(payload: list[dict[str, Any]], limit: int = 50) -> list[FloodEvent]:
    events: list[FloodEvent] = []
    for item in payload[:limit]:
        ev = _map_crossing_to_event(item)
        if ev:
            events.append(ev)
    return events


def parse_austin_road_closures(payload: list[dict[str, Any]], limit: int = 50) -> list[FloodEvent]:
    events: list[FloodEvent] = []
    for item in payload[:limit]:
        ev = _map_road_closure_to_event(item)
        if ev:
            events.append(ev)
    return events


async def fetch_austin_crossings(limit: int = 50) -> list[FloodEvent]:
    params = {"$limit": str(limit)}
    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        resp = await client.get(AUSTIN_CROSSINGS_URL, params=params)
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, list):
            raise RuntimeError("Austin crossing endpoint returned a non-list payload")
        return parse_austin_crossings(data, limit=limit)


async def fetch_austin_road_closures(limit: int = 50) -> list[FloodEvent]:
    params = {"$limit": str(limit)}
    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        resp = await client.get(AUSTIN_ROAD_CLOSURES_URL, params=params)
        resp.raise_for_status()
        data = resp.json()
    if not isinstance(data, list):
        raise RuntimeError("Austin road-closure endpoint returned a non-list payload")
    return parse_austin_road_closures(data, limit=limit)
