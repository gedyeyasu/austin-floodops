from __future__ import annotations

import re
from dataclasses import dataclass, replace
from pathlib import Path
from statistics import mean
from tempfile import TemporaryDirectory
from time import perf_counter
from typing import Any

from app.models import FloodEvent, IncidentDecision, PlaybookRule, ProposedAction
from app.service import FloodOpsService
from app.storage.sqlite import Store


@dataclass(frozen=True)
class ScenarioSpec:
    scenario_id: str
    expected_risk: str
    trigger: str
    action: str
    rationale: str
    tags: list[str]


SCENARIOS = [
    ScenarioSpec(
        "flash-flood-warning-only", "high",
        "Multiple severe flash flood warnings affect Austin-area low-water crossings",
        "Set risk level to high and request approval to stage crossing closures",
        "Overlapping official warnings justify precautionary staging while keeping dispatch human-controlled.",
        ["flash", "flood", "warning", "crossing", "austin"],
    ),
    ScenarioSpec(
        "gage-rise-with-warning", "catastrophic",
        "A severe flood warning coincides with a rapid gage rise above 12 feet",
        "Set risk level to catastrophic and request approval to close exposed crossings",
        "The combined warning and observed rapid rise is stronger evidence than either source alone.",
        ["gage", "rise", "warning", "usgs", "flood"],
    ),
    ScenarioSpec(
        "all-clear-scenario", "low",
        "Warnings are cancelled and gage observations show sustained falling water",
        "Set risk level to low and keep crossings under observation",
        "Improving official conditions should reduce interventions without auto-reopening infrastructure.",
        ["cancelled", "falling", "improving", "gage", "clear"],
    ),
]


class EvaluationRunner:
    def __init__(self, service: FloodOpsService):
        self.service = service

    async def _assessor(
        self, events: list[FloodEvent], scenario_id: str, memories: list[dict[str, Any]]
    ) -> IncidentDecision:
        risk = "moderate"
        if memories:
            match = re.search(r"risk level to (low|moderate|high|catastrophic)", str(memories[0].get("action", "")).lower())
            if match:
                risk = match.group(1)
        else:
            titles = " ".join(event.title.lower() for event in events)
            if "flood warning" in titles or "flash flood warning" in titles:
                risk = "high"
        target = next((event.location for event in events if event.location), "Austin-area crossings")
        return IncidentDecision(
            mode="replay",
            scenario_id=scenario_id,
            summary=f"Replay evaluation classified {scenario_id} as {risk} risk.",
            risk_level=risk,  # type: ignore[arg-type]
            confidence=0.88 if memories else 0.68,
            evidence_event_ids=[event.event_id for event in events],
            citations=[event.event_id for event in events[:3]],
            proposed_action=ProposedAction(
                action_type="request_approval",
                target=target,
                rationale="Evaluation uses official replay evidence and any context-matched operator rule.",
            ),
            policy_status="approval_required",
            model_name="evaluation-threshold-v1",
        )

    async def _run_one(self, spec: ScenarioSpec, *, memory_enabled: bool) -> dict[str, Any]:
        events = await self.service.gather("replay", spec.scenario_id)
        started = perf_counter()
        _, decision, error = await self.service.assess_events(
            events,
            spec.scenario_id,
            memory_enabled=memory_enabled,
            model_assessor=self._assessor,
            publish=False,
            security_scan=False,
        )
        latency_ms = (perf_counter() - started) * 1000
        risk = decision.risk_level if decision else "unknown"
        accurate = risk == spec.expected_risk
        return {
            "risk_level": risk,
            "expected_risk": spec.expected_risk,
            "accurate": accurate,
            "latency_ms": round(latency_ms, 2),
            "interventions": 0 if accurate else 1,
            "incident_id": decision.incident_id if decision else None,
            "error": error,
            "retrieved_memories": decision.raw_model_response.get("learning", {}).get("retrieved_memories", []) if decision else [],
        }

    async def _run_isolated(self) -> dict[str, Any]:
        run_1 = {spec.scenario_id: await self._run_one(spec, memory_enabled=False) for spec in SCENARIOS}
        memories: dict[str, dict[str, Any]] = {}
        for spec in SCENARIOS:
            source = f"evaluation:{spec.scenario_id}"
            self.service.store.retire_memories_by_source(source)
            memory_id = self.service.store.add_memory(
                PlaybookRule(
                    trigger=spec.trigger,
                    action=spec.action,
                    rationale=spec.rationale,
                    confidence=0.95,
                    context_tags=spec.tags,
                ),
                source,
            )
            memories[spec.scenario_id] = next(item for item in self.service.store.list_memories() if item["id"] == memory_id)
        run_2 = {spec.scenario_id: await self._run_one(spec, memory_enabled=True) for spec in SCENARIOS}
        scenarios = []
        for spec in SCENARIOS:
            first, second = run_1[spec.scenario_id], run_2[spec.scenario_id]
            scenarios.append(
                {
                    "scenario_id": spec.scenario_id,
                    "expected_risk": spec.expected_risk,
                    "run_1": first,
                    "run_2": second,
                    "memory": memories[spec.scenario_id],
                    "outcome_changed": first["risk_level"] != second["risk_level"],
                }
            )
        def metrics(name: str) -> dict[str, Any]:
            values = [item[name] for item in scenarios]
            return {
                "accuracy_percent": round(100 * mean(1 if value["accurate"] else 0 for value in values), 1),
                "latency_ms": round(mean(value["latency_ms"] for value in values), 2),
                "interventions": sum(value["interventions"] for value in values),
            }
        first_metrics, second_metrics = metrics("run_1"), metrics("run_2")
        return {
            "status": "completed",
            "scenario_count": len(scenarios),
            "scenarios": scenarios,
            "comparison": {
                "run_1": first_metrics,
                "run_2": second_metrics,
                "accuracy_delta": round(second_metrics["accuracy_percent"] - first_metrics["accuracy_percent"], 1),
                "latency_delta_ms": round(second_metrics["latency_ms"] - first_metrics["latency_ms"], 2),
                "intervention_delta": second_metrics["interventions"] - first_metrics["interventions"],
            },
        }

    async def run(self) -> dict[str, Any]:
        with TemporaryDirectory(prefix="floodops-evaluation-") as directory:
            local = replace(
                self.service.settings,
                db_path=Path(directory) / "evaluation.sqlite3",
                kafka_bootstrap_servers="",
                supabase_url="",
                supabase_service_role_key="",
                hiddenlayer_interactions_url="",
                hiddenlayer_api_key="",
                openshell_gateway="",
            )
            isolated = FloodOpsService(local, Store(local.db_path))
            return await EvaluationRunner(isolated)._run_isolated()
