# V2 experiment protocol — frozen before fitting

Prepared before v2 fitting. The companion model-protocol-v2-lock.json records
accepted notebook10 input hashes and the final model configuration. This file
retains its original draft filename for the recorded dependency interface;
once the companion lock is written its exact bytes are frozen. No results yet.
User requests three candidate models, a serious baseline comparison, feature
enrichment and evidence runnable as VS Code Python notebooks. No guaranteed win.

## Cohort and units
Use accepted v2 preparation outputs only. Daily province count is primary;
province x6-hour block is a separate experiment. Same eligible keys for every
method/feature variant within each unit; missing external features never drop
rows per model. No comparison of raw daily vs6h errors as if the target matched.
Offline quality masks remain outcome-derived; sources cover recorded MOT-network
events, not complete all-road accidents. Production=false, research only.
V1 and its selected Poisson stay frozen. V2 has a repaired cohort: report shared-
key comparison separately if claiming numerical improvement over V1.
Accepted preparation: 106308 retained records, 140602 daily cells and 562408
6h cells; 116973 eligible daily cells. The 2024 research mask retains only
7885/28182 daily cells, so that diagnostic is strongly selected. Current archived
weather covers all provinces in 2021/22 and 50 provinces in 2023; 2024/25 weather
features are unavailable, never backfilled. Weather ablations therefore test
this partial collection and its shift, not complete five-year weather coverage.

## Feature variants (fixed before fitting)
Use explicit approved columns from10, forbidden outcome/ID/mask columns rejected.
All models receive the same variant's information; deterministic transforms such
as log1p(AADT) allowed, learned encoders/imputers/scalers fitted inside Train.
Poisson/RF numeric imputers use add_indicator=false: no extra source-quality or
collection-coverage predictors beyond the declared feature groups. HGB keeps
native missing handling; retrospective source coverage can still confound its
splits and must be diagnosed, not presented as proven availability at issue.

1. core: province +date calendar/cyclical features (+block for6h).
2. calendar: core +festival/bank-calendar/season features.
3. calendar_weather: calendar +archived48h-lead JMA forecasts.
4. calendar_traffic: calendar +prior available DOH annual survey summaries.
5. full: calendar +weather +traffic.

No incident weather, involved-vehicle count, injury/cause/type, raw IDs/dates,
source status or retrospective label-quality flags as predictors. Traffic means
are covariates, NOT a validated exposure denominator/Poisson offset. Historylags
remain separate pending research scenario; no silent current/future labels.
Weather/calendar/traffic availability policies from v2-feature-policy apply.

## Three candidate families / bounded configurations
Proposed fixed configurations per variant (final parameters lock before fitting):

- PoissonRegressor alpha0.001 and0.01, max_iter1000,tol1e-6; onehot categorical
  inputs, train-only imputation/standardization for numeric inputs. All-missing
  train features preserved; record convergence warnings, don't ignore silently.
- RandomForestRegressor criterion=poisson,80trees,max_depth18,max_leaf_nodes128,
  min_samples_leaf50,max_features0.8,random_state42,n_jobs2. Onehot categoricals,
  train-only numeric imputation; no ordinal geography distance implied.
- HistGradientBoostingRegressor loss=poisson,160iterations,max_leaf_nodes15,
  min_samples_leaf100,l2_regularization5,learning_rate0.05,early_stopping=false,
  random_state42. Train-only categorical encoding declared categorical, numeric
  missing handled explicitly/native. Record fitted features and unknown levels.

This is a bounded comparison plus ablation, not endless tuning against later
years. If practical runtime justifies adjustment, revise and lock BEFORE fits,
not after observing model scores. No reuse of old model weights.

## Strong baselines (separate from the three models)
Fit from each fold's Train only; identical evaluation keys:
zero(sparsitydiagnostic), globalmean, provincemean, province-weekday smoothedk10,
province-month smoothedk30, and recent90-calendar-day provincemean with full-
Train/global fallback. For6h use province-block parent and province-block-weekday/
month smoothing and recent90province-block; globalfallback may respectblock
only if fitted on Train and explicitly defined in final lock. Zero has no finite
Poisson-deviance score; report raw MAE/RMSE/totals, don't silently turn0positive.
Recent90baseline frozen at fold start, no evaluation-label updates.

## Chronological evaluation and decision
Same expanding Train backtests:2022H1,2022H2,2023H1,2023H2. Fit labels end no
later than first evaluation issue time (previousday18:00Bangkok); report exact
boundaries, disjointkeys, support/exclusions. Publication availability of original
accident snapshots is still unknown; boundary guards don't prove operationality.

Pool OOF predictions, row-weighted mean Poisson deviance primary. Secondary MAE,
RMSE,WAPE(null ifsumy0),bias,totals,runtime,coverage. Reject negative/nonfinite
predictions; floor at1e-9 ONLY for deviance, report floor counts. Raw predictions
for other metrics. Select best configuration/variant per family by OOF deviance
(ties configID). Best candidate across three families by same metric, ties prefer
Poisson,RF,HGB thenID. Select strongest nonzero baseline by pooledOOF deviance.

Stable-gain gate:>=1% deviance reduction, MAE<=1.02*baseline, wins>=3/4folds,
paired7-calendar-day blockbootstrap500(seed42) upper95%CI for deviance difference
<0. Bootstrap is exploratory after model/variant selection, not adjusted for
multiple comparisons. If gate fails recommend strongest baseline as reference
while showing best of the three candidate families and reasons.

Freeze selection/choicehash BEFORE2024/2025 diagnostics. Fit specified methods
on originalTrain2021-23 only; no refit on2024, no winner change from2024/25 scores.
For this final diagnostic fit, also exclude any training cell whose target end
is after the first 2024 issue time (2023-12-31 18:00 Asia/Bangkok): the full
2023-12-31 daily cell and its 18-24 block are unavailable at that issue. Record
the actual final cutoff and excluded cell count; never fit those future labels.
Both later years were seen earlier; no untouched test exists. Report failures,
coverage gaps, missingness shifts and temporal drift. A win on research folds
doesn't authorize a production route/personal-risk forecast.

## Evidence and error analysis
All business logic Python.ipynb (planned11 training/12 evaluation-analysis), .py
runner/tests only, freshkernelVSCode. Full local predictions/bundles ignored;
tracked aggregate metrics/fold tables/ablation deltas/plots/modelcard/manifests.
Input/config/notebook/source hashes, package versions, warnings, elapsedtime,
reload-prediction consistency, selectionlock verified before/after diagnostics.

Analyze bymonth/province/weekday/block/festival/weather/trafficmissingness,
highcount vszero, calibration bins withsupport and largest aggregate residuals.
Outcome-defined slices are retrospective diagnostics, not predictors/causes.
Feature benefit compares methods on identical keys; sourcecoverage sensitivity
must use the same declared fixedkeys for all comparators and remain separate.
Report feature variants that harm performance, not just the best result.
