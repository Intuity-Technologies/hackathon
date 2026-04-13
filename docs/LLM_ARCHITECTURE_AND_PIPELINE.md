# LLM Query Architecture And Data Refresh Pipeline

## 1) LLM Querying Generated Scores (Runtime Architecture)

```mermaid
flowchart LR
    U["User"] --> FE["LLM Frontend Chat UI"]
    FE --> ORCH["LLM Orchestrator / Retrieval Layer"]
    ORCH --> API["Azure Functions API (api/function_app.py)"]

    API --> R1["GET /api/areas"]
    API --> R2["GET /api/area/{name}"]
    API --> R3["GET /api/model/schema"]
    API --> R4["GET /api/model/features"]

    R1 --> SIG["Signals Dataset (parquet + latest.json)"]
    R2 --> SIG
    R3 --> SIG
    R4 --> SIG

    SIG --> LLMOUT["Structured Evidence for LLM"]
    LLMOUT --> FE
    FE --> U
```

### Runtime intent

- ETL computes scores once; LLM does retrieval and explanation only.
- API is the stable contract between scored data and LLM interaction.
- LLM should answer using retrieved fields (`overall score`, `classification`, `driver`, `rank`, `percentile`, trend features).

## 2) Data Refresh + Scoring Pipeline (Batch Architecture)

```mermaid
flowchart TB
    T["Trigger: Weekly Cron or Manual Dispatch"] --> W["GitHub Workflow: refresh-data.yml"]
    W --> S["Resolve Source Files (PEA08, RIQ02, NDQxx/BHQxx)"]

    S --> N1["normalize_population.py"]
    S --> N2["normalize_rents.py"]
    S --> N3["normalize_planning.py"]

    N1 --> C1["curated/population parquet"]
    N2 --> C2["curated/rents parquet"]
    N3 --> C3["curated/planning parquet"]

    C1 --> B["build_signals.py"]
    C2 --> B
    C3 --> B

    B --> O1["signals/housing_pressure/part-000.parquet"]
    B --> O2["signals/housing_pressure/latest.json"]

    O1 --> V["check_signals_contract.py"]
    O2 --> V
    V --> A["Artifact Upload + API Readability"]
```

### Refresh intent

- Normalize raw files into consistent county-level curated tables.
- Build deterministic component scores and composite score.
- Publish both machine-friendly parquet and LLM-friendly JSON.
- Validate schema/range/coverage before downstream usage.
