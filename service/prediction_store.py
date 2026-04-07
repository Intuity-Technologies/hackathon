MOCK_PREDICTIONS = [
    {
        "city": "Galway",
        "prediction_type": "median_price",
        "horizon_months": 12,
        "predicted_value": 387000,
        "confidence": 0.91,
        "model_name": "regression_v1"
    }
]

def lookup_prediction(city, prediction_type, horizon_months):
    if city is None or prediction_type is None or horizon_months is None:
        return None

    for p in MOCK_PREDICTIONS:
        if (
            p["city"].lower() == city.lower()
            and p["prediction_type"] == prediction_type
            and p["horizon_months"] == horizon_months
        ):
            return p

    return None
