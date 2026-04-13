# Reviewer Demo Guide

This prototype is designed for a short judged walkthrough that proves technical depth, transparency, and usability.

## 1. Run The Prototype

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt -r requirements-dev.txt -r etl/requirements.txt -r api/requirements.txt
$env:PYTHONPATH="."
python etl\transform\build_demo_artifacts.py
python web.py
```

Open `http://127.0.0.1:5000`.

## 2. Suggested 5-Minute Demo Flow

1. Start on the dashboard hero and explain that county housing pressure is deterministic and refreshed from scored artifacts.
2. Show the leaderboard to highlight which counties are currently under the greatest housing pressure.
3. Open the county drilldown for `Mayo` or `Dublin` and call out:
   - composite score and classification
   - dominant driver
   - trend line
   - county, regional, and national context cards with clear scope labels
4. Use the compare panel for `Cork` vs `Galway` or `Dublin` vs `Mayo`.
5. Ask the assistant a retrieval-first question such as:
   - `What is the latest housing pressure classification for Mayo?`
   - `Compare Cork and Galway for affordable housing pressure.`
   - `Which counties are under the highest housing pressure right now?`
6. Close by showing `docs/ETHICS_AND_LIMITATIONS.md` or the evidence panel to explain fairness, transparency, and accountability choices.

## 3. What To Emphasize

- The county score is deterministic and explainable.
- Context signals are separated by scope instead of being mixed into the score without justification.
- The same artifact layer powers the dashboard, API, and assistant.
- The same judged UI can run from checked-in local artifacts or from Azure-hosted `signals` and `demo` artifacts provisioned by the Bicep stack.

## 4. Supporting Technical Evidence

- ETL and demo artifact build: `etl/transform/`
- Shared evidence layer: `service/housing_data.py`
- API surface: `api/function_app.py`
- UI shell: `templates/index.html`
- Contracts: `contracts/`
- CI: `.github/workflows/ci.yml`

## 5. Validation Commands

```powershell
$env:PYTHONPATH="."
python -m compileall api etl service model web.py
ruff check .
pytest
python etl\transform\build_demo_artifacts.py
```
