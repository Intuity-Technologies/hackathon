# Affordable Housing Signals Prototype

Review-ready prototype for the itag AI Challenge housing problem area, focused on affordable housing, smart housing context, and urban-planning evidence.

## What This Prototype Does

- Scores county-level housing pressure deterministically from population growth, rent pressure, and housing completions.
- Surfaces county median sale price plus clearly labeled regional and national context signals for affordability and housing-system pressure.
- Serves one judged experience through Flask: dashboard, county drilldown, compare flow, and guided chat.
- Keeps Azure Functions, App Service, Bicep, and optional Azure ML deployment paths intact.

## Architecture

- `etl/transform/`: normalizers, signal builder, and local demo artifact generator.
- `etl/common/storage.py`: local/ADLS storage abstraction for pipeline steps.
- `service/housing_data.py`: shared demo artifact layer used by Flask and Azure Functions.
- `api/function_app.py`: health, overview, area, compare, trends, sources, and model feature endpoints.
- `web.py` + `templates/index.html`: dashboard-plus-chat prototype.
- `contracts/`: current-state signal and future forecast contracts.

## Local Quick Start

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt -r requirements-dev.txt -r etl/requirements.txt -r api/requirements.txt
$env:PYTHONPATH="."
python etl\transform\build_demo_artifacts.py
python web.py
```

The app works locally without Azure credentials by reading checked-in signals and demo artifacts. In Azure, the same dashboard reads its `signals` and `demo` payloads directly from ADLS-backed storage.

## ETL Modes

- Local-first mode: `PIPELINE_DATA_MODE=local` reads and writes under `data/`.
- ADLS mode: `PIPELINE_DATA_MODE=adls` uses Azure storage settings and preserves the cloud refresh/deploy path.

Typical local validation commands:

```powershell
$env:PYTHONPATH="."
python -m compileall api etl service model web.py
ruff check .
pytest
python etl\transform\build_demo_artifacts.py
```

## API Surface

- `GET /api/health`
- `GET /api/areas`
- `GET /api/overview`
- `GET /api/area/{name}`
- `GET /api/compare?areas=Cork;Galway`
- `GET /api/trends/{name}`
- `GET /api/sources`
- `GET /api/model/schema`
- `GET /api/model/features`

## Guardrails

- County scores are deterministic and retrieval-first.
- Regional and national signals are shown as context only and are not blended into the county composite score.
- The dashboard and assistant expose freshness, scope, provenance, and quality metadata.
- Future predictions remain a separate contract from current-state insights.

## Challenge Alignment

- Problem definition: county housing pressure, affordability, and supply delivery are framed for practical housing-agency decision support.
- Innovation: combines a guided prototype UI with a transparent retrieval-first evidence layer.
- Technical depth: repo includes ETL, API, frontend, IaC, CI, and model assets.
- Ethical compliance: demo explicitly labels scope, limitations, and non-comparable contextual signals.
- Presentation quality: reviewer guide and prebuilt local artifacts support a stable 5-minute walkthrough.

## More Reading

- `docs/REVIEWER_DEMO_GUIDE.md`
- `docs/ETHICS_AND_LIMITATIONS.md`
- `.github/infra/README.md`
- `model/README.md`
