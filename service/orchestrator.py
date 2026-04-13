from service.prediction_store import lookup_prediction
from service.render import render_prediction
from service.llm_client import call_llm
from service.intent_extractor import extract_intent


def answer(question: str):
    # 1 Extract intent (LLM, intent only)
    intent = extract_intent(question)

    area = intent.get("area")
    field = intent.get("field")
    time_period = intent.get("time_period")

    # 2 Deterministic lookup (NO LLM)
    artifact = lookup_prediction(area, time_period)

    if artifact:
        # Guaranteed: no LLM touches data
        return render_prediction(artifact, field)

    # 3 LLM fallback ONLY if no artifact exists
    return call_llm(question)