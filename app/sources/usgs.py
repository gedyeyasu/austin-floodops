from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from app.models import FloodEvent


USGS_IV_URL = "https://waterservices.usgs.gov/nwis/iv/"


def _parse_usgs_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def parse_usgs_observations(payload: dict[str, Any], site_id: str, parameter_codes: str, *, mode: str = "live") -> list[FloodEvent]:
    events: list[FloodEvent] = []
    for series in payload.get("value", {}).get("timeSeries", []):
        source_info = series.get("sourceInfo", {})
        variable = series.get("variable", {})
        values = series.get("values", [{}])[0].get("value", [])
        if not values:
            continue
        latest = values[-1]
        value = latest.get("value")
        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            continue
        observed_at = _parse_usgs_time(latest["dateTime"])
        unit = variable.get("unit", {}).get("unitCode")
        label = variable.get("variableDescription") or variable.get("variableName") or "USGS observation"
        parameter = variable.get("variableCode", [{}])[0].get("value") or parameter_codes
        events.append(
            FloodEvent(
                event_id=f"usgs-{site_id}-{parameter}-{observed_at.isoformat()}",
                source="usgs",
                observed_at=observed_at,
                kind="water_observation",
                title=label,
                location=source_info.get("siteName") or f"USGS {site_id}",
                latitude=(source_info.get("geoLocation") or {}).get("geogLocation", {}).get("latitude"),
                longitude=(source_info.get("geoLocation") or {}).get("geogLocation", {}).get("longitude"),
                value=numeric_value,
                unit=unit,
                provenance_url=f"{USGS_IV_URL}?sites={site_id}&parameterCd={parameter_codes}",
                raw=series,
                mode=mode,
            )
        )
    return events


async def fetch_usgs_observations(site_id: str, parameter_codes: str) -> list[FloodEvent]:
    params = {
        "format": "json",
        "sites": site_id,
        "parameterCd": parameter_codes,
        "siteStatus": "all",
    }
    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        response = await client.get(USGS_IV_URL, params=params)
        response.raise_for_status()
        payload: dict[str, Any] = response.json()
    return parse_usgs_observations(payload, site_id, parameter_codes)
