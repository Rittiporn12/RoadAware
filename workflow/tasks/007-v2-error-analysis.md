# Goal

Implement notebook 12 for independent reading and analysis of the completed V2
experiment. The user needs inspectable experiment results, error analysis and
reasons for model choice, including feature additions that did not help. This
is research analysis, not the future web Dashboard or route-risk interface.

# Preconditions / context

Manager status 2026-11-10 22:02: single worker006 finished; no other Claude
worker. 09 source correction and10 preparation independently ACCEPTED. Actual10
has106308 retained records,140602daily/5624086h cells; all8data/24report hashes
identical on isolated replay. 11 assembled,19model fixtures+50V2fixtures PASS,
protocol/config/input hashes locked in workflow/model-protocol-v2-lock.json.
Codex has STARTED actual11 kernel; model results are PENDING, not accepted.
Implement12 now against11's declared interface; NO11/config/lock changes while
it runs, no invented metrics or fit claims. Use read-only source aid
.ai-team/references/notebook11-source-current.txt to avoid hugeipynb Read failure.
Actual source weather204/385province-years,2021/22all77,2023first50;2024/25no
weather. Retrospective2024 labelmask only7885/28182daily cells. Explicit in
analysis. READMEs may now truthfully mark09/10 accepted research-only;11pending.

Delegate only after task 006 implementation finishes, using its exact output
interface. Codex may still be running notebook 11; implementation may proceed
against its schema, but execution requires a successful and independently
verified experiment run. Read AGENTS.md, the locked model protocol, accepted
09/10 evidence, actual 11 config/source and its next_stage_interface. No second
Claude worker. File tools only; Codex runs commands and independently reviews.

# Allowed scope

New backend/notebooks/12_v2_evaluation_error_analysis.ipynb, new focused fixture
tests backend/tests/test_v2_analysis_notebook.py, extend existing V2 runner with
an explicit evaluate stage for 12 only, truthful README status. Generated tracked
aggregate reports/plots under reports/v2/analysis. No fits or changes to notebook
11, its chosen models/config/protocol/selection lock, 09/10, V1, frontend or API.
Large local row diagnostics only ignored data/v2/analysis. Use ignored payloads
and checked assembler if necessary; all final business logic inside .ipynb.

# Acceptance criteria

1. Fresh-kernel, self-contained FUNCTIONS cells. Validate experiment completion,
   exact input/output hashes and selection lock before reading predictions.
   Read-only dependencies hashed before/after. No network, fitting, reselection
   or data/config changes. Fail missing files/tampering rather than inventing
   results. Keep daily and 6h panels separate.
2. Independently recompute metrics from raw local predictions; reconcile to 11
   aggregates within explicit numeric tolerance and fail mismatches. All family
   winners and strongest baseline visible; show the decision gate, paired
   exploratory bootstrap interval, per-fold wins and reasons for recommendation.
3. Error slices with support, actual/predicted totals, signed bias, MAE/RMSE and
   deviance: year/month, province, weekday, 6h block, Songkran/New Year windows,
   bank-calendar coverage and weather/traffic availability. Include zero and
   high-count cells as retrospective outcome-defined slices. Missingness flags
   in this analysis are diagnostics only, never input features or causal claims.
   Prevent small/empty slices from being framed as reliable effect estimates.
4. Observed-vs-predicted calibration bins with support (stable repeated values,
   no qcut crash), largest aggregate residuals, actual-vs-predicted time series
   and ablation comparisons against the same method/core on identical keys.
   Cover benefits and harms; no cherry-picking. Later-year temporal drift and
   source-coverage shifts described explicitly. Source availability alone is
   not evidence of a feature effect.
5. Modest readable PNG figures, Thai explanation and updated model card/report
   linking to the actual data/fold/metric tables. Clearly distinguish OOF
   selection, previously seen 2024 development and 2025 reused diagnostics.
   No untouched-test, all-road, personal-risk, production or deployed-Web claims.
   If no candidate beats the baseline gate, explain this plainly and retain the
   protocol's baseline recommendation; do not tune or change the winner.
6. Reproducible manifest with code/config/input/output hashes, package versions,
   actual checks, caveats and production_ready=false. Tiny hand-calculated tests
   for metric reconciliation, weighted slice totals, calibration ties/empty
   slices, paired keys and tamper rejection. Codex executes actual notebook and
   visually inspects saved plots. Never list checks not run as passed.

# Worker report

List changed files, checks actually run, checks not run, exact execution commands,
interface/output paths, known issues and remaining steps. No shell, Git, paid
services, deployment or additional workers. Do not alter a running 11 notebook.
