# Goal
Correction round2 FINAL for020. Read AGENTS.md. One narrow test-only correction; Claude writes all code, Codex tests/reviews. No other worker.

# Evidence
020a source was assembled. Actual backend/rerun-historical-catalog-020-003 completed7.98s manifestcomplete, independent CLI verify_historical_catalog.py passed67checks;all106308rawdescriptions/legacy84296/selected27459/province77x60/daily6h/asofexamples/hashes/privacy match. Both actualPNGs inspected/readable. Do NOT rerun kernel or edit these outputs.
Targeted49pass1fail;full641pass1fail26.81s. Sole failure backend/tests/test_historical_catalog_notebook.py test_output_guards around480: configured protected reportdir reports/v3/spatial_preparation/x now correctly raises CatalogError('protected snapshot overlaps runtime outputs: ...') earlier in snapshot_rels, but test expects old 'overlaps guarded'. Function correctly refuses before any writes. Runtime/config changes not requested.

# Scope
ONLY backend/tests/test_historical_catalog_notebook.py. No handoff/notebook/config/runner/verifier/docs/memory changes. Fix the assertion for the actual early validation path; retain the separate regular output guard assertion and all symlink/reuse checks. Add a meaningful no-write assertion for bad protected-dir config if useful, not a broad catch-all or force pass. Keep codePython3.9.

# Acceptance and verification
Correct test distinguishes intended protected snapshot overlap refusal, preserves attempted target unchanged/uncreated. No acceptance weakening. Codex runs targeted andfullsuite. Actual003 remains valid because runtime/config immutable;no unnecessary kernel rerun. Reportexactdiff and commandsactuallyrun(none),notrun,issues. Keep response short.
