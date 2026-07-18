# Austin FloodOps — three-minute Loom script

Record with Loom, camera on, and keep the dashboard visible. Do not claim an integration is verified unless its status is green during this recording.

## 0:00–0:20 — Problem and user

“Flood responders must correlate weather warnings, water-gage readings, and crossing conditions spread across separate systems. Austin FloodOps is a persistent decision-support agent that turns fresh public evidence into one cited, reversible recommendation while keeping a human in control.”

## 0:20–0:55 — Live heartbeat

Show the heartbeat label, cycle number, source statuses, freshness, and event timeline.

“Every thirty seconds the agent checks official public feeds, deduplicates unchanged records, and acts only when evidence changes. A failed source is shown as degraded; the system never substitutes synthetic live observations.”

If no new live incident is available, say so and switch to the clearly labeled replay scenario.

## 0:55–1:35 — Core decision loop

Run **gage rise + warning**. Show the National Weather Service and United States Geological Survey evidence, three grounded citations, Nemotron risk assessment, confidence, and proposed reversible action.

“Configured Kafka-compatible streaming round-trips new evidence through publish and consume before assessment. Without Kafka, the interval-based live feeds still satisfy the track and the direct fallback is reported explicitly.”

## 1:35–1:55 — Human authority

Show approval-required, click approve, and show the audit entry.

“The model cannot dispatch. A human reviews the evidence and explicitly approves or rejects the reversible recommendation.”

## 1:55–2:25 — Learning

Run the learning evaluation and show run one versus run two.

“An operator correction becomes a versioned playbook rule. A later run retrieves that rule. This chart is a controlled evaluation result, not a claim of production accuracy.”

## 2:25–2:45 — Runtime security

Run the adversarial test and show quarantine plus the six HiddenLayer boundaries. Briefly show the checked-in OpenShell deny evidence.

“Public input, memory, model requests, tool calls, tool results, and final output are treated as untrusted. Prompt injection is quarantined before inference, and OpenShell blocks unauthorized network access.”

## 2:45–3:00 — Close

“Austin FloodOps does not stop water or replace incident command. It shortens the path from fragmented, fresh evidence to a safe, cited, human-approved decision—and learns from every correction.”

Show the public repository and reproduction command.
