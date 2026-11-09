# Live model-stage review feedback

This file is Codex's verification channel for the currently running bounded task.
Read it before final reporting as required by the task. Do not alter the locked
protocol or parameter grid based on observed scores.

## Setup verified

- Protocol committed/pushed BEFORE training: 1059257.
- .venv installed: Python3.9.6, scikit-learn1.6.1, scipy1.13.1, joblib1.5.3,
  threadpoolctl3.7.0, pandas2.3.3, numpy2.0.2.
- Latest user explicitly requires three real tested families, not counting
  Baselines: Poisson, Random Forest, HGB. All three must be trained here.
- Existing data masks/readiness remain unchanged. Work is conditional,
  retrospective research, not proof of issue-time availability or route safety.

## Current findings

No model code has been executed yet. Codex will append specific runtime findings
here if found. Treat absent execution as pending, never passed.

## Independent fold-scope verification (2026-11-09)

Codex inspected the four proposed fold cutoffs. Each fit cohort already has
positive eligible recorded events in ALL 77 evaluation provinces, so the
full-Train province universe does not introduce future-only provinces in these
actual inner backtests. Actual fit-row counts by evaluation start:
2022-01-01:21622; 2022-07-01:32297; 2023-01-01:43354; 2023-07-01:53211.

Record/audit this in fold support (derive known provinces from positive past
labels, not merely the panel's province column). Keep unknown-category fallback
tests, but do not imply a future-only spatial scope was evaluated as known in
the real experiment. Original issue-time data-availability caveat still applies.

Expected eligible evaluation support derived independently from the unchanged
panel: fold1=10675 rows/6623 labels sum; fold2=11057/6425;
fold3=9855/5825; fold4=10471/5575. Total OOF rows per complete method=42058,
total recorded count=24448. Original full eligible Train has 63757 rows.
Strictly parse eligibility booleans; never use bool('False') on CSV strings.

## Actual runtime findings (2026-11-09 21:59 Bangkok)

Claude session limit stopped task002 after writing06 and model runner. Tests,
requirements/docs and later-stage notebooks were not written. No final worker
report of completed task exists; result text reports the session limit.

Codex executed real06 to /private/tmp/roadaware-model-precheck-v1. All44 fold
fits and all11 full-Train fits succeeded without warnings. OOF42,058 rows and
count24,448 match independently computed support. Metrics independently match
sklearn for all11 methods. Strongest candidate by locked primary metric is
poisson_alpha_1e-4; strongest baseline is baseline_province_mean.

Notebook fails at cell17's np.array_equal reload check for the larger forest.
Independent repeated predictions from the SAME forest differ at most
1.7763568394002505e-15 (allclose rtol=atol=1e-12 passes). Parallel floating-point
summation order is the issue, not a demonstrated corrupted bundle. Required
bounded fix: record maximum absolute reload difference and verify numerical
agreement at an explicit tight tolerance (e.g.1e-12), retaining rejection of
meaningful differences. Do not change the model configuration or hide failures.
Rerun full notebook after fixing, including final manifests and immutable lock.

Current verification: original data fixture tests54 passed; tiny synthetic fits,
unknown-category and bundle reload smoke checks passed all3 families. New
meaningful model fixture tests remain pending. No model task acceptance yet.
