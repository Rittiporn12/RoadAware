# รายงานเตรียมข้อมูล v2 (Notebook 10): ซ่อมวันที่, panel เป้าหมาย, feature และตรวจ leakage

สถานะ: งานวิจัยเท่านั้น | production_ready = false | operational = BLOCKED | **ยังไม่มีการ fit หรือเทียบโมเดลใด ๆ** (ขั้นถัดไปคือ notebook 11)

## 1. สิ่งที่เปลี่ยนจาก v1 และเหตุผล

- แถวนำเข้า 127375 แถว (CSV ดิบเดิมทุกปี รวม 2026 ที่เป็น diagnostic เท่านั้น); v1 retained 84296 -> v2 retained 106308
- ซ่อมวันที่กำกวม (D/M vs M/D) ได้ 22052 แถว โดยใช้เฉพาะคู่ข้อมูล XLSX ของผู้เผยแพร่ที่ ACC_CODE ตรงตัว, วันที่ typed เดียว, อยู่ในชุดวันที่ผู้สมัครของแถวนั้น และ notebook 10 ตรวจบริบทจังหวัด + เวลา (HH:MM) ซ้ำเองอย่างอิสระแล้วตรงกันทุกแถวของ ID
- ผลตรวจบริบทอิสระ: {'agree': 22052, 'unavailable_province': 5} (unavailable = ข้อมูลบริบทไม่ครบ จึงไม่ถือว่ายืนยัน และไม่ซ่อม)
- วันที่ที่ v1 อ่านได้ไม่กำกวมไม่ถูกเปลี่ยนเลย (ตรวจ assert แล้ว); กลุ่ม id_conflict_* เดิมยังถูกกักกัน; ไม่มีแถวใหม่จาก XLSX; ปี 2022 เป็นรูปแบบผสม จึงไม่มี parser D/M หรือ M/D แบบรวมทั้งปี

| ปี พ.ศ. | ปี ค.ศ. | นำเข้า | retained | collapsed | quarantined | diagnostic | v1 retained | ส่วนต่าง | สมดุล |
|---|---|---|---|---|---|---|---|---|---|
| 2564 | 2021 | 20062 | 19996 | 0 | 66 | 0 | 12599 | 7397 | True |
| 2565 | 2022 | 20566 | 20492 | 0 | 74 | 0 | 13249 | 7243 | True |
| 2566 | 2023 | 23841 | 20490 | 0 | 3351 | 0 | 13118 | 7372 | True |
| 2567 | 2024 | 23952 | 21788 | 0 | 2164 | 0 | 21788 | 0 | True |
| 2568 | 2025 | 23715 | 23542 | 0 | 173 | 0 | 23542 | 0 | True |
| 2569 | 2026 | 15239 | 0 | 0 | 0 | 15239 | 0 | 0 | True |

## 2. ธงป้ายกำกับที่ไม่ทราบ (unknown labels)

ธงสร้างใหม่จากความไม่แน่นอนที่เหลือ: v1 41378 -> v2 23629 province-days (ลบเพราะซ่อมได้ 17749, เพิ่ม 0). แถวจังหวัดว่าง/ไม่อยู่ใน panel ธงทั้ง 77 จังหวัด (1953 แถว); แถวไม่มีวันที่ผู้สมัคร 0 แถว (นโยบาย v1_count_only: นับใน unplaceable_rows_province_year เป็น caveat ไม่ใช่ศูนย์ที่ทราบ). เซลล์ที่ถูกธง training_eligible = false และธงรายวันกระจายไปทั้ง 4 บล็อก. ธง/mask เป็นตัวกรองวิจัยแบบ offline ที่ได้จากผลลัพธ์ ห้ามใช้เป็น feature

## 3. Panel เป้าหมาย

- province-day: 140602 แถว (77 x 1826), eligible 116973; province x 6 ชม.: 562408 แถว, eligible 467892
- เหตุการณ์ที่วางลง panel 106308; ตรวจ: {'counts_nonnegative': True, 'daily_equals_sum_of_blocks': True, 'daily_total_equals_events': True, 'block_total_equals_events': True, 'blocks_per_day': True, 'flags_broadcast_to_blocks': True, 'eligible_is_not_flagged': True}
- issue = วันก่อนเป้าหมาย 18:00 Asia/Bangkok ทั้งสองหน่วย; target_start/target_end ระบุ offset +07:00 ชัดเจน; 00-06/06-12/12-18/18-24 (06:00:00 อยู่บล็อก 06-12; 24:00 ไม่ valid)
- y_recorded_count = จำนวนบันทึก MOT ที่ถูกเลือก ไม่ใช่อุบัติเหตุจริงทั้งหมด; ศูนย์ในเซลล์ที่ทราบ = ไม่มีบันทึกที่ถูกเลือก ไม่ใช่ศูนย์จริงที่พิสูจน์แล้ว
- split เดิม: train 2021-2023, development_2024, reused_seen_2025 (เคยเห็นแล้ว ไม่ใช่ test อิสระ); 2026 ไม่เป็น label

## 4. คอลัมน์ canonical ที่ใช้/ไม่ใช้

| canonical | header ต้นฉบับ (alias) | บทบาทใน v2 |
|---|---|---|
| year_reported | ปีที่เกิดเหตุ | v1 consistency check only |
| date_raw | วันที่เกิดเหตุ | label (วันที่เหตุการณ์) + date repair |
| time_raw | เวลา | label (บล็อกเวลา 6 ชม.) + context check |
| report_date_raw | วันที่รายงาน | ไม่ใช้เป็น feature (descriptive/v1 ID-conflict signature เท่านั้น) |
| report_time_raw | เวลาที่รายงาน | ไม่ใช้เป็น feature (descriptive/v1 ID-conflict signature เท่านั้น) |
| acc_code | ACC_CODE | lineage/ID group only |
| agency | หน่วยงาน | ไม่ใช้เป็น feature (descriptive/v1 ID-conflict signature เท่านั้น) |
| road_agency_type | สายทางหน่วยงาน | ไม่ใช้เป็น feature (descriptive/v1 ID-conflict signature เท่านั้น) |
| route_code | รหัสสายทาง | ไม่ใช้เป็น feature (descriptive/v1 ID-conflict signature เท่านั้น) |
| route_name | สายทาง | ไม่ใช้เป็น feature (descriptive/v1 ID-conflict signature เท่านั้น) |
| km | KM / ก.ม. | ไม่ใช้เป็น feature (descriptive/v1 ID-conflict signature เท่านั้น) |
| province | จังหวัด | label key + context check |
| vehicle_1 | รถคันที่1 | ไม่ใช้เป็น feature (descriptive/v1 ID-conflict signature เท่านั้น) |
| location_type | บริเวณที่เกิดเหตุ / บริเวณที่เกิดเหตุ/ลักษณะทาง | ไม่ใช้เป็น feature (descriptive/v1 ID-conflict signature เท่านั้น) |
| location_other | บริเวณที่เกิดเหตุอื่น | ไม่ใช้เป็น feature (descriptive/v1 ID-conflict signature เท่านั้น) |
| presumed_cause | มูลเหตุสันนิษฐาน | ไม่ใช้เป็น feature (descriptive/v1 ID-conflict signature เท่านั้น) |
| accident_type | ลักษณะการเกิดเหตุ / ลักษณะการเกิดอุบัติเหตุ | ไม่ใช้เป็น feature (descriptive/v1 ID-conflict signature เท่านั้น) |
| weather | สภาพอากาศ | ไม่ใช้เป็น feature (descriptive/v1 ID-conflict signature เท่านั้น) |
| latitude | LATITUDE | v1 coordinate exclusion only |
| longitude | LONGITUDE | v1 coordinate exclusion only |
| n_vehicles | รถที่เกิดเหตุ / จำนวนรถที่เกิดเหตุ(รวมคันที่1) | ไม่ใช้เป็น feature (descriptive/v1 ID-conflict signature เท่านั้น) |
| n_involved | รถและคนที่เกิดเหตุ / จำนวนที่เกิดเหตุทั้งหมด(รวมคนเดินเท้า) | ไม่ใช้เป็น feature (descriptive/v1 ID-conflict signature เท่านั้น) |
| deaths | ผู้เสียชีวิต / จำนวนผู้เสียชีวิต | ไม่ใช้เป็น feature (descriptive/v1 ID-conflict signature เท่านั้น) |
| serious_injuries | ผู้บาดเจ็บสาหัส / จำนวนผู้บาดเจ็บสาหัส | ไม่ใช้เป็น feature (descriptive/v1 ID-conflict signature เท่านั้น) |
| minor_injuries | ผู้บาดเจ็บเล็กน้อย / จำนวนผู้บาดเจ็บเล็กน้อย | ไม่ใช้เป็น feature (descriptive/v1 ID-conflict signature เท่านั้น) |
| injured_total | รวมจำนวนผู้บาดเจ็บ | ไม่ใช้เป็น feature (descriptive/v1 ID-conflict signature เท่านั้น) |

การ normalize ข้ามปี: ข้อความถูกยุบช่องว่างเท่านั้น (ไม่ recode ประเภทอุบัติเหตุ); ชื่อจังหวัดใช้ alias ที่ตรวจแล้วแบบตรงตัว (พระนครศรีอยุธยา -> อยุธยา); ประเภทอุบัติเหตุแสดงเฉพาะใน descriptive_only_accident_type_by_year.csv (แถว v1 retained) และไม่ใช่ตัวทำนาย

## 5. Feature (รู้ก่อนเวลา issue) และข้อจำกัด

| กลุ่ม | ชื่อ | หน่วย | available_at | non-null | สถานะทดสอบ |
|---|---|---|---|---|---|
| core | province | category (v1 77-province key) | static | 1.000 | deterministic_rule_tested |
| core | day_of_week | 0=Mon..6=Sun | deterministic | 1.000 | deterministic_rule_tested |
| core | month | 1..12 | deterministic | 1.000 | deterministic_rule_tested |
| core | day_of_month | 1..31 | deterministic | 1.000 | deterministic_rule_tested |
| core | is_weekend | 0/1 | deterministic | 1.000 | deterministic_rule_tested |
| core | doy_sin | sin(2*pi*(doy-1)/days_in_year) | deterministic | 1.000 | deterministic_rule_tested |
| core | doy_cos | cos(2*pi*(doy-1)/days_in_year) | deterministic | 1.000 | deterministic_rule_tested |
| timeblock | time_block | category 00-06/06-12/12-18/18-24 local | deterministic | 1.000 | deterministic_rule_tested |
| festival | fest_songkran_dist | days, signed, clipped +-14 | deterministic | 1.000 | deterministic_rule_tested |
| festival | fest_songkran_in | 0/1 | deterministic | 1.000 | deterministic_rule_tested |
| festival | fest_songkran_pre_1_3 | 0/1 | deterministic | 1.000 | deterministic_rule_tested |
| festival | fest_songkran_pre_4_7 | 0/1 | deterministic | 1.000 | deterministic_rule_tested |
| festival | fest_songkran_post_1_3 | 0/1 | deterministic | 1.000 | deterministic_rule_tested |
| festival | fest_songkran_post_4_7 | 0/1 | deterministic | 1.000 | deterministic_rule_tested |
| festival | fest_new_year_dist | days, signed, clipped +-14 | deterministic | 1.000 | deterministic_rule_tested |
| festival | fest_new_year_in | 0/1 | deterministic | 1.000 | deterministic_rule_tested |
| festival | fest_new_year_pre_1_3 | 0/1 | deterministic | 1.000 | deterministic_rule_tested |
| festival | fest_new_year_pre_4_7 | 0/1 | deterministic | 1.000 | deterministic_rule_tested |
| festival | fest_new_year_post_1_3 | 0/1 | deterministic | 1.000 | deterministic_rule_tested |
| festival | fest_new_year_post_4_7 | 0/1 | deterministic | 1.000 | deterministic_rule_tested |
| bank_calendar | bank_holiday_asof | 0/1, NaN when coverage unknown at issue | known_from + 1 day 00:00 local <= issue (add/remove replay) | 0.996 | asof_assertions_and_negative_controls_passed |
| bank_calendar | bank_calendar_known_asof | 0/1 | issue time | 1.000 | asof_assertions_and_negative_controls_passed |
| season | season_hot | 0/1 | deterministic | 1.000 | deterministic_rule_tested |
| season | season_wet | 0/1 | deterministic | 1.000 | deterministic_rule_tested |
| season | season_cool | 0/1 | deterministic | 1.000 | deterministic_rule_tested |
| weather | wx_rain_sum_mm_d2 | mm per target day (sum of 24 preceding-hour values) | latest nominal issue bound + 6 h <= issue | 0.529 | asof_assertions_and_negative_controls_passed |
| weather | wx_temp_mean_c_d2 | deg C mean of 24 instant values | latest nominal issue bound + 6 h <= issue | 0.530 | asof_assertions_and_negative_controls_passed |
| weather | wx_block_rain_sum_mm_d2 | mm per target block (6 preceding-hour values) | latest nominal issue bound + 6 h <= issue | 0.529 | asof_assertions_and_negative_controls_passed |
| weather | wx_block_temp_mean_c_d2 | deg C mean of 6 instant values | latest nominal issue bound + 6 h <= issue | 0.530 | asof_assertions_and_negative_controls_passed |
| traffic | trf_mean_aadt | vehicles/day, mean over DOH survey-point station rows | newest prior vintage with proxy available_from <= issue | 0.754 | asof_assertions_and_negative_controls_passed |
| traffic | trf_median_aadt | vehicles/day, median over station rows | as trf_mean_aadt | 0.754 | asof_assertions_and_negative_controls_passed |
| traffic | trf_mean_heavy_share_pct | % heavy vehicles, mean over valid station rows | as trf_mean_aadt | 0.754 | asof_assertions_and_negative_controls_passed |
| traffic | trf_n_station_rows | count of station rows (survey coverage) | as trf_mean_aadt | 0.754 | asof_assertions_and_negative_controls_passed |
| history | (none) |  | unverified | 0.000 | pending_not_implemented |

- เทศกาล: signed distance = target date - nearest festival day (0 inside the festival, negative before the first day, positive after the last day); nearest occurrence searched in the previous, same and next year; clipped to [-clip_days, clip_days]
- ฤดูกาล: simplistic national calendar-month proxy (hot Mar-May, wet Jun-Oct, cool Nov-Feb); not observed rain, not proof all regions share these seasons
- อากาศ: JMA GSM previous_day2 (nominal ~48 h lead) archived forecast at the province representative point; feature only when every hour is present (no partial sums) and latest nominal issue bound + 6 h <= issue time; otherwise NaN (train-only imputation later). Never target-day observations/reanalysis.
- จราจร: newest PRIOR survey year (survey_year_ce < target year) whose catalog proxy available_from (max(created, last_modified) + 1 day) <= issue time; no target-year actuals, no future/nearest backfill; missing -> NaN. Catalog proxy does not prove historical bytes.
- ปฏิทินธนาคาร (ธปท.) ≠ วันหยุดราชการ; ปีที่ไม่รู้ coverage ณ เวลา issue เป็น NaN ไม่ใช่วันปกติ
- ประวัติอุบัติเหตุ: PENDING: conditional history sensitivity not implemented; historical publication availability is unverified and Codex must confirm a separate scenario after the primary experiment (30-day minimum delay assumption per v2-feature-policy).
- negative controls ที่ถูกปฏิเสธ: 13/13; as-of assertions: {'traffic_prior_year_only': True, 'traffic_available_before_issue': True, 'bank_holiday_known_before_issue': True, 'bank_unknown_coverage_is_nan': True, 'weather_guard_rechecked_in_10': True, 'features_have_no_infinity': True, 'same_keys_all_models': True}

## 6. ความครอบคลุมของแหล่งข้อมูลรายปี

year,cells,eligible_share,weather_rain_nonnull,weather_temp_nonnull,traffic_nonnull,bank_calendar_known,weather_block_rain_nonnull
2021,28105,0.9926,0.9997,1.0,0.0,0.9808,0.9999
2022,28105,0.9922,0.9986,1.0,0.7699,1.0,0.9996
2023,28105,0.9153,0.6466,0.6494,1.0,1.0,0.6485
2024,28182,0.2798,0.0,0.0,1.0,1.0,0.0
2025,28105,0.9814,0.0,0.0,1.0,1.0,0.0


## 7. ข้อจำกัด / ช่องว่าง (จากการรันจริง)

- labels are selected recorded MOT-source counts (MOT road network only), not complete all-road accidents
- date repair relies on the publisher's own XLSX counterpart (not independent ground truth)
- training_eligible is an outcome-derived offline research filter, unavailable for prospective claims
- weather: nominal JMA GSM lead; historical public delivery latency unverified; coverage may be quota-partial
- traffic: catalog-vintage proxy does not prove historical bytes; revised resources push availability later
- bank calendar: reviewed BOT transcriptions with conservative known_from; later amendments unknown; not a public-holiday calendar
- no model has been fitted or compared in notebook 10

## 8. ส่งต่อให้ notebook 11

- ใช้ panel_daily_v2 / panel_6h_v2 + features_daily_v2 / features_6h_v2 (keys เรียงตรงกันทุกแถว) จาก data/v2 ที่ hash ตรงกับ preparation_manifest.json
- train/evaluate เฉพาะ training_eligible = true; ทุกโมเดลและ baseline ใช้ keys ชุดเดียวกัน; feature ที่หายเป็น NaN ให้ imputer ที่ fit จาก train เท่านั้น
- ห้ามนำ target_date/split/ID/target/mask/ธง เข้าโมเดล; ต้องล็อก protocol v2 ก่อน fit; ยังไม่มีข้ออ้างว่าโมเดลใดดีกว่า baseline
