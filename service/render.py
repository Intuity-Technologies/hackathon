TEMPLATES = {
    "median_price": (
        "The predicted median house price in {city} "
        "in {horizon_months} months is €{predicted_value:,} "
        "(confidence {confidence:.0%})."
    ),
    "rent": (
        "The predicted average rent in {city} "
        "in {horizon_months} months is €{predicted_value:,} per month "
        "(confidence {confidence:.0%})."
    ),
    "growth_rate": (
        "House prices in {city} are predicted to change by "
        "{predicted_value:.1f}% over the next {horizon_months} months "
        "(confidence {confidence:.0%})."
    )
}

def render_prediction(p):
    template = TEMPLATES[p["prediction_type"]]
    return template.format(**p)
