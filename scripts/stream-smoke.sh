#!/usr/bin/env bash
set -euo pipefail

floodops_port="${FLOODOPS_PORT:-18081}"
base="${BASE_URL:-http://127.0.0.1:${floodops_port}}"
export FLOODOPS_PORT="$floodops_port"
# The proof must exercise new evidence on every run. Use an ephemeral database
# inside the recreated app container without deleting the operator's ledger.
export FLOODOPS_DB_PATH="/tmp/austin-floodops-stream-smoke.sqlite3"

docker compose up --build -d redpanda app
ready=false
for _ in $(seq 1 60); do
  if curl -fsS "$base/health" >/dev/null 2>&1; then
    ready=true
    break
  fi
  sleep 2
done
if [[ "$ready" != "true" ]]; then
  echo "Dockerized FloodOps did not become ready at ${base}." >&2
  docker compose logs --tail=100 app >&2
  exit 1
fi

echo "=== Dedicated Kafka publish/consume probe ==="
curl -fsS -X POST "$base/api/integrations/kafka/probe" > /tmp/austin-floodops-kafka-probe.json

echo "=== Replay through Kafka, HiddenLayer, NVIDIA, and policy ==="
curl -fsS "$base/api/assess" \
  -H 'content-type: application/json' \
  -d '{"mode":"replay","scenario_id":"gage-rise-with-warning"}' \
  > /tmp/austin-floodops-stream-assessment.json

python3 - <<'PY'
import json
from pathlib import Path

probe = json.loads(Path("/tmp/austin-floodops-kafka-probe.json").read_text())
assessment = json.loads(Path("/tmp/austin-floodops-stream-assessment.json").read_text())
assert probe["status"] == "verified", probe
assert probe["published"] == 1 and probe["consumed"] == 1
assert assessment["error"] is None, assessment.get("error")
decision = assessment["decision"]
assert decision and decision["model_name"] != "hiddenlayer-quarantine"
security = decision["raw_model_response"]["security"]
stream = security["kafka"]
hiddenlayer = security["hiddenlayer"]
assert stream["status"] == "verified", stream
assert stream["published"] >= 1 and stream["published"] == stream["consumed"]
assert stream["fallback"] == 0
assert hiddenlayer["status"] in {"verified", "scanned_with_findings"}, hiddenlayer
assert set(hiddenlayer["boundaries_scanned"]) == {
    "ingested_content", "user_prompt_memory", "model_request",
    "tool_call", "tool_result", "final_answer",
}
citation_validation = decision["raw_model_response"]["austin_floodops"]["citation_validation"]
assert citation_validation["status"] in {"model_citations_valid", "model_text_references_grounded"}

print(json.dumps({
    "probe": probe["status"],
    "stream": stream,
    "hiddenlayer": hiddenlayer["status"],
    "hiddenlayer_boundaries": hiddenlayer["boundaries_scanned"],
    "model": decision["model_name"],
    "citation_validation": citation_validation,
    "policy": decision["policy_status"],
}, indent=2))
PY

echo "Strict streaming assessment passed. Compose stack remains running for inspection."
