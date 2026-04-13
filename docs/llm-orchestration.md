# LLM Orchestration Layer

This project uses a retrieval-first architecture for integrating
ETL/API housing signals with an LLM UX.

## Key Design Points

- Signals are computed by ETL and exposed through Azure Functions endpoints.
- The orchestration layer checks for an existing artifact before any LLM call.
- Numeric topics (`price`, `rent`) only return retrieved artifacts or an explicit
  "no verified data" response.
- This prevents numerical hallucinations by construction.

## Current State

- `prediction_store.py` reads county-level artifacts from `/api/area/{name}`.
- If API is unavailable locally, it can read from `data/signals/housing_pressure/latest.json`.
- LLM fallback is used for qualitative explanations only.
