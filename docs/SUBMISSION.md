# Austin FloodOps submission package

## Track

Primary: **Red Hat Live Data**. The qualifying mechanism is the autonomous thirty-second heartbeat over live public feeds; Kafka is an optional stream transport, not a track requirement.

Secondary technical strengths: Recursive Intelligence and HiddenLayer Runtime Security.

## 150–300 word submission description

Flood responders often have to correlate weather alerts, river-gage readings, crossing conditions, road closures, and local reports across separate systems while conditions change by the minute. Austin FloodOps is a persistent decision-support agent for emergency-operations personnel. Every thirty seconds it gathers fresh public evidence from the National Weather Service, the United States Geological Survey, and City of Austin sources, preserves timestamps and provenance, deduplicates unchanged records, and reacts only when the evidence changes.

New evidence is treated as untrusted. HiddenLayer scans six boundaries across ingestion, memory, model requests, proposed tool calls, tool results, and final output. NVIDIA Nemotron produces one structured recommendation containing risk, confidence, a reversible action, and exact evidence references grounded against the input. The adapter normalizes only identifiers the model actually wrote and fails closed when the required grounded references are absent. A deterministic policy prevents automatic dispatch and requires a human operator to approve or reject consequential actions. Operator corrections become versioned playbook rules that can be retrieved during later incidents, with a controlled evaluation comparing behavior before and after learning.

When configured, a Kafka-compatible broker round-trips new records through publish and consume before assessment; Docker Compose provides this locally through Redpanda. Supabase mirrors the local SQLite ledger. A real NemoClaw/OpenShell sandbox proof uses managed Nemotron inference and demonstrates deny-by-default egress containment. Austin FloodOps does not claim to predict flood inundation or replace incident command. Its goal is to reduce coordination delay between fragmented live evidence and a safe, cited, auditable human decision.

## Required submission fields

- Project title: Austin FloodOps
- Team name: Austin FloodOps
- Team members, roles, and contact details: **ADD BEFORE SUBMISSION**
- Loom URL, two to five minutes, camera on: **ADD BEFORE SUBMISSION**
- Public repository URL: **MAKE PUBLIC ONLY AFTER CREDENTIAL ROTATION AND HISTORY CLEANUP**
- Deployed URL or working-application capture: **ADD BEFORE SUBMISSION**

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

## Known limitations

- The impact calculation is a transparent screening model, not a hydraulic inundation model.
- LCRA, TxDOT, and Austin endpoints may be unavailable or return unsupported formats; they remain visibly degraded with no synthetic live fallback.
- WebEOC is a standards-oriented preview adapter and has no agency authorization or production credentials.
- Resource assignment and routing are prototypes and require agency data and acceptance testing.
- The recursive evaluation is controlled harness evidence, not a production-accuracy claim.
- vLLM does not qualify for its bounty unless a real self-hosted endpoint is configured and used in the recorded loop.
