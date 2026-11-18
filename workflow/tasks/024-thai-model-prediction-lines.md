# Goal
Create tools/render_thai_model_predictions.py rendering real actual-vs-predicted Thai line charts for all THREE V3 models, not a metric line chart. Codex executes/verifies. Do not run shell.

## Sources / scope
Read accepted backend/rerun-spatial-model-016-002/data/v3/spatial_experiments/arrays_index.json and array metadata + manifest. OOF arrays float64/uint8 with implicit date->segment->block ordering, offsets in index. Never infer ordering without checking index. Daily OOF has 730dates *3105 segments =2266650 cells. 6h=9066600. Model names: poisson_a1e-05, rf_poisson_fixed, hgb_poisson_fixed; policy routed_context MUST derive np.where(context_mask==1, context, core) for each config. Baseline segment_mean_k365. y from oof_<unit>_y.npy. mmap np.load allow_pickle=False. No training/loading joblib. All dates OOF2022-2023. Reference output/spatial-model-results/v3-evaluation-017-002/figure_method_comparison.csv for aggregate score reconciliation and current workflow/model-gate-presentation-th.md.

## Allowed
Only create tools/render_thai_model_predictions.py. Runtime outputs output/presentation-th/model-predictions/: prediction_lines_daily_th.png/svg and prediction_lines_6h_th.png/svg; daily_totals.csv, monthly_totals.csv, metadata.json. No modifications existing reports/scripts/arrays. Reuse Thai font helpers tools/render_thai_calibration.py via import.

## Design / calculations
For each unit sum all segments (and 4 blocks for6h) to daily totals, then calendar-month totals (24 months). Use MONTHLY SUM so predictions all3 visibly compare against observed temporal variation; label clearly monthly aggregation of daily/6h predictions, NOT a monthly forecast model. No date windows cherry-picked, smooth/interpolate or fitted curves. Make one polished 16:9 >=3000x1688 white PNG per unit, Thai title 'แต่ละโมเดลทำนายใกล้กับข้อมูลที่บันทึกแค่ไหน?' subtitle distinguishes daily or6h aggregated monthly OOF2022-2023. Plot 5 lines: actual black thick, Poisson purple, RF blue, HGB teal bold, baseline gray dashed. Clear Thai x month/year tick labels (every3 months, label year clearly) y 'จำนวนรายการรวมต่อเดือน'; all months on full axis, y starts0, light grid. Colorblind readable and white background navy. Legend no overlap. Footer 'รวมทุกช่วงถนนในพื้นที่ศึกษา • เส้นใกล้ข้อมูลที่บันทึก = ยอดรวมใกล้เคียง • ไม่ใช่คะแนนรายช่วงถนน'. Could make 3 small multiples actual+eachmodel instead if severe overlapping, but default single 5-line plot as user requests comparative graph.

## Verification
Validate n/order/dates from index, hashes of actual arrays against available index hashes before consume, finite/nonnegative, mask0/1. Recompute pooled daily MAE/RMSE and Poisson deviance for all3 routed + baseline and reconcile source figure_method_comparison.csv 1e-9. sum actual10701, HGB daily9574.098230117164/6h9446.016245708677 within1e-7. Require monthly totals conserve full totals; metadata full source hashes, arrays shapes/order, methods, totals, metric reconciliation,24 points per series, output hashes. Codex independently verifies metadata/CSV and visually PNG. Use memory efficient chunks if necessary.

## Final report
Changed files, checks actually run/notrun, issues. Implementation focused, no invented numbers or claim total-line similarity means overall best. Final code only scope above.
