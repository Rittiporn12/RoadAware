# Goal
Correction round 1 of catalog020. Read AGENTS.md, workflow/claude-implementation-only-th.md and original020-historical-catalog-v3.md (all acceptance requirements remain). Claude authors all code; Codex executes and reviews. No concurrent worker.

# Observed evidence
Notebook14 assembled exactly. Targeted tests:44pass/1fail in test_real_config_and_notebook_contract: snapshot assertion rejects any string containing spatial_experiments, including legitimately protected scripts/run_spatial_experiments.py. Inspect snapshot_rels actual output; ensure output run roots excluded but source config/notebook/runner/tests protected.
Actual backend/rerun-historical-catalog-020-002 completed recovery/province/spatial tables then failed cell12 run_query_controls: no UID-like strings in spatial results expected0 observed4. Read relevant error in reports/v3/run_manifest_historical_catalog.json and cell_06_functions_5.py, not whole executed notebook. Inspect whether real event UIDs leaked or the regex mistakes stable public segment IDs/dates for event UIDs. Preserve failed output unchanged. Sandbox-only020-001 failed opening kernel port and is unrelated.

# Scope
Only020 handoff payloads, canonical notebook14 (unexecuted), catalog_v3 config if necessary, focused catalog/assembler tests and NEW backend/scripts/verify_historical_catalog.py verification-only script. No accepted16-20 sources or results, no API/evaluation/serving implementation. Narrow docs allowed. No shell/network/worker launches.

# Acceptance
- Fix actual defects with shared controls exercised by regression tests, no force-true/removing privacy checks. Explicit public result schema and actual retained UID leakage detection: public stable segment IDs permitted; event_uid/source_row/individual accident coordinates/narratives forbidden recursively. Include counterexamples with actual UID-shaped strings and forbidden nested keys. Fail real leaks, tolerate legitimate IDs/date strings.
- Snapshot assertion must distinguish runtime outputs from protected source files; test actual configured snapshot membership and output-root exclusion.
- Preserve all catalog/raw-recovery/history/cutoff requirements. No model or data edits. Provide exact assembler/test/fresh-run commands. Canonical notebook can be mechanically assembled by Codex after worker ends.
- Supply a small read-only verification CLI that verifies real accepted producer hashes and catalog outputs, independently compares recovered descriptions against pinned raw/lineage data and legacy oracle (do not call catalog recovery to verify itself), reconciles province monthly/category and selected27459 daily/6h totals and as-of query examples. It may use original preflight .ai-team/references/catalog_raw_enrichment_preflight.py as a disclosed independent development aid, never runtime dependency. Avoid saving new raw rows; aggregate evidence only. Read input schemas from actual config. CLI can save bounded JSON evidence if explicit output path. Never exec unverified code. Include all checks not run honestly.
- Inspect report/final-load stage which was not reached, resolve other concrete issues in scope now, not arbitrary refactor.

# Verification and report
Codex will inspect diff; assemble; targeted/full suite; NEW backend/rerun-historical-catalog-020-003 actual kernel; independent verifier and graph review. Worker report changed files, real interfaces, commands actually run(none), commands not run, remaining issues. Do not alter permissions or memory files.
