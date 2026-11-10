# Goal
Implement ONLY notebook07 and its tests/runner/docs as the first bounded half of workflow/tasks/003-model-evaluation-analysis.md. Read that FULL contract; all relevant integrity, frozen selection, support and metric requirements apply. Do not implement08 in this run.

# Current context
Notebook06 was independently executed on actual data:44 fold fits and11 full fits passed, final manifests statusok. Real artifacts exist under backend/data/model and backend/reports/models. Read workflow/model-training-verification-th.md and live workflow/model-review-feedback.md. Use06 helpers as frozen source. Do not Read the huge executed notebook directly: source-only reading aid `.ai-team/references/notebook06-source-current.txt` is provided by Codex. The actual notebook remains authoritative for hashing and extraction.

# Allowed changes
Add backend/notebooks/07_evaluation_experiment_results.ipynb. Extend backend/tests/test_model_notebooks.py, backend/scripts/run_model_notebooks.py, backend/notebooks/README.md, backend/README.md and root README only. No06/config/protocol/model/data-foundation changes. No08, shell, git, deployments or new dependencies. All business logic lives in notebook07; tests/runner may be .py. Small aggregate reports generated at runtime only, row predictions ignored data/model.

# Acceptance
Requirements1-5,10-13 of003 apply to07. Strictly verify data/config/protocol/source hashes and statusok model manifests, all file/bundle hashes BEFORE loading trusted own bundles. Current runner hash in06 manifest is provenance: runner will necessarily change to support07; do not require old runner bytes to equal current runner. Record actual runner provenance separately. Verify semantic06 and its FUNCTIONS hash exactly. Verify lock bytes and decision/choice hashes before/after scoring. All11 frozen methods evaluated on identical eligible2024/2025 cells; zero deviance null, no diagnostic2026, no refit. Main table frozen best3 + strongest baseline + zero, detailed allconfig table, coverage all60 historical months incl2024Q4 zero support/nullscores. Metric recomputation assertions, finite JSON, honest research caveats and later-year ranks. No new winner from later-year scores.

Runner supports --stage train(06), analysis(07 for now), all(default06->07); task003b later extends to08. New07 standalone from fresh kernel using same env/output-dir/data-root semantics. Stage analysis does not refit or replace06 artifacts. Version/hash/status manifests and usable output contracts for08 required. Tests: hand metrics, missing support/nulls, frozen picks unaffected by later ranks, identical-key/eligibility joins, source/artifact/hash tampering and lock mutation rejection. Never claim unrun tests passed.

# Verification requested
Codex will inspect diff, run all tests, execute07 using actual06 bundles, independently recompute saved diagnostic metrics and confirm immutable input/model/lock hashes. Codex then accepts this bounded task before launching08. Read live feedback before final/docs and fix concrete same-run issues.

# Final report
Changed files, checks run/not run with exact commands, manifest/prediction schema for08, unresolved limitations. End after07; no speculative frontend/API.
