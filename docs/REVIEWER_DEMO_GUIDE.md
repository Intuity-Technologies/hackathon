# Reviewer Demo Guide

This repository is structured to demonstrate end-to-end technical delivery for the itag AI Challenge.

## 1) Frontend and Retrieval UX

- Flask app entrypoint: `web.py`
- UI template: `templates/index.html`
- Retrieval-first routing: `service/orchestrator.py`

Run locally:

```bash
pip install -r requirements.txt
python web.py
```

## 2) ETL and API

- ETL transforms: `etl/transform/*`
- Ingestion utilities: `etl/ingest/*`
- API endpoints: `api/function_app.py`

Contract check:

```bash
python etl/tests/check_signals_contract.py --min-periods 4 --min-areas 3
```

## 3) Azure Infrastructure as Code

- Main composition: `.github/infra/main.bicep`
- Modules: `.github/infra/modules/*`
- CI deployment workflow: `.github/workflows/deploy-infra.yml`

## 4) Model Deployment to Azure ML

- Training script: `model/training/train_baseline.py`
- Scoring entrypoint: `model/azureml/score.py`
- Endpoint/deployment specs: `model/azureml/*.yml`
- Workflow: `.github/workflows/deploy-model-azureml.yml`

## 5) Colab Templates for Walkthrough

- `output/jupyter-notebook/colab-template-01-data-ingestion.ipynb`
- `output/jupyter-notebook/colab-template-02-signal-pipeline.ipynb`
- `output/jupyter-notebook/colab-template-03-retrieval-demo.ipynb`
