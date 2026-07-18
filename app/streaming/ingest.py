from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, AsyncIterator

from app.models import FloodEvent
from app.sources.austin import fetch_austin_crossings, fetch_austin_road_closures
from app.sources.lcra import fetch_lcra_stages
from app.sources.nws import fetch_nws_alerts
from app.sources.txdot import fetch_austin_311, fetch_txdot_closures
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
    nws_task = fetch_nws_alerts(user_agent=user_agent)
    usgs_task = fetch_usgs_observations(site_id=site_id, parameter_codes=parameter_codes)
    austin_crossings_task = fetch_austin_crossings(limit=50)
    austin_roads_task = fetch_austin_road_closures(limit=30)
    lcra_task = fetch_lcra_stages(limit=15)
    txdot_task = fetch_txdot_closures(limit=20)
    austin_311_task = fetch_austin_311(limit=15)

    results = await asyncio.gather(
        nws_task, usgs_task, austin_crossings_task, austin_roads_task, lcra_task, txdot_task, austin_311_task, return_exceptions=True
    )
    events: list[FloodEvent] = []
    status: dict[str, dict[str, Any]] = {}
    source_names = ("nws", "usgs", "austin_crossings", "austin_roads", "lcra", "txdot", "austin_311")
    for source, result in zip(source_names, results, strict=True):
        if isinstance(result, list):
            events.extend(result)
            status[source] = {"status": "ok", "events": len(result)}
        else:
            status[source] = {"status": "degraded", "error": type(result).__name__, "detail": str(result)[:300]}

    # Compatibility: older heartbeat logic expecting usgs+nws keys only, but expose new ones too
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
