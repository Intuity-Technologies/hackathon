# Model Deployment (Azure ML)

This folder contains baseline model assets and Azure ML deployment templates for public demos.

## Contents

- `training/train_baseline.py`: trains a RandomForest baseline from ETL signal parquet data.
- `azureml/model.yml`: model registration definition.
- `azureml/endpoint.yml`: managed online endpoint definition.
- `azureml/deployment.yml`: online deployment config.
- `azureml/score.py`: inference entrypoint (`init()`/`run()`).
- `azureml/environment.yml`: runtime environment dependencies.
- `azureml/sample-request.json`: sample payload for endpoint testing.

## Local training

```bash
python model/training/train_baseline.py
```

## Azure ML deployment flow

```bash
az ml model create --file model/azureml/model.yml --resource-group <rg> --workspace-name <ws>
az ml online-endpoint create --file model/azureml/endpoint.yml --resource-group <rg> --workspace-name <ws>
az ml online-deployment create --file model/azureml/deployment.yml --all-traffic --resource-group <rg> --workspace-name <ws>
az ml online-endpoint invoke --name irish-housing-signals-endpoint --request-file model/azureml/sample-request.json --resource-group <rg> --workspace-name <ws>
```

The scoring service is deterministic and model-backed. It does not use the LLM layer.
