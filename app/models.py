from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class FloodEvent(BaseModel):
    model_config = ConfigDict(extra="allow")

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    source: Literal["nws", "usgs", "austin", "replay"]
    observed_at: datetime
    received_at: datetime = Field(default_factory=utc_now)
    kind: str
    title: str
    severity: str = "unknown"
    location: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    value: float | None = None
    unit: str | None = None
    freshness_seconds: float | None = None
    provenance_url: str
    raw: dict[str, Any] = Field(default_factory=dict)
    mode: Literal["live", "replay"] = "live"


class IncidentRequest(BaseModel):
    mode: Literal["live", "replay"] = "live"
    scenario_id: str = "east-austin-night-market"


class SimulationRequest(BaseModel):
    mode: Literal["live", "replay"] = "replay"
    scenario_id: str = "east-austin-night-market"
    horizon_minutes: int = Field(default=60, ge=5, le=360)


class ImpactEstimate(BaseModel):
    scenario_id: str
    generated_at: datetime = Field(default_factory=utc_now)
    mode: Literal["live", "replay"]
    horizon_minutes: int
    risk_level: Literal["low", "moderate", "high", "catastrophic", "unknown"]
    severity_score: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    estimated_depth_m: float = Field(ge=0)
    exposed_people: int = Field(ge=0)
    route_delay_minutes: int = Field(ge=0)
    blocked_crossings: list[str]
    evidence_event_ids: list[str]
    assumptions: list[str]
    model_version: str


class FirstResponderDispatchRequest(BaseModel):
    confirm: bool = False


class ProposedAction(BaseModel):
    action_type: Literal["close_crossing_and_reroute", "request_approval", "quarantine"]
    target: str
    rationale: str
    approval_required: bool = True
    reversible: bool = True


class IncidentDecision(BaseModel):
    incident_id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: datetime = Field(default_factory=utc_now)
    mode: Literal["live", "replay"]
    scenario_id: str
    summary: str
    risk_level: Literal["low", "moderate", "high", "catastrophic", "unknown"]
    confidence: float = Field(ge=0, le=1)
    evidence_event_ids: list[str]
    citations: list[str]
    proposed_action: ProposedAction
    policy_status: Literal["approval_required", "blocked", "allowed"]
    model_name: str
    raw_model_response: dict[str, Any] = Field(default_factory=dict)


class OperatorFeedback(BaseModel):
    correction: str = Field(min_length=3, max_length=1000)
    outcome: Literal["helpful", "not_helpful", "unknown"] = "unknown"


class PlaybookRule(BaseModel):
    trigger: str = Field(min_length=3, max_length=500)
    action: str = Field(min_length=3, max_length=500)
    rationale: str = Field(min_length=3, max_length=1000)
    confidence: float = Field(ge=0, le=1)
    context_tags: list[str] = Field(default_factory=list, max_length=20)


class IntegrationStatus(BaseModel):
    name: str
    configured: bool
    verified: bool
    detail: str


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded", "blocked"]
    mode: str
    integrations: list[IntegrationStatus]
