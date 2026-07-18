#!/usr/bin/env bash
set -euo pipefail

port="${FLOODOPS_SMOKE_PORT:-18181}"
db_path="${DB_PATH:-/tmp/austin-floodops-smoke-$$.sqlite3}"
log_path="/tmp/austin-floodops-smoke-$$.log"
base="http://127.0.0.1:${port}"

if curl -fsS "${base}/health" >/dev/null 2>&1; then
  echo "Smoke port ${port} is already serving another process; choose FLOODOPS_SMOKE_PORT." >&2
  exit 1
fi

DB_PATH="$db_path" \
HEARTBEAT_ENABLED=false \
KAFKA_BOOTSTRAP_SERVERS="" \
HIDDENLAYER_CLIENT_ID="" \
HIDDENLAYER_CLIENT_SECRET="" \
SUPABASE_URL="" \
SUPABASE_SERVICE_ROLE_KEY="" \
ENABLE_RBAC=false \
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port "$port" >"$log_path" 2>&1 &
server_pid=$!
trap 'kill "$server_pid" 2>/dev/null || true' EXIT

echo "Waiting for isolated smoke server on ${base}..."
ready=false
for _ in $(seq 1 30); do
  if ! kill -0 "$server_pid" 2>/dev/null; then
    echo "Smoke server exited before readiness. See ${log_path}." >&2
    exit 1
  fi
  if curl -fsS "$base/health" > /tmp/austin-floodops-smoke-health.json 2>/dev/null; then
    ready=true
    break
  fi
  sleep 1
done
if [[ "$ready" != "true" ]]; then
  echo "Smoke server did not become ready. See ${log_path}." >&2
  exit 1
fi

curl -fsS "$base/api/heartbeat" > /tmp/austin-floodops-smoke-heartbeat.json
curl -fsS "$base/api/simulate" \
  -H 'content-type: application/json' \
  -d '{"mode":"replay","scenario_id":"gage-rise-with-warning","horizon_minutes":60}' \
  > /tmp/austin-floodops-smoke-simulation.json
curl -fsS -X POST "$base/api/security/adversarial-test" > /tmp/austin-floodops-smoke-adversarial.json
curl -fsS -X POST "$base/api/integrations/kafka/probe" > /tmp/austin-floodops-smoke-kafka.json

python3 - <<'PY'
import json
from pathlib import Path

def load(name):
    return json.loads(Path(f"/tmp/austin-floodops-smoke-{name}.json").read_text())

health = load("health")
heartbeat = load("heartbeat")
simulation = load("simulation")
adversarial = load("adversarial")
kafka = load("kafka")

assert health["status"] in {"ok", "degraded"}
assert heartbeat["enabled"] is False
assert simulation["estimate"]["scenario_id"] == "gage-rise-with-warning"
assert simulation["estimate"]["evidence_event_ids"]
assert adversarial["status"] == "quarantined" and adversarial["policy"] == "blocked"
assert kafka["status"] == "unconfigured"

print(json.dumps({
    "health": health["status"],
    "simulation_risk": simulation["estimate"]["risk_level"],
    "adversarial_policy": adversarial["policy"],
    "unconfigured_kafka_fails_honestly": kafka["status"],
}, indent=2))
PY

echo "Local smoke passed. Logs: ${log_path}"
