from service.prediction_store import lookup_prediction
from service.render import render_prediction
from service.llm_client import call_llm
from service.intent_extractor import extract_intent


def answer(question: str):
    # 1) Extract structured intent using LLM (JSON only)
    intent = extract_intent(question)

    city = intent.get("city")
    topic = intent.get("topic")
    horizon = intent.get("horizon_months")

    # 2) Map topic -> retrieval artifact type.
    prediction_type_map = {
        "price": "housing_pressure",
        "rent": "rent_pressure",
        "homelessness": "homelessness",
        "population_density": "population_density",
    }
    prediction_type = prediction_type_map.get(topic)

    # 3) Deterministic lookup from API-backed prediction store.
    prediction = lookup_prediction(city, prediction_type, horizon)

    if prediction:
        # Hard guarantee: if retrieval exists, return deterministic text.
        return render_prediction(prediction)

    if topic in {"price", "rent"}:
        return (
            "I could not find a verified numeric artifact for that query. "
            "Try asking for a county with available data (for example: Mayo, Cork, Dublin)."
        )

    # LLM fallback only for qualitative answers when no artifact exists.
    return call_llm(question)


if __name__ == "__main__":
    print("Housing Signal Assistant (retrieval-first)")
    print("Type your question, Ctrl+C to exit\n")

    while True:
        q = input("> ")
        print(answer(q))
        print()
