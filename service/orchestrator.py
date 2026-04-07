from prediction_store import lookup_prediction
from render import render_prediction
from llm_client import call_llm


def parse_question(question: str):
    """
    Very simple intent parser for now.
    This can be improved later without changing orchestration logic.
    """
    q = question.lower()

    city = "Galway" if "galway" in q else None
    prediction_type = "median_price" if "price" in q else None
    horizon = 12 if ("year" in q or "12" in q) else None

    return city, prediction_type, horizon


def answer(question: str):
    city, prediction_type, horizon = parse_question(question)

    prediction = lookup_prediction(city, prediction_type, horizon)

    if prediction:
        # 🔒 HARD GUARANTEE:
        # If a prediction exists, the LLM is NEVER called.
        return render_prediction(prediction)

    # ✅ Only reached when NO model output exists
    return call_llm(question)


if __name__ == "__main__":
    print("Housing Prediction Assistant (retrieval-first)")
    print("Type your question, Ctrl+C to exit\n")

    while True:
        q = input("> ")
        print(answer(q))
        print()
