from __future__ import annotations

from typing import Any

import httpx


FLOODPLAIN_URL = "https://data.austintexas.gov/resource/3p2e-ps67.json"


# Fallback synthetic polygons around Austin watersheds (approx boxes)
FALLBACK_FLOODPLAIN: list[dict[str, Any]] = [
    {
        "type": "Feature",
        "properties": {"name": "Onion Creek 100yr synthetic", "source": "fallback", "flood_zone": "100yr"},
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    [-97.85, 30.15],
                    [-97.75, 30.15],
                    [-97.75, 30.10],
                    [-97.85, 30.10],
                    [-97.85, 30.15],
                ]
            ],
        },
    },
    {
        "type": "Feature",
        "properties": {"name": "Shoal Creek 100yr synthetic", "source": "fallback", "flood_zone": "100yr"},
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    [-97.77, 30.35],
                    [-97.72, 30.35],
                    [-97.72, 30.30],
                    [-97.77, 30.30],
                    [-97.77, 30.35],
                ]
            ],
        },
    },
    {
        "type": "Feature",
        "properties": {"name": "Barton Creek 100yr synthetic", "source": "fallback", "flood_zone": "100yr"},
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    [-97.85, 30.28],
                    [-97.78, 30.28],
                    [-97.78, 30.24],
                    [-97.85, 30.24],
                    [-97.85, 30.28],
                ]
            ],
        },
    },
]


def _to_geojson(features: list[dict[str, Any]]) -> dict[str, Any]:
    # Normalize Austin open data rows to GeoJSON FeatureCollection if needed
    geo_features: list[dict[str, Any]] = []
    for item in features:
        # If already GeoJSON feature
        if item.get("type") == "Feature" and "geometry" in item:
            geo_features.append(item)
            continue
        # If Socrata row with location geometry?
        # Example fields: shape, the_geom, geometry, floodplain
        geom = None
        # Try to parse WKT? For simplicity ignore; use fallback if not parseable
        # If item has latitude/longitude, create point buffer approx?
        # Here we attempt to create point feature if location present
        loc = item.get("location") or item.get("point") or {}
        lat = None
        lon = None
        if isinstance(loc, dict):
            lat = loc.get("latitude")
            lon = loc.get("longitude")
        if lat and lon:
            try:
                geo_features.append(
                    {
                        "type": "Feature",
                        "properties": {k: str(v)[:200] for k, v in item.items() if k != "location"},
                        "geometry": {"type": "Point", "coordinates": [float(lon), float(lat)]},
                    }
                )
            except Exception:
                continue
    if not geo_features:
        # Return fallback
        return {"type": "FeatureCollection", "features": FALLBACK_FLOODPLAIN, "fallback": True}
    return {"type": "FeatureCollection", "features": geo_features, "fallback": False}


async def fetch_floodplain(limit: int = 100) -> dict[str, Any]:
    """
    Fetch floodplain from https://data.austintexas.gov/resource/3p2e-ps67.json with fallback synthetic polygons.
    Returns GeoJSON FeatureCollection.
    """
    params = {"$limit": str(limit)}
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            resp = await client.get(FLOODPLAIN_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list) and data:
                fc = _to_geojson(data)
                if fc["features"]:
                    return fc
            # else fallback
    except Exception:
        pass

    return {"type": "FeatureCollection", "features": FALLBACK_FLOODPLAIN, "fallback": True, "source_url": FLOODPLAIN_URL}
