from __future__ import annotations

import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from flask import Flask, jsonify, redirect, render_template, request, session, url_for

from service.housing_data import (
    compare_areas,
    get_area_detail,
    get_leaderboard,
    get_overview,
    get_sources_manifest,
    list_available_areas,
)
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
    overview = get_overview()
    leaderboard = get_leaderboard()
    areas = list_available_areas()
    featured_area = get_area_detail(overview["featured_counties"][0]["area_name"])
    default_compare = compare_areas(areas[:2])
    return render_template(
        "index.html",
        messages=messages,
        overview=overview,
        leaderboard=leaderboard,
        available_areas=areas,
        featured_area=featured_area,
        default_compare=default_compare,
        sources_manifest=get_sources_manifest(),
    )


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
