import argparse
import io
import os

import pandas as pd
from azure.identity import DefaultAzureCredential
from azure.storage.filedatalake import DataLakeServiceClient

REQUIRED_COLUMNS = [
    "area_name",
    "area_level",
    "time_period",
    "population_growth",
    "rent_growth",
    "housing_completions",
    "population_growth_score",
    "rent_pressure_score",
    "supply_gap_score",
    "overall_housing_pressure_score",
    "classification",
    "dominant_driver",
    "explanation_summary",
    "score_qoq_change",
    "score_4q_avg",
    "rent_growth_4q_avg",
    "population_growth_4q_avg",
    "score_rank_in_period",
    "score_percentile_in_period",
    "model_feature_version",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate signal parquet contract.")
    parser.add_argument(
        "--file-system",
        default=os.getenv("SIGNALS_FILE_SYSTEM", "signals"),
        help="ADLS file system/container for signals parquet",
    )
    parser.add_argument(
        "--path",
        default=os.getenv(
            "SIGNALS_FILE_PATH",
            "housing_pressure/area_level=county/part-000.parquet",
        ),
        help="Path to signals parquet file within ADLS file system",
    )
    parser.add_argument(
        "--min-periods",
        type=int,
        default=4,
        help="Minimum number of unique time periods expected",
    )
    parser.add_argument(
        "--min-areas",
        type=int,
        default=3,
        help="Minimum number of unique areas expected",
    )
    return parser.parse_args()


def _load_signals_df(file_system: str, path: str) -> pd.DataFrame:
    account = os.getenv("AZURE_STORAGE_ACCOUNT", "").strip()
    if not account:
        raise ValueError("AZURE_STORAGE_ACCOUNT env var not set")
    svc = DataLakeServiceClient(
        account_url=f"https://{account}.dfs.core.windows.net",
        credential=DefaultAzureCredential(),
    )
    fs = svc.get_file_system_client(file_system)
    file_client = fs.get_file_client(path)
    data = file_client.download_file().readall()
    return pd.read_parquet(io.BytesIO(data))


def main() -> None:
    args = parse_args()
    df = _load_signals_df(args.file_system, args.path)
    if df.empty:
        raise ValueError("Signals dataframe is empty.")

    missing = sorted(set(REQUIRED_COLUMNS) - set(df.columns))
    if missing:
        raise ValueError(f"Signals missing required columns: {missing}")

    unique_periods = df["time_period"].astype(str).nunique()
    if unique_periods < args.min_periods:
        raise ValueError(
            f"Expected at least {args.min_periods} unique time_period values, found {unique_periods}."
        )

    unique_areas = df["area_name"].astype(str).nunique()
    if unique_areas < args.min_areas:
        raise ValueError(
            f"Expected at least {args.min_areas} unique area_name values, found {unique_areas}."
        )

    score = pd.to_numeric(df["overall_housing_pressure_score"], errors="coerce")
    if score.isna().all():
        raise ValueError("overall_housing_pressure_score is all null after numeric conversion.")

    invalid_score = df[(score < 0) | (score > 100)]
    if not invalid_score.empty:
        raise ValueError(
            "overall_housing_pressure_score has values outside expected 0-100 range."
        )

    print(
        "Signals contract check passed:"
        f" rows={len(df)}, areas={unique_areas}, periods={unique_periods}"
    )


if __name__ == "__main__":
    main()
