## Purpose

This folder contains the retrieval-first orchestration layer for user questions.

The LLM does not generate or estimate financial numbers. Numeric responses are
resolved through `prediction_store.py`, which reads from the Azure Functions API
(`api/function_app.py`) and can fall back to a local signals snapshot for local dev.

### Responsibilities

- `intent_extractor.py`: convert user question into structured intent.
- `prediction_store.py`: fetch hard data artifacts by county/topic.
- `render.py`: deterministic text formatting for retrieved artifacts.
- `llm_client.py`: qualitative fallback only when numeric artifacts are unavailable.
- `orchestrator.py`: route and enforce retrieval-first guarantees.
