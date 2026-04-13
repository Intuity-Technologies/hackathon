import io
import os

import pandas as pd
from azure.identity import DefaultAzureCredential
from azure.storage.filedatalake import DataLakeServiceClient

AREA_LEVEL = os.getenv("AREA_LEVEL", "county")
RAW_FS = os.getenv("RAW_FILE_SYSTEM", "raw")
CURATED_FS = os.getenv("CURATED_FILE_SYSTEM", "curated")
PLANNING_SOURCE_PATH = os.getenv(
    "PLANNING_SOURCE_PATH",
    "planning/latest/planning.csv",
)
PLANNING_WEIGHTS_SOURCE_PATH = os.getenv("PLANNING_WEIGHTS_SOURCE_PATH", "").strip()
PLANNING_CURATED_PATH = os.getenv(
    "PLANNING_CURATED_PATH",
    f"planning/area_level={AREA_LEVEL}/part-000.parquet",
)

COUNTY_NAMES = {
    "Carlow",
    "Cavan",
    "Clare",
    "Cork",
    "Donegal",
    "Dublin",
    "Galway",
    "Kerry",
    "Kildare",
    "Kilkenny",
    "Laois",
    "Leitrim",
    "Limerick",
    "Longford",
    "Louth",
    "Mayo",
    "Meath",
    "Monaghan",
    "Offaly",
    "Roscommon",
    "Sligo",
    "Tipperary",
    "Waterford",
    "Westmeath",
    "Wexford",
    "Wicklow",
}

COUNTY_CODE_MAP = {
    "CW": "Carlow",
    "CN": "Cavan",
    "CE": "Clare",
    "CC": "Cork",
    "CK": "Cork",
    "DL": "Donegal",
    "DC": "Dublin",
    "DR": "Dublin",
    "FL": "Dublin",
    "SD": "Dublin",
    "GC": "Galway",
    "KY": "Kerry",
    "KE": "Kildare",
    "KK": "Kilkenny",
    "LS": "Laois",
    "LM": "Leitrim",
    "LK": "Limerick",
    "LD": "Longford",
    "LH": "Louth",
    "MO": "Mayo",
    "MH": "Meath",
    "MN": "Monaghan",
    "OY": "Offaly",
    "RN": "Roscommon",
    "SO": "Sligo",
    "TY": "Tipperary",
    "WD": "Waterford",
    "WH": "Westmeath",
    "WX": "Wexford",
    "WW": "Wicklow",
    "GY": "Galway",
}


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


def _is_true(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _normalize_county_name(value: str) -> str:
    text = str(value).strip()
    text = text.replace("Co. ", "").replace("County ", "")
    text = text.replace(" City and County", "").replace(" County", "").replace(" City", "")
    text = text.replace("Dun-Laoghaire Rathdown", "Dublin").replace(
        "Dun Laoghaire-Rathdown", "Dublin"
    )
    text = text.replace("South Dublin", "Dublin").replace("Fingal", "Dublin")
    text = text.replace("Galway County", "Galway").replace("Galway City", "Galway")
    text = text.replace("Cork County", "Cork").replace("Cork City", "Cork")
    text = text.replace("Waterford City and County", "Waterford")
    text = text.replace("Limerick City and County", "Limerick")
    text = text.replace("All", "").strip()
    return text


def _strict_mode_for_source(source_name: str) -> bool:
    mode = os.getenv("PLANNING_STRICT_COUNTY_ONLY", "auto").strip().lower()
    if mode in {"false", "0", "off", "no"}:
        return False
    if _is_true(mode):
        return True
    auto_markers = ("NDQ05", "NDQ06", "BHQ17", "BHA14")
    return any(marker in source_name.upper() for marker in auto_markers)


def _load_source_dataframe() -> tuple[pd.DataFrame, str]:
    source_name = PLANNING_SOURCE_PATH.rsplit("/", 1)[-1]
    return _download_csv(RAW_FS, PLANNING_SOURCE_PATH), source_name


def _county_weights_from_proxy() -> pd.DataFrame:
    if PLANNING_WEIGHTS_SOURCE_PATH:
        base = _download_csv(RAW_FS, PLANNING_WEIGHTS_SOURCE_PATH)
        if {"GEOGDESC", "T6_2_16LH", "T6_2_TH"}.issubset(set(base.columns)):
            base = base.rename(columns={"GEOGDESC": "area_name"}).copy()
            base["area_name"] = base["area_name"].astype(str).str.strip().replace(COUNTY_CODE_MAP)
            recent_stock = pd.to_numeric(base["T6_2_16LH"], errors="coerce")
            total_stock = pd.to_numeric(base["T6_2_TH"], errors="coerce").replace(0, pd.NA)
            base["weight_raw"] = recent_stock / total_stock
            base = base[["area_name", "weight_raw"]]
            base = base[~base["area_name"].str.lower().isin({"ireland", "state", "all"})]
            base = base.dropna(subset=["area_name", "weight_raw"])
            base = base.groupby("area_name", as_index=False)["weight_raw"].mean()
            total = base["weight_raw"].sum()
            if total > 0:
                base["weight"] = base["weight_raw"] / total
                return base[["area_name", "weight"]]

    # Last-resort equal weighting across known counties.
    weights = pd.DataFrame({"area_name": sorted(COUNTY_NAMES)})
    weights["weight"] = 1.0 / len(weights)
    return weights


def _normalize_planning_headers(df: pd.DataFrame, source_name: str) -> pd.DataFrame:
    cols = set(df.columns)
    strict_mode = _strict_mode_for_source(source_name)

    area_col = None
    for candidate in ["Local Authority", "County", "Location"]:
        if candidate in cols:
            area_col = candidate
            break

    if {"Quarter", "VALUE"}.issubset(cols) and area_col:
        out = df.copy()
        out["Quarter"] = out["Quarter"].astype(str).str.strip()
        out[area_col] = out[area_col].astype(str).str.strip()
        out["area_name"] = out[area_col].map(_normalize_county_name)
        out["VALUE"] = pd.to_numeric(
            out["VALUE"].astype(str).str.replace(",", "", regex=False), errors="coerce"
        )
        if "Type of House" in out.columns:
            out["Type of House"] = out["Type of House"].astype(str).str.strip()
            out = out[
                (out["Type of House"].str.lower() == "all house types")
                & out["VALUE"].notna()
            ]
        else:
            out = out[out["VALUE"].notna()]
        out = out[out["area_name"].isin(COUNTY_NAMES)]

        if out.empty and strict_mode:
            raise ValueError(
                f"Strict county planning mode enabled, but {source_name} did not map to county rows."
            )

        out = (
            out.groupby(["area_name", "Quarter"], as_index=False)["VALUE"]
            .sum()
            .rename(columns={"Quarter": "time_period", "VALUE": "housing_completions"})
        )
    elif {"Quarter", "Type of House", "VALUE"}.issubset(cols):
        if strict_mode:
            raise ValueError(
                f"Strict county planning mode enabled. {source_name} appears national-only "
                "and cannot be used with weighted fallback."
            )
        out = df.copy()
        out["Quarter"] = out["Quarter"].astype(str).str.strip()
        out["Type of House"] = out["Type of House"].astype(str).str.strip()
        out["VALUE"] = pd.to_numeric(
            out["VALUE"].astype(str).str.replace(",", "", regex=False), errors="coerce"
        )
        out = out[
            (out["Type of House"].str.lower() == "all house types")
            & out["VALUE"].notna()
        ][["Quarter", "VALUE"]]
        out = out.groupby("Quarter", as_index=False)["VALUE"].sum()
        weights = _county_weights_from_proxy()
        out["key"] = 1
        weights["key"] = 1
        out = out.merge(weights, on="key", how="inner").drop(columns=["key"])
        out["housing_completions"] = out["VALUE"] * out["weight"]
        out = out.rename(columns={"Quarter": "time_period"})
        out = out[["area_name", "housing_completions", "time_period"]]
    elif {"County", "HousingCompletions"}.issubset(cols):
        out = df.rename(columns={"County": "area_name", "HousingCompletions": "housing_completions"})
        out["area_name"] = out["area_name"].map(_normalize_county_name)
    elif {"GEOGDESC", "T6_2_16LH", "T6_2_TH"}.issubset(cols):
        if strict_mode:
            raise ValueError(
                f"Strict county planning mode enabled. {source_name} is a proxy source and not a "
                "direct county completions/planning table."
            )
        # Proxy: recent housing stock share (built since 2016) by county.
        out = df.rename(columns={"GEOGDESC": "area_name"}).copy()
        out["area_name"] = out["area_name"].astype(str).str.strip().replace(COUNTY_CODE_MAP)
        recent_stock = pd.to_numeric(out["T6_2_16LH"], errors="coerce")
        total_stock = pd.to_numeric(out["T6_2_TH"], errors="coerce").replace(0, pd.NA)
        out["housing_completions"] = (recent_stock / total_stock) * 100.0
    else:
        raise ValueError(
            "Planning source is missing supported headers. "
            "Expected one of: {County, HousingCompletions}, {GEOGDESC, T6_2_16LH, T6_2_TH}."
        )

    keep_cols = ["area_name", "housing_completions"]
    if "time_period" in out.columns:
        keep_cols.append("time_period")
    out = out[keep_cols].copy()
    out["area_name"] = out["area_name"].astype(str).str.strip()
    out["housing_completions"] = pd.to_numeric(out["housing_completions"], errors="coerce")
    out = out[~out["area_name"].str.lower().isin({"ireland", "state", "all"})]
    out = out.dropna(subset=["area_name", "housing_completions"])
    if "time_period" in out.columns:
        out = (
            out.groupby(["area_name", "time_period"], as_index=False)["housing_completions"]
            .mean()
            .copy()
        )
    else:
        out = (
            out.groupby("area_name", as_index=False)["housing_completions"]
            .mean()
            .copy()
        )
    out["area_level"] = "county"
    if "time_period" not in out.columns:
        out["time_period"] = str(os.getenv("PLANNING_TIME_PERIOD", "2024"))
    return out


def _write_curated(df: pd.DataFrame) -> None:
    svc = _get_service_client()
    curated_fs = svc.get_file_system_client(CURATED_FS)

    parquet_buffer = io.BytesIO()
    df.to_parquet(parquet_buffer, index=False)

    out = curated_fs.get_file_client(PLANNING_CURATED_PATH)
    payload = parquet_buffer.getvalue()
    if out.exists():
        out.delete_file()
    out.create_file()
    out.append_data(payload, 0, len(payload))
    out.flush_data(len(payload))


def main() -> None:
    df, source_name = _load_source_dataframe()
    normalized = _normalize_planning_headers(df, source_name)
    _write_curated(normalized)


if __name__ == "__main__":
    main()
