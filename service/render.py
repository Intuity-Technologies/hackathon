FIELD_TEMPLATES = {
    "predicted_classification_glm": (
        "Housing stress in {area_name} during {time_period} "
        "is classified as {predicted_classification_glm}."
    ),
    "pred_housing_stress_score": (
        "The housing stress score for {area_name} in {time_period} "
        "is {pred_housing_stress_score}."
    ),
    "cluster_label": (
        "{area_name} falls within the '{cluster_label}' housing cluster "
        "during {time_period}."
    ),
    "dominant_model_driver": (
        "The dominant driver of housing stress in {area_name} during "
        "{time_period} is {dominant_model_driver}."
    ),
    "pred_rent_level": (
        "The predicted average rent level in {area_name} during "
        "{time_period} is €{pred_rent_level:,} per month."
    ),
    "pred_arrears_90d_rate": (
        "The predicted 90‑day mortgage arrears rate in {area_name} during "
        "{time_period} is {pred_arrears_90d_rate:.1%}."
    ),
    "rent_growth": (
        "Rent growth in {area_name} during {time_period} "
        "was {rent_growth}%."
    ),
    "population_growth": (
        "Population growth in {area_name} during {time_period} "
        "was {population_growth}%."
    ),
    "housing_completions": (
        "There were {housing_completions:,} housing completions in "
        "{area_name} during {time_period}."
    ),
}



def render_prediction(artifact: dict, field: str) -> str | None:
    template = FIELD_TEMPLATES.get(field)
    
    if not template:
            return None

    return template.format(**artifact)
