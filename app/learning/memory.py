from __future__ import annotations

import re
from typing import Any

from app.models import FloodEvent
from app.storage.sqlite import Store


def _terms(value: str) -> set[str]:
    return {term for term in re.findall(r"[a-z0-9]+", value.lower()) if len(term) > 2}


def rank_memories(store: Store, events: list[FloodEvent], limit: int = 3) -> list[dict[str, Any]]:
    event_terms: set[str] = set()
    for event in events:
        event_terms |= _terms(" ".join(filter(None, [event.source, event.kind, event.title, event.severity, event.location or "", event.unit or ""])))
    ranked: list[tuple[float, dict[str, Any]]] = []
    for memory in store.active_memories(100):
        tags = {str(tag).lower() for tag in memory.get("context_tags", [])}
        trigger_terms = _terms(str(memory.get("trigger") or memory.get("rule") or ""))
        other_terms = _terms(" ".join(str(memory.get(key) or "") for key in ("action", "rationale", "rule")))
        score = 3 * len(tags & event_terms) + 2 * len(trigger_terms & event_terms) + len(other_terms & event_terms)
        score += float(memory.get("confidence", 0.0))
        ranked.append((score, memory))
    ranked.sort(key=lambda item: (item[0], item[1]["id"]), reverse=True)
    positive = [memory for score, memory in ranked if score > float(memory.get("confidence", 0.0))]
    return positive[:limit]


def retrieval_context(store: Store, events: list[FloodEvent], limit: int = 3) -> str:
    memories = rank_memories(store, events, limit)
    if not memories:
        return "No relevant operator-validated playbook rules are available."
    lines = ["Relevant operator-validated playbook rules (advisory only; evidence and approval policy still control):"]
    for item in memories:
        tags = ", ".join(item.get("context_tags", [])) or "none"
        lines.append(
            f"- Rule {item['id']} v{item.get('version', 1)}: IF {item.get('trigger') or item['rule']} "
            f"THEN {item.get('action') or item['rule']}. Rationale: {item.get('rationale') or 'operator correction'}. "
            f"Confidence: {float(item.get('confidence', 0.5)):.2f}. Tags: {tags}."
        )
    return "\n".join(lines)
