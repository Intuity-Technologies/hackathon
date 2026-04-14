# Google Colab Showcase Notebooks

These notebooks are now public showcase artifacts rather than empty setup templates.

- `colab-template-01-data-ingestion.ipynb`: demonstrates source provenance, ingestion commands, and safe secret-gated reruns.
- `colab-template-02-signal-pipeline.ipynb`: walks through normalization, scoring, and the latest county leaderboard snapshot.
- `colab-template-03-retrieval-demo.ipynb`: shows the retrieval and orchestration layer with example questions, answers, and optional hosted API checks.

## How to use them

1. Open the notebook from GitHub in Colab with the included badge.
2. Run the repo setup cell to clone the repository and install dependencies.
3. Review the checked-in narrative, tables, and example outputs even if you do not have credentials.
4. For live reruns, add secrets in the Colab key panel and grant notebook access.

## Recommended Colab secret names

- `AZURE_STORAGE_ACCOUNT`
- `AZURE_TENANT_ID`
- `AZURE_CLIENT_ID`
- `AZURE_CLIENT_SECRET`
- `PREDICTION_API_BASE_URL`

The notebooks use `google.colab.userdata.get(...)` when available and never embed plaintext secrets in notebook source.
