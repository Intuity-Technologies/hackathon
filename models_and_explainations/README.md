Housing Stress Modelling & Explainability Framework
Overview:
This project develops a county-level housing stress model for Ireland, combining rental data,
population growth, housing supply, and mortgage arrears. The aim is to quantify housing pressure
and provide interpretable, policy-relevant insights.
Data Integration:
Four datasets were combined:
- Signals (rent growth, population growth, housing completions)
- RTB rents (average rent levels)
- Property Price Index (market trends)
- Mortgage arrears (financial stress indicators)
All datasets were standardised to county level and quarterly time format.
Feature Engineering:
Key features include rent growth, population growth, housing completions, rent level, arrears rates,
and property price indices.
Modelling:
A Poisson GLM was used to model arrears:
arrears ~ rent_growth + population_growth + log(housing_completions) + cluster
Clustering:
Counties were grouped into similar housing regimes using K-means clustering.
Housing Stress Score:
A composite score combines:
- 40% arrears pressure
- 40% rent pressure
- 20% supply pressure
Explainability:
Three explanation types were created:
1. Factual – current situation
2. Semi-factual – near improvements
3. Counterfactual – required changes
Example:
To move from Watchlist to Stable:
- Reduce rent growth by ~2.3 percentage points OR
- Increase housing supply by ~18.6%
Ethical & Interpretability Benefits:
- Transparent model (GLM)
- No personal data used
- Clear explanations for each prediction
- Policy-relevant outputs
Conclusion:
This framework provides an interpretable, ethical, and practical tool for analysing housing stress
and supporting decision-making.