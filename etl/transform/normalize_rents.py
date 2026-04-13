import io
import os

import pandas as pd
from azure.identity import DefaultAzureCredential
from azure.storage.filedatalake import DataLakeServiceClient

AREA_LEVEL = os.getenv("AREA_LEVEL", "county")
RAW_FS = os.getenv("RAW_FILE_SYSTEM", "raw")
CURATED_FS = os.getenv("CURATED_FILE_SYSTEM", "curated")
RENTS_SOURCE_PATH = os.getenv(
    "RENTS_SOURCE_PATH",
    "rents/latest/rents.csv",
)
RENTS_CURATED_PATH = os.getenv(
    "RENTS_CURATED_PATH",
    f"rents/area_level={AREA_LEVEL}/part-000.parquet",
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
    return _download_csv(RAW_FS, RENTS_SOURCE_PATH)


def _normalize_rent_headers(df: pd.DataFrame) -> pd.DataFrame:
    cols = set(df.columns)
    inferred_time_period = str(os.getenv("RENTS_TIME_PERIOD", "2024"))

    if {"Location", "Quarter", "Number of Bedrooms", "Property Type", "VALUE"}.issubset(cols):
        out = df.copy()
        out["Location"] = out["Location"].astype(str).str.strip()
        out["Quarter"] = out["Quarter"].astype(str).str.strip()
        out["Number of Bedrooms"] = out["Number of Bedrooms"].astype(str).str.strip()
        out["Property Type"] = out["Property Type"].astype(str).str.strip()
        out["VALUE"] = pd.to_numeric(out["VALUE"], errors="coerce")

        county_names = {
            "Carlow", "Cavan", "Clare", "Cork", "Donegal", "Dublin", "Galway",
            "Kerry", "Kildare", "Kilkenny", "Laois", "Leitrim", "Limerick",
            "Longford", "Louth", "Mayo", "Meath", "Monaghan", "Offaly",
            "Roscommon", "Sligo", "Tipperary", "Waterford", "Westmeath",
            "Wexford", "Wicklow",
        }

        out = out[
            (out["Number of Bedrooms"].str.lower() == "all bedrooms")
            & (out["Property Type"].str.lower() == "all property types")
            & out["Location"].isin(county_names)
            & out["VALUE"].notna()
        ].copy()

        out["year"] = pd.to_numeric(out["Quarter"].str.slice(0, 4), errors="coerce")
        out["q"] = pd.to_numeric(
            out["Quarter"].str.extract(r"Q([1-4])", expand=False), errors="coerce"
        )
        out = out.dropna(subset=["year", "q"]).copy()
        out["period_index"] = (out["year"].astype(int) * 4) + out["q"].astype(int)
        out = (
            out[["Location", "Quarter", "VALUE", "period_index"]]
            .rename(
                columns={
                    "Location": "area_name",
                    "Quarter": "time_period",
                    "VALUE": "rent_value",
                }
            )
            .drop_duplicates(subset=["area_name", "time_period"], keep="last")
            .sort_values(["area_name", "period_index"])
        )
        out["previous_value"] = out.groupby("area_name")["rent_value"].shift(4)
        out = out[out["previous_value"].notna() & (out["previous_value"] != 0)].copy()
        out["rent_growth"] = ((out["rent_value"] - out["previous_value"]) / out["previous_value"]) * 100.0
        out = out[["area_name", "rent_growth", "time_period"]]
    elif {"County", "RentGrowth"}.issubset(cols):
        out = df.rename(columns={"County": "area_name", "RentGrowth": "rent_growth"})
    elif {"GEOGDESC", "T6_3_RPLH", "T6_3_TH"}.issubset(cols):
        # Proxy: share of private-rented households by county.
        out = df.rename(columns={"GEOGDESC": "area_name"}).copy()
        rent_private = pd.to_numeric(out["T6_3_RPLH"], errors="coerce")
        rent_total = pd.to_numeric(out["T6_3_TH"], errors="coerce").replace(0, pd.NA)
        out["rent_growth"] = (rent_private / rent_total) * 100.0
    else:
        raise ValueError(
            "Rents source is missing supported headers. "
            "Expected one of: {Location, Quarter, Number of Bedrooms, Property Type, VALUE}, "
            "{County, RentGrowth}, {GEOGDESC, T6_3_RPLH, T6_3_TH}."
        )

    keep_cols = ["area_name", "rent_growth"]
    if "time_period" in out.columns:
        keep_cols.append("time_period")
    out = out[keep_cols].copy()
    out["area_name"] = out["area_name"].astype(str).str.strip()
    out["rent_growth"] = pd.to_numeric(out["rent_growth"], errors="coerce")
    out = out[~out["area_name"].str.lower().isin({"ireland", "state", "all"})]
    out = out.dropna(subset=["area_name", "rent_growth"])
    out["area_level"] = "county"
    if "time_period" not in out.columns:
        out["time_period"] = inferred_time_period
    return out


def _write_curated(df: pd.DataFrame) -> None:
    svc = _get_service_client()
    curated_fs = svc.get_file_system_client(CURATED_FS)

    parquet_buffer = io.BytesIO()
    df.to_parquet(parquet_buffer, index=False)

    out = curated_fs.get_file_client(RENTS_CURATED_PATH)
    payload = parquet_buffer.getvalue()
    if out.exists():
        out.delete_file()
    out.create_file()
    out.append_data(payload, 0, len(payload))
    out.flush_data(len(payload))


def main() -> None:
    df = _load_source_dataframe()
    normalized = _normalize_rent_headers(df)
    _write_curated(normalized)


if __name__ == "__main__":
    main()
