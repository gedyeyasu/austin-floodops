from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
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
    nws_task = fetch_nws_alerts(user_agent=user_agent)
    usgs_task = fetch_usgs_observations(site_id=site_id, parameter_codes=parameter_codes)
    results = await asyncio.gather(nws_task, usgs_task, return_exceptions=True)
    events: list[FloodEvent] = []
    status: dict[str, dict[str, Any]] = {}
    for source, result in zip(("nws", "usgs"), results, strict=True):
        if isinstance(result, list):
            events.extend(result)
            status[source] = {"status": "ok", "events": len(result)}
        else:
            status[source] = {"status": "degraded", "error": type(result).__name__}
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
