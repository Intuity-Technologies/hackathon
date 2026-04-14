
import pandas as pd
from pathlib import Path

print("REAL prediction_store loaded")

# This module is responsible for looking up predictions from our dataset of pre-generated artifacts.
ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_PATH = ROOT / "data" / "processed" / "regional_housing_artifacts.csv"

_ARTIFACTS = pd.read_csv(ARTIFACT_PATH)

# Lookup is based on area_name and time_period, which are the most "deterministic" fields we can extract from user questions. We want to avoid any LLM involvement in this lookup process to ensure data integrity.
def lookup_prediction(area_name: str, time_period: str):
    matches = _ARTIFACTS[

        # Match on area_name, exact match on time_period
        (_ARTIFACTS["area_name"].str.lower() == area_name.lower()) &
        (_ARTIFACTS["time_period"] == time_period)
    ]

    # If multiple matches, just take the first one
    if matches.empty:
        return None

    return matches.iloc[0].to_dict()