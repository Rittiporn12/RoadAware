# รายงาน 13 — สัญญาการให้บริการ inference V2 (research), registry ที่ตรวจ hash ได้, ความทนทานเมื่อข้อมูลขาด และเวลาใช้งาน

**สถานะ: งานวิจัยเท่านั้น | production_ready = false | operational = BLOCKED** — ไม่ใช่ระบบเตือนภัย/ความเสี่ยงรายบุคคลหรือรายเส้นทาง ไม่มีข้อมูล live

## 1. โมเดลที่ให้บริการ (ไม่ fit ใหม่ ไม่ tune ไม่เลือกใหม่)

- **daily**: `hgb_poisson__full` (variant full, 30 features, ใช้ weather=True, traffic=True); bundle sha256 `1b7e794d6278cd6c…`; training cutoff 2023-12-31T18:00:00+07:00; baseline เทียบ `baseline_province_month_k30`
- **6h**: `hgb_poisson__calendar_traffic` (variant calendar_traffic, 29 features, ใช้ weather=False, traffic=True); bundle sha256 `f006ded45f660be8…`; training cutoff 2023-12-31T18:00:00+07:00; baseline เทียบ `baseline_province_block_mean`

registry `2f8a1e2e910fcd01` ตรวจ 32 hash (trust anchors ใน `config/inference_v2.json`, รายงาน/อินพุต/โค้ด 11, selection lock, FUNCTIONS 10/11, ตาราง source 09, bundle) ก่อน `joblib.load` ทุกครั้ง; เวอร์ชัน scikit-learn/joblib ต้องตรงกับที่บันทึก

## 2. สัญญาคำขอ (public function `predict_batch(reg, requests)`)

- รับเฉพาะ `province_key`, `target_date` (สตริง CE `YYYY-MM-DD`), `unit` (`daily`/`6h`) และ `time_block` (เฉพาะ 6h); batch 1–128
- ช่วงวันที่ให้บริการ 2024-01-01..2030-12-31 เป็นการจำกัดทรัพยากรสำหรับ research scenario ไม่ใช่ช่วงที่ตรวจสอบแล้ว; ช่วงที่ประเมิน (เคยเห็นแล้ว) 2024-01-01..2025-12-31
- issue time = วันก่อนเป้าหมาย 18:00 Asia/Bangkok (ลูกค้ากำหนดเองไม่ได้); ชื่อจังหวัดต้องตรง 77 key หรือ alias ที่ audit แล้วเท่านั้น (พระนครศรีอยุธยา→อยุธยา)
- คำขอผิด 35 แบบถูกปฏิเสธทั้ง batch พร้อม error code (field ผลลัพธ์/mask/feature/path, วันที่ผิด/BE/bool/NaN/inf, block ไม่เข้ากับ unit, ซ้ำ ฯลฯ)
- ผลลัพธ์: `expected_recorded_count` (ค่าเฉลี่ยจำนวน record ที่ถูกเลือก เป็นทศนิยม ไม่ปัดเศษ ไม่ใช่ความน่าจะเป็นของการชน ไม่มีสี/เปอร์เซ็นต์ความเสี่ยง), baseline comparator ที่ติดป้ายชัด, ขอบเขต cell/issue/timezone, hash โมเดล, coverage ของ source และ `limitations` (`out_of_evaluated_period`, `stale_model`, covariate ขาด ฯลฯ)

## 3. ความตรงกัน (parity)

- daily saved_10_features selected `hgb_poisson__full`: n=35467, max |diff| = 8.88e-16 (tol 1e-12) → ผ่าน
- daily saved_10_features baseline_comparator `baseline_province_month_k30`: n=35467, max |diff| = 4.44e-16 (tol 1e-12) → ผ่าน
- daily request_builder selected `hgb_poisson__full`: n=35467, max |diff| = 8.88e-16 (tol 1e-12) → ผ่าน
- daily request_builder baseline_comparator `baseline_province_month_k30`: n=35467, max |diff| = 4.44e-16 (tol 1e-12) → ผ่าน
- 6h saved_10_features selected `hgb_poisson__calendar_traffic`: n=141868, max |diff| = 4.44e-16 (tol 1e-12) → ผ่าน
- 6h saved_10_features baseline_comparator `baseline_province_block_mean`: n=141868, max |diff| = 2.22e-16 (tol 1e-12) → ผ่าน
- 6h request_builder selected `hgb_poisson__calendar_traffic`: n=141868, max |diff| = 4.44e-16 (tol 1e-12) → ผ่าน
- 6h request_builder baseline_comparator `baseline_province_block_mean`: n=141868, max |diff| = 2.22e-16 (tol 1e-12) → ผ่าน
- builder vs ตาราง feature 10 (daily): 2253 แถวกำหนดแน่นอน (วันพิเศษ 57, eligible 1889, unknown-label 364, มี weather 1244, ไม่มี weather 1009, ไม่มี traffic 571, ปี 2021, 2022, 2023, 2024, 2025) — ไม่พบความต่าง
- builder vs ตาราง feature 10 (6h): 2428 แถวกำหนดแน่นอน (วันพิเศษ 228, eligible 1944, unknown-label 484, มี weather 1294, ไม่มี weather 1134, ไม่มี traffic 582, ปี 2021, 2022, 2023, 2024, 2025) — ไม่พบความต่าง

**สัญญาการแทนค่าตัวเลขของ training (`training_numeric_representation`)**: feature ตัวเลขของคำขอผ่านการเขียนเป็นข้อความ CSV แบบ default ของ pandas (เหมือน `write_csv_gz` ของ notebook 10) และ parse ด้วย `pd.read_csv` แบบ default (เหมือน `load_unit_frame` ของ notebook 11) ก่อนเข้าโมเดล เพราะ parser default อาจให้ค่าต่างจากค่าในหน่วยความจำ 1 ulp (พบที่ doy_sin/doy_cos) และ threshold ของต้นไม้ขยายความต่างนี้ได้; ไม่ปัดทศนิยม ไม่ clip prediction ไม่เปลี่ยน tolerance ไม่ใช้ label หรือค่าที่บันทึกไว้
- daily: ค่า feature ที่สัญญานี้เปลี่ยน 22590 ค่า; ค่าที่ยังไม่เท่ากับตาราง 10 แบบ bitwise 0 ค่า; ถ้าไม่ใช้สัญญานี้ prediction ต่างจาก 11 สูงสุด 4.45 (diagnostic เท่านั้น)
- 6h: ค่า feature ที่สัญญานี้เปลี่ยน 90360 ค่า; ค่าที่ยังไม่เท่ากับตาราง 10 แบบ bitwise 0 ค่า; ถ้าไม่ใช้สัญญานี้ prediction ต่างจาก 11 สูงสุด 1.43 (diagnostic เท่านั้น)

## 4. Stress: ตั้ง covariate เป็น missing บน keys เดิม (แยก 2024 development / 2025 reused)

> เป็นการทดสอบความไวต่อข้อมูลขาดเท่านั้น ไม่ใช่โลกทางเลือกที่สอดคล้องทางกายภาพหรือผลเชิงสาเหตุ และไม่มีการเปลี่ยน inference จากคะแนนเหล่านี้

| unit | split | scenario | คอลัมน์โมเดลที่ถูกกระทบ | n | deviance | Δ deviance | การเปลี่ยน prediction สูงสุด (ค่าสัมบูรณ์) | สัดส่วนแถวที่ขาดอยู่แล้ว |
|---|---|---|---|---|---|---|---|---|
| daily | development_2024 | unmodified | 0 | 7885 | 1.0944 | 0.0000 | 0.0000 | n/a |
| daily | reused_seen_2025 | unmodified | 0 | 27582 | 1.1319 | 0.0000 | 0.0000 | n/a |
| daily | development_2024 | weather_missing | 2 | 7885 | 1.0944 | 0.0000 | 0.0000 | 1.000 |
| daily | reused_seen_2025 | weather_missing | 2 | 27582 | 1.1319 | 0.0000 | 0.0000 | 1.000 |
| daily | development_2024 | traffic_missing | 4 | 7885 | 1.1388 | 0.0445 | 2.9315 | 0.000 |
| daily | reused_seen_2025 | traffic_missing | 4 | 27582 | 1.1555 | 0.0235 | 2.5073 | 0.000 |
| daily | development_2024 | weather_and_traffic_missing | 6 | 7885 | 1.1388 | 0.0445 | 2.9315 | 1.000 |
| daily | reused_seen_2025 | weather_and_traffic_missing | 6 | 27582 | 1.1555 | 0.0235 | 2.5073 | 1.000 |
| 6h | development_2024 | unmodified | 0 | 31540 | 0.6159 | 0.0000 | 0.0000 | n/a |
| 6h | reused_seen_2025 | unmodified | 0 | 110328 | 0.6214 | 0.0000 | 0.0000 | n/a |
| 6h | development_2024 | weather_missing | 0 | 31540 | 0.6159 | 0.0000 | 0.0000 | n/a |
| 6h | reused_seen_2025 | weather_missing | 0 | 110328 | 0.6214 | 0.0000 | 0.0000 | n/a |
| 6h | development_2024 | traffic_missing | 4 | 31540 | 0.6309 | 0.0150 | 1.9274 | 0.000 |
| 6h | reused_seen_2025 | traffic_missing | 4 | 110328 | 0.6287 | 0.0073 | 1.9564 | 0.000 |
| 6h | development_2024 | weather_and_traffic_missing | 4 | 31540 | 0.6309 | 0.0150 | 1.9274 | 0.000 |
| 6h | reused_seen_2025 | weather_and_traffic_missing | 4 | 110328 | 0.6287 | 0.0073 | 1.9564 | 0.000 |

- daily กับผลรวม 4 ช่วง 6h เป็นโมเดลอิสระ: 1848 province-day, ratio median 0.955 (p05 0.823, p95 1.084) — รายงานไว้ ไม่บังคับให้เท่ากัน

## 5. ความปลอดภัยของ artifact

- 9 negative controls (bundle ถูกแก้ไบต์, path นอก root, model data หาย, anchor ไม่ตรง, selection ต่าง, FUNCTIONS 11 ถูกแก้, notebook 10 หาย, เวอร์ชัน sklearn ไม่ตรง, registry ไม่มีโมเดล) ล้มเหลวตามคาดด้วย DependencyError ก่อนถึงขั้น deserialize

## 6. เวลาใช้งานที่วัดจริง (เครื่องนี้; ไม่มีเกณฑ์ที่แต่งขึ้น)

| ประเภท | unit | batch | n | median ms | p95 ms |
|---|---|---|---|---|---|
| cold_registry_load | (both) |  | 1 | 1599.8 | 1599.8 |
| repeat_registry_load_warm_os_cache | (both) |  | 1 | 988.1 | 988.1 |
| warm_predict_batch | daily | 1 | 15 | 18.8 | 20.0 |
| warm_predict_batch | daily | 32 | 15 | 49.6 | 53.9 |
| warm_predict_batch | daily | 128 | 15 | 111.1 | 120.4 |
| warm_predict_batch | 6h | 1 | 15 | 18.6 | 19.4 |
| warm_predict_batch | 6h | 32 | 15 | 49.7 | 51.1 |
| warm_predict_batch | 6h | 128 | 15 | 110.6 | 112.3 |

## 7. กลุ่มย่อย/จุดพลาดสูงสุดจาก notebook 12 ที่ตรวจรับแล้ว (support เพียงพอเท่านั้น)

- 6h / development_2024 / highest_selected_deviance: high_count=high_ge_2 (dev 4.869, Δbaseline -0.119, n=897); outcome_bin=2-3 (dev 4.516, Δbaseline -0.024, n=817); outcome_bin=1 (dev 1.836, Δbaseline 0.056, n=4021)
- 6h / development_2024 / selected_worse_than_baseline: festival=songkran_pre_1_3 (dev 0.764, Δbaseline 0.064, n=308); outcome_bin=1 (dev 1.836, Δbaseline 0.056, n=4021); province_key=บุรีรัมย์ (dev 0.573, Δbaseline 0.026, n=412)
- 6h / oof / highest_selected_deviance: outcome_bin=4-6 (dev 8.538, Δbaseline -2.476, n=362); high_count=high_ge_2 (dev 4.732, Δbaseline -0.687, n=5195); outcome_bin=2-3 (dev 4.393, Δbaseline -0.528, n=4817)
- 6h / oof / selected_worse_than_baseline: outcome_bin=1 (dev 1.845, Δbaseline 0.055, n=25069); festival=songkran_pre_4_7 (dev 0.601, Δbaseline 0.038, n=2400); province_key=ประจวบคีรีขันธ์ (dev 0.747, Δbaseline 0.011, n=2832)
- 6h / reused_seen_2025 / highest_selected_deviance: outcome_bin=4-6 (dev 7.895, Δbaseline -1.642, n=281); high_count=high_ge_2 (dev 4.846, Δbaseline -0.611, n=3194); outcome_bin=2-3 (dev 4.404, Δbaseline -0.482, n=2887)
- 6h / reused_seen_2025 / selected_worse_than_baseline: province_key=สมุทรสาคร (dev 0.732, Δbaseline 0.044, n=1440); outcome_bin=1 (dev 1.864, Δbaseline 0.014, n=13772); year_month=2025-02 (dev 0.651, Δbaseline 0.004, n=8576)
- daily / development_2024 / highest_selected_deviance: outcome_bin=4-6 (dev 3.698, Δbaseline -0.144, n=226); outcome_bin=2-3 (dev 1.787, Δbaseline -0.050, n=1105); year_month=2024-04 (dev 1.231, Δbaseline -0.085, n=994)
- daily / development_2024 / selected_worse_than_baseline: year_month=2024-06 (dev 0.998, Δbaseline 0.018, n=615); weekday=Mon (dev 1.071, Δbaseline 0.002, n=1145); year_month=2024-07 (dev 0.995, Δbaseline 0.001, n=229)
- daily / oof / highest_selected_deviance: outcome_bin=7-9 (dev 5.218, Δbaseline -2.988, n=247); high_count=high_ge_5 (dev 4.447, Δbaseline -2.517, n=904); outcome_bin=4-6 (dev 3.321, Δbaseline -1.089, n=1381)
- daily / oof / selected_worse_than_baseline: province_key=สุโขทัย (dev 1.362, Δbaseline 0.120, n=700); outcome_bin=1 (dev 0.577, Δbaseline 0.083, n=13435); year_month=2022-02 (dev 1.151, Δbaseline 0.033, n=2076)
- daily / reused_seen_2025 / highest_selected_deviance: high_count=high_ge_5 (dev 5.266, Δbaseline -2.053, n=653); outcome_bin=4-6 (dev 3.573, Δbaseline -1.182, n=807); festival=new_year_pre_4_7 (dev 3.034, Δbaseline 0.085, n=306)
- daily / reused_seen_2025 / selected_worse_than_baseline: province_key=สมุทรสาคร (dev 1.687, Δbaseline 0.297, n=360); festival=new_year_pre_4_7 (dev 3.034, Δbaseline 0.085, n=306); festival=new_year_post_4_7 (dev 1.368, Δbaseline 0.053, n=307)

## 8. ข้อจำกัด (คงเดิมจากหลักฐาน V2)

- labels are selected recorded MOT-source counts (MOT road network only), not complete all-road accidents
- date repair relies on the publisher's own XLSX counterpart (not independent ground truth)
- training_eligible is an outcome-derived offline research filter, unavailable for prospective claims
- weather: nominal JMA GSM lead; historical public delivery latency unverified; coverage may be quota-partial
- traffic: catalog-vintage proxy does not prove historical bytes; revised resources push availability later
- bank calendar: reviewed BOT transcriptions with conservative known_from; later amendments unknown; not a public-holiday calendar
- no untouched test: 2024 development and 2025 reused diagnostics were both seen during development
- training_eligible is an outcome-derived offline filter; served predictions are returned for every cell regardless of label status
- expected counts are model means of SELECTED RECORDED records, not collision probabilities and not personal or route risk
- daily and 6 h models are independent; the sum of four block predictions need not equal the daily prediction
- weather archive มีถึง 2023-12-31 เท่านั้น: วันที่ให้บริการทั้งหมด (≥2024) ไม่มีค่า weather โมเดล daily จึงทำงานด้วย weather = NaN เสมอ
- traffic เป็น AADT รายปี (survey ปี [2020, 2021, 2022, 2023, 2024, 2025]); ปีอนาคตใช้ vintage ล่าสุดก่อนหน้าที่มี ณ issue time และติดป้าย `traffic_vintage_stale` เมื่อห่างเกิน 1 ปี
- bank calendar ที่ review แล้วมีเฉพาะปี [2021, 2022, 2023, 2024, 2025]; ปีอื่นเป็น unknown (NaN) ไม่ถือเป็นวันทำการปกติ
- ไม่มี untouched test; ผลนี้ปิดงาน ML research serving เท่านั้น ไม่ได้แก้ blocker ทางวิทยาศาสตร์สำหรับ production
