# Ethics And Limitations

## Design Principles

- Fairness: county scores are calculated from consistent pipeline logic instead of ad hoc prompting.
- Transparency: every area response exposes freshness, provenance, scope, and supporting signals.
- Accountability: regional and national indicators are labeled as context only and are not silently blended into county scores.

## What The Prototype Does Not Do

- It does not generate unsupported numeric estimates for a county when retrieval evidence is unavailable.
- It does not treat regional homelessness or national affordability measures as if they were county-equivalent data.
- It does not present future forecasts as current-state facts.

## Scope Labels

- `County`: eligible for direct comparison inside the composite housing-pressure workflow.
- `Region`: relevant context, but not blended into the county score.
- `National`: system-wide context for affordability, supply, or homelessness trends.

## Risk Controls

- Current-state housing answers are retrieval-first.
- The assistant falls back to general qualitative language only when structured evidence does not cover the request.
- Demo artifacts are generated locally and checked into a stable shape for testing and presentation.

## Responsible Interpretation

- A high county score indicates pressure within this composite framework, not a full policy diagnosis.
- Context cards should be used to support discussion, not to imply causation on their own.
- Reviewers and users should interpret the prototype as decision support, not as an automated policy decision engine.
