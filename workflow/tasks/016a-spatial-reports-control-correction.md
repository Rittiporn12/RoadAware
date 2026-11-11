# Goal — correction round 1 of task016

Read AGENTS.md, workflow/claude-implementation-only-th.md and original workflow/tasks/016-spatial-count-experiments.md. Preserve every original experiment requirement. Fix the actual reports-stage failure, add meaningful regression coverage, and provide a worker-authored notebook assembler. Claude writes ALL code; Codex only plans, inspects, assembles through your script and runs checks. No other worker is active.

# Current context and observed failure

Original worker run20261111-140025-2040 implementation was checkpointed e352a6f. Actual fresh-root experiment backend/rerun-spatial-model-016-001 ran3286.74s, completed temporal fits/OOF, frozen selection, seen-year diagnostics and spatial transfer, then failed at reports cell14. Read the runner log reports/v3/run_manifest_spatial_experiments.json there, but avoid full executed notebooks/large arrays. Source payload .ai-team/handoffs/016/cell_14_reports.py contains routing_trigger_excludes_bank_calendar_and_labels using substring 'y_' not in c. Permitted aadt_mean_heavy_share_pct contains y_ inside heavy_share, causing a false failure. Formal Codex review FAIL is recorded. No final CSVs, arrays_index, figures or complete manifest were generated. Existing saved arrays and frozen selection are NOT an accepted experiment. Preserve failed run unchanged.

27 fixtures previously passed but missed this pipeline check. Codex independently checked OOF metrics/labels and seen-year labels before failure; do not change models, sampling, splits, predictors, baselines, selection, seeds or thresholds based on observed scores. Read workflow/spatial-experiment-interface-v3.md for actual output interfaces. Other queued tasks14/21/22/API are not in this correction scope.

# Allowed scope

- Modify notebook20 source payloads in .ai-team/handoffs/016/ and backend/notebooks/20_spatial_count_experiments.ipynb only for this correction; prefer payloads and let Codex assemble using your new tool.
- Modify backend/tests/test_spatial_experiments_notebook.py; add narrowly scoped new tests for the assembler if needed.
- NEW tools/assemble_notebook_payloads.py, a generic mechanical nbformat-v4 assembler accepting the existing notebook_cells.json format. Report exact invocation. Reject duplicate IDs, invalid cell types/missing files, unsafe targets/path escapes/symlinks; sources must remain exact file contents, target must be explicit approved backend/notebooks notebook, no arbitrary overwrites outside this scope. Keep execution out of assembler. Do not change bridge or dependencies.
- Optional NEW verification-only script under backend/scripts if needed to independently compare actual saved y arrays against existing .ai-team/references/016-label-oracles/*.npy and report hashes/shape/exact equality without executing producer FUNCTIONS or changing any artifacts. If provided, scope input paths explicitly and report command.
- No changes to configs, protocols, manager pins, accepted notebooks09–19, accepted data/reports/models, failed output root or frontend/API. No runtime dependency on .ai-team in application/ML logic (assembler handoff input is development-only).

# Acceptance criteria

1. Replace the faulty substring heuristic with an explicit, defensible validation of routed-trigger columns against allowed additional weather/AADT predictors, excluding target/outcome/identifier/bank-calendar columns. Do not merely force the check true or remove it. Share the actual validation used by the report stage with meaningful fixtures. Configured daily and6h triggers must pass; actual label/target/event-coordinate/identifier/bank-calendar additions must fail; the legitimate heavy-share feature must pass.
2. Preserve all scientific behavior and every original acceptance requirement. No retuning or selection changes. New tests exercise the exact report validation path that failed rather than a separate look-alike expression.
3. Source payload order and canonical notebook can be mechanically assembled with exact sources by the worker-authored tool, Python3.9 compatible, no inline Python authored by Codex needed. Explain command and any canonical notebook handling.
4. Codex will inspect actual diff, run targeted fixtures/full backend tests and then a NEW full experiment root backend/rerun-spatial-model-016-002. Do not implement recovery that silently reuses unverified arrays, edits completed status or bypasses checks. No tests claimed passed unless actually run; worker has file tools only, Codex runs commands.
5. Report any other concrete issues discovered in reporting, without expanding scientific scope. Original >=3 actual-result figures, CSV/array hashes, complete manifest/protected-input checks must all succeed on the rerun before acceptance.

# Verification requested and report

Provide changed files, exact assembler/test/run commands, implementation rationale, checks actually run, checks not run, remaining issues. Read relevant source chunks only; no huge notebook outputs or data dumps. Do not ask routine permission. At most this correction and one further correction are available under AGENTS.md; be precise.
