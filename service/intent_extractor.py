import os
from openai import AzureOpenAI
import json

client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version="2024-02-15-preview"
)

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

def extract_intent(question: str) -> dict:
    response = client.chat.completions.create(
        model=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
        messages=[
            {"role": "system", "content": INTENT_SYSTEM_PROMPT},
            {"role": "user", "content": question}
        ],
        temperature=0,  # important: consistency > creativity
    )

    return json.loads(response.choices[0].message.content)
