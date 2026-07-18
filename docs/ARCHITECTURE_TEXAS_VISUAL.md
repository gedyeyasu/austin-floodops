# Austin FloodOps: Visual Architecture

## Live decision loop

```mermaid
flowchart TD
    subgraph Sources["Observed public evidence"]
        NWS["National Weather Service alerts"]
        USGS["United States Geological Survey gages"]
        AUS["Austin low-water crossings"]
        TRY["Attempted LCRA, TxDOT, and Austin 311 adapters"]
    end

    Sources --> NORMALIZE["Normalize and validate FloodEvent"]
    NORMALIZE --> DEDUP["Stable identifier deduplication"]
    DEDUP --> STREAM{"Kafka-compatible broker configured?"}
    STREAM -->|yes| KAFKA["Redpanda or Kafka\npublish → consume → validate"]
    STREAM -->|no| DIRECT["Explicit direct path"]
    KAFKA --> SECURITY["HiddenLayer security boundaries"]
    DIRECT --> SECURITY
    SECURITY --> MODEL["NVIDIA Nemotron\ntyped recommendation"]
    MODEL --> GROUND["Ground every citation in input evidence"]
    GROUND --> POLICY["Deterministic approval policy"]
    POLICY --> LEDGER["SQLite ledger\noptional Supabase mirror"]
    LEDGER --> HUMAN["Human review\napprove · reject · correct"]
    HUMAN --> MEMORY["Versioned playbook memory"]
    MEMORY -. relevant active rules .-> MODEL
```

## Trust boundaries

```mermaid
sequenceDiagram
    participant Feed as Public feed
    participant Stream as Kafka-compatible stream
    participant Guard as HiddenLayer and validators
    participant Model as Nemotron
    participant Policy as Policy gate
    participant Human as Human operator
    participant Adapter as Responder adapter

    Feed->>Stream: Normalized FloodEvent
    Stream->>Guard: Consumed and schema-validated event
    Guard-->>Guard: Quarantine unsafe text or continue
    Guard->>Model: Bounded evidence and active memories
    Model->>Guard: Structured recommendation
    Guard-->>Guard: Validate type and ground citations
    Guard->>Policy: Proposed reversible action
    Policy-->>Human: Approval required
    Human->>Policy: Approve or reject
    Policy-->>Adapter: Eligible only after explicit confirmation
```

## Sponsor-tool contribution

| Tool | Work it performs | Proof in the product |
|---|---|---|
| NVIDIA Nemotron | Correlates live evidence into one typed recommendation | Decision contains model name, raw response metadata, rationale, and grounded citations |
| HiddenLayer Runtime Security | Scans untrusted evidence and model boundaries | Security panel shows each real boundary outcome; suspicious content is quarantined |
| NemoClaw and OpenShell | Restricts filesystem, process, and network access when launched in that sandbox | Checked-in policy and deny evidence; not claimed when running plain Docker Compose |
| Redpanda using the Kafka protocol | Provides the local live event backbone | `make stream-smoke` must publish and consume the same event identifier |
| Supabase | Optionally mirrors the local ledger | Runtime probe and best-effort writes; SQLite remains authoritative |

## Demo versus operational status

```mermaid
flowchart LR
    REAL["Working prototype\nLive feeds · stream · model · policy · ledger"]
    DEMO["Labeled demonstrations\nReplay · resource inventory · heuristic impact"]
    FUTURE["Requires agency work\nAuthorization · calibration · certification · field exercises"]
    REAL --> DEMO --> FUTURE
```

The Red Hat Live Data track does not require a Red Hat-hosted Kafka service. The qualifying heartbeat is the updating public data itself. Kafka-compatible streaming strengthens the architecture by making freshness, replay, back pressure, and consumer independence explicit.
