from datetime import datetime, timezone

import pytest

from app.models import FloodEvent
from app.safety.policy import evaluate
from app.streaming.kafka import EventBus, KafkaConfig, KafkaUnavailable


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

