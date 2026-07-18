from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

# Gage thresholds in feet for Austin area screening
GAGE_THRESHOLDS_FT: dict[str, float] = {
    "low": 5.0,
    "moderate": 8.0,
    "high": 11.0,
    "catastrophic": 13.0,
}


def _gage_value_to_score(value_ft: float) -> float:
    """Map gage ft to 0-1 score using thresholds piecewise linear."""
    thresholds = GAGE_THRESHOLDS_FT
    if value_ft <= thresholds["low"]:
        return max(0.0, (value_ft / thresholds["low"]) * 0.3)
    if value_ft <= thresholds["moderate"]:
        # 5->0.3 to 8->0.6
        frac = (value_ft - thresholds["low"]) / (thresholds["moderate"] - thresholds["low"])
        return 0.3 + frac * 0.3
    if value_ft <= thresholds["high"]:
        frac = (value_ft - thresholds["moderate"]) / (thresholds["high"] - thresholds["moderate"])
        return 0.6 + frac * 0.25
    if value_ft <= thresholds["catastrophic"]:
        frac = (value_ft - thresholds["high"]) / (thresholds["catastrophic"] - thresholds["high"])
        return 0.85 + frac * 0.1
    # above catastrophic
    extra = min(1.0, (value_ft - thresholds["catastrophic"]) / 5.0 * 0.05 + 0.95)
    return min(1.0, extra)


def _alert_signal(severity: str, title: str) -> float:
    t = (title or "").lower()
    s = (severity or "").lower()
    # explicit mapping
    if "flash flood emergency" in t:
        return 1.0
    if "flash flood warning" in t:
        return 0.9
    if "flood warning" in t:
        return 0.75
    if "flood watch" in t:
        return 0.45
    if "flood" in t:
        return 0.6
    if s in {"extreme", "severe"}:
        return 0.85
    if s == "moderate":
        return 0.5
    return 0.2


def _risk_level_from_score(score: float) -> str:
    if score >= 0.85:
        return "catastrophic"
    if score >= 0.65:
        return "high"
    if score >= 0.35:
        return "moderate"
    if score > 0.05:
        return "low"
    return "unknown"


@dataclass(frozen=True)
class RiskPoint:
    horizon_minutes: int
    gage_ft: float
    gage_score: float
    alert_score: float
    combined_score: float
    risk_level: str


def risk_trajectory(
    forecast_points: Sequence,  # list[ForecastPoint]
    *,
    current_alert_severity: str = "unknown",
    current_alert_title: str = "",
    memory_boost: float = 0.0,
) -> list[RiskPoint]:
    """
    Combine alert + gage + memory boost into risk trajectory.
    """
    alert_score = _alert_signal(current_alert_severity, current_alert_title)
    trajectory: list[RiskPoint] = []
    for fp in forecast_points:
        # fp should have value_ft
        gage_ft = getattr(fp, "value_ft", 0.0)
        gage_score = _gage_value_to_score(gage_ft)
        # synergy: if both alert and gage high, boost 0.1
        synergy = 0.1 if (alert_score > 0.5 and gage_score > 0.5) else 0.0
        combined = max(0.0, min(1.0, 0.5 * alert_score + 0.5 * gage_score + synergy + memory_boost))
        # memory_boost from operator memory context roughly +0.1 if relevant
        trajectory.append(
            RiskPoint(
                horizon_minutes=getattr(fp, "horizon_minutes", 0),
                gage_ft=gage_ft,
                gage_score=round(gage_score, 3),
                alert_score=round(alert_score, 3),
                combined_score=round(combined, 3),
                risk_level=_risk_level_from_score(combined),
            )
        )
    return trajectory
