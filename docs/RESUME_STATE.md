# Austin FloodOps: Current Engineering State

Updated July 18, 2026.

## Current product boundary

Austin FloodOps is an approval-gated hackathon prototype for correlating live public flood evidence. It is not an autonomous dispatcher, hydraulic flood model, or authorized government integration.

## Implemented

- Thirty-second heartbeat over National Weather Service, United States Geological Survey, Austin, and optional Texas adapters.
- Stable normalization, deduplication, freshness, and provenance.
- Honest per-source degradation with no synthetic records in live mode.
- Kafka-compatible publish, consume, revalidation, and assessment path when configured.
- Local Redpanda Docker Compose stack and strict stream smoke test.
- NVIDIA Nemotron structured decisions with retry, schema validation, enumerated fields, and evidence-grounded citations.
- HiddenLayer six-boundary instrumentation when valid credentials are configured.
- Deterministic reversible-action and human-approval policy.
- SQLite ledger, optional Supabase mirror, feedback memory, evaluation harness, and application audit chain.
- Clearly labeled replay, heuristic simulation, linear gage prediction, demo resource inventory, and interoperability previews.

## Verified in the current hardening iteration

- Automated test suite passes.
- Application exposes no duplicate method-and-path route registrations.
- Live collection returned observed National Weather Service, United States Geological Survey, and Austin crossing records.
- Unavailable Austin road, Lower Colorado River Authority, DriveTexas, and Austin 311 adapters reported degraded instead of fabricating data.
- Live Nemotron compatibility and local Kafka-compatible streaming are re-verified before release; use the current command output, not old evidence, as the source of truth.

## Required before submission

1. Run `make test`, `make smoke`, and `make stream-smoke` from a clean checkout.
2. Confirm the dashboard shows the current runtime state without claiming unrun integrations are verified.
3. Rotate any credential ever committed and purge it from history before making the repository public.
4. Replace submission and video placeholders in `docs/SUBMISSION.md`.
5. Record the demo using `docs/LOOM_SCRIPT.md`.

## Required before an operational pilot

- Agency sponsorship and written authorization.
- Confirmed data contracts and source-specific service-level expectations.
- Station-specific hydrologic and hydraulic calibration.
- Accessibility, security, privacy, reliability, and disaster-recovery reviews.
- Vendor validation for Common Alerting Protocol, Emergency Data Exchange Language, and WebEOC exports.
- Tabletop exercises and supervised field trials with emergency managers.
