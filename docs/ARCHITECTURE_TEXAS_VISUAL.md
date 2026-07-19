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
    SECURITY --> MODEL["NVIDIA Nemotron\nforced decision tool call"]
    MODEL --> GROUND["Ground every citation in input evidence"]
    GROUND --> POLICY["Deterministic approval policy"]
    POLICY --> LEDGER["Persistent SQLite ledger\nverified Supabase mirror"]
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
| NVIDIA Nemotron | Correlates live evidence by calling a constrained decision function | Decision contains model name, tool arguments, rationale, and exact grounded citations |
| HiddenLayer Runtime Security | Scans untrusted evidence and model boundaries | Security panel shows each real boundary outcome; suspicious content is quarantined |
| NemoClaw and OpenShell | Restricts filesystem, process, and network access when launched in that sandbox | Checked-in policy and deny evidence; not claimed when running plain Docker Compose |
| Redpanda using the Kafka protocol | Provides the live event backbone locally and on OpenShift | Runtime state and `make stream-smoke` prove publication and consumption of the same event identifier |
| Supabase | Mirrors the local ledger into hosted PostgreSQL | Production runtime probe and best-effort writes; SQLite remains authoritative |

## Deployed topology

```mermaid
flowchart LR
    BROWSER["Browser\npublic viewer or signed-in operator"] --> ROUTE["OpenShift secure route"]
    ROUTE --> APP["FastAPI pod\nheartbeat + dashboard + policy"]
    APP <--> BROKER["Redpanda pod\nKafka-compatible topic"]
    APP --> PVC1["SQLite persistent volume"]
    BROKER --> PVC2["Stream persistent volume"]
    APP --> NVIDIA["Hosted NVIDIA Nemotron"]
    APP --> HIDDEN["HiddenLayer runtime scans"]
    APP --> SUPABASE["Supabase PostgreSQL mirror"]
```

OpenShift Secrets provide server credentials. Anonymous users are read-only;
the demo login issues a supervisor token held only in browser memory.

## Demo versus operational status

```mermaid
flowchart LR
    REAL["Working prototype\nLive feeds · stream · model · policy · ledger"]
    DEMO["Labeled demonstrations\nReplay · resource inventory · heuristic impact"]
    FUTURE["Requires agency work\nAuthorization · calibration · certification · field exercises"]
    REAL --> DEMO --> FUTURE
```

The Red Hat Live Data track does not require a Red Hat-hosted Kafka service. The qualifying heartbeat is the updating public data itself. Kafka-compatible streaming strengthens the architecture by making freshness, replay, back pressure, and consumer independence explicit.
