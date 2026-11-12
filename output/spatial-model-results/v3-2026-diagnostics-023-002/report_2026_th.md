# รายงานวินิจฉัยข้อมูลปี 2026 (raw observed records) — RoadAware V3

**สถานะ:** complete | research only | production_ready = false

## 1. ข้อเท็จจริงของแหล่งข้อมูล

- ไฟล์ CKAN resource 4625b7aa-99a4-4dfb-9a0f-6402814d0f2c last_modified 2026-11-02T03:23:45.994271, 10098288 bytes, raw rows 18448 แถว (1 แถว = 1 raw observed record; ไม่มี ACC_CODE จึงยืนยัน unique physical event ไม่ได้)
- sha256 ของไฟล์ 42cdd12055c5a1f26b965ec5dda3bf0d43684ecd1a21c3e976836d9a1a89d232 (ตรงกับ manager source pin); ckan hash เท่ากับ md5 ของไฟล์: False
- วันที่เกิดเหตุ 2026-01-01 ถึง 2026-10-31; วันที่รายงาน 2026-01-01 ถึง 2026-11-02; exact full-row duplicates หลังแถวแรก 22
- ช่วงที่ขอ 2026-01-01..2026-09-30 (ตัดตุลาคมด้วยกติกาวันที่ก่อนดูคะแนน). ไฟล์เดิมจบ 7 ก.ย. จึงไม่ใช้อ้างครบกันยายน
- วันอัปเดตไฟล์ไม่ใช่หลักฐานว่าข้อมูลครบ; ข้อมูลที่เข้ามาหลัง 2026-11-02 ไม่ทราบ

## 2. Ledger การคัดเลือก (exclusive ตามลำดับที่ลงทะเบียนไว้)

| step | reason | records | remaining_after_step | any_issue_flag_records |
|---|---|---|---|---|
| 1 | outside_window | 1176 | 17272 | 1176 |
| 2 | exact_duplicate_after_first | 22 | 17250 | 22 |
| 3 | invalid_date_time | 0 | 17250 | 0 |
| 4 | agency_outside_doh_scope | 1086 | 16164 | 1200 |
| 5 | invalid_or_unknown_route | 7344 | 8820 | 8838 |
| 6 | invalid_coordinates_or_province | 250 | 8570 | 471 |
| 7 | outside_pilot_envelope | 4052 | 4518 | 12534 |
| 8 | linkage_outside_50m | 96 | 4422 | 112 |
| 9 | linkage_ambiguous | 43 | 4379 | 46 |
| 10 | linkage_unknown | 0 | 4379 | 0 |
| 11 | no_accepted_segment | 43 | 4336 | 50 |
| 12 | eligible | 4336 | 4336 | 4336 |


รวมทุกเหตุผลเท่ากับ raw rows ทุกแถว (reconciled). ตารางรายเดือน/จังหวัด/หน่วยงานอยู่ใน ledger_by_*.csv (UNKNOWN คงไว้)

## 3. ความล่าช้าในการรายงานและความครบถ้วน

| event_month | n_raw_records | n_lag_known | n_report_date_unknown | n_negative_lag | lag_median_days | lag_p90_days | lag_p99_days | share_lag_gt_label_days | late_arrival_risk_indicator | maturity |
|---|---|---|---|---|---|---|---|---|---|---|
| 2026-01 | 2661 | 2641 | 20 | 0 | 34 | 110 | 232 | 0.5271 | 0.0001895 | unverified |
| 2026-02 | 1933 | 1916 | 17 | 0 | 31 | 92 | 241.7 | 0.5146 | 0.002873 | unverified |
| 2026-03 | 1844 | 1815 | 29 | 0 | 26 | 86 | 218.9 | 0.4402 | 0.009049 | unverified |
| 2026-04 | 2733 | 2725 | 8 | 0 | 2 | 72 | 183 | 0.1989 | 0.01756 | unverified |
| 2026-05 | 1756 | 1755 | 1 | 0 | 21 | 96 | 159 | 0.4131 | 0.02265 | unverified |
| 2026-06 | 1683 | 1683 | 0 | 0 | 24 | 91 | 127 | 0.4658 | 0.03546 | unverified |
| 2026-07 | 1663 | 1663 | 0 | 0 | 32 | 98 | 108 | 0.5105 | 0.07083 | unverified |
| 2026-08 | 1564 | 1564 | 0 | 0 | 16 | 67 | 83 | 0.3165 | 0.1325 | unverified |
| 2026-09 | 1435 | 1435 | 0 | 0 | 8 | 35 | 53 | 0.1268 | 0.2919 | unverified |
| 2026-10 | 1176 | 1176 | 0 | 0 | 5 | 18 | 26 | 0.0008503 | 0.6547 | unverified |


- lag = วันที่รายงาน − วันที่เกิดเหตุ (วัน) เฉพาะ record ที่ parse ได้ทั้งสองวันและ lag ≥ 0; report date ที่ parse ไม่ได้คงเป็น unknown (null) และ lag ติดลบนับแยกไว้ ไม่ถูกนับเป็น 0
- maturity = unverified ทุกเดือน: ไม่มีหลักฐานว่าเดือนใดครบแล้ว และ CKAN last_modified ไม่ได้พิสูจน์ความครบถ้วน
- สมมติฐาน label พร้อมใช้ใน 30 วันของโปรโตคอลเดิมเป็น research assumption; lag ที่วัดได้ (share_lag_gt_label_days > 0) ขัดแย้งกับการอ้างว่าครบใน 30 วัน (ไม่ได้แก้โปรโตคอลเดิมเงียบ ๆ)
- **นิยาม late_arrival_risk_indicator:** สำหรับแต่ละ record ในกลุ่มที่วันที่เกิดเหตุ parse ได้ ให้ อายุ = snapshot (2026-11-02) − วันที่เกิดเหตุ (วัน); คำนวณสัดส่วนของ lag เชิงประจักษ์ของเดือนอ้างอิง [1, 2, 3] (ม.ค.–มี.ค., เฉพาะ lag ที่ ok) ที่ **มากกว่า** อายุนั้น แล้วเฉลี่ยทุก record ในกลุ่ม
- ตัวชี้นี้เป็น risk indicator เท่านั้น: การกระจาย lag อ้างอิงเองก็ถูกตัดขวา (right-truncated) ณ snapshot; **ไม่ใช่** สัดส่วนเหตุการณ์จริงที่ยังไม่ถูกรายงาน ไม่ใช่ความน่าจะเป็น ไม่ใช่ค่าประมาณความครบถ้วน และไม่ได้ใช้ถ่วงน้ำหนักหรือแก้ค่าใด ๆ

## 4. การเปรียบเทียบ snapshot เดิมกับใหม่ (net record-count change/revisions)

| event_month | old_raw_records | new_raw_records | net_record_count_change | identical_full_rows_in_both | old_rows_without_identical_new_row | new_rows_without_identical_old_row |
|---|---|---|---|---|---|---|
| 2026-01 | 2631 | 2661 | 30 | 2352 | 279 | 309 |
| 2026-02 | 1893 | 1933 | 40 | 1604 | 289 | 329 |
| 2026-03 | 1743 | 1844 | 101 | 1370 | 373 | 474 |
| 2026-04 | 2473 | 2733 | 260 | 1957 | 516 | 776 |
| 2026-05 | 1746 | 1756 | 10 | 1647 | 99 | 109 |
| 2026-06 | 1674 | 1683 | 9 | 1439 | 235 | 244 |
| 2026-07 | 1600 | 1663 | 63 | 911 | 689 | 752 |
| 2026-08 | 1361 | 1564 | 203 | 850 | 511 | 714 |
| 2026-09 | 118 | 1435 | 1317 | 40 | 78 | 1395 |
| 2026-10 | 0 | 1176 | 1176 | 0 | 0 | 1176 |


ไม่มี ACC_CODE: แถวที่เปลี่ยนค่าในบางฟิลด์กับแถวใหม่แยกกันไม่ได้ จึงไม่ใช่หลักฐาน late-arriving unique events

## 5. ผลวินิจฉัยโมเดลบน observed positive cells เท่านั้น

| unit | method | n_positive_cells | n_raw_records | n_segments | actual_total | pred_total | mean_poisson_deviance | deviance_status | n_zero_pred_on_positive | deviance_floor_audit | deviance_floor_audit_n_floored | deviance_floor_audit_floored_contribution | mae | rmse | bias_pred_minus_actual | wape |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| daily | selected | 4116 | 4336 | 1128 | 4336 | 153.6 | 7.198 | finite | 0 | 7.198 | 0 | 0 | 1.016 | 1.046 | -1.016 | 0.9646 |
| daily | strong_baseline | 4116 | 4336 | 1128 | 4336 | 144 | n/a | infinite_due_zero_prediction | 50 | 8.011 | 50 | 0.6606 | 1.018 | 1.049 | -1.018 | 0.9668 |
| 6h | selected | 4232 | 4336 | 1128 | 4336 | 41.41 | 9.763 | finite | 0 | 9.763 | 0 | 0 | 1.015 | 1.028 | -1.015 | 0.9904 |
| 6h | strong_baseline | 4232 | 4336 | 1128 | 4336 | 43.82 | n/a | infinite_due_zero_prediction | 175 | 11.51 | 175 | 2.202 | 1.014 | 1.027 | -1.014 | 0.9899 |


- ประเมินเฉพาะ cell (segment × วัน หรือ × ช่วง 6 ชม.) ที่มี eligible linked record อย่างน้อย 1 รายการ ทั้ง selected HGB policy และ strong baseline ใช้ key/y ชุดเดียวกัน
- **outcome-conditioned selection bias:** ทุก cell มี y ≥ 1 จึงไม่เทียบโดยตรงกับ full-population OOF 2022–23 หรือ seen diagnostic 2024–25; ไม่มี verified zero และไม่มี full-population 2026 accuracy
- actual_total/pred_total เป็นผลรวมบน observed positive cells เท่านั้น ไม่ใช่การพยากรณ์ทั้งประชากรหรือรายปี

### นิยาม deviance

- **mean_poisson_deviance (raw, metric หลักของรายงานนี้):** (1/N) Σ 2[y·ln(y/λ) − (y − λ)] บน λ ที่ไม่ปรับค่า. ถ้ามี cell ที่ y > 0 แต่ λ = 0 ค่า limit คือ +∞ → แสดง n/a (JSON null เพราะ strict JSON ไม่รองรับ Infinity) พร้อม deviance_status = infinite_due_zero_prediction และจำนวน n_zero_pred_on_positive; finite = คำนวณได้, unavailable_empty = ไม่มี cell
- **deviance_floor_audit (numerical-floor audit เท่านั้น):** สูตรเดิมของ notebook 20 ที่ล็อกไว้ m = max(λ, 1e-12) เฉพาะใน metric (floor จาก config20 sha256 fbd053cca837 ผ่าน runtime pin chain, ไม่ได้เปลี่ยนค่า). deviance_floor_audit_n_floored = จำนวน cell ที่ λ < floor, deviance_floor_audit_floored_contribution = ส่วนของ mean ที่มาจาก cell เหล่านั้น. ค่านี้ใช้ตรวจสอบเท่านั้น **ไม่ใช่เกณฑ์ใหม่ ไม่ได้ใช้เลือก/ปรับโมเดล** และไม่ได้ทำให้ raw deviance ของ baseline กลายเป็นค่าจำกัด; ถ้า n_floored = 0 นิยามทั้งสองให้ค่าเดียวกันบน cohort นี้

### กลุ่ม under/over (ทิศทางจริง)

- 6h / selected: กลุ่มที่มี support 117 กลุ่ม; ทำนายต่ำกว่าจริง (ratio < 1) 117 กลุ่ม, ทำนายสูงกว่าจริง (ratio > 1) 0 กลุ่ม — **ไม่มีกลุ่มใดที่ทำนายสูงกว่าจริง**; กลุ่มที่ ratio สูงสุดก็ยังทำนายต่ำกว่าจริง
- 6h / strong_baseline: กลุ่มที่มี support 117 กลุ่ม; ทำนายต่ำกว่าจริง (ratio < 1) 117 กลุ่ม, ทำนายสูงกว่าจริง (ratio > 1) 0 กลุ่ม — **ไม่มีกลุ่มใดที่ทำนายสูงกว่าจริง**; กลุ่มที่ ratio สูงสุดก็ยังทำนายต่ำกว่าจริง
- daily / selected: กลุ่มที่มี support 114 กลุ่ม; ทำนายต่ำกว่าจริง (ratio < 1) 114 กลุ่ม, ทำนายสูงกว่าจริง (ratio > 1) 0 กลุ่ม — **ไม่มีกลุ่มใดที่ทำนายสูงกว่าจริง**; กลุ่มที่ ratio สูงสุดก็ยังทำนายต่ำกว่าจริง
- daily / strong_baseline: กลุ่มที่มี support 114 กลุ่ม; ทำนายต่ำกว่าจริง (ratio < 1) 114 กลุ่ม, ทำนายสูงกว่าจริง (ratio > 1) 0 กลุ่ม — **ไม่มีกลุ่มใดที่ทำนายสูงกว่าจริง**; กลุ่มที่ ratio สูงสุดก็ยังทำนายต่ำกว่าจริง
- under_over_ranking.csv: kind = under_predicted (ratio < 1, ต่ำสุดก่อน) / over_predicted (ratio > 1, สูงสุดก่อน) / total_match; ฝั่งที่ว่างมีแถว NONE ระบุชัด
- กลุ่มที่ baseline ดีกว่ารายงานไว้ใน method_comparison.csv; การจัดอันดับเป็นคำอธิบายเท่านั้น ไม่ได้ใช้เปลี่ยน eligibility หรือการเลือกโมเดล

### นิยามกลุ่มภูมิศาสตร์และปฏิทิน

- จังหวัดของ cell ปี 2026 = จังหวัดที่บันทึกใน record ที่พบบ่อยที่สุดของ cell (เสมอกันเลือกตามลำดับตัวอักษร) **ไม่ใช่** จังหวัดจากจุดกึ่งกลาง segment ที่ใช้ใน OOF error groups จึงเทียบกลุ่มโดยตรงไม่ได้
| unit | positive_cells | multi_province_cells | raw_records_in_multi_province_cells | province_rule |
|---|---|---|---|---|
| daily | 4116 | 0 | 0 | mode of recorded event province per cell, ties lexical; not the segment-midpoint province used by OOF error groups |
| 6h | 4232 | 0 | 0 | mode of recorded event province per cell, ties lexical; not the segment-midpoint province used by OOF error groups |


- ช่วงเทศกาล new_year_2026 2026-01-01..2026-01-04, songkran_2026 2026-04-11..2026-04-17 และฤดู (ตามเดือน) เป็น analytical windows สำหรับจัดกลุ่มเท่านั้น ไม่ใช่วันหยุดราชการที่ตรวจสอบแล้ว และไม่ใช่ input ของโมเดล. ช่วงปฏิทินเหล่านี้กำหนดใน config เวลา 07:19 วันที่ 2026-11-12 ก่อนรันจริง 001; ผู้จัดการยืนยันหลัง runner 001 ทำงานเสร็จแต่ก่อนดูผลรายกลุ่ม (timeline แก้ไขเวลา 08:13); correction 1 ไม่ได้เปลี่ยนช่วงใด

## 6. แยกหลักฐานสามชุด

- OOF 2022–23: ใช้เลือกโมเดล (ก่อนมีคะแนน 2026)
- 2024–25: previously seen diagnostic
- 2026: raw observed-record positive-cell diagnostic (ไม่ใช่ strict untouched test เพราะเคยมี data audit ปี 2026 ในโครงการ)

## ข้อจำกัด

- RAW OBSERVED-RECORD diagnostic: no ACC_CODE, so unique physical-event identity and event-level deduplication are unverified; only exact full-row duplicates are removed.
- Only observed POSITIVE eligible linked segment x date (or 6 h block) cells are scored. Full calendar x segment zero-label coverage is NOT verified; unobserved cells stay unknown (never zero). The cell selection is outcome-conditioned, so these metrics are biased and NOT comparable with the full-population 2022-23 OOF or 2024-25 seen diagnostics.
- The snapshot (CKAN last_modified 2026-11-02) does not prove completeness; later arrivals after 2026-11-02 are unknown. The 30-day label availability of the old protocol is a research assumption that the measured report lag contradicts as a completeness claim; no reweighting or correction is applied.
- 2026 had earlier diagnostic data audits in this project; this is NOT a strict untouched test. The models were selected on 2022-23 OOF before any 2026 score.
- Expected SELECTED+LINKED recorded-count rate per segment and horizon; not a probability, not a safety statement, no causal interpretation.
- Research only: production_ready is false.
