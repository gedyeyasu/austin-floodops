# Loom Demo Script - Austin FloodOps v0.3.0 Enterprise Gov-Grade (3 min)

## 0:00 - Intro (15s)
"Hello, I'm showing Austin FloodOps Enterprise Gov-Grade - approval-gated live flood-response coordination using official public data, NVIDIA Nemotron with self-hosted vLLM fallback, tamper-evident audit chain, RBAC, prediction, and OSRM routing. Version 0.3.0 with 16 verified integrations, running in Docker + OpenShell sandbox policy v1."

Show health endpoint: `curl /health` - 16 integrations: heartbeat NWS USGS Nemotron vLLM Kafka Supabase OpenShell HiddenLayer CAP WebEOC Austin crossings roads floodplain OSRM RBAC audit prediction.

## 0:15 - Event Timeline + Map (30s)
- Open dashboard http://127.0.0.1:8080
- Click "Inject · gage rise + warning" replay scenario
- Show timeline: NWS Flash Flood Warning severe + USGS gage 12.4 ft
- Map: ensureMap + renderMap - Leaflet shows markers Onion Creek, Shoal Creek. Click marker popup with provenance_url.
- "All evidence preserves provenance_url, no fabrication in live mode, replay labeled replay."

## 0:45 - Decision + Approval Gate + Security (30s)
- Show incident title, risk HIGH/CATASTROPHIC, confidence, proposed action close_crossing_and_reroute
- Approve button disabled until decision exists, policy status approval_required
- Security console: HiddenLayer not_configured or verified, OpenShell enforced, policy approval_required, vLLM not_used or used if fallback.
- Click Approve -> state chip successful-approval green, audit logs approved event with actor_id, actor_role.
- Show CAP export `/api/decisions/{id}/cap` XML.

## 1:15 - Prediction (30s)
- Click "Run prediction (15-180m)"
- Explain JS runPrediction(): calls POST /api/predict with horizons [15,30,60,120,180]
- Show prediction panel: 5 points grid with risk_level, risk_score, gage_ft, confidence, estimated_depth_m, exposed_people
- "Gage forecast uses OLS slope ft/hour from last 20 obs last 12h, risk_trajectory combines alert signal (warning 0.9, emergency 1.0) + gage thresholds low5 moderate8 high11 catastrophic13 + memory boost"
- Show raw forecast slope, intercept, R2, method ols-lastX-12h

## 1:45 - Routing (20s)
- Click "Compute detour"
- JS runRouting(): POST /api/routing/detour with blocked_crossings from events
- Show routing panel: route_id, origin->destination, km, minutes via OSRM or haversine fallback, blocked avoided
- Map draws polyline geojson from OSRM geometry or fallback line
- "OSRM base router.project-osrm.org public, configurable OSRM_BASE_URL for self-hosted"

## 2:05 - Audit Chain + After-Action + RBAC (40s)
- Click "Refresh recent audit"
- Show audit-box: event_type evidence_ingested, decision_created, approved, list hashes prev_hash hash truncated, actor_id sub role
- Explain SHA256(prev_hash+payload+timestamp) tamper-evident
- Click "Verify chain" -> calls /api/audit/verify/{id} returns global verified true, total_entries, errors empty, last_hash
- Click "After-action report" -> POST /api/after-action/{id} generates timeline metrics compliance FOIA package redacted positive narrative
- Show after-action-box metrics evidence_count sources feedback_count memory_count, compliance evidence_cited provenance_preserved approval_gate_enforced audit_chain_verified, positive_change_narrative
- RBAC panel: getTokenAs() quick switch, select role viewer/operator/supervisor/admin/auditor/system, get token via /api/auth/token, setAuthToken stores in localStorage, authHeaders adds Bearer, auth/me shows sub role is_system rbac_enabled. "When ENABLE_RBAC false demo returns system role to avoid friction."

## 2:45 - Integrations Probe + Docker + Close (15s)
- Click Probe vLLM -> POST /api/integrations/vllm/probe probes /v1/models then /v1/chat/completions
- Click Probe OSRM -> POST /api/integrations/osrm/probe
- Show Makefile docker-build docker-run docker-down docker-logs, Dockerfile healthcheck curl /health, docker-compose with Redpanda Kafka-compatible broker for local Red Hat Streams test, .env.example with VLLM JWT_SECRET ENABLE_RBAC OSRM ENABLE_PREDICTION ENABLE_AUDIT_CHAIN
- Show openshell policy v1 include_workdir true read_only read_write landlock run_as_user sandbox network public-evidence allow api.weather.gov waterservices.usgs.gov data.austintexas.gov integrate.api.nvidia.com + router.project-osrm.org read-only python binaries
- "pytest -q still passes 21 tests, audit_chain optional so FloodOpsService(local, Store) 2 args works, pyproject has pyjwt"

End.
