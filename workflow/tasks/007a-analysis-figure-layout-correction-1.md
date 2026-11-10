# Goal
Correct only notebook 12 OOF-method plot layout after actual visual review.

# Context
Read AGENTS.md. Task 007 actual notebook completed (18.36 seconds), isolated replay completed (18.6 seconds). All reconciliation checks passed, but both fig_oof_methods_daily.png and fig_oof_methods_6h.png visibly clip their long title and x-label disclosure that the axis does not start at zero. Original run 20261110-220240-6856 was rejected for this layout issue only. No worker active. This is correction round 1 for 007. Notebook11 completed successfully and is immutable.

# Scope
Only backend/notebooks/12_v2_evaluation_error_analysis.ipynb plotting cell, or an ignored checked payload/applier under .ai-team/handoffs/007a. Use line breaks/shorter truthful wording and layout to keep title and axis disclosure inside both images. No changes to FUNCTIONS, statistical logic, config, locks, notebook11, tests unrelated to layout, or existing generated reports. Codex will archive the initial analysis outputs then run again.

# Acceptance
Both method plots show full title, all method names and full disclosure that the horizontal axis starts above zero. Every other code cell unchanged. All metrics and choices identical on rerun. Original task007 requirements remain applicable: research only, no fits/network/reselection, input hashes protected, daily/6h separate, identical evaluation keys, error slices/calibration/ablations/drift with support.

# Verification requested
Provide exact old/new cell hashes and checked mechanical applier if needed. Codex runs pytest, notebook12, hash comparison and visual inspection. Do not execute shell/Git or edit generated evidence.

# Report
List changed files, changes made, checks actually run, checks not run, remaining issues.
