from __future__ import annotations

from typing import Any


def render_prediction(payload: dict[str, Any]) -> str:
    prediction_type = payload.get("prediction_type")
    if prediction_type == "housing_pressure":
        return (
            f"{payload['city']} is {payload['classification']} in {payload['time_period']} "
            f"with a housing pressure score of {payload['overall_housing_pressure_score']:.1f}/100. "
            f"Dominant driver: {payload['dominant_driver']}."
        )
    if prediction_type == "rent_pressure":
        return (
            f"{payload['city']} rent pressure in {payload['time_period']} shows "
            f"{payload['rent_growth']:.2f}% year-over-year growth."
        )
    if prediction_type == "population_density":
        return (
            f"{payload['city']} population pressure in {payload['time_period']} is "
            f"{payload['population_growth']:.2f}%."
        )
    if prediction_type == "homelessness":
        return (
            f"{payload['city']} homelessness context is {payload['classification']} in "
            f"{payload['time_period']}. {payload['explanation_summary']}"
        )
    return "I found evidence for that area, but could not map it to a response."


def render_area_detail(area: dict[str, Any], topic: str | None = None) -> str:
    name = area["area_name"]
    latest_period = area["time_period"]
    score = area["overall_housing_pressure_score"]
    classification = area["classification"]
    driver = area["dominant_driver"]
    qoq = area.get("score_qoq_change")
    qoq_text = "flat quarter-on-quarter" if qoq in (None, 0) else f"{qoq:+.1f} points quarter-on-quarter"

    if topic == "price":
        sale_price = area.get("median_sale_price_display", "Unavailable")
        return (
            f"{name} sale-price context shows a median sale price of {sale_price}. "
            f"The county's broader housing pressure is {classification} at {score:.1f}/100 in {latest_period}, "
            f"with {driver.lower()} as the strongest driver."
        )

    if topic == "rent":
        return (
            f"{name} rent pressure context in {latest_period} shows {area['rent_growth']:.2f}% rent growth. "
            f"Overall housing pressure is {classification} at {score:.1f}/100, and the score is {qoq_text}."
        )

    if topic == "homelessness":
        homelessness = next(
            (signal for signal in area["context_signals"] if signal["id"] == "regional_homelessness_adults"),
            None,
        )
        homelessness_text = homelessness["display_value"] if homelessness else "regional homelessness context unavailable"
        return (
            f"{name} sits in the {area['area_context']['region']} region, where the latest homelessness context shows "
            f"{homelessness_text}. The county's current housing pressure is {classification} at {score:.1f}/100."
        )

    if topic == "supply":
        return (
            f"{name} is {classification} at {score:.1f}/100 in {latest_period}. "
            f"Supply-side evidence shows {area['housing_completions']:.1f} housing completions in the scored pipeline, "
            f"and the dominant driver is {driver.lower()}."
        )

    if topic == "population_density":
        return (
            f"{name} population pressure in {latest_period} is {area['population_growth']:.2f}% growth. "
            f"Overall housing pressure is {classification} at {score:.1f}/100."
        )

    return (
        f"{name} is currently {classification} for housing pressure in {latest_period} with a score of {score:.1f}/100. "
        f"The strongest driver is {driver.lower()}, and the score is {qoq_text}. "
        f"{area['area_context']['explanation_summary']}"
    )


def render_compare(compare_payload: dict[str, Any]) -> str:
    areas = compare_payload["areas"]
    names = [area["area_name"] for area in areas]
    ordered = sorted(areas, key=lambda area: area["overall_housing_pressure_score"], reverse=True)
    leader = ordered[0]
    lagger = ordered[-1]
    winner_bits = ", ".join(
        f"{metric['label']}: {metric['winner']}" for metric in compare_payload["metric_summary"][:3]
    )
    return (
        f"In {compare_payload['latest_period']}, {leader['area_name']} has the higher housing pressure score "
        f"at {leader['overall_housing_pressure_score']:.1f}/100, while {lagger['area_name']} is lower at "
        f"{lagger['overall_housing_pressure_score']:.1f}/100. Compared counties: {', '.join(names)}. "
        f"Metric leaders: {winner_bits}."
    )


def render_overview(overview: dict[str, Any], leaderboard: dict[str, Any]) -> str:
    top = leaderboard["rows"][0]
    return (
        f"The latest scored period is {overview['latest_period']} across {overview['summary']['counties_covered']} counties. "
        f"There are {overview['summary']['critical_count']} critical counties and "
        f"{overview['summary']['high_pressure_count']} high-pressure counties. "
        f"{top['area_name']} currently leads the pressure ranking at "
        f"{top['overall_housing_pressure_score']:.1f}/100."
    )
