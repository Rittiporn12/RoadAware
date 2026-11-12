# Notebook 22 spatial inference runbook (task 018). Research readiness only; production_ready=false; nothing deployed

## Sources and assembly
- Payloads `.ai-team/handoffs/018/` in `notebook_cells.json` order: title, parameters, FUNCTIONS 1..5, setup, inputs_baseline, service_parity, requests_robustness, reports, outputs.
- Config `backend/config/spatial_inference_v3.json`; manager pins `workflow/serving/input-pins-v3.json` (read-only; never edited by 22).
- Assemble: `.venv/bin/python tools/assemble_notebook_payloads.py --spec .ai-team/handoffs/018/notebook_cells.json --target backend/notebooks/22_spatial_inference_contract.ipynb`

## Commands (Codex runs; repository root)
1. Fixtures/tests: `.venv/bin/python -m pytest backend/tests/test_spatial_inference_notebook.py backend/tests/test_assemble_notebook_payloads.py -q`, then the full `backend/tests` suite.
2. Fresh kernel: `.venv/bin/python backend/scripts/run_spatial_inference.py --output-dir backend/rerun-spatial-serving-018-001` (a NEW root each attempt; failed roots are kept).
3. Independent verifier: `.venv/bin/python backend/scripts/verify_spatial_inference.py --run-root backend/rerun-spatial-serving-018-001 --save <new evidence json>`.

## Trust chain at startup (load_service)
pins kind/selection/roots -> every pinned file sha -> 19 manifest (complete, FUNCTIONS sha) -> 20 manifest (complete, lock/selection sha, consumed bundles/meta/reference CSV/diag arrays) -> 20 lock (19 code cells, prepared hashes, feature columns) -> model_bundles.json -> 21 manifest (complete, FUNCTIONS sha, colour contracts) -> exec 19/20 FUNCTIONS and 21 FUNCTIONS cells 1+3 -> pinned prepared context -> bundle meta + `load_bundle` (sha BEFORE joblib.load) -> reference self-test (internal, includes 2021 training-sample keys) -> baseline stats npz sha -> immutable service. Any failure -> `status=unavailable` with a code; requests then return `artifact_unavailable`.

## Interfaces for API019 (transport only; no feature logic in the API)
- `load_service(backend, cfg, pins, baseline_files)`; `baseline_files={unit: (path, sha256)}` from the accepted 22 `serving_record.json`/manifest (paths are server-side only).
- `predict_batch(service, unit, requests)` / `predict_baseline_batch(...)`: unit `daily|6h`; 1..128 objects with exactly `segment_id,target_date` (+`time_block` iff 6h); strings only; ordered output; strict finite JSON.
- `metadata(service)`, `coverage(service, segment_ids)`, `health(service)` (startup availability separate from production_ready=false).
- Error families: invalid (`invalid_*`, `batch_size`, `duplicate_keys`, `date_out_of_range`, `date_before_artifact_asof`), coverage (`unknown_segment`, `unsupported_segment`), unavailable (`artifact_*`, `prediction_invalid`).

## Artifact facts
- Default API artifact = benchmark `roadaware-spatial-v3-benchmark-issue-2023-12-31T18`: fit issue 2023-12-31 18:00 (+07), training labels to 2023-12-01 18:00; public target dates 2024-01-01..2027-12-31; >2025-12-31 flagged research scenario.
- No extended 2021-25 refit (user closure); no OOF fold models -> no OOF replay claim; OOF routing verified as arrays by the verifier.
- Routed policy: context component iff all weather/AADT trigger columns finite, else the same-config core component (reason lists missing columns); pure context ablation is refused.
- Observed scope: the saved 2024/25 diagnostic mask has no observed weather/AADT context, so the real full-population parity is core-fallback only (`observed_routing_scope` reported, not assumed). Context/mixed routing is exercised only by the clearly SYNTHETIC fixture `synthetic_routing_probe` (`synthetic_routing_fixture_NOT_observed.csv`): trigger columns overwritten in a service copy, same pinned schema/bundles; never observed evidence.
- Error rows: `error.rows` lists the first 10 offending request positions (row 0 included) of the first failing family; families run in the pinned 19 order (fields/value -> invalid_date -> date_out_of_range -> invalid_time_block -> duplicate_keys -> coverage) then the 22 as-of rules. A failing batch is refused whole (no `results`).
- Baseline `segment_mean_k365` sufficient statistics rebuilt ONCE offline from pinned 19 labels with the exact 20 cutoff; never fitted in a request.

## Not done here (later scope)
Live HTTP API and smoke helper (019), 2026 audit/evaluation (023), frontend/route engine/deployment.
