TEMPLATES = {
    "housing_pressure": (
        "{city} is currently classified as {classification} for housing pressure "
        "in {time_period}. Overall score: {overall_housing_pressure_score:.1f}/100. "
        "Dominant driver: {dominant_driver}."
    ),
    "rent_pressure": (
        "{city} rent pressure trend ({time_period}) shows a {rent_growth:.2f}% "
        "year-over-year change. Current classification: {classification}."
    ),
    "homelessness": (
        "{city} homelessness risk proxy in {time_period}: {classification}. "
        "Dominant pressure driver: {dominant_driver}. {explanation_summary}"
    ),
    "population_density": (
        "{city} population pressure proxy ({time_period}) is "
        "{population_growth:.2f}% growth, with overall classification {classification}."
    ),
}


def render_prediction(p):
    prediction_type = p.get("prediction_type")
    template = TEMPLATES.get(prediction_type)
    if not template:
        return "I found data for this area, but could not map it to a response template."

    if prediction_type == "housing_pressure":
        if p.get("overall_housing_pressure_score") is None:
            return (
                f'{p.get("city", "This area")} has a classification of '
                f'{p.get("classification", "unknown")} in {p.get("time_period", "the latest period")}.'
            )
    if prediction_type == "rent_pressure":
        if p.get("rent_growth") is None:
            return (
                f'{p.get("city", "This area")} has rent pressure classification '
                f'{p.get("classification", "unknown")} in {p.get("time_period", "the latest period")}.'
            )
    if prediction_type == "population_density":
        if p.get("population_growth") is None:
            return (
                f'{p.get("city", "This area")} has overall classification '
                f'{p.get("classification", "unknown")} in {p.get("time_period", "the latest period")}.'
            )

    return template.format(**p)
