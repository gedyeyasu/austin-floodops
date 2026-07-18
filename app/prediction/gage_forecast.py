from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Sequence
import math


@dataclass(frozen=True)
class GagePoint:
    observed_at: datetime
    value_ft: float


@dataclass(frozen=True)
class ForecastPoint:
    horizon_minutes: int
    predicted_at: datetime
    value_ft: float
    confidence: float


@dataclass(frozen=True)
class GageForecast:
    site_id: str
    points: list[ForecastPoint]
    slope_ft_per_hour: float
    intercept_ft: float
    r_squared: float | None
    method: str


def _linear_regression(x: list[float], y: list[float]) -> tuple[float, float, float | None]:
    """
    OLS slope ft/hour. x = hours since start, y = ft.
    Returns slope, intercept, r2.
    """
    n = len(x)
    if n < 2:
        return 0.0, (y[0] if y else 0.0), None
    mean_x = sum(x) / n
    mean_y = sum(y) / n
    num = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
    den = sum((xi - mean_x) ** 2 for xi in x)
    if den == 0:
        return 0.0, mean_y, None
    slope = num / den
    intercept = mean_y - slope * mean_x
    # r2
    ss_tot = sum((yi - mean_y) ** 2 for yi in y)
    if ss_tot == 0:
        r2 = 1.0
    else:
        ss_res = sum((yi - (slope * xi + intercept)) ** 2 for xi, yi in zip(x, y))
        r2 = max(0.0, 1 - ss_res / ss_tot)
    return slope, intercept, r2


def forecast_gage(
    observations: Sequence[GagePoint],
    *,
    horizons_minutes: list[int] | None = None,
    site_id: str = "unknown",
    max_points: int = 20,
    lookback_hours: int = 12,
) -> GageForecast:
    """
    Forecast gage from last 20 obs last 12h.
    Uses OLS linear regression.
    """
    if horizons_minutes is None:
        horizons_minutes = [15, 30, 60, 120, 180]

    now = datetime.now(timezone.utc)
    filtered = [p for p in observations if (now - p.observed_at).total_seconds() <= lookback_hours * 3600]
    # sort oldest first
    filtered.sort(key=lambda p: p.observed_at)
    # take last max_points
    if len(filtered) > max_points:
        filtered = filtered[-max_points:]

    if not filtered:
        # No data -> return flat zero forecast with low confidence
        pts = [
            ForecastPoint(horizon_minutes=h, predicted_at=now + timedelta(minutes=h), value_ft=0.0, confidence=0.0)
            for h in horizons_minutes
        ]
        return GageForecast(site_id=site_id, points=pts, slope_ft_per_hour=0.0, intercept_ft=0.0, r_squared=None, method="no-data")

    # convert to x hours elapsed
    t0 = filtered[0].observed_at
    x = [(p.observed_at - t0).total_seconds() / 3600.0 for p in filtered]
    y = [p.value_ft for p in filtered]

    slope, intercept, r2 = _linear_regression(x, y)

    # forecast: predict from last point's time
    last_t = filtered[-1].observed_at
    last_x = (last_t - t0).total_seconds() / 3600.0
    # baseline: use last observed as anchor but trend via slope
    # predicted = intercept + slope * (last_x + horizon_hours)
    # However we want continuity: if last observed deviates from regression, blend?
    # Simple: use regression line.
    points: list[ForecastPoint] = []
    for h in horizons_minutes:
        horizon_hours = h / 60.0
        future_x = last_x + horizon_hours
        pred_ft = intercept + slope * future_x
        # Clamp negative gage unrealistic to 0
        pred_ft = max(0.0, pred_ft)
        # confidence heuristic: based on r2 and num points and horizon
        base_conf = 0.5
        if r2 is not None:
            base_conf = 0.3 + 0.6 * r2
        # decay with horizon
        decay = 1.0 - (h / 360.0) * 0.5  # at 3h, 0.5 decay factor
        conf = max(0.1, min(0.95, base_conf * decay * (0.5 + 0.5 * min(1.0, len(filtered) / 10))))
        points.append(
            ForecastPoint(horizon_minutes=h, predicted_at=last_t + timedelta(minutes=h), value_ft=round(pred_ft, 2), confidence=round(conf, 3))
        )

    return GageForecast(
        site_id=site_id,
        points=points,
        slope_ft_per_hour=round(slope, 4),
        intercept_ft=round(intercept, 3),
        r_squared=round(r2, 3) if r2 is not None else None,
        method=f"ols-last{len(filtered)}-12h",
    )
