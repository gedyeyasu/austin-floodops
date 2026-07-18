#!/usr/bin/env bash
set -euo pipefail

sandbox="${NEMOCLAW_SANDBOX:-austin-floodops}"
allow_output="$(mktemp -t floodops-openshell-allow.XXXXXX)"
deny_output="$(mktemp -t floodops-openshell-deny.XXXXXX)"
trap 'rm -f "$allow_output" "$deny_output"' EXIT

command -v nemoclaw >/dev/null

nemoclaw "$sandbox" exec --no-tty --timeout 60 -- \
  curl -fsS https://inference.local/v1/chat/completions \
  -H content-type:application/json \
  -d '{"model":"nvidia/nemotron-3-super-120b-a12b","messages":[{"role":"user","content":"Reply with exactly FLOODOPS_SANDBOX_OK"}],"temperature":0,"max_tokens":32,"chat_template_kwargs":{"enable_thinking":false}}' \
  > "$allow_output"

python3 - "$allow_output" <<'PY'
import json
import sys

data = json.load(open(sys.argv[1]))
choice = data["choices"][0]
assert data["model"] == "nvidia/nemotron-3-super-120b-a12b"
assert choice["message"]["content"] == "FLOODOPS_SANDBOX_OK"
assert choice["finish_reason"] == "stop"
PY

set +e
nemoclaw "$sandbox" exec --no-tty --timeout 30 -- curl -fsS https://example.com > "$deny_output" 2>&1
deny_status=$?
set -e
if [[ "$deny_status" -eq 0 ]]; then
  echo "OpenShell unexpectedly allowed undeclared egress to example.com." >&2
  exit 1
fi

python3 - "$deny_output" "$deny_status" <<'PY'
import json
import sys

output = open(sys.argv[1]).read()
status = int(sys.argv[2])
assert status == 22, (status, output)
assert "403" in output and "network policy denial" in output, output
print(json.dumps({
    "sandbox": "austin-floodops",
    "managed_inference": "verified",
    "model": "nvidia/nemotron-3-super-120b-a12b",
    "response": "FLOODOPS_SANDBOX_OK",
    "undeclared_egress": "denied",
    "denied_host": "example.com:443",
}, indent=2))
PY
