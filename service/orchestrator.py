from prediction_store import lookup_prediction
from render import render_prediction

def parse_question(question: str):
    # VERY simple for now (can expand later)
    q = question.lower()
    city = "Galway" if "galway" in q else None
    prediction_type = "median_price" if "price" in q else None
    horizon = 12 if "year" in q else None
    return city, prediction_type, horizon


def answer(question: str):
    city, prediction_type, horizon = parse_question(question)

    prediction = lookup_prediction(city, prediction_type, horizon)

    if prediction:
        # 🔒 LLM IS NEVER CALLED HERE
        return render_prediction(prediction)

    return "No model prediction available for this question."


if __name__ == "__main__":
    while True:
        q = input("> ")
        print(answer(q))
