from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.config import Settings
from app.learning.memory import retrieval_context
from app.model.nemotron import IntegrationUnavailable, assess_incident
from app.models import FloodEvent, IncidentDecision, OperatorFeedback
from app.security.hiddenlayer import HiddenLayerConfig, HiddenLayerUnavailable, scan_interaction
from app.safety.policy import PolicyResult, evaluate
from app.simulation.model import simulate_impact
from app.storage.sqlite import Store
from app.storage.supabase import SupabaseConfig, SupabaseStore, SupabaseUnavailable
from app.streaming.ingest import collect_live, replay
from app.streaming.kafka import EventBus, KafkaConfig, KafkaUnavailable


@dataclass
class FloodOpsService:
    settings: Settings
    store: Store

    @classmethod
    def create(cls, settings: Settings) -> "FloodOpsService":
        return cls(settings=settings, store=Store(settings.db_path))

    def event_bus(self) -> EventBus:
        return EventBus(
            KafkaConfig(
                bootstrap_servers=self.settings.kafka_bootstrap_servers,
                topic=self.settings.kafka_topic,
                security_protocol=self.settings.kafka_security_protocol,
                sasl_mechanism=self.settings.kafka_sasl_mechanism,
                username=self.settings.kafka_username,
                password=self.settings.kafka_password,
            )
        )

    def hiddenlayer(self) -> HiddenLayerConfig:
        return HiddenLayerConfig(
            interactions_url=self.settings.hiddenlayer_interactions_url,
            api_key=self.settings.hiddenlayer_api_key,
            project=self.settings.hiddenlayer_project,
        )

    def supabase(self) -> SupabaseStore:
        return SupabaseStore(SupabaseConfig(url=self.settings.supabase_url, service_role_key=self.settings.supabase_service_role_key))

    async def _remote_write(self, operation) -> None:
        if not self.settings.has_supabase:
            return
        try:
            await operation(self.supabase())
        except SupabaseUnavailable:
            # Local SQLite remains authoritative during a remote outage.
            pass

    async def gather(self, mode: str, scenario_id: str) -> list[FloodEvent]:
        if mode == "replay":
            path = Path(__file__).resolve().parents[1] / "data" / "replay" / f"{scenario_id}.jsonl"
            return [event async for event in replay(path)]
        events = await collect_live(
            user_agent=self.settings.nws_user_agent,
            site_id=self.settings.usgs_site_id,
            parameter_codes=self.settings.usgs_parameter_codes,
        )
        if events and self.settings.has_kafka:
            try:
                self.event_bus().publish(events)
            except KafkaUnavailable:
                # The local evidence ledger remains authoritative when the optional broker is down.
                pass
        return events

    async def assess(self, mode: str, scenario_id: str) -> tuple[list[FloodEvent], IncidentDecision | None, str | None]:
        events = await self.gather(mode, scenario_id)
        if events:
            self.store.save_events(events)
            await self._remote_write(lambda remote: remote.save_events(events))
        if not events:
            return [], None, "No events received from configured sources."
        try:
            decision = await assess_incident(
                api_key=self.settings.nvidia_key,
                base_url=self.settings.nvidia_base_url,
                model=self.settings.nemotron_model,
                events=events,
                scenario_id=scenario_id,
            )
        except IntegrationUnavailable as exc:
            return events, None, str(exc)
        if self.settings.has_hiddenlayer:
            try:
                scan = await scan_interaction(
                    self.hiddenlayer(),
                    input_text="\n".join(f"{event.event_id}: {event.title}" for event in events),
                    output_text=f"{decision.summary}\n{decision.proposed_action.rationale}",
                )
                decision.raw_model_response["hiddenlayer"] = scan
            except HiddenLayerUnavailable as exc:
                return events, None, str(exc)
        decision.raw_model_response.setdefault("memory_context", retrieval_context(self.store))
        decision.policy_status = evaluate(decision).status  # type: ignore[misc]
        self.store.save_decision(decision)
        await self._remote_write(lambda remote: remote.save_decision(decision))
        return events, decision, None

    def approve(self, decision: IncidentDecision) -> PolicyResult:
        result = evaluate(decision, operator_approved=True)
        decision.policy_status = result.status  # type: ignore[misc]
        self.store.save_decision(decision)
        return result

    def feedback(self, incident_id: str, feedback: OperatorFeedback) -> int:
        feedback_id = self.store.add_feedback(incident_id, feedback)
        # Feedback is recorded locally synchronously; the remote mirror is
        # scheduled by the endpoint because this method is intentionally sync.
        return feedback_id

    def simulate(self, events: list[FloodEvent], *, mode: str, scenario_id: str, horizon_minutes: int):
        return simulate_impact(events, mode=mode, scenario_id=scenario_id, horizon_minutes=horizon_minutes)
