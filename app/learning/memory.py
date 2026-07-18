from __future__ import annotations

from app.storage.sqlite import Store


def retrieval_context(store: Store, limit: int = 5) -> str:
    memories = store.active_memories(limit)
    if not memories:
        return "No prior operator corrections are available."
    return "Prior operator corrections:\n" + "\n".join(f"- {item['rule']}" for item in memories)

