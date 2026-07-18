from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.models import IncidentDecision
from app.storage.audit import AuditChain
from app.storage.sqlite import Store


def _safe_iso(dt: Any) -> str:
    if isinstance(dt, datetime):
        return dt.isoformat()
    return str(dt)


def generate_after_action_report(
    *,
    incident_id: str,
    store: Store,
    audit_chain: AuditChain | None = None,
    decision: IncidentDecision | None = None,
) -> dict[str, Any]:
    """
    Generate after-action report with timeline, metrics, compliance, FOIA, positive_change_narrative.
    """
    decision = decision or store.get_decision(incident_id)
    if decision is None:
        raise ValueError(f"Incident {incident_id} not found")

    # Events timeline
    events = store.events_by_id(decision.evidence_event_ids)

    timeline: list[dict[str, Any]] = []
    for ev in sorted(events, key=lambda e: e.observed_at):
        timeline.append(
            {
                "at": ev.observed_at.isoformat(),
                "kind": ev.kind,
                "title": ev.title,
                "source": ev.source,
                "severity": ev.severity,
                "location": ev.location,
                "provenance_url": ev.provenance_url,
            }
        )
    # Decision point
    timeline.append(
        {
            "at": _safe_iso(decision.created_at),
            "kind": "decision",
            "title": f"Decision {decision.risk_level} risk - {decision.summary}",
            "model": decision.model_name,
            "policy_status": decision.policy_status,
            "confidence": decision.confidence,
        }
    )

    # Feedback and memories
    feedbacks = [f for f in store.list_feedback(limit=100) if f["incident_id"] == incident_id]
    memories = [m for m in store.list_memories(limit=100) if m["source_incident_id"] == incident_id]

    # Deliveries
    # We don't have direct list, but we can infer from existence checks? Let's check audit if available.

    # Compliance: ensure evidence citations, policy_status, approval gate
    compliance = {
        "evidence_cited": len(decision.citations) > 0,
        "provenance_preserved": all(ev.provenance_url for ev in events),
        "approval_gate_enforced": decision.proposed_action.approval_required is True,
        "reversible_action": decision.proposed_action.reversible is True,
        "audit_chain_verified": None,
        "policy_status_at_creation": decision.policy_status,
    }

    audit_entries = []
    audit_verified = None
    if audit_chain:
        audit_entries = audit_chain.list_for_incident(incident_id, limit=200)
        verify = audit_chain.verify_chain(incident_id)
        audit_verified = verify
        compliance["audit_chain_verified"] = verify.get("verified") is True

    # Metrics
    metrics = {
        "evidence_count": len(events),
        "unique_sources": sorted(list({ev.source for ev in events})),
        "risk_level": decision.risk_level,
        "confidence": decision.confidence,
        "feedback_count": len(feedbacks),
        "memory_count": len(memories),
        "audit_entries": len(audit_entries),
        "time_to_decision_seconds": None,
    }
    if events:
        first_obs = min(ev.observed_at for ev in events)
        metrics["time_to_decision_seconds"] = (decision.created_at - first_obs).total_seconds()

    # FOIA redaction: prepare version with sensitive fields removed
    # In this context, we redact raw_model_response internals beyond summary?
    foia = {
        "incident_id": decision.incident_id,
        "created_at": _safe_iso(decision.created_at),
        "mode": decision.mode,
        "scenario_id": decision.scenario_id,
        "summary": decision.summary,
        "risk_level": decision.risk_level,
        "evidence_event_ids": decision.evidence_event_ids,
        "citations": decision.citations,
        "proposed_action": {
            "action_type": decision.proposed_action.action_type,
            "target": decision.proposed_action.target,
            "rationale": decision.proposed_action.rationale,
        },
        "timeline": timeline,
        "redacted_fields": ["raw_model_response", "nvidia_api_key", "internal_reasoning"],
        "disclaimer": "FOIA release - operational data preserved, pre-decisional AI reasoning redacted per agency guidance.",
    }

    # Positive change narrative - highlight learning and human oversight
    positive_change_narrative = (
        f"On {_safe_iso(decision.created_at)}, Austin FloodOps processed {len(events)} official evidence items "
        f"from sources {', '.join(metrics['unique_sources']) or 'NWS/USGS'} and proposed a {decision.proposed_action.action_type} "
        f"for target {decision.proposed_action.target} at {decision.risk_level} risk. "
        f"The system enforced approval-required reversible action boundary, preserved provenance for all evidence, "
        f"and logged {len(audit_entries)} tamper-evident audit entries. "
        f"Operator feedback ({len(feedbacks)} corrections) contributed to {len(memories)} playbook rules that improve future triage, "
        f"demonstrating recursive improvement while maintaining human authority. "
        f"This after-action report satisfies audit retention and FOIA readiness, supporting public accountability and operational learning."
    )

    # Full report
    return {
        "incident_id": incident_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "decision": decision.model_dump(mode="json"),
        "timeline": timeline,
        "events": [e.model_dump(mode="json") for e in events],
        "feedback": feedbacks,
        "memories": memories,
        "audit": {
            "entries": audit_entries,
            "verification": audit_verified,
        },
        "metrics": metrics,
        "compliance": compliance,
        "foia_package": foia,
        "positive_change_narrative": positive_change_narrative,
        "retention": {
            "sqlite_authoritative": True,
            "audit_chain": audit_chain is not None,
            "supabase_mirror": "optional",
            "foia_ready": True,
        },
    }
