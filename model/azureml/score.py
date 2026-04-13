from __future__ import annotations

import json
import os
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

MODEL = None
FEATURE_COLUMNS = [
    "population_growth",
    "rent_growth",
    "housing_completions",
    "population_growth_score",
    "rent_pressure_score",
    "supply_gap_score",
]


def init() -> None:
    global MODEL
    model_dir = Path(os.getenv("AZUREML_MODEL_DIR", "model/artifacts"))
    model_path = model_dir / "housing_pressure_model.joblib"
    if model_path.exists():
        payload = joblib.load(model_path)
        MODEL = payload.get("model")
        loaded_features = payload.get("feature_columns")
        if isinstance(loaded_features, list) and loaded_features:
            _update_features(loaded_features)


def _update_features(features: list[str]) -> None:
    global FEATURE_COLUMNS
    FEATURE_COLUMNS = [str(feature) for feature in features]


def _fallback_score(df: pd.DataFrame) -> np.ndarray:
    weighted = (
        (df["population_growth_score"].fillna(0) * 0.2)
        + (df["rent_pressure_score"].fillna(0) * 0.4)
        + (df["supply_gap_score"].fillna(0) * 0.4)
    )
    return weighted.to_numpy(dtype=float)


def run(raw_data: str):
    try:
        payload = json.loads(raw_data)
    except json.JSONDecodeError:
        return {"error": "Invalid JSON payload."}

    records = payload.get("data") if isinstance(payload, dict) else payload
    if not isinstance(records, list) or not records:
        return {"error": "Expected a non-empty list in payload.data."}

    frame = pd.DataFrame(records)
    missing = [feature for feature in FEATURE_COLUMNS if feature not in frame.columns]
    if missing:
        return {"error": f"Missing required features: {missing}"}

    model_input = frame[FEATURE_COLUMNS].apply(pd.to_numeric, errors="coerce").fillna(0)

    if MODEL is None:
        predictions = _fallback_score(model_input)
    else:
        predictions = MODEL.predict(model_input)

    return {
        "count": int(len(predictions)),
        "predictions": [float(value) for value in predictions],
        "feature_columns": FEATURE_COLUMNS,
    }
