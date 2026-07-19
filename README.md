# Austin FloodOps v0.3.0

Approval-gated, audit-chained, AI-assisted decision support for flood emergency operations. Built for the AITX Community x NVIDIA Claw Agent Hackathon (July 17–19, 2026).

**Primary track:** Red Hat Live Data · **Secondary:** Recursive Intelligence · **Security:** HiddenLayer Runtime Security

## What It Does

Austin FloodOps watches live public incident feeds, produces one typed recommendation with citations and provenance, and keeps every consequential action approval-gated and reversible. Its evaluation harness measures whether operator-approved memory changes later recommendations; it does not assume every correction improves the model.

It is **not** a hydraulic flood model or autonomous dispatcher. It is an operational decision-support prototype over public NWS, USGS, and City of Austin evidence. The WebEOC component is an unconnected interoperability adapter, not an authorized government integration.

## Architecture

```text
NWS Alerts + USGS Gage + Austin Crossings + Road Closures
            |
            v
    Heartbeat Engine (30s poll, dedup, failure recovery)
            |
    Kafka-compatible stream when configured
    (publish → consume → assess; direct fallback is explicit)
            |
    HiddenLayer v2 SDK  (6 boundary scans)
            |
    NVIDIA Nemotron 3 Nano  (structured JSON incident decision)
            |
    Policy Gate  (approval-required, reversible-only, quarantine-safe)
            |
    SQLite + Supabase  (events, decisions, feedback, versioned memories, audit chain)
            |
    Dashboard  (Leaflet map, event timeline, learning panel, eval chart, security console)
```

## Sponsor Integrations

| Integration | Status | How It's Used |
|---|---|---|
| **NVIDIA Nemotron 3 Nano** | Runtime-verified | Structured incident assessment via the hosted NVIDIA endpoint; the gate turns verified only after a successful decision |
| **HiddenLayer Runtime Security** | Runtime-verified | Six-boundary scan with pre-model prompt-injection quarantine; the gate reports the last real scan |
| **NemoClaw / OpenShell** | Sandbox-only | Checked-in sandbox policy and deny evidence; Docker Compose alone does not enforce it |
| **Kafka-compatible streaming** | Runtime-verified | Redpanda provides the Kafka protocol locally and on OpenShift; `make stream-smoke` proves publish → consume before assessment |
| **Supabase** | Runtime-verified mirror | Remote probe plus best-effort mirror; SQLite remains authoritative if Supabase is unavailable |
| **vLLM** | Optional fallback | Counts only when a real self-hosted endpoint is configured and used |

## Data Sources

| Source | Endpoint | What It Provides |
|---|---|---|
| NWS Alerts | `api.weather.gov/alerts/active?area=TX` | Flash flood warnings, watches, emergency alerts |
| USGS Water Services | `waterservices.usgs.gov/nwis/iv/` | Gage height, streamflow at Colorado River site 08158000 |
| Austin Low-Water Crossings | `data.austintexas.gov/d/q6kt-v2zm` | 70+ crossing locations with gate types and gage numbers |
| Austin Road Closures | `data.austintexas.gov/resource/fw5i-n4te.json` | Real-time road closure status |
| LCRA Hydromet | `hydromet.lcra.org` | Attempted river-stage source; visibly degraded when unavailable |
| TxDOT DriveTexas | `drivetexas.org` | Attempted closure source; visibly degraded when unavailable |

Public source adapters do not require API keys. Unavailable sources are marked degraded and never replaced with synthetic live records. Replay fixtures are labeled and provide deterministic demonstrations.

## Quick Start

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[texas,test]'
cp .env.example .env
.venv/bin/pytest -q
.venv/bin/uvicorn app.main:app --reload --port 8080
```

Open <http://127.0.0.1:8080>. The dashboard shows the integration gate, event timeline, incident workspace, learning panel, evaluation chart, and security console.

**Minimum for live assessment:** set `NVIDIA_API_KEY` in `.env`.
**Minimum for Kafka:** set `KAFKA_BOOTSTRAP_SERVERS`.
**Minimum for HiddenLayer:** set `HIDDENLAYER_CLIENT_ID` and `HIDDENLAYER_CLIENT_SECRET`.

## Demo Path

```bash
make demo
```

Starts the server with the autonomous heartbeat enabled and leaves the dashboard open. Use the labeled replay controls for the deterministic learning demonstration:

1. **Run 1** (no memory) — baseline accuracy, latency, interventions
2. **Run 2** (after operator correction) — improved accuracy, fewer interventions
3. **Comparison** — accuracy delta, latency delta, intervention delta

The evaluation runs only when an operator clicks **Run learning evaluation**; loading the page does not mutate evaluation state.

## Testing

```bash
make test         # Unit and service-flow tests
make smoke        # Local API smoke: health + replay + security + configured probes
make stream-smoke # Docker Compose Redpanda publish/consume verification on port 18081 by default
make preflight   # Dependency status: NVIDIA, Kafka, Supabase, HiddenLayer, WebEOC, vLLM, OSRM
```

## Deploy on Red Hat OpenShift

The recommended hackathon deployment runs FastAPI and a real Kafka-compatible
Redpanda broker on OpenShift while Supabase remains the remote PostgreSQL
mirror:

```bash
brew install openshift-cli
oc login --web https://api.<cluster-domain>:6443
oc project <project-name>
./scripts/deploy-openshift.sh
```

The script keeps `.env` out of the image, creates an OpenShift Secret, performs
a binary container build, waits for both workloads, and verifies the public
Transport Layer Security health endpoint. See
[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

## Key Endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/health` | GET | Integration gate that distinguishes configured from verified |
| `/api/heartbeat` | GET | Heartbeat state: cycle count, source status, last decision |
| `/api/assess` | POST | Gather events → Nemotron assessment → policy gate → store |
| `/api/simulate` | POST | Deterministic threshold-v1 impact model |
| `/api/evaluation/run` | POST | 3-scenario before/after comparison with accuracy/latency metrics |
| `/api/memories` | GET | Versioned playbook rules with tags and confidence |
| `/api/memory/{id}/retire` | POST | Retire a harmful or outdated rule |
| `/api/security/adversarial-test` | POST | Inject prompt injection, verify quarantine |
| `/api/decisions/{id}/approve` | POST | Operator approves reversible action |
| `/api/decisions/{id}/reject` | POST | Operator rejects proposed action |
| `/api/decisions/{id}/cap` | GET | Export CAP 1.2 XML |
| `/api/decisions/{id}/first-responder` | POST | Send CAP to webhook (requires confirm + approval) |
| `/api/decisions/{id}/webeoc` | POST | Send CAP through a WebEOC SOAP adapter only when agency-issued credentials and explicit approval are present |
| `/api/decisions/{id}/feedback` | POST | Record operator correction → reflection → memory extraction |
| `/api/integrations/kafka/probe` | POST | Kafka publish/consume round-trip |
| `/api/integrations/hiddenlayer/probe` | POST | HiddenLayer scan verification |
| `/api/integrations/supabase/probe` | POST | Supabase REST connection verification |
| `/api/integrations/vllm/probe` | POST | vLLM endpoint verification |
| `/api/integrations/osrm/probe` | POST | OSRM routing verification |
| `/api/predict` | POST | Gage trajectory forecast with risk scoring |
| `/api/routing/detour` | POST | OSRM-based evacuation detour around blocked crossings |
| `/api/audit/recent` | GET | Recent audit chain entries |
| `/api/audit/{id}` | GET | Audit trail for specific incident |
| `/api/audit/verify/{id}` | GET | Verify audit chain integrity |
| `/api/after-action/{id}` | POST | Generate after-action report |
| `/api/resources` | GET/POST | Fictional exercise inventory workflow; no agency asset connection |
| `/api/export/events.csv` | GET | Evidence CSV draft for records-officer review |
| `/api/export/decisions.csv` | GET | Decision CSV draft for records-officer review |
| `/api/decisions/{id}/edxl-de` | GET | Unvalidated EDXL-DE-shaped interoperability draft |
| `/api/decisions/{id}/foia` | GET | Backward-compatible route for a draft records bundle; no release or retention determination |
| `/api/auth/token` | POST | JWT token issuance |
| `/api/auth/me` | GET | Current actor and role |

## Learning Mechanism

1. **Operator correction** → `POST /api/decisions/{id}/feedback`
2. **Nemotron reflection** → extracts structured PlaybookRule (trigger, action, rationale, confidence, context_tags)
3. **Tag-based ranking** → retrieves most relevant rules for current evidence
4. **Memory-augmented prompt** → injected into next Nemotron assessment
5. **Evaluation harness** → compares the baseline and memory-assisted runs without assuming improvement
6. **Retirement** → harmful or outdated rules can be individually retired

## Security

- **HiddenLayer v2 SDK** scans 6 boundaries per assessment: ingested content, user prompt/memory, model request, tool call, tool result, and final answer
- **Prompt injection quarantine** — poisoned events are blocked before reaching the model
- **Fail-closed security** — unavailable security scans block the decision path; unavailable data sources remain visible as degraded
- **RBAC** — optional JWT-based role-based access control (viewer, operator, supervisor, admin, and auditor); the internal system role cannot be issued by the token endpoint
- **Audit chain** — append-only log of every event, decision, approval, feedback, and memory change with verification
- **No secrets in client** — all API keys stay server-side; never logged or sent to browser

## OpenShell Policy

`openshell/austin-floodops.yaml` defines the restrictive sandbox:

- **Filesystem:** read-only replay data, read-write data directory and tmp
- **Process:** runs as sandbox user/group
- **Network:** only declared public-data, model, routing, and local-inference hosts are allowlisted
- **Credentials:** narrowed to sandbox scope; inference keys are provider-managed

The external sandbox proof is intentionally separate from the Docker application health. Run `make openshell-smoke` to execute one managed Nemotron request through `inference.local` and verify that OpenShell denies an undeclared outbound host. The dashboard stays unverified for OpenShell unless the application itself is launched through a configured gateway.

## Configuration

See `.env.example` for all 50+ configuration fields. Key groups:

| Group | Variables | Purpose |
|---|---|---|
| Runtime | `APP_ENV`, `DATA_MODE`, `HOST`, `PORT`, `DB_PATH` | Server configuration |
| Data Sources | `NWS_USER_AGENT`, `USGS_SITE_ID`, `POLL_SECONDS` | Public data feeds |
| NVIDIA | `NVIDIA_API_KEY`, `NEMOTRON_MODEL` | Primary AI assessment |
| vLLM | `VLLM_BASE_URL`, `VLLM_MODEL` | Fallback inference |
| Kafka | `KAFKA_BOOTSTRAP_SERVERS`, `KAFKA_TOPIC` | Event bus |
| Supabase | `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` | Remote persistence |
| HiddenLayer | `HIDDENLAYER_CLIENT_ID`, `HIDDENLAYER_CLIENT_SECRET` | Runtime security |
| WebEOC | `WEBEOC_API_URL`, `WEBEOC_USERNAME` | Texas responder adapter |
| RBAC | `JWT_SECRET`, `AUTH_BOOTSTRAP_TOKEN`, `ENABLE_RBAC` | Explicit role policy; secure token minting requires two independent 32+ character secrets |
| Features | `ENABLE_PREDICTION`, `ENABLE_AUDIT_CHAIN` | Feature toggles |

## Deployment

- **Local:** `make run` starts the FastAPI server with hot reload
- **Docker:** `make docker-build && make docker-run`
- **NemoClaw/OpenShell:** must run through the actual sandbox for the policy to be enforced
- **Supabase:** deploy `supabase/migrations/20260718000000_initial_floodops_ledger.sql` for remote ledger

## Project Structure

```text
app/
├── main.py              # FastAPI app: 30+ routes, lifespan heartbeat
├── config.py            # 50+ settings from env vars
├── models.py            # Pydantic v2: FloodEvent, IncidentDecision, PlaybookRule, etc.
├── service.py           # FloodOpsService orchestrator: gather → assess → approve → feedback
├── auth.py              # JWT/RBAC: Actor, Role, token creation
├── model/
│   ├── nemotron.py      # NVIDIA Nemotron adapter (prompt injection defenses, retry)
│   └── vllm.py          # vLLM OpenAI-compatible fallback
├── sources/
│   ├── nws.py           # NWS active alerts (api.weather.gov)
│   ├── usgs.py          # USGS instantaneous water observations
│   ├── austin.py        # Austin low-water crossings + road closures
│   ├── austin_floodplain.py  # Austin floodplain GeoJSON
│   ├── lcra.py          # LCRA Hydromet water data
│   └── txdot.py         # TxDOT road conditions
├── streaming/
│   ├── ingest.py        # collect_live() gathers all sources, replay() reads JSONL
│   ├── heartbeat.py     # Autonomous 30s poll with dedup, failure recovery
│   └── kafka.py         # Red Hat Streams/Kafka producer/consumer
├── storage/
│   ├── sqlite.py        # Local SQLite: events, decisions, feedback, memories, audit, resources
│   ├── supabase.py      # Remote Supabase REST adapter
│   └── audit.py         # Append-only audit chain with verification
├── safety/
│   └── policy.py        # Approval gate: reversible + operator-approved only
├── security/
│   └── hiddenlayer.py   # HiddenLayer v2 SDK: six-boundary deep scan
├── learning/
│   ├── reflection.py    # Nemotron extracts PlaybookRule from operator feedback
│   └── memory.py        # Tag-based memory ranking and retrieval
├── evaluation/
│   └── runner.py        # 3-scenario before/after comparison harness
├── simulation/
│   ├── model.py         # threshold-v1 deterministic impact model
│   └── routing.py       # OSRM evacuation detour computation
├── prediction/
│   ├── model.py         # Prediction data models
│   ├── gage_forecast.py # Linear regression gage trajectory
│   └── risk_predictor.py # Risk scoring with memory boost
├── responders/
│   ├── cap.py           # CAP 1.2 XML builder + webhook sender
│   ├── webeoc.py        # WebEOC SOAP AddData adapter; organization contract required
│   ├── after_action.py  # After-action report generator
│   └── foia.py          # Draft records-review CSV and EDXL-DE-shaped exports
└── static/
    └── index.html       # Operations dashboard: map, timeline, learning, security, and approvals

data/replay/
├── east-austin-night-market.jsonl       # Original demo scenario
├── flash-flood-warning-only.jsonl       # 3 NWS warnings (expected: high risk)
├── gage-rise-with-warning.jsonl         # 2 warnings + 3 gage observations (expected: catastrophic)
└── all-clear-scenario.jsonl             # Cancelled warnings + falling gage (expected: low)

tests/                    # Automated tests: heartbeat, evaluation, memory, sources, streaming, service flow, policy, storage, CAP
openshell/                # OpenShell sandbox policy
scripts/                  # demo.sh, smoke.sh
supabase/                 # Schema + migrations
```

## Texas Case Study

Named scenario: "East Austin Night Market opens in 40 minutes; a crossing is becoming unsafe."

Motivated by the catastrophic July 4, 2025 Kerr County/Hill Country flash flood. This prototype demonstrates how approval-gated coordination over public NWS and USGS evidence, plus an unconnected downstream interoperability adapter, could reduce the delay between signal and action.

## License

Built for the AITX Community x NVIDIA Claw Agent Hackathon. See [HACKATHON_PLAN.md](HACKATHON_PLAN.md) for the full decision record.
