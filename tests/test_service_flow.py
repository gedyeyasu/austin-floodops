from dataclasses import replace
from datetime import datetime, timezone

import pytest

from app.config import settings
from app.models import FloodEvent, IncidentDecision, OperatorFeedback, PlaybookRule, ProposedAction
from app.service import FloodOpsService
from app.security.hiddenlayer import HiddenLayerUnavailable
from app.storage.sqlite import Store


@pytest.mark.asyncio
async def test_gather_assess_approve_feedback_reassess_flow(tmp_path, monkeypatch):
    local = replace(
        settings,
        db_path=tmp_path / "flow.sqlite3",
        kafka_bootstrap_servers="",
        supabase_url="",
        supabase_service_role_key="",
        hiddenlayer_interactions_url="",
        hiddenlayer_api_key="",
        hiddenlayer_client_id="",
        hiddenlayer_client_secret="",
    )
    service = FloodOpsService(local, Store(local.db_path))
    evidence = [FloodEvent(event_id="flow-1", source="nws", observed_at=datetime.now(timezone.utc), kind="weather_alert", title="Flash Flood Warning", severity="severe", location="Onion Creek", provenance_url="https://example.test/flow-1")]
    contexts = []

    async def gather(mode, scenario_id): return evidence
    async def assessor(**kwargs):
        contexts.append(kwargs["memory_context"])
        return IncidentDecision(mode="live", scenario_id=kwargs["scenario_id"], summary="Warning detected.", risk_level="high", confidence=0.9, evidence_event_ids=["flow-1"], citations=["flow-1"], proposed_action=ProposedAction(action_type="request_approval", target="Onion Creek", rationale="Official warning."), policy_status="approval_required", model_name="mock-nemotron")
    async def reflect(**kwargs):
        return PlaybookRule(trigger="flash flood warning at Onion Creek", action="request closure approval", rationale="operator confirmed exposure", confidence=0.95, context_tags=["flash", "flood", "onion"])

    monkeypatch.setattr(service, "gather", gather)
    monkeypatch.setattr("app.service.assess_incident", assessor)
    monkeypatch.setattr("app.service.reflect_on_feedback", reflect)
    _, first, error = await service.assess("live", "flow")
    assert error is None and first is not None
    assert service.approve(first).status == "allowed"
    feedback = await service.record_feedback(first, OperatorFeedback(correction="Close earlier when Onion Creek is warned.", outcome="helpful"))
    assert feedback["reflection_status"] == "created"
    _, second, error = await service.assess("live", "flow")
    assert error is None and second is not None
    assert "Rule" in contexts[-1]
    assert second.raw_model_response["learning"]["retrieved_memories"]


@pytest.mark.asyncio
async def test_hiddenlayer_scans_three_inputs_before_model_and_three_outputs_after(tmp_path, monkeypatch):
    local = replace(
        settings,
        db_path=tmp_path / "hiddenlayer.sqlite3",
        kafka_bootstrap_servers="",
        supabase_url="",
        supabase_service_role_key="",
        hiddenlayer_interactions_url="",
        hiddenlayer_api_key="",
        hiddenlayer_client_id="client-id",
        hiddenlayer_client_secret="client-secret",
    )
    service = FloodOpsService(local, Store(local.db_path))
    evidence = [FloodEvent(event_id="hl-1", source="nws", observed_at=datetime.now(timezone.utc), kind="weather_alert", title="Flash Flood Warning", severity="severe", location="Onion Creek", provenance_url="https://example.test/hl-1")]
    order: list[str] = []
    model_request_payloads: list[dict] = []

    async def scan(**kwargs):
        boundary = kwargs["requester_id"].removeprefix("floodops-")
        order.append(boundary)
        if boundary == "model_request":
            model_request_payloads.append(kwargs["interaction"])
        return {"status": "scanned", "fired_signals": []}

    async def assessor(events, scenario_id, memories):
        order.append("model")
        return IncidentDecision(mode="live", scenario_id=scenario_id, summary="Warning detected.", risk_level="high", confidence=0.9, evidence_event_ids=["hl-1"], citations=["hl-1"], proposed_action=ProposedAction(action_type="request_approval", target="Onion Creek", rationale="Official warning."), policy_status="approval_required", model_name="mock-nemotron")

    monkeypatch.setattr("app.service.evaluate_interaction_v2", scan)
    _, assessed, error = await service.assess_events(evidence, "hiddenlayer-test", model_assessor=assessor)
    assert error is None and assessed is not None
    assert order == ["ingested_content", "user_prompt_memory", "model_request", "model", "tool_call", "tool_result", "final_answer"]
    assert model_request_payloads[0]["guided_json"]["properties"]["citations"]["items"]["enum"] == ["hl-1"]
    assert assessed.raw_model_response["security"]["hiddenlayer"]["status"] == "verified"
    assert set(assessed.raw_model_response["security"]["hiddenlayer"]["boundaries_scanned"]) == {
        "ingested_content", "user_prompt_memory", "model_request", "tool_call", "tool_result", "final_answer"
    }


@pytest.mark.asyncio
async def test_hiddenlayer_scan_failure_blocks_before_model(tmp_path, monkeypatch):
    local = replace(
        settings,
        db_path=tmp_path / "hiddenlayer-fail.sqlite3",
        kafka_bootstrap_servers="",
        supabase_url="",
        supabase_service_role_key="",
        hiddenlayer_client_id="client-id",
        hiddenlayer_client_secret="client-secret",
    )
    service = FloodOpsService(local, Store(local.db_path))
    evidence = [FloodEvent(event_id="hl-fail", source="nws", observed_at=datetime.now(timezone.utc), kind="weather_alert", title="Warning", provenance_url="https://example.test/hl-fail")]
    model_called = False

    async def scan(**kwargs):
        if kwargs["requester_id"] == "floodops-model_request":
            raise HiddenLayerUnavailable("temporary security service failure")
        return {"status": "scanned", "fired_signals": []}

    async def assessor(events, scenario_id, memories):
        nonlocal model_called
        model_called = True
        raise AssertionError("model must not be called")

    monkeypatch.setattr("app.service.evaluate_interaction_v2", scan)
    _, assessed, error = await service.assess_events(evidence, "hiddenlayer-fail", model_assessor=assessor)
    assert model_called is False
    assert assessed is not None and assessed.policy_status == "blocked"
    assert assessed.model_name == "hiddenlayer-quarantine"
    assert "before inference" in error
