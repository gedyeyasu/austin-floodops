from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Awaitable, Callable
import logging

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
from app.storage.audit import AuditChain
from app.streaming.ingest import collect_live, collect_live_with_status, replay
from app.streaming.kafka import EventBus, KafkaConfig, KafkaUnavailable

logger = logging.getLogger("austin_floodops.service")

DecisionAssessor = Callable[[list[FloodEvent], str, list[dict[str, Any]]], Awaitable[IncidentDecision]]


@dataclass
class FloodOpsService:
    settings: Settings
    store: Store
    audit_chain: AuditChain | None = field(default=None)

    def __post_init__(self) -> None:
        # Initialize audit_chain if enabled and not provided
        if self.audit_chain is None and self.settings.enable_audit_chain:
            try:
                self.audit_chain = AuditChain(self.settings.db_path)
                logger.info("AuditChain initialized at %s", self.settings.db_path)
            except Exception as exc:
                logger.warning("Failed to init AuditChain: %s", exc)
                self.audit_chain = None

    @classmethod
    def create(cls, settings: Settings) -> "FloodOpsService":
        store = Store(settings.db_path)
        audit = None
        if settings.enable_audit_chain:
            try:
                audit = AuditChain(settings.db_path)
            except Exception:
                audit = None
        return cls(settings=settings, store=store, audit_chain=audit)

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

    def _audit(self, *, incident_id: str | None, event_type: str, actor_id: str = "system", actor_role: str = "system", payload: dict[str, Any] | None = None) -> None:
        if not self.audit_chain or not self.settings.enable_audit_chain:
            return
        try:
            self.audit_chain.append(
                incident_id=incident_id,
                event_type=event_type,
                actor_id=actor_id,
                actor_role=actor_role,
                payload=payload or {},
            )
        except Exception as exc:
            logger.warning("Audit append failed %s: %s", event_type, exc)

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
        actor_id: str = "system",
        actor_role: str = "system",
    ) -> tuple[list[FloodEvent], IncidentDecision | None, str | None]:
        if not events:
            return [], None, "No events received from configured sources."
        new_events = self.store.filter_new_events(events)
        if new_events:
            self.store.save_events(new_events)
            await self._remote_write(lambda remote: remote.save_events(new_events))
            # audit evidence_ingested
            self._audit(
                incident_id=None,
                event_type="evidence_ingested",
                actor_id=actor_id,
                actor_role=actor_role,
                payload={"new_events": len(new_events), "total_events": len(events), "scenario_id": scenario_id, "event_ids": [e.event_id for e in new_events[:10]]},
            )
        kafka_result = await self.publish_events(new_events) if publish else {"status": "skipped", "published": 0}
        memories = rank_memories(self.store, events, 3) if memory_enabled else []
        memory_context = retrieval_context(self.store, events, 3) if memory_enabled else "Memory disabled for run-1 baseline."
        try:
            if model_assessor:
                decision = await model_assessor(events, scenario_id, memories)
            else:
                try:
                    decision = await assess_incident(
                        api_key=self.settings.nvidia_key,
                        base_url=self.settings.nvidia_base_url,
                        model=self.settings.nemotron_model,
                        events=events,
                        scenario_id=scenario_id,
                        memory_context=memory_context,
                    )
                except IntegrationUnavailable as nemotron_exc:
                    # vLLM fallback
                    if self.settings.has_vllm:
                        logger.info("Nemotron unavailable (%s), trying vLLM fallback at %s", nemotron_exc, self.settings.vllm_base_url)
                        try:
                            from app.model.vllm import assess_incident_vllm, VLLMUnavailable

                            decision = await assess_incident_vllm(
                                base_url=self.settings.vllm_base_url,
                                model=self.settings.vllm_model,
                                api_key=self.settings.vllm_api_key,
                                events=events,
                                scenario_id=scenario_id,
                                memory_context=memory_context,
                            )
                        except Exception as vllm_exc:  # noqa: BLE001
                            self._audit(
                                incident_id=None,
                                event_type="assessment_failed",
                                actor_id=actor_id,
                                actor_role=actor_role,
                                payload={"scenario_id": scenario_id, "nemotron_error": str(nemotron_exc), "vllm_error": str(vllm_exc)},
                            )
                            return events, None, f"Nemotron: {nemotron_exc}; vLLM fallback failed: {vllm_exc}"
                    else:
                        self._audit(
                            incident_id=None,
                            event_type="assessment_failed",
                            actor_id=actor_id,
                            actor_role=actor_role,
                            payload={"scenario_id": scenario_id, "error": str(nemotron_exc)},
                        )
                        return events, None, str(nemotron_exc)
        except IntegrationUnavailable as exc:
            self._audit(
                incident_id=None,
                event_type="assessment_failed",
                actor_id=actor_id,
                actor_role=actor_role,
                payload={"scenario_id": scenario_id, "error": str(exc)},
            )
            return events, None, str(exc)

        # capture incident_id for audit
        incident_id = decision.incident_id

        security: dict[str, Any] = {
            "hiddenlayer": {"status": "not_configured"},
            "openshell": {
                "status": "configured" if self.settings.has_openshell else "not_configured",
                "decision": "approval_boundary_enforced",
            },
            "kafka": kafka_result,
            "vllm": {"status": "used" if decision.model_name == self.settings.vllm_model and self.settings.has_vllm else "not_used"},
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
                self._audit(
                    incident_id=incident_id,
                    event_type="security_blocked",
                    actor_id=actor_id,
                    actor_role=actor_role,
                    payload={"reason": str(exc), "security": security},
                )
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

        # audit decision_created
        self._audit(
            incident_id=incident_id,
            event_type="decision_created",
            actor_id=actor_id,
            actor_role=actor_role,
            payload={
                "scenario_id": scenario_id,
                "risk_level": decision.risk_level,
                "confidence": decision.confidence,
                "model": decision.model_name,
                "policy_status": decision.policy_status,
                "evidence_count": len(events),
            },
        )

        return events, decision, None

    async def assess(self, mode: str, scenario_id: str) -> tuple[list[FloodEvent], IncidentDecision | None, str | None]:
        events = await self.gather(mode, scenario_id)
        return await self.assess_events(events, scenario_id)

    def approve(self, decision: IncidentDecision, *, actor_id: str = "system", actor_role: str = "system") -> PolicyResult:
        result = evaluate(decision, operator_approved=True)
        decision.policy_status = result.status  # type: ignore[misc]
        decision.raw_model_response.setdefault("security", {})["policy"] = {"status": result.status, "reason": result.reason}
        self.store.save_decision(decision)
        self._audit(
            incident_id=decision.incident_id,
            event_type="approved",
            actor_id=actor_id,
            actor_role=actor_role,
            payload={"reason": result.reason, "status": result.status},
        )
        return result

    def reject(self, decision: IncidentDecision, *, actor_id: str = "system", actor_role: str = "system") -> PolicyResult:
        result = PolicyResult("blocked", "Operator rejected the proposed action; no dispatch occurred.")
        decision.policy_status = "blocked"
        decision.raw_model_response.setdefault("security", {})["policy"] = {"status": result.status, "reason": result.reason}
        self.store.save_decision(decision)
        self._audit(
            incident_id=decision.incident_id,
            event_type="rejected",
            actor_id=actor_id,
            actor_role=actor_role,
            payload={"reason": result.reason},
        )
        return result

    async def record_feedback(self, decision: IncidentDecision, feedback: OperatorFeedback, *, actor_id: str = "system", actor_role: str = "system") -> dict[str, Any]:
        feedback_id = self.store.add_feedback(decision.incident_id, feedback)
        self._audit(
            incident_id=decision.incident_id,
            event_type="feedback",
            actor_id=actor_id,
            actor_role=actor_role,
            payload={"feedback_id": feedback_id, "correction": feedback.correction, "outcome": feedback.outcome},
        )
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
            self._audit(
                incident_id=decision.incident_id,
                event_type="memory_created",
                actor_id=actor_id,
                actor_role=actor_role,
                payload={"memory_id": memory_id, "rule": memory},
            )
            return {"feedback_id": feedback_id, "memory": memory, "reflection_status": "created"}
        except ReflectionUnavailable as exc:
            return {"feedback_id": feedback_id, "memory": None, "reflection_status": "degraded", "detail": str(exc)}

    def simulate(self, events: list[FloodEvent], *, mode: str, scenario_id: str, horizon_minutes: int):
        return simulate_impact(events, mode=mode, scenario_id=scenario_id, horizon_minutes=horizon_minutes)

    def record_delivery(self, incident_id: str, channel: str, response_status: int, *, actor_id: str = "system", actor_role: str = "system") -> None:
        self.store.record_delivery(incident_id, channel, response_status)
        self._audit(
            incident_id=incident_id,
            event_type="delivery",
            actor_id=actor_id,
            actor_role=actor_role,
            payload={"channel": channel, "response_status": response_status},
        )

    def record_prediction(self, incident_id: str, prediction_result: Any, *, actor_id: str = "system", actor_role: str = "system") -> None:
        self._audit(
            incident_id=incident_id,
            event_type="prediction_generated",
            actor_id=actor_id,
            actor_role=actor_role,
            payload={"incident_id": incident_id, "site_id": getattr(prediction_result, "site_id", "unknown"), "method": getattr(prediction_result, "method", "unknown")},
        )
