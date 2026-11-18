# รายงานเก็บ geometry ถนนทางการ (notebook 17, V4 national envelope)

**สถานะ: COMPLETE (ครบทุกแหล่งในกรอบ query)**

- config: spatial_road_sources_v4.0 | แหล่ง (3): doh_highway, drr_rural, exat_expressway
- โหมด: online | cache: /Users/earthnaja/Documents/GitHub/Work - Earth/Project Work/Source Code/RoadAware/backend/rerun-road-national-001/data/v4/road_collection/raw
- กรอบที่ลงทะเบียนไว้ก่อน: EPSG4326 [97.3, 5.5, 105.7, 20.5] (esriSpatialRelIntersects) เป็นกรอบนำร่องเก็บ geometry **ไม่ใช่เส้นทางที่คำนวณ** และไม่ครอบคลุม 6 จังหวัดทั้งหมด
- full snapshot = feature ทั้งหมดที่ query กรอบนี้คืน (รวมถนนที่ไม่เคยมีเหตุ) ไม่ใช่ถนนทั้งประเทศ; เก็บ section เต็มตามที่คืนมา ส่วนที่ตัดตามกรอบเป็น derivative แยก
- ความครอบคลุมของแหล่งถนน (ชั้นข้อมูลถนนทางการหนึ่งชั้นต่อหน่วยงาน DOH/DRR/EXAT) **ไม่ใช่** ความครบของรายงานอุบัติเหตุ ไม่ใช่ปริมาณการใช้ถนน (exposure) และไม่ใช่ความน่าจะเป็นของเหตุ
- จำนวนระดับประเทศ/นำร่องที่ manager สังเกตไว้เป็นบริบทเท่านั้น ไม่ใช่ค่าคาดหวัง (ค่าว่าง = manager ไม่ได้ query เช่น จำนวน EXAT ระดับประเทศ)

## จำนวน feature และการกระทบยอด object ID

| source_id | status | count_before | ids_before | pages_planned | pages_present | features_returned | unique_oid | count_after | inventory_stable | geometry_bytes | captured_first_utc | captured_last_utc | context_pilot_count_manager | context_national_count_manager |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| doh_highway | complete | 3044 | 3044 | 153 | 153 | 3044 | 3044 | 3044 | True | 142515115 | 2026-11-18T15:27:16.218046+00:00 | 2026-11-18T15:27:52.592494+00:00 | 599 | 3044 |
| drr_rural | complete | 3700 | 3700 | 185 | 185 | 3700 | 3700 | 3700 | True | 46134512 | 2026-11-18T15:27:54.639668+00:00 | 2026-11-18T15:30:06.096236+00:00 | 547 | 3700 |
| exat_expressway | complete | 8 | 8 | 1 | 1 | 8 | 8 | 8 | True | 3434022 | 2026-11-18T15:30:06.914045+00:00 | 2026-11-18T15:30:08.497131+00:00 | 8 |  |

ตรวจ: count = จำนวน ID (predicate เดียวกัน), ทุก batch คืน ID ครบตามที่ขอ ไม่มี ID ซ้ำ/เกิน, ไม่มี exceededTransferLimit, ทุกหน้า spatialReference 4326, count/IDs หลังดาวน์โหลดตรงกับก่อนดาวน์โหลด; object ID คือ objectIdField ของแต่ละ layer (EXAT ใช้ objectid_1 ไม่ใช่ objectid)

## ปัญหาที่พบ

_(ไม่มีข้อมูล)_

## คุณภาพ geometry (flag เท่านั้น ไม่ซ่อม ไม่ลบ ไม่ simplify)

| source_id | features | geojson_derivative_ok | geom_missing | curve_geometry | empty_or_short_part | nonfinite_coord | extra_dims | lon_out_of_range | lat_out_of_range | latlon_swap_suspect | outside_thailand_bbox | bbox_disjoint_envelope | clip_empty | features_with_dup_consecutive_vertices | multipart | shapely_invalid | not_simple | sections_with_length | total_full_km | total_clipped_km | median_full_m | p10_full_m | p90_full_m | max_full_m |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| doh_highway | 3044 | 3044 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 14 | 3044 | 5.238e+04 | 5.238e+04 | 1.38e+04 | 855.2 | 3.718e+04 | 1.27e+05 |
| drr_rural | 3700 | 3700 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 35 | 3700 | 5.141e+04 | 5.141e+04 | 1.162e+04 | 4245 | 2.604e+04 | 8.669e+04 |
| exat_expressway | 8 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 4 | 8 | 701.4 | 701.4 | 8.744e+04 | 4.085e+04 | 1.314e+05 | 1.486e+05 |

ความยาวคำนวณแบบ geodesic บน WGS84 (Vincenty, stdlib) ไม่ใช้ระยะ degree เป็นเมตร; pyproj 3.6.1 Geod.line_length on 6752 sections: max relative difference 1.61e-07

## section ทางการ เทียบ segment 0.5/1/2 กม. ที่เสนอ

section ของ DOH/DRR/EXAT เป็นช่วงหยาบตามระบบงานของหน่วยงาน ไม่ใช่ segment มาตรฐานของโมเดล ตารางนี้แสดงสัดส่วนเท่านั้น **ยังไม่ได้ตัด segment**

| source_id | proposed_segment_km | sections_with_length | share_sections_shorter | share_sections_longer |
|---|---|---|---|---|
| doh_highway | 0.5 | 3044 | 0.0696 | 0.9304 |
| doh_highway | 1 | 3044 | 0.1127 | 0.8873 |
| doh_highway | 2 | 3044 | 0.1623 | 0.8377 |
| drr_rural | 0.5 | 3700 | 0.0038 | 0.9962 |
| drr_rural | 1 | 3700 | 0.0122 | 0.9878 |
| drr_rural | 2 | 3700 | 0.0319 | 0.9681 |
| exat_expressway | 0.5 | 8 | 0 | 1 |
| exat_expressway | 1 | 8 | 0 | 1 |
| exat_expressway | 2 | 8 | 0 | 1 |

## หน่วยของ attribute (สมมติฐาน รอยืนยันจากเอกสารทางการ)

EXAT ไม่มี attribute กม./ความยาวที่กำหนดใน config (SHAPE__Length เป็นหน่วย degree ไม่ใช้เป็นเมตร)

| source_id | quantity | field | n_compared | share_in_band_m | median_ratio_m | share_in_band_km | median_ratio_km | hypothesis | status |
|---|---|---|---|---|---|---|---|---|---|
| doh_highway | length attribute | length | 3023 | 0 | 0.001 | 0.9742 | 1 | consistent_with_km | hypothesis_pending_official_confirmation |
| doh_highway | abs(km_end - km_start) | km_end - km_start | 3044 | 0.9744 | 1 | 0 | 1001 | consistent_with_m | hypothesis_pending_official_confirmation |
| doh_highway | geometry length field | SHAPE__Length | 0 |  |  |  |  | units per layer geometryProperties: esriDecimalDegrees | not_metres_never_used_as_length |
| drr_rural | length attribute | length_gps | 3540 | 0.0003 | 0.001 | 0.9184 | 1 | consistent_with_km | hypothesis_pending_official_confirmation |
| drr_rural | length attribute | length_drr | 3700 | 0 | 0.001 | 0.9654 | 0.9978 | consistent_with_km | hypothesis_pending_official_confirmation |
| drr_rural | abs(km_end - km_start) | km_end - km_start | 3700 | 0.9654 | 0.9978 | 0 | 997.8 | consistent_with_m | hypothesis_pending_official_confirmation |
| exat_expressway | geometry length field | SHAPE__Length | 0 |  |  |  |  | units per layer geometryProperties: esriDecimalDegrees | not_metres_never_used_as_length |

## vintage / licence metadata

| source_id | item | field | n_present | min | max | note |
|---|---|---|---|---|---|---|
| doh_highway | snapshot capture (UTC) |  |  | 2026-11-18T15:27:16.218046+00:00 | 2026-11-18T15:27:52.592494+00:00 | current service state; not a 2021-2025 historical topology |
| doh_highway | layer lastEditDate | editingInfo |  |  |  | None = not published by the service |
| doh_highway | service/layer version | currentVersion |  | 11.5 |  | ArcGIS server version, not a data vintage |
| doh_highway | licence |  |  |  |  | pending: licence text of the MOT catalog resource was not captured; confirm on the catalog resource page before redistribution / copyrightText: '' |
| drr_rural | snapshot capture (UTC) |  |  | 2026-11-18T15:27:54.639668+00:00 | 2026-11-18T15:30:06.096236+00:00 | current service state; not a 2021-2025 historical topology |
| drr_rural | layer lastEditDate | editingInfo |  |  |  | None = not published by the service |
| drr_rural | service/layer version | currentVersion |  | 10.11 |  | ArcGIS server version, not a data vintage |
| drr_rural | licence |  |  |  |  | pending: licence text of the MOT catalog resource was not captured; confirm on the catalog resource page before redistribution / copyrightText: '' |
| drr_rural | date attribute | updated_date | 3700 | 2025-01-22 | 2025-04-18 | meaning of the date (survey/update) per official documentation: pending |
| drr_rural | date attribute | survey_date | 0 |  |  | meaning of the date (survey/update) per official documentation: pending |
| drr_rural | year attribute | budget_year | 3700 | 2569 | 2569 | calendar (BE/CE) and meaning pending confirmation |
| exat_expressway | snapshot capture (UTC) |  |  | 2026-11-18T15:30:06.914045+00:00 | 2026-11-18T15:30:08.497131+00:00 | current service state; not a 2021-2025 historical topology |
| exat_expressway | layer lastEditDate | editingInfo |  |  |  | None = not published by the service |
| exat_expressway | service/layer version | currentVersion |  | 11.5 |  | ArcGIS server version, not a data vintage |
| exat_expressway | licence |  |  |  |  | pending: licence text of the MOT catalog resource was not captured; confirm on the catalog resource page before redistribution / copyrightText: '' |

## ความครบของ attribute

| source_id | field | esri_type | n_features | n_null | n_blank_string | n_numeric_zero | share_missing |
|---|---|---|---|---|---|---|---|
| doh_highway | objectid | esriFieldTypeOID | 3044 | 0 | 0 | 0 | 0 |
| doh_highway | road_code | esriFieldTypeString | 3044 | 0 | 0 | 0 | 0 |
| doh_highway | road_name | esriFieldTypeString | 3044 | 0 | 0 | 0 | 0 |
| doh_highway | section_co | esriFieldTypeString | 3044 | 0 | 0 | 0 | 0 |
| doh_highway | section_na | esriFieldTypeString | 3044 | 0 | 0 | 0 | 0 |
| doh_highway | km_start | esriFieldTypeInteger | 3044 | 0 | 0 | 1463 | 0 |
| doh_highway | km_end | esriFieldTypeInteger | 3044 | 0 | 0 | 0 | 0 |
| doh_highway | length | esriFieldTypeDouble | 3044 | 0 | 0 | 21 | 0 |
| doh_highway | SHAPE__Length | esriFieldTypeDouble | 3044 | 0 | 0 | 0 | 0 |
| drr_rural | OBJECTID | esriFieldTypeOID | 3700 | 0 | 0 | 0 | 0 |
| drr_rural | direction | esriFieldTypeString | 3700 | 0 | 35 | 0 | 0.0095 |
| drr_rural | status | esriFieldTypeString | 3700 | 0 | 0 | 0 | 0 |
| drr_rural | updated_date | esriFieldTypeDate | 3700 | 0 | 0 | 0 | 0 |
| drr_rural | route_name | esriFieldTypeString | 3700 | 0 | 0 | 0 | 0 |
| drr_rural | length_gps | esriFieldTypeDouble | 3700 | 0 | 0 | 160 | 0 |
| drr_rural | length_drr | esriFieldTypeDouble | 3700 | 0 | 0 | 0 | 0 |
| drr_rural | lane_width | esriFieldTypeDouble | 3700 | 0 | 0 | 895 | 0 |
| drr_rural | user_name | esriFieldTypeString | 3700 | 0 | 0 | 0 | 0 |
| drr_rural | road_code | esriFieldTypeString | 3700 | 0 | 0 | 0 | 0 |
| drr_rural | link_id | esriFieldTypeInteger | 3700 | 0 | 0 | 0 | 0 |
| drr_rural | sublink_id | esriFieldTypeInteger | 3700 | 0 | 0 | 3683 | 0 |
| drr_rural | budget_year | esriFieldTypeInteger | 3700 | 0 | 0 | 0 | 0 |
| drr_rural | gid | esriFieldTypeInteger | 3700 | 0 | 0 | 0 | 0 |
| drr_rural | km_start | esriFieldTypeInteger | 3700 | 0 | 0 | 3627 | 0 |
| drr_rural | km_end | esriFieldTypeInteger | 3700 | 0 | 0 | 0 | 0 |
| drr_rural | sublink_revision | esriFieldTypeInteger | 3700 | 23 | 0 | 2148 | 0.0062 |
| drr_rural | lane_count | esriFieldTypeInteger | 3700 | 6 | 0 | 0 | 0.0016 |
| drr_rural | link_revision | esriFieldTypeInteger | 3700 | 0 | 0 | 2122 | 0 |
| drr_rural | survey_date | esriFieldTypeDate | 3700 | 3700 | 0 | 0 | 1 |
| exat_expressway | objectid_1 | esriFieldTypeOID | 8 | 0 | 0 | 0 | 0 |
| exat_expressway | objectid | esriFieldTypeInteger | 8 | 0 | 0 | 0 | 0 |
| exat_expressway | route | esriFieldTypeString | 8 | 0 | 0 | 0 | 0 |
| exat_expressway | centerline | esriFieldTypeString | 8 | 0 | 0 | 0 | 0 |
| exat_expressway | SHAPE__Length | esriFieldTypeDouble | 8 | 0 | 0 | 0 | 0 |

## ตาราง readiness

| check | source_id | status | evidence |
|---|---|---|---|
| preregistered_envelope | all | info | EPSG4326 [97.3, 5.5, 105.7, 20.5] esriSpatialRelIntersects; geometry pilot only, not a routed path, not all six candidate provinces |
| collection_complete | doh_highway | pass | complete |
| count_ids_pages_reconciled | doh_highway | pass | count 3044, IDs 3044, pages 153/153, unique features 3044 |
| inventory_stable_pre_post | doh_highway | pass | count before 3044, after 3044; non-transactional caveat remains |
| crs_outsr_4326 | doh_highway | pass | every page spatialReference must be 4326; layer wkid 4326 |
| geometry_nonempty_finite_lines | doh_highway | pass | 0 features flagged (kept in raw, excluded only from the GeoJSON derivative); derivative ok 3044 |
| lonlat_order_and_bounds | doh_highway | pass | swap suspects 0, outside Thailand box 0 |
| envelope_predicate_consistency | doh_highway | pass | bbox disjoint 0, empty clip 0 |
| geodesic_lengths | doh_highway | pass | WGS84 Vincenty (stdlib) on 3044 sections; pyproj 3.6.1 Geod.line_length on 6752 sections: max relative difference 1.61e-07 |
| topology_simple_valid | doh_highway | review | not simple 14, invalid 0 (flag only, no repair) |
| units: length | doh_highway | pending | consistent_with_km (hypothesis_pending_official_confirmation) |
| units: km_end - km_start | doh_highway | pending | consistent_with_m (hypothesis_pending_official_confirmation) |
| units: SHAPE__Length | doh_highway | pending | units per layer geometryProperties: esriDecimalDegrees (not_metres_never_used_as_length) |
| vintage_historical_topology | doh_highway | pending | current snapshot only; does not prove the 2021-2025 road network |
| licence | doh_highway | pending | pending: licence text of the MOT catalog resource was not captured; confirm on the catalog resource page before redistribution |
| collection_complete | drr_rural | pass | complete |
| count_ids_pages_reconciled | drr_rural | pass | count 3700, IDs 3700, pages 185/185, unique features 3700 |
| inventory_stable_pre_post | drr_rural | pass | count before 3700, after 3700; non-transactional caveat remains |
| crs_outsr_4326 | drr_rural | pass | every page spatialReference must be 4326; layer wkid 4326 |
| geometry_nonempty_finite_lines | drr_rural | pass | 0 features flagged (kept in raw, excluded only from the GeoJSON derivative); derivative ok 3700 |
| lonlat_order_and_bounds | drr_rural | pass | swap suspects 0, outside Thailand box 0 |
| envelope_predicate_consistency | drr_rural | pass | bbox disjoint 0, empty clip 0 |
| geodesic_lengths | drr_rural | pass | WGS84 Vincenty (stdlib) on 3700 sections; pyproj 3.6.1 Geod.line_length on 6752 sections: max relative difference 1.61e-07 |
| topology_simple_valid | drr_rural | review | not simple 35, invalid 0 (flag only, no repair) |
| units: length_gps | drr_rural | pending | consistent_with_km (hypothesis_pending_official_confirmation) |
| units: length_drr | drr_rural | pending | consistent_with_km (hypothesis_pending_official_confirmation) |
| units: km_end - km_start | drr_rural | pending | consistent_with_m (hypothesis_pending_official_confirmation) |
| vintage_historical_topology | drr_rural | pending | current snapshot only; does not prove the 2021-2025 road network |
| licence | drr_rural | pending | pending: licence text of the MOT catalog resource was not captured; confirm on the catalog resource page before redistribution |
| collection_complete | exat_expressway | pass | complete |
| count_ids_pages_reconciled | exat_expressway | pass | count 8, IDs 8, pages 1/1, unique features 8 |
| inventory_stable_pre_post | exat_expressway | pass | count before 8, after 8; non-transactional caveat remains |
| crs_outsr_4326 | exat_expressway | pass | every page spatialReference must be 4326; layer wkid 4326 |
| geometry_nonempty_finite_lines | exat_expressway | pass | 0 features flagged (kept in raw, excluded only from the GeoJSON derivative); derivative ok 8 |
| lonlat_order_and_bounds | exat_expressway | pass | swap suspects 0, outside Thailand box 0 |
| envelope_predicate_consistency | exat_expressway | pass | bbox disjoint 0, empty clip 0 |
| geodesic_lengths | exat_expressway | pass | WGS84 Vincenty (stdlib) on 8 sections; pyproj 3.6.1 Geod.line_length on 6752 sections: max relative difference 1.61e-07 |
| topology_simple_valid | exat_expressway | review | not simple 4, invalid 0 (flag only, no repair) |
| units: SHAPE__Length | exat_expressway | pending | units per layer geometryProperties: esriDecimalDegrees (not_metres_never_used_as_length) |
| vintage_historical_topology | exat_expressway | pending | current snapshot only; does not prove the 2021-2025 road network |
| licence | exat_expressway | pending | pending: licence text of the MOT catalog resource was not captured; confirm on the catalog resource page before redistribution |
| model_segments_0.5_1_2km | all | pending | official records are coarse sections; segmentation not built in this task |
| road_snapping_zero_labels_completeness | all | not_in_scope | no snapping, labels, accident-report completeness or route-level skill |
| routed_spu_khaoyai_path | all | not_in_scope | no route computed; the envelope is not a route |

## ข้อจำกัดที่ต้องอ่านคู่กัน

- ArcGIS REST queries are not transactional: count and IDs are re-queried after the download and must match, but an edit to the attributes or geometry of an existing OID between requests cannot be excluded
- snapshot = current service state at capture time; it does not prove the 2021-2025 road topology
- full official sections intersecting the envelope are kept as returned; the envelope-clipped geometry is a separate derivative
- national/pilot counts observed by the manager are context only, never expected values
- source coverage (one official road layer per configured agency, e.g. DOH/DRR/EXAT) is not accident-report completeness, road exposure or event probability
- official records are coarse road sections, not the proposed 0.5/1/2 km model segments (not built here)
- no road snapping, zero labels, accident-report completeness, model, risk score or route-level skill is evaluated; no SPU-Khao Yai route is computed

## Runbook

- VS Code: เลือก kernel .venv แล้ว Run All (offline ต้องมี cache ที่ตรวจครบของ config นี้ที่ backend/data/v4/road_collection)
- Codex online: .venv/bin/python backend/scripts/run_spatial_road_collection.py --online --output-dir backend/rerun-road-<UTC>
- Codex offline ตรวจซ้ำ: .venv/bin/python backend/scripts/run_spatial_road_collection.py --output-dir backend/rerun-road-<UTC2> --cache-from backend/rerun-road-<UTC>/data/v4/road_collection --expect-manifest backend/rerun-road-<UTC>/reports/v4/road_collection/road_collection_manifest.json
- raw/cache/GeoJSON อยู่ใต้ data/v4/road_collection (gitignored) ส่วน reports/v4/road_collection เก็บเฉพาะตารางสรุป รูป และ manifest
- cache ต้องมีชุดแหล่งตรงกับ config (doh_highway, drr_rural, exat_expressway); cache ของ config รุ่นก่อนที่มีแหล่งไม่ครบจะถูกปฏิเสธ ห้ามนำมาผสม
- ทุกครั้งใช้ output root ใหม่; การเปลี่ยนกรอบหรือ budget ต้องบันทึกใน config ก่อนดูผลโมเดลใด ๆ

## ขั้นต่อไป

- doh_highway: none: complete for the preregistered envelope
- drr_rural: none: complete for the preregistered envelope
- exat_expressway: none: complete for the preregistered envelope
