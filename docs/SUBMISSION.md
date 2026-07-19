# Austin FloodOps submission package

## Track

Primary: **Red Hat Live Data**. The qualifying mechanism is the autonomous thirty-second heartbeat over live public feeds; Kafka is an optional stream transport, not a track requirement.

Secondary technical strengths: Recursive Intelligence and HiddenLayer Runtime Security.

## 150–300 word submission description

Flood responders often have to correlate weather alerts, river-gage readings, crossing conditions, road closures, and local reports across separate systems while conditions change by the minute. Austin FloodOps is a persistent decision-support agent for emergency-operations personnel. Every thirty seconds it gathers fresh public evidence from the National Weather Service, the United States Geological Survey, and City of Austin sources, preserves timestamps and provenance, deduplicates unchanged records, and reacts only when the evidence changes.

New evidence is treated as untrusted. HiddenLayer scans six boundaries across ingestion, memory, model requests, proposed tool calls, tool results, and final output. NVIDIA Nemotron is forced to call a typed incident-decision function containing risk, confidence, one reversible action, and exact evidence references grounded against the input. The adapter accepts only identifiers the model actually wrote and fails closed when the required grounded references are absent. A deterministic policy prevents automatic dispatch and requires a human operator to approve or reject consequential actions. Operator corrections become versioned playbook rules that can be retrieved during later incidents, with a controlled evaluation comparing behavior before and after learning.

The public application and a Kafka-compatible Redpanda broker run continuously on Red Hat OpenShift. New records round-trip through publish and consume before assessment. A persistent SQLite ledger remains authoritative while Supabase mirrors records into hosted PostgreSQL. A separate NemoClaw and OpenShell sandbox proof uses managed Nemotron inference and demonstrates deny-by-default network containment; it is not represented as the boundary around the public OpenShift pod. Austin FloodOps does not claim to predict flood inundation or replace incident command. Its goal is to reduce coordination delay between fragmented live evidence and a safe, cited, auditable human decision.

## Required submission fields

- Project title: Austin FloodOps
- Team name: Austin FloodOps
- Team members, roles, and contact details: **ADD BEFORE SUBMISSION**
- Loom URL, two to five minutes, camera on: **ADD BEFORE SUBMISSION**
- Public repository URL: **MAKE PUBLIC ONLY AFTER CREDENTIAL ROTATION AND HISTORY CLEANUP**
- Deployed URL: https://austin-floodops-gedeon-tona-us-dev.apps.rm1.0a51.p1.openshiftapps.com

Demo operator email: `gedeon@aitx.com`. Share the password separately; never
place it in the submission text, repository, screenshot, or video.

## Reproduction

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[texas,test]'
cp .env.example .env
.venv/bin/pytest -q
.venv/bin/uvicorn app.main:app --port 8080
```

For the local Kafka-compatible path:

```bash
docker compose up --build
make stream-smoke
make openshell-smoke
```

For the recorded path, follow [LOOM_SCRIPT.md](LOOM_SCRIPT.md). The script uses
the deployed OpenShift application and explicitly separates current live data,
labeled replay, production probes, and separate OpenShell evidence.

## Known limitations

- The impact calculation is a transparent screening model, not a hydraulic inundation model.
- LCRA, TxDOT, and Austin endpoints may be unavailable or return unsupported formats; they remain visibly degraded with no synthetic live fallback.
- WebEOC is a standards-oriented preview adapter and has no agency authorization or production credentials.
- Resource assignment and routing are prototypes and require agency data and acceptance testing.
- The recursive evaluation is controlled harness evidence, not a production-accuracy claim.
- vLLM does not qualify for its bounty unless a real self-hosted endpoint is configured and used in the recorded loop.
