# Post-Hackathon Operationalization Plan

This is a future hardening backlog, not a statement that the current prototype is production ready.

## Current starting point

The hackathon build already runs as a single-instance OpenShift deployment with
a persistent application ledger, a persistent Kafka-compatible broker,
server-side secrets, read-only anonymous access, authenticated supervisor
actions, a Supabase mirror, and runtime probes. Operationalization is therefore
an upgrade from a working vertical slice, not a proposal to replace mock
components.

## Evidence and hydrology

- Establish supported source contracts and monitor schema changes.
- Add station metadata, datum conversion, rating curves, rainfall, soil moisture, terrain, drainage, and forecast uncertainty.
- Calibrate and back-test each watershed with hydrologists.
- Define freshness and conflict policies with emergency managers.

## Reliability

- Separate collection, normalization, assessment, and notification workers with durable Kafka consumer groups.
- Add a dead-letter topic, replay tooling, lag alerts, and idempotent recovery tests.
- Run multi-zone storage, backups, restore drills, and load tests.
- Define service-level objectives and an incident-response rotation.
- Replace the single OpenShift application and Redpanda instances with
  multi-zone replicas, disruption budgets, broker replication, monitored
  consumer lag, and tested failover.

## Safety and security

- Commission independent threat modeling and penetration testing.
- Rotate credentials, use a managed secret store, and scan every commit and container.
- Enable role-based access control by default with organization identity.
- Require two-person approval for consequential external delivery.
- Complete accessibility, privacy, records-retention, and legal reviews.
- Replace the shared demo account with organization identity, short-lived
  sessions, multi-factor authentication, and agency-managed role assignments.
- Run the production worker inside an approved OpenShell or equivalent runtime
  boundary and independently validate the HiddenLayer fail-closed policy.

## Agency and vendor integration

- Obtain written agency sponsorship and sandbox credentials.
- Validate Common Alerting Protocol and Emergency Data Exchange Language documents with receiving systems.
- Certify WebEOC behavior with the vendor or agency owner.
- Integrate a real resource-management system only after a signed interface agreement.
- Run tabletop exercises, shadow operation, and supervised field trials before any live use.
