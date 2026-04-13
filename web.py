import os

from flask import Flask, jsonify, redirect, render_template, request, session, url_for

from service.orchestrator import answer

MAX_SESSION_MESSAGES = 30

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "local-dev-only-secret-key")


def _ensure_messages() -> list[dict[str, str]]:
    messages = session.get("messages", [])
    if not isinstance(messages, list):
        messages = []
    session["messages"] = messages
    return messages


def _trim_messages(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    if len(messages) <= MAX_SESSION_MESSAGES:
        return messages
    return messages[-MAX_SESSION_MESSAGES:]


@app.route("/", methods=["GET"])
def index():
    messages = _ensure_messages()
    return render_template("index.html", messages=messages)


@app.route("/api/ask", methods=["POST"])
def api_ask():
    messages = _ensure_messages()

    payload = request.get_json(silent=True) or {}
    question = payload.get("question") or request.form.get("question", "")
    question = str(question).strip()
    if not question:
        return jsonify({"ok": False, "error": "Empty question"}), 400

    messages.append({"role": "user", "content": question})

    reply = answer(question)

    messages.append({"role": "assistant", "content": reply})
    session["messages"] = _trim_messages(messages)
    session.modified = True

    return jsonify({"ok": True, "reply": reply})


@app.route("/clear", methods=["POST"])
def clear():
    session.pop("messages", None)
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)
