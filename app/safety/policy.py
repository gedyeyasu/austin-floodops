from __future__ import annotations

from dataclasses import dataclass

from app.models import IncidentDecision


@dataclass(frozen=True)
class PolicyResult:
    status: str
    reason: str


def evaluate(decision: IncidentDecision, *, operator_approved: bool = False) -> PolicyResult:
    action = decision.proposed_action
    if not action.reversible:
        return PolicyResult("blocked", "Only reversible actions are permitted.")
    if decision.risk_level in {"high", "catastrophic"} and not operator_approved:
        return PolicyResult("approval_required", "High-impact action requires explicit operator approval.")
    if action.action_type == "quarantine":
        return PolicyResult("blocked", "Quarantine is a safety hold, not an executable action.")
    if not operator_approved:
        return PolicyResult("approval_required", "Operator approval is required before execution.")
    return PolicyResult("allowed", "Approved reversible action.")

