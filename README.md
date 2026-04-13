Setup
1. Environment variables
You’ll be provided with a private .env file containing the Azure OpenAI agent credentials.
Place the file in the repo root:
.env

(No changes required inside the file.)

2. Start the application
From the repo root:
Shellpython web.pyShow more lines
Flask will start and print a local URL, typically:
http://127.0.0.1:5000

Open this in your browser to use the chat interface.

Using the Assistant
You can ask questions about any housing metric that exists in the artifact store, for a specific location and time period.
Example prompts (artifact‑backed)

Housing stress

“What was housing stress in Carlow in 2018Q1?”
“What was the housing stress score for Carlow in early 2018?”


Drivers & classification

“What was driving housing stress in Carlow in 2018Q1?”
“What cluster was Carlow in during 2018?”


Rent & arrears

“What was the predicted rent level in Carlow in 2018Q1?”
“What was the predicted arrears rate in Carlow at the end of 2018?”


Supporting signals

“What was rent growth in Carlow in 2018Q1?”
“What was population growth in Galway last year?”
“How many housing completions were there in Carlow in early 2018?”



If an answer can be produced from an artifact, it will always be deterministic and consistent.
If not (e.g. vague, incomplete, or abstract questions), the system returns an AI‑generated response with a warning.

Notes

Artifacts live in data/processed/ and are the sole source of deterministic answers.
The LLM is used only for intent parsing and fallback generation.
The LLM never processes or modifies artifact data.