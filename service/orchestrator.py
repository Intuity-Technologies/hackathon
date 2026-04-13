from __future__ import annotations

from service.housing_data import compare_areas, get_area_detail, get_leaderboard, get_overview
from service.intent_extractor import extract_intent
from service.llm_client import call_llm
from service.render import render_area_detail, render_compare, render_overview


def answer(question: str) -> str:
    intent = extract_intent(question)
    areas = intent.get("areas") or []
    topic = intent.get("topic")
    intent_name = intent.get("intent")

    if intent_name == "compare" and len(areas) >= 2:
        try:
            comparison = compare_areas(areas)
        except ValueError:
            comparison = None
        if comparison:
            return render_compare(comparison)

    if areas:
        area = get_area_detail(areas[0])
        if area:
            return render_area_detail(area, topic)

    if intent_name == "overview" or topic == "housing_pressure" or not areas:
        return render_overview(get_overview(), get_leaderboard())

    return call_llm(question)


if __name__ == "__main__":
    print("Housing Signal Assistant (retrieval-first)")
    print("Type your question, Ctrl+C to exit\n")

    while True:
        q = input("> ")
        print(answer(q))
        print()
