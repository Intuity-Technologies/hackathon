# High Level Design

## Goal

Provide a reliable housing-pressure signal system where:

- ETL produces consistent, explainable scores.
- API exposes retrieval-friendly score payloads.
- LLM frontend turns retrieved statistics into interactive insights.

## System Boundaries

- In scope: ingest/normalize/score pipeline, signal publishing, retrieval API.
- Out of scope: final prediction product UX, model orchestration strategy, business policy decisions.

## Core Layers

1. Data ingestion and normalization  
   Converts heterogeneous source formats into unified curated parquet tables.

2. Signal scoring  
   Derives component scores (`population`, `rent`, `supply`), composite score, classification, rank/percentile, and trend features.

3. Retrieval API  
   Exposes latest and model-feature views for downstream consumers and LLMs.

4. LLM interaction layer  
   Retrieves procedural outputs and explains them; does not recompute ETL formulas.

## Why this architecture works for LLM

- Deterministic scoring prevents inconsistent AI-only calculations.
- Named metrics and derived features improve explainability.
- Rank/percentile fields make relative comparisons easy in conversational responses.
- Trend features (`qoq`, `4q avg`) support narrative about direction and persistence.

## Recommended prediction framing

- Keep current-period score procedural (already defined by ETL).
- Use ML for future-state questions (`t+1` score/class/risk shift).
- Return predictions as a separate contract so LLM can combine:
  - current deterministic signal
  - forecasted pressure/risk signal
