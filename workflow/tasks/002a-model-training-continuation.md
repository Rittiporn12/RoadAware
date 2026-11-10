# Goal
Complete interrupted task002 (read workflow/tasks/002-model-training.md in full). User confirmed Claude reset and wants work resumed. Preserve all original requirements and locked protocol. This is a bounded continuation, not a restart or a new model search.

# Current context
Read workflow/model-review-feedback.md, workflow/model-preliminary-findings-th.md and workflow/model-protocol-v1.md. Previous run .ai-team/runs/20261109-214057-25245 stopped on quota before tests/docs. Existing notebook06 and runner are real implementations. Codex independently executed all44 fold fits and11 full Train fits, but06 stopped on an overly strict RF serialization assertion. Fix numerical agreement with explicit rtol/atol1e-12 and max absolute difference recorded; retain rejection of meaningful differences. Do not change protocol/config/parameters or scoring. Current outputs are clearly WIP and must not be represented as acceptance.

# Allowed scope
Same implementation files as task002: notebook06, model config ONLY if required to restore original protocol (do not tune), model runner, NEW backend/tests/test_model_notebooks.py, backend requirements/docs, root README, backend/.gitignore. No notebooks07/08 in this stage. Codex handles workflow docs, shell execution and Git. Use Write for .ipynb (Edit is not supported for notebook files). No shell/subagents/git/dependency installation. Leave notebooks01-05/data/reports/data unchanged.

# Acceptance criteria
1. All original task002 criteria, including meaningful synthetic model tests and reusable helper contracts.
2. Fix actual RF reload numerical issue with documented tolerance and visible measured difference. Include a regression test rejecting material changes and allowing floating roundoff. Review other exact comparisons of ML outputs for the same issue; deterministic key/choice/hash checks remain strict.
3. Record fold province support from positive past labels, not merely all panel provinces; actual four fit counts21622/32297/43354/53211 and OOF42058 rows/count24448 remain unchanged.
4. Ensure final experiment/artifact manifests complete and correctly hash sources, bundles and outputs. No stale ok status carried from old output. Re-running same source/data/config supported.
5. Add tests covering hand metrics/domains, invalid inputs, fold cutoffs/disjointness, train-only encoders/unknown categories for all3 real families on tiny fixtures, baseline fallback, ties/frozen selection, paired calendar bootstrap/reproducibility, fresh-interpreter reload where feasible. Tests must test behavior, not mirror code. Python3.9 compatible.
6. Docs distinguish actual precheck from pending final verification. Explicitly warn later-year diagnostic baseline outperformed candidates and cleaning/date-format regime shift; no production readiness or unseen-test claims. Final status will be updated by Codex after verification.

# Verification requested
Report exact tests/run commands for Codex. Codex will inspect diff, run pytest, execute06 against unchanged real panel, recompute metrics/locks and verify reload/input fingerprints before acceptance. Do not claim you ran tests: tools allow file work only.

# Final report
Changed files; checks actually run and not run; output/helper contracts for task003; remaining issues. Read live workflow/model-review-feedback.md before final and before docs updates. End after this bounded stage.
