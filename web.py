
from flask import Flask, request, render_template, session, redirect, url_for, jsonify
from service.orchestrator import answer

app = Flask(__name__)
app.secret_key = "demo-secret-key"

@app.route("/", methods=["GET"])
def index():
    if "messages" not in session:
        session["messages"] = []
    return render_template("index.html", messages=session["messages"])

@app.route("/api/ask", methods=["POST"])
def api_ask():
    if "messages" not in session:
        session["messages"] = []

    question = request.form.get("question", "").strip()
    if not question:
        return jsonify({"ok": False, "error": "Empty question"}), 400

    # store user message
    session["messages"].append({"role": "user", "content": question})

    # compute reply (artifact or LLM)
    reply = answer(question)

    # store assistant message
    session["messages"].append({"role": "assistant", "content": reply})
    session.modified = True

    return jsonify({"ok": True, "reply": reply})

@app.route("/clear", methods=["POST"])
def clear():
    session.pop("messages", None)
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)
