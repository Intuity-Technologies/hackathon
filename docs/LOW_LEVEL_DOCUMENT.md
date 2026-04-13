# Low Level Design

## 1) ETL Implementation Units

- `etl/transform/normalize_population.py`
  - Produces `population_growth`, `area_name`, `time_period`, `area_level`.
- `etl/transform/normalize_rents.py`
  - Produces `rent_growth`, `area_name`, `time_period`, `area_level`.
- `etl/transform/normalize_planning.py`
  - Produces `housing_completions`, `area_name`, `time_period`, `area_level`.
- `etl/transform/build_signals.py`
  - Joins curated inputs, computes all score fields, writes parquet + `latest.json`.
- `etl/tests/check_signals_contract.py`
  - Validates required columns, score range, minimum area/period coverage.

## 2) Score Computation Contract

For each `time_period`:

- `population_growth_score = minmax(population_growth) * 100`
- `rent_pressure_score = minmax(rent_growth) * 100`
- `supply_gap_score = 100 - minmax(housing_completions) * 100`
- `overall_housing_pressure_score = 0.2*population_growth_score + 0.4*rent_pressure_score + 0.4*supply_gap_score`

Class thresholds:

- `Critical >= 80`
- `High pressure >= 60`
- `Watchlist >= 40`
- `Stable < 40`

Additional derived features:

- `dominant_driver = argmax(population_growth_score, rent_pressure_score, supply_gap_score)`
- `time_index` from `YYYYQn` or `YYYY`
- `score_qoq_change` as first difference by `area_name`
- rolling averages: `score_4q_avg`, `rent_growth_4q_avg`, `population_growth_4q_avg`
- `score_rank_in_period` descending dense rank by overall score
- `score_percentile_in_period` percentile rank by overall score
- `model_feature_version = v1`

## 3) Physical Outputs

- `${SIGNALS_FILE_SYSTEM}/${SIGNALS_FILE_PATH}`
- `${SIGNALS_FILE_SYSTEM}/${SIGNALS_LATEST_JSON_PATH}`

Both are created from the same final dataframe in `build_signals.py`.

## 4) API Retrieval Contract

Defined in `api/function_app.py`:

- `GET /api/health`
- `GET /api/areas` (latest period summary rows)
- `GET /api/area/{name}` (latest period detail row)
- `GET /api/model/schema` (feature list + target column metadata)
- `GET /api/model/features` (latest period model-ready feature rows)
- `GET /api/model/features?time_period=YYYYQn` (explicit period feature rows)

Model feature column set:

- `population_growth`
- `rent_growth`
- `housing_completions`
- `population_growth_score`
- `rent_pressure_score`
- `supply_gap_score`
- `overall_housing_pressure_score`
- `score_qoq_change`
- `score_4q_avg`
- `rent_growth_4q_avg`
- `population_growth_4q_avg`
- `score_percentile_in_period`

## 5) Refresh Mechanics

Workflow: `.github/workflows/refresh-data.yml`

- Trigger:
  - weekly schedule: Monday at `05:00` UTC
  - manual dispatch
- Steps:
  - resolve blob input paths
  - run normalization scripts
  - run `build_signals.py`
  - run contract check
  - verify API can read latest signals

## 6) LLM Interaction Pattern

- Retrieve from API, do not recalculate ETL scores inside prompt logic.
- Build responses from:
  - current score state (`overall`, `classification`, `driver`, `rank`, `percentile`)
  - trend context (`qoq`, `4q averages`)
  - raw evidence (`rent_growth`, `population_growth`, `housing_completions`)

This keeps responses explainable, reproducible, and aligned with pipeline outputs.
