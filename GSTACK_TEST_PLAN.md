# Austin FloodOps Verification Plan

This plan distinguishes automated coverage from live integration proof. A component is not verified merely because credentials exist or an old evidence file exists.

## Release gates

| Gate | Required proof |
|---|---|
| Automated behavior | `.venv/bin/pytest -q` passes from the current tree |
| Static quality | `git diff --check`, Python compilation, and route uniqueness pass |
| Live public data | National Weather Service, United States Geological Survey, and Austin return observed records; optional failures appear degraded |
| Nemotron | A real replay request returns the typed decision contract and all final citations match input evidence |
| Kafka-compatible stream | `make stream-smoke` publishes and consumes the same event identifier and exits zero |
| Local application | `make smoke` passes health, replay assessment, quarantine, and configured probes |
| Interface | Browser walkthrough covers loading, partial source failure, replay, model error, approval, rejection, quarantine, and offline states |
| Secrets | Current tree and Git history are scanned; leaked credentials are rotated and purged before public release |

## Automated coverage

- Event normalization, citation grounding, and source provenance types.
- Heartbeat deduplication, partial failures, and source recovery.
- Kafka unconfigured, degraded, and publish-consume assessment paths.
- Model fail-closed behavior and response parsing.
- Reversible-action approval policy.
- SQLite idempotency and versioned memory.
- Feedback, reflection, retrieval, and reassessment.
- Three-scenario evaluation and retired-rule exclusion.
- Common Alerting Protocol XML and WebEOC envelope construction.

## Failure expectations

| Failure | Required behavior |
|---|---|
| One public source fails | Other feeds continue; failed source is degraded with no fabricated event |
| Kafka fails | Stream is degraded and the counted direct safety fallback is used |
| Nemotron is unavailable or malformed twice | No decision is created; integration error is shown |
| HiddenLayer required scan fails | Assessment is blocked, not silently treated as clean |
| Supabase fails | SQLite remains authoritative; remote mirror failure does not lose local state |
| Harmful playbook memory | Operator can retire it; retrieval excludes it |
| Prompt injection | Content is quarantined before model inference |

## Demo reproducibility

```bash
make test
make smoke
make stream-smoke
make preflight
```

`make demo` starts the heartbeat and opens the interface. It does not automatically mutate evaluation state; the operator starts the evaluation from the dashboard.
