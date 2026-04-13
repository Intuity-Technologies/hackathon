import os
import json
from openai import AzureOpenAI

client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version="2024-02-15-preview"
)

INTENT_SYSTEM_PROMPT = """
You extract structured intent for a housing data system.

Return ONLY valid JSON matching this schema:
{
  "area": string | null,
  "field": string | null,
  "time_period": string | null
}

Rules:
- "area" is the county or city being asked about (e.g. Galway, Carlow).
- "field" must be one of the following artifact fields:
  [
    "predicted_classification_glm",
    "pred_housing_stress_score",
    "cluster_label",
    "dominant_model_driver",
    "pred_rent_level",
    "pred_arrears_90d_rate",
    "rent_growth",
    "population_growth",
    "housing_completions"
  ]
- "time_period" must be a specific quarter like "2018Q1", "2023Q4".
- If the user says "last year", infer the most recent complete year, Q4.
- If the user says "early 2018", infer "2018Q1".
- Use null only if the value cannot be confidently inferred.
- Do NOT include explanations or extra text.
"""

def extract_intent(question: str) -> dict:
    response = client.chat.completions.create(
        model=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
        messages=[
            {"role": "system", "content": INTENT_SYSTEM_PROMPT},
            {"role": "user", "content": question}
        ],
        temperature=0
    )

    return json.loads(response.choices[0].message.content)