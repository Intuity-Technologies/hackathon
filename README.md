# itag AI Challenge 2025 - Housing Crisis Info Retrieval

Unified repository that merges:
- `hackathon-test`: ETL pipeline, Azure Functions API, infrastructure workflows.
- `hackathon-main`: Flask frontend and retrieval-first LLM orchestration.

## Architecture

- `etl/`: Ingest, normalize, and score housing pressure indicators.
- `api/`: Azure Functions endpoints serving latest county/national signals.
- `service/`: LLM intent extraction + deterministic retrieval routing.
- `web.py` + `templates/`: Flask chat frontend.
- `model/`: baseline training and Azure ML endpoint deployment assets.
- `output/jupyter-notebook/`: Google Colab demo templates for reviewers.
- `.github/`: CI, data contract checks, infra/model deploy workflows.

## Retrieval-First Guardrail

Numeric topics are served from hard data only.
- `service/prediction_store.py` fetches from `api/area/{name}`.
- If API is unavailable locally, it can use `data/signals/housing_pressure/latest.json`.
- LLM fallback is only for qualitative explanations.

## Quick Start (Local)

1. Create a virtual environment and install dependencies:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt -r etl/requirements.txt -r api/requirements.txt
```

2. Copy `.env.example` to `.env` and populate Azure credentials.

3. Run Flask web app:

```powershell
python web.py
```

4. Run ETL pipeline (requires ADLS access):

```powershell
$env:PYTHONPATH="."
python etl/transform/normalize_population.py
python etl/transform/normalize_rents.py
python etl/transform/normalize_planning.py
python etl/transform/build_signals.py
```

Optional ingestion utilities for official external sources:

```powershell
python etl/ingest/fetch_world_bank_indicator.py FP.CPI.TOTL.ZG --country IE
python etl/ingest/fetch_central_bank_dataset.py --dataset-id retail_rates --url "https://example.centralbank.ie/data.csv"
```

5. Start Azure Functions API from `api/`:

```powershell
func start
```

## API Routes

- `GET /api/health`
- `GET /api/areas`
- `GET /api/area/{name}`
- `GET /api/model/schema`
- `GET /api/model/features`

## Infra And Deployment Assets

- Bicep templates: `.github/infra/main.bicep` + `.github/infra/modules/*`
- Infra docs: `.github/infra/README.md`
- Infra workflow: `.github/workflows/deploy-infra.yml`
- Static Web App workflow: `.github/workflows/deploy-static-web.yml`
- Model deploy workflow: `.github/workflows/deploy-model-azureml.yml`

## CI/CD Coverage

- Azure Functions API: `.github/workflows/deploy-api.yml` (deploy + post-deploy `/api/health` smoke test)
- Flask frontend on App Service: `.github/workflows/deploy-web.yml` (deploy + post-deploy `/` smoke test)
- Azure Static Web App (optional landing page): `.github/workflows/deploy-static-web.yml` from `static-web/`
- ETL refresh with latest CSO pulls: `.github/workflows/refresh-data.yml`
- Versioned Azure ML model release with optional Bicep + data refresh: `.github/workflows/deploy-model-azureml.yml`

Required GitHub secrets for these workflows include:
- `AZURE_CREDENTIALS`
- `AZURE_STORAGE_ACCOUNT`, `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`
- `AZURE_FUNCTIONAPP_NAME`, `AZURE_FUNCTIONAPP_PUBLISH_PROFILE`
- `AZURE_WEBAPP_NAME`, `AZURE_WEBAPP_PUBLISH_PROFILE`
- `AZURE_STATIC_WEB_APPS_API_TOKEN` (only if Static Web App deployment is enabled)

## Model Deployment Assets

- Baseline trainer: `model/training/train_baseline.py`
- Azure ML score entrypoint: `model/azureml/score.py`
- Azure ML endpoint/deployment specs: `model/azureml/endpoint.yml`, `model/azureml/deployment.yml`
- Model docs: `model/README.md`

## Google Colab Templates

- `output/jupyter-notebook/colab-template-01-data-ingestion.ipynb`
- `output/jupyter-notebook/colab-template-02-signal-pipeline.ipynb`
- `output/jupyter-notebook/colab-template-03-retrieval-demo.ipynb`
- Reviewer walkthrough: `docs/REVIEWER_DEMO_GUIDE.md`

## Useful Validation Commands

```powershell
python -m compileall api etl service web.py
python etl/tests/check_signals_contract.py --min-periods 4 --min-areas 3
az bicep build --file .github/infra/main.bicep
```
