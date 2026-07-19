# Austin FloodOps: Demo and Operator Guide

Austin FloodOps is a flood decision-support prototype. It helps an operator correlate changing public evidence and prepare a reversible response. It does not replace an emergency manager, hydrologist, dispatcher, or official alert.

## Start the system

Public hackathon application:

<https://austin-floodops-gedeon-tona-us-dev.apps.rm1.0a51.p1.openshiftapps.com>

Anonymous visitors can read the dashboard but cannot run assessments or change
decisions. Sign in with the presenter-provided demo account to receive an
eight-hour supervisor token kept only in browser memory. The shared email is
`gedeon@aitx.com`; the password is deliberately stored outside Git and this
guide.

Local application:

```bash
make test
make run
```

Kafka-compatible application stack:

```bash
make stream-smoke
```

Open `http://127.0.0.1:8080` for `make run`. The strict `make stream-smoke` stack uses `http://127.0.0.1:18081` by default so it cannot accidentally probe an existing development server. It leaves Docker Compose running for inspection. `make docker-down` stops it without deleting the local Docker volume.

## Read the top status

The heartbeat label is based on the server state:

- Checking or starting means no completed heartbeat cycle has been observed yet.
- Live means the most recent cycle completed and its source states are visible.
- Live partial means at least one optional source is degraded.
- Offline means the server cannot be reached.
- Paused means the autonomous heartbeat is disabled.

This label does not assert that every source or integration is healthy. Open the source status and integration gate to see individual results.

## Main interface

### Event timeline

The left timeline lists observed or replay evidence. Each card shows its source, time, title, location, and whether it is live or replay. Selecting evidence does not dispatch anything.

### Replay controls

Replay buttons load deterministic incidents for presentation and automated evaluation. Replay records are clearly labeled. They are not presented as current conditions.

For the main presentation, use **Inject · gage rise + warning**. The request
still uses the deployed Redpanda stream, all six HiddenLayer boundaries, and
hosted NVIDIA inference. Only the evidence itself comes from the labeled replay
fixture so the judge sees the same incident every time.

### Incident workspace

After assessment, the center workspace shows:

- the model summary and risk level;
- confidence from zero through one hundred percent;
- the proposed reversible action and target;
- the deterministic policy result;
- evidence identifiers and grounded citations;
- the heuristic impact estimate and its assumptions;
- map, prediction, routing, and audit views.

The model recommendation is advisory. NVIDIA is forced to call the typed
`record_incident_decision` function, and every citation is checked against the
exact evidence supplied to the model. The policy starts at approval required.
Approve and Reject change the local decision state and append an audit entry.

### Learning panel

Record a correction and outcome after reviewing a decision. The reflection step can turn that feedback into a versioned playbook rule. A later incident retrieves relevant active rules. Retire a rule if it is wrong or outdated.

Run learning evaluation only when you want to execute the three replay scenarios. It compares a baseline with a memory-assisted run and reports accuracy, latency, and interventions. The evaluation is a deterministic demonstration, not field validation.

### Security console

The console distinguishes configured, verified, degraded, blocked, and not configured states. HiddenLayer results appear only after a real scan. The public deployment currently verifies all six HiddenLayer boundaries. OpenShell restrictions count only when the application is actually launched through the OpenShell sandbox; the current OpenShift pod correctly shows OpenShell as not configured. The adversarial test deliberately submits unsafe text and should return quarantined.

### Integration gate

Configured means settings are present. Verified means the running application observed a successful operation. Those are different claims. A credential may be configured but expired, a service may be unreachable, or a component may not have run yet.

### Texas source adapters

National Weather Service, United States Geological Survey, and Austin crossing records are the core observed feeds. Lower Colorado River Authority, Texas Department of Transportation, Austin 311, and road-closure adapters are opportunistic. If they fail, the interface shows degraded and zero observed events. The live path never inserts a synthetic replacement.

### Resource inventory

The barricades, high-water vehicles, shelters, and personnel list is a local demonstration inventory. Assignment buttons demonstrate the human workflow and audit trail. They are not connected to an agency asset-management system.

### Simulation and prediction

Simulation uses a transparent threshold heuristic. It converts alert severity and gage levels into illustrative depth, exposure, and delay. Prediction fits a simple linear trend to recent gage observations and applies the same heuristic at future horizons. Always show the assumptions. Never present these values as an official forecast or hydraulic inundation model.

### Offline continuity

The service worker caches some interface assets and can keep an approval or rejection intent as a browser-local draft. It never executes that draft automatically and never caches authenticated application programming interface responses. This is not a FirstNet integration. After reconnecting, review current evidence, authenticate, and explicitly confirm the action again.

### Common Alerting Protocol and WebEOC previews

Common Alerting Protocol version 1.2 is an XML warning format. WebEOC is a commercial emergency-operations information-management product. The preview panel shows the Common Alerting Protocol XML and Simple Object Access Protocol envelope that the adapter can build.

The hackathon project is not an authorized Texas Division of Emergency Management connection. A delivery attempt remains blocked unless all of the following are true:

1. The decision is approved under policy.
2. The operator checks the explicit confirmation control.
3. Complete organization-issued WebEOC settings are configured.
4. The incident has not already been delivered.

## Recommended three-minute demo

1. Open the integration gate and state that configured and verified are separate.
2. Show a heartbeat with real National Weather Service, United States Geological Survey, and Austin records. Point out any degraded optional sources.
3. Run a replay assessment so the presentation is deterministic.
4. Open the decision and show the exact evidence identifiers behind all citations.
5. Explain that the policy requires a human and approve one reversible action.
6. Record an operator correction, then show the versioned memory.
7. Run the evaluation and show the before-and-after metrics.
8. Run the adversarial security test and show quarantine.
9. Show the Kafka probe result from `make stream-smoke`.
10. End with the boundary: working technical prototype now, agency authorization and hydrologic calibration next.

For the final timed narration, screen actions, recovery plan, and claims to
avoid, use [LOOM_SCRIPT.md](LOOM_SCRIPT.md).

## Useful verification commands

```bash
make test
make smoke
make stream-smoke
make preflight
```

The submission should include fresh outputs from these commands. Old evidence files are not substitutes for a passing current run.

## Presentation answers

If asked whether Kafka is required: no. The Red Hat track requires genuinely updating data. Kafka is used because it makes the event backbone replayable and independently consumable.

If asked whether the data is real: the successful live source records are real and carry provenance. Replay is labeled. Failed sources are shown as degraded, never replaced with fabricated live observations.

If asked whether it prevents flooding: it cannot prevent rainfall or flooding. It can reduce the time between warning evidence and a reviewed action such as closing a crossing, staging a barricade, or preparing a responder message.

If asked whether it is production ready: it is an end-to-end hackathon prototype. Operational deployment still requires agency authorization, calibrated hydrology, reliability work, accessibility review, security assessment, and field exercises.
