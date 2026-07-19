# Austin FloodOps: Current Engineering State

Updated July 18, 2026.

## Current product boundary

Austin FloodOps is an approval-gated hackathon prototype for correlating live public flood evidence. It is not an autonomous dispatcher, hydraulic flood model, or authorized government integration.

Public application: <https://austin-floodops-gedeon-tona-us-dev.apps.rm1.0a51.p1.openshiftapps.com>

## Implemented

- Thirty-second heartbeat over National Weather Service, United States Geological Survey, Austin, and optional Texas adapters.
- Stable normalization, deduplication, freshness, and provenance.
- Honest per-source degradation with no synthetic records in live mode.
- Kafka-compatible publish, consume, revalidation, and assessment path when configured.
- Local Docker Compose and deployed OpenShift Redpanda stacks with strict stream verification.
- NVIDIA Nemotron forced decision function calls with retry, schema validation, enumerated fields, and evidence-grounded citations.
- HiddenLayer six-boundary instrumentation when valid credentials are configured.
- Deterministic reversible-action and human-approval policy.
- Persistent SQLite ledger, verified Supabase mirror, feedback memory, evaluation harness, and application audit chain.
- Clearly labeled replay, heuristic simulation, linear gage prediction, demo resource inventory, and interoperability previews.
- Read-only public access and a secure demo operator login that issues a browser-memory supervisor token.

## Verified in the final deployed iteration

- All 54 automated tests pass.
- Application exposes no duplicate method-and-path route registrations.
- Live collection returned observed National Weather Service, United States Geological Survey, and Austin crossing records.
- Unavailable Austin road, Lower Colorado River Authority, DriveTexas, and Austin 311 adapters reported degraded instead of fabricating data.
- The public heartbeat is healthy, with zero consecutive failures at the final verification.
- OpenShift Redpanda published and consumed matching records before assessment.
- Hosted NVIDIA Nemotron produced a high-risk approval-gated decision through the forced tool contract with grounded citations.
- HiddenLayer completed all six model-interaction boundaries.
- Supabase, routing, role permissions, demo login, and the hash-chained audit record passed runtime probes.
- NemoClaw and OpenShell are separate sandbox proof, not configured inside the public OpenShift application.

## Required before submission

1. Rotate any credential ever committed and purge it from history before making the repository public.
2. Add team/contact details and the final public repository address to `docs/SUBMISSION.md`.
3. Record the demo using `docs/LOOM_SCRIPT.md` and add the Loom address to the submission.
4. Re-run the health and heartbeat checks immediately before recording because vendor credentials and public sources can change.

## Required before an operational pilot

- Agency sponsorship and written authorization.
- Confirmed data contracts and source-specific service-level expectations.
- Station-specific hydrologic and hydraulic calibration.
- Accessibility, security, privacy, reliability, and disaster-recovery reviews.
- Vendor validation for Common Alerting Protocol, Emergency Data Exchange Language, and WebEOC exports.
- Tabletop exercises and supervised field trials with emergency managers.
