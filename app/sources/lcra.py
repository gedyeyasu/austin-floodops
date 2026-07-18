from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from app.models import FloodEvent


LCRA_HYDROMET_URL = "https://hydromet.lcra.org/api/v1/river-stages"
LCRA_PROVENANCE_URL = "https://hydromet.lcra.org"


def _parse_observed(value: Any) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


async def fetch_lcra_stages(*, limit: int = 20, mode: str = "live") -> list[FloodEvent]:
    """Fetch LCRA observations or report a degraded source; never fabricate live readings."""
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            response = await client.get(LCRA_HYDROMET_URL, params={"limit": limit})
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise RuntimeError(f"LCRA Hydromet unavailable: {type(exc).__name__}") from exc

    items = data.get("items", data.get("gauges", data)) if isinstance(data, dict) else data
    if not isinstance(items, list):
        raise RuntimeError("LCRA Hydromet returned an unsupported payload")

    events: list[FloodEvent] = []
    for item in items[:limit]:
        if not isinstance(item, dict):
            continue
        stage = item.get("stage") or item.get("value") or item.get("riverStage")
        try:
            numeric_stage = float(stage)
        except (TypeError, ValueError):
            continue
        observed = _parse_observed(item.get("observedAt") or item.get("timestamp"))
        site_name = item.get("siteName") or item.get("location") or "LCRA gauge"
        site_id = item.get("siteId") or item.get("id") or site_name
        events.append(
            FloodEvent(
                event_id=f"lcra-{site_id}-{observed.isoformat()}",
                source="lcra",
                observed_at=observed,
                kind="water_observation",
                title=f"LCRA {site_name} stage {numeric_stage} ft",
                severity="severe" if numeric_stage > 15 else "moderate" if numeric_stage > 8 else "low",
                location=str(site_name),
                latitude=item.get("latitude"),
                longitude=item.get("longitude"),
                value=numeric_stage,
                unit="ft",
                freshness_seconds=max(0.0, (datetime.now(timezone.utc) - observed).total_seconds()),
                provenance_url=LCRA_PROVENANCE_URL,
                raw=item,
                mode=mode,
            )
        )
    return events
