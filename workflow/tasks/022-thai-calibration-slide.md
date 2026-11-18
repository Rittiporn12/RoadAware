# Goal
Write tools/render_thai_calibration.py to render a beautiful, readable Thai calibration PNG/SVG for the user's Evaluation Metrics slide. Codex runs and verifies. Do not run shell commands.

## Context
Accepted source output/spatial-model-results/v3-evaluation-017-002/figure_calibration.csv has unit, role, method, group, n, total_pred,total_actual,exposure_segment_km_periods,predicted_records_per_km_period,observed_records_per_km_period. Read it and existing figures/calibration.png if needed. Preserve every CSV plotted point for selected and baseline, daily and 6h. No refit/rebinning/recalibration/data alteration.

## Scope
Only create tools/render_thai_calibration.py. Runtime outputs output/presentation-th/calibration_th.png, calibration_th.svg, calibration_th_metadata.json. Do not modify existing files/reports. Use matplotlib Agg + stdlib csv/json/hashlib; no new dependencies. Locate Thai Sarabun font via pathlib glob under /System/Library/AssetsV2 (or Thai font fallback). Use writable MPLCONFIGDIR set by caller.

## Design
High-res white background 16:9 figure 3000x1688 approx. Navy title 'ค่าทำนายใกล้เคียงกับข้อมูลที่บันทึกแค่ไหน?' subtitle 'ผล OOF ปี 2022–2023 • HGB เทียบกับ Baseline'. Two roomy panels titled 'รายวัน' and 'ช่วงละ 6 ชั่วโมง'. Teal HGB and orange baseline, clear dashed diagonal 'ทำนายตรงกับข้อมูล'. Both axes log10, share bounds based on full positive point ranges with margin, no cropped labels. X 'ค่าทำนาย (รายการ / กม. / ช่วงเวลา)' Y 'ข้อมูลที่บันทึก (รายการ / กม. / ช่วงเวลา)'. Thai legend, minimal grid, large fonts. Bottom explanation 'ใกล้เส้นประ = สอดคล้อง  |  เหนือเส้น = ทำนายต่ำ  |  ใต้เส้น = ทำนายสูง'. Small footer 'แกนลอการิทึม • เฉพาะรายการที่ผ่านการคัดเลือกและเชื่อมถนนได้'. No boxes that collide with chart; professional clean slide visual. Ensure Thai vowel marks/font work. SVG text editable if possible.

## Acceptance / Verification
Validate x/y recomputed totals/exposure vs supplied rates within 1e-12, fail invalid data; require exactly selected/baseline for both units. Metadata records CSV hash, all plotted x/y, n,role/unit and reconciliation. Codex runs script, checks metadata vs original and visually checks PNG for clipping and Thai legibility. Worker does not claim checks unrun.

## Final report
Report changed files, checks run, checks not run, issues. No secrets, no model changes.
