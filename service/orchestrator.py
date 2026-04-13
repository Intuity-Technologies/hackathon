from service.prediction_store import lookup_prediction
from service.render import render_prediction
from service.llm_client import call_llm
from service.intent_extractor import extract_intent


def answer(question: str):
    # 1 Extract intent (LLM used ONLY for intent)
    intent = extract_intent(question)

    area = intent.get("area")
    field = intent.get("field")
    time_period = intent.get("time_period")

    # 2 Deterministic path ONLY if intent is complete
    if area and field and time_period:
        artifact = lookup_prediction(area, time_period)
        if artifact:
            rendered = render_prediction(artifact, field)
            if rendered:
                return rendered

    # 3 Anything else → LLM fallback
    return call_llm(question)