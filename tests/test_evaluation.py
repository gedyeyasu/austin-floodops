from dataclasses import replace

import pytest

from app.config import settings
from app.evaluation.runner import EvaluationRunner
from app.learning.memory import rank_memories
from app.models import PlaybookRule
from app.service import FloodOpsService
from app.storage.sqlite import Store


@pytest.mark.asyncio
async def test_evaluation_compares_all_scenarios_and_improves(tmp_path):
    local = replace(
        settings,
        db_path=tmp_path / "evaluation.sqlite3",
        kafka_bootstrap_servers="",
        supabase_url="",
        supabase_service_role_key="",
        hiddenlayer_interactions_url="",
        hiddenlayer_api_key="",
        hiddenlayer_client_id="",
        hiddenlayer_client_secret="",
    )
    service = FloodOpsService(local, Store(local.db_path))
    result = await EvaluationRunner(service).run()
    assert result["status"] == "completed"
    assert result["scenario_count"] == 3
    assert result["comparison"]["run_2"]["accuracy_percent"] > result["comparison"]["run_1"]["accuracy_percent"]
    assert result["comparison"]["run_2"]["interventions"] < result["comparison"]["run_1"]["interventions"]
    assert all(item["run_2"]["accurate"] for item in result["scenarios"])


def test_retired_evaluation_rule_is_excluded(tmp_path):
    store = Store(tmp_path / "evaluation.sqlite3")
    memory_id = store.add_memory(PlaybookRule(trigger="flash flood warning", action="set risk level to high", rationale="official warning", confidence=0.9, context_tags=["flash", "flood"]), "evaluation:test")
    assert store.retire_memory(memory_id)
    assert rank_memories(store, [], 3) == []
