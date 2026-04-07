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
  "topic": "price" | "rent" | null,
  "horizon_months": number | null
}

Rules:
- Use "price" for anything about house prices, costs, affordability, or how expensive housing is.
- Use "rent" only for rental-related questions.
- Use null if the value cannot be confidently inferred.
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