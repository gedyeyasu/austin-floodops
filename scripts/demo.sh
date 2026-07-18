#!/usr/bin/env bash
set -euo pipefail

port="${PORT:-8080}"
base="http://127.0.0.1:${port}"
demo_db="${DEMO_DB_PATH:-/tmp/austin-floodops-demo.sqlite3}"

HEARTBEAT_ENABLED="${HEARTBEAT_ENABLED:-true}" DB_PATH="$demo_db" .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port "$port" >/tmp/austin-floodops-demo.log 2>&1 &
server_pid=$!
trap 'kill "$server_pid" 2>/dev/null || true' EXIT

for _ in $(seq 1 30); do
  if curl -fsS "$base/health" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

printf 'Dashboard: %s\n' "$base"

printf 'Demo server is running. Press Ctrl-C to stop.\n'
wait "$server_pid"
