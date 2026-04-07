from openai import AzureOpenAI
import os

client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version="2024-02-15-preview",
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
)

SYSTEM_PROMPT = """
You are a housing analysis assistant.

RULES:
- You may NOT generate numerical housing predictions.
- If no model prediction exists, explain qualitatively and clearly.
- If you are unsure, say so.
"""

def call_llm(question: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4o-mini",  # use whatever deployment name you have
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question}
        ],
        temperature=0.2
    )
    return response.choices[0].message.content
