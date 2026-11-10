# Goal
Create beautiful, reproducible presentation charts and Thai explanations using ONLY actual frozen RoadAware V2 results. User will arrange slides themselves; no PPTX/PDF or frontend required.

# Context
The user needs five topics: Baseline and Candidate Models, Evaluation Metrics, Experiment Results, Error Analysis, Reasons for choosing the model. Existing experiment and analysis outputs are accepted and immutable. ML model selection is already frozen. Produce reporting notebook; do not fit/tune models.

# Allowed scope
Only add backend/notebooks/15_presentation_results.ipynb and backend/reports/presentation_v2/ (outputs generated when Codex runs notebook). Do not modify any other notebooks, data, model artifacts, config, accepted reports, or application code.

# Deliverables / acceptance
- Self-contained Python reporting notebook runnable with existing .venv through VS Code. Resolve repo root by walking cwd parents. Use pandas/matplotlib/PIL/stdlib already installed. Notebook outputs must display plots inline and a concise comparison table. All plotting logic lives in this notebook. No seaborn/new dependency.
- Read authoritative backend/reports/v2/models/{selection_lock.json,oof_metrics_pooled.csv,oof_metrics_by_fold.csv,diagnostic_metrics.csv} and backend/reports/v2/analysis/{decision_summary.csv,fold_comparison.csv,gate_checks.csv,calibration_bins_daily.csv,calibration_bins_6h.csv,slices_daily.csv,slices_6h.csv}. Can inspect other frozen CSVs.
- At least 8 polished charts, each PNG 200+ dpi and SVG, white/off-white backgrounds, consistent navy/teal/orange palette, large legible labels, no clipping, minimal clutter. English labels in graphics avoid Thai glyph shaping issues; Thai explanation in README and notebook markdown. Approximately 16:9, suitable slide insertion. Plot real data, never fabricated illustrative series. Chart filenames and source CSV provenance clear.
- Suggested charts: (1) strongest baseline + best member each of 3 candidate families daily/6h Poisson deviance separate panels; (2) MAE/RMSE comparison separate units; (3) HGB vs baseline four temporal OOF folds; (4) HGB 5-feature variants actual ablation scores; (5) calibration actual vs predicted OOF/2024/2025 with clear seen diagnostic labels; (6) festival mean actual vs predicted with sample supports; (7) 6h time-block error; (8) HGB selection evidence gains and CI / and/or later-year scores. Include zero-baseline MAE tradeoff in chart or table, NOT hide it.
- Export exact chart data to CSV(s), and source hashes/output manifest JSON. No raw personal records. README_th.md maps outputs to five topics, explains all metrics (Poisson deviance primary, MAE events per province-day or per province-6h, RMSE, signed bias), chosen variants, baseline definitions, model intuition, actual numeric evidence, and concise speaker notes.
- Highlight final HGB daily full and 6h calendar_traffic, OOF deviance reductions 7.163804815% and 3.986795770% vs strongest nonzero baseline. Do NOT call these accuracy percentages. Four folds expanding time, pooled row weighted, choice made before 2024/2025.
- Material caveats: 2024/2025 previously seen diagnostics NOT untouched future test; 2024 eligible coverage incomplete (7885/28182 daily cells, 103 dates Jan-Sep); province aggregate MOT-record counts NOT route point risk or personal probability; exploratory post-selection bootstrap not adjusted multiple comparisons; weather unavailable 2024/25 (no claim proven weather gain); AADT station-based annual proxy NOT live congestion; no model dominates every metric (zero MAE can look best in sparse 6h data). Daily/6h metrics not directly comparable. High-count outcome-defined slices retrospective only. No production-ready claims.
- Avoid causal feature importance claims from ablations, CI not standalone proof. No invented confusion matrices/accuracy/F1 for regression.
- Do not run shell commands. Codex executes notebook and independently verifies data and visuals.

# Worker report
Report files changed, checks actually run, checks not run, remaining issues. CLI success is not acceptance.

# Execution status / clarified scope
Delegation attempt 20261111-001817-39834 failed before any implementation: Claude bridge returned `Not logged in · Please run /login`. User clarified that actual result images/tables suffice and they will arrange slides themselves. Codex authored report-only graphics under output/model-results from immutable CSVs, independently recomputed 54 scores from stored predictions, and supplied Thai presentation notes. No new backend notebook exists; this task's proposed notebook is not a completed deliverable. Do not automatically resume notebook implementation without considering the user's current scope.
