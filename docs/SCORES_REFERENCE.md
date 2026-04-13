# Housing Signals Score Reference

This reference defines the metrics produced by the ETL pipeline (used in `latest.json` and parquet) and how they should be used by an LLM retrieval layer.

## Why These Fields Exist

- Raw metrics (`rent_growth`, `population_growth`, `housing_completions`) capture observed market conditions.
- Normalized component scores make areas comparable in the same period.
- Composite and ranking fields support prioritization, triage, and narrative generation.
- Trend fields support forward-looking risk discussion without re-running ETL logic in the LLM.

## Field Definitions (Formula + Use)

| Field | Definition / Formula | How to Use in LLM Responses | Benefit |
|---|---|---|---|
| `population_growth` | YoY % population change for area. | Explain demand-side pressure. | Grounded demand signal. |
| `rent_growth` | YoY % rent change for area. | Explain affordability pressure. | Direct affordability stress indicator. |
| `housing_completions` | Housing supply delivered (count/proxy from planning pipeline). | Explain supply-side relief or shortage. | Supply context for pressure interpretation. |
| `population_growth_score` | `minmax(population_growth by time_period) * 100` | Compare area demand pressure to peers in same period. | Comparable 0-100 scale. |
| `rent_pressure_score` | `minmax(rent_growth by time_period) * 100` | Compare affordability pressure to peers in same period. | Comparable 0-100 scale. |
| `supply_gap_score` | `100 - minmax(housing_completions by time_period) * 100` | Higher means weaker supply vs peers. | Converts supply into pressure direction. |
| `overall_housing_pressure_score` | `0.2*population_growth_score + 0.4*rent_pressure_score + 0.4*supply_gap_score` | Primary headline pressure metric. | Single prioritization score. |
| `classification` | Thresholds on overall score: `>=80 Critical`, `>=60 High pressure`, `>=40 Watchlist`, else `Stable`. | Human-readable risk band. | Fast triage and summarization. |
| `dominant_driver` | Max of component scores (`Population growth`, `Affordability`, `Supply gap`). | Answer “why is this area pressured?” | Built-in explainability. |
| `time_index` | Time sort key (`YYYYQn -> year*4 + q`; `YYYY -> year*4`). | Correctly order time-series narratives. | Stable chronological sorting. |
| `score_qoq_change` | Quarter-over-quarter delta of overall score by area. | Describe acceleration/deceleration in pressure. | Momentum signal. |
| `score_4q_avg` | 4-quarter rolling average of overall score by area. | Distinguish persistent vs short-term spikes. | Smoother trend context. |
| `rent_growth_4q_avg` | 4-quarter rolling average of `rent_growth`. | Describe sustained affordability trend. | Reduces quarter noise. |
| `population_growth_4q_avg` | 4-quarter rolling average of `population_growth`. | Describe sustained demand trend. | Reduces quarter noise. |
| `score_rank_in_period` | Dense rank of overall score within period, descending (`1 = highest pressure`). | Answer “where does this area rank right now?” | Clear relative ordering. |
| `score_percentile_in_period` | Percentile rank of overall score in period (`0-100`, highest near `100`). | Answer “top X% pressure area?” | Intuitive peer positioning. |
| `model_feature_version` | Feature schema tag (current `v1`). | Validate model/retrieval schema compatibility. | Prevents feature drift issues. |
| `explanation_summary` | ETL-generated natural-language summary. | Use as baseline narrative and augment with context. | Consistent first-pass explanation. |

## Interpretation Rules (Important)

- Scores are **relative within each `time_period`**, not absolute across all time.
- High percentile means high pressure **vs peers in that period**.
- `score_rank_in_period` and `score_percentile_in_period` should be used together in responses.

## What the LLM Should Retrieve First

For an area-level answer, retrieve:

1. Current period: `overall_housing_pressure_score`, `classification`, `dominant_driver`, `score_rank_in_period`, `score_percentile_in_period`.
2. Trend context: `score_qoq_change`, `score_4q_avg`, `rent_growth_4q_avg`, `population_growth_4q_avg`.
3. Driver evidence: `population_growth_score`, `rent_pressure_score`, `supply_gap_score` plus raw metrics.

This produces answers that are both explainable and statistically grounded.
