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
- `POST /api/decisions/{incident_id}/webeoc` is the primary Texas responder adapter. It submits the approved CAP payload through TDEM WebEOC's documented SOAP `AddData` operation; it remains blocked until an authorized board/position/incident configuration is present.
- HiddenLayer is an optional runtime scan of the Nemotron interaction. Set its tenant-specific Interactions URL and key to enable fail-closed scanning. NemoClaw/OpenShell remains provider-managed: the sandbox policy does not expose raw inference credentials.
- Deployment target: run the API/agent in a NemoClaw/OpenShell container (Brev is preferred for the NVIDIA demo) and use Supabase Postgres/Realtime for the durable ledger. The linked Supabase project should deploy `supabase/migrations/20260718000000_initial_floodops_ledger.sql`; `supabase/schema.sql` remains a readable manual fallback. Do not deploy the FastAPI process to Supabase, and never put its service-role key in browser code.
- `/api/integrations/supabase/probe` verifies the server-side REST connection. Assessments and feedback dual-write to Supabase when configured, while SQLite remains authoritative if the remote service is unavailable.
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

## Test the project

Run the deterministic end-to-end smoke path:

```bash
make smoke
```

Then open <http://127.0.0.1:8080> and click **Run replay simulation**. This works without external model credentials. **Run live assessment** uses the real NWS/USGS feeds and NVIDIA Nemotron; it is blocked if the NVIDIA endpoint is unavailable.

The smoke output reports the Supabase probe separately. A `404` from `/rest/v1/events` means the project is configured but the migration has not been deployed. Supabase GitHub integration must use the repository root (`.`) as its working directory and deploy the `supabase/migrations/` directory.

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
