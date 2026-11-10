# Goal

First bounded correction for006: fix the mutable runner-log hash dependency in
notebook11 reporting and align12 completion verification. No statistical change,
no new configurations, no tuning. Codex will run a clean full experiment again
if necessary; preserve the first attempt and disclose the correction.

# Context / observed defect

Only previous worker007 has finished. Read AGENTS.md and its report
.ai-team/runs/20261110-220240-6856/result.json plus current feedback. Actual11
kernel is STILL RUNNING six-hour OOF. DO NOT EDIT actual11/config/protocol/lock
or move any live artifact. Worker may author a checked exact patch payload;
Codex applies it ONLY AFTER kernel exits. Notebook12 has authored payloads under
.ai-team/handoffs/007; not yet assembled. Source09/prepare10 accepted/frozen.

Independent static finding and007 report agree:11 report cell17 builds
report_outputs from every REP file except model_manifest.json, thereby hashing
run_manifest_model.json. The runner rewrites that file after every cell. Thus
the next final-check cell18 sees a changed hash and fails. This is metadata/log
bookkeeping, not an observed model-score failure. Do not claim actual11 passed.

# Allowed changes

- Checked targeted patch to11 REPORT cell only: exclude mutable runner logs
  from immutable report_outputs (exact known filenames, do not exclude metrics,
  selection locks or real evidence). No FUNCTIONS/model/split/fitting cells
  changed; verify their byte hashes unchanged before applying.
- backend/scripts/run_v2_notebooks.py: put model runner log OUTSIDE model report
  dir, e.g. output/reports/v2/run_manifest_model.json (same pattern as analysis).
  Setup changes can be applied while the old runner process runs; no live files
  moved/rewritten by worker. New clean run must retain accurate actual status.
- Corresponding12 helper payload and tests: validate the new canonical runner
  log path (model report parent), accept legacy report-local path when present;
  require available canonical/legacy model runner status ok before analysis.
  Do not waive model completion or ignore real mismatches. No model manifests
  altered to pretend an unexecuted check passed.
- Focused regression fixtures in backend/tests/test_v2_model_notebooks.py and
  test_v2_analysis_notebook.py; truthful README update only if needed.
- Ignored patch/applier under .ai-team/handoffs/006a (compile/layout guards and
  exact old-string occurrence required; idempotent, refuse other changes).

# Acceptance / verification

1. REPORT manifest no longer hashes a mutable runner log. Every genuine report
   remains hashed. Tests create a runner log, mutate it between report/final
   checks, and prove no false dependency; changing metrics still fails.
2. Current11 statistical FUNCTIONS and all fit/selection/diagnostic cells stay
   byte-identical. Config/protocol/data/selection criteria unchanged. Codex may
   amend only the extra notebook-source hash in the manager lock AFTER current
   attempt exits, recording old/new and report-only diff; do not edit it yourself.
3.12 uses proper canonical completion log, rejects failed/running/missing status
   and verifies every immutable report/output hash. Fixture both root layouts.
4. Codex assembles12/applies patch when safe, runs focused+regression tests, then
   archives failed first attempt without deleting evidence and runs clean11.
   Full rerun is allowed only with the identical locked statistical settings;
   observed scores cannot change features, hyperparameters or thresholds.
5. Worker lists changed files, actual checks (file-tools only: none), checks not
   run, exact apply/test/run commands, known issues. No shell/Git/subagents or
   changes to live model artifacts. Read feedback before finishing.
