import io
import os

import pandas as pd
from azure.identity import DefaultAzureCredential
from azure.storage.filedatalake import DataLakeServiceClient

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


def _get_service_client() -> DataLakeServiceClient:
    account = os.getenv("AZURE_STORAGE_ACCOUNT", "").strip()
    if not account:
        raise ValueError("AZURE_STORAGE_ACCOUNT env var not set")
    return DataLakeServiceClient(
        account_url=f"https://{account}.dfs.core.windows.net",
        credential=DefaultAzureCredential(),
    )


def _download_csv(file_system: str, path: str) -> pd.DataFrame:
    svc = _get_service_client()
    fs = svc.get_file_system_client(file_system)
    file_client = fs.get_file_client(path)
    data = file_client.download_file().readall()
    return pd.read_csv(io.BytesIO(data))


def _load_source_dataframe() -> pd.DataFrame:
    return _download_csv(RAW_FS, POPULATION_SOURCE_PATH)


def _normalize_population_headers(df: pd.DataFrame) -> pd.DataFrame:
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


def _write_curated(df: pd.DataFrame) -> None:
    svc = _get_service_client()
    curated_fs = svc.get_file_system_client(CURATED_FS)

    parquet_buffer = io.BytesIO()
    df.to_parquet(parquet_buffer, index=False)

    out = curated_fs.get_file_client(POPULATION_CURATED_PATH)
    payload = parquet_buffer.getvalue()
    if out.exists():
        out.delete_file()
    out.create_file()
    out.append_data(payload, 0, len(payload))
    out.flush_data(len(payload))


def main() -> None:
    df = _load_source_dataframe()
    normalized = _normalize_population_headers(df)
    _write_curated(normalized)


if __name__ == "__main__":
    main()
