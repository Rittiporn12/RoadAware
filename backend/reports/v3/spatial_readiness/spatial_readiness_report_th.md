# รายงานความพร้อมข้อมูลเชิงพื้นที่ RoadAware (V3 audit)

สร้าง 2026-11-11T01:35:12.385063+00:00 UTC · config `spatial_readiness_v3.0` · notebook `16_spatial_data_readiness.ipynb`

**สถานะ: audit/feasibility เท่านั้น** ไม่มีการ fit โมเดล ไม่มี threshold/สี ไม่มีการดาวน์โหลด ผล V2 (province daily/6h) ไม่ได้ยืนยันความสามารถรายพื้นที่ ปี 2024/2025 เป็น seen diagnostic ปี 2026 (ไม่มี ID) เป็น diagnostic เท่านั้น ไม่มี untouched future test

## 1. Raw linkage

เชื่อม V2 retained events ได้ **106,308/106,308** แบบ 1:1 (source_file/source_row → data index source_row−2, BE-year:ACC_CODE ตรงทุกแถว, ไม่มี raw record ถูกใช้ซ้ำ) · event_date ปีไม่ตรงกับปีไฟล์: 0 (รายงานเท่านั้น ไม่แก้)

| source_file | ce_year | split | n_linked | raw_records | n_event_year_ne_file_year |
|---|---|---|---|---|---|
| accidents_2564_original.csv | 2,021 | train | 19,996 | 20,062 | 0 |
| accidents_2565_original.csv | 2,022 | train | 20,492 | 20,566 | 0 |
| accidents_2566_original.csv | 2,023 | train | 20,490 | 23,841 | 0 |
| accidents_2567_original.csv | 2,024 | seen_diagnostic | 21,788 | 23,952 | 0 |
| accidents_2568_original.csv | 2,025 | seen_diagnostic | 23,542 | 23,715 | 0 |

## 2. พิกัด / สายทาง / KM (flag เท่านั้น ไม่แก้ค่า)

retained: inside broad bbox (ยังไม่ยืนยันถนน/จังหวัด/datum) 106,308 · swap candidate (ไม่สลับให้) 0 · datum ในแหล่งข้อมูล: ไม่ระบุ

| coord_status | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|
| inside_broad_bbox_unverified | 19,996 | 20,492 | 20,490 | 21,788 | 23,542 |

raw ทุกแถวตาม disposition เดิมของ V2 (ไม่เขียนทับ disposition):

| v2_disposition | coord_status | n_records |
|---|---|---|
| diagnostic | inside_broad_bbox_unverified | 15,088 |
| diagnostic | missing | 151 |
| quarantined | inside_broad_bbox_unverified | 5,101 |
| quarantined | missing | 721 |
| quarantined | outside_broad_bbox | 5 |
| quarantined | swap_candidate_unrepaired | 1 |
| retained | inside_broad_bbox_unverified | 106,308 |

| split | n_events | n_inside_bbox_unverified | n_low_precision | n_lat_equals_lon | n_at_repeated_coordinate | n_far_from_province_event_median |
|---|---|---|---|---|---|---|
| seen_diagnostic | 45,330 | 45,330 | 22 | 0 | 545 | 25 |
| train | 60,978 | 60,978 | 14 | 0 | 733 | 23 |

far rule: great-circle distance > 150 km from the median recorded point of its own province (candidate inconsistency, not point-in-province)

จุดพิกัดซ้ำ (≥5 เหตุ): {'coord_keys_repeated': 188, 'events_at_repeated_keys': 1278, 'keys_spanning_multiple_route_keys': 2, 'keys_spanning_multiple_provinces': 0, 'keys_with_events_on_one_date_only': 0} — ไม่ถือว่าเป็นเหตุซ้ำ อาจเป็นจุด default/landmark/ปัดเศษ หรือ hotspot จริง

รูปแบบ KM (ตัวเลข = km ตามหัวคอลัมน์; `a+b` = a km + b m เป็นสมมติฐานที่บันทึกไว้; comma กำกวมจึงไม่ parse):

| km_format | km_status | n_events |
|---|---|---|
| decimal_number | parsed_unvalidated | 105,991 |
| missing | missing | 317 |

| route_format | n_events |
|---|---|
| digits_only | 101,364 |
| letters_and_digits | 4,935 |
| missing | 9 |

## 3. Geometry ที่มีในเครื่อง

| capability | requires_role | status | reason |
|---|---|---|---|
| point_in_province | province_polygons | PENDING_NOT_VERIFIED | no hash-verified province_polygons dataset in the local registry |
| road_snapping | road_network | PENDING_NOT_VERIFIED | no hash-verified road_network dataset in the local registry |
| road_universe_denominator | road_network | PENDING_NOT_VERIFIED | no hash-verified road_network dataset in the local registry |
| stable_segment_ids | road_network | PENDING_NOT_VERIFIED | no hash-verified road_network dataset in the local registry |
| route_corridor_intersection | road_network | PENDING_NOT_VERIFIED | no hash-verified road_network dataset in the local registry |

| source_id | role | format | status | license | version |
|---|---|---|---|---|---|
| mot_transportgis_road_network | road_network | WMS | not_collected | to verify at collection | unknown |
| osm_thailand_snapshot | road_network | PBF | not_collected | ODbL 1.0 (attribution required) | dated snapshot to be chosen |
| geoboundaries_tha_adm1 | province_polygons | GEOJSON | not_collected | gbOpen (verify at collection) | commit 9469f09 |

ไฟล์ geometry ที่พบในเครื่อง: 1 ไฟล์ (ยังไม่ register จึงใช้ไม่ได้) · catalog snapshot ในเครื่อง (metadata เท่านั้น): image_or_map_service_not_vector: 1, tabular_no_verified_geometry: 34, vector_geometry_candidate: 2

แผนเก็บ geometry (ขั้นถัดไปที่ Codex ควบคุม ต้องใช้ network): (1) ตรวจว่า MOT transportgis มี vector/API + license ไม่ใช่เฉพาะ WMS ภาพ (2) ถ้าไม่มี ใช้ OSM snapshot ที่ลงวันที่ + ODbL attribution โดยไม่เรียกว่าเป็นโครงข่าย MOT ครบ (3) polygon จังหวัด geoBoundaries ADM1 ที่ pin commit (4) pin sha256 ใน config แล้ว audit CRS/vintage/coverage/stable ID ก่อนใช้

## 4. Candidate corridor envelope (ไม่ใช่เส้นทาง SPU–เขาใหญ่ที่ routing แล้ว)

| province_key | split | n_events | n_coord_inside_bbox_unverified | n_route_present | n_km_present | n_km_parsed_unvalidated | n_route_keys | n_distinct_coord_keys | n_at_repeated_coordinate |
|---|---|---|---|---|---|---|---|---|---|
| กรุงเทพมหานคร | seen_diagnostic | 5,380 | 5,380 | 5,380 | 5,351 | 5,351 | 49 | 4,857 | 276 |
| กรุงเทพมหานคร | train | 4,959 | 4,959 | 4,959 | 4,928 | 4,928 | 48 | 4,374 | 361 |
| นครนายก | seen_diagnostic | 184 | 184 | 184 | 184 | 184 | 15 | 178 | 0 |
| นครนายก | train | 251 | 251 | 251 | 251 | 251 | 25 | 247 | 0 |
| นครราชสีมา | seen_diagnostic | 2,142 | 2,142 | 2,139 | 2,138 | 2,138 | 55 | 2,057 | 16 |
| นครราชสีมา | train | 2,646 | 2,646 | 2,646 | 2,645 | 2,645 | 59 | 2,592 | 8 |
| ปทุมธานี | seen_diagnostic | 944 | 944 | 944 | 944 | 944 | 46 | 917 | 11 |
| ปทุมธานี | train | 1,443 | 1,443 | 1,443 | 1,442 | 1,442 | 36 | 1,419 | 4 |
| สระบุรี | seen_diagnostic | 479 | 479 | 479 | 479 | 479 | 51 | 459 | 0 |
| สระบุรี | train | 758 | 758 | 758 | 756 | 756 | 52 | 739 | 0 |
| อยุธยา | seen_diagnostic | 836 | 836 | 836 | 817 | 817 | 54 | 821 | 0 |
| อยุธยา | train | 1,170 | 1,170 | 1,170 | 1,116 | 1,116 | 58 | 1,147 | 0 |

การกระจายพิกัด (great-circle; median event point ไม่ใช่ centroid ของ polygon):

| province_key | split | n_events_valid_coord | n_distinct_coord_keys | dist_to_event_median_km_p50 | dist_to_event_median_km_p90 | dist_to_event_median_km_max | nn_m_p10 | nn_m_p50 | nn_m_p90 | share_nn_same_point | nn_subsampled |
|---|---|---|---|---|---|---|---|---|---|---|---|
| กรุงเทพมหานคร | seen_diagnostic | 5,380 | 4,857 | 17.106 | 22.704 | 43.544 | 0 | 7.57 | 67.931 | 0.151 | False |
| กรุงเทพมหานคร | train | 4,959 | 4,374 | 13.583 | 29.565 | 35.42 | 0 | 9.564 | 59.548 | 0.174 | False |
| นครนายก | seen_diagnostic | 184 | 178 | 10.125 | 18.564 | 29.353 | 15.18 | 191.142 | 1,255.036 | 0.065 | False |
| นครนายก | train | 251 | 247 | 10.934 | 20.354 | 29.988 | 6.144 | 171.401 | 1,283.792 | 0.032 | False |
| นครราชสีมา | seen_diagnostic | 2,142 | 2,057 | 40.194 | 75.49 | 121.836 | 4.01 | 89.769 | 829.629 | 0.068 | False |
| นครราชสีมา | train | 2,646 | 2,592 | 41.687 | 80.424 | 117.178 | 3.144 | 55.349 | 698.39 | 0.036 | False |
| ปทุมธานี | seen_diagnostic | 944 | 917 | 8.807 | 22.938 | 39.798 | 1.851 | 31.429 | 601.381 | 0.048 | False |
| ปทุมธานี | train | 1,443 | 1,419 | 8.579 | 18.347 | 39.349 | 1.164 | 18.518 | 279.279 | 0.031 | False |
| สระบุรี | seen_diagnostic | 479 | 459 | 16.238 | 27.276 | 54.391 | 7.94 | 126.017 | 1,051.234 | 0.077 | False |
| สระบุรี | train | 758 | 739 | 16.642 | 28.89 | 78.645 | 0.813 | 100.917 | 795.558 | 0.046 | False |
| อยุธยา | seen_diagnostic | 836 | 821 | 11.43 | 32.677 | 48.123 | 6.211 | 52.516 | 877.832 | 0.033 | False |
| อยุธยา | train | 1,170 | 1,147 | 12.576 | 32.584 | 46.084 | 1.821 | 49.304 | 563.844 | 0.038 | False |

Reconcile กับ preflight ของ manager:

| scope | metric | preflight | this_run | match |
|---|---|---|---|---|
| all retained | finite_coords | 106,308 | 106,308 | True |
| all retained | inside_broad_thailand_bbox | 106,308 | 106,308 | True |
| all retained | route_code_present | 106,299 | 106,299 | True |
| all retained | km_field_present | 105,991 | 105,991 | True |
| all retained | unique_coords_rounded_6dp | 101,473 | 101,473 | True |
| all retained | retained_v2_events | 106,308 | 106,308 | True |
| กรุงเทพมหานคร | events | 10,339 | 10,339 | True |
| กรุงเทพมหานคร | route_code_present | 10,339 | 10,339 | True |
| กรุงเทพมหานคร | km_field_present | 10,279 | 10,279 | True |
| นครนายก | events | 435 | 435 | True |
| นครนายก | route_code_present | 435 | 435 | True |
| นครนายก | km_field_present | 435 | 435 | True |
| นครราชสีมา | events | 4,788 | 4,788 | True |
| นครราชสีมา | route_code_present | 4,785 | 4,785 | True |
| นครราชสีมา | km_field_present | 4,783 | 4,783 | True |
| ปทุมธานี | events | 2,387 | 2,387 | True |
| ปทุมธานี | route_code_present | 2,387 | 2,387 | True |
| ปทุมธานี | km_field_present | 2,386 | 2,386 | True |
| สระบุรี | events | 1,237 | 1,237 | True |
| สระบุรี | route_code_present | 1,237 | 1,237 | True |
| สระบุรี | km_field_present | 1,235 | 1,235 | True |
| อยุธยา | events | 2,006 | 2,006 | True |
| อยุธยา | route_code_present | 2,006 | 2,006 | True |
| อยุธยา | km_field_present | 1,933 | 1,933 | True |

ช่วงถนน [0.5, 1, 2] km เป็นข้อเสนอจนกว่าจะมี road inventory; ไม่สร้าง segment ID จาก cluster ของเหตุ

## 5. ความเบาบาง (proxy, train 2021–2023, corridor envelope)

| grouping | n_space_keys_observed | n_occupied_groups | share_occupied_groups_exactly_1_event | events_per_occupied_group_p50 | events_per_occupied_group_p90 |
|---|---|---|---|---|---|
| province x day (proxy) | 6 | 4,113 | 0.382 | 2 | 6 |
| province x 6h (proxy) | 6 | 7,497 | 0.683 | 1 | 3 |
| province x 7d (proxy) | 6 | 893 | 0.074 | 8 | 30 |
| province+route code x day (proxy) | 278 | 8,132 | 0.755 | 1 | 2 |
| province+route code x 6h (proxy) | 278 | 9,890 | 0.89 | 1 | 2 |
| province+route code x 7d (proxy) | 278 | 4,369 | 0.578 | 1 | 6 |

zero labels: **NOT_ESTABLISHED: no verified road universe or reporting coverage** — ไม่มีการสร้าง zero และไม่ train

| split | grouping | n_space_keys_observed | n_periods | crossproduct_cells_if_built | within_budget |
|---|---|---|---|---|---|
| train | province x day (proxy) | 77 | 1,095 | 84,315 | True |
| train | province x 6h (proxy) | 77 | 4,380 | 337,260 | True |
| train | province x 7d (proxy) | 77 | 157 | 12,089 | True |
| train | province+route code x day (proxy) | 2,487 | 1,095 | 2,723,265 | True |
| train | province+route code x 6h (proxy) | 2,487 | 4,380 | 10,893,060 | False |
| train | province+route code x 7d (proxy) | 2,487 | 157 | 390,459 | True |
| seen_diagnostic | province x day (proxy) | 77 | 731 | 56,287 | True |
| seen_diagnostic | province x 6h (proxy) | 77 | 2,924 | 225,148 | True |
| seen_diagnostic | province x 7d (proxy) | 77 | 105 | 8,085 | True |
| seen_diagnostic | province+route code x day (proxy) | 2,292 | 731 | 1,675,452 | True |
| seen_diagnostic | province+route code x 6h (proxy) | 2,292 | 2,924 | 6,701,808 | False |
| seen_diagnostic | province+route code x 7d (proxy) | 2,292 | 105 | 240,660 | True |

V2 province-day panel (บริบทเท่านั้น; eligibility มาจาก outcome ใช้เป็น coverage รายพื้นที่ไม่ได้):

| province_key | split | n_province_days | n_training_eligible_days | n_eligible_zero_days | recorded_count_sum |
|---|---|---|---|---|---|
| กรุงเทพมหานคร | seen_diagnostic | 731 | 279 | 0 | 5,380 |
| กรุงเทพมหานคร | train | 1,095 | 771 | 31 | 4,959 |
| นครนายก | seen_diagnostic | 731 | 463 | 368 | 184 |
| นครนายก | train | 1,095 | 1,061 | 883 | 251 |
| นครราชสีมา | seen_diagnostic | 731 | 463 | 32 | 2,142 |
| นครราชสีมา | train | 1,095 | 1,038 | 152 | 2,646 |
| ปทุมธานี | seen_diagnostic | 731 | 463 | 154 | 944 |
| ปทุมธานี | train | 1,095 | 1,055 | 319 | 1,443 |
| สระบุรี | seen_diagnostic | 731 | 463 | 256 | 479 |
| สระบุรี | train | 1,095 | 1,037 | 564 | 758 |
| อยุธยา | seen_diagnostic | 731 | 463 | 177 | 836 |
| อยุธยา | train | 1,095 | 1,060 | 420 | 1,170 |

## 6. Spatial universe / geocoding / snap quality ที่ต้องมีในขั้นถัดไป

- Road universe ของพื้นที่ศึกษา รวมช่วงที่ไม่เคยมีเหตุ เป็นตัวหาร; แยก observed zero / unknown reporting / outside network
- Snap: รหัสสายทางตรง + KM สอดคล้อง + ระยะ snap ไม่เกินเกณฑ์ที่กำหนดจาก training; สถานะ matched / ambiguous / unmatched / parallel-road / grade-separated; ห้าม snap ถนนใกล้สุดแบบไม่มีเงื่อนไข; reconcile จำนวนทุกสถานะ
- ทั้งหมดนี้ **BLOCKED / NOT VERIFIED** ในรอบนี้เพราะไม่มี geometry ที่ตรวจ hash

## 7. Feature readiness

| feature_group | status | geographic_resolution | reason |
|---|---|---|---|
| calendar_time | allow | national / date | known before the target window |
| province_context | allow_context_only | province | coarse context; does not give location precision |
| road_segment_attributes | pending | segment | needs a hash-verified road dataset |
| segment_ids_and_length | pending | segment | no stable IDs without a road dataset |
| traffic_station_to_segment | pending | count station | station value is not traffic on every segment; no pseudo live congestion |
| province_aadt_v2 | allow_context_only | province | province AADT is not segment exposure and cannot be a per-location denominator |
| local_archived_forecast_weather | pending | grid/segment (not collected) | no local forecast archive with issue times has been collected |
| province_point_forecast_weather_v2 | allow_context_only | province point | province-point forecast, not local weather at a segment |
| historical_location_lags | blocked | segment/route | blocked until reporting latency is supported or an explicit research-only assumption is isolated |
| target_day_outcomes | blocked | event | explanatory outcomes of the target window, never predictors |
| crash_record_route_km_coordinates | blocked | event point | outcome-derived; usable only as a label-linkage key after snapping |
| description_recovery_history_layer | blocked | event | history display only, never a predictor |
| v2_training_eligibility | blocked | province-day | outcome-derived label policy, not operational observation coverage |

## 8. Blockers

- point_in_province: PENDING_NOT_VERIFIED (no hash-verified province_polygons dataset in the local registry)
- road_snapping: PENDING_NOT_VERIFIED (no hash-verified road_network dataset in the local registry)
- road_universe_denominator: PENDING_NOT_VERIFIED (no hash-verified road_network dataset in the local registry)
- stable_segment_ids: PENDING_NOT_VERIFIED (no hash-verified road_network dataset in the local registry)
- route_corridor_intersection: PENDING_NOT_VERIFIED (no hash-verified road_network dataset in the local registry)
- zero labels for any location unit: NOT ESTABLISHED (no verified road universe or reporting coverage)
- coordinate datum/CRS: NOT DOCUMENTED in source metadata (WGS84 not verified)
- reporting latency for historical lags: NOT VERIFIED (lags blocked)
- local archived forecast weather with issue times: NOT COLLECTED
- traffic station-to-segment linkage: NOT POSSIBLE without road geometry
- projected CRS / H3 grid: pyproj/h3 not installed in .venv; no metric grid built

## 9. ข้อเสนอ protocol ถัดไป (PROPOSED — Codex ต้องตรวจและล็อกก่อน)

- **ต้องเก็บ geometry ก่อนทำโมเดลระดับถนน: ใช่** ระหว่างนี้ grid/H3 ทำได้เฉพาะเป็น area-level experiment หลังอนุมัติ pyproj/h3 และเลือก CRS
- หน่วยที่ควรทดสอบ: segment 0.5/1/2 km × วัน และ × 6 ชม. (เลือกจาก support ใน training เท่านั้น); 7 วันเป็น target แยกที่ไม่อ้างความเสี่ยงรายชั่วโมง
- Folds: expanding chronological ภายใน 2021–2023; 2024/2025 คง seen diagnostic; spatial group holdout + buffer ที่กำหนดจาก training
- Baselines: zero, train-only global/road-type mean, smoothed segment/time mean + fallback; Poisson GLM / RF Poisson / HGB Poisson ประเมินใหม่ ไม่ถือว่า HGB ชนะ
- Alert layer: ระดับเฝ้าระวังแบบ relative ของ expected recorded count (cutoff จาก training/OOF ภายหลัง); สีเทา missing/out-of-coverage มาก่อนเสมอ; severity และ personal probability แยก; ไม่มีตัวเลขความแม่นยำ/ความน่าจะเป็นในรายงานนี้

## 10. ทำซ้ำได้อย่างไร

- `.venv/bin/python backend/scripts/run_spatial_readiness.py --output-dir backend/rerun-spatial-<UTC>` (ไม่ใช้ network, ไม่เขียนทับรอบเดิม)
- `.venv/bin/python -m pytest backend/tests/test_spatial_readiness_notebook.py -q`
- protected inputs เปลี่ยนระหว่างรัน: 0 ไฟล์

## ยังไม่ได้ยืนยัน (NOT VERIFIED)

- road geometry / road universe / stable segment IDs
- point-in-province
- road snapping and ambiguity handling
- true coordinate accuracy and datum
- route-code / KM validity against a road
- reporting completeness and zero labels
- any spatial model quality, calibration or colour thresholds
