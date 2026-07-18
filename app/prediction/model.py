from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Sequence

from app.models import FloodEvent
from app.prediction.gage_forecast import GagePoint, forecast_gage, ForecastPoint
from app.prediction.risk_predictor import risk_trajectory
from app.simulation.model import simulate_impact


@dataclass(frozen=True)
class PredictionPoint:
    horizon_minutes: int
    predicted_at: datetime
    gage_ft: float
    gage_confidence: float
    risk_level: str
    risk_score: float
    impact: dict[str, Any]
    evidence_ids: list[str]


@dataclass(frozen=True)
class PredictionResult:
    incident_id: str
    generated_at: datetime
    site_id: str
    forecast: Any  # GageForecast
    trajectory: list
    points: list[PredictionPoint]
    method: str


def _extract_gage_observations(events: list[FloodEvent]) -> list[GagePoint]:
    points: list[GagePoint] = []
    for e in events:
        if e.kind == "water_observation" and e.value is not None:
            # Normalize to ft; assume US locations ft default unless m
            unit = (e.unit or "ft").lower()
            val = float(e.value)
            if unit in {"m", "meter", "meters"}:
                val = val * 3.28084
            elif unit in {"cfs", "ft3/s", "cms"}:
                # crude screening: skip discharge for gage forecast, map via heuristic?
                # Skip cfs for now - not reliable for ft forecast
                continue
            points.append(GagePoint(observed_at=e.observed_at, value_ft=val))
    return points


def predict_future(
    events: list[FloodEvent],
    *,
    incident_id: str = "prediction",
    horizons_minutes: list[int] | None = None,
    site_id: str | None = None,
    memory_boost: float = 0.0,
) -> PredictionResult:
    """
    Predict future combining forecast_gage + risk_trajectory + simulate_impact for each horizon.
    """
    if horizons_minutes is None:
        horizons_minutes = [15, 30, 60, 120, 180]

    now = datetime.now(timezone.utc)
    # Derive site_id from USGS event or config
    if site_id is None:
        usgs = next((e for e in events if e.source == "usgs"), None)
        site_id = getattr(usgs, "location", None) or "08158000"

    gage_obs = _extract_gage_observations(events)

    gage_forecast = forecast_gage(gage_obs, horizons_minutes=horizons_minutes, site_id=site_id)

    # Determine current alert for risk trajectory
    alert_event = next((e for e in events if e.kind == "weather_alert"), None)
    alert_sev = alert_event.severity if alert_event else "unknown"
    alert_title = alert_event.title if alert_event else ""

    traj = risk_trajectory(
        gage_forecast.points,
        current_alert_severity=alert_sev,
        current_alert_title=alert_title,
        memory_boost=memory_boost,
    )

    points: list[PredictionPoint] = []
    for fp, tp in zip(gage_forecast.points, traj):
        # Simulate synthetic events for impact model at each horizon
        synthetic_events: list[FloodEvent] = list(events)  # copy
        # Add synthetic gage observation for that horizon
        synthetic_events.append(
            FloodEvent(
                event_id=f"synth-{fp.horizon_minutes}-{fp.predicted_at.isoformat()}",
                source="usgs",
                observed_at=fp.predicted_at,
                kind="water_observation",
                title=f"Predicted gage {fp.value_ft} ft",
                severity=tp.risk_level,
                value=fp.value_ft,
                unit="ft",
                provenance_url="prediction://synthetic",
                mode="live",
                location=site_id,
            )
        )
        impact_est = simulate_impact(
            synthetic_events,
            mode="live",
            scenario_id=incident_id,
            horizon_minutes=fp.horizon_minutes,
        )
        points.append(
            PredictionPoint(
                horizon_minutes=fp.horizon_minutes,
                predicted_at=fp.predicted_at,
                gage_ft=fp.value_ft,
                gage_confidence=fp.confidence,
                risk_level=tp.risk_level,
                risk_score=tp.combined_score,
                impact=impact_est.model_dump(mode="json"),
                evidence_ids=[e.event_id for e in events],
            )
        )

    return PredictionResult(
        incident_id=incident_id,
        generated_at=now,
        site_id=site_id,
        forecast=gage_forecast,
        trajectory=traj,
        points=points,
        method=f"forecast-{gage_forecast.method}+risk-trajectory+threshold-v1",
    )
