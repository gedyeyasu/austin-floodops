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

## Final production verification, July 18, 2026

- 54 automated tests passed from the final application tree.
- The public OpenShift route returned `status: ok` over Transport Layer Security.
- The autonomous heartbeat was running with zero consecutive failures.
- National Weather Service, United States Geological Survey, and Austin crossing adapters returned observed records; optional Austin road, Lower Colorado River Authority, DriveTexas, and Austin 311 adapters were visibly degraded.
- A Kafka-compatible Redpanda record was published and consumed with the same event identifier before assessment.
- NVIDIA Nemotron called the forced `record_incident_decision` tool and supplied exact evidence citations that passed application grounding.
- HiddenLayer completed all three pre-model and all three post-model scans. Non-blocking personally identifiable information and address findings remained visible; prompt injection was not detected on the benign run.
- Supabase, Open Source Routing Machine routing, demo authentication, role permissions, and the application audit chain passed runtime probes.
- NemoClaw and OpenShell are not configured inside the public OpenShift application. Separate checked-in sandbox evidence must be described as a separate proof, not as the deployed runtime.

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

For the hosted judged path, use the public route in `README.md`, sign in with
the presenter-provided demo account, and run **Inject · gage rise + warning**.
Do not display or speak the password during recording.
