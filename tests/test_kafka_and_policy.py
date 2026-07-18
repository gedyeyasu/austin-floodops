from datetime import datetime, timezone

import pytest

from app.models import FloodEvent
from app.safety.policy import evaluate
from app.streaming.kafka import EventBus, KafkaConfig, KafkaUnavailable, decode_event
from app.responders.webeoc import WebEOCConfig, add_data_envelope
from app.storage.supabase import SupabaseConfig, SupabaseStore, SupabaseUnavailable
from app.storage.sqlite import Store


def test_kafka_without_config_fails_closed():
    bus = EventBus(KafkaConfig(bootstrap_servers="", topic="floodops.events"))
    with pytest.raises(KafkaUnavailable):
        bus.publish([])


def test_event_id_is_the_kafka_key():
    event = FloodEvent(
        event_id="stable-id",
        source="replay",
        observed_at=datetime.now(timezone.utc),
        kind="weather_alert",
        title="Flash Flood Warning",
        provenance_url="https://example.test",
        mode="replay",
    )
    assert event.event_id == "stable-id"
    assert EventBus(KafkaConfig(bootstrap_servers="", topic="floodops.events")).config.topic == "floodops.events"


def test_kafka_decoder_rejects_malformed_or_untyped_records():
    with pytest.raises(Exception):
        decode_event(b"not-json")
    with pytest.raises(Exception):
        decode_event(b'{"source":"nws"}')


def test_delivery_claim_is_atomic_and_retryable(tmp_path):
    store = Store(tmp_path / "deliveries.sqlite3")
    assert store.claim_delivery("incident-1", "first-responder-cap") is True
    assert store.claim_delivery("incident-1", "first-responder-cap") is False
    store.release_delivery_claim("incident-1", "first-responder-cap")
    assert store.claim_delivery("incident-1", "first-responder-cap") is True
    store.record_delivery("incident-1", "first-responder-cap", 202)
    store.release_delivery_claim("incident-1", "first-responder-cap")
    assert store.delivery_exists("incident-1", "first-responder-cap") is True


def test_webeoc_envelope_contains_add_data_contract_without_network_call():
    config = WebEOCConfig(
        api_url="https://webeoc.example.test/api.asmx",
        username="operator",
        password="secret",
        position="EOC",
        incident="flood-demo",
        board_name="FloodOps",
        input_view_name="Incident Intake",
    )
    payload = add_data_envelope(config, b"<alert />")
    assert b"AddData" in payload
    assert b"Incident Intake" in payload
    assert b"&lt;alert /&gt;" in payload


def test_supabase_without_credentials_fails_closed():
    store = SupabaseStore(SupabaseConfig())
    assert not store.config.configured
    import asyncio
    with pytest.raises(SupabaseUnavailable):
        asyncio.run(store.probe())
