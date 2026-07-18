from datetime import datetime, timezone

import httpx
import pytest

from app.learning.memory import rank_memories
from app.learning.reflection import reflect_on_feedback
from app.models import FloodEvent, IncidentDecision, OperatorFeedback, PlaybookRule, ProposedAction
from app.storage.sqlite import Store


def event(title="Gage height rapid rise", location="Onion Creek"):
    return FloodEvent(event_id="e1", source="usgs", observed_at=datetime.now(timezone.utc), kind="water_observation", title=title, location=location, value=12.3, unit="ft", provenance_url="https://example.test")


def decision():
    return IncidentDecision(mode="live", scenario_id="test", summary="Risk is high.", risk_level="high", confidence=0.8, evidence_event_ids=["e1"], citations=["e1"], proposed_action=ProposedAction(action_type="request_approval", target="Onion Creek", rationale="Rapid rise."), policy_status="approval_required", model_name="test")


@pytest.mark.asyncio
async def test_reflection_extracts_structured_rule(monkeypatch):
    response = httpx.Response(200, request=httpx.Request("POST", "https://example.test"), json={"choices":[{"message":{"content":"{\"trigger\":\"gage rises above 12 ft\",\"action\":\"request approval to close crossing\",\"rationale\":\"rapid rise increases exposure\",\"confidence\":0.91,\"context_tags\":[\"Gage\",\"Flood\"]}"}}]})

    class Client:
        async def __aenter__(self): return self
        async def __aexit__(self, *args): return None
        async def post(self, *args, **kwargs): return response

    monkeypatch.setattr("app.learning.reflection.httpx.AsyncClient", lambda **kwargs: Client())
    rule = await reflect_on_feedback(api_key="key", base_url="https://example.test", model="test", feedback=OperatorFeedback(correction="Require closure above 12 ft", outcome="helpful"), decision=decision(), events=[event()])
    assert rule.trigger == "gage rises above 12 ft"
    assert rule.context_tags == ["gage", "flood"]
    assert rule.confidence == 0.91


def test_memory_ranking_and_retirement(tmp_path):
    store = Store(tmp_path / "memory.sqlite3")
    relevant = store.add_memory(PlaybookRule(trigger="rapid gage rise at Onion Creek", action="request crossing closure approval", rationale="rising water", confidence=0.9, context_tags=["gage", "onion", "flood"]), "incident-1")
    store.add_memory(PlaybookRule(trigger="wildfire smoke", action="notify air quality desk", rationale="unrelated", confidence=0.99, context_tags=["fire", "smoke"]), "incident-2")
    assert rank_memories(store, [event()], 1)[0]["id"] == relevant
    assert store.retire_memory(relevant)
    assert all(item["id"] != relevant for item in rank_memories(store, [event()], 3))
    assert rank_memories(store, [event()], 3) == []
    assert not next(item for item in store.list_memories() if item["id"] == relevant)["active"]
