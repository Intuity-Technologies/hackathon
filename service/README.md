## Purpose

This folder contains the shared evidence and orchestration layer for the prototype.

### Responsibilities

- `housing_data.py`: loads or builds local demo artifacts for overview, leaderboard, area detail, compare, trends, and sources.
- `intent_extractor.py`: maps user language into housing topics and county intents.
- `render.py`: deterministic text rendering for overview, county detail, and compare responses.
- `orchestrator.py`: retrieval-first routing for the assistant.
- `llm_client.py`: qualitative fallback only when structured evidence is not a fit.
