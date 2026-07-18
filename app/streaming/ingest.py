from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, AsyncIterator

from app.models import FloodEvent
from app.sources.nws import fetch_nws_alerts
from app.sources.usgs import fetch_usgs_observations


async def collect_live(*, user_agent: str, site_id: str, parameter_codes: str) -> list[FloodEvent]:
    events, _ = await collect_live_with_status(
        user_agent=user_agent,
        site_id=site_id,
        parameter_codes=parameter_codes,
    )
    return events


async def collect_live_with_status(
    *, user_agent: str, site_id: str, parameter_codes: str
) -> tuple[list[FloodEvent], dict[str, dict[str, Any]]]:
    # Lazy import Austin sources to avoid circular/hard fails if not installed
    try:
        from app.sources.austin import fetch_austin_crossings, fetch_austin_road_closures
    except Exception:

        async def fetch_austin_crossings(limit=50):  # type: ignore
            return []

        async def fetch_austin_road_closures(limit=50):  # type: ignore
            return []

    nws_task = fetch_nws_alerts(user_agent=user_agent)
    usgs_task = fetch_usgs_observations(site_id=site_id, parameter_codes=parameter_codes)
    austin_crossings_task = fetch_austin_crossings(limit=50)
    austin_roads_task = fetch_austin_road_closures(limit=30)

    results = await asyncio.gather(nws_task, usgs_task, austin_crossings_task, austin_roads_task, return_exceptions=True)
    events: list[FloodEvent] = []
    status: dict[str, dict[str, Any]] = {}
    source_names = ("nws", "usgs", "austin_crossings", "austin_roads")
    for source, result in zip(source_names, results, strict=True):
        if isinstance(result, list):
            events.extend(result)
            status[source] = {"status": "ok", "events": len(result)}
        else:
            status[source] = {"status": "degraded", "error": type(result).__name__, "detail": str(result)[:300]}

    # Compatibility: keep older heartbeat logic expecting usgs+nws keys only,
    # but also expose new ones - heartbeat aggregator will handle both.
    return events, status


async def replay(path: Path) -> AsyncIterator[FloodEvent]:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        payload["mode"] = "replay"
        yield FloodEvent.model_validate(payload)
        await asyncio.sleep(0)
