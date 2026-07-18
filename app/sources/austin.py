from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from app.models import FloodEvent

AUSTIN_CROSSINGS_URL = "https://data.austintexas.gov/resource/q3y8-2xnm.json"
AUSTIN_ROAD_CLOSURES_URL = "https://data.austintexas.gov/resource/fw5i-n4te.json"  # may vary; fallback handled


def _parse_dt(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return datetime.now(timezone.utc)


def _map_crossing_to_event(item: dict[str, Any]) -> FloodEvent | None:
    # Austin low-water crossings dataset fields: location_name, crossing_status, etc.
    # We treat blocked/closed as severe.
    name = item.get("location_name") or item.get("crossing_name") or item.get("address") or "Low-water crossing"
    status = str(item.get("status") or item.get("crossing_status") or item.get("closure_status") or "unknown").lower()
    # Some datasets have fields like location
    lat = None
    lon = None
    # geolocation sometimes in 'location' dict or separate lat/long
    loc = item.get("location") or {}
    if isinstance(loc, dict):
        lat = loc.get("latitude")
        lon = loc.get("longitude")
        try:
            if lat is not None:
                lat = float(lat)
            if lon is not None:
                lon = float(lon)
        except Exception:
            lat = None
            lon = None
    if lat is None:
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

    severity = "unknown"
    if "closed" in status or "blocked" in status or "impassable" in status:
        severity = "severe"
    elif "open" in status:
        severity = "minor"
    elif "caution" in status or "warning" in status:
        severity = "moderate"

    observed = _parse_dt(item.get("updated_at") or item.get("status_updated") or item.get("last_updated"))

    event_id = f"austin-crossing-{item.get('crossing_id') or item.get('id') or name}-{observed.isoformat()}".replace(" ", "_")

    title = f"Road closure: {name} is {status}" if status != "unknown" else f"Crossing status: {name}"

    return FloodEvent(
        event_id=event_id,
        source="austin",
        observed_at=observed,
        kind="road_closure" if "closed" in status else "crossing_status",
        title=title,
        severity=severity,
        location=name,
        latitude=lat,
        longitude=lon,
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

    event_id = f"austin-road-{item.get('id') or name}-{observed.isoformat()}".replace(" ", "_")[:120]

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
    params = {"$limit": str(limit), "$order": "updated_at DESC"}
    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        resp = await client.get(AUSTIN_CROSSINGS_URL, params=params)
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, list):
            return []
        return parse_austin_crossings(data, limit=limit)


async def fetch_austin_road_closures(limit: int = 50) -> list[FloodEvent]:
    # Try road closures endpoint; if fails, return empty not raise
    try:
        params = {"$limit": str(limit)}
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            resp = await client.get(AUSTIN_ROAD_CLOSURES_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list):
                return parse_austin_road_closures(data, limit=limit)
            return []
    except Exception:
        # Fallback: treat as no closures
        return []
