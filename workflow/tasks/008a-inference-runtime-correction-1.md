# Goal

Correction round1 for task008: repair concrete runtime failures in notebook13 so registry load and public mixed-unit predict_batch actually run. Original task008 and backend-completion-plan requirements remain in force. Read AGENTS.md. Only execute after worker008 finishes; no concurrent worker.

# Observed failures (Codex actual preflight)

Executing both FUNCTIONS payloads from008 and calling load_registry(backend=Path('backend'),load_models=False) raises AttributeError: 'dict' object has no attribute 'read_str_csv'. exec_pinned_functions returns a dict, but notebook10 helpers are called with attribute access throughout load_registry and build_feature_frame. Notebook11 helpers correctly use mapping access. Make representation consistent without changing pinned10/11 sources.

With a diagnostic in-memory namespace adapter for notebook10 ONLY (no implementation files changed), trusted registry loads in1.719seconds, but predict_batch then raises NameError: free variable 'unit' referenced before assignment in its unit-selection comprehension: it compares c['unit'] == unit before the outer unit is bound; compare against the comprehension variable u. With both diagnostic in-memory shims, actual daily2026-11-11 and6h2024-02-29 requests return finite predictions, indicating the failures are in the new adapter. This is diagnostic evidence, NOT passing acceptance. See .ai-team/references/008-preflight-feedback.md.

Recheck actual finalized source; if008 already fixed either issue, do not reintroduce it. Also address test/notebook failures supplied by manager in this task's appended notes before running. Do not claim any unexecuted test passes.

# Scope

Only notebook13 / its ignored008 payloads + checked applier/assembler under .ai-team/handoffs/008a, focused tests backend/tests/test_inference_notebook.py; inference config/runner only if strictly necessary for a concrete failure with explanation. No accepted09-12/V1/model artifacts/config/selection/protocol changes, no fits/network/frontend/API implementation yet. Codex runs commands. Final business logic must be in .ipynb, no .ai-team runtime dependency.

# Acceptance and verification requested

Registry loads via actual public function with no monkeypatch; requests of daily and6h separately and mixed preserve order and match saved11 results; first-use public predict_batch does not reference an unbound unit. Include meaningful regression tests for helper-container consistency and actual mixed-unit path, not only mocked model arrays. All original008 feature/as-of/hash/strictvalidation/robustness requirements retained. Provide exact changed cells and applier command; manager executes targeted tests and full notebook13, inspects diff and evaluates evidence independently. Do not edit previously generated failed manifests to look completed; fresh output root or preserved archive.

# Report

Changed files/cells, reasons, checks actually run/not run, exact commands, remaining issues. No Git/shell/second worker. At most two correction rounds for008 including this one.
