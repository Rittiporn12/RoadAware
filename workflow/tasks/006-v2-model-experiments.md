# Goal

Implement notebook 11 for the actual V2 model experiment in VS Code:
three candidate families (Poisson, Random Forest, HGB), strong baselines,
feature ablations, chronological evaluation and a documented model decision.
Detailed notebook 12 error analysis is a subsequent bounded task. Do not promise
a win or manufacture results.

# Preconditions / context

Manager update 2026-11-10 18:03: You may IMPLEMENT now while Codex verifies source
004c/prepare005. The ONLY previous Claude worker has finished. Codex runs the
online 09 collector; NEVER modify 09/10 or their inputs/configs. NO fitting or
execution until Codex accepts both stages and locks actual input hashes. Read
AGENTS.md, workflow/v2-feature-policy.md, workflow/model-protocol-v2-draft.md
(then its locked successor when available), notebooks 09/10, their configs/manifests,
the preparation next_stage_interface and Codex review feedback. V1 is frozen.
No implementation may choose features or hyperparameters from 2024/25 scores.

The user requests reproducible source code and executed evidence, all ML
business logic in .ipynb, no frontend screens yet, and meaningful GitHub history.
Codex runs commands and independently verifies; worker uses file tools only.
For large notebook edits, author exact cell payloads and a checked mechanical
applier under ignored .ai-team/handoffs/006; the final notebooks must contain
all logic without runtime imports from handoff files.

# Allowed scope

New backend/notebooks/11_v2_model_experiments.ipynb;
new backend/config/model_experiment_v2.json;
extend backend/scripts/run_v2_notebooks.py with explicit model stage;
new backend/tests/test_v2_model_notebooks.py; truthful README updates. Generated
row predictions, serialized models and matrices live only under ignored data/v2.
Tracked aggregate reports under backend/reports/v2/models. Do not change 01–10,
their configs or accepted source/preparation artifacts, or any V1 files. No API,
frontend, deployment, paid services, Git, shell or additional workers.

# Acceptance criteria

1. Fresh-kernel, self-contained FUNCTIONS cells; strict input/dependency hashes,
   schemas and approved feature guard; issue-time split boundaries and disjoint
   keys verified before fits. All model and baseline methods use identical
   eligible keys per unit. Missing feature values never remove model-specific
   evaluation rows. Respect final diagnostic cutoff in the locked protocol.
2. Implement exactly the locked configurations, feature variants, four expanding
   folds and both target units separately. Fit learned preprocessing only on
   fold Train; preserve all-missing columns; avoid fitting encoders on evaluation.
   Record actual convergence warnings, timings and failures. No silent fallback
   model, unsupported Poisson exposure offset, label history or tuning loops.
3. Baselines fitted solely from Train; recent-history baseline frozen at fold
   start. Save exact OOF keys/predictions locally and aggregate metrics/fold
   boundaries/coverage, including prediction floors only for deviance and null
   zero-baseline deviance. Strongest nonzero baseline and best member of all
   three candidate families clearly identified.
4. Select only using pooled OOF under the locked rule. Evaluate stability gate
   and exploratory paired calendar-block bootstrap. Write a selection lock
   containing actual input/config/OOF hashes BEFORE later-year diagnostics, and
   verify unchanged afterwards. If no candidate passes, recommend the strongest
   baseline while explaining the best candidate family and observed shortfalls.
5. Fit final specified methods only on the allowed pre-issue training cells;
   report 2024 development and 2025 reused/previously-seen diagnostics honestly.
   Never call either an untouched test. Reload fitted artifacts and verify
   prediction consistency on a fixed supported sample.
6. Notebook 11 writes a compact Thai experiment report and model card explaining
   all family results, ablation benefits AND harms on identical keys, selection
   gate and limitations. Explicit machine-readable next_stage_interface for
   notebook 12: OOF and diagnostic predictions, panels, selected methods/baselines,
   selection lock and hashes; keep all fit-time features available by joining
   accepted 10 immutable feature keys. Detailed plots/slice analysis deferred to12.
7. Unit fixtures use small hand-calculated examples for smoothing/fallbacks,
   temporal cutoff, no evaluation-label updates, preprocessing leakage, family
   selection/ties, metric floor behavior, bootstrap calendar grouping, selection
   lock tampering and reload consistency. Tests exercise real notebook functions.
   Codex runs actual notebooks and independently compares report aggregates to
   stored predictions. Do not report unrun checks as passed.

# Worker handoff

Report changed files, checks actually run, checks not run, exact commands Codex
should execute, output/interface paths, runtime expectations and remaining
issues. Read live review feedback before finishing. CLI success is not acceptance.

# Exact implementation clarifications

Use draft configurations unchanged; protocol is fixed BEFORE any V2 fits.
Require a manager-created workflow/model-protocol-v2-lock.json at runtime. Its
schema is roadaware-v2-experiment-lock/1 and contains protocol_sha256 (the draft
file bytes), model_config_sha256, preparation_manifest_sha256, preparation
data_outputs (path + sha256 copied exactly from accepted 10 manifest), and
source_run_id/preparation_run_id. Fail absent/mismatched lock. Exclude unrelated
changing notebook outputs from the manager lock. Codex creates this planning
record only after acceptance; worker must not fabricate hashes or write results.

The final final-fit cutoff is 2023-12-31 18:00 +07 as in the amended draft.
Use cell target_end_local <= issue. At fold starts use the same boundary, not
merely target_date < first evaluation date. All methods share exactly this fit
cohort. Additional accident-report publication latency remains unverified.

Keep computation bounded without changing statistical configurations: avoid
refitting identical baseline predictions per feature variant; cache identical
fold transforms where safe; constrain numerical thread pools and RF n_jobs=2;
never share fitted preprocessors across folds. Report full run timing. Daily
and 6h selections independent, no cross-unit winner by raw metric magnitude.
Use backend/data/v2/models for local bundles/predictions and reports/v2/models
for tracked aggregate outputs; configurable output root. If 11 is too large for
file tools, write ordered plain cell payloads + checked assembler under ignored
.ai-team/handoffs/006. No need to add notebook 12 or its runner stage yet.
