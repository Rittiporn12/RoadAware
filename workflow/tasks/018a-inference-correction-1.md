# Goal: correction 1 of at most 2 for task018

Read AGENTS.md and workflow/tasks/018-spatial-serving-contract.md. Preserve ALL original runtime/parity/trust/robustness acceptance criteria and no-refit restriction. Claude remains sole code/test author; Codex runs checks. Do not re-read entire history or change accepted19/20/21, manager pins, models, data or thresholds.

# Actual verification and source findings

Codex assembled exact018payloads into notebook22. `.venv/bin/python -m pytest backend/tests/test_spatial_inference_notebook.py backend/tests/test_assemble_notebook_payloads.py -q`: **50 passed, 2 failed in4.39s**. Both failures at test_live_parity_mixture_and_future line267, expected40context+40core but actual saved diagnostic mask has core only. This was already an accepted limitation: 2024/25 all context unavailable -> core fallback. Do not change source data/mask or pretend context was observed.

Source inspection: ServingError.__init__ in FUNCTIONS1 uses `[int(r) for r in (rows or [])]`. Callers pass `np.flatnonzero(...)`. An ndarray with multiple entries raises ambiguous-truth ValueError; `[0]` loses row0. Thus multi-row pre-asof/invalid requests can become artifact_unavailable rather than intended invalid code. Normalize rows explicitly without ndarray truth. Add meaningful regressions for 2+ offending rows, mixed good/bad rows, row0, both units and selected/baseline response codes/indices; requests should remain atomic with no partial predictions.

# Allowed changes

Only018payloads/source22, inference tests/config/runner/verifier/runbook as needed for these findings; assembler files only if necessary. Keep notebook source and payload hashes/spec synchronized (Codex assembles). Do not write source notebook with huge NotebookEdit batches. No model fits, refits, reselection, accepted artifact edits, network, memory writes, API or2026work.

# Acceptance / requested verification

1. Real saved-array parity test derives expectations from actual saved mask for sampled offsets and explicitly reports actual core-only scope. Preserve numeric equality <=1e-12 and future-date/order/strictJSON checks. Add a separate **clearly synthetic fixture** exercising context-complete/core fallback/mixed routing through runtime path; assert both component outputs and reasons, same feature schema/preprocessors. Syntheticfixture must never be presented as real observed2024/25evidence. No arbitrary skipping failing assertions.
2. Fix rows normalization and cover above invalid batches including stable invalid/coverage families, preserved indices and no partial output. Add same multi-row probe to independent live verifier or actual robustness pipeline so this is exercised outside pytest too.
3. Reinspect remaining018integration paths for concrete related blockers before handoff; keep bounded scope. Codex will run targeted/full tests, actual fresh018-001 and verifier. None of these are yet run/passed. Full parity against all saved diagnostic cells remains required; no OOF runtime replay claim.

# Report

Changed files, exact assembly/test/runner/verifier commands, checks actually run (worker no shell), checks not run, remaining limits. Do not self-accept. Do not change manager pins or existing results.
