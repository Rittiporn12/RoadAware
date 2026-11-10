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

Current execution evidence is recorded below; final acceptance remains pending.

## Resumed run setup (2026-11-10)

If Read rejects the large executed notebook, Codex extracted its CURRENT cell
sources verbatim to `.ai-team/references/notebook06-source.txt` (no outputs).
Read that small reference in chunks. It is a reading aid, not a separate module.
Use Write on the actual notebook when implementing fixes. Preserve actual source
cells; stale failed execution outputs may be cleared for pending rerun.
At02:01 Codex cleared ONLY the existing notebook06 stale outputs/execution
counts as setup to reduce Read size. All cell sources were asserted unchanged;
backup `.ai-team/references/notebook06-precheck-executed.ipynb` preserves old
evidence. Retry Read on actual notebook if needed; then Write implementation.
At02:06 Codex validated and transferred your authored
`06_baseline_candidate_models.ipynb.continuation` VERBATIM onto the actual06
path as artifact handoff (no Codex source edits). You need not rewrite06 again.
Codex is executing it. Finish tests/docs and report the tooling handoff candidly.

## Continuation runtime evidence (2026-11-10 02:07)

Actual06 now PASSED all13 code cells in42.45s. All44 fold fits and11 full-Train
fits statusok, zero warnings. Reload max8.88e-16, repeated-prediction max1.33e-15,
all within declared1e-12. Both final manifests statusok. Choice remains Poisson
alpha1e-4, same original decision_sha25663aeb272...; choice_sha2564781bb5a....
Codex independently recomputed all11 OOF methods' metrics with sklearn (match
1e-12); OOF42058/count24448; all33 watched data/report hashes unchanged.
Original54 data tests passed0.73s. NEW model tests still pending worker.
Do not overwrite executed06; your .continuation has already been applied exactly.

## Model fixture execution feedback (02:08, same run)

`.venv/bin/python -m pytest backend/tests -q`:96 passed,1 failed in5.88s.
Failure test_nonconverged_and_failed_fits_are_ineligible_not_scored line293:
unknown family svm correctly returns statusfailed but error is KeyError:'svm'
(encoding lookup precedes final family branch), not 'unknown model family'.
Fix the overly specific test to assert failed/error and refusal to predict,
or add a deliberate family validation only if truly necessary; do not rewrite06
just for an error string and invalidate already verified sources unnecessarily.
Other tests including all3 fresh-interpreter reload fixtures passed. Codex also
verified actual11 bundle hashes/reload totals and all manifest/source hashes in
a fresh interpreter. One sandbox loky core-count warning, no failed predictions.

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

## User decision after quota interruption

The user chose to wait for Claude's reset and keep the original division of
roles. Codex is NOT authorized to take over implementation. Code and evidence
are backed up at59186ad. On resumption, delegate a bounded continuation to
Claude: fix the RF numerical reload check, complete model tests and notebook06
verification, then implement evaluation/error-analysis notebooks07-08. Preserve
the locked protocol and candid later-year/cohort-shift findings. Do not restart
the project or treat the partial model task as accepted.
