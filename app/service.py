from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.config import Settings
from app.learning.memory import retrieval_context
from app.model.nemotron import IntegrationUnavailable, assess_incident
from app.models import FloodEvent, IncidentDecision, OperatorFeedback
from app.safety.policy import PolicyResult, evaluate
from app.storage.sqlite import Store
from app.streaming.ingest import collect_live, replay


@dataclass
class FloodOpsService:
    settings: Settings
    store: Store

    @classmethod
    def create(cls, settings: Settings) -> "FloodOpsService":
        return cls(settings=settings, store=Store(settings.db_path))

    async def gather(self, mode: str, scenario_id: str) -> list[FloodEvent]:
        if mode == "replay":
            path = Path(__file__).resolve().parents[1] / "data" / "replay" / f"{scenario_id}.jsonl"
            return [event async for event in replay(path)]
        events = await collect_live(
            user_agent=self.settings.nws_user_agent,
            site_id=self.settings.usgs_site_id,
            parameter_codes=self.settings.usgs_parameter_codes,
        )
        return events

    async def assess(self, mode: str, scenario_id: str) -> tuple[list[FloodEvent], IncidentDecision | None, str | None]:
        events = await self.gather(mode, scenario_id)
        if events:
            self.store.save_events(events)
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
        decision.raw_model_response.setdefault("memory_context", retrieval_context(self.store))
        decision.policy_status = evaluate(decision).status  # type: ignore[misc]
        self.store.save_decision(decision)
        return events, decision, None

    def approve(self, decision: IncidentDecision) -> PolicyResult:
        result = evaluate(decision, operator_approved=True)
        decision.policy_status = result.status  # type: ignore[misc]
        self.store.save_decision(decision)
        return result

    def feedback(self, incident_id: str, feedback: OperatorFeedback) -> int:
        return self.store.add_feedback(incident_id, feedback)

