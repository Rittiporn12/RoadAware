# Live model-stage review feedback

This file is Codex's verification channel for the currently running bounded task.
Read it before final reporting as required by the task. Do not alter the locked
protocol or parameter grid based on observed scores.

## COMPLETED: task003b / notebook08 — ACCEPTED

Final verification2026-11-10: allClaude-authored patches applied verbatim and
report/plot artifacts regenerated;143tests passed8.36s; full06/07/08rerun passed
42.63/8.11/6.16s. Compared30CSV524columns within1e-12 (maxabs2.27e-13), exact
choicehash/keys,22diagnostic and618group independentoraclespassed, dataunchanged.
Workerfinalreportread and formalreviewPASS recorded. See model-final-verification-th.md.
Remaining notes below are chronological history, not open implementation tasks.
Research Model phase complete; production/routeforecast remainsBLOCKED bydata.

### LIVE08 TOOLING HANDOFF (08:07)

Codex recovered your FOUR failed Edit requests VERBATIM from run events and
applied their exact old_string/new_string pairs to08 (each matched exactlyonce).
This fixes your walrus line and three boolean expressions exactly as YOU authored.
All08codecells now compile. Do NOT rewrite the whole08file again: changes applied.
Source-only reading aid `.ai-team/references/notebook08-source-current.txt` exists.
Read this live feedback now, finish runner/tests/docs, and report handoff. If
further edits are needed, write small JSON old_string/new_string patch requests
to `backend/notebooks/08_patch_handoff.json` for Codex to apply VERBATIM, avoiding
huge full notebook rewrites. Allowed as a tooling handoff only; do not execute.

### Actual08 runtime/review (08:08, same run)

After the4verbatim edits, realanalysis07->08 PASSED:07=8.46s,08=13cells4.79s,
modelcard/decision/error manifest statusok;06+07artifacts unchanged during08.
Do NOT rewrite entire08. Two precise report wording fixes needed as small JSON
patch handoff before final:
1. Modelcard currently says 'ข้อแลกเปลี่ยนบน OOF: ... MAE ต่ำสุด' but this is
only among the THREE primary-metric-frozen familybest configs. Acrossall7configs,
HGB160 has MAE0.561516, below HGB1200.563377. Qualify explicitly 'ในสาม
configuration ที่ล็อกจากแต่ละตระกูลตาม primary metric' (or report both). Do not
change choice/metrics. Current unqualified 'lowest' statement is misleading.
2. Card says 'Train eligible2021-01-01–2023-12-31', but actualeligiblelastdate
is2023-12-29. Use COH actual target_date min/max, or explicitly label configured
split date range and actual eligible range separately. Recorded source dates
must match actual support. Write exact authored replacements to08_patch_handoff.json.
No runtime defects otherwise observed yet; independent618group checks pending.
Independent618group checks now PASSED within1e-12 (province/yearmonth/weekday/
outcome bins); fullTrain early14001rows/2407count and1168positive diagonal rows
match; calibration bin totals correct;08outputhashes/06+datahashesverified.
VisualQA: province scatter/calibration readable. cleaning_regime_shift.png last
two xlabels 'reused_test_2025' overlap: shorten display names to e.g.'2025 reused'
or rotate/space labels via a small authored patch; do not alter data. No Thai
font is needed currently because plots use numeric province scatter, not Thai
province labels. Modelcard text fixes above remain necessary.
At08:09 fulltests with08 fixtures:143 PASSED in7.99s. No failed runtime tests.
Once the report/plot patch handoff is written Codex will apply it verbatim,
rerun analysis and full06-08 independent outputroot, then post final evidence.
Do not mark the entire task accepted before those final checks.

Both06 and07 are ACCEPTED.07checkpoint68893ec: actual12cells8.3s,
128tests7.97s,22independent oracle comparisons passed,61upstreamhashesunchanged.
07 initial run timedout only during finalREADME; correction1 report accepted.
Implement08 only as its task contract; earlier pending/failure notes are history.
Source-only references06/07 exist under.ai-team/references for small Read.
Do not modify06/07 or frozen model/diagnostic files. New08 should have no outputs
until Codex runs it. Update runner and its stage fixture for07->08; README
VSCode RunAll order should now be01->08 (data01-05 thenmodels06-08).
Next-run timeout is3000s (budget/tools unchanged), extended because07 took20min
and was interrupted only at docs. Keep work bounded; prioritize required08 over
optional permutation sensitivity, which may be omitted with reason.
For date-regime diagnostics distinguish full eligible originalTrain63,757 rows
from OOF42,058 rows. FullTrain day1-12 positive rows1168 are all day==month;
mean0.171916 vsday13-31 mean0.686369. Recompute frompanel; if errors areOOF-only,
label themOOF separately rather than confusing fullTrain counts withOOF errors.
Visual QA: province labels are Thai. This Mac has Thonburi/Sarabun/Tahoma fonts
(confirmed read-only font inventory). Prefer an available Thai font discovered
with matplotlib.font_manager for province plots; keep English axis labels and
fallback if unavailable. Do not install fonts/dependencies. Avoid unreadable
missing-glyph boxes in plots; Codex will inspect PNGs after execution.
Verification scope: runner `--stage analysis` legitimately re-executes07 then08.
07 diagnostics/run timestamps may therefore change BEFORE08 starts. During08,
all06/07 artifacts must stay byte-identical to08's own before snapshot. Across
the whole analysis rerun,06/lock must remain exact,07 source semantic hash exact,
and07 metrics/predictions numerically equivalent. Do not accidentally treat a
normal07 execution's runtime/timestamp changes as tampering in08.

## Current stage: task003a / notebook07 (2026-11-10)

Task002/002a is ACCEPTED:97 tests passed5.77s, actual06 all13 cells42.45s,
all hashes/reloads/metrics verified. GitHub checkpointd41f08f. Earlier failure
notes below are historical and resolved. Implement only07 now. Read06 source
via `.ai-team/references/notebook06-source-current.txt` to avoid oversized
executed .ipynb Read errors. Actual06 remains authoritative, DO NOT modify it.
Runner hash in06 is provenance, not immutable-current-runner requirement (the
runner must be extended for07). All06 model/data/lock files stay immutable.
Use simple new notebooks with no outputs initially so Write succeeds.

### Actual07 verification (07:43, same run)

Codex executed `.venv/bin/python backend/scripts/run_model_notebooks.py --stage analysis --timeout 900`:
all12 code cells PASSED in8.3s, diagnostic manifest statusok. Independent sklearn
oracle computed BEFORE07 matches all22 method/year metric combinations within
1e-12; coverage60months and2024Q4null correct. All61 watched data/model/evidence
files unchanged, including06 notebook and selectionlock.07 output hashes verified.
No source changes to07 after this execution yet. Do not rewrite07 outputs/source
unless needed for a real defect. New07 fixture tests still pending completion.
At07:44 Codex ran full suite after your new tests:128 PASSED in7.97s.
Visual inspection of diagnostic_main_deviance.png passed (readable, later-year
reversal visible). No runtime defects found. Finish docs/final report only;
07 acceptance can follow independent final source/hash consistency check.

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
