# Goal
Write tools/render_thai_fold_results.py producing a clean Thai PNG/SVG for Experiment Results. Codex runs/verifies. Do not execute shell commands.

## Context
Input output/spatial-model-results/v3-evaluation-017-002/figure_period_performance.csv (inspect schema). Plot OOF 2022H1/H2,2023H1/H2 only, selected HGB vs baseline segment_mean_k365 for daily/6h. Source current workflow/model-gate-presentation-th.md if context needed. No V2 or 2024+ points. Existing tools/render_thai_calibration.py supplies locate_thai_font, configure_style reusable by import (do not modify).

## Scope / deliverables
Only create tools/render_thai_fold_results.py. Output output/presentation-th/fold_results_th.png, .svg, _metadata.json. Use existing matplotlib Agg/stdlib. Caller sets MPLCONFIGDIR. 3000x1688 16:9, white, navy Thai title 'HGB ให้ผลดีกว่า Baseline ครบทั้ง 4 รอบ', subtitle 'ผล OOF ปี 2022–2023 • เปรียบเทียบแยกรายวันและช่วงละ 6 ชั่วโมง'. Two side-by-side orange/teal bar charts of percent deviance reduction (not raw loss). Left รายวัน values from CSV (~4.20,2.58,2.55,0.97), right 6h (~12.71,8.30,7.74,3.65). Thai ticks 'ต้นปี 2022','ปลายปี 2022','ต้นปี 2023','ปลายปี 2023' use two lines to fit. Axis 'ลด Poisson deviance จาก Baseline (%)', y starts0 each panel, annotations +x.xx% from exact data. Footer 'แท่งสูง = ลดความคลาดเคลื่อนได้มาก • เป็นผลรายรอบ ไม่ใช่เปอร์เซ็นต์ความแม่นยำ'. Colors dark teal daily and blue six-hour, no busy grid, large text. All labels not clipped. SVG text editable. Avoid claiming all rounds reduce >=1% (last daily .968%). No added pooled claims.

## Acceptance
Recompute gains (baseline-selected)/baseline from exact CSV values; if CSV already stores gain reconcile. Expect 8 unit-period groups; fail duplicates/missing. Metadata stores source SHA256, all input selected/baseline deviance and computed plotted percentages for independent verification. Preserve data no refit. Need only focused script, reuse font helper.

## Final report
List changed files, checks actually run/not run, issues. No source changes.
