from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Sequence

import httpx

from app.config import settings


@dataclass(frozen=True)
class RoutePoint:
    lon: float
    lat: float
    name: str | None = None


@dataclass(frozen=True)
class EvacuationRoute:
    route_id: str
    origin: RoutePoint
    destination: RoutePoint
    distance_m: float
    duration_s: float
    geometry: dict[str, Any] | None
    steps: list[dict[str, Any]]
    method: str
    blocked_crossings_avoided: list[str]


def _haversine(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    R = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


async def _osrm_route(
    origin: RoutePoint,
    dest: RoutePoint,
    *,
    base_url: str,
    timeout: int = 15,
) -> dict[str, Any] | None:
    """
    Call OSRM router.project-osrm.org or configured OSRM_BASE_URL.
    Endpoint: {base_url}/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=full&geometries=geojson&steps=true
    """
    url = f"{base_url.rstrip('/')}/route/v1/driving/{origin.lon},{origin.lat};{dest.lon},{dest.lat}"
    params = {"overview": "full", "geometries": "geojson", "steps": "true"}
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            routes = data.get("routes") or []
            if not routes:
                return None
            r = routes[0]
            return {
                "distance": r.get("distance", 0),
                "duration": r.get("duration", 0),
                "geometry": r.get("geometry"),
                "legs": r.get("legs", []),
            }
    except Exception:
        return None


def _fallback_route(origin: RoutePoint, dest: RoutePoint, route_id: str, blocked: list[str]) -> EvacuationRoute:
    dist = _haversine(origin.lon, origin.lat, dest.lon, dest.lat)
    # assume 30 mph avg for evacuation ~13.4 m/s, but slower if flood
    duration = dist / 10.0  # 36 km/h ~ 10 m/s conservative
    return EvacuationRoute(
        route_id=route_id,
        origin=origin,
        destination=dest,
        distance_m=round(dist, 1),
        duration_s=round(duration, 1),
        geometry={
            "type": "LineString",
            "coordinates": [[origin.lon, origin.lat], [dest.lon, dest.lat]],
        },
        steps=[
            {"maneuver": {"type": "depart", "location": [origin.lon, origin.lat]}, "name": origin.name or "origin"},
            {"maneuver": {"type": "arrive", "location": [dest.lon, dest.lat]}, "name": dest.name or "destination"},
        ],
        method="haversine-fallback",
        blocked_crossings_avoided=blocked,
    )


async def compute_evacuation_routes(
    blocked_crossings: Sequence[dict[str, Any]] | None,
    *,
    origins: Sequence[RoutePoint] | None = None,
    safe_destinations: Sequence[RoutePoint] | None = None,
    osrm_base_url: str | None = None,
) -> list[EvacuationRoute]:
    """
    Compute evacuation routes for blocked crossings.
    If origins/destinations not supplied, use Austin central safe points.
    """
    base_url = osrm_base_url or settings.osrm_base_url or "https://router.project-osrm.org"

    # Default safe destinations: Austin high ground
    if safe_destinations is None:
        safe_destinations = [
            RoutePoint(lon=-97.7431, lat=30.2672, name="Exercise destination A"),
            RoutePoint(lon=-97.75, lat=30.32, name="Exercise destination B"),
        ]
    if origins is None:
        # Derive origins from blocked crossings if provided, else generic
        if blocked_crossings:
            origins_list: list[RoutePoint] = []
            for bc in blocked_crossings:
                lon = bc.get("longitude") or bc.get("lon")
                lat = bc.get("latitude") or bc.get("lat")
                if lon and lat:
                    try:
                        origins_list.append(RoutePoint(lon=float(lon), lat=float(lat), name=str(bc.get("location") or bc.get("name") or "blocked crossing")))
                    except Exception:
                        continue
            if not origins_list:
                origins_list = [RoutePoint(lon=-97.8, lat=30.12, name="Onion Creek vicinity")]
            origins = origins_list
        else:
            origins = [RoutePoint(lon=-97.8, lat=30.12, name="Onion Creek vicinity")]

    blocked_names = []
    if blocked_crossings:
        for bc in blocked_crossings:
            blocked_names.append(str(bc.get("location") or bc.get("name") or bc.get("target") or "crossing"))

    routes: list[EvacuationRoute] = []
    for i, origin in enumerate(origins):
        for j, dest in enumerate(safe_destinations):
            osrm_data = None
            if settings.has_osrm:
                osrm_data = await _osrm_route(origin, dest, base_url=base_url)
            if osrm_data:
                steps = []
                for leg in osrm_data.get("legs", []):
                    steps.extend(leg.get("steps", []))
                routes.append(
                    EvacuationRoute(
                        route_id=f"evac-{i}-{j}",
                        origin=origin,
                        destination=dest,
                        distance_m=float(osrm_data.get("distance", 0)),
                        duration_s=float(osrm_data.get("duration", 0)),
                        geometry=osrm_data.get("geometry"),
                        steps=steps,
                        method=f"osrm:{base_url}",
                        blocked_crossings_avoided=blocked_names,
                    )
                )
            else:
                routes.append(_fallback_route(origin, dest, route_id=f"evac-{i}-{j}-fallback", blocked=blocked_names))

    return routes
