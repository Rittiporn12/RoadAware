# รายงานเก็บ geometry ถนนทางการ (notebook 17, V3 pilot envelope)

**สถานะ: COMPLETE (ครบทุกแหล่งในกรอบ query)**

- config: spatial_road_sources_v3.1 | แหล่ง (3): doh_highway, drr_rural, exat_expressway
- โหมด: offline | cache: /Users/earthnaja/Documents/GitHub/Work - Earth/Project Work/Source Code/RoadAware/backend/rerun-road-013a-online-001/data/v3/road_collection_v3_1/raw
- กรอบที่ลงทะเบียนไว้ก่อน: EPSG4326 [100.2, 13.5, 102.0, 15.3] (esriSpatialRelIntersects) เป็นกรอบนำร่องเก็บ geometry **ไม่ใช่เส้นทางที่คำนวณ** และไม่ครอบคลุม 6 จังหวัดทั้งหมด
- full snapshot = feature ทั้งหมดที่ query กรอบนี้คืน (รวมถนนที่ไม่เคยมีเหตุ) ไม่ใช่ถนนทั้งประเทศ; เก็บ section เต็มตามที่คืนมา ส่วนที่ตัดตามกรอบเป็น derivative แยก
- ความครอบคลุมของแหล่งถนน (ชั้นข้อมูลถนนทางการหนึ่งชั้นต่อหน่วยงาน DOH/DRR/EXAT) **ไม่ใช่** ความครบของรายงานอุบัติเหตุ ไม่ใช่ปริมาณการใช้ถนน (exposure) และไม่ใช่ความน่าจะเป็นของเหตุ
- จำนวนระดับประเทศ/นำร่องที่ manager สังเกตไว้เป็นบริบทเท่านั้น ไม่ใช่ค่าคาดหวัง (ค่าว่าง = manager ไม่ได้ query เช่น จำนวน EXAT ระดับประเทศ)

## จำนวน feature และการกระทบยอด object ID

| source_id | status | count_before | ids_before | pages_planned | pages_present | features_returned | unique_oid | count_after | inventory_stable | geometry_bytes | captured_first_utc | captured_last_utc | context_pilot_count_manager | context_national_count_manager |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| doh_highway | complete | 599 | 599 | 30 | 30 | 599 | 599 | 599 | True | 36369962 | 2026-11-11T02:29:12.170187+00:00 | 2026-11-11T02:29:19.966190+00:00 | 599 | 3044 |
| drr_rural | complete | 547 | 547 | 28 | 28 | 547 | 547 | 547 | True | 4733323 | 2026-11-11T02:29:20.629203+00:00 | 2026-11-11T02:29:29.437360+00:00 | 547 | 3700 |
| exat_expressway | complete | 8 | 8 | 1 | 1 | 8 | 8 | 8 | True | 3434022 | 2026-11-11T02:29:29.476780+00:00 | 2026-11-11T02:29:30.342523+00:00 | 8 |  |

ตรวจ: count = จำนวน ID (predicate เดียวกัน), ทุก batch คืน ID ครบตามที่ขอ ไม่มี ID ซ้ำ/เกิน, ไม่มี exceededTransferLimit, ทุกหน้า spatialReference 4326, count/IDs หลังดาวน์โหลดตรงกับก่อนดาวน์โหลด; object ID คือ objectIdField ของแต่ละ layer (EXAT ใช้ objectid_1 ไม่ใช่ objectid)

## ปัญหาที่พบ

_(ไม่มีข้อมูล)_

## คุณภาพ geometry (flag เท่านั้น ไม่ซ่อม ไม่ลบ ไม่ simplify)

| source_id | features | geojson_derivative_ok | geom_missing | curve_geometry | empty_or_short_part | nonfinite_coord | extra_dims | lon_out_of_range | lat_out_of_range | latlon_swap_suspect | outside_thailand_bbox | bbox_disjoint_envelope | clip_empty | features_with_dup_consecutive_vertices | multipart | shapely_invalid | not_simple | sections_with_length | total_full_km | total_clipped_km | median_full_m | p10_full_m | p90_full_m | max_full_m |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| doh_highway | 599 | 599 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 599 | 6685 | 5957 | 9073 | 490.1 | 2.51e+04 | 8.489e+04 |
| drr_rural | 547 | 547 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 547 | 6389 | 5987 | 1.002e+04 | 3283 | 2.158e+04 | 7.463e+04 |
| exat_expressway | 8 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 4 | 8 | 701.4 | 689.5 | 8.744e+04 | 4.085e+04 | 1.314e+05 | 1.486e+05 |

ความยาวคำนวณแบบ geodesic บน WGS84 (Vincenty, stdlib) ไม่ใช้ระยะ degree เป็นเมตร; pyproj 3.6.1 Geod.line_length on 1154 sections: max relative difference 1.61e-07

## section ทางการ เทียบ segment 0.5/1/2 กม. ที่เสนอ

section ของ DOH/DRR/EXAT เป็นช่วงหยาบตามระบบงานของหน่วยงาน ไม่ใช่ segment มาตรฐานของโมเดล ตารางนี้แสดงสัดส่วนเท่านั้น **ยังไม่ได้ตัด segment**

| source_id | proposed_segment_km | sections_with_length | share_sections_shorter | share_sections_longer |
|---|---|---|---|---|
| doh_highway | 0.5 | 599 | 0.1052 | 0.8948 |
| doh_highway | 1 | 599 | 0.172 | 0.828 |
| doh_highway | 2 | 599 | 0.2387 | 0.7613 |
| drr_rural | 0.5 | 547 | 0.0091 | 0.9909 |
| drr_rural | 1 | 547 | 0.0274 | 0.9726 |
| drr_rural | 2 | 547 | 0.0494 | 0.9506 |
| exat_expressway | 0.5 | 8 | 0 | 1 |
| exat_expressway | 1 | 8 | 0 | 1 |
| exat_expressway | 2 | 8 | 0 | 1 |

## หน่วยของ attribute (สมมติฐาน รอยืนยันจากเอกสารทางการ)

EXAT ไม่มี attribute กม./ความยาวที่กำหนดใน config (SHAPE__Length เป็นหน่วย degree ไม่ใช้เป็นเมตร)

| source_id | quantity | field | n_compared | share_in_band_m | median_ratio_m | share_in_band_km | median_ratio_km | hypothesis | status |
|---|---|---|---|---|---|---|---|---|---|
| doh_highway | length attribute | length | 585 | 0 | 0.001 | 0.9744 | 1 | consistent_with_km | hypothesis_pending_official_confirmation |
| doh_highway | abs(km_end - km_start) | km_end - km_start | 599 | 0.975 | 1 | 0 | 1000 | consistent_with_m | hypothesis_pending_official_confirmation |
| doh_highway | geometry length field | SHAPE__Length | 0 |  |  |  |  | units per layer geometryProperties: esriDecimalDegrees | not_metres_never_used_as_length |
| drr_rural | length attribute | length_gps | 514 | 0.0019 | 0.001 | 0.9066 | 0.9999 | consistent_with_km | hypothesis_pending_official_confirmation |
| drr_rural | length attribute | length_drr | 547 | 0 | 0.001 | 0.9744 | 0.9967 | consistent_with_km | hypothesis_pending_official_confirmation |
| drr_rural | abs(km_end - km_start) | km_end - km_start | 547 | 0.9744 | 0.9967 | 0 | 996.7 | consistent_with_m | hypothesis_pending_official_confirmation |
| exat_expressway | geometry length field | SHAPE__Length | 0 |  |  |  |  | units per layer geometryProperties: esriDecimalDegrees | not_metres_never_used_as_length |

## vintage / licence metadata

| source_id | item | field | n_present | min | max | note |
|---|---|---|---|---|---|---|
| doh_highway | snapshot capture (UTC) |  |  | 2026-11-11T02:29:12.170187+00:00 | 2026-11-11T02:29:19.966190+00:00 | current service state; not a 2021-2025 historical topology |
| doh_highway | layer lastEditDate | editingInfo |  |  |  | None = not published by the service |
| doh_highway | service/layer version | currentVersion |  | 11.5 |  | ArcGIS server version, not a data vintage |
| doh_highway | licence |  |  |  |  | pending: licence text of the MOT catalog resource was not captured; confirm on the catalog resource page before redistribution / copyrightText: '' |
| drr_rural | snapshot capture (UTC) |  |  | 2026-11-11T02:29:20.629203+00:00 | 2026-11-11T02:29:29.437360+00:00 | current service state; not a 2021-2025 historical topology |
| drr_rural | layer lastEditDate | editingInfo |  |  |  | None = not published by the service |
| drr_rural | service/layer version | currentVersion |  | 10.11 |  | ArcGIS server version, not a data vintage |
| drr_rural | licence |  |  |  |  | pending: licence text of the MOT catalog resource was not captured; confirm on the catalog resource page before redistribution / copyrightText: '' |
| drr_rural | date attribute | updated_date | 547 | 2025-01-22 | 2025-04-18 | meaning of the date (survey/update) per official documentation: pending |
| drr_rural | date attribute | survey_date | 0 |  |  | meaning of the date (survey/update) per official documentation: pending |
| drr_rural | year attribute | budget_year | 547 | 2569 | 2569 | calendar (BE/CE) and meaning pending confirmation |
| exat_expressway | snapshot capture (UTC) |  |  | 2026-11-11T02:29:29.476780+00:00 | 2026-11-11T02:29:30.342523+00:00 | current service state; not a 2021-2025 historical topology |
| exat_expressway | layer lastEditDate | editingInfo |  |  |  | None = not published by the service |
| exat_expressway | service/layer version | currentVersion |  | 11.5 |  | ArcGIS server version, not a data vintage |
| exat_expressway | licence |  |  |  |  | pending: licence text of the MOT catalog resource was not captured; confirm on the catalog resource page before redistribution / copyrightText: '' |

## ความครบของ attribute

| source_id | field | esri_type | n_features | n_null | n_blank_string | n_numeric_zero | share_missing |
|---|---|---|---|---|---|---|---|
| doh_highway | objectid | esriFieldTypeOID | 599 | 0 | 0 | 0 | 0 |
| doh_highway | road_code | esriFieldTypeString | 599 | 0 | 0 | 0 | 0 |
| doh_highway | road_name | esriFieldTypeString | 599 | 0 | 0 | 0 | 0 |
| doh_highway | section_co | esriFieldTypeString | 599 | 0 | 0 | 0 | 0 |
| doh_highway | section_na | esriFieldTypeString | 599 | 0 | 0 | 0 | 0 |
| doh_highway | km_start | esriFieldTypeInteger | 599 | 0 | 0 | 211 | 0 |
| doh_highway | km_end | esriFieldTypeInteger | 599 | 0 | 0 | 0 | 0 |
| doh_highway | length | esriFieldTypeDouble | 599 | 0 | 0 | 14 | 0 |
| doh_highway | SHAPE__Length | esriFieldTypeDouble | 599 | 0 | 0 | 0 | 0 |
| drr_rural | OBJECTID | esriFieldTypeOID | 547 | 0 | 0 | 0 | 0 |
| drr_rural | direction | esriFieldTypeString | 547 | 0 | 4 | 0 | 0.0073 |
| drr_rural | status | esriFieldTypeString | 547 | 0 | 0 | 0 | 0 |
| drr_rural | updated_date | esriFieldTypeDate | 547 | 0 | 0 | 0 | 0 |
| drr_rural | route_name | esriFieldTypeString | 547 | 0 | 0 | 0 | 0 |
| drr_rural | length_gps | esriFieldTypeDouble | 547 | 0 | 0 | 33 | 0 |
| drr_rural | length_drr | esriFieldTypeDouble | 547 | 0 | 0 | 0 | 0 |
| drr_rural | lane_width | esriFieldTypeDouble | 547 | 0 | 0 | 96 | 0 |
| drr_rural | user_name | esriFieldTypeString | 547 | 0 | 0 | 0 | 0 |
| drr_rural | road_code | esriFieldTypeString | 547 | 0 | 0 | 0 | 0 |
| drr_rural | link_id | esriFieldTypeInteger | 547 | 0 | 0 | 0 | 0 |
| drr_rural | sublink_id | esriFieldTypeInteger | 547 | 0 | 0 | 544 | 0 |
| drr_rural | budget_year | esriFieldTypeInteger | 547 | 0 | 0 | 0 | 0 |
| drr_rural | gid | esriFieldTypeInteger | 547 | 0 | 0 | 0 | 0 |
| drr_rural | km_start | esriFieldTypeInteger | 547 | 0 | 0 | 529 | 0 |
| drr_rural | km_end | esriFieldTypeInteger | 547 | 0 | 0 | 0 | 0 |
| drr_rural | sublink_revision | esriFieldTypeInteger | 547 | 23 | 0 | 284 | 0.042 |
| drr_rural | lane_count | esriFieldTypeInteger | 547 | 1 | 0 | 0 | 0.0018 |
| drr_rural | link_revision | esriFieldTypeInteger | 547 | 0 | 0 | 307 | 0 |
| drr_rural | survey_date | esriFieldTypeDate | 547 | 547 | 0 | 0 | 1 |
| exat_expressway | objectid_1 | esriFieldTypeOID | 8 | 0 | 0 | 0 | 0 |
| exat_expressway | objectid | esriFieldTypeInteger | 8 | 0 | 0 | 0 | 0 |
| exat_expressway | route | esriFieldTypeString | 8 | 0 | 0 | 0 | 0 |
| exat_expressway | centerline | esriFieldTypeString | 8 | 0 | 0 | 0 | 0 |
| exat_expressway | SHAPE__Length | esriFieldTypeDouble | 8 | 0 | 0 | 0 | 0 |

## ตาราง readiness

| check | source_id | status | evidence |
|---|---|---|---|
| preregistered_envelope | all | info | EPSG4326 [100.2, 13.5, 102.0, 15.3] esriSpatialRelIntersects; geometry pilot only, not a routed path, not all six candidate provinces |
| collection_complete | doh_highway | pass | complete |
| count_ids_pages_reconciled | doh_highway | pass | count 599, IDs 599, pages 30/30, unique features 599 |
| inventory_stable_pre_post | doh_highway | pass | count before 599, after 599; non-transactional caveat remains |
| crs_outsr_4326 | doh_highway | pass | every page spatialReference must be 4326; layer wkid 4326 |
| geometry_nonempty_finite_lines | doh_highway | pass | 0 features flagged (kept in raw, excluded only from the GeoJSON derivative); derivative ok 599 |
| lonlat_order_and_bounds | doh_highway | pass | swap suspects 0, outside Thailand box 0 |
| envelope_predicate_consistency | doh_highway | pass | bbox disjoint 0, empty clip 0 |
| geodesic_lengths | doh_highway | pass | WGS84 Vincenty (stdlib) on 599 sections; pyproj 3.6.1 Geod.line_length on 1154 sections: max relative difference 1.61e-07 |
| topology_simple_valid | doh_highway | review | not simple 2, invalid 0 (flag only, no repair) |
| units: length | doh_highway | pending | consistent_with_km (hypothesis_pending_official_confirmation) |
| units: km_end - km_start | doh_highway | pending | consistent_with_m (hypothesis_pending_official_confirmation) |
| units: SHAPE__Length | doh_highway | pending | units per layer geometryProperties: esriDecimalDegrees (not_metres_never_used_as_length) |
| vintage_historical_topology | doh_highway | pending | current snapshot only; does not prove the 2021-2025 road network |
| licence | doh_highway | pending | pending: licence text of the MOT catalog resource was not captured; confirm on the catalog resource page before redistribution |
| collection_complete | drr_rural | pass | complete |
| count_ids_pages_reconciled | drr_rural | pass | count 547, IDs 547, pages 28/28, unique features 547 |
| inventory_stable_pre_post | drr_rural | pass | count before 547, after 547; non-transactional caveat remains |
| crs_outsr_4326 | drr_rural | pass | every page spatialReference must be 4326; layer wkid 4326 |
| geometry_nonempty_finite_lines | drr_rural | pass | 0 features flagged (kept in raw, excluded only from the GeoJSON derivative); derivative ok 547 |
| lonlat_order_and_bounds | drr_rural | pass | swap suspects 0, outside Thailand box 0 |
| envelope_predicate_consistency | drr_rural | pass | bbox disjoint 0, empty clip 0 |
| geodesic_lengths | drr_rural | pass | WGS84 Vincenty (stdlib) on 547 sections; pyproj 3.6.1 Geod.line_length on 1154 sections: max relative difference 1.61e-07 |
| topology_simple_valid | drr_rural | review | not simple 4, invalid 0 (flag only, no repair) |
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
| geodesic_lengths | exat_expressway | pass | WGS84 Vincenty (stdlib) on 8 sections; pyproj 3.6.1 Geod.line_length on 1154 sections: max relative difference 1.61e-07 |
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

- VS Code: เลือก kernel .venv แล้ว Run All (offline ต้องมี cache ที่ตรวจครบของ config นี้ที่ backend/data/v3/road_collection_v3_1)
- Codex online: .venv/bin/python backend/scripts/run_spatial_road_collection.py --online --output-dir backend/rerun-road-<UTC>
- Codex offline ตรวจซ้ำ: .venv/bin/python backend/scripts/run_spatial_road_collection.py --output-dir backend/rerun-road-<UTC2> --cache-from backend/rerun-road-<UTC>/data/v3/road_collection_v3_1 --expect-manifest backend/rerun-road-<UTC>/reports/v3/road_collection_v3_1/road_collection_manifest.json
- raw/cache/GeoJSON อยู่ใต้ data/v3/road_collection_v3_1 (gitignored) ส่วน reports/v3/road_collection_v3_1 เก็บเฉพาะตารางสรุป รูป และ manifest
- cache ต้องมีชุดแหล่งตรงกับ config (doh_highway, drr_rural, exat_expressway); cache ของ config รุ่นก่อนที่มีแหล่งไม่ครบจะถูกปฏิเสธ ห้ามนำมาผสม
- ทุกครั้งใช้ output root ใหม่; การเปลี่ยนกรอบหรือ budget ต้องบันทึกใน config ก่อนดูผลโมเดลใด ๆ

## ขั้นต่อไป

- doh_highway: none: complete for the preregistered envelope
- drr_rural: none: complete for the preregistered envelope
- exat_expressway: none: complete for the preregistered envelope
