# Austin FloodOps: four-minute Loom recording script

This is the final presenter script for a two-to-five-minute hackathon video.
The target length is about four minutes and twenty seconds. Keep the camera
bubble on, speak conversationally, and leave the cursor beside the evidence you
are describing.

## Before recording

1. Open the public application:
   <https://austin-floodops-gedeon-tona-us-dev.apps.rm1.0a51.p1.openshiftapps.com>.
2. Use a desktop browser around 1440 by 900 pixels at 80 or 90 percent zoom.
3. Sign in with `gedeon@aitx.com` and paste the demo password from the secure
   note. Never say or show the password, token, or secure note.
4. Confirm the signed-in role is `supervisor`, the heartbeat is running, and
   NVIDIA Nemotron, HiddenLayer, the Kafka-compatible stream, Supabase,
   OpenShift, routing, role permissions, and the audit chain are available.
5. Click **Reset view to run 1** before recording. Close unrelated tabs and
   notifications.

## Know the page before you record

The dashboard has three columns that scroll independently:

- **Left column:** live event timeline, replay controls, adversarial test, and
  operator login.
- **Center column:** decision, risk, evidence, map, prediction, routing, audit,
  learning evaluation, WebEOC preview, resources, Texas data, and offline mode.
- **Right column:** source health, HiddenLayer and OpenShell status, learning
  memory, sponsor integration gate, routing probe, and role information.

The header and state strip remain at the top. When this script says “scroll the
center” or “scroll the right column,” keep the pointer inside that specific
column while scrolling.

## 0:00–0:35 — Motivation and problem

**Show:** Keep all three columns at the top. Point first to **Austin FloodOps**
and the live heartbeat, then to the official events in the left timeline.

**Say:**

> Austin FloodOps is flood decision support for Texas. It is motivated by the
> July fourth, 2025 Hill Country flood, which killed at least 135 people across
> Central Texas, and by this week's severe flooding and crossing closures in San
> Antonio. Flooding is water covering land that is normally dry; fast runoff can
> make a low-water crossing dangerous within minutes. This product cannot stop
> rain or claim it would have prevented a specific death. It helps an official
> move faster from fragmented evidence to one cited, reversible recommendation.

## 0:35–1:00 — Prove the live-data heartbeat

**Show:** Point to **LIVE · 30s poll** in the header. In the left timeline,
point to one National Weather Service alert and one United States Geological
Survey gage observation. In the right **Security console**, point to one green
source and one degraded optional source.

**Say:**

> Every thirty seconds the agent checks real public feeds from the National
> Weather Service, the United States Geological Survey, and Austin. It keeps the
> source time, removes duplicates, and reacts when evidence changes. This is the
> Red Hat Live Data track: freshness changes the decision. Optional sources stay
> visibly degraded when unavailable; the system never replaces them with fake
> live records.

## 1:00–1:35 — Explain the application and sponsor stack

**Show:** Scroll only the right column to **Integration gate (18)**. Point to
NVIDIA Nemotron, Kafka-compatible stream, Supabase, HiddenLayer, Open Source
Routing Machine, and role-based access control. Keep the OpenShift application
address visible in the browser.

**Say:**

> The interface is HTML, CSS, and JavaScript with Leaflet and OpenStreetMap. A
> Python FastAPI backend validates typed data with Pydantic. Red Hat OpenShift
> hosts the application and Redpanda, which implements the Apache Kafka
> streaming protocol. SQLite is the durable operational ledger, and Supabase
> mirrors records into hosted PostgreSQL. NVIDIA Nemotron 3 Nano creates the
> cited recommendation through NVIDIA's hosted inference service. HiddenLayer
> scans six trust boundaries, and the Open Source Routing Machine computes
> detours around blocked crossings.

## 1:35–2:15 — Run the judged incident end to end

**Show:** Return the right column to **Security console**. In the left column,
click **Inject · gage rise + warning**. Wait for the result. Point to **Replay
mode**, the warning and gage evidence, the center risk and confidence, grounded
citations, proposed action, and **Pending approval**.

**Say:**

> I am using a clearly labeled replay so every judge sees the same incident,
> not fake current weather. The evidence still crosses the real Kafka
> publish-consume-assess loop. HiddenLayer scans inputs, memory, model traffic,
> and outputs. NVIDIA Nemotron must call one typed decision function, and each
> citation must exactly match evidence supplied to the model. A mismatch fails
> closed. The result is a risk level, confidence, cited explanation, and a
> reversible action that still requires a human supervisor.

## 2:15–2:40 — Show prediction, impact, and routing honestly

**Show:** While the center is at the top, click **Run prediction (15–180m)** and
**Compute detour**. Then scroll only the center column to **Ops map**,
**Prediction panel**, and **Routing**.

**Say:**

> The prediction is a transparent simulation, not an official hydraulic flood
> forecast. It projects the recent gage trend across the selected time horizon
> and converts that trajectory into illustrative risk and impact. A production
> forecast would need calibrated terrain, drainage, rainfall, and uncertainty.
> Routing separately uses the Open Source Routing Machine to propose a detour
> around a blocked crossing.

## 2:40–3:00 — Prove human authority and auditability

**Show:** Scroll the center back to the decision and click **Approve reversible
action**. Point to **Approved**. Scroll the center to **Audit chain**, click
**Refresh recent audit**, then **Verify chain**.

**Say:**

> The model cannot approve itself, and approval does not dispatch anything. A
> signed-in supervisor changes only the local policy state. The audit ledger
> records the actor, decision, and previous record hash, making later edits
> detectable. Any external handoff remains a separate, confirmed action.

## 3:00–3:30 — Explain WebEOC and the future responder handoff

**Show:** Scroll the center to **WebEOC Message Export Prototype**. Click
**Preview CAP + SOAP Message**. Point to **CAP 1.2 XML Test Preview**, **SOAP
AddData Envelope Preview**, and the disabled **Attempt Configured WebEOC
Delivery** button. Do not check the confirmation box or attempt delivery.

**Say:**

> WebEOC is incident-coordination software used by emergency organizations.
> This build is not connected to or authorized by a government agency. It
> creates a test Common Alerting Protocol message and wraps it in a Simple
> Object Access Protocol AddData preview. In an agency pilot, the organization
> would supply its endpoint, credentials, board, and schema. Only after human
> approval and a second explicit confirmation could an idempotent delivery post
> the message to an authorized board used by emergency managers and first
> responders.

## 3:30–3:55 — Show learning and the security boundary

**Show:** Click the fixed-header **Run learning evaluation** button, then scroll
the center to **Recursive improvement** and **Evaluation trace**. Next, click
**Run adversarial payload** in the left column and point to **Quarantined** and
the HiddenLayer result in the right **Security console**.

**Say:**

> Operator corrections become versioned, reviewable playbook rules and can be
> retired; they do not silently retrain the base model. The controlled chart
> shows whether retrieval changes later decisions. HiddenLayer also quarantines
> the adversarial prompt instead of letting it reach an action. The separate
> NemoClaw and OpenShell proof in the repository blocks undeclared network
> access; the public page honestly shows that sandbox is not configured around
> this OpenShift pod.

## 3:55–4:20 — Close on impact and credibility

**Show:** Click **Reset view to run 1**. Return the center and right columns to
the top. End with the live heartbeat, official event timeline, cited decision,
and human-approval controls visible.

**Say:**

> Austin FloodOps does not replace the National Weather Service, incident
> command, or first responders. It shortens the path from fresh public evidence
> to a secure, cited, human-reviewed decision and preserves why that decision
> changed. The same pattern can support wildfire, heat, tornado, and other
> fast-moving hazards. The next step is an agency-sponsored shadow pilot with
> calibrated hydrology, authorized WebEOC testing, and field validation.

## Exact claims for sponsor tools

| Tool or platform | What is real in this build | What to show |
|---|---|---|
| Red Hat OpenShift | Hosts the deployed application and its internal Redpanda broker | Public OpenShift address, heartbeat, and Kafka status |
| Red Hat Live Data track | Live public feeds refresh every 30 seconds and materially change assessments | Heartbeat, source timestamps, deduplication, and degraded-source honesty |
| NVIDIA Nemotron 3 Nano | Hosted model produces the typed, grounded flood recommendation | Model name, risk, confidence, citations, and proposed action |
| HiddenLayer | Scans three boundaries before inference and three after; adversarial input is quarantined | Security console and adversarial test |
| Supabase | Mirrors the operational record into hosted PostgreSQL; SQLite remains authoritative | Verified Supabase row in the integration gate |
| NemoClaw and OpenShell | Separate checked-in sandbox proof enforces a reversible-action and network boundary | Mention the repository proof; do not claim it surrounds the public pod |
| WebEOC adapter | Generates test Common Alerting Protocol XML and a Simple Object Access Protocol AddData preview | Preview panel; never claim an agency connection or click delivery |

Do not say the project uses the retired Red Hat Streams service. It uses a real
Kafka-compatible Redpanda broker running on Red Hat OpenShift, which satisfies
the track because live streaming data performs meaningful work in the loop.

## Motivation sources for the presenter

- The [Texas House report on the July 4, 2025 Camp Mystic and Hill Country flood](https://www.house.texas.gov/pdfs/committees/355/Report-on-the-Camp-Mystic-Flood-Disaster-of-July-4-2025.pdf) reports at least 135 deaths across Central Texas, 117 deaths in Kerr County including 37 children, and the Guadalupe River at Hunt rising from about 10 feet around 3:00 a.m. to a 37.52-foot crest at 5:10 a.m.
- The [City of San Antonio's July 15, 2026 severe-weather update](https://www.sa.gov/Directory/News-Releases/City-Responds-to-Tornado-and-Severe-Weather) reports significant storm damage, 20 barricaded low-water crossings, cleanup and damage assessment, and no reported injuries.
- The [National Weather Service Austin and San Antonio preliminary storm report](https://forecast.weather.gov/product.php?format=CI&glossary=1&issuedby=EWX&product=LSR&site=SJT&version=1) records flash flooding around Leon Valley and numerous flooded low-water crossings on the northwest side of San Antonio.

These sources support the motivation, not a counterfactual claim. Never say that
Austin FloodOps would have prevented a specific death or disaster. Say it is
designed to reduce the coordination delay between existing warning evidence and
a reviewed protective action.

## Recording recovery plan

- If a live public source fails, keep recording and explain the visible degraded state. Do not rerun until it looks green.
- If NVIDIA or HiddenLayer fails, stop the recording, verify `/health`, and record again. Do not substitute a fixture decision or edit around a failed integration.
- If the replay is slow, say the request is crossing Kafka, six security scans, and hosted NVIDIA inference. Do not fill the pause with an unsupported claim.
- If the learning chart is already populated, say it is the latest controlled evaluation and click the button only if time permits.
- Never click **Attempt Configured WebEOC Delivery**. The adapter is intentionally unconfigured and unauthorized.

## Submission checklist after recording

1. Confirm the video is between two and five minutes and the camera is on.
2. Check that no password, token, secret, personal notification, or private tab appears in any frame.
3. Confirm **Replay mode** is visible when the deterministic incident runs.
4. Confirm the video shows a current heartbeat, Kafka publish and consume, NVIDIA model name, grounded citations, six HiddenLayer boundaries, and human approval.
5. Confirm WebEOC is described as an integration-ready preview, not as a completed government connection.
6. Paste the Loom link into `docs/SUBMISSION.md` and the hackathon submission form.
