# Austin FloodOps: four-minute Loom recording script

This is the final presenter script for a two-to-five-minute hackathon video.
Keep the camera bubble on, speak at a steady conversational pace, and leave the
cursor beside the evidence you are describing. The target length is four
minutes and thirty-five seconds.

## Before recording

1. Open the public application:
   <https://austin-floodops-gedeon-tona-us-dev.apps.rm1.0a51.p1.openshiftapps.com>.
2. Use a desktop browser at about 1440 by 900 pixels and set zoom to 80 or 90 percent so the status rail, incident workspace, and integration gate are visible.
3. Sign in with `gedeon@aitx.com` and paste the demo password from the secure note. Do not say the password, show the secure note, or save the password in the browser.
4. Confirm the page says the signed-in role is `supervisor`.
5. Confirm the heartbeat is running and the National Weather Service, United States Geological Survey, Kafka-compatible stream, NVIDIA, HiddenLayer, Supabase, routing, role permissions, and audit entries are green or verified.
6. It is acceptable for Austin road closures, Lower Colorado River Authority, DriveTexas, and Austin 311 to show degraded. That proves the application exposes source failure instead of fabricating records.
7. Close unrelated tabs and notifications. Keep this script on a second device or printed page so the recording shows only the product.

## 0:00–0:45: Explain the Texas motivation and human stakes

**Screen:** Start on the top of the dashboard. Keep the application name,
heartbeat, source state, and event timeline visible. Use one respectful still
image of the Texas Hill Country only if its license and source are clear. Do not
use graphic disaster imagery.

**Say:**

> Austin FloodOps is motivated by the flooding crisis in the great state of
> Texas. On July fourth, 2025, the catastrophic Hill Country flood killed at
> least 135 people across Central Texas, including 117 people in Kerr County.
> At Hunt, the Guadalupe River rose from about ten feet to 37.52 feet in just
> over two hours. And this week, San Antonio again faced flash flooding and
> severe weather: numerous low-water crossings flooded, and the city barricaded
> twenty crossings while crews assessed damage. This system cannot stop rain or
> claim it would have prevented those deaths. It tries to help officials act
> sooner by turning fragmented warnings, gage readings, and crossing information
> into one cited, reversible recommendation with a human still in control.

## 0:45–1:10: Prove the live-data track

**Screen:** Point to the heartbeat cycle, last-success time, the successful
National Weather Service and United States Geological Survey sources, the
source timestamps, and one degraded optional source.

**Say:**

> This is the Red Hat Live Data track. Every thirty seconds the deployed agent
> checks real public feeds, preserves source and observation time, deduplicates
> unchanged records, and reacts when evidence changes. The live path receives
> official weather, water, and Austin crossing records. An unavailable optional
> feed stays degraded and is never replaced with fake live data.

## 1:10–1:35: Explain the real stream and deployed stack

**Screen:** Scroll or point to the integration gate. Highlight the
Kafka-compatible stream, Supabase, and OpenShift-backed public route.

**Say:**

> The application and a Redpanda broker run continuously on Red Hat OpenShift.
> Every new event is published through the Apache Kafka protocol, consumed,
> validated, and matched by identifier before assessment. SQLite keeps the
> authoritative ledger on persistent storage, while Supabase mirrors the record
> into hosted PostgreSQL without becoming a single point of failure.

## 1:35–2:15: Run the judged incident

**Screen:** Click **Inject · gage rise + warning**. While it runs, point to the
Replay state so nobody mistakes the deterministic scenario for current weather.
When the result appears, point to the warning records, gage observations, risk,
confidence, citations, proposed action, and Pending approval state.

**Say:**

> For a repeatable judge demonstration, I am now using a clearly labeled replay
> with two flood warnings and three rising gage observations. The same production
> pipeline still runs: Kafka round trip, three HiddenLayer scans before the model,
> hosted NVIDIA Nemotron inference, and three HiddenLayer scans afterward.
> Nemotron is forced to call one typed decision function. It cannot return an
> arbitrary tool or silently invent evidence. Every citation must exactly match
> an event identifier supplied to the model, or the assessment fails closed.

## 2:15–2:35: Separate reasoning from flood physics

**Screen:** Point to the Impact and Assumptions panel. Do not call the displayed
depth an official water-depth forecast.

**Say:**

> Nemotron correlates the evidence and explains a reversible action. A separate
> deterministic model produces an illustrative severity, exposure, and delay.
> It is transparent, but it is not a hydraulic flood model. Operational depth
> prediction still requires station calibration, terrain, drainage, uncertainty,
> and agency validation.

## 2:35–3:00: Prove human authority and auditability

**Screen:** Click **Approve reversible action**. Point to the Approved state.
Click **Refresh recent audit**, then **Verify chain**.

**Say:**

> The model cannot approve itself and approval does not dispatch anything. A
> signed-in supervisor reviews the cited evidence and changes only the local
> policy state. External delivery is a separate confirmed action and is blocked
> without organization-issued settings. The audit chain records the actor,
> decision, and previous record hash, so later edits become detectable.

## 3:00–3:25: Prove that operator feedback can change later behavior

**Screen:** Click **Run learning evaluation**. Point to Run 1 and Run 2 plus
memory in the chart and the intervention comparison.

**Say:**

> Austin FloodOps also learns from human correction without retraining the base
> model. Feedback becomes a versioned playbook rule. Relevant active rules can
> be retrieved for later incidents and retired if they become harmful. This
> three-scenario chart proves the feedback and retrieval mechanism changes the
> controlled evaluation. It is not a claim of one-hundred-percent real-world
> flood accuracy.

## 3:25–3:50: Prove the security boundary

**Screen:** Click **Run adversarial payload**. Point to Quarantined and the
HiddenLayer result. Then point to the integration gate where OpenShell is not
configured in the public pod.

**Say:**

> Public text, retrieved memory, the model request, the proposed tool call, the
> tool result, and the final answer are all treated as untrusted. HiddenLayer
> scans all six boundaries and prompt injection is quarantined. The repository
> also contains a separate NemoClaw and OpenShell sandbox proof that denied an
> undeclared network destination. I am not pretending that separate sandbox is
> the boundary around this public OpenShift pod.

## 3:50–4:35: Close on impact and credibility

**Screen:** Return to the incident card and keep the live heartbeat visible.
End on the repository or submission page only if it is already public.

**Say:**

> Austin FloodOps does not stop rainfall, replace incident command, or claim an
> authorized government connection. It shortens the path from fresh, fragmented
> evidence to a secure, cited, human-approved decision, and preserves why that
> decision changed. The goal is not to replace the National Weather Service,
> emergency managers, or first responders. It is to help them see converging
> evidence and consider a protective action sooner. The same adapter pattern can
> later support wildfire, heat, tornado, and other fast-moving hazards. The next
> step is an agency-sponsored shadow pilot with calibrated hydrology and field
> validation.

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
- If the NVIDIA or HiddenLayer assessment fails, stop the recording, verify `/health`, and record again. Do not substitute a fixture decision or edit around a failed integration.
- If the deterministic replay is slow, say that the request is crossing Kafka, six security scans, and hosted NVIDIA inference. Do not fill the pause with an unsupported claim.
- If the learning chart was already populated, say it is the most recent controlled evaluation and click the button only if there is enough time.
- Never click **Attempt Configured WebEOC Delivery** during the video. The adapter is intentionally unconfigured and unauthorized.

## Submission checklist after recording

1. Confirm the final video is between two and five minutes and the camera is on.
2. Check that no password, token, secret, personal notification, or private browser tab appears in any frame.
3. Confirm Replay is visible when the deterministic incident runs.
4. Confirm the video shows at least one current heartbeat timestamp, matching Kafka publication and consumption, the NVIDIA model name, grounded citations, six HiddenLayer boundaries, and the human approval state.
5. Paste the Loom link into `docs/SUBMISSION.md` and the hackathon submission form.
