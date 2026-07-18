# Austin FloodOps Enterprise Upgrade Plan v0.3.0

Goal: Gov-grade flood ops with vLLM fallback, RBAC, audit chain, prediction, routing, Austin open data, after-action.

## Tracks addressed
- NemoClaw / OpenShell: sandbox policy with 16 integrations, filesystem include_workdir true, least privilege network
- HiddenLayer: fail-closed scanning for Nemotron + vLLM
- Red Hat Streams/Kafka: local Redpanda compose + SASL_SSL prod config
- Supabase: optional mirror, SQLite authoritative
- NVIDIA: primary Nemotron, vLLM fallback OpenAI-compat probe /v1/models then /v1/chat/completions

## Architecture additions

### Config
- VLLM_BASE_URL, VLLM_MODEL, VLLM_API_KEY, JWT_SECRET, ENABLE_RBAC, OSRM_BASE_URL, ENABLE_PREDICTION, ENABLE_AUDIT_CHAIN
- has_vllm, has_osrm properties

### Auth
- app/auth.py Role = viewer, operator, supervisor, admin, auditor, system
- ROLE_RANK, ACTION_ROLES mapping
- bearer_scheme, _decode_token, current_actor returning system when ENABLE_RBAC false (demo)
- require_role, require_action, create_token via pyjwt

### Model
- app/model/vllm.py VLLMUnavailable, _extract_json resilient, _prompt, assess_incident_vllm, probe_vllm

### Audit
- app/storage/audit.py AuditChain tamper-evident SHA256(prev_hash+payload+timestamp)
- table audit_chain(id, incident_id, prev_hash, hash, event_type, actor_id, actor_role, payload, created_at)
- methods genesis, last_hash, append, list_for_incident, list_recent, verify_chain

### Prediction
- gage_forecast.py: GagePoint, ForecastPoint, GageForecast, _linear_regression OLS slope ft/hour, forecast_gage last 20 obs last 12h
- risk_predictor.py: GAGE_THRESHOLDS_FT low5 moderate8 high11 catastrophic13, _gage_value_to_score, _alert_signal, risk_trajectory combining alert+gage+memory boost
- model.py: PredictionPoint, PredictionResult, predict_future uses forecast_gage + risk_trajectory + simulate_impact per horizon

### Sources
- app/sources/austin.py fetch_austin_crossings limit 50 from data.austintexas.gov q3y8-2xnm, fetch_austin_road_closures fw5i-n4te fallback empty
- app/sources/austin_floodplain.py fetch_floodplain from 3p2e-ps67.json fallback synthetic polygons around Onion, Shoal, Barton creeks

### Routing
- app/simulation/routing.py RoutePoint, EvacuationRoute, _osrm_route calling OSRM router.project-osrm.org with geojson steps, compute_evacuation_routes haversine fallback

### Responders
- after_action.py generate_after_action_report timeline, metrics, compliance, FOIA package, positive_change_narrative

### Service
- audit_chain optional field, __post_init__ init if ENABLE_AUDIT_CHAIN
- create() also wires audit
- _audit helper
- evidence_ingested, decision_created, security_blocked, assessment_failed, approved, rejected, feedback, memory_created, prediction_generated, delivery
- vLLM fallback in assess_events: try Nemotron, if IntegrationUnavailable and has_vllm then try assess_incident_vllm, else return error
- record_delivery and record_prediction audit wrappers
- FloodOpsService(local, Store) with 2 args still works (audit_chain defaults None)

### Main
- version 0.3.0 Enterprise Gov-Grade 16 integrations
- endpoints: POST /api/predict, GET /api/floodplain, POST /api/routing/detour, GET /api/audit/recent, /api/audit/{id}, /api/audit/verify/{id}, POST /api/after-action/{id}, POST /api/auth/token, GET /api/auth/me, POST /api/integrations/vllm/probe, osrm/probe
- auth dependencies using require_action / require_role but system bypass when RBAC false

### Streaming
- heartbeat.py fixed run_cycle returns dict cycles, new_events, sources, consecutive_failures, last_error, decision_outcome, flexible __init__ accepting poll_seconds alias
- ingest.py added austin_crossings + austin_roads parallel tasks, merged into collect_live_with_status with degraded handling

### OpenShell policy
- version 1, filesystem_policy include_workdir true, read_only /app/data/replay /app/app/static /usr /lib, read_write /app/data /tmp /app/logs, landlock best_effort, process run_as_user sandbox, network_policies public-evidence allow api.weather.gov, waterservices.usgs.gov, data.austintexas.gov, router.project-osrm.org, integrate.api.nvidia.com read-only for python binaries

### Static
- index.html expanded with Leaflet map + prediction panel + routing + audit + after-action + RBAC panel + JS functions runPrediction, runRouting, loadFloodplain, refreshAudit, generateAfterAction, setAuthToken, getTokenAs, ensureMap, renderMap, probeVLLM, probeOSRM

### Docker
- Dockerfile, docker-compose.yml with redpanda local, healthcheck, env overrides
- Makefile docker-build, docker-run, docker-down, docker-logs, docker-probe

### Env
- .env.example adds VLLM, JWT_SECRET, ENABLE_RBAC, OSRM, ENABLE_PREDICTION, ENABLE_AUDIT_CHAIN

## Test compatibility
- AuditChain optional so tests using FloodOpsService(settings, Store) with 2 args continue to pass
- No new required env vars; feature toggles default safe
- pyjwt added to pyproject dependencies

## Gov-grade compliance
- Approval-gated, reversible actions
- Tamper-evident audit hash chain verified via /api/audit/verify/{id}
- FOIA-ready after-action report redacts raw_model_response but preserves timeline, metrics, compliance
- Provenance URLs preserved for all evidence
- Fail-closed on HiddenLayer block

## Demo flow update
- Inject replay -> map renders geo events
- Run prediction -> forecast points + risk trajectory + impact per horizon
- Compute detour -> OSRM route or haversine fallback draws polyline
- Approve -> audit logs approved, delivery logs
- Refresh audit -> shows chain
- Verify chain -> SHA256 verification
- After-action -> FOIA package + positive narrative
- RBAC -> get token as viewer/operator/supervisor/admin/auditor/system, set token, call auth/me
- vLLM probe -> shows /v1/models list and chat completion ping
