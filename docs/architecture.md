# Austin FloodOps Architecture v0.3.0 Enterprise

```
                       +---------------------+
                       |  Public Evidence    |
                       | api.weather.gov     |
                       | waterservices.usgs  |
                       | data.austintexas.gov|
                       +----------+----------+
                                  |
                                  v
+------------+  +------------------+--+  +-------------------+  +------------------+
|  Operator  +->+ HeartbeatEngine   |  |  Austin Sources     |  |  Replay Fixtures |
|  Dashboard |  | 30s polling       +->+ crossings q3y8-2xnm|  |  3 scenarios     |
|  (Leaflet) |  | deduplicate IDs   |  |  road fw5i-n4te     |  +---------+--------+
+-----+------+  +---------+---------+  |  floodplain 3p2e-ps|            |
      |                   |            +-------------------+             |
      |                   v                                                |
      |         +---------+---------+                                      |
      |         |  collect_live_with_status (nws, usgs, austin_crossings,  |
      |         |               austin_roads)                              |
      |         +---------+---------+                                      |
      |                   |                                                |
      |         +---------v---------+                                      |
      +-------->+ Store (SQLite)    +<-------------------------------------+
      |         | filter_new_events |
      |         | save_events       |
      |         | save_decision     |
      |         | heartbeat_state   |
      |         +---------+---------+
      |                   |
      |         +---------v---------+
      |         |  Kafka publish    |
      |         |  (degraded safe)  |
      |         +---------+---------+
      |                   |
      |         +---------v----------------------------------+
      |         |  Memory ranking                            |
      +-------->+  retrieval_context (top 3 active rules)    |
                +---------+----------------------------------+
                          |
            +-------------v----------------+
            |  Nemotron assess_incident    |
            |  NVIDIA hosted               |
            |  fallback -> vLLM            |
            |  OpenAI compat /v1/chat      |
            +-------------+---------------+
                          |
            +-------------v---------------+
            |  Security gate              |
            |  HiddenLayer scan (fail-closed)
            |  OpenShell approval boundary|
            |  Policy evaluate            |
            +-------------+---------------+
                          |
            +-------------v---------------+
            |  FloodOpsService            |
            |  audit_chain optional       |
            |  audit: evidence_ingested,  |
            |  decision_created, blocked, |
            |  approved, rejected, etc    |
            +-------------+---------------+
                          |
        +-----------------+------------------+
        |                 |                  |
   +----v-----+   +-------v------+   +-------v------+
   | Impact   |   | Prediction   |   | Routing      |
   | threshold|   | gage_forecast|   | OSRM detour  |
   | v1       |   | OLS ft/h     |   | haversine FB |
   | depth,   |   | risk_traj    |   | evac routes  |
   | exposure |   | combine alert|   | avoid blocked|
   +----+-----+   +-------+------+   +-------+------+
        |                 |                  |
        +-----------------+------------------+
                          |
            +-------------v---------------+
            |  FastAPI 0.3.0 Enterprise   |
            |  16 integrations health     |
            |  /api/assess,/simulate,     |
            |  /predict,/floodplain,       |
            |  /routing/detour,           |
            |  /audit/recent,{id},verify, |
            |  /after-action/{id},        |
            |  /auth/token,/auth/me,      |
            |  /integrations/vllm,osrm    |
            +-------------+---------------+
                          |
            +-------------v---------------+
            |  Approval Gate / RBAC       |
            |  viewer,operator,supervisor,|
            |  admin,auditor,system       |
            |  JWT pyjwt + role rank      |
            +-------------+---------------+
                          |
        +-----------------+------------------+
        |                 |                  |
   +----v-----+   +-------v------+   +-------v------+
   | CAP 1.2  |   | WebEOC SOAP  |   | AuditChain   |
   | webhook  |   | AddData      |   | SHA256 chain |
   | idempotent|  | idempotent   |   | verify_chain |
   +----------+   +--------------+   +--------------+
```

## Components 16 integrations (health endpoint)

1. Autonomous heartbeat polling NWS + USGS + Austin (30s)
2. NWS alerts weather.gov
3. USGS waterservices
4. NVIDIA Nemotron primary
5. vLLM open-weight fallback OpenAI compat
6. Red Hat Streams / Kafka (Redpanda local)
7. Supabase mirror (SQLite authoritative)
8. NemoClaw/OpenShell sandbox policy v1
9. HiddenLayer runtime security fail-closed
10. First-responder CAP webhook
11. Texas TDEM WebEOC SOAP AddData
12. Austin low-water crossings open data
13. Austin road closures
14. Austin floodplain GeoJSON with synthetic fallback
15. OSRM routing project-osrm.org
16. RBAC/JWT + Audit chain + Prediction ensemble

## Data flow
- Heartbeat gathers live with status, deduplicates via Store.filter_new_events
- Publishes new events to Kafka (degraded safe)
- Ranks memories, builds retrieval_context
- Calls Nemotron, fallback vLLM if unavailable and VLLM_BASE_URL set
- Security: HiddenLayer scan, policy evaluate, OpenShell boundary
- Saves decision, audits decision_created
- Dashboard shows risk, action, impact, map, prediction, routing, audit
- Operator approves/rejects via RBAC-checked endpoints, audit logs
- Delivery to CAP webhook / WebEOC after approval, idempotent, audit logs delivery
- Feedback creates memory, audit logs feedback + memory_created
- Prediction endpoint uses forecast_gage OLS + risk_trajectory + simulate_impact per horizon, audits prediction_generated
- After-action report pulls timeline, metrics, compliance, audit verification, FOIA redacted package, positive narrative

## Security
- OpenShell policy version 1: include_workdir true, filesystem read_only /app/data/replay etc, read_write /app/data /tmp /app/logs, landlock best_effort, process run_as_user sandbox, network public-evidence allow list read-only python binaries
- HiddenLayer optional, fail-closed
- RBAC JWT pyjwt, roles viewer through system, ACTION_ROLES mapping, current_actor returns system when ENABLE_RBAC false for demo
- Approval required, reversible actions, no auto-dispatch

## Audit chain
- SQLite table audit_chain(id, incident_id, prev_hash, hash, event_type, actor_id, actor_role, payload, created_at)
- SHA256(prev_hash+payload+timestamp) tamper-evident
- Events: evidence_ingested, decision_created, security_blocked, assessment_failed, approved, rejected, feedback, memory_created, prediction_generated, delivery, after_action_generated, memory_retired, etc
- verify_chain walks full chain verifying prev_hash linkage and hash recomputation

## Prediction
- GagePoint observed_at, value_ft
- OLS linear regression slope ft/hour from last 20 obs last 12h
- GAGE_THRESHOLDS_FT low5 moderate8 high11 catastrophic13 mapping to 0-1 score
- risk_trajectory combines alert signal (warning 0.9 emergency 1.0) + gage score + synergy 0.1 + memory boost
- predict_future builds PredictionPoint per horizon with impact simulation

## Routing
- RoutePoint lon lat name, EvacuationRoute origin dest distance duration geometry steps method blocked_crossings_avoided
- _osrm_route calls {OSRM_BASE_URL}/route/v1/driving/{lon},{lat};{lon},{lat}?overview=full&geometries=geojson&steps=true
- compute_evacuation_routes loops origins x destinations, tries OSRM, falls back haversine with estimated 10 m/s

## Gov-grade
- Provenance preserved, CAP export, FOIA package, after-action retention declarative
- SQLite local queue remains authoritative if Supabase down
- Kafka degraded safe
- Threshold impact model transparent assumptions

See architecture.svg for visual.
