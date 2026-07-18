# Verification Evidence

Evidence files are supporting artifacts, not permanent truth. Re-run the release gates from the final commit because public endpoints, credentials, and vendor services can change.

## Current hardening evidence

- `live-sources-2026-07-18.json`: one heartbeat over real public sources. Successful sources contain observed counts; failed optional adapters are degraded with zero fabricated events.
- `kafka-probe.log`: isolated Kafka-compatible producer and consumer observed the same event identifier.
- `end-to-end-2026-07-18.json`: Dockerized replay went through five Kafka publications and consumptions, six HiddenLayer boundaries, NVIDIA Nemotron, citation grounding, and the approval-required policy with no stream fallback.
- `openshell-runtime-2026-07-18.json`: the real `austin-floodops` NemoClaw sandbox completed managed Nemotron inference and denied an undeclared outbound host with an OpenShell policy response.

## Other checked-in artifacts

The remaining logs and exports record earlier feature exercises: HiddenLayer adversarial scanning, OpenShell allow-and-deny behavior, prediction, resource-demo state, routing, and export formats. Treat them as historical until they are refreshed. Do not infer a current vendor connection or agency authorization from a file in this directory.

## Evidence policy

- Live mode stores only successfully parsed observed records with source, time, and provenance.
- Replay fixtures are labeled `mode: replay`.
- Optional source failure appears as `degraded`; it never creates a synthetic live replacement.
- Configured and verified are separate runtime states.
- Normalized citations must be exact identifiers or provenance addresses that the model itself wrote and that exist in the selected input evidence. Missing references are not silently filled.
- No credential value may be written to evidence, logs, client code, or documentation.
- Simulation and prediction values are screening heuristics, not hydraulic results.

Run the current proof:

```bash
make test
make smoke
make stream-smoke
make openshell-smoke
```
