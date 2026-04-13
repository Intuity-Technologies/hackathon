# Dataset to field mapping

## 1. population.parquet
Source:
- CSO Census / population tables from data.cso.ie

Fields:
- area_name
- area_level
- time_period
- population_growth

Transformation:
population_growth = (latest_population - baseline_population) / baseline_population

## 2. rents.parquet
Source:
- RTB / ESRI Rent Index
- CSO Housing Hub rents references

Fields:
- area_name
- area_level
- time_period
- rent_growth

Transformation:
rent_growth = (latest_rent_index - prior_year_rent_index) / prior_year_rent_index

## 3. prices.parquet
Source:
- CSO Residential Property Price Index

Fields:
- area_name
- area_level
- time_period
- price_growth

Transformation:
price_growth = (latest_price_index - prior_year_price_index) / prior_year_price_index

## 4. planning.parquet
Source:
- Department of Housing planning registers
- CSO Home Building / completions where suitable

Fields:
- area_name
- area_level
- time_period
- planning_approvals
- housing_completions

## 5. overburden.parquet
Source:
- CSO affordability / SILC housing cost burden outputs

Fields:
- area_name
- area_level
- time_period
- housing_cost_overburden_rate

Note:
May only be available at regional level.

## 6. homelessness.parquet
Source:
- Department of Housing monthly Homelessness Reports

Fields:
- area_name
- area_level
- time_period
- homeless_count
- homeless_rate

Transformation:
homeless_rate = homeless_count / population * 1000