# RoadAware model experiment protocol v1

Locked before model fitting on 2026-11-09. User requires three distinct models,
with Baselines reported separately. Start interpreting Poisson first; train all
three families to satisfy the latest requirement. Do not reuse old model weights.

## Scope and data

- Retrospective conditional research on the existing reported-province/day panel.
  This is NOT the route model or a verified as-of operational forecast experiment.
- Input: backend/data/processed/province_day_panel.csv and the verified source,
  interim and split manifests, plus data leakage readiness report.
- Readiness remains BLOCKED. training_eligible is an offline cohort filter known
  after observing quality problems; its future availability is NOT established.
  Conditioning on it introduces selection bias. Never call these clean prospective
  forecasts, claim a personal crash probability or turn production on.
- All methods use the same eligible cells. Flags/outcomes/IDs/split/timestamps are
  not features. No historical lags, target-day reanalysis, traffic or holidays.
- Features: existing allowlist only: province, day_of_week, month, day_of_month,
  day_of_year, is_weekend. All learned preprocessing fitted on each fold's Train.
- Dataset preparation and masks remain unchanged. Do not resolve ambiguous dates
  by assumption or tune cleaning based on model scores.

## Baselines and candidates

Baselines: zero (sparsity diagnostic only), global Train mean, province Train
mean with global fallback, province×weekday mean smoothed toward province mean
with 10 pseudo-observations. Means come only from the fitted fold.

Distinct candidate families:

1. PoissonRegressor: alpha 0.0001, 0.01, 1.0; log-link; one-hot all six input
   features; handle_unknown=ignore; max_iter=1000, tol=1e-6.
2. RandomForestRegressor with criterion='poisson', random_state=42, n_jobs=2,
   max_features=0.7: (80 trees, depth12, max_leaf_nodes64, min_samples_leaf50)
   and (120 trees, depth16, max_leaf_nodes128, min_samples_leaf100).
   One-hot province/weekday/month/weekend and pass through day/month-of-year
   numeric fields (day_of_month and day_of_year).
3. HistGradientBoostingRegressor with loss='poisson', learning_rate=0.05,
   early_stopping=False, random_state=42: (120 iterations, 15 leaves,
   min_samples_leaf50, l2=1) and (160 iterations, 31 leaves,
   min_samples_leaf100, l2=5). OrdinalEncoder fitted on Train for province,
   weekday/month/weekend, unknown_value=-1; explicitly declare these columns
   categorical, pass through day_of_month/day_of_year as numerical.

No extra hyperparameter search, target encoding, automatic random early-stopping
split, calibration using future data, or old artifacts. Record convergence warnings.

## Temporal evaluation

Four expanding-window backtests within original Train:

| Fold | Evaluation targets |
| --- | --- |
| 1 | 2022-01-01 through 2022-06-30 |
| 2 | 2022-07-01 through 2022-12-31 |
| 3 | 2023-01-01 through 2023-06-30 |
| 4 | 2023-07-01 through 2023-12-31 |

Fit uses only eligible original-Train rows whose target_end <= first evaluation
issue_time. Evaluation uses eligible rows in the stated interval. Explicitly
assert disjoint keys and labels ending before first issue. This handles label
boundaries; it does NOT prove historical publication availability.

Pool out-of-fold predictions from these four folds for tuning/selection. After
selection fit every specified method on the same eligible original Train, then
report 2024 validation and 2025 reused-test diagnostics separately, using the
same frozen models. Never refit on 2024, use 2026 as labels, or change the winner
from 2024/2025 scores. Neither later year is an independent untouched test.

Coverage must be visible: 2024 has 7,885 eligible province-days and zero eligible
targets in October–December; July/September have only 3/2 distinct eligible dates.
Scores describe selected cells, not complete annual or road coverage.

## Metrics and decision

- Primary: pooled row-weighted mean Poisson deviance on identical OOF cells.
- Secondary: MAE, RMSE, aggregate WAPE (null when observed sum=0), signed bias,
  predicted/observed totals, per-fold and monthly behavior, runtime.
- Zero baseline: report raw MAE/RMSE and totals; Poisson deviance=null because
  exact zero is outside the metric's domain. Never silently score it as positive.
- For other methods, explicitly floor predicted means at 1e-9 ONLY when needed
  for Poisson deviance, record number floored; raw predictions for MAE/RMSE/bias.
  Reject nonfinite or negative predictions and invalid labels.
- Best configuration per family = lowest pooled OOF deviance; exact ties use ID.
  Selected candidate = lowest pooled OOF deviance across all three families;
  exact ties prefer Poisson, then Random Forest, then HGB, then config ID.
- Compare selected candidate with strongest nonzero baseline. Describe stable
  gain only if deviance improves >=1%, MAE is <=baseline MAE×1.02, deviance improves
  in >=3 of 4 folds, and the upper 95% paired block-bootstrap CI of the deviance
  difference is <0. Bootstrap is exploratory and not adjusted for model selection.
  Otherwise retain strongest baseline as the recommended current reference while
  still identifying the best of the three candidates for the user's comparison.
- Paired moving-block bootstrap: 7 CALENDAR days, 500 replicates, seed42;
  reindex full OOF date range, keep day row-count weights, resample same day blocks
  for candidate/baseline. Missing dates have weight0, not observed zero outcomes.
- Save selected candidate, baseline comparison and recommended reference before
  later-year diagnostic scoring; verify choice/hash unchanged afterwards.

## Analysis and evidence

Report coverage, monthly/province/day-of-week errors, high-count vs zero-count
errors, observed-vs-predicted totals, calibration bins with support, largest
aggregate residual groups, and comparative tradeoffs. Missing groups have null
metrics, never a fake perfect score. Outcome-defined slices are diagnostic, not
features or evidence of causal effects. No weather/holiday effects claimed.

All business logic in Python .ipynb for VS Code, with executed outputs, meaningful
fixture tests and reproducible headless execution without a Jupyter website.
Save local full predictions/model bundles, tracked aggregate CSV/JSON/PNG,
config/source/data hashes, package versions, fit warnings and model-selection
rationale. Keep UI/Dashboard deferred and checkpoint GitHub at meaningful stages.

Primary method references: [Poisson](https://scikit-learn.org/1.6/modules/generated/sklearn.linear_model.PoissonRegressor.html),
[Random Forest](https://scikit-learn.org/1.6/modules/generated/sklearn.ensemble.RandomForestRegressor.html),
[HGB](https://scikit-learn.org/1.6/modules/generated/sklearn.ensemble.HistGradientBoostingRegressor.html),
[Poisson deviance domain](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.mean_poisson_deviance.html).
