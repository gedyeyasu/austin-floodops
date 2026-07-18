from datetime import datetime, timezone

import pytest

from app.model.nemotron import IntegrationUnavailable, _extract_json
from app.models import FloodEvent, IncidentDecision, ProposedAction
from app.responders.cap import build_cap_alert
from app.simulation.model import simulate_impact
from app.safety.policy import evaluate
from app.storage.sqlite import Store


def event(event_id: str = "e1") -> FloodEvent:
    return FloodEvent(
        event_id=event_id,
        source="replay",
        observed_at=datetime.now(timezone.utc),
        kind="weather_alert",
        title="Flash Flood Warning",
        provenance_url="https://example.test/evidence",
        mode="replay",
    )


def decision() -> IncidentDecision:
    return IncidentDecision(
        mode="replay",
        scenario_id="test",
        summary="Crossing risk is rising.",
        risk_level="high",
        confidence=0.9,
        evidence_event_ids=["e1"],
        citations=["e1"],
        proposed_action=ProposedAction(
            action_type="close_crossing_and_reroute",
            target="Test crossing",
            rationale="Flood warning and rising gage.",
        ),
        policy_status="approval_required",
        model_name="test",
    )


def test_json_extraction_handles_fenced_output():
    assert _extract_json("```json\n{\"risk_level\": \"high\"}\n```")["risk_level"] == "high"


def test_missing_nvidia_key_is_fail_closed():
    with pytest.raises(IntegrationUnavailable):
        import asyncio
        asyncio.run(__import__("app.model.nemotron", fromlist=["assess_incident"]).assess_incident(
            api_key="", base_url="https://example.test/v1", model="test", events=[event()], scenario_id="test"
        ))


def test_policy_requires_approval_then_allows_reversible_action():
    assessed = decision()
    assert evaluate(assessed).status == "approval_required"
    assert evaluate(assessed, operator_approved=True).status == "allowed"


def test_store_is_idempotent_and_versions_feedback(tmp_path):
    store = Store(tmp_path / "floodops.sqlite3")
    store.save_events([event(), event()])
    assert len(store.list_events()) == 1
    assessed = decision()
    store.save_decision(assessed)
    store.add_feedback(assessed.incident_id, __import__("app.models", fromlist=["OperatorFeedback"]).OperatorFeedback(correction="Require a second gage before closure.", outcome="helpful"))
    assert store.active_memories()[0]["rule"].startswith("Require a second")


def test_replay_simulation_exposes_assumptions_and_high_risk():
    events = [
        event("warning"),
        FloodEvent(
            event_id="gage",
            source="replay",
            observed_at=datetime.now(timezone.utc),
            kind="water_observation",
            title="Gage height",
            value=12.4,
            unit="ft",
            provenance_url="https://example.test/gage",
            mode="replay",
        ),
    ]
    events[0].title = "Flash Flood Warning"
    estimate = simulate_impact(events, mode="replay", scenario_id="test", horizon_minutes=60)
    assert estimate.risk_level == "catastrophic"
    assert estimate.evidence_event_ids == ["warning", "gage"]
    assert estimate.assumptions


def test_cap_export_is_xml_and_contains_incident_id():
    assessed = decision()
    payload = build_cap_alert(assessed)
    assert payload.startswith(b"<?xml")
    assert assessed.incident_id.encode() in payload
