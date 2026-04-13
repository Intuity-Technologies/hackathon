from __future__ import annotations

import json
import os
import re

from dotenv import load_dotenv
from openai import AzureOpenAI

from service.housing_data import list_available_areas

load_dotenv()

CLIENT = None


INTENT_SYSTEM_PROMPT = """
You extract structured intent from housing questions.

Return ONLY valid JSON matching this schema:
{
  "areas": string[],
  "topic": "housing_pressure" | "price" | "rent" | "homelessness" | "population_density" | "supply" | null,
  "intent": "overview" | "area_detail" | "compare" | null,
  "horizon_months": number | null
}

Rules:
- Use "housing_pressure" for questions about housing pressure, affordable housing, classification, score, pressure ranking, or general housing stress.
- Use "price" for house prices, sale prices, housing costs, or affordability of buying.
- Use "rent" for rental price or rent pressure questions.
- Use "homelessness" for homelessness, emergency accommodation, or housing insecurity.
- Use "population_density" for density, population pressure, or urban spread.
- Use "supply" for dwelling completions, planning, supply pipeline, or urban planning delivery.
- Use "compare" intent when the user compares two or more places.
- Use "overview" when the question asks for leaders, rankings, top risks, or a broad summary with no specific county.
- Use "area_detail" for a county-specific question.
- Only set "horizon_months" if the question clearly asks about the future.
- Do not include explanations or extra text.
"""


def _get_client() -> AzureOpenAI | None:
    global CLIENT
    if CLIENT is not None:
        return CLIENT

    api_key = os.getenv("AZURE_OPENAI_API_KEY", "").strip()
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").strip()
    if not api_key or not endpoint:
        return None

    CLIENT = AzureOpenAI(
        api_key=api_key,
        azure_endpoint=endpoint,
        api_version="2024-02-15-preview",
    )
    return CLIENT


def _base_intent() -> dict:
    return {"areas": [], "topic": None, "intent": None, "horizon_months": None}


def _extract_json(text: str) -> dict:
    cleaned = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, flags=re.DOTALL)
    if fenced:
        cleaned = fenced.group(1)

    payload = json.loads(cleaned)
    if not isinstance(payload, dict):
        raise ValueError("Intent payload must be a JSON object.")
    return payload


def _extract_area_mentions(question: str) -> list[str]:
    lowered = question.lower()
    matches = []
    for area in list_available_areas():
        if re.search(rf"\b{re.escape(area.lower())}\b", lowered):
            matches.append(area)
    return matches


def _heuristic_intent(question: str) -> dict:
    lowered = question.lower()
    intent = _base_intent()
    intent["areas"] = _extract_area_mentions(question)

    if any(word in lowered for word in ("compare", "versus", " vs ", "against")) and len(intent["areas"]) >= 2:
        intent["intent"] = "compare"
    elif intent["areas"]:
        intent["intent"] = "area_detail"
    else:
        intent["intent"] = "overview"

    if any(word in lowered for word in ("rent", "rental", "tenant")):
        intent["topic"] = "rent"
    elif any(word in lowered for word in ("sale price", "median sale", "buy", "mortgage", "purchase")):
        intent["topic"] = "price"
    elif any(word in lowered for word in ("homeless", "emergency accommodation", "housing insecurity")):
        intent["topic"] = "homelessness"
    elif any(word in lowered for word in ("planning", "dwelling completion", "supply", "urban planning", "pipeline")):
        intent["topic"] = "supply"
    elif any(word in lowered for word in ("density", "dense", "urban spread", "population pressure")):
        intent["topic"] = "population_density"
    elif any(
        word in lowered
        for word in (
            "housing pressure",
            "pressure",
            "classification",
            "affordable housing",
            "affordability",
            "housing stress",
            "smart housing",
        )
    ):
        intent["topic"] = "housing_pressure"

    if "next year" in lowered or "in a year" in lowered:
        intent["horizon_months"] = 12
    else:
        match = re.search(r"\b(\d{1,2})\s*months?\b", lowered)
        if match:
            intent["horizon_months"] = int(match.group(1))

    return intent


def extract_intent(question: str) -> dict:
    client = _get_client()
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "").strip()

    if not client or not deployment:
        return _heuristic_intent(question)

    try:
        response = client.chat.completions.create(
            model=deployment,
            messages=[
                {"role": "system", "content": INTENT_SYSTEM_PROMPT},
                {"role": "user", "content": question},
            ],
            temperature=0,
        )
        content = response.choices[0].message.content or "{}"
        parsed = _extract_json(content)
    except Exception:
        return _heuristic_intent(question)

    intent = _base_intent()
    allowed_topics = {
        "housing_pressure",
        "price",
        "rent",
        "homelessness",
        "population_density",
        "supply",
    }
    allowed_intents = {"overview", "area_detail", "compare"}

    areas = parsed.get("areas") or []
    if isinstance(areas, list):
        intent["areas"] = [area for area in areas if isinstance(area, str) and area.strip()]

    topic = parsed.get("topic")
    if topic in allowed_topics:
        intent["topic"] = topic

    intent_name = parsed.get("intent")
    if intent_name in allowed_intents:
        intent["intent"] = intent_name

    horizon = parsed.get("horizon_months")
    intent["horizon_months"] = int(horizon) if isinstance(horizon, (int, float)) else None

    if not intent["areas"]:
        intent["areas"] = _extract_area_mentions(question)
    if intent["intent"] is None:
        intent["intent"] = "compare" if len(intent["areas"]) >= 2 else ("area_detail" if intent["areas"] else "overview")
    if intent["topic"] is None:
        intent["topic"] = _heuristic_intent(question)["topic"]

    return intent
