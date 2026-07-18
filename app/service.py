from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Awaitable, Callable

from app.config import Settings
from app.learning.memory import rank_memories, retrieval_context
from app.learning.reflection import ReflectionUnavailable, reflect_on_feedback
from app.model.nemotron import IntegrationUnavailable, assess_incident
from app.models import FloodEvent, IncidentDecision, OperatorFeedback
from app.safety.policy import PolicyResult, evaluate
from app.security.hiddenlayer import HiddenLayerConfig, HiddenLayerUnavailable, scan_interaction
from app.simulation.model import simulate_impact
from app.storage.sqlite import Store
from app.storage.supabase import SupabaseConfig, SupabaseStore, SupabaseUnavailable
from app.streaming.ingest import collect_live, collect_live_with_status, replay
from app.streaming.kafka import EventBus, KafkaConfig, KafkaUnavailable


DecisionAssessor = Callable[[list[FloodEvent], str, list[dict[str, Any]]], Awaitable[IncidentDecision]]


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
            pass

    async def publish_events(self, events: list[FloodEvent]) -> dict[str, Any]:
        if not events or not self.settings.has_kafka:
            return {"status": "not_configured" if not self.settings.has_kafka else "idle", "published": 0}
        try:
            published = await asyncio.to_thread(self.event_bus().publish, events)
            return {"status": "published", "published": published}
        except KafkaUnavailable as exc:
            return {"status": "degraded", "published": 0, "detail": str(exc)}

    async def gather(self, mode: str, scenario_id: str) -> list[FloodEvent]:
        if mode == "replay":
            path = Path(__file__).resolve().parents[1] / "data" / "replay" / f"{scenario_id}.jsonl"
            return [event async for event in replay(path)]
        return await collect_live(
            user_agent=self.settings.nws_user_agent,
            site_id=self.settings.usgs_site_id,
            parameter_codes=self.settings.usgs_parameter_codes,
        )

    async def gather_live_with_status(self) -> tuple[list[FloodEvent], dict[str, dict[str, Any]]]:
        return await collect_live_with_status(
            user_agent=self.settings.nws_user_agent,
            site_id=self.settings.usgs_site_id,
            parameter_codes=self.settings.usgs_parameter_codes,
        )

    async def assess_events(
        self,
        events: list[FloodEvent],
        scenario_id: str,
        *,
        memory_enabled: bool = True,
        model_assessor: DecisionAssessor | None = None,
        publish: bool = True,
        security_scan: bool = True,
    ) -> tuple[list[FloodEvent], IncidentDecision | None, str | None]:
        if not events:
            return [], None, "No events received from configured sources."
        new_events = self.store.filter_new_events(events)
        if new_events:
            self.store.save_events(new_events)
            await self._remote_write(lambda remote: remote.save_events(new_events))
        kafka_result = await self.publish_events(new_events) if publish else {"status": "skipped", "published": 0}
        memories = rank_memories(self.store, events, 3) if memory_enabled else []
        memory_context = retrieval_context(self.store, events, 3) if memory_enabled else "Memory disabled for run-1 baseline."
        try:
            if model_assessor:
                decision = await model_assessor(events, scenario_id, memories)
            else:
                decision = await assess_incident(
                    api_key=self.settings.nvidia_key,
                    base_url=self.settings.nvidia_base_url,
                    model=self.settings.nemotron_model,
                    events=events,
                    scenario_id=scenario_id,
                    memory_context=memory_context,
                )
        except IntegrationUnavailable as exc:
            return events, None, str(exc)
        security: dict[str, Any] = {
            "hiddenlayer": {"status": "not_configured"},
            "openshell": {
                "status": "configured" if self.settings.has_openshell else "not_configured",
                "decision": "approval_boundary_enforced",
            },
            "kafka": kafka_result,
        }
        if security_scan and self.settings.has_hiddenlayer:
            try:
                scan = await scan_interaction(
                    self.hiddenlayer(),
                    input_text="\n".join(f"{event.event_id}: {event.title}" for event in events),
                    output_text=f"{decision.summary}\n{decision.proposed_action.rationale}",
                )
                security["hiddenlayer"] = {"status": "verified", "result": scan}
            except HiddenLayerUnavailable as exc:
                security["hiddenlayer"] = {"status": "blocked", "detail": str(exc)}
                decision.policy_status = "blocked"
                decision.raw_model_response["security"] = security
                self.store.save_decision(decision)
                return events, decision, str(exc)
        policy = evaluate(decision)
        decision.policy_status = policy.status  # type: ignore[misc]
        security["policy"] = {"status": policy.status, "reason": policy.reason}
        decision.raw_model_response["learning"] = {
            "memory_context": memory_context,
            "retrieved_memories": memories,
        }
        decision.raw_model_response["security"] = security
        self.store.save_decision(decision)
        await self._remote_write(lambda remote: remote.save_decision(decision))
        return events, decision, None

    async def assess(self, mode: str, scenario_id: str) -> tuple[list[FloodEvent], IncidentDecision | None, str | None]:
        events = await self.gather(mode, scenario_id)
        return await self.assess_events(events, scenario_id)

    def approve(self, decision: IncidentDecision) -> PolicyResult:
        result = evaluate(decision, operator_approved=True)
        decision.policy_status = result.status  # type: ignore[misc]
        decision.raw_model_response.setdefault("security", {})["policy"] = {"status": result.status, "reason": result.reason}
        self.store.save_decision(decision)
        return result

    def reject(self, decision: IncidentDecision) -> PolicyResult:
        result = PolicyResult("blocked", "Operator rejected the proposed action; no dispatch occurred.")
        decision.policy_status = "blocked"
        decision.raw_model_response.setdefault("security", {})["policy"] = {"status": result.status, "reason": result.reason}
        self.store.save_decision(decision)
        return result

    async def record_feedback(self, decision: IncidentDecision, feedback: OperatorFeedback) -> dict[str, Any]:
        feedback_id = self.store.add_feedback(decision.incident_id, feedback)
        events = self.store.events_by_id(decision.evidence_event_ids)
        try:
            rule = await reflect_on_feedback(
                api_key=self.settings.nvidia_key,
                base_url=self.settings.nvidia_base_url,
                model=self.settings.nemotron_model,
                feedback=feedback,
                decision=decision,
                events=events,
            )
            memory_id = self.store.add_memory(rule, decision.incident_id)
            memory = next(item for item in self.store.list_memories() if item["id"] == memory_id)
            return {"feedback_id": feedback_id, "memory": memory, "reflection_status": "created"}
        except ReflectionUnavailable as exc:
            return {"feedback_id": feedback_id, "memory": None, "reflection_status": "degraded", "detail": str(exc)}

    def simulate(self, events: list[FloodEvent], *, mode: str, scenario_id: str, horizon_minutes: int):
        return simulate_impact(events, mode=mode, scenario_id=scenario_id, horizon_minutes=horizon_minutes)
