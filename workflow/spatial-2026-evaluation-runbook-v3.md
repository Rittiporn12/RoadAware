# Runbook: notebook 23 — 2026 raw observed-record audit + positive-cell diagnostic (task 023)

Research only (`production_ready = false`). No training, refit, reselection, tuning, API, network or deploy.

## Inputs (manager pins, never edited by the worker)
- `workflow/serving/accepted-runtime-v3.json` — accepted notebook-22 runtime (files + joined FUNCTIONS sha).
- `workflow/evaluation-2026/source-pins-v3.json` — new CKAN snapshot, saved package metadata, original CSV.
- `workflow/evaluation-2026/linkage-pins-v3.json` — notebook 18 file + joined FUNCTIONS sha, config18, road manifest, province points.
- Config: `backend/config/spatial_2026_evaluation_v3.json` (window 2026-01-01..2026-09-30, exclusive ledger order, grouping calendar, metric rules).

## Commands (repository root; Codex runs them)
```
.venv/bin/python tools/assemble_notebook_payloads.py --spec .ai-team/handoffs/023/notebook_cells.json --target backend/notebooks/23_2026_record_diagnostics.ipynb
.venv/bin/python tools/assemble_notebook_payloads.py --spec .ai-team/handoffs/023/notebook_cells.json --target backend/notebooks/23_2026_record_diagnostics.ipynb --check
.venv/bin/python -m pytest backend/tests/test_spatial_2026_evaluation_notebook.py backend/tests/test_assemble_notebook_payloads.py -q
.venv/bin/python backend/scripts/run_spatial_2026_evaluation.py --output-dir backend/rerun-2026-eval-023-002
.venv/bin/python backend/scripts/verify_spatial_2026_evaluation.py --run-root backend/rerun-2026-eval-023-002 --json-out /tmp/verify_2026_023_002.json
```
A failed root is kept; rerun with a NEW root id (`rerun-2026-eval-023-003`, ...). The runner refuses existing paths and protected overlaps. Root `rerun-2026-eval-023-001` is kept unchanged.

## Correction 1 (report/metric/verification only)
- Cohort, eligibility, cells, y and runtime predictions are unchanged; compare `data/v3/evaluation_2026/{row_ledger,cells_*,predictions_*}.csv` of 002 with 001 byte-for-byte.
- Raw mean Poisson deviance kept; new `deviance_status` (finite | infinite_due_zero_prediction | unavailable_empty) and `n_zero_pred_on_positive` explain every null (limit +∞ when λ = 0 on a positive cell).
- `deviance_floor_audit*`: original locked notebook-20 floor (config20 `metrics.deviance_floor` = 1e-12, hash-verified via the pinned 22 input pins), recomputed from the saved λ; numerical audit only, never a reselection criterion.
- `under_over_ranking.csv`: true direction only (`under_predicted` ratio < 1, `over_predicted` ratio > 1, `total_match`), explicit `NONE` row for an empty side.
- `multi_province.csv`: 2026 cell province = mode of recorded event province (ties lexical), not the OOF segment-midpoint province.
- Verifier also re-derives CKAN facts, date bounds, unknown report dates/negative lag, lag quantiles/share > 30 d/late-arrival-risk arithmetic, province/agency totals, old/new counts, every group metric, deviance status/floor audit, cell province mode and ranking direction.

## Order inside the notebook
1. Source + linkage pins verified → CKAN provenance → schema → explicit D/M/Y dates, times, lag/maturity, exact full-row duplicates, old/new net change.
2. Runtime pins verified → notebook-22 FUNCTIONS (joined sha) → accepted `load_service` (re-verifies 19/20/21 chain and bundle hashes; self-test).
3. Notebook-18 FUNCTIONS (joined sha) → accepted roads (derived files vs config18 + road manifest) → 50 m / 5 m linkage → independent segment-geometry re-check → exclusive ledger.
4. Observed positive cells only → `predict_batch` / `predict_baseline_batch` on identical ordered chunks ≤ 128 → metrics, comparison, ranking, coverage flags.
5. Aggregate reports (CSV/PNG/SVG, `report_2026_th.md`, `source_facts.json`) + strict manifest; row ledger and cell predictions only in the gitignored data dir.

## Interpretation limits
- One CSV row = one raw observed record; no ACC_CODE → unique event identity unverified; exact full-row duplicates only.
- Unobserved segment × date cells are unknown (never zero) → outcome-conditioned positive-cell diagnostic, not comparable with full-population OOF 2022–23 or seen 2024–25.
- Snapshot last_modified 2026-11-02 does not prove completeness; later arrivals unknown; measured report lag contradicts the 30-day label assumption as a completeness claim. No reweighting.
- 2026 is not a strict untouched test (earlier project data audits); models were selected on 2022–23 OOF before any 2026 score.
