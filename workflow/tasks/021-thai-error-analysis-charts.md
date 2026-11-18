# Goal
Create a Python script producing two clear Thai-language presentation charts for accepted V3 Error Analysis. Codex executes the script and visually verifies output. Do not run shell commands.

## Context and evidence
Read workflow/model-gate-presentation-th.md section 4 and output/spatial-model-results/v3-evaluation-017-002/model_gate_presentation_th.md. Use accepted OOF 2022-2023 only, never V2 or 2026. Existing error figures are too technical for the user's slide.

## Allowed files
Only create tools/render_thai_error_analysis.py. Its runtime outputs must be under output/presentation-th/error-analysis/ (PNG and SVG). Do not modify any model, source, report, config or existing output.

## Deliverables
One executable Python script using matplotlib, standard library and existing local fonts. Find Thai font via filesystem glob (Sarabun preferred). No downloads or new dependencies. Use Agg, spacious white backgrounds, dark navy titles, teal actual and orange predicted, direct labels, minimal chart ink, 16:9 >=2400x1350. PNG and SVG for each figure.

1. error_totals_th: two panels daily and 6h. Bar comparison actual recorded selected+linked total 10,701 for both units; HGB predicted totals daily 9,574.10 and 6h 9,446.02. Axis label 'จำนวนรายการรวม'; explanatory title 'HGB ยังทำนายยอดรวมต่ำกว่าที่บันทึก'; percent shortfall direct callouts computed from values (10.53%,11.73%). Both panels share y-scale starting at 0, avoid suggesting per-period average or comparing model quality across units. Footer 'ผล OOF ปี 2022–2023 • เฉพาะรายการที่ผ่านการคัดเลือกและเชื่อมถนนได้'.
2. error_areas_th: simple horizontal bars depicting HGB deviance higher than baseline (positive worse magnitudes), สุพรรณบุรี 3.5754%, ชลบุรี 1.5434%, ฉะเชิงเทรา 0.3536%. Title 'บางพื้นที่ Baseline ยังให้ผลดีกว่า HGB'. Explicit label 'Deviance ของ HGB สูงกว่า Baseline (%)', n records 34/29/661 shown in text labels. Footer 'OOF รายวัน ปี 2022–2023 • จังหวัดตามจุดกึ่งกลางช่วงถนน • บางกลุ่มมีรายการน้อย'. Note reversing the signed gain to positive worse magnitude is intentional and must not label as error increase in MAE or accident rates.

## Acceptance / verification
Script must validate inputs and calculate percentage shortfalls, write metadata JSON with exact source numbers and derived values for independent checks. Codex will run .venv/bin/python tools/render_thai_error_analysis.py, inspect PNGs, verify numbers and Thai rendering. No training/tests of ML pipeline needed.

## Constraints / final report
No invented values or causal claims, no prediction modifications. No user credentials. Report changed files, checks actually run, checks not run, remaining issues. Keep implementation focused.
