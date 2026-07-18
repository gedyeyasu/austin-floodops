from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncIterator

from app.models import FloodEvent
from app.sources.nws import fetch_nws_alerts
from app.sources.usgs import fetch_usgs_observations


async def collect_live(*, user_agent: str, site_id: str, parameter_codes: str) -> list[FloodEvent]:
    nws_task = fetch_nws_alerts(user_agent=user_agent)
    usgs_task = fetch_usgs_observations(site_id=site_id, parameter_codes=parameter_codes)
    results = await asyncio.gather(nws_task, usgs_task, return_exceptions=True)
    events: list[FloodEvent] = []
    for result in results:
        if isinstance(result, list):
            events.extend(result)
    return events


async def replay(path: Path) -> AsyncIterator[FloodEvent]:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        payload["mode"] = "replay"
        payload["source"] = "replay"
        yield FloodEvent.model_validate(payload)
        await asyncio.sleep(0)
