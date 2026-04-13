from __future__ import annotations

import os
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

FEATURE_COLUMNS = [
    "population_growth",
    "rent_growth",
    "housing_completions",
    "population_growth_score",
    "rent_pressure_score",
    "supply_gap_score",
]
TARGET_COLUMN = "overall_housing_pressure_score"


def _load_training_df(path: str) -> pd.DataFrame:
    dataframe = pd.read_parquet(path)
    missing = sorted(set(FEATURE_COLUMNS + [TARGET_COLUMN]) - set(dataframe.columns))
    if missing:
        raise ValueError(f"Missing columns in training data: {missing}")
    data = dataframe[FEATURE_COLUMNS + [TARGET_COLUMN]].copy()
    return data.dropna()


def main() -> None:
    input_path = os.getenv(
        "SIGNALS_TRAINING_PARQUET",
        "data/signals/housing_pressure/area_level=county/part-000.parquet",
    )
    output_dir = Path(os.getenv("MODEL_OUTPUT_DIR", "model/artifacts"))
    output_dir.mkdir(parents=True, exist_ok=True)

    df = _load_training_df(input_path)
    if len(df) < 30:
        raise ValueError("Not enough rows to train a baseline model. Need at least 30 rows.")

    x = df[FEATURE_COLUMNS]
    y = df[TARGET_COLUMN]

    x_train, x_valid, y_train, y_valid = train_test_split(
        x, y, test_size=0.2, random_state=42
    )

    model = Pipeline(
        steps=[
            ("scale", StandardScaler()),
            (
                "rf",
                RandomForestRegressor(
                    n_estimators=300,
                    random_state=42,
                    max_depth=8,
                    min_samples_leaf=2,
                ),
            ),
        ]
    )

    model.fit(x_train, y_train)
    preds = model.predict(x_valid)
    mae = mean_absolute_error(y_valid, preds)

    artifact = {
        "model": model,
        "feature_columns": FEATURE_COLUMNS,
        "target_column": TARGET_COLUMN,
        "validation_mae": float(mae),
    }

    artifact_path = output_dir / "housing_pressure_model.joblib"
    joblib.dump(artifact, artifact_path)
    print(f"Saved model artifact: {artifact_path}")
    print(f"Validation MAE: {mae:.4f}")


if __name__ == "__main__":
    main()
