from __future__ import annotations

from app.models import FloodEvent, ImpactEstimate


MODEL_VERSION = "threshold-v1"


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _alert_signal(events: list[FloodEvent]) -> float:
    scores = {
        "flash flood warning": 0.95,
        "flash flood emergency": 1.0,
        "flood warning": 0.8,
        "flood watch": 0.5,
        "special weather statement": 0.25,
    }
    return max((score for event in events for label, score in scores.items() if label in event.title.lower()), default=0.0)


def _gage_signal(events: list[FloodEvent]) -> tuple[float, bool]:
    observations = [event for event in events if event.kind == "water_observation" and event.value is not None]
    if not observations:
        return 0.0, False
    signals: list[float] = []
    for event in observations:
        unit = (event.unit or "").lower()
        if unit in {"ft", "feet", "foot"}:
            signals.append(_clamp(event.value / 15.0))
        elif unit in {"m", "meter", "meters"}:
            signals.append(_clamp(event.value / 4.5))
        elif unit in {"cfs", "ft3/s", "cms"}:
            signals.append(_clamp(event.value / (30_000.0 if unit != "cms" else 850.0)))
        else:
            # Unknown units are still evidence, but are deliberately capped.
            signals.append(0.35)
    return max(signals), True


def _risk_level(score: float) -> str:
    if score >= 0.9:
        return "catastrophic"
    if score >= 0.7:
        return "high"
    if score >= 0.4:
        return "moderate"
    if score > 0:
        return "low"
    return "unknown"


def simulate_impact(events: list[FloodEvent], *, mode: str, scenario_id: str, horizon_minutes: int) -> ImpactEstimate:
    """Produce a transparent scenario estimate from observed signals.

    This is intentionally not a hydrologic forecast. It is a deterministic
    triage model that makes every threshold visible to operators and can be
    replaced by a calibrated model once a jurisdiction supplies local data.
    """
    alert = _alert_signal(events)
    gage, has_gage = _gage_signal(events)
    synergy = 0.1 if alert and has_gage else 0.0
    score = _clamp(0.6 * alert + 0.4 * gage + synergy)
    hazard_events = [event for event in events if event.kind in {"weather_alert", "water_observation", "road_closure", "311_report"}]
    confidence = _clamp(0.35 + (0.25 if alert else 0.0) + (0.25 if has_gage else 0.0) + min(0.15, 0.05 * max(0, len(hazard_events) - 2)))
    warning = next((event for event in events if event.kind == "weather_alert"), None)
    location = warning.location if warning and warning.location else "the observed flood area"
    crossings = [f"Priority low-water crossings near {location}"] if score >= 0.4 else []
    assumptions = [
        "Alert scores are based on event titles from NWS or replay evidence.",
        "Gage normalization uses fixed screening thresholds (15 ft, 4.5 m, 30,000 cfs, or 850 cms).",
        "Exposure is a screening estimate, not a census or hydraulic inundation result.",
    ]
    return ImpactEstimate(
        scenario_id=scenario_id,
        mode=mode,  # type: ignore[arg-type]
        horizon_minutes=horizon_minutes,
        risk_level=_risk_level(score),  # type: ignore[arg-type]
        severity_score=round(score, 3),
        confidence=round(confidence, 3),
        estimated_depth_m=round(0.05 + score * 0.95, 2),
        exposed_people=round(score * 2500),
        route_delay_minutes=round(score * 60),
        blocked_crossings=crossings,
        evidence_event_ids=[event.event_id for event in events],
        assumptions=assumptions,
        model_version=MODEL_VERSION,
    )
