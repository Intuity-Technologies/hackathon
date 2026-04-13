from __future__ import annotations

import json
import os
from urllib.parse import unquote

import azure.functions as func
import pandas as pd

from etl.common.storage import build_storage_backend
from etl.transform.build_signals import MODEL_FEATURE_COLUMNS
from service.housing_data import (
    build_compare_from_query,
    compare_areas,
    get_area_detail,
    get_area_trends,
    get_leaderboard,
    get_overview,
    get_sources_manifest,
    list_available_areas,
)

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


def _json_response(payload: dict | list, status_code: int = 200) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps(payload, ensure_ascii=False),
        mimetype="application/json",
        status_code=status_code,
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
        return str(df.loc[idx.idxmax(), "time_period"])
    return str(df["time_period"].astype(str).max())


def load_signal_dataframe() -> pd.DataFrame:
    storage = build_storage_backend()
    return storage.read_parquet(
        os.getenv("SIGNALS_FILE_SYSTEM", "signals"),
        os.getenv("SIGNALS_FILE_PATH", "housing_pressure/area_level=county/part-000.parquet"),
    )


@app.route(route="health", methods=["GET"])
def health(req: func.HttpRequest) -> func.HttpResponse:
    del req
    overview = get_overview()
    return _json_response(
        {
            "status": "ok",
            "runtime_mode": overview["freshness"]["runtime_mode"],
            "data_mode": overview["freshness"]["data_mode"],
            "latest_period": overview["freshness"]["latest_period"],
            "published_at": overview["freshness"]["published_at"],
            "counties_covered": overview["summary"]["counties_covered"],
        }
    )


@app.route(route="areas", methods=["GET"])
def areas(req: func.HttpRequest) -> func.HttpResponse:
    del req
    leaderboard = get_leaderboard()
    return _json_response(leaderboard["rows"])


@app.route(route="overview", methods=["GET"])
def overview(req: func.HttpRequest) -> func.HttpResponse:
    del req
    return _json_response(get_overview())


@app.route(route="sources", methods=["GET"])
def sources(req: func.HttpRequest) -> func.HttpResponse:
    del req
    return _json_response(get_sources_manifest())


@app.route(route="area/{name}", methods=["GET"])
def area(req: func.HttpRequest) -> func.HttpResponse:
    requested_name = unquote(req.route_params.get("name", "")).strip()
    payload = get_area_detail(requested_name)
    if payload is None:
        return _json_response({"error": f'Area "{requested_name}" not found'}, status_code=404)
    return _json_response(payload)


@app.route(route="trends/{name}", methods=["GET"])
def trends(req: func.HttpRequest) -> func.HttpResponse:
    requested_name = unquote(req.route_params.get("name", "")).strip()
    payload = get_area_trends(requested_name)
    if payload is None:
        return _json_response({"error": f'Area "{requested_name}" not found'}, status_code=404)
    return _json_response(payload)


@app.route(route="compare", methods=["GET"])
def compare(req: func.HttpRequest) -> func.HttpResponse:
    raw = (req.params.get("areas") or "").strip()
    names = build_compare_from_query(raw)
    try:
        payload = compare_areas(names)
    except ValueError as exc:
        return _json_response({"error": str(exc), "available_areas": list_available_areas()}, status_code=400)
    return _json_response(payload)


@app.route(route="model/schema", methods=["GET"])
def model_schema(req: func.HttpRequest) -> func.HttpResponse:
    del req
    body = {
        "feature_columns": MODEL_FEATURE_COLUMNS,
        "id_columns": ["area_name", "area_level", "time_period"],
        "target_column": "overall_housing_pressure_score",
    }
    return _json_response(body)


@app.route(route="model/features", methods=["GET"])
def model_features(req: func.HttpRequest) -> func.HttpResponse:
    df = load_signal_dataframe()
    requested_period = (req.params.get("time_period") or "").strip()
    if requested_period:
        df = df[df["time_period"].astype(str) == requested_period].copy()
    else:
        latest_period = _latest_period(df)
        if latest_period is not None:
            df = df[df["time_period"].astype(str) == latest_period].copy()

    keep = ["area_name", "area_level", "time_period"] + [
        column for column in MODEL_FEATURE_COLUMNS if column in df.columns
    ]
    payload = df[keep].copy()
    for column in MODEL_FEATURE_COLUMNS:
        if column in payload.columns:
            payload[column] = pd.to_numeric(payload[column], errors="coerce")
    payload = payload.replace({pd.NA: None}).where(pd.notnull(payload), None)
    return _json_response(payload.to_dict(orient="records"))
