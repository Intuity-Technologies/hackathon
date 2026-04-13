from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from etl.common.geography import normalize_area_name
from etl.common.storage import utc_now_iso

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = REPO_ROOT / "data"
DEMO_ROOT = DATA_ROOT / "demo"

DEFAULT_SIGNALS_PATH = DATA_ROOT / "signals" / "housing_pressure" / "area_level=county" / "part-000.parquet"
DEFAULT_PRICE_PATH = DATA_ROOT / "Median sale price by county, Feb 2025.csv"
DEFAULT_HOMELESSNESS_REGIONAL_PATH = DATA_ROOT / "homelessness-report-december-2025.csv"
DEFAULT_HOMELESSNESS_NATIONAL_PATH = DATA_ROOT / "Homeless households.csv"
DEFAULT_OVERBURDEN_PATH = DATA_ROOT / "curated" / "overburden.parquet"
DEFAULT_PBSA_PATH = DATA_ROOT / "PBSA 2024.csv"
DEFAULT_ESB_TOTAL_PATH = DATA_ROOT / "ESB Total Annual Connections.csv"
DEFAULT_NDC_PATH = DATA_ROOT / "NDC Q4 2024.csv"

ARTIFACT_FILES = {
    "overview": DEMO_ROOT / "overview.json",
    "leaderboard": DEMO_ROOT / "leaderboard.json",
    "area_detail": DEMO_ROOT / "area_detail.json",
    "compare": DEMO_ROOT / "compare.json",
    "trends": DEMO_ROOT / "trends.json",
    "sources_manifest": DEMO_ROOT / "sources_manifest.json",
}

COUNTY_TO_REGION = {
    "Carlow": "South-East",
    "Cavan": "North-East",
    "Clare": "Mid-West",
    "Cork": "South-West",
    "Donegal": "North-West",
    "Dublin": "Dublin",
    "Galway": "West",
    "Kerry": "South-West",
    "Kildare": "Mid-East",
    "Kilkenny": "South-East",
    "Laois": "Midlands",
    "Leitrim": "North-West",
    "Limerick": "Mid-West",
    "Longford": "Midlands",
    "Louth": "North-East",
    "Mayo": "West",
    "Meath": "Mid-East",
    "Monaghan": "North-East",
    "Offaly": "Midlands",
    "Roscommon": "West",
    "Sligo": "North-West",
    "Tipperary": "Mid-West",
    "Waterford": "South-East",
    "Westmeath": "Midlands",
    "Wexford": "South-East",
    "Wicklow": "Mid-East",
}


@dataclass(slots=True)
class DemoArtifactBundle:
    overview: dict[str, Any]
    leaderboard: dict[str, Any]
    area_detail: dict[str, Any]
    compare: dict[str, Any]
    trends: dict[str, Any]
    sources_manifest: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "overview": self.overview,
            "leaderboard": self.leaderboard,
            "area_detail": self.area_detail,
            "compare": self.compare,
            "trends": self.trends,
            "sources_manifest": self.sources_manifest,
        }


_CACHE: dict[str, Any] = {"signature": None, "bundle": None}


def _mtime_signature(paths: list[Path]) -> str:
    pieces = []
    for path in paths:
        if not path.exists():
            pieces.append(f"{path.name}:missing")
            continue
        pieces.append(f"{path.name}:{int(path.stat().st_mtime)}:{path.stat().st_size}")
    return "|".join(pieces)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _to_float(value: Any) -> float | None:
    try:
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _latest_period(df: pd.DataFrame) -> str:
    latest = df.sort_values("time_index", ascending=False).iloc[0]
    return str(latest["time_period"])


def _format_number(value: float | int | None, digits: int = 0) -> str:
    if value is None:
        return "Unavailable"
    if digits == 0:
        return f"{value:,.0f}"
    return f"{value:,.{digits}f}"


def _format_percent(value: float | None, digits: int = 1) -> str:
    if value is None:
        return "Unavailable"
    return f"{value:.{digits}f}%"


def _format_currency(value: float | None) -> str:
    if value is None:
        return "Unavailable"
    return f"EUR {value:,.0f}"


def _load_signals_dataframe(path: Path = DEFAULT_SIGNALS_PATH) -> pd.DataFrame:
    df = pd.read_parquet(path).copy()
    for column in [
        "overall_housing_pressure_score",
        "population_growth",
        "rent_growth",
        "housing_completions",
        "score_qoq_change",
        "score_4q_avg",
        "population_growth_score",
        "rent_pressure_score",
        "supply_gap_score",
        "score_rank_in_period",
        "score_percentile_in_period",
        "time_index",
    ]:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")
    return df


def _load_county_sale_prices() -> dict[str, dict[str, Any]]:
    frame = pd.read_csv(DEFAULT_PRICE_PATH).rename(
        columns={"Unnamed: 0": "area_name", "Unnamed: 1": "median_sale_price"}
    )
    frame["area_name"] = frame["area_name"].astype(str).str.strip()
    frame["median_sale_price"] = (
        frame["median_sale_price"].astype(str).str.replace(",", "", regex=False).str.strip()
    )
    frame["median_sale_price"] = pd.to_numeric(frame["median_sale_price"], errors="coerce")
    records: dict[str, dict[str, Any]] = {}
    for row in frame.dropna(subset=["area_name", "median_sale_price"]).itertuples():
        records[row.area_name] = {
            "id": "median_sale_price",
            "label": "Median sale price",
            "metric": "median_sale_price",
            "value": float(row.median_sale_price),
            "display_value": _format_currency(float(row.median_sale_price)),
            "source_name": "Median sale price by county",
            "source_period": "2025-02",
            "geography_level": "county",
            "coverage_scope": "County",
            "quality_flag": "verified-context",
            "data_mode": "local",
        }
    return records


def _load_regional_homelessness() -> dict[str, dict[str, Any]]:
    frame = pd.read_csv(DEFAULT_HOMELESSNESS_REGIONAL_PATH)
    out: dict[str, dict[str, Any]] = {}
    for row in frame.to_dict(orient="records"):
        region = str(row.get("Region", "")).strip()
        total_adults = _to_float(row.get("Total Adults"))
        families = _to_float(row.get("Number of Families"))
        out[region] = {
            "region": region,
            "total_adults": total_adults,
            "display_total_adults": f"{_format_number(total_adults)} adults",
            "families": families,
            "display_families": f"{_format_number(families)} families",
            "source_name": "Homelessness report December 2025",
            "source_period": "2025-12",
            "geography_level": "region",
            "coverage_scope": "Region",
            "quality_flag": "verified-context",
            "data_mode": "local",
        }
    return out


def _load_national_overburden() -> dict[str, Any]:
    frame = pd.read_parquet(DEFAULT_OVERBURDEN_PATH)
    latest = frame.sort_values("time_period", ascending=False).iloc[0]
    rate = _to_float(latest.get("housing_cost_overburden_rate"))
    percent_rate = rate * 100.0 if rate is not None and rate <= 1 else rate
    return {
        "id": "housing_cost_overburden_rate",
        "label": "Housing cost overburden",
        "metric": "housing_cost_overburden_rate",
        "value": percent_rate,
        "display_value": _format_percent(percent_rate),
        "source_name": "SILC housing cost overburden",
        "source_period": str(latest.get("time_period", "2024")),
        "geography_level": "national",
        "coverage_scope": "National",
        "quality_flag": "verified-context",
        "data_mode": "local",
    }


def _load_latest_pbsa() -> dict[str, Any]:
    frame = pd.read_csv(DEFAULT_PBSA_PATH)
    frame["Quarter"] = frame["Quarter"].astype(str).str.strip()
    frame["Total"] = pd.to_numeric(frame["Total"], errors="coerce")
    latest = frame.dropna(subset=["Total"]).sort_values("Quarter", ascending=False).iloc[0]
    total = _to_float(latest["Total"])
    return {
        "id": "pbsa_pipeline_total",
        "label": "PBSA pipeline",
        "metric": "pbsa_pipeline_total",
        "value": total,
        "display_value": f"{_format_number(total)} beds",
        "source_name": "PBSA 2024",
        "source_period": str(latest["Quarter"]),
        "geography_level": "national",
        "coverage_scope": "National",
        "quality_flag": "context-only",
        "data_mode": "local",
    }


def _load_latest_esb_connections() -> dict[str, Any]:
    frame = pd.read_csv(DEFAULT_ESB_TOTAL_PATH).rename(
        columns={"Unnamed: 0": "year", "Total ESB Connections": "total_connections"}
    )
    frame["year"] = pd.to_numeric(frame["year"], errors="coerce")
    frame["total_connections"] = pd.to_numeric(frame["total_connections"], errors="coerce")
    latest = frame.dropna(subset=["year", "total_connections"]).sort_values("year", ascending=False).iloc[0]
    total = _to_float(latest["total_connections"])
    return {
        "id": "esb_total_connections",
        "label": "ESB annual connections",
        "metric": "esb_total_connections",
        "value": total,
        "display_value": _format_number(total),
        "source_name": "ESB Total Annual Connections",
        "source_period": str(int(latest["year"])),
        "geography_level": "national",
        "coverage_scope": "National",
        "quality_flag": "context-only",
        "data_mode": "local",
    }


def _load_latest_supply_mix() -> dict[str, Any]:
    frame = pd.read_csv(DEFAULT_NDC_PATH).rename(columns={"Unnamed: 0": "time_period"})
    for column in ["Single House", "Scheme House", "Apartment"]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    latest = frame.dropna(subset=["time_period"]).sort_values("time_period", ascending=False).iloc[0]
    single = _to_float(latest.get("Single House"))
    scheme = _to_float(latest.get("Scheme House"))
    apartment = _to_float(latest.get("Apartment"))
    total = sum(value or 0 for value in [single, scheme, apartment])
    display = (
        f"Single {_format_number(single)} | "
        f"Scheme {_format_number(scheme)} | "
        f"Apartment {_format_number(apartment)}"
    )
    return {
        "id": "new_dwelling_mix",
        "label": "New dwelling mix",
        "metric": "new_dwelling_mix",
        "value": total,
        "display_value": display,
        "breakdown": {
            "single_house": single,
            "scheme_house": scheme,
            "apartment": apartment,
        },
        "source_name": "New dwelling completions by type",
        "source_period": str(latest["time_period"]),
        "geography_level": "national",
        "coverage_scope": "National",
        "quality_flag": "verified-context",
        "data_mode": "local",
    }


def _load_national_homeless_trend() -> dict[str, Any]:
    frame = pd.read_csv(DEFAULT_HOMELESSNESS_NATIONAL_PATH).rename(
        columns={
            "Unnamed: 0": "time_period",
            "Total Single Adults": "single_adults",
            "Total Families": "families",
            "Total No. of Households in Homelessness": "households",
        }
    )
    for column in ["single_adults", "families", "households"]:
        frame[column] = frame[column].astype(str).str.replace(",", "", regex=False).str.strip()
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    latest = frame.dropna(subset=["households"]).iloc[-1]
    households = _to_float(latest["households"])
    return {
        "id": "national_homeless_households",
        "label": "Homeless households",
        "metric": "national_homeless_households",
        "value": households,
        "display_value": _format_number(households),
        "source_name": "Homeless households",
        "source_period": str(latest["time_period"]),
        "geography_level": "national",
        "coverage_scope": "National",
        "quality_flag": "verified-context",
        "data_mode": "local",
    }


def _context_signals_for_area(
    area_name: str,
    sale_prices: dict[str, dict[str, Any]],
    regional_homelessness: dict[str, dict[str, Any]],
    national_overburden: dict[str, Any],
    national_pbsa: dict[str, Any],
    national_esb: dict[str, Any],
    national_supply_mix: dict[str, Any],
    national_homeless_trend: dict[str, Any],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if area_name in sale_prices:
        records.append(dict(sale_prices[area_name]))

    region = COUNTY_TO_REGION.get(area_name)
    if region and region in regional_homelessness:
        regional = regional_homelessness[region]
        records.append(
            {
                "id": "regional_homelessness_adults",
                "label": f"{region} homelessness pressure",
                "metric": "regional_homelessness_adults",
                "value": regional["total_adults"],
                "display_value": regional["display_total_adults"],
                "secondary_display": regional["display_families"],
                "source_name": regional["source_name"],
                "source_period": regional["source_period"],
                "geography_level": regional["geography_level"],
                "coverage_scope": regional["coverage_scope"],
                "quality_flag": regional["quality_flag"],
                "data_mode": regional["data_mode"],
            }
        )

    records.extend(
        [
            dict(national_overburden),
            dict(national_homeless_trend),
            dict(national_supply_mix),
            dict(national_pbsa),
            dict(national_esb),
        ]
    )
    return records


def _summary_row(row: pd.Series, sale_price_signal: dict[str, Any] | None = None) -> dict[str, Any]:
    output = {
        "area_name": str(row["area_name"]),
        "area_level": str(row.get("area_level", "county")),
        "geography_level": str(row.get("geography_level", "county")),
        "coverage_scope": str(row.get("coverage_scope", "County")),
        "time_period": str(row["time_period"]),
        "classification": str(row["classification"]),
        "dominant_driver": str(row["dominant_driver"]),
        "overall_housing_pressure_score": round(float(row["overall_housing_pressure_score"]), 2),
        "score_rank_in_period": int(row["score_rank_in_period"]),
        "score_percentile_in_period": round(float(row["score_percentile_in_period"]), 2),
        "score_qoq_change": round(float(row["score_qoq_change"]), 2) if pd.notna(row["score_qoq_change"]) else None,
        "rent_growth": round(float(row["rent_growth"]), 2),
        "population_growth": round(float(row["population_growth"]), 2),
        "housing_completions": round(float(row["housing_completions"]), 2),
        "published_at": str(row.get("published_at", "")),
        "quality_flag": str(row.get("quality_flag", "verified-composite")),
        "data_mode": str(row.get("data_mode", "local")),
    }
    if sale_price_signal:
        output["median_sale_price"] = sale_price_signal["value"]
        output["median_sale_price_display"] = sale_price_signal["display_value"]
    return output


def build_demo_payloads(signal_df: pd.DataFrame | None = None) -> DemoArtifactBundle:
    df = signal_df.copy() if signal_df is not None else _load_signals_dataframe()
    latest_period = _latest_period(df)
    latest = df[df["time_period"].astype(str) == latest_period].copy()
    latest = latest.sort_values("overall_housing_pressure_score", ascending=False).reset_index(drop=True)

    generated_at = utc_now_iso()
    published_at = str(latest["published_at"].iloc[0]) if "published_at" in latest.columns else generated_at
    data_mode = str(latest["data_mode"].iloc[0]) if "data_mode" in latest.columns else "local"

    sale_prices = _load_county_sale_prices()
    regional_homelessness = _load_regional_homelessness()
    national_overburden = _load_national_overburden()
    national_pbsa = _load_latest_pbsa()
    national_esb = _load_latest_esb_connections()
    national_supply_mix = _load_latest_supply_mix()
    national_homeless_trend = _load_national_homeless_trend()

    leaderboard_rows = [
        _summary_row(row, sale_prices.get(str(row["area_name"])))
        for _, row in latest.iterrows()
    ]

    class_counts = latest["classification"].value_counts().to_dict()
    highest_pressure = leaderboard_rows[0]
    highest_sale_price = max(sale_prices.items(), key=lambda item: item[1]["value"])
    total_regional_homeless_adults = sum(item["total_adults"] or 0 for item in regional_homelessness.values())

    overview = {
        "generated_at": generated_at,
        "latest_period": latest_period,
        "published_at": published_at,
        "data_mode": data_mode,
        "summary": {
            "counties_covered": int(latest["area_name"].nunique()),
            "average_score": round(float(latest["overall_housing_pressure_score"].mean()), 2),
            "critical_count": int(class_counts.get("Critical", 0)),
            "high_pressure_count": int(class_counts.get("High pressure", 0)),
            "watchlist_count": int(class_counts.get("Watchlist", 0)),
            "stable_count": int(class_counts.get("Stable", 0)),
        },
        "headline_cards": [
            {
                "id": "county_coverage",
                "label": "County coverage",
                "value": str(int(latest["area_name"].nunique())),
                "detail": f"Latest scored quarter: {latest_period}",
            },
            {
                "id": "highest_pressure",
                "label": "Highest pressure county",
                "value": highest_pressure["area_name"],
                "detail": f"{highest_pressure['overall_housing_pressure_score']}/100 ({highest_pressure['classification']})",
            },
            {
                "id": "highest_sale_price",
                "label": "Highest median sale price",
                "value": highest_sale_price[0],
                "detail": highest_sale_price[1]["display_value"],
            },
            {
                "id": "regional_homelessness",
                "label": "Regional homelessness adults",
                "value": _format_number(total_regional_homeless_adults),
                "detail": "Sum across December 2025 regions",
            },
            {
                "id": "overburden",
                "label": "National overburden",
                "value": national_overburden["display_value"],
                "detail": "Housing cost burden reference",
            },
            {
                "id": "pbsa_pipeline",
                "label": "Latest PBSA pipeline",
                "value": national_pbsa["display_value"],
                "detail": national_pbsa["source_period"],
            },
        ],
        "featured_counties": leaderboard_rows[:4],
        "freshness": {
            "latest_period": latest_period,
            "published_at": published_at,
            "runtime_mode": "local-first",
            "data_mode": data_mode,
            "quality_flag": "verified-demo-artifacts",
        },
        "ethics_note": (
            "Current-state scores are deterministic. Context signals with regional or national scope "
            "are shown as supporting evidence and are not blended into the county score."
        ),
    }

    leaderboard = {
        "generated_at": generated_at,
        "latest_period": latest_period,
        "data_mode": data_mode,
        "rows": leaderboard_rows,
    }

    area_detail: dict[str, Any] = {}
    trend_payload: dict[str, Any] = {}
    compare_rows: dict[str, Any] = {}
    for area_name, history in df.groupby("area_name"):
        history = history.sort_values("time_index").reset_index(drop=True)
        latest_row = history.iloc[-1]
        contexts = _context_signals_for_area(
            area_name,
            sale_prices,
            regional_homelessness,
            national_overburden,
            national_pbsa,
            national_esb,
            national_supply_mix,
            national_homeless_trend,
        )
        trend_rows = []
        for _, row in history.iterrows():
            trend_rows.append(
                {
                    "time_period": str(row["time_period"]),
                    "overall_housing_pressure_score": round(float(row["overall_housing_pressure_score"]), 2),
                    "rent_growth": round(float(row["rent_growth"]), 2),
                    "population_growth": round(float(row["population_growth"]), 2),
                    "housing_completions": round(float(row["housing_completions"]), 2),
                    "classification": str(row["classification"]),
                }
            )
        summary = _summary_row(latest_row, sale_prices.get(area_name))
        area_detail[area_name] = {
            **summary,
            "area_context": {
                "region": COUNTY_TO_REGION.get(area_name),
                "score_breakdown": [
                    {"label": "Population growth", "value": round(float(latest_row["population_growth_score"]), 2)},
                    {"label": "Affordability", "value": round(float(latest_row["rent_pressure_score"]), 2)},
                    {"label": "Supply gap", "value": round(float(latest_row["supply_gap_score"]), 2)},
                ],
                "moving_average_score": round(float(latest_row["score_4q_avg"]), 2),
                "explanation_summary": str(latest_row["explanation_summary"]),
            },
            "context_signals": contexts,
            "trend": {
                "latest_qoq_change": summary["score_qoq_change"],
                "series": trend_rows,
            },
            "provenance": {
                "source_name": str(latest_row.get("source_name", "")),
                "source_period": str(latest_row.get("source_period", latest_period)),
                "published_at": str(latest_row.get("published_at", published_at)),
            },
            "freshness": overview["freshness"],
            "quality_flag": summary["quality_flag"],
            "data_mode": data_mode,
        }
        trend_payload[area_name] = {
            "area_name": area_name,
            "latest_period": latest_period,
            "data_mode": data_mode,
            "series": trend_rows,
        }
        compare_rows[area_name] = summary

    compare = {
        "generated_at": generated_at,
        "latest_period": latest_period,
        "data_mode": data_mode,
        "areas": compare_rows,
    }

    sources_manifest = {
        "generated_at": generated_at,
        "data_mode": data_mode,
        "sources": [
            {
                "id": "housing_pressure_composite",
                "label": "Composite county housing pressure score",
                "source_name": "Signals parquet",
                "source_period": latest_period,
                "geography_level": "county",
                "coverage_scope": "County",
                "quality_flag": "verified-composite",
                "path": str(DEFAULT_SIGNALS_PATH.relative_to(REPO_ROOT)),
                "notes": "Deterministic score using population growth, rent pressure, and housing completions.",
            },
            {
                "id": "median_sale_price",
                "label": "County median sale price",
                "source_name": "Median sale price by county",
                "source_period": "2025-02",
                "geography_level": "county",
                "coverage_scope": "County",
                "quality_flag": "verified-context",
                "path": str(DEFAULT_PRICE_PATH.relative_to(REPO_ROOT)),
                "notes": "Affordable housing context signal, not blended into the composite score.",
            },
            {
                "id": "regional_homelessness",
                "label": "Regional homelessness adults",
                "source_name": "Homelessness report December 2025",
                "source_period": "2025-12",
                "geography_level": "region",
                "coverage_scope": "Region",
                "quality_flag": "verified-context",
                "path": str(DEFAULT_HOMELESSNESS_REGIONAL_PATH.relative_to(REPO_ROOT)),
                "notes": "Displayed with regional scope badges only.",
            },
            {
                "id": "housing_overburden",
                "label": "National housing cost overburden",
                "source_name": "Curated overburden parquet",
                "source_period": national_overburden["source_period"],
                "geography_level": "national",
                "coverage_scope": "National",
                "quality_flag": "verified-context",
                "path": str(DEFAULT_OVERBURDEN_PATH.relative_to(REPO_ROOT)),
                "notes": "National reference signal for affordability stress.",
            },
            {
                "id": "pbsa_pipeline",
                "label": "PBSA pipeline",
                "source_name": "PBSA 2024",
                "source_period": national_pbsa["source_period"],
                "geography_level": "national",
                "coverage_scope": "National",
                "quality_flag": "context-only",
                "path": str(DEFAULT_PBSA_PATH.relative_to(REPO_ROOT)),
                "notes": "Useful context for student-demand and urban-planning discussions.",
            },
            {
                "id": "new_dwelling_mix",
                "label": "National dwelling mix",
                "source_name": "NDC Q4 2024",
                "source_period": national_supply_mix["source_period"],
                "geography_level": "national",
                "coverage_scope": "National",
                "quality_flag": "verified-context",
                "path": str(DEFAULT_NDC_PATH.relative_to(REPO_ROOT)),
                "notes": "Used as a supporting supply mix indicator.",
            },
            {
                "id": "esb_connections",
                "label": "ESB annual connections",
                "source_name": "ESB Total Annual Connections",
                "source_period": national_esb["source_period"],
                "geography_level": "national",
                "coverage_scope": "National",
                "quality_flag": "context-only",
                "path": str(DEFAULT_ESB_TOTAL_PATH.relative_to(REPO_ROOT)),
                "notes": "Long-run supply and infrastructure context.",
            },
        ],
    }

    return DemoArtifactBundle(
        overview=overview,
        leaderboard=leaderboard,
        area_detail=area_detail,
        compare=compare,
        trends=trend_payload,
        sources_manifest=sources_manifest,
    )


def write_demo_artifacts(output_dir: Path = DEMO_ROOT, signal_df: pd.DataFrame | None = None) -> DemoArtifactBundle:
    bundle = build_demo_payloads(signal_df=signal_df)
    output_dir.mkdir(parents=True, exist_ok=True)
    for key, path in ARTIFACT_FILES.items():
        _write_json(path if output_dir == DEMO_ROOT else output_dir / path.name, getattr(bundle, key))
    return bundle


def _load_bundle_from_artifacts() -> DemoArtifactBundle | None:
    if not all(path.exists() for path in ARTIFACT_FILES.values()):
        return None
    return DemoArtifactBundle(
        overview=_read_json(ARTIFACT_FILES["overview"]),
        leaderboard=_read_json(ARTIFACT_FILES["leaderboard"]),
        area_detail=_read_json(ARTIFACT_FILES["area_detail"]),
        compare=_read_json(ARTIFACT_FILES["compare"]),
        trends=_read_json(ARTIFACT_FILES["trends"]),
        sources_manifest=_read_json(ARTIFACT_FILES["sources_manifest"]),
    )


def load_demo_artifacts(force_rebuild: bool = False) -> DemoArtifactBundle:
    signature = _mtime_signature(
        list(ARTIFACT_FILES.values())
        + [
            DEFAULT_SIGNALS_PATH,
            DEFAULT_PRICE_PATH,
            DEFAULT_HOMELESSNESS_REGIONAL_PATH,
            DEFAULT_HOMELESSNESS_NATIONAL_PATH,
            DEFAULT_OVERBURDEN_PATH,
            DEFAULT_PBSA_PATH,
            DEFAULT_ESB_TOTAL_PATH,
            DEFAULT_NDC_PATH,
        ]
    )
    if not force_rebuild and _CACHE["signature"] == signature and _CACHE["bundle"] is not None:
        return _CACHE["bundle"]

    bundle = None if force_rebuild else _load_bundle_from_artifacts()
    if bundle is None:
        bundle = build_demo_payloads()
    _CACHE["signature"] = signature
    _CACHE["bundle"] = bundle
    return bundle


def list_available_areas() -> list[str]:
    bundle = load_demo_artifacts()
    return sorted(bundle.area_detail.keys())


def match_area_name(name: str) -> str | None:
    target = normalize_area_name(name).lower()
    for area in list_available_areas():
        if area.lower() == target:
            return area
    return None


def get_overview() -> dict[str, Any]:
    return load_demo_artifacts().overview


def get_leaderboard() -> dict[str, Any]:
    return load_demo_artifacts().leaderboard


def get_area_detail(name: str) -> dict[str, Any] | None:
    bundle = load_demo_artifacts()
    matched = match_area_name(name)
    if not matched:
        return None
    return bundle.area_detail.get(matched)


def get_area_trends(name: str) -> dict[str, Any] | None:
    bundle = load_demo_artifacts()
    matched = match_area_name(name)
    if not matched:
        return None
    return bundle.trends.get(matched)


def compare_areas(area_names: list[str]) -> dict[str, Any]:
    bundle = load_demo_artifacts()
    selected = []
    for area in area_names:
        matched = match_area_name(area)
        if matched and matched not in [item["area_name"] for item in selected]:
            selected.append(dict(bundle.compare["areas"][matched]))

    if len(selected) < 2:
        raise ValueError("Provide at least two valid county names to compare.")

    metrics = []
    for metric, label, higher_is_worse in [
        ("overall_housing_pressure_score", "Housing pressure score", True),
        ("rent_growth", "Rent growth", True),
        ("population_growth", "Population growth", True),
        ("housing_completions", "Housing completions", False),
    ]:
        ranked = sorted(
            selected,
            key=lambda row: row.get(metric) if row.get(metric) is not None else float("-inf"),
            reverse=higher_is_worse,
        )
        metrics.append(
            {
                "metric": metric,
                "label": label,
                "winner": ranked[0]["area_name"],
                "higher_is_worse": higher_is_worse,
            }
        )

    return {
        "latest_period": bundle.compare["latest_period"],
        "data_mode": bundle.compare["data_mode"],
        "areas": selected,
        "metric_summary": metrics,
    }


def get_sources_manifest() -> dict[str, Any]:
    return load_demo_artifacts().sources_manifest


def build_compare_from_query(raw_value: str) -> list[str]:
    return [piece.strip() for piece in re.split(r"[;,]", raw_value) if piece.strip()]
