from dataclasses import replace
from datetime import datetime, timezone

import pytest

from app.config import settings
from app.models import FloodEvent, IncidentDecision, ProposedAction
from app.service import FloodOpsService
from app.storage.sqlite import Store
from app.streaming.heartbeat import HeartbeatEngine
from app.streaming.kafka import KafkaUnavailable


def event() -> FloodEvent:
    return FloodEvent(
        event_id="stable-heartbeat-event",
        source="nws",
        observed_at=datetime.now(timezone.utc),
        kind="weather_alert",
        title="Flash Flood Warning",
        severity="severe",
        provenance_url="https://example.test/alert",
    )


def decision() -> IncidentDecision:
    return IncidentDecision(
        mode="live", scenario_id="heartbeat", summary="Warning detected.", risk_level="high", confidence=0.9,
        evidence_event_ids=["stable-heartbeat-event"], citations=["stable-heartbeat-event"],
        proposed_action=ProposedAction(action_type="request_approval", target="Test crossing", rationale="Official warning."),
        policy_status="approval_required", model_name="test",
    )


@pytest.mark.asyncio
async def test_heartbeat_deduplicates_and_assesses_only_new_events(tmp_path, monkeypatch):
    local = replace(settings, db_path=tmp_path / "heartbeat.sqlite3", kafka_bootstrap_servers="", supabase_url="", supabase_service_role_key="")
    service = FloodOpsService(local, Store(local.db_path))
    calls = []

    async def gather_live_with_status():
        return [event(), event()], {
            "nws": {"status": "ok", "events": 2},
            "usgs": {"status": "ok", "events": 0},
        }

    async def assess_events(events, scenario_id):
        calls.append([item.event_id for item in events])
        service.store.save_events(events)
        return events, decision(), None

    monkeypatch.setattr(service, "gather_live_with_status", gather_live_with_status)
    monkeypatch.setattr(service, "assess_events", assess_events)
    engine = HeartbeatEngine(service, 30)
    first = await engine.run_cycle()
    second = await engine.run_cycle()
    assert first["new_events"] == 1
    assert second["new_events"] == 0
    assert calls == [["stable-heartbeat-event"]]
    assert service.store.heartbeat_state()["cycles"] == 2


@pytest.mark.asyncio
async def test_heartbeat_survives_source_failure(tmp_path, monkeypatch):
    local = replace(settings, db_path=tmp_path / "heartbeat.sqlite3", kafka_bootstrap_servers="", supabase_url="", supabase_service_role_key="")
    service = FloodOpsService(local, Store(local.db_path))

    async def gather_live_with_status():
        raise TimeoutError("source timeout")

    monkeypatch.setattr(service, "gather_live_with_status", gather_live_with_status)
    state = await HeartbeatEngine(service).run_cycle()
    assert state["decision_outcome"] == "degraded"
    assert state["consecutive_failures"] == 1
    assert "TimeoutError" in state["last_error"]


@pytest.mark.asyncio
async def test_heartbeat_exposes_partial_source_failure(tmp_path, monkeypatch):
    local = replace(settings, db_path=tmp_path / "heartbeat.sqlite3", kafka_bootstrap_servers="", supabase_url="", supabase_service_role_key="")
    service = FloodOpsService(local, Store(local.db_path))

    async def gather_live_with_status():
        return [], {
            "nws": {"status": "degraded", "error": "ReadTimeout"},
            "usgs": {"status": "ok", "events": 0},
        }

    monkeypatch.setattr(service, "gather_live_with_status", gather_live_with_status)
    state = await HeartbeatEngine(service).run_cycle()
    assert state["sources"]["nws"]["status"] == "degraded"
    assert state["sources"]["usgs"]["status"] == "ok"
    assert state["last_error"] == "Core source degraded: nws"
    assert state["consecutive_failures"] == 1


@pytest.mark.asyncio
async def test_optional_source_failure_is_warning_not_heartbeat_failure(tmp_path, monkeypatch):
    local = replace(settings, db_path=tmp_path / "heartbeat.sqlite3", kafka_bootstrap_servers="", supabase_url="", supabase_service_role_key="")
    service = FloodOpsService(local, Store(local.db_path))

    async def gather_live_with_status():
        return [], {
            "nws": {"status": "ok", "events": 0},
            "usgs": {"status": "ok", "events": 0},
            "austin_roads": {"status": "degraded", "error": "HTTPStatusError"},
        }

    monkeypatch.setattr(service, "gather_live_with_status", gather_live_with_status)
    state = await HeartbeatEngine(service).run_cycle()
    assert state["last_error"] is None
    assert state["last_success_at"]
    assert state["consecutive_failures"] == 0
    assert state["source_warnings"] == ["austin_roads"]


@pytest.mark.asyncio
async def test_quiet_heartbeat_preserves_last_verified_stream_evidence(tmp_path, monkeypatch):
    local = replace(settings, db_path=tmp_path / "heartbeat.sqlite3", kafka_bootstrap_servers="broker:9092", supabase_url="", supabase_service_role_key="")
    service = FloodOpsService(local, Store(local.db_path))
    service.store.save_heartbeat_state(
        {"stream": {"status": "verified", "published": 2, "consumed": 2, "fallback": 0}, "cycles": 1}
    )

    async def gather_live_with_status():
        return [], {"nws": {"status": "ok", "events": 0}, "usgs": {"status": "ok", "events": 0}}

    monkeypatch.setattr(service, "gather_live_with_status", gather_live_with_status)
    state = await HeartbeatEngine(service).run_cycle()
    assert state["stream"]["status"] == "verified"
    assert state["stream"]["current_cycle"] == "idle"
    assert state["stream"]["published"] == 2


@pytest.mark.asyncio
async def test_kafka_failure_degrades_without_losing_assessment(tmp_path, monkeypatch):
    local = replace(
        settings,
        db_path=tmp_path / "heartbeat.sqlite3",
        kafka_bootstrap_servers="broker:9092",
        supabase_url="",
        supabase_service_role_key="",
        hiddenlayer_interactions_url="",
        hiddenlayer_api_key="",
        hiddenlayer_client_id="",
        hiddenlayer_client_secret="",
    )
    service = FloodOpsService(local, Store(local.db_path))

    class BrokenBus:
        def publish(self, events):
            raise KafkaUnavailable("broker unavailable")

    async def assessor(events, scenario_id, memories):
        return decision()

    monkeypatch.setattr(service, "event_bus", lambda: BrokenBus())
    _, assessed, error = await service.assess_events([event()], "heartbeat", model_assessor=assessor)
    assert error is None
    assert assessed is not None
    assert assessed.raw_model_response["security"]["kafka"]["status"] == "degraded"
    assert service.store.list_events()[0].event_id == "stable-heartbeat-event"


@pytest.mark.asyncio
async def test_kafka_round_trip_is_the_assessment_path(tmp_path, monkeypatch):
    local = replace(
        settings,
        db_path=tmp_path / "heartbeat.sqlite3",
        kafka_bootstrap_servers="broker:9092",
        supabase_url="",
        supabase_service_role_key="",
        hiddenlayer_interactions_url="",
        hiddenlayer_api_key="",
        hiddenlayer_client_id="",
        hiddenlayer_client_secret="",
    )
    service = FloodOpsService(local, Store(local.db_path))
    published: list[FloodEvent] = []
    assessed_ids: list[str] = []

    class LoopbackBus:
        def publish(self, events):
            published.extend(events)
            return len(events)

        def consume(self, **kwargs):
            yield from published

    async def assessor(events, scenario_id, memories):
        assessed_ids.extend(item.event_id for item in events)
        return decision()

    monkeypatch.setattr(service, "event_bus", lambda: LoopbackBus())
    _, assessed, error = await service.assess_events([event()], "heartbeat", model_assessor=assessor)
    assert error is None
    assert assessed is not None
    assert assessed_ids == ["stable-heartbeat-event"]
    assert assessed.raw_model_response["security"]["kafka"] == {
        "status": "verified",
        "published": 1,
        "consumed": 1,
        "fallback": 0,
        "event_ids": ["stable-heartbeat-event"],
    }
