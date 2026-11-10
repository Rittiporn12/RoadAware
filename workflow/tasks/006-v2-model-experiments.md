# Goal

Implement the actual V2 model experiment as Python notebooks for VS Code:
three candidate families (Poisson, Random Forest, HGB), strong baselines,
feature ablations, chronological evaluation, error analysis and a documented
model decision. Do not promise a win or manufacture results.

# Preconditions / context

NOT READY TO DELEGATE until Codex records source task 004c and preparation
task 005 acceptance and locks the protocol with actual input hashes. Read
AGENTS.md, workflow/v2-feature-policy.md, workflow/model-protocol-v2-draft.md
(then its locked successor), accepted notebooks 09/10, their configs/manifests,
the preparation next_stage_interface and Codex review feedback. V1 is frozen.
No implementation may choose features or hyperparameters from 2024/25 scores.

The user requests reproducible source code and executed evidence, all ML
business logic in .ipynb, no frontend screens yet, and meaningful GitHub history.
Codex runs commands and independently verifies; worker uses file tools only.
For large notebook edits, author exact cell payloads and a checked mechanical
applier under ignored .ai-team/handoffs/006; the final notebooks must contain
all logic without runtime imports from handoff files.

# Allowed scope

New backend/notebooks/11_v2_model_experiments.ipynb and
12_v2_evaluation_error_analysis.ipynb; new backend/config/model_experiment_v2.json;
extend backend/scripts/run_v2_notebooks.py with explicit model/evaluate stages;
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
6. Notebook 12 reads immutable experiment outputs and produces error analysis:
   month, province, weekday, block, festivals, feature availability, zero/high
   counts, calibration/support and aggregate residuals; ablation benefits AND
   harms on identical keys. Plots and Thai model card explain selected model,
   practical limitations, count-vs-personal-risk distinction and production=false.
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
