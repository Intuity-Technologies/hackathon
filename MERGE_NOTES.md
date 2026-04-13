# Merge Notes

This working tree was consolidated from two snapshot folders:

- `hackathon-test`: ETL, API, data, and GitHub workflows.
- `hackathon-main`: Flask UI and LLM orchestration layer.

## Integration outcomes

- Unified top-level structure now includes `api/`, `etl/`, `service/`, `templates/`, and `data/`.
- Retrieval-first orchestration now pulls county artifacts from the API (or local snapshot fallback).
- CI/dependabot now target the Python/Flask architecture instead of a missing `web/` Next.js app.
- Added ingestion utilities for World Bank indicators and Central Bank dataset URLs.
