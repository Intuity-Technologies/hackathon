import os

import pandas as pd

from etl.common.storage import StorageBackend, build_storage_backend

AREA_LEVEL = os.getenv("AREA_LEVEL", "county")
RAW_FS = os.getenv("RAW_FILE_SYSTEM", "raw")
CURATED_FS = os.getenv("CURATED_FILE_SYSTEM", "curated")
POPULATION_SOURCE_PATH = os.getenv(
    "POPULATION_SOURCE_PATH",
    "cso_population/latest/population.csv",
)
POPULATION_CURATED_PATH = os.getenv(
    "POPULATION_CURATED_PATH",
    f"population/area_level={AREA_LEVEL}/part-000.parquet",
)

def load_population_source(
    storage: StorageBackend | None = None,
    *,
    file_system: str = RAW_FS,
    path: str = POPULATION_SOURCE_PATH,
) -> pd.DataFrame:
    backend = storage or build_storage_backend()
    return backend.read_csv(file_system, path)


def normalize_population_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    cols = set(df.columns)
    inferred_time_period = str(os.getenv("POPULATION_TIME_PERIOD", "2022"))

    if {"County", "Year", "Age Group", "Sex", "VALUE"}.issubset(cols):
        out = df.copy()
        out["County"] = out["County"].astype(str).str.strip()
        out["Age Group"] = out["Age Group"].astype(str).str.strip()
        out["Sex"] = out["Sex"].astype(str).str.strip()
        out["VALUE"] = pd.to_numeric(out["VALUE"], errors="coerce")
        out["Year"] = pd.to_numeric(out["Year"], errors="coerce")

        out = out[
            (out["Age Group"].str.lower() == "all ages")
            & (out["Sex"].str.lower() == "both sexes")
            & out["VALUE"].notna()
            & out["Year"].notna()
        ].copy()
        out["County"] = out["County"].str.replace("^Co\\.\\s*", "", regex=True)
        out = out[~out["County"].str.lower().isin({"ireland", "state", "all"})]

        out = (
            out[["County", "Year", "VALUE"]]
            .rename(columns={"County": "area_name", "Year": "year", "VALUE": "population_value"})
            .drop_duplicates(subset=["area_name", "year"], keep="last")
            .sort_values(["area_name", "year"])
        )
        out["previous_value"] = out.groupby("area_name")["population_value"].shift(1)
        out = out[out["previous_value"].notna() & (out["previous_value"] != 0)].copy()
        out["population_growth"] = (
            (out["population_value"] - out["previous_value"]) / out["previous_value"]
        ) * 100.0
        out["time_period"] = out["year"].astype(int).astype(str)
        out = out[["area_name", "population_growth", "time_period"]]
    elif {"County", "PopulationGrowth"}.issubset(cols):
        out = df.rename(columns={"County": "area_name", "PopulationGrowth": "population_growth"})
    elif {"County", "Population"}.issubset(cols):
        out = df.rename(columns={"County": "area_name", "Population": "population_growth"})
    elif {"GEOGDESC", "T1_1AGETT"}.issubset(cols):
        # Census county extracts provide point-in-time totals; use this as pressure proxy.
        out = df.rename(columns={"GEOGDESC": "area_name", "T1_1AGETT": "population_growth"})
    else:
        raise ValueError(
            "Population source is missing supported headers. "
            "Expected one of: "
            "{County, Year, Age Group, Sex, VALUE}, "
            "{County, PopulationGrowth}, {County, Population}, {GEOGDESC, T1_1AGETT}."
        )

    keep_cols = ["area_name", "population_growth"]
    if "time_period" in out.columns:
        keep_cols.append("time_period")
    out = out[keep_cols].copy()
    out["area_name"] = out["area_name"].astype(str).str.strip()
    out["population_growth"] = pd.to_numeric(out["population_growth"], errors="coerce")
    out["area_name"] = out["area_name"].str.replace("^Co\\.\\s*", "", regex=True)
    out = out[~out["area_name"].str.lower().isin({"ireland", "state", "all"})]
    out = out.dropna(subset=["area_name", "population_growth"])
    out["area_level"] = "county"
    if "time_period" not in out.columns:
        out["time_period"] = inferred_time_period
    return out


def publish_population_dataframe(
    df: pd.DataFrame,
    storage: StorageBackend | None = None,
    *,
    file_system: str = CURATED_FS,
    path: str = POPULATION_CURATED_PATH,
) -> None:
    backend = storage or build_storage_backend()
    backend.write_parquet(file_system, path, df)


def run_population_pipeline(storage: StorageBackend | None = None) -> pd.DataFrame:
    backend = storage or build_storage_backend()
    source_df = load_population_source(backend)
    normalized = normalize_population_dataframe(source_df)
    publish_population_dataframe(normalized, backend)
    return normalized


def main() -> None:
    normalized = run_population_pipeline()
    print(f"Normalized {len(normalized)} population rows")


if __name__ == "__main__":
    main()
