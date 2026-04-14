from __future__ import annotations

from typing import Tuple

import pandas as pd

from etl.common.scoring import minmax_score
from etl.common.storage import StorageBackend, build_storage_backend, utc_now_iso

AREA_LEVEL = "county"

CURATED_FS = "curated"
SIGNALS_FS = "signals"
POPULATION_CURATED_PATH = "population/area_level=county/part-000.parquet"
RENTS_CURATED_PATH = "rents/area_level=county/part-000.parquet"
PLANNING_CURATED_PATH = "planning/area_level=county/part-000.parquet"
SIGNALS_FILE_PATH = "housing_pressure/area_level=county/part-000.parquet"
SIGNALS_CSV_PATH = "housing_pressure/area_level=county/signals.csv"
SIGNALS_LATEST_JSON_PATH = "housing_pressure/latest.json"

MODEL_FEATURE_COLUMNS = [
    "population_growth",
    "rent_growth",
    "housing_completions",
    "population_growth_score",
    "rent_pressure_score",
    "supply_gap_score",
    "overall_housing_pressure_score",
    "score_qoq_change",
    "score_4q_avg",
    "rent_growth_4q_avg",
    "population_growth_4q_avg",
    "score_percentile_in_period",
]

SOURCE_NAME = "CSO and Department of Housing composite housing pressure pipeline"
QUALITY_FLAG = "verified-composite"


def _env(name: str, default: str) -> str:
    import os

    return os.getenv(name, default)


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


def load_curated_inputs(storage: StorageBackend | None = None) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    backend = storage or build_storage_backend()
    pop = backend.read_parquet(
        _env("CURATED_FILE_SYSTEM", CURATED_FS),
        _env("POPULATION_CURATED_PATH", POPULATION_CURATED_PATH),
    )
    rents = backend.read_parquet(
        _env("CURATED_FILE_SYSTEM", CURATED_FS),
        _env("RENTS_CURATED_PATH", RENTS_CURATED_PATH),
    )
    planning = backend.read_parquet(
        _env("CURATED_FILE_SYSTEM", CURATED_FS),
        _env("PLANNING_CURATED_PATH", PLANNING_CURATED_PATH),
    )
    return pop, rents, planning


def _extract_year(period_series: pd.Series) -> pd.Series:
    return period_series.astype(str).str.extract(r"^(\d{4})", expand=False).astype(float)


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


def build_signal_dataframe(
    pop: pd.DataFrame,
    rents: pd.DataFrame,
    planning: pd.DataFrame,
    *,
    published_at: str | None = None,
    data_mode: str = "local",
) -> pd.DataFrame:
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
        planning_quarterly = planning_work.rename(columns={"time_period": "signal_time_period"})[
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
        df["housing_completions"] = df["housing_completions"].fillna(df["housing_completions_fallback"])
        df = df.drop(columns=["housing_completions_fallback"])

    df["time_period"] = df["signal_time_period"]
    df = df.drop(columns=["signal_time_period", "year"])

    if df.empty:
        raise ValueError("Joined dataset is empty. Check geography keys and curated inputs.")

    df["population_growth_score"] = (
        df.groupby("time_period")["population_growth"]
        .transform(lambda series: minmax_score(series.astype(float)))
        .astype(float)
    )
    df["rent_pressure_score"] = (
        df.groupby("time_period")["rent_growth"]
        .transform(lambda series: minmax_score(series.astype(float)))
        .astype(float)
    )
    df["supply_gap_score"] = 100.0 - (
        df.groupby("time_period")["housing_completions"]
        .transform(lambda series: minmax_score(series.astype(float)))
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
    df["score_qoq_change"] = df.groupby("area_name")["overall_housing_pressure_score"].diff()
    df["score_4q_avg"] = (
        df.groupby("area_name")["overall_housing_pressure_score"]
        .transform(lambda series: series.rolling(4, min_periods=1).mean())
    )
    df["rent_growth_4q_avg"] = (
        df.groupby("area_name")["rent_growth"]
        .transform(lambda series: series.rolling(4, min_periods=1).mean())
    )
    df["population_growth_4q_avg"] = (
        df.groupby("area_name")["population_growth"]
        .transform(lambda series: series.rolling(4, min_periods=1).mean())
    )
    df["score_rank_in_period"] = (
        df.groupby("time_period")["overall_housing_pressure_score"]
        .rank(ascending=False, method="dense")
        .astype(int)
    )
    df["score_percentile_in_period"] = (
        df.groupby("time_period")["overall_housing_pressure_score"].rank(pct=True).astype(float) * 100.0
    )
    df["model_feature_version"] = "v1"

    generated_at = published_at or utc_now_iso()
    df["geography_level"] = AREA_LEVEL
    df["coverage_scope"] = "County"
    df["source_name"] = SOURCE_NAME
    df["source_period"] = df["time_period"].astype(str)
    df["published_at"] = generated_at
    df["quality_flag"] = QUALITY_FLAG
    df["data_mode"] = data_mode

    df = df.sort_values(
        ["time_index", "overall_housing_pressure_score"],
        ascending=[False, False],
    ).reset_index(drop=True)

    return df


def publish_signal_outputs(df: pd.DataFrame, storage: StorageBackend | None = None) -> None:
    backend = storage or build_storage_backend()
    file_system = _env("SIGNALS_FILE_SYSTEM", SIGNALS_FS)
    backend.write_parquet(file_system, _env("SIGNALS_FILE_PATH", SIGNALS_FILE_PATH), df)
    backend.write_text(
        file_system,
        _env("SIGNALS_CSV_PATH", SIGNALS_CSV_PATH),
        df.to_csv(index=False),
    )
    backend.write_json(
        file_system,
        _env("SIGNALS_LATEST_JSON_PATH", SIGNALS_LATEST_JSON_PATH),
        df.to_dict(orient="records"),
    )


def run_signal_pipeline(storage: StorageBackend | None = None) -> pd.DataFrame:
    backend = storage or build_storage_backend()
    pop, rents, planning = load_curated_inputs(backend)
    df = build_signal_dataframe(pop, rents, planning, data_mode=backend.data_mode)
    publish_signal_outputs(df, backend)
    return df


def main() -> None:
    df = run_signal_pipeline()
    print(
        f"Wrote {len(df)} signal rows to "
        f"{_env('SIGNALS_FILE_SYSTEM', SIGNALS_FS)}/{_env('SIGNALS_FILE_PATH', SIGNALS_FILE_PATH)}"
    )


if __name__ == "__main__":
    main()
