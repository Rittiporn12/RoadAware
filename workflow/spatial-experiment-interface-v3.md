# Notebook20 handoff interface — provisional until actual acceptance

Source checkpoint e352a6f; actual run backend/rerun-spatial-model-016-001 is active. This document describes source interfaces, not accepted final metrics. Do not pin unfinished outputs or use preliminary daily results as final backend acceptance.

## Files and array representation

- reports/v3/spatial_experiments: spatial_experiments_manifest.json (complete only on full success), experiment_lock.json, selection_frozen.json, leaderboard_oof.csv, fold_metrics.csv, selection.csv, feature_ablation.csv, diagnostics_seen_2024_2025.csv, transfer_metrics.csv, bootstrap.csv, strata_metrics.csv, context_availability.csv, sampling.csv, model_fits.csv, feature_parity.csv and actual figures/results_th.md.
- ignored data/v3/spatial_experiments: arrays_index.json, selection_frozen.json, experiment_lock.json, model_bundles.json, oof_daily_deviance_daily.csv / oof_daily_deviance_6h.csv, models/ and arrays/.
- arrays_index.units[unit]: oof / oof_periods / diag / diag_periods / transfer. Each array metadata has file basename,kind,dtype,shape,sha256,bytes. OOF/diag files in arrays/, transfer files in arrays/transfer/. Transfer dates2023 and sorted eval IDs in arrays_index.transfer_axes. Main implicit axis is accepted19population_axes.json, order date→sortedsegment→block. Periods carry row_offset/rows.
- Predictions/y float64 numeric .npy, allow_pickleFalse; context_mask uint8. Methods config_id::core,config_id::context,config_id::routed_context. Only component arrays stored for OOF; routed = where(context_mask,context,core). Zero baseline identically0, notstored. Other baseline arrays stored. Diagnostics save selectedpolicy plus strongestbaseline only. Never assume a separate routedOOFfile exists.
- Manager source reads/pins after execution must use FUNCTIONS/codecell source hashes, not pre-execution full notebook file hash (outputs/metadata change on canonical executed-copy).
- Source20 manifest does not itself include FUNCTIONS/codecellhash fields. The runner records full source SHA before/after; Codex independently records source-cell hashes in the accepted review and future manager input pins. Do not invent missing manifest keys or auto-trust current source at serving startup.

## Model retention and serving consequences

20 keeps only benchmark selected-policy required components under models/<unit>/. No OOFfold model bundles retained. Therefore22 can verify full benchmark selected/baseline predictions against saved diagnostic arrays; it must not claim to replay OOF with a model that was refitted using later labels. OOF component/routing reconstruction remains independently testable as numerical arrays.

Benchmark bundles have .meta.json and reference requests/predictions, hash in accepted manifest/model_bundles.json. Verify trusted expected hash BEFORE joblib.load. Baseline sufficient statistics are not serialized by20:22 may reconstruct them ONCE from pinned19labels and exact20cutoff/recipe, persist verified serving stats and validate against saved baseline diagnostic predictions; never recompute learning inside HTTPrequests.

Extended2021–25refit is separate artifact/version with its own declared as-of issue and allowed targetdate range. No reselection from2024/25. Default runtime must reject requests whose targetissue precedes chosen artifact's fit/as-of date; builder's broad2021–2027calendar range is not permission to make falsely prospective historical forecasts.

## Verified manager aids (ignored, not runtime dependencies)

.ai-team/references/verify_016_arrays.py independently recomputes metrics from numeric arrays with scipy.special.xlogy, including derivedrouting and floor counts. Other independent oracles cover full UID-based baseline count matrices/calendar denominators in8folds, allstratum sampleweights forfirst/lastfolds, exact30dembargo boundaries and fixed geometrytransfer IDs. Acceptance must collect actual results afterruncomplete, not treat existence of verification scripts as passed tests.
