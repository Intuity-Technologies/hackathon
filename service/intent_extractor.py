import json
import os
import re

from dotenv import load_dotenv
from openai import AzureOpenAI

load_dotenv()

CLIENT = None


INTENT_SYSTEM_PROMPT = """
You extract structured intent from housing questions.

Return ONLY valid JSON matching this schema:
{
  "city": string | null,
  "topic": "price" | "rent" | "homelessness" | "population_density" | null,
  "horizon_months": number | null
}

Rules:
- Use "price" for anything about house prices, housing costs, affordability, or how expensive buying a home is.
- Use "rent" for questions about renting, rental prices, or cost of renting.
- Use "homelessness" for questions about homelessness, rough sleeping, housing insecurity, or emergency accommodation.
- Use "population_density" for questions about how dense, urban, or spread out a city is.
- Only set "horizon_months" if the question clearly refers to a future time (e.g. "next year", "in a year").
- Use null if a value cannot be confidently inferred.
- Do NOT include explanations or extra text.
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
    return {"city": None, "topic": None, "horizon_months": None}


def _extract_json(text: str) -> dict:
    cleaned = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, flags=re.DOTALL)
    if fenced:
        cleaned = fenced.group(1)

    payload = json.loads(cleaned)
    if not isinstance(payload, dict):
        raise ValueError("Intent payload must be a JSON object.")
    return payload


def _heuristic_intent(question: str) -> dict:
    lowered = question.lower()
    intent = _base_intent()

    county_matches = re.findall(
        r"\b(carlow|cavan|clare|cork|donegal|dublin|galway|kerry|kildare|kilkenny|"
        r"laois|leitrim|limerick|longford|louth|mayo|meath|monaghan|offaly|"
        r"roscommon|sligo|tipperary|waterford|westmeath|wexford|wicklow)\b",
        lowered,
    )
    if county_matches:
        intent["city"] = county_matches[0].title()

    if any(word in lowered for word in ("rent", "rental", "tenant")):
        intent["topic"] = "rent"
    elif any(word in lowered for word in ("price", "buy", "home cost", "mortgage")):
        intent["topic"] = "price"
    elif any(word in lowered for word in ("homeless", "emergency accommodation")):
        intent["topic"] = "homelessness"
    elif any(word in lowered for word in ("density", "dense", "population spread")):
        intent["topic"] = "population_density"

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
            temperature=0,  # consistency > creativity
        )
        content = response.choices[0].message.content or "{}"
        parsed = _extract_json(content)
    except Exception:
        return _heuristic_intent(question)

    intent = _base_intent()
    allowed_topics = {"price", "rent", "homelessness", "population_density"}

    city = parsed.get("city")
    topic = parsed.get("topic")
    horizon = parsed.get("horizon_months")

    intent["city"] = city if isinstance(city, str) and city.strip() else None
    intent["topic"] = topic if topic in allowed_topics else None
    intent["horizon_months"] = int(horizon) if isinstance(horizon, (int, float)) else None

    return intent
