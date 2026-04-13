
import pandas as pd
from pathlib import Path

print("REAL prediction_store loaded")

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_PATH = ROOT / "data" / "processed" / "regional_housing_artifacts.csv"

_ARTIFACTS = pd.read_csv(ARTIFACT_PATH)

def lookup_prediction(area_name: str, time_period: str):
    matches = _ARTIFACTS[
        (_ARTIFACTS["area_name"].str.lower() == area_name.lower()) &
        (_ARTIFACTS["time_period"] == time_period)
    ]

    if matches.empty:
        return None

    return matches.iloc[0].to_dict()