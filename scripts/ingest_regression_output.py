import pandas as pd
from pathlib import Path

# ----------------------------
# Paths
# ----------------------------
ROOT = Path(__file__).resolve().parents[1]
RAW_PATH = ROOT / "data" / "raw" / "ITAG_finaldata.csv"
OUT_PATH = ROOT / "data" / "processed" / "regional_housing_artifacts.csv"

# ----------------------------
# Sanity check: raw file must exist
# ----------------------------
if not RAW_PATH.exists():
    raise FileNotFoundError(
        f"""
❌ Raw model output not found.

Expected file:
  {RAW_PATH}

Action:
- Copy the regression output CSV into data/raw/
- Name it exactly: ITAG_finaldata.csv
- Re-run this script
"""
    )

# ----------------------------
# Load raw model output
# ----------------------------
df = pd.read_csv(RAW_PATH)

if df.empty:
    raise ValueError("❌ Raw CSV loaded but contains no rows.")

# ----------------------------
# Define the artifact schema
# (THIS is the contract)
# ----------------------------
ARTIFACT_COLUMNS = [
    # identifiers
    "area_name",
    "time_period",
    "year",
    "quarter",

    # headline model outputs
    "predicted_classification_glm",
    "pred_housing_stress_score",
    "cluster_label",
    "dominant_model_driver",

    # secondary numeric outputs
    "pred_rent_level",
    "pred_arrears_90d_rate",

    # contextual signals (display only)
    "rent_growth",
    "population_growth",
    "housing_completions",
]

# ----------------------------
# Schema validation
# ----------------------------
missing = sorted(set(ARTIFACT_COLUMNS) - set(df.columns))
if missing:
    raise ValueError(
        f"❌ Missing expected columns in raw CSV:\n  {missing}"
    )

artifact_df = df[ARTIFACT_COLUMNS].copy()

# ----------------------------
# Drop completely empty artifacts
# ----------------------------
artifact_df = artifact_df.dropna(
    subset=["area_name", "time_period", "predicted_classification_glm"]
)

# ----------------------------
# Normalise / clean values
# ----------------------------
artifact_df["pred_housing_stress_score"] = (
    artifact_df["pred_housing_stress_score"]
    .astype(float)
    .round(1)
)

artifact_df["pred_rent_level"] = (
    artifact_df["pred_rent_level"]
    .astype(float)
    .round(0)
)

artifact_df["pred_arrears_90d_rate"] = (
    artifact_df["pred_arrears_90d_rate"]
    .astype(float)
    .round(3)
)

artifact_df["rent_growth"] = artifact_df["rent_growth"].astype(float).round(1)
artifact_df["population_growth"] = artifact_df["population_growth"].astype(float).round(1)

artifact_df["housing_completions"] = (
    artifact_df["housing_completions"]
    .astype(float)
    .round(0)
    .astype("Int64")
)


before = len(artifact_df)
artifact_df = artifact_df.drop_duplicates(subset=ARTIFACT_COLUMNS, keep="first")
after = len(artifact_df)
print(f"ℹDropped {before - after} exact duplicate artifact rows")


# ----------------------------
# Collapse duplicates by key (KEEP FIRST)
# ----------------------------
before = len(artifact_df)

artifact_df = artifact_df.drop_duplicates(
    subset=["area_name", "time_period"],
    keep="first"   # <- literally keep the first row encountered
)

after = len(artifact_df)
print(f"ℹDropped {before - after} rows due to duplicate (area_name, time_period)")


# ----------------------------
# Stable ordering (clean diffs)
# ----------------------------
artifact_df = artifact_df.sort_values(
    by=["area_name", "year", "quarter"]
).reset_index(drop=True)

# ----------------------------
# Write processed artifacts
# ----------------------------
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
artifact_df.to_csv(OUT_PATH, index=False)

print(
    f"Wrote {len(artifact_df)} artifacts → {OUT_PATH}\n"
    f"Areas: {artifact_df['area_name'].nunique()} | "
    f"Periods: {artifact_df['time_period'].nunique()}"
)