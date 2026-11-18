# Goal / corrected scope
User wants a two-panel grouped-bar comparison of all3 actual RoadAware model families +baseline like reference. Original025 mistakenly required2025 all3 models; source has ONLY HGB+baseline, so do NOT use2025/make missing bars. Corrected design: ONE PNG with LEFT Poissondeviance, RIGHT MAE; BOTH OOF2022-2023. Xgroups in each:รายวัน,ช่วงละ6ชั่วโมง. This fixes scope from parent, not source data. Implement now.

## Sources
output/spatial-model-results/v3-evaluation-017-002/figure_method_comparison.csv (all16 needed metric values for8 unique rows). Select exactly methods segment_mean_k365,poisson_a1e-05::routed_context,rf_poisson_fixed::routed_context,hgb_poisson_fixed::routed_context for each daily,6h. Reconcile leaderboard_oof.csv if needed. No2025, no refit. All3 model policies same routed_context.

## Allowed changes
Only tools/render_thai_grouped_models.py (replace original025 script). Outputs output/presentation-th/model-comparison/grouped_models_oof_th.png/svg, plotted_values.csv,metadata.json. Reuse font helpers from tools/render_thai_calibration.py unchanged. Do not edit original sources, prior models, other scripts or memory. Codex runs. No shell required for worker.

## Design / acceptance
3000x1688 white navy title 'เปรียบเทียบผลทั้ง 3 โมเดลกับ Baseline';subtitle 'ผล OOF ปี 2022–2023 • ค่ายิ่งต่ำยิ่งดี'. Left panel 'Poisson deviance',right 'MAE — ผิดเฉลี่ยกี่รายการ';separate y scales (differentmetrics) start0. Two groups perpanel,4bars pergroup. Baselinegray,Poissonpurple,RFblue,HGBteal. Thai labels รายวัน/ช่วงละ6ชั่วโมง. Label all16 bars sixdecimals rotated90 if needed for space; highlabelsize avoid overlap. Legend shared below chart. Footer 'เปรียบเทียบภายในหน่วยเวลาเดียวกัน • HGB มี deviance ต่ำสุด แต่ Baseline มี MAE ต่ำกว่า'. No unsupported bestallmetric claims. Validation unique8rows,finitepositive; metadata sourcehash,all16 input/plotted values and method/unit/metric, image dims. Output PNG text in Thai uses Sarabun. CSV dailyvalues known deviance .040956/.041921/.040064/.039898;MAE .008601/.008793/.008757/.008662 but use exactsource.6h fromsource.

## Verification/report
Codex runs script, independent16bar comparison withCSV, visual PNGcheck. Worker reports changedfiles/checksrun/notrun/issues. Keep concise and focused.
