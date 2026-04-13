import io
import json
import os
from urllib.parse import unquote

import azure.functions as func
import pandas as pd
from azure.identity import DefaultAzureCredential
from azure.storage.filedatalake import DataLakeServiceClient

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)
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


def get_service_client() -> DataLakeServiceClient:
    storage_account = os.environ["AZURE_STORAGE_ACCOUNT"]
    return DataLakeServiceClient(
        account_url=f"https://{storage_account}.dfs.core.windows.net",
        credential=DefaultAzureCredential(),
    )


def _period_index(period_series: pd.Series) -> pd.Series:
    text = period_series.astype(str)
    quarter = text.str.extract(r"^(\d{4})Q([1-4])$", expand=True)
    year = text.str.extract(r"^(\d{4})$", expand=False)
    out = pd.Series([float("nan")] * len(text), index=text.index)
    has_q = quarter[0].notna() & quarter[1].notna()
    out.loc[has_q] = (
        quarter.loc[has_q, 0].astype(float) * 4.0 + quarter.loc[has_q, 1].astype(float)
    )
    has_y = year.notna() & ~has_q
    out.loc[has_y] = year.loc[has_y].astype(float) * 4.0
    return out


def _latest_period(df: pd.DataFrame) -> str | None:
    if "time_period" not in df.columns or df.empty:
        return None
    idx = _period_index(df["time_period"])
    if idx.notna().any():
        return df.loc[idx.idxmax(), "time_period"]
    return df["time_period"].astype(str).max()


def _json_safe(value):
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


def load_latest_signals() -> pd.DataFrame:
    storage_account = os.getenv("AZURE_STORAGE_ACCOUNT", "").strip()
    if not storage_account:
        raise ValueError(
            "AZURE_STORAGE_ACCOUNT env var not set. "
            "Configure blob storage settings for API signal loading."
        )

    fs_name = os.getenv("SIGNALS_FILE_SYSTEM", "signals")
    file_path = os.getenv(
        "SIGNALS_FILE_PATH",
        "housing_pressure/area_level=county/part-000.parquet",
    )
    svc = get_service_client()
    fs = svc.get_file_system_client(fs_name)
    file_client = fs.get_file_client(file_path)
    data = file_client.download_file().readall()
    return pd.read_parquet(io.BytesIO(data))


@app.route(route="health", methods=["GET"])
def health(req: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps({"status": "ok"}),
        mimetype="application/json",
        status_code=200,
    )


@app.route(route="areas", methods=["GET"])
def areas(req: func.HttpRequest) -> func.HttpResponse:
    try:
        df = load_latest_signals()
        latest_period = _latest_period(df)
        if latest_period is not None and "time_period" in df.columns:
            df = df[df["time_period"].astype(str) == str(latest_period)].copy()
        columns = [
            "area_name",
            "area_level",
            "time_period",
            "overall_housing_pressure_score",
            "classification",
            "dominant_driver",
        ]
        payload = df[[c for c in columns if c in df.columns]].copy()
        if "overall_housing_pressure_score" in payload.columns:
            payload["overall_housing_pressure_score"] = payload[
                "overall_housing_pressure_score"
            ].round(2)

        return func.HttpResponse(
            payload.to_json(orient="records"),
            mimetype="application/json",
            status_code=200,
        )
    except Exception as ex:
        return func.HttpResponse(
            json.dumps({"error": str(ex)}),
            mimetype="application/json",
            status_code=500,
        )


@app.route(route="area/{name}", methods=["GET"])
def area(req: func.HttpRequest) -> func.HttpResponse:
    try:
        requested_name = unquote(req.route_params.get("name", "")).strip().lower()
        df = load_latest_signals()
        latest_period = _latest_period(df)
        if latest_period is not None and "time_period" in df.columns:
            df = df[df["time_period"].astype(str) == str(latest_period)].copy()

        if "area_name" not in df.columns:
            return func.HttpResponse(
                json.dumps({"error": "Signal table missing area_name column"}),
                mimetype="application/json",
                status_code=500,
            )

        normalized = df["area_name"].astype(str).str.strip().str.lower()
        match = df[normalized == requested_name]
        if match.empty:
            return func.HttpResponse(
                json.dumps({"error": f'Area "{requested_name}" not found'}),
                mimetype="application/json",
                status_code=404,
            )

        row = {k: _json_safe(v) for k, v in match.iloc[0].to_dict().items()}

        return func.HttpResponse(
            json.dumps(row, ensure_ascii=False),
            mimetype="application/json",
            status_code=200,
        )
    except Exception as ex:
        return func.HttpResponse(
            json.dumps({"error": str(ex)}),
            mimetype="application/json",
            status_code=500,
        )


@app.route(route="model/schema", methods=["GET"])
def model_schema(req: func.HttpRequest) -> func.HttpResponse:
    body = {
        "feature_columns": MODEL_FEATURE_COLUMNS,
        "id_columns": ["area_name", "area_level", "time_period"],
        "target_column": "overall_housing_pressure_score",
    }
    return func.HttpResponse(json.dumps(body), mimetype="application/json", status_code=200)


@app.route(route="model/features", methods=["GET"])
def model_features(req: func.HttpRequest) -> func.HttpResponse:
    try:
        df = load_latest_signals()
        requested_period = (req.params.get("time_period") or "").strip()
        if requested_period:
            df = df[df["time_period"].astype(str) == requested_period].copy()
        else:
            latest_period = _latest_period(df)
            if latest_period is not None and "time_period" in df.columns:
                df = df[df["time_period"].astype(str) == str(latest_period)].copy()

        keep = ["area_name", "area_level", "time_period"] + [
            c for c in MODEL_FEATURE_COLUMNS if c in df.columns
        ]
        payload = df[keep].copy()
        for col in MODEL_FEATURE_COLUMNS:
            if col in payload.columns:
                payload[col] = pd.to_numeric(payload[col], errors="coerce")
        payload = payload.replace({pd.NA: None}).where(pd.notnull(payload), None)

        return func.HttpResponse(
            payload.to_json(orient="records"),
            mimetype="application/json",
            status_code=200,
        )
    except Exception as ex:
        return func.HttpResponse(
            json.dumps({"error": str(ex)}),
            mimetype="application/json",
            status_code=500,
        )
