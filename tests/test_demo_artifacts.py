from __future__ import annotations

import json
from pathlib import Path

from jsonschema import validate

from service.housing_data import build_demo_payloads, compare_areas, write_demo_artifacts


def test_build_demo_payloads_uses_county_backbone() -> None:
    bundle = build_demo_payloads()

    assert bundle.overview["latest_period"] == "2025Q3"
    assert bundle.overview["summary"]["counties_covered"] == 26
    assert bundle.overview["summary"]["critical_count"] >= 1
    assert "Mayo" in bundle.area_detail
    assert bundle.area_detail["Mayo"]["context_signals"]


def test_area_detail_matches_schema() -> None:
    bundle = build_demo_payloads()
    schema_path = Path("contracts/housing_signal_response.schema.json")
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    validate(instance=bundle.area_detail["Mayo"], schema=schema)


def test_write_demo_artifacts_creates_all_outputs(tmp_path: Path) -> None:
    write_demo_artifacts(output_dir=tmp_path)

    expected = {
        "overview.json",
        "leaderboard.json",
        "area_detail.json",
        "compare.json",
        "trends.json",
        "sources_manifest.json",
    }
    assert expected == {path.name for path in tmp_path.iterdir()}


def test_compare_areas_returns_metric_summary() -> None:
    payload = compare_areas(["Cork", "Galway"])

    assert payload["latest_period"] == "2025Q3"
    assert len(payload["areas"]) == 2
    assert payload["metric_summary"][0]["metric"] == "overall_housing_pressure_score"
