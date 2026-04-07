# LLM Orchestration Layer

This project uses a retrieval-first architecture for integrating
regression-based housing predictions with an LLM.

## Key Design Points

- Regression models output structured prediction artifacts.
- The orchestration layer checks for an existing prediction before any LLM is called.
- If a prediction exists, the LLM is never invoked.
- This prevents numerical hallucinations by construction.

## Current State

- Uses mock prediction data while regression models are under development.
- Real model outputs can be dropped in without changing orchestration logic.
