# Infrastructure (Bicep)

This folder contains modular Bicep templates for a public review-ready deployment:

- ADLS Gen2 storage for `raw`, `curated`, `signals`
- Azure Functions API host
- Flask web frontend on Azure App Service
- Key Vault + Log Analytics + App Insights
- Optional Azure ML workspace and ACR for model serving
- Optional Static Web App for public landing pages

## Module map

- `modules/storage.bicep`
- `modules/observability.bicep`
- `modules/function-app.bicep`
- `modules/web-app.bicep`
- `modules/key-vault.bicep`
- `modules/ml-platform.bicep`
- `modules/static-web.bicep`

## Deploy manually

```bash
az group create --name rg-irish-signals-dev --location westeurope
az deployment group create \
  --resource-group rg-irish-signals-dev \
  --template-file .github/infra/main.bicep \
  --parameters @.github/infra/parameters.dev.json
```

## Validate Bicep

```bash
az bicep build --file .github/infra/main.bicep
```

## Related delivery workflows

- `.github/workflows/deploy-infra.yml` deploys this Bicep stack.
- `.github/workflows/deploy-api.yml` deploys Azure Functions and verifies `/api/health`.
- `.github/workflows/deploy-web.yml` deploys Flask App Service and verifies `/`.
- `.github/workflows/deploy-static-web.yml` deploys `static-web/` to Azure Static Web Apps.
- `.github/workflows/deploy-model-azureml.yml` can optionally run Bicep, refresh CSO data, and release a new Azure ML model version.
