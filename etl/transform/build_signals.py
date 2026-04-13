import io
import json
import os
from typing import Tuple

import pandas as pd
from azure.identity import DefaultAzureCredential
from azure.storage.filedatalake import DataLakeServiceClient

from etl.common.scoring import minmax_score

AREA_LEVEL = os.getenv("AREA_LEVEL", "county")

CURATED_FS = os.getenv("CURATED_FILE_SYSTEM", "curated")
SIGNALS_FS = os.getenv("SIGNALS_FILE_SYSTEM", "signals")
POPULATION_CURATED_PATH = os.getenv(
    "POPULATION_CURATED_PATH",
    f"population/area_level={AREA_LEVEL}/part-000.parquet",
)
RENTS_CURATED_PATH = os.getenv(
    "RENTS_CURATED_PATH",
    f"rents/area_level={AREA_LEVEL}/part-000.parquet",
)
PLANNING_CURATED_PATH = os.getenv(
    "PLANNING_CURATED_PATH",
    f"planning/area_level={AREA_LEVEL}/part-000.parquet",
)
SIGNALS_FILE_PATH = os.getenv(
    "SIGNALS_FILE_PATH",
    f"housing_pressure/area_level={AREA_LEVEL}/part-000.parquet",
)
SIGNALS_LATEST_JSON_PATH = os.getenv(
    "SIGNALS_LATEST_JSON_PATH",
    "housing_pressure/latest.json",
)


def get_service_client() -> DataLakeServiceClient:
    storage_account = os.getenv("AZURE_STORAGE_ACCOUNT", "").strip()
    if not storage_account:
        raise ValueError("AZURE_STORAGE_ACCOUNT env var not set")
    return DataLakeServiceClient(
        account_url=f"https://{storage_account}.dfs.core.windows.net",
        credential=DefaultAzureCredential(),
    )


def read_parquet_from_adls(file_system: str, path: str) -> pd.DataFrame:
    svc = get_service_client()
    fs = svc.get_file_system_client(file_system)
    file_client = fs.get_file_client(path)
    data = file_client.download_file().readall()
    return pd.read_parquet(io.BytesIO(data))


def upload_bytes(file_system: str, path: str, payload: bytes) -> None:
    svc = get_service_client()
    fs = svc.get_file_system_client(file_system)
    file_client = fs.get_file_client(path)

    if file_client.exists():
        file_client.delete_file()

    file_client.create_file()
    file_client.append_data(data=payload, offset=0, length=len(payload))
    file_client.flush_data(len(payload))


def classify(score: float) -> str:
    if score >= 80:
        return "Critical"
    if score >= 60:
        return "High pressure"
    if score >= 40:
        return "Watchlist"
    return "Stable"


def dominant_driver(row: pd.Series) -> str:
    components = {
        "Population growth": row["population_growth_score"],
        "Affordability": row["rent_pressure_score"],
        "Supply gap": row["supply_gap_score"],
    }
    return max(components, key=components.get)


def build_explanation(row: pd.Series) -> str:
    return (
        f'{row["area_name"]} is classified as {row["classification"]} with an overall score of '
        f'{round(row["overall_housing_pressure_score"], 1)}. '
        f'The dominant driver is {row["dominant_driver"].lower()}, supported by '
        f'population score {round(row["population_growth_score"], 1)}, '
        f'rent score {round(row["rent_pressure_score"], 1)}, and '
        f'supply gap score {round(row["supply_gap_score"], 1)}.'
    )


def load_curated_inputs() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    pop = read_parquet_from_adls(CURATED_FS, POPULATION_CURATED_PATH)
    rents = read_parquet_from_adls(CURATED_FS, RENTS_CURATED_PATH)
    planning = read_parquet_from_adls(CURATED_FS, PLANNING_CURATED_PATH)
    return pop, rents, planning


def _extract_year(period_series: pd.Series) -> pd.Series:
    return (
        period_series.astype(str).str.extract(r"^(\d{4})", expand=False).astype(float)
    )


def _is_quarterly(period_series: pd.Series) -> bool:
    return period_series.astype(str).str.contains(r"Q[1-4]$", regex=True).any()


def _period_index(period_series: pd.Series) -> pd.Series:
    text = period_series.astype(str)
    quarter_match = text.str.extract(r"^(\d{4})Q([1-4])$", expand=True)
    year_only = text.str.extract(r"^(\d{4})$", expand=False)

    idx = pd.Series([pd.NA] * len(text), index=text.index, dtype="object")
    has_q = quarter_match[0].notna() & quarter_match[1].notna()
    idx.loc[has_q] = (
        quarter_match.loc[has_q, 0].astype(int) * 4
        + quarter_match.loc[has_q, 1].astype(int)
    ).astype("Int64")
    has_y = year_only.notna() & ~has_q
    idx.loc[has_y] = (year_only.loc[has_y].astype(int) * 4).astype("Int64")
    return pd.to_numeric(idx, errors="coerce")


def main() -> None:
    pop, rents, planning = load_curated_inputs()

    required_pop = {"area_name", "area_level", "population_growth"}
    required_rents = {"area_name", "area_level", "rent_growth"}
    required_planning = {"area_name", "area_level", "housing_completions"}

    for name, df, required in [
        ("population", pop, required_pop),
        ("rents", rents, required_rents),
        ("planning", planning, required_planning),
    ]:
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"{name} dataset missing required columns: {sorted(missing)}")

    pop_work = pop[["area_name", "area_level", "population_growth", "time_period"]].copy()
    rents_work = rents[["area_name", "area_level", "rent_growth", "time_period"]].copy()
    planning_work = planning[["area_name", "area_level", "housing_completions", "time_period"]].copy()

    pop_work["year"] = _extract_year(pop_work["time_period"])
    rents_work["year"] = _extract_year(rents_work["time_period"])
    planning_work["year"] = _extract_year(planning_work["time_period"])

    df = rents_work.rename(columns={"time_period": "signal_time_period"}).merge(
        pop_work[["area_name", "area_level", "year", "population_growth"]],
        on=["area_name", "area_level", "year"],
        how="inner",
    )

    if _is_quarterly(planning_work["time_period"]):
        planning_quarterly = planning_work.rename(
            columns={"time_period": "signal_time_period"}
        )[
            ["area_name", "area_level", "signal_time_period", "housing_completions"]
        ]
        df = df.merge(
            planning_quarterly,
            on=["area_name", "area_level", "signal_time_period"],
            how="left",
        )
    else:
        planning_latest = (
            planning_work.sort_values(["area_name", "area_level", "year"])
            .dropna(subset=["housing_completions"])
            .groupby(["area_name", "area_level"], as_index=False)
            .tail(1)[["area_name", "area_level", "housing_completions"]]
        )
        df = df.merge(planning_latest, on=["area_name", "area_level"], how="left")

    if df["housing_completions"].isna().any():
        fill = (
            planning_work.sort_values(["area_name", "area_level", "year"])
            .groupby(["area_name", "area_level"], as_index=False)
            .tail(1)[["area_name", "area_level", "housing_completions"]]
            .rename(columns={"housing_completions": "housing_completions_fallback"})
        )
        df = df.merge(fill, on=["area_name", "area_level"], how="left")
        df["housing_completions"] = df["housing_completions"].fillna(
            df["housing_completions_fallback"]
        )
        df = df.drop(columns=["housing_completions_fallback"])

    df["time_period"] = df["signal_time_period"]
    df = df.drop(columns=["signal_time_period", "year"])

    if df.empty:
        raise ValueError("Joined dataset is empty. Check geography keys and curated inputs.")

    df["population_growth_score"] = (
        df.groupby("time_period")["population_growth"]
        .transform(lambda s: minmax_score(s.astype(float)))
        .astype(float)
    )
    df["rent_pressure_score"] = (
        df.groupby("time_period")["rent_growth"]
        .transform(lambda s: minmax_score(s.astype(float)))
        .astype(float)
    )
    df["supply_gap_score"] = 100.0 - (
        df.groupby("time_period")["housing_completions"]
        .transform(lambda s: minmax_score(s.astype(float)))
        .astype(float)
    )

    df["overall_housing_pressure_score"] = (
        df["population_growth_score"] * 0.2
        + df["rent_pressure_score"] * 0.4
        + df["supply_gap_score"] * 0.4
    )

    df["classification"] = df["overall_housing_pressure_score"].apply(classify)
    df["dominant_driver"] = df.apply(dominant_driver, axis=1)
    df["explanation_summary"] = df.apply(build_explanation, axis=1)
    df["time_index"] = _period_index(df["time_period"])

    df = df.sort_values(["area_name", "time_index"])
    df["score_qoq_change"] = df.groupby("area_name")[
        "overall_housing_pressure_score"
    ].diff()
    df["score_4q_avg"] = (
        df.groupby("area_name")["overall_housing_pressure_score"]
        .transform(lambda s: s.rolling(4, min_periods=1).mean())
    )
    df["rent_growth_4q_avg"] = (
        df.groupby("area_name")["rent_growth"]
        .transform(lambda s: s.rolling(4, min_periods=1).mean())
    )
    df["population_growth_4q_avg"] = (
        df.groupby("area_name")["population_growth"]
        .transform(lambda s: s.rolling(4, min_periods=1).mean())
    )
    df["score_rank_in_period"] = (
        df.groupby("time_period")["overall_housing_pressure_score"]
        .rank(ascending=False, method="dense")
        .astype(int)
    )
    df["score_percentile_in_period"] = (
        df.groupby("time_period")["overall_housing_pressure_score"]
        .rank(pct=True)
        .astype(float)
        * 100.0
    )
    df["model_feature_version"] = "v1"

    df = df.sort_values(
        ["time_index", "overall_housing_pressure_score"], ascending=[False, False]
    ).reset_index(drop=True)

    parquet_buffer = io.BytesIO()
    df.to_parquet(parquet_buffer, index=False)
    upload_bytes(
        SIGNALS_FS,
        SIGNALS_FILE_PATH,
        parquet_buffer.getvalue(),
    )

    latest_json = df.to_dict(orient="records")
    upload_bytes(
        SIGNALS_FS,
        SIGNALS_LATEST_JSON_PATH,
        json.dumps(latest_json, ensure_ascii=False, indent=2).encode("utf-8"),
    )

    print(
        f"Wrote {len(df)} signal rows to "
        f"{SIGNALS_FS}/{SIGNALS_FILE_PATH} and {SIGNALS_FS}/{SIGNALS_LATEST_JSON_PATH}"
    )


if __name__ == "__main__":
    main()
