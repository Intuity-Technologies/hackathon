
MOCK_PREDICTIONS = [
    {
        "city": "Galway",
        "prediction_type": "median_price",
        "horizon_months": 12,
        "predicted_value": 387000,
        "confidence": 0.91,
        "model_name": "regression_v1"
    },
    {
        "city": "Donegal",
        "prediction_type": "median_price",
        "horizon_months": 12,
        "predicted_value": 215000,
        "confidence": 0.88,
        "model_name": "regression_v1"
    },
    {
        "city": "Galway",
        "prediction_type": "rent",
        "horizon_months": 12,
        "predicted_value": 1650,
        "confidence": 0.85,
        "model_name": "regression_v1"
    },
    {
        "city": "Galway",
        "prediction_type": "homelessness",
        "description": (
            "Homelessness in Galway is influenced by housing supply constraints, "
            "rental affordability, and availability of emergency accommodation."
        )
    },
    {
        "city": "Galway",
        "prediction_type": "population_density",
        "category": "medium-to-high",
        "description": (
            "Galway has a compact urban core with higher density, "
            "surrounded by lower-density suburban and rural areas."
        )
    }

]


def lookup_prediction(city, prediction_type, horizon_months):
    if city is None or prediction_type is None:
        return None

    for p in MOCK_PREDICTIONS:
        if (
            p["city"].lower() == city.lower()
            and p["prediction_type"] == prediction_type
            and (
                "horizon_months" not in p
                or p.get("horizon_months") == horizon_months
            )
        ):
            return p

    return None
