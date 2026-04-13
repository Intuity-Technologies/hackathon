from __future__ import annotations

import json

import azure.functions as func

from api.function_app import area, compare, health, overview
from service.orchestrator import answer


def _request(
    *,
    url: str,
    params: dict[str, str] | None = None,
    route_params: dict[str, str] | None = None,
) -> func.HttpRequest:
    return func.HttpRequest(
        method="GET",
        url=url,
        params=params or {},
        route_params=route_params or {},
        body=b"",
    )


def test_orchestrator_handles_housing_pressure_area_query() -> None:
    text = answer("What is the latest housing pressure classification for Mayo?")
    assert "Mayo" in text
    assert "Critical" in text


def test_orchestrator_handles_compare_query() -> None:
    text = answer("Compare Cork and Galway for affordable housing pressure.")
    assert "Cork" in text
    assert "Galway" in text
    assert "Metric leaders" in text


def test_health_endpoint_returns_runtime_metadata() -> None:
    response = health(_request(url="/api/health"))
    payload = json.loads(response.get_body())

    assert payload["status"] == "ok"
    assert payload["latest_period"] == "2025Q3"


def test_overview_and_area_endpoints_return_structured_payloads() -> None:
    overview_response = overview(_request(url="/api/overview"))
    overview_payload = json.loads(overview_response.get_body())
    area_response = area(_request(url="/api/area/Mayo", route_params={"name": "Mayo"}))
    area_payload = json.loads(area_response.get_body())

    assert overview_payload["summary"]["counties_covered"] == 26
    assert area_payload["area_name"] == "Mayo"
    assert "context_signals" in area_payload


def test_compare_endpoint_validates_and_returns_payload() -> None:
    response = compare(_request(url="/api/compare", params={"areas": "Cork;Galway"}))
    payload = json.loads(response.get_body())

    assert payload["latest_period"] == "2025Q3"
    assert len(payload["areas"]) == 2
