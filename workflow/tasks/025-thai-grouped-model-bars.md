# Goal
Create tools/render_thai_grouped_models.py to produce grouped-bar Thai charts matching user's two-panel reference. Codex runs/verifies. Do not execute shell commands.

## Context/source
User wants 3 models compared with Baseline as bars, two panels, no copied price forecasts. Inputs in backend/rerun-spatial-model-016-002/reports/v3/spatial_experiments/: leaderboard_oof.csv and diagnostics_seen_2024_2025.csv (inspect schemas). Left pooled OOF2022-2023 used for selection, right previously seen year2025 only. Each panel two groups daily and6h (these are units NOT1/2/3-month horizons). Four methods: segment_mean_k365, poisson_a1e-05::routed_context, rf_poisson_fixed::routed_context,hgb_poisson_fixed::routed_context. Require exact source rows, no different policy/tuning/extra models.

## Scope
Only create tools/render_thai_grouped_models.py. Reuse tools/render_thai_calibration.py fonts/style imports. Output output/presentation-th/model-comparison/model_comparison_deviance_th.png/svg and model_comparison_mae_th.png/svg plus plotted_values.csv and metadata.json. No other file changes/no memory edits. Inputs read-only, no model fit.

## Design
3000x1688 white clean Thai. Two panels and shared legend bottom, grouped bars. Colors baseline gray, Poisson purple,RFblue,HGBteal. X groups 'รายวัน','ช่วงละ 6 ชั่วโมง'. Titles left 'ผล OOF ปี 2022–2023' subtitle 'ใช้คัดเลือกโมเดล';right 'ผลปี 2025' subtitle 'เคยเห็นแล้ว • ใช้วิเคราะห์เพิ่มเติม'. Main deviance title 'เปรียบเทียบโมเดล: Poisson deviance' and subtitle 'ค่ายิ่งต่ำยิ่งดี • เปรียบเทียบภายในหน่วยเวลาเดียวกัน'. MAE title 'เปรียบเทียบโมเดล: MAE' subtitle 'ผิดเฉลี่ยกี่รายการต่อช่วงถนน–ช่วงเวลา • ค่ายิ่งต่ำยิ่งดี'. Within each figure panels share y axis range based max, start0. All16 bars labelled exact 5or6decimals so close numbers distinguish (deviance6decimal MAE6). Labels may rotate60/90 degrees to avoid overlap but readable. Use plenty whitespace, minimal grid. Footer 'ปี 2025 ไม่ใช่ชุดทดสอบใหม่ที่ไม่เคยเห็น • ไม่ใช้เลือกโมเดลใหม่'. Do not claim HGB best in every metric, daily vs6h accuracy comparison, or 2026/test12months. Legend Baseline,Poisson Regression,Random Forest,HGB Poisson. User wants clear attractive PNG; best effort labels no overlap.

## Acceptance
Validate exactly one row per method/unit/split, reconcile daily/6h OOF values to output/spatial-model-results/v3-evaluation-017-002/figure_method_comparison.csv, use manifest hashes where available. Metadata all16 bar sources and values and plotted heights permetric; sourcehash. Codex checks originalCSV independently and visual output. No refit or data changes.

## Final
Report changed files, checks run/notrun, remaining issues. Focus script only.
