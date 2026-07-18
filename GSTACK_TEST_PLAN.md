# Austin FloodOps gstack Test Plan

This is the executable test plan for the engineering review. Every test must pass with real integrations before that integration is named in the submission.

## Smoke gates

1. Produce and consume one real event on the Red Hat Streams/Kafka topic.
2. Fetch a real NWS alert and USGS/Austin observation; verify timestamps and freshness.
3. Call NVIDIA's hosted `nvidia/nemotron-3-nano-30b-a3b` endpoint through NemoClaw/OpenShell and validate the action schema.
4. Submit a poisoned payload to the real HiddenLayer path and verify quarantine.
5. Trigger the real OpenShell policy with an exfiltration attempt and capture the deny log.
6. Write and read the event, decision, and memory from Supabase.

## Functional tests

- Normal incident creates one typed assessment and one approval-gated crossing action.
- Duplicate event IDs are idempotent.
- Heartbeat resumes an unresolved incident without creating duplicate actions.
- Operator correction creates a new memory version, not a prompt edit.
- Replay retrieves the new rule and improves the recorded metric.
- Harmful memories can be retired and are excluded from later retrieval.

## Failure tests

- NWS or USGS timeout shows stale status and never claims LIVE.
- Kafka disconnect shows degraded status and preserves event IDs for retry.
- Model timeout or malformed output disables approval after bounded retry.
- NVIDIA endpoint 429/503 shows provider health and retry-after guidance; it never silently switches providers.
- HiddenLayer timeout fails closed for action execution.
- OpenShell blocks network exfiltration regardless of model intent.
- Supabase outage shows persistence pending and does not lose the local evidence queue.

## UI and submission tests

- Loading, empty, stale, replay, model error, blocked, pending approval, approved, rejected, quarantined, and retired-memory states are visible.
- Keyboard navigation and text labels do not rely on color alone.
- `make demo` or equivalent works from a clean environment without external credentials.
- `make preflight` reports each dependency as verified, unavailable, or intentionally omitted.
- Loom shows the same evidence recorded by the test run: timestamps, action, correction, metric, and deny log.
