from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from etl.transform.normalize_planning import normalize_planning_dataframe
from etl.transform.normalize_population import normalize_population_dataframe
from etl.transform.normalize_rents import normalize_rent_dataframe

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "etl"


def test_normalize_population_dataframe_computes_growth() -> None:
    frame = pd.read_csv(FIXTURES / "population_cso.csv")
    output = normalize_population_dataframe(frame)

    assert set(output["area_name"]) == {"Mayo", "Cork"}
    mayo_growth = output.loc[output["area_name"] == "Mayo", "population_growth"].iloc[0]
    assert round(float(mayo_growth), 2) == 2.00


def test_normalize_rent_dataframe_computes_yoy_growth() -> None:
    frame = pd.read_csv(FIXTURES / "rents_riq02.csv")
    output = normalize_rent_dataframe(frame)

    assert set(output["area_name"]) == {"Mayo", "Cork"}
    assert set(output["time_period"]) == {"2025Q1"}
    mayo_growth = output.loc[output["area_name"] == "Mayo", "rent_growth"].iloc[0]
    assert round(float(mayo_growth), 2) == 10.00


def test_normalize_planning_dataframe_handles_local_authorities() -> None:
    frame = pd.read_csv(FIXTURES / "planning_local_authority.csv")
    output = normalize_planning_dataframe(frame, "NDQ05.csv")

    assert set(output["area_name"]) == {"Mayo", "Cork"}
    assert set(output["time_period"]) == {"2025Q1", "2025Q2"}


def test_normalize_planning_dataframe_can_use_national_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    frame = pd.read_csv(FIXTURES / "planning_national.csv")
    monkeypatch.setenv("PLANNING_STRICT_COUNTY_ONLY", "false")
    output = normalize_planning_dataframe(frame, "national.csv")

    assert output["area_name"].nunique() == 26
    q1_total = output.loc[output["time_period"] == "2025Q1", "housing_completions"].sum()
    assert round(float(q1_total), 2) == 1000.00


def test_normalize_population_dataframe_rejects_unknown_headers() -> None:
    frame = pd.DataFrame({"CountyName": ["Mayo"], "Value": [1]})
    with pytest.raises(ValueError):
        normalize_population_dataframe(frame)
