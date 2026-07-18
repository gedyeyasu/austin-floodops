from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Iterator

from app.models import FloodEvent

logger = logging.getLogger("austin_floodops.kafka")


class KafkaUnavailable(RuntimeError):
    """Raised when the configured Kafka broker cannot be used."""


def decode_event(value: bytes) -> FloodEvent:
    """Decode and validate one broker record at the stream trust boundary."""
    payload = json.loads(value.decode("utf-8"))
    return FloodEvent.model_validate(payload)


@dataclass(frozen=True)
class KafkaConfig:
    bootstrap_servers: str
    topic: str
    security_protocol: str = "SASL_SSL"
    sasl_mechanism: str = "PLAIN"
    username: str = ""
    password: str = ""
    group_id: str = "austin-floodops-normalizer"


class EventBus:
    def __init__(self, config: KafkaConfig):
        self.config = config
        self._producer = None

    def _producer_client(self):
        if self._producer is not None:
            return self._producer
        if not self.config.bootstrap_servers:
            raise KafkaUnavailable("Kafka bootstrap servers are not configured")
        try:
            from kafka import KafkaProducer
        except ImportError as exc:
            raise KafkaUnavailable("Install the streaming extra to enable Kafka") from exc
        try:
            self._producer = KafkaProducer(
                bootstrap_servers=[item.strip() for item in self.config.bootstrap_servers.split(",") if item.strip()],
                security_protocol=self.config.security_protocol,
                sasl_mechanism=self.config.sasl_mechanism,
                sasl_plain_username=self.config.username or None,
                sasl_plain_password=self.config.password or None,
                value_serializer=lambda value: json.dumps(value).encode("utf-8"),
                key_serializer=lambda value: value.encode("utf-8"),
                request_timeout_ms=5000,
            )
        except Exception as exc:
            raise KafkaUnavailable(f"Kafka producer could not connect: {exc}") from exc
        return self._producer

    def publish(self, events: list[FloodEvent]) -> int:
        producer = self._producer_client()
        futures = [
            producer.send(self.config.topic, key=event.event_id, value=event.model_dump(mode="json"))
            for event in events
        ]
        try:
            for future in futures:
                future.get(timeout=10)
            producer.flush(timeout=10)
        except Exception as exc:
            raise KafkaUnavailable(f"Kafka publish failed: {exc}") from exc
        return len(futures)

    def consume(self, *, timeout_ms: int = 5000, max_records: int = 20) -> Iterator[FloodEvent]:
        if not self.config.bootstrap_servers:
            raise KafkaUnavailable("Kafka bootstrap servers are not configured")
        try:
            from kafka import KafkaConsumer
        except ImportError as exc:
            raise KafkaUnavailable("Install the streaming extra to enable Kafka") from exc
        try:
            consumer = KafkaConsumer(
                self.config.topic,
                bootstrap_servers=[item.strip() for item in self.config.bootstrap_servers.split(",") if item.strip()],
                security_protocol=self.config.security_protocol,
                sasl_mechanism=self.config.sasl_mechanism,
                sasl_plain_username=self.config.username or None,
                sasl_plain_password=self.config.password or None,
                # Decode in the loop so malformed records can be committed and
                # skipped instead of permanently poisoning this consumer group.
                value_deserializer=None,
                consumer_timeout_ms=timeout_ms,
                auto_offset_reset="earliest",
                enable_auto_commit=False,
                group_id=self.config.group_id,
            )
        except Exception as exc:
            raise KafkaUnavailable(f"Kafka consumer could not connect: {exc}") from exc
        try:
            count = 0
            for message in consumer:
                try:
                    event = decode_event(message.value)
                except Exception as exc:
                    logger.warning("Skipping malformed Kafka record after validation failure: %s", type(exc).__name__)
                    consumer.commit()
                    continue
                yield event
                consumer.commit()
                count += 1
                if count >= max_records:
                    break
        finally:
            consumer.close()
