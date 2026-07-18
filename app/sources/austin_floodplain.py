from __future__ import annotations

from typing import Any

import httpx


FLOODPLAIN_URL = "https://data.austintexas.gov/resource/3p2e-ps67.json"


def _to_geojson(features: list[dict[str, Any]]) -> dict[str, Any]:
    geo_features: list[dict[str, Any]] = []
    for item in features:
        if item.get("type") == "Feature" and item.get("geometry"):
            geo_features.append(item)
            continue
        location = item.get("location") or item.get("point") or {}
        if not isinstance(location, dict):
            continue
        latitude = location.get("latitude")
        longitude = location.get("longitude")
        if latitude is None or longitude is None:
            continue
        try:
            geo_features.append(
                {
                    "type": "Feature",
                    "properties": {key: str(value)[:200] for key, value in item.items() if key != "location"},
                    "geometry": {"type": "Point", "coordinates": [float(longitude), float(latitude)]},
                }
            )
        except (TypeError, ValueError):
            continue
    return {
        "type": "FeatureCollection",
        "features": geo_features,
        "source_url": FLOODPLAIN_URL,
        "synthetic": False,
    }


async def fetch_floodplain(limit: int = 100) -> dict[str, Any]:
    """Fetch parseable Austin floodplain records; fail visibly instead of drawing synthetic geometry."""
    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        response = await client.get(FLOODPLAIN_URL, params={"$limit": str(limit)})
        response.raise_for_status()
        data = response.json()
    if not isinstance(data, list):
        raise RuntimeError("Austin floodplain endpoint returned an unsupported payload")
    collection = _to_geojson(data)
    if not collection["features"]:
        raise RuntimeError("Austin floodplain endpoint returned no parseable geometry")
    return collection
