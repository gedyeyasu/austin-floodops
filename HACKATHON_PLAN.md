<!-- /autoplan restore point: /Users/gedeoneyasu/.gstack/projects/RedHatHackthon/master-autoplan-restore-20260717-182513.md -->
# ClawOps: Self-Improving Live Incident Commander

## Implementation checkpoint: Kafka/OpenShell slice

The current branch has a real optional Kafka producer/consumer in `app/streaming/kafka.py`, an HTTP probe at `/api/integrations/kafka/probe`, and an OpenShell policy artifact at `openshell/austin-floodops.yaml`. Broker errors are converted to a typed degraded state; no broker or sandbox claim is considered verified until the smoke probe fires against the configured service.

Status: GSTACK DEBATE VERDICT — NARROW BEFORE BUILD

## Implementation checkpoint: simulation and responder boundary

The current branch also has a real deterministic `threshold-v1` impact model at
`POST /api/simulate`. It returns severity, screening depth/exposure, route
delay, evidence IDs, and explicit assumptions for live or replay events. This
is decision support, not hydraulic forecasting. Approved decisions can be
exported as CAP 1.2 XML locally; a generic responder webhook sender is
configured separately, requires `confirm=true` plus an `allowed` policy status,
and uses a durable idempotency key. HiddenLayer is a fail-closed adapter whose
tenant-specific Interactions URL must be supplied; it is not represented as
verified while unconfigured. The OpenShell artifact now uses the current
policy-v1 sections (`filesystem_policy`, `landlock`, `process`, and
`network_policies`) and leaves inference credentials provider-managed.

The deployment decision is explicit: Supabase is the managed ledger and
Realtime surface, not the application runtime. The API/agent runs in a
NemoClaw/OpenShell container (Brev is the preferred NVIDIA-hosted path), with
SQLite retained for offline replay. `supabase/schema.sql` is the first
database migration; the Supabase gate stays unverified until one real event
and one decision are written and read back with server-side credentials.
Hackathon: AITX Community x NVIDIA Claw Agent Hackathon, July 17-19, 2026
Primary track: Red Hat Live Data
Secondary qualification targets: Recursive Intelligence, HiddenLayer Runtime Security, Best Use of vLLM, Best Use of NemoClaw + OpenShell, Best Use of Nemotron, Most Commercializable Hack

## One-Line Pitch

ClawOps is an always-on operations agent that watches live public incident feeds, predicts what will need attention next, safely executes a response playbook, and proves that it gets faster and more accurate after every heartbeat.

## Problem and User

Small city operations teams, transit operators, campus safety teams, and event operators monitor several live feeds but lack a 24/7 analyst. Alerts arrive in separate dashboards. Staff manually correlate them, decide severity, find the right playbook, and communicate a response. The delay between signal and action is the product problem.

The initial demo persona is an Austin emergency-operations or event-operations lead responsible for protecting people during a fast-moving flood. The architecture is hazard-agnostic, but the judged demo is intentionally flood-first so the data and response loop are concrete.

## Texas Case-Study Motivation and Government Fit

The human reason for building this is the catastrophic July 4, 2025 Kerr County/Hill Country flash flood. A U.S. Department of Commerce Inspector General review reports that the Guadalupe River rose rapidly, the Hunt gauge rose from about 10 feet around 3:00 a.m. to 37.52 feet at 5:10 a.m., and at least 135 people were reported killed statewide, including 117 in Kerr County as of September 2025. The review also documents the roles of NWS alerts, USGS gauge data, partner coordination, and warning lead time. [Official OIG review](https://www.oig.doc.gov/wp-content/OIGPublications/OIG-26-017-I-SECURED.pdf)

That event is motivation and a retrospective replay source, not a claim that this prototype can predict a river or prove a counterfactual death toll. The product is an approval-gated coordination layer over existing government systems:

- ingest official alerts, gauge observations, crossing status, and partner updates;
- surface one prioritized decision with timestamps, provenance, uncertainty, and a named owner;
- preserve an audit trail for why the recommendation changed;
- let trained officials approve, reject, or retire a playbook rule;
- integrate with existing emergency-management procedures rather than replace NWS, TDEM, USGS, sirens, EAS, or WEA.

Texas policy discussions after the flood explicitly focused on stronger emergency communication, outdoor warning systems, flood gauges, drills, and after-action reports. That makes an auditable coordination and after-action product more credible for government than an autonomous “AI dispatcher.” [Texas Senate flood-preparedness package](https://www.ltgov.texas.gov/2025/08/12/lt-gov-dan-patrick-statement-on-the-texas-senates-unanimous-passage-of-a-disaster-preparedness-and-flood-relief-package/)

### Government adoption path

1. **Pilot:** venue, youth-camp, campus, or county operations team uses replay mode on historical/public data.
2. **Shadow mode:** the agent observes live feeds but only produces recommendations; officials compare it with existing procedures.
3. **Approval mode:** officials can approve reversible internal actions such as closing a crossing or rerouting a shuttle.
4. **After-action mode:** the system measures alert-to-decision time, missed/duplicate escalations, provenance completeness, and operator interventions.
5. **Integration:** only after procurement, security, accessibility, records-retention, and incident-command review should it connect to operational systems.

The demo must say “could reduce coordination delay” or “could help officials act on existing signals sooner,” not “would have prevented the Kerr County deaths.”

## Why the Data Is Realistic

Austin and federal agencies already publish enough public data to build this without inventing a fake sensor network:

- **NWS/NOAA:** free `api.weather.gov` alerts, forecasts, observations, and point/county filters. NWS recommends polling the active-alert service no more often than every 30 seconds.
- **USGS Water Data:** machine-readable real-time streamflow and gage-height measurements through REST APIs.
- **Austin FEWS / ATX Flood Safety:** the City describes a 24/7 Flood Early Warning System with more than 100 rain or creek-level gauges, low-water-crossing gates, cameras, radar rainfall, predictive mapping, and City/LCRA/USGS water-level data. The raw FEWS telemetry endpoint must be verified during implementation, so it is an enhancement rather than the sole dependency.
- **Austin Open Data:** public Socrata/ArcGIS datasets for low-water crossings, floodplain geometry, road conditions, watershed assets, and 311 service requests. The real-time road-condition dataset is updated every five minutes.
- **Transit and mobility:** add a public GTFS-Realtime feed only if the agency endpoint is stable; otherwise use Austin road conditions and 311 as the second live stream.

The first version uses NWS active alerts + USGS/Austin water observations + Austin floodplain/low-water-crossing geometry. A replay fixture guarantees a deterministic demo if a public endpoint is down.

## Multi-Hazard Expansion Model

The product is not a flood predictor. It is a reusable live-hazard response loop with source adapters:

| Hazard | Live/open source adapter | Example action playbook |
|---|---|---|
| Flash flood | NWS alerts + USGS/Austin gauges + crossing status | close crossings, route responders, prioritize shelters |
| Wildfire/smoke | NWS fire-weather alerts + NASA FIRMS active-fire feed + AirNow AQI | issue smoke precautions, stage resources, reroute outdoor events |
| Extreme heat | NWS heat alerts + weather observations + AirNow | open cooling locations, change staffing, notify vulnerable sites |
| Drought | Drought.gov daily indices + USGS streamflow | water-use escalation, conservation communications |
| Earthquake | USGS real-time GeoJSON feed | inspect critical sites, verify roads, start damage checklist |
| Severe storm/tornado | NWS warnings and observations | shelter decision, event pause, accountability checklist |

Only the flood adapter is required for the hackathon. Adding a new hazard should mean adding a normalized event schema and playbook, not rewriting the agent.

## Core Demo Loop (Narrowed Golden Path)

1. A live NWS active-alert feed and one USGS/Austin water observation enter Red Hat Streams for Apache Kafka. Austin crossing geometry is preloaded; GTFS-RT, FEWS raw telemetry, Apify, and extra hazards are optional integrations, not demo dependencies.
2. A heartbeat wakes every 30 seconds and evaluates new events plus unresolved tasks.
3. HiddenLayer scans the verified boundary path (ingested event -> model request/response -> proposed tool call/result); if the SDK supports all five checks, show the full matrix, otherwise label unverified checks rather than faking coverage.
4. Nemotron 3 Nano produces a typed incident assessment through NVIDIA's hosted free endpoint at `https://integrate.api.nvidia.com/v1`. NemoClaw routes the sandbox through OpenShell's `inference.local` path so the NVIDIA inference key stays on the host. Local vLLM is optional and is used only if a real GPU/Brev environment is available.
5. A policy engine proposes one reversible simulated action: close a named low-water crossing and reroute an event shuttle. The operator must approve it.
6. A real OpenShell policy blocks one adversarial exfiltration attempt regardless of model output. NemoClaw is claimed only if the agent is actually launched through it.
7. Supabase stores events, decisions, outcomes, feedback, and episodic memories; Realtime updates the dashboard. Keep pgvector optional until the simple retrieval path is stable.
8. After one operator correction, the agent extracts a versioned playbook rule and retrieves it on replay.
9. The evaluation panel reruns three fixed scenarios first; expand to ten only if the golden path is already reliable. Show run 1 versus current accuracy, latency, and interventions.

## Winning Demo Story

Named scenario: “East Austin Night Market opens in 40 minutes; a crossing is becoming unsafe.” The same multi-signal incident is run twice. On run one, the agent is slow, asks for unnecessary context, and proposes a weak response. The operator corrects it once. On run two, it retrieves the learned playbook, completes the assessment faster, chooses the right reversible shuttle reroute, and cites the lesson it learned. Then an adversarial feed injects instructions to exfiltrate credentials: HiddenLayer flags the content and OpenShell blocks the forbidden network call. The dashboard makes the improvement and containment visible. Say “safer/faster coordination,” never “flood prevention.”

## Proposed Architecture

```text
NWS + USGS/Austin + replay fixture
          |
          v
Red Hat Streams for Apache Kafka
  raw.events -> normalized.events -> incidents
          |                           |
          v                           v
 HiddenLayer scan             Heartbeat orchestrator
                                      |
                           NemoClaw + OpenShell sandbox
                                      |
                 Nemotron via NVIDIA hosted NIM endpoint
                                      |
                        typed decision + proposed action
                                      |
                     policy gate -> execute/approve/refuse
                                      |
                     Supabase Postgres + pgvector memory
                                      |
                       Supabase Realtime -> web dashboard
```

## Sponsor Technology: Why It Is Necessary

- Red Hat Streams for Apache Kafka: live feeds are independent, bursty, replayable event streams. Kafka topics let the demo replay the exact same incident for before/after evaluation without pretending a static file is live.
- HiddenLayer: the agent consumes hostile public data and emits tool calls, so scanning only user prompts is insufficient. Findings become inputs to the action policy.
- NemoClaw + OpenShell: the agent has genuine credentials and tool access. The security boundary lives outside the model and can be adversarially tested.
- Nemotron: performs event correlation, severity reasoning, structured action planning, and memory compression. It is central, not a chat layer.
- NVIDIA hosted NIM/Nemotron: the free `nvidia/nemotron-3-nano-30b-a3b` endpoint is the primary model path. Direct application calls use `NVIDIA_API_KEY`; NemoClaw onboarding uses the provider-specific `NVIDIA_INFERENCE_API_KEY` variable. Keep keys server-side and never put them in the browser bundle.
- vLLM: optional local deployment through NemoClaw/Brev or DGX Spark. Do not claim the vLLM bounty unless `/v1/models` and a real inference request are captured from a vLLM server.
- Supabase: $25 credit funds Postgres, pgvector memory, evaluation history, and Realtime dashboard updates.
- Apify: $50 credit funds resilient polling/scraping of a public incident page when a formal streaming endpoint is unavailable.
- Featherless AI: $25 hosting credit is a fallback hosted open-model endpoint for development and a degraded demo mode if local GPU capacity fails.
- Brev: use the Linktree “Launch NemoClaw on Brev” action if the hackathon account grants access and it reduces setup risk. It is a deployment vehicle, not a reason to block the hosted endpoint path.

## Learning Mechanism

The agent does not retrain a model. Each completed incident produces an episodic record: signals, assessment, chosen action, operator correction, outcome, and security findings. A reflection step extracts a short playbook rule with confidence and provenance. Retrieval ranks rules by incident similarity, outcome score, freshness, and prior usefulness. Rules that hurt results are down-ranked or retired.

The fixed evaluation suite contains at least 10 incident scenarios. Every run records:

- decision accuracy against a rubric;
- time to actionable recommendation;
- number of model/tool calls;
- operator interventions;
- unsafe actions proposed, detected, and blocked;
- citation/provenance completeness.

The headline graph is run 1 versus run N, with raw evidence available for judges.

## Hackathon Resource Map (Verified July 17, 2026)

The [Late Night Hackathon resource page](https://linktr.ee/latenighthackathon) provides the following relevant resources. The links are divided by whether they belong in the judged path or only in setup/support.

| Resource | Use in this project | Status / proof rule |
|---|---|---|
| [NVIDIA Nemotron 3 Nano free endpoint](https://build.nvidia.com/nvidia/nemotron-3-nano-30b-a3b) | Primary incident correlation, structured action planning, and memory reflection | Required. Generate an NVIDIA API key and capture a real `/v1/chat/completions` response. |
| [NemoClaw quick start](https://docs.nvidia.com/nemoclaw/user-guide/openclaw/get-started/quickstart) | Launch the always-on agent and configure hosted NVIDIA inference | Required if claiming NemoClaw. Run onboarding and save status output. |
| [OpenShell quick start](https://docs.nvidia.com/openshell/get-started/quickstart) | Enforce network, filesystem, credential, and action policy | Required if claiming OpenShell. A deny policy must fire during the demo. |
| [NemoClaw documentation](https://docs.nvidia.com/nemoclaw/user-guide/openclaw/home) | Provider validation, `inference.local`, policy, status, and troubleshooting | Required implementation reference. |
| [Launch NemoClaw on Brev](https://brev.nvidia.com/launchable/deploy/now?launchableID=env-3Azt0aYgVNFEuz7opyx3gscmowS) | Real hosted environment if local Docker/GPU access is insufficient | Use when access is granted; do not block on it if hosted Nemotron works. |
| [Build with NVIDIA NIMs](https://build.nvidia.com/) | Confirm model endpoint, API key, and OpenAI-compatible examples | Required for endpoint smoke test. |
| [NVIDIA skills repository](https://github.com/nvidia/skills) | Borrow only a directly relevant agent skill or integration pattern | Optional; no broad skill installation during the critical path. |
| [NemoClaw repository](https://github.com/NVIDIA/NemoClaw) and [OpenShell repository](https://github.com/NVIDIA/OpenShell) | Inspect source, version, examples, and policy syntax | Use for reproducibility and version pinning. |
| Build-a-Claw Assistant / NVIDIA Discord | Setup help and troubleshooting | Support resources, not product dependencies. |

### Credential handling

The direct NVIDIA hosted endpoint uses `NVIDIA_API_KEY`. NemoClaw's NVIDIA Endpoints provider expects `NVIDIA_INFERENCE_API_KEY`; treat these as separate configuration names even if the same issued key is used. Secrets stay on the host or server. They never enter Supabase rows, browser JavaScript, screenshots, Loom video, or Git history.

### Why hosted Nemotron is the right primary path

The hosted free endpoint gives us a real NVIDIA model without pretending that a local GPU or vLLM server exists. NemoClaw documents NVIDIA Endpoints as an OpenAI-compatible provider and routes sandbox traffic through `inference.local` while keeping raw credentials outside the sandbox. A local vLLM deployment remains a valid enhancement, but it is not a dependency and is not claimed for the vLLM bounty unless its server is actually running and logged.

## UI Scope

One desktop-first operations dashboard:

- Live event rail: timestamped weather and transit events with source freshness.
- Incident workspace: current hypothesis, confidence, evidence, action status, and policy decision.
- Learning panel: the exact memory retrieved and whether it helped.
- Improvement chart: accuracy, latency, and interventions across runs.
- Security console: HiddenLayer findings and OpenShell allow/block decisions.
- Demo controls: inject a known scenario, adversarial payload, approve/reject an action, reset to run one.

## Weekend Scope (Engineering Gate)

### Must Work by Code Freeze

- One genuinely live NWS feed plus one water observation, with a recorded replay fixture.
- One Kafka topic and a normalized event stream; add topic fan-out only after the golden path works.
- Heartbeat loop with persistent task state and interruption recovery.
- Nemotron structured incident assessment through the verified NVIDIA hosted endpoint, using `nvidia/nemotron-3-nano-30b-a3b`. A local vLLM/NIM deployment is a stretch path only when the Brev/DGX/GPU preflight is green.
- One real HiddenLayer path with evidence for each boundary actually scanned; never imply mocked coverage is real.
- One real OpenShell YAML policy with a judge-testable blocked action; claim NemoClaw only when its launch path is verified.
- Supabase persistence and a simple retrieval path; add pgvector/RealtIme only after the core works.
- Operator correction -> memory extraction -> measurable second-run improvement.
- Three-scenario evaluation harness and before/after chart; ten scenarios are stretch scope.
- One polished dashboard and one rehearsed 3.5-minute Loom demo.
- Public repository and complete README/submission materials.

### Explicitly Not in the Hackathon Build

- Production emergency dispatch or automated messages to the public.
- Multi-tenant billing, enterprise SSO, or a full workflow builder.
- Model fine-tuning.
- More than two live data sources unless the core loop is already stable.
- A broad multi-hazard dashboard in the judged demo.
- Production claims such as flood prevention, autonomous dispatch, or public messaging.

## Failure and Safety Posture

- Feed unavailable: mark source stale, consume the other feed, and offer deterministic replay.
- Kafka unavailable: buffer locally with visible degraded status; never label buffered data as live.
- Model timeout/malformed JSON/refusal: bounded retry, schema repair once, then operator escalation.
- HiddenLayer unavailable: fail closed for tool execution; dashboard can continue read-only.
- Supabase unavailable: append to a local durable queue and show sync pending.
- Memory retrieval produces a harmful rule: compare against no-memory baseline and permit operator retirement.
- Prompt injection: quarantine the event, show the finding, and prevent it from entering memory.
- Forbidden tool call: OpenShell blocks it regardless of model intent and logs the policy rule.

## Build Sequence

1. Lock data feeds, schemas, replay fixtures, and evaluation rubric.
2. Build Kafka ingestion and event normalizer.
3. Build heartbeat state machine and typed Nemotron call.
4. Add Supabase event/incident/memory/evaluation schema.
5. Add HiddenLayer boundary wrapper and OpenShell policy.
6. Build operator correction and reflection/retrieval loop.
7. Build dashboard from recorded data, then connect Realtime.
8. Run evaluation suite, tune prompts/retrieval, and capture baseline/current metrics.
9. Adversarially test security and degraded modes.
10. Freeze features, rehearse demo, record Loom, and finish submission assets.

## First 2–4 Hour Integration Gate

Before building UI breadth, verify these judge-facing facts in order: (G1) a real Red Hat Streams/Kafka event can be produced and consumed; (G2) a hosted NVIDIA Nemotron call through NemoClaw/OpenShell returns typed JSON; (G3) an OpenShell policy actually denies an exfiltration attempt; (G4) NWS/USGS freshness changes a recommendation; and (G5) one Supabase evidence row can be written and read. If a gate fails, stop claiming that component and pivot immediately: use replay/local Kafka, a clearly labeled model fallback, an application policy gate, local persistence, or—if genuine streaming is impossible—make Recursive Intelligence the primary track. Never leave a simulated sponsor badge in the demo.

## Success Criteria

- Core workflow completes three consecutive times without manual repair.
- At least 20% improvement on the defined composite score from run 1 to run N.
- A poisoned event is detected before model/tool execution and cannot create persistent memory.
- A forbidden exfiltration attempt is blocked by OpenShell policy.
- Live-feed freshness is visible and changes the recommended action.
- A judge can understand the architecture, learning delta, and containment story in under 90 seconds.
- A new developer can reproduce the recorded demo from the public README.

## Submission Requirements Captured

- Due July 19, 2026 at 11:00 AM CST.
- Select one primary track.
- Loom video, 2-5 minutes, camera on, showing the core loop live.
- Public repository.
- README with quick start, stack and architecture diagram, demo reproduction, env vars/sample `.env`, data provenance, known limitations, and next steps.
- Deployed URL or short working-app capture.
- Team roster and 150-300 word problem/user/solution/impact write-up.

## Open Premises for CEO Review

- A narrow event-operations wedge will score higher than a generic incident-management platform.
- Demonstrating first-run versus later-run improvement is more persuasive than claiming a learning mechanism.
- The build should optimize for one flawless 3.5-minute story, while the architecture proves technical depth.
- It is better to use every sponsor technology in one causal pipeline than to add unrelated sponsor integrations.
- Real external actions should remain simulated or approval-gated during the hackathon.

## GSTACK Multi-Agent Debate Verdict

Three adversarial reviewers independently judged the proposal (strategy/judge, principal engineering, and demo/DX). Their shared conclusion is that the idea is a strong contender only after a vertical-slice cut.

| Question | Debate result |
|---|---|
| Primary track | **Red Hat Live Data**. The stream must be visibly live, timestamped, and causally change the crossing recommendation. |
| Secondary track | **Recursive Intelligence**, if the operator correction changes a versioned rule and the replay shows a measured run-1 -> run-N improvement. |
| Security track | Treat HiddenLayer Runtime Security as a target only when the actual scan path and finding-to-policy gate are visible; otherwise do not claim it. |
| Bounties | NemoClaw + OpenShell and Nemotron are plausible; vLLM is high-risk unless a real endpoint is running. Supabase, Apify, and Featherless credits are enabling resources, not reasons to add scope. |
| Current plan score | Roughly **55–68/100** because the stack is too broad to verify. |
| Narrowed plan score | Roughly **82–90/100** if one golden path is flawless, evidence-backed, and reproducible. |
| Win/feature verdict | **Not a guaranteed overall winner.** As written, low ship confidence; narrowed and polished, a credible track-winner/finalist and feature candidate. |

### The debate's strongest objection

“Generic incident dashboard with sponsor logos” is the failure mode. Judges must see why Kafka, Nemotron, the security boundary, and the learning loop each change the outcome. A static replay presented as live data, cosmetic memory retrieval, or mocked sponsor panels will lower the score more than omitting a non-working integration.

### Decision and non-negotiable cuts

Build **Austin FloodOps**, a decision-support and containment demo for venue/transit operations—not a flood predictor or emergency dispatch system. Show one named crossing, one reversible action, one operator correction, one replay improvement chart, and one blocked hostile feed. Keep other hazards as an adapter roadmap. Use LIVE and REPLAY labels, source timestamps, provenance, and a deterministic `make demo` path in the README.

### Judge-facing 3:30 story

0:00 stakes and KPI; 0:20 live/replay NWS + gauge signals on Kafka and map; 0:55 typed recommendation with three citations and approval gate; 1:25 operator correction; 2:05 replay with faster/correct action and retrieved rule; 2:45 hostile event quarantined and exfiltration blocked; 3:15 Austin-first, hazard-adapter roadmap and reproducible repo.

## GSTACK REVIEW REPORT

### Plan summary

This plan builds a real, approval-gated Austin flood-response decision-support vertical slice. It uses public NWS and USGS/Austin observations, an actual event broker, a real structured model endpoint, persistent evidence, one real security denial, and a measurable operator-feedback loop. It deliberately refuses to claim any sponsor integration that does not pass a live smoke test.

### CEO premise challenge

| Premise | Assessment | Decision |
|---|---|---|
| Public data is sufficient for a credible live demo | Confirmed: NWS, USGS, and Austin publish usable alert, gauge, crossing, and provenance data | Accept |
| A generic all-hazards platform is the best product story | Rejected: it dilutes the causal demo and resembles existing incident suites | Use Austin FloodOps as the wedge; keep adapters in the roadmap |
| “Self-improving” means model retraining | Rejected: retraining is unnecessary and unverifiable in a weekend | Use versioned human-feedback memory with before/after evaluation |
| Every sponsor integration can be made real from an empty repo | Unconfirmed and a feasibility risk; credentials, clusters, SDKs, and GPU access may be absent | Gate each dependency; remove unsupported claims |
| Autonomous emergency dispatch is appropriate | Rejected on safety and liability grounds | Simulate one reversible action and require approval |

### What already exists

The repository is a greenfield, empty Git repository. There is no application code, dependency manifest, deployment configuration, test suite, or design system to reuse. The existing asset is this plan and its source research. Therefore the build must start with a thin vertical slice, not an integration-heavy platform scaffold.

### Dream-state delta

```text
CURRENT: empty repo + validated public-data research
   |
   v
THIS PLAN: Austin FloodOps, one real live path, evidence logs, replay learning,
           approval-gated action, reproducible README and deployed demo
   |
   v
12-MONTH IDEAL: feed-agnostic operations copilot for venues, campuses, and transit;
                many hazard adapters, tenant controls, calibrated outcomes, audit APIs,
                and production integrations with existing city systems
```

### Implementation alternatives

| Approach | Human effort | Risk | Result | Decision |
|---|---:|---|---|---|
| Full original stack: many feeds, five security boundaries, ten scenarios, broad UI | 46–80 hours | High integration and demo failure risk | Wide architecture, shallow proof | Reject |
| Narrow Austin FloodOps golden path with live gates and honest fallbacks | 20–36 hours after access setup | Medium; bounded by dependency gates | One complete, judge-verifiable product loop | **Choose** |
| Recursive Intelligence first with replay data and minimal live streaming | 12–24 hours | Low runtime risk, weaker Red Hat track fit | Strong learning proof, weaker live-data story | Hold as fallback only |

### Error & Rescue Registry

| Error | Detection | User-visible response | Rescue |
|---|---|---|---|
| Kafka/Red Hat broker unavailable | startup health check and publish/consume probe | “Streaming unavailable”; no LIVE badge | use fixture replay, disclose fallback, remove Red Hat claim if no genuine stream |
| NWS/USGS request fails or is stale | HTTP status, source timestamp, freshness threshold | stale chip and last-observed time | exponential backoff, cached official payload, clearly labeled REPLAY |
| Model endpoint unavailable or malformed | health check, timeout, JSON schema validation | decision unavailable; approval disabled | bounded retry, then fixture decision only for local tests; never claim a live model call |
| HiddenLayer scan fails | API response and timeout | security status unknown; action blocked | fail closed and show read-only incident; remove security bounty claim if unverified |
| OpenShell policy does not fire | adversarial smoke test | security check fails; action disabled | app-level deny for safety only, and omit NemoClaw/OpenShell bounty claim |
| Supabase unavailable | write/read health check | persistence pending badge | local append-only evidence queue, with sync status; no Realtime claim |
| Unsafe or malformed action | typed action schema and policy validation | approval button disabled | quarantine and require operator review |
| Harmful learned rule | replay against no-memory baseline | rule marked harmful and not retrieved | retire rule, preserve audit record, rerun benchmark |

### Failure Modes Registry

| Failure mode | Severity | Prevention/test | Shipping rule |
|---|---|---|---|
| Replay payload mislabeled as live | P0 | LIVE/REPLAY state is part of every event and screenshot | never ship ambiguous freshness |
| Sponsor panel is mocked | P0 | evidence matrix links every claim to a request and log | omit the panel/bounty claim |
| Learning is a hardcoded prompt | P0 | delete memory and compare baseline/current runs | no Recursive claim without a changed versioned rule |
| Model proposes public dispatch | P0 | typed action allowlist and approval gate | simulated crossing closure only |
| Poisoned feed enters memory | P0 | scan before model and before memory write | quarantine and record finding |
| One public API rate-limits the demo | P1 | cache, backoff, fixture, freshness indicator | keep second source and replay path working |
| UI hides why an action was chosen | P1 | three citations, timestamps, confidence, policy trace | no approval control without evidence |
| Credentials leak into logs or client bundle | P0 | server-only secrets, redaction tests, OpenShell boundary | block release until secret scan is clean |

### Phase 1: CEO review completion

Mode: **SELECTIVE EXPANSION**. The plan expands only within the Austin response-support wedge and defers unrelated platform breadth. Strategy review found one high-confidence correction: the product must be positioned as response coordination, not flood prevention. The primary track is Red Hat Live Data; Recursive Intelligence is a measured secondary; security and sponsor bounties are conditional on proof.

CEO voices from the prior multi-agent review agreed on the following consensus:

| Dimension | Strategy judge | Engineering judge | Consensus |
|---|---|---|---|
| Premises valid | public feeds and flood wedge valid | sponsor access unconfirmed | valid with access gate |
| Right problem | concrete operations delay | generic incident platform risk | right only when narrowed |
| Scope | broad plan too large | 46–80 hours from empty repo | cut to golden path |
| Alternatives | hazard breadth is roadmap | Recursive-first is fallback | choose narrow live path |
| Market risk | incumbents exist | liability risk | sell to venue/transit operators |
| 6-month trajectory | adapters can expand later | avoid premature platform work | sound if evidence-first |

Phase 1 complete. Premises are accepted only with the dependency gate and safety boundary above.

### Phase 2: Design review

UI scope is present. Design completeness before this review: **5/10**. The plan now specifies the primary reading order, states, and proof points.

| Dimension | Score | Decision |
|---|---:|---|
| Information hierarchy | 9/10 | stakes/KPI first, then map, then decision evidence |
| User journey | 9/10 | signal → recommendation → approval → correction → improvement |
| State coverage | 8/10 | loading, stale, replay, blocked, unavailable, and approval states required |
| Specificity | 9/10 | one named crossing, one action, one metric |
| Accessibility | 7/10 | keyboard approval, color-independent status labels, readable contrast |
| Responsive behavior | 7/10 | desktop-first; narrow view stacks timeline above map |
| Featureability | 9/10 | visible counterfactual and blocked attack create a clear story |

Required screen order:

```text
Top bar: LIVE/REPLAY + freshness + run score
     |
Event rail: source, timestamp, payload provenance
     |
Map + incident card: named crossing, risk, one proposed action
     |
Decision trace: citations, confidence, policy result, Approve/Reject
     |
Learning/security panel: correction, retrieved rule, before/after, quarantine log
```

Required states: loading, no incidents, stale source, replay mode, model error, blocked action, pending approval, successful approval, rejected action, quarantined payload, and retired memory. No state may silently look successful.

Phase 2 complete. The design is intentionally narrow; multi-hazard screens and sponsor logo walls are deferred.

### Phase 3: Engineering review

#### Dependency graph

```text
NWS alerts + USGS/Austin gauge
             |
             v
       source adapters + freshness
             |
             v
   Red Hat Streams/Kafka raw topic
             |
             v
       normalizer + heartbeat
          |            |
          |            +--> HiddenLayer scan: input/request/response/tool/result
          v                         |
   Nemotron via NVIDIA hosted NIM  v
          |                  quarantine or allow
          v                         |
 typed incident + proposed action   v
             |                 OpenShell policy deny/allow
             v                         |
        approval gate <---------------+
             |
             v
 Supabase evidence + versioned memory + Realtime dashboard
```

#### Engineering decisions

- One Kafka topic and one normalized stream first. Add raw/normalized/incident fan-out only after the producer/consumer probe passes.
- One typed model call first. Add concurrency/throughput measurement only after structured output is stable.
- One OpenShell deny policy first. Do not claim broad sandbox coverage until the actual policy fires.
- Simple retrieval first. pgvector is an optimization, not a prerequisite for the learning proof.
- All actions are simulations behind approval. No public notification or dispatch integration.

#### Test diagram

| Flow/codepath | Required test | Pass evidence |
|---|---|---|
| NWS/USGS fetch | contract test with fixture + live smoke test | schema, timestamp, freshness |
| Kafka publish/consume | integration test | event ID arrives once and is normalized |
| Heartbeat | fake-clock test | no duplicate processing; stale task resumes |
| Model call | schema/timeout/retry test | typed JSON or explicit unavailable state |
| Action policy | allow/deny matrix | crossing action requires approval; exfiltration denied |
| HiddenLayer boundary | poisoned fixture test | finding prevents action and memory write |
| Memory learning | baseline → correction → replay | version changes and metric improves |
| Supabase persistence | write/read/reconnect test | evidence survives reload |
| Dashboard states | browser smoke test | every required state is visible and labeled |
| Secrets | static scan + runtime redaction | no credentials in logs or client bundle |
| Demo reproducibility | clean-environment run | README path works without manual repair |

#### Engineering completion summary

The plan is executable from an empty repo only after access setup. The first 2–4 hours are a hard gate. Expected engineering score is high only when logs prove the broker, model, policy, security scan, and persistence; otherwise the plan must honestly narrow its claims.

Phase 3 complete. The architecture is explicit, the test paths are enumerated, and the no-mock rule is enforced by the evidence matrix and gate.

### Phase 3.5: Developer-experience review

Product type: an operations dashboard plus a reproducible developer demo. Initial DX completeness: **3/10** because the repository is empty. Target time-to-first-hello-world (TTHW): **under 10 minutes for replay mode**, with live integrations added through a preflight command.

#### Developer journey map

| Stage | Developer need | Plan requirement |
|---|---|---|
| 1. Discover | understand the product quickly | README one-sentence pitch + 90-second GIF |
| 2. Install | know prerequisites | versioned runtime list and preflight script |
| 3. Configure | avoid secret guessing | `.env.example`, server-only secret table |
| 4. Start replay | see value without credentials | `make demo` or equivalent deterministic command |
| 5. Connect live feeds | verify access | `make preflight` with per-dependency status |
| 6. Run incident | understand controls | scenario seed and reset command |
| 7. Inspect evidence | trust output | event IDs, timestamps, citations, policy logs |
| 8. Test failure | learn recovery | stale/offline/poisoned fixtures and expected output |
| 9. Extend | add a hazard adapter | normalized schema and playbook template |

#### Developer empathy narrative

“I clone the repo and want to see the product before hunting for five credentials. Replay mode should work first. If live mode fails, I need the preflight output to say which dependency is missing, why it matters, and how to fix it. I should be able to reproduce the judge’s exact scenario, inspect the event provenance, and tell which sponsor integrations are verified rather than trusting a badge.”

#### DX scorecard

| Dimension | Score now | Target |
|---|---:|---:|
| Time to hello world | 3/10 | 9/10, under 10 minutes in replay |
| Error messages | 2/10 | 8/10, problem/cause/fix in every preflight result |
| Configuration | 3/10 | 8/10, sample env and clear secret ownership |
| API/command naming | 4/10 | 8/10, `demo`, `preflight`, `reset`, `evaluate` |
| Documentation | 3/10 | 9/10, copy-paste quick start plus architecture |
| Testability | 3/10 | 8/10, fixtures for every failure mode |
| Upgrade path | 4/10 | 7/10, pinned versions and migration notes |
| Escape hatches | 4/10 | 8/10, switch live/replay and provider via config |

#### DX implementation checklist

- Add `README.md`, `.env.example`, and a dependency preflight command.
- Make replay mode work without external credentials.
- Make every live integration opt-in and report verified/unverified status.
- Include sample payloads, data provenance, rate-limit behavior, and reset instructions.
- Document how to reproduce the Loom scenario and how to run the test matrix.
- Add a provider interface so a failed sponsor endpoint cannot force a code rewrite.

Phase 3.5 complete. The developer path is part of the product: judges and contributors must be able to reproduce the evidence without guessing.

### Cross-phase themes

1. **Evidence over breadth** appeared in strategy, design, and engineering: one verified causal path beats a catalog of integrations.
2. **Honest state labeling** appeared in design, engineering, and DX: LIVE, REPLAY, stale, blocked, and unverified must be explicit.
3. **Approval-gated safety** appeared in CEO and engineering review: this is decision support, not autonomous dispatch.
4. **Human-feedback learning** appeared in strategy and design: the correction must visibly change the next run.

### Deferred to TODOS.md

- Add GTFS-RT and raw FEWS telemetry only after the flood path is stable.
- Add wildfire, heat, drought, earthquake, and smoke adapters after the hackathon.
- Add ten-scenario evaluation only after three scenarios pass repeatedly.
- Add multi-tenant auth, production dispatch, audit API, and enterprise deployment later.
- Add pgvector, Realtime polish, Apify, Featherless, and Brev only when the core evidence is already green.

### Decision Audit Trail

| # | Phase | Decision | Classification | Principle | Rationale | Rejected |
|---:|---|---|---|---|---|---|
| 1 | CEO | Choose Red Hat Live Data as primary | Mechanical | Explicit over clever | Live public feeds and Kafka make the causal story visible | Generic all-hazards primary |
| 2 | CEO | Narrow to Austin FloodOps | User challenge resolved | Pragmatic | Named user, place, action, and metric are easier to judge | Broad incident platform |
| 3 | CEO | Keep Recursive Intelligence secondary | Mechanical | Completeness | Feedback loop adds distinct proof without changing the wedge | Cosmetic “AI learns” claim |
| 4 | CEO | Gate every sponsor integration | Mechanical | Explicit over clever | No credentials or SDK should be hidden behind a mock | Sponsor bingo |
| 5 | Design | Put stakes and map before architecture | Mechanical | User outcome first | Judges understand the decision before the stack | Architecture-first Loom |
| 6 | Design | Make LIVE/REPLAY and stale states explicit | Mechanical | Completeness | Prevents a credibility failure | Silent fallback |
| 7 | Engineering | One action and one policy denial | Mechanical | Pragmatic | Smallest complete safety proof | Multi-action dispatch |
| 8 | Engineering | Three evaluation scenarios first | Taste decision | Boil lakes | More scenarios only after the evidence path works | Ten scenarios as a prerequisite |
| 9 | DX | Replay works without credentials | Mechanical | Bias toward action | Developers get a working result before setup friction | Live-only first run |
| 10 | DX | Omit unsupported bounty claims | Mechanical | Explicit over clever | Honest omission scores better than a mocked integration | Unverified sponsor panel |

### Final plan status

**DONE_WITH_CONCERNS.** The plan is complete and executable as a real vertical slice. It is not a promise that unavailable third-party credentials will appear. The build begins with the dependency gate, and every failed gate causes an honest scope/track adjustment instead of a mock.
