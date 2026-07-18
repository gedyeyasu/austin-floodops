# Austin FloodOps

Austin FloodOps is a decision-support service for flood operations. It gathers official National Weather Service alerts and USGS instantaneous observations, records their provenance, asks NVIDIA Nemotron for one structured recommendation, and keeps any action approval-gated and reversible.

The current vertical slice is real-data-first:

- `DATA_MODE=live` calls the public NWS and USGS APIs and will not fabricate evidence.
- Nemotron uses NVIDIA's OpenAI-compatible hosted endpoint. If no key is configured, the assessment is explicitly blocked.
- SQLite stores event, decision, and versioned operator-feedback records locally; Supabase is an optional persistence adapter in the plan.
- `app/streaming/kafka.py` is the real Red Hat Streams/Kafka producer/consumer path. Configure the broker and call `POST /api/integrations/kafka/probe` to verify a publish/consume round trip.
- `openshell/austin-floodops.yaml` is the restrictive sandbox policy artifact: public evidence and NVIDIA inference are allowlisted, credentials are narrowed, and actions default to deny.
- `POST /api/simulate` runs the deterministic `threshold-v1` impact model against live or replay evidence. It estimates screening exposure, depth, route delay, and priority crossings; it is not a hydraulic forecast and every assumption is returned in the response.
- `GET /api/decisions/{incident_id}/cap` exports a standards-based CAP 1.2 message. `POST /api/decisions/{incident_id}/first-responder` can send it to a configured responder webhook only after the decision is approved and the request includes `confirm=true`; delivery is idempotent.
- HiddenLayer is an optional runtime scan of the Nemotron interaction. Set its tenant-specific Interactions URL and key to enable fail-closed scanning. NemoClaw/OpenShell remains provider-managed: the sandbox policy does not expose raw inference credentials.
- `DATA_MODE=replay` uses the checked-in East Austin scenario only for repeatable tests and demos. Replay is always labeled replay.

## Run locally

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[test]'
cp .env.example .env
.venv/bin/pytest -q
.venv/bin/uvicorn app.main:app --reload --port 8080
```

Open <http://127.0.0.1:8080>. The integration panel distinguishes configured services from verified services. Set `NVIDIA_API_KEY` or `NVIDIA_INFERENCE_API_KEY` in `.env` to enable live Nemotron assessment.

## Demo path

For a deterministic demo, set `DATA_MODE=replay`, then call:

```bash
curl -s http://127.0.0.1:8080/api/assess \
  -H 'content-type: application/json' \
  -d '{"mode":"replay","scenario_id":"east-austin-night-market"}'
```

Run the impact simulation without an NVIDIA key:

```bash
curl -s http://127.0.0.1:8080/api/simulate \
  -H 'content-type: application/json' \
  -d '{"mode":"replay","scenario_id":"east-austin-night-market","horizon_minutes":60}'
```

The replay still requires a real NVIDIA key for an assessment. Without one, the service returns the evidence and a clear integration-blocked state; it never swaps in a mock model response.

## Project plan

See [HACKATHON_PLAN.md](HACKATHON_PLAN.md) for the gstack decision record, track fit, integration gates, and the remaining sponsor adapters.
