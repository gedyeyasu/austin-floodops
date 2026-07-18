#!/usr/bin/env bash
set -euo pipefail

port="${PORT:-8080}"
db_path="${DB_PATH:-/tmp/austin-floodops-smoke.sqlite3}"
base="http://127.0.0.1:${port}"

DB_PATH="$db_path" .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port "$port" > /tmp/austin-floodops-smoke.log 2>&1 &
server_pid=$!
trap 'kill "$server_pid" 2>/dev/null || true' EXIT

for _ in $(seq 1 30); do
  if curl -fsS "$base/health" >/tmp/austin-floodops-health.json; then break; fi
  sleep 1
done

curl -fsS "$base/health"
printf '\n--- replay simulation ---\n'
curl -fsS "$base/api/simulate" \
  -H 'content-type: application/json' \
  -d '{"mode":"replay","scenario_id":"east-austin-night-market","horizon_minutes":60}'
printf '\n--- Supabase probe ---\n'
curl -fsS -X POST "$base/api/integrations/supabase/probe"
printf '\n'
