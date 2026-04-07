from prediction_store import lookup_prediction
from render import render_prediction
from llm_client import call_llm
from intent_extractor import extract_intent


def answer(question: str):
    # 1️⃣ Extract structured intent using LLM (JSON only)
    intent = extract_intent(question)

    city = intent["city"]
    topic = intent["topic"]
    horizon = intent["horizon_months"]

    # 2️⃣ Map topic → prediction type
    prediction_type = None
    if topic == "price":
        prediction_type = "median_price"
    elif topic == "rent":
        prediction_type = "rent"

    # 3️⃣ Deterministic lookup
    prediction = lookup_prediction(city, prediction_type, horizon)

    if prediction:
        # 🔒 HARD GUARANTEE:
        # If a prediction exists, the LLM is NEVER used for answers
        return render_prediction(prediction)

    # ✅ LLM fallback only when no artifact exists
    return call_llm(question)


if __name__ == "__main__":
    print("Housing Prediction Assistant (retrieval-first)")
    print("Type your question, Ctrl+C to exit\n")

    while True:
        q = input("> ")
        print(answer(q))
        print()