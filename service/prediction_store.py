import json
import os
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests

DEFAULT_LOCAL_SIGNALS_PATH = "data/signals/housing_pressure/latest.json"


def _to_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _api_base_url() -> str | None:
    for key in ("PREDICTION_API_BASE_URL", "NEXT_PUBLIC_API_BASE_URL"):
        value = os.getenv(key, "").strip()
        if value:
            return value.rstrip("/")
    return None


def _load_local_signal_rows() -> list[dict[str, Any]]:
    configured_path = os.getenv("SIGNALS_LOCAL_JSON_PATH", DEFAULT_LOCAL_SIGNALS_PATH)
    path = Path(configured_path)
    if not path.is_absolute():
        path = Path(__file__).resolve().parents[1] / configured_path
    if not path.exists():
        return []

    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def _fetch_area_record(city: str) -> tuple[dict[str, Any] | None, str | None]:
    base_url = _api_base_url()
    if base_url:
        url = f"{base_url}/api/area/{quote(city)}"
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                payload = response.json()
                if isinstance(payload, dict):
                    return payload, "azure-functions-api"
            elif response.status_code not in {400, 404}:
                response.raise_for_status()
        except (requests.RequestException, ValueError):
            pass

    normalized_city = city.strip().lower()
    for row in _load_local_signal_rows():
        area = str(row.get("area_name", "")).strip().lower()
        if area == normalized_city:
            return row, "local-snapshot"

    return None, None


def _lookup_housing_pressure(row: dict[str, Any], source: str) -> dict[str, Any]:
    return {
        "prediction_type": "housing_pressure",
        "city": row.get("area_name"),
        "time_period": row.get("time_period"),
        "overall_housing_pressure_score": _to_float(
            row.get("overall_housing_pressure_score")
        ),
        "classification": row.get("classification"),
        "dominant_driver": row.get("dominant_driver"),
        "explanation_summary": row.get("explanation_summary"),
        "source": source,
    }


def _lookup_rent_pressure(row: dict[str, Any], source: str) -> dict[str, Any]:
    rent_growth = _to_float(row.get("rent_growth_4q_avg"))
    if rent_growth is None:
        rent_growth = _to_float(row.get("rent_growth"))

    return {
        "prediction_type": "rent_pressure",
        "city": row.get("area_name"),
        "time_period": row.get("time_period"),
        "rent_growth": rent_growth,
        "classification": row.get("classification"),
        "source": source,
    }


def _lookup_population_density(row: dict[str, Any], source: str) -> dict[str, Any]:
    population_growth = _to_float(row.get("population_growth_4q_avg"))
    if population_growth is None:
        population_growth = _to_float(row.get("population_growth"))

    return {
        "prediction_type": "population_density",
        "city": row.get("area_name"),
        "time_period": row.get("time_period"),
        "population_growth": population_growth,
        "classification": row.get("classification"),
        "source": source,
    }


def _lookup_homelessness(row: dict[str, Any], source: str) -> dict[str, Any]:
    return {
        "prediction_type": "homelessness",
        "city": row.get("area_name"),
        "time_period": row.get("time_period"),
        "classification": row.get("classification"),
        "dominant_driver": row.get("dominant_driver"),
        "explanation_summary": row.get("explanation_summary"),
        "source": source,
    }


def lookup_prediction(
    city: str | None, prediction_type: str | None, horizon_months: int | None = None
) -> dict[str, Any] | None:
    del horizon_months  # Reserved for future model-backed forecasts.

    if not city or not prediction_type:
        return None

    row, source = _fetch_area_record(city)
    if not row or not source:
        return None

    if prediction_type == "housing_pressure":
        return _lookup_housing_pressure(row, source)
    if prediction_type == "rent_pressure":
        return _lookup_rent_pressure(row, source)
    if prediction_type == "population_density":
        return _lookup_population_density(row, source)
    if prediction_type == "homelessness":
        return _lookup_homelessness(row, source)

    return None
