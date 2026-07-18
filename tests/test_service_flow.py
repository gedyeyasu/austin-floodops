from dataclasses import replace
from datetime import datetime, timezone

import pytest

from app.config import settings
from app.models import FloodEvent, IncidentDecision, OperatorFeedback, PlaybookRule, ProposedAction
from app.service import FloodOpsService
from app.storage.sqlite import Store


@pytest.mark.asyncio
async def test_gather_assess_approve_feedback_reassess_flow(tmp_path, monkeypatch):
    local = replace(settings, db_path=tmp_path / "flow.sqlite3", kafka_bootstrap_servers="", supabase_url="", supabase_service_role_key="", hiddenlayer_interactions_url="", hiddenlayer_api_key="")
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
