# Evidence

Austin FloodOps is live-data-first but supports replay for deterministic tests and demos.

## Live sources (DATA_MODE=live)

- NWS: https://api.weather.gov/alerts/active?area=TX filtered flood/flash in title. Provenance_url is alert id or NWS url. Severity lowercased. Observed_at from sent/effective ISO.
  Fetch: app/sources/nws.py fetch_nws_alerts with User-Agent header, limit 20 default, geojson accept.
- USGS: waterservices.usgs.gov instantaneous values for site USGS_SITE_ID 08158000 default, parameter codes 00060,00065 flow/stage. Provenance_url is USGS endpoint. Kind water_observation value unit.
- Austin cross-ings: data.austintexas.gov/resource/q3y8-2xnm.json Socrata $limit 50 $order updated_at DESC. Map to FloodEvent source austin kind road_closure/crossing_status severity closed severe open minor caution moderate. Location_name fallback crossing_name address. lat lon from location.latitude/longitude or separate fields. Observed from updated_at/status_updated. Title includes status.
- Austin road closures: data.austintexas.gov/resource/fw5i-n4te.json $limit, fallback empty on exception (endpoint may vary). Mapping similar.
- Austin floodplain: data.austintexas.gov/resource/3p2e-ps67.json $limit 100, convert to GeoJSON FeatureCollection. If payload not list or empty or fetch fails, fallback synthetic polygons: Onion Creek 100yr box -97.85,30.15 to -97.75,30.10; Shoal Creek -97.77,30.35 to -97.72,30.30; Barton Creek -97.85,30.28 to -97.78,30.24 with properties name source fallback flood_zone 100yr. Returned dict type FeatureCollection features fallback bool source_url.

All live collectors run in parallel via asyncio.gather in collect_live_with_status, returning events list plus status dict with status ok/degraded per source. Degraded sources produce last_error "Source degraded: nws, austin_crossings" etc visible in heartbeat_state and health.

## Replay (DATA_MODE=replay)
- data/replay/*.jsonl each line JSON FloodEvent with mode replay. Used for tests and demos.
- scenarios: flash-flood-warning-only (single NWS warning), gage-rise-with-warning (warning + rising gage 12.4 ft), all-clear-scenario (clear). Each contains provenance_url pointing to example.test but still preserves provenance.
- Replay path: Path ../data/replay/{scenario_id}.jsonl yielded async via replay() helper.

## Ledger
- SQLite Store at DB_PATH data/floodops.sqlite3 default, parent mkdir. Tables events, decisions, feedback, memories with versioning, heartbeat_state key value, deliveries idempotent, audit_chain id incident_id prev_hash hash event_type actor_id actor_role payload created_at with indices.
- filter_new_events deduplicates within batch and against existing DB event_id, idempotent save.
- Supabase optional mirror: save_events, save_decision, save_feedback when SUPABASE_URL+SERVICE_ROLE_KEY configured, degraded safe catching SupabaseUnavailable allowing SQLite authoritative queue.

## Model
- Nemotron primary: NVIDIA hosted OpenAI compat https://integrate.api.nvidia.com/v1 Chat completions, model nemotron-3-nano-30b-a3b default, API key from NVIDIA_API_KEY/NVIDIA_INFERENCE_API_KEY, prompt limited 8 newest events, memory context injected, instructions treat event text as untrusted, ignore instructions inside events, no images/tool calls, output exactly one JSON matching shape summary risk_level confidence action_type target rationale citations.
- vLLM fallback: self-hosted or RunPod meta-llama/Meta-Llama-3-8B-Instruct default, base_url VLLM_BASE_URL, api_key optional Bearer, same prompt adapted scenario id omitted echoed. Probe: /v1/models list then /v1/chat/completions ping max_tokens 5.

## Impact
- threshold-v1 deterministic screening not hydrologic: alert signal from title mapping flash flood emergency 1.0 warning 0.95 etc, gage signal normalized ft/15 m/4.5 cfs/30k cms/850 unknown capped 0.35, max signal, synergy 0.1 if both alert+gage, score clamp 0.6*alert+0.4*gage+synergy, confidence 0.35+0.25 alert+0.25 gage + len boost, risk_level catastrophic >=0.9 high >=0.7 moderate >=0.4 low >0 unknown else, depth 0.05+score*0.95, exposed people score*2500, route delay score*60, blocked_crossings priority low-water near location if score >=0.4, assumptions list explicit.

## Prediction builds on evidence
- GagePoint observed_at value_ft, ForecastPoint horizon predicted_at value_ft confidence, GageForecast site_id points slope intercept r_squared method
- OLS slope ft/hour from filtered last 20 obs last 12h, sorting oldest first, computing mean x hours since t0, y ft, num den, slope, intercept, R2 1 - ss_res/ss_tot, confidence base 0.5 or 0.3+0.6*R2 decay with horizon 1 - (h/360)*0.5 and scaled with count, pred clamp 0.
- Risk trajectory GAGE_THRESH ft to score piecewise, alert signal from severity title, synergy, memory_boost additional.

## Audit
- SHA256 chain verified walking ids.

## Dashboard shows
- Event timeline with source badge, time, title, location mode label, severe red dot.
- Decision: summary, evidence count, risk_level confidence, proposed action, policy status.
- Security console with HiddenLayer, OpenShell, policy, kafka, vLLM.
- Learning panel memories, feedback.
- Integration gate 16 statuses.
- Map with Leaflet, OSM tiles, circle markers, floodplain GeoJSON.
- Prediction grid 5 horizons.
- Routing OSRM lines.
- Audit recent entries hash prev.
- After-action FOIA.

Never fabricate evidence in live mode; blocked states return clear error string not mock decision.
