# รายงานตรวจการเชื่อมโยงอุบัติเหตุกับถนนและคลัง segment (V3 notebook 18)

> **หลักฐานเชิงพรรณนาของการเชื่อมโยงข้อมูลเท่านั้น ไม่ใช่การพยากรณ์ ไม่ใช่ระดับความเสี่ยง** ไม่มีการ train โมเดล ไม่มี probability/threshold/สีเตือน

สถานะการตรวจรับอัตโนมัติ: **complete** (38/38 checks pass) · config spatial_linkage_v3.0 · snapshot rc31f3d87fc7

## 1. ขอบเขตและวันที่
envelope ที่ลงทะเบียนไว้ EPSG4326 [100.2, 13.5, 102.0, 15.3] (ไม่ใช่เส้นทาง SPU-เขาใหญ่ ไม่ครอบคลุม 6 จังหวัด ใช้เป็นตัวกรองขอบเขต ไม่ใช่การยืนยันว่าอยู่บนถนน)

| split | event_date | retained | pilot_in_envelope | outside_envelope | coord_not_usable | matched_50m | matched_with_segment_50m |
|---|---|---|---|---|---|---|---|
| all | 2021-01-01..2025-12-31 | 106308 | 31089 | 75219 | 0 | 28476 | 28353 |
| train | 2021-01-01..2023-12-30 | 60978 | 16910 | 44068 | 0 | 15808 | 15738 |
| seen_diagnostic | 2024-01-01..2025-12-31 | 45330 | 14179 | 31151 | 0 | 12668 | 12615 |

train = 2021-2023 · seen_diagnostic = 2024-2025 (ข้อมูลที่เคยเห็นแล้ว ใช้รายงาน linkage เท่านั้น ไม่ใช้เลือก resolution)

## 2. Input ที่ตรวจ hash แล้ว
| input | sha256 | rule | status |
|---|---|---|---|
| road_manifest | 6783d259ae91db2e2b684d0c3cd9ae376b70dfeb1af74fbe436e86f15e6fb465 | config pin | pass |
| road_review | 864eb24f2feed41d37935b29f17eef59778fbc362909c6f730cdd8b5b1121320 | config pin | pass |
| readiness_manifest | 0004b14460fef8af8a5de69f0b0d1711faf27c9acfeb897087ebaba03ad6e243 | config pin | pass |
| doh_highway_clipped.geojson | 05a7a1e95ac939f533ebea3daefe40b1394b8ae3289ffbac57ce7589c50a9f38 | config pin == road manifest derived_files | pass |
| doh_highway_full.geojson | a8d7ade7961d6b11723c5f1feaf3342ee0319e94d661600d06b9538fdb9bc16c | config pin == road manifest derived_files | pass |
| drr_rural_clipped.geojson | dcbb253a6a8273738e3ec8109a3f4571cdc3e0d2ec4c4fa5819dc0712a385187 | config pin == road manifest derived_files | pass |
| drr_rural_full.geojson | 1c30231ce2ae50fe3eeb856a51ca1dcbcf4aac68b9e4781d2628fa14fde4c941 | config pin == road manifest derived_files | pass |
| exat_expressway_clipped.geojson | 8a6acbc7d486706f34c467127f3e96a6b05797cd0410cae7b3b01bcd752fac2c | config pin == road manifest derived_files | pass |
| exat_expressway_full.geojson | 8e54d2e567356979727fc33ac4f101bfac188cbf53d07ef697ce2ccb7e3cb3e8 | config pin == road manifest derived_files | pass |
| feature_diagnostics.csv | f694d422b0c3bd31f04946d90b84405a29086cf57f4cfe56464615669a0472a7 | config pin == road manifest derived_files | pass |
| lineage | 78ded7939a327e5cbd45132e297b5a1bfbe76bef117ac3ac5da9b4a90352da2c | config pin == readiness manifest row_level_outputs_gitignored | pass |

## 3. พิกัด (ไม่ซ่อม)
พิกัดที่ swap/หาย/ไม่เป็นตัวเลข/นอกกรอบประเทศ ถูก flag ตามสถานะจาก notebook 16 และไม่ถูกแก้ ค่าความละเอียดต่ำ (ทศนิยม ≤ 3) หรือ lat==lon = ไม่เหมาะกับการกำหนดถนนแบบมั่นใจ

| dimension | value | split | n |
|---|---|---|---|
| retained | all | all | 106308 |
| scope | outside_envelope | all | 75219 |
| scope | pilot | all | 31089 |
| pilot_raw_agency_exact | กรมทางหลวง | all | 28726 |
| pilot_raw_agency_exact | กรมทางหลวงชนบท | all | 1290 |
| pilot_raw_agency_exact | การทางพิเศษแห่งประเทศไทย | all | 1073 |
| pilot_event_date_range | 2021-01-01..2025-12-31 | all | 31089 |

## 4. กฎ identity ของสายทาง (exact, ไม่มี alias)
| source_id | agency_exact | normalizer | rule | alias_entries |
|---|---|---|---|---|
| doh_highway | กรมทางหลวง | doh_numeric_zfill4 | NFKC + strip; must match ^[0-9]{1,4}$ (ASCII digits only), then zfill(4); anything else is route_nonstandard | 0 |
| drr_rural | กรมทางหลวงชนบท | drr_prefix_digits | NFKC, remove all whitespace, collapse repeated dots, strip leading/trailing dots; standard = exactly two Thai consonants + '.' + exactly four ASCII digits (e.g. นบ.3021), leading zeros and prefix kept verbatim. Codes 'ส.' + digits are special_unverified; anything else nonstandard. No padding, no inserted dot, no alias | 0 |
| exat_expressway | การทางพิเศษแห่งประเทศไทย | exat_unresolved | no verified crosswalk between accident route codes (e.g. E007S013/I) and geometry routes (RAE, FES, ...): every EXAT event is identity_unresolved; exact name equalities are listed as unadopted proposals only | 0 |

| source_label | identity_status | n |
|---|---|---|
| doh_highway | route_missing | 2 |
| doh_highway | route_not_in_snapshot | 3 |
| doh_highway | verified | 28721 |
| drr_rural | route_not_in_snapshot | 16 |
| drr_rural | route_special_unverified | 548 |
| drr_rural | verified | 726 |
| exat_expressway | identity_unresolved | 1073 |

EXAT: ข้อเสนอชื่อที่ตรงกันแบบ exact (ยังไม่นำมาใช้):
| source_id | raw_route_code | raw_route_name | n_pilot | n_train | exact_name_equal_geometry | decision | matched |
|---|---|---|---|---|---|---|---|
| exat_expressway | E001S001/I | ดินแดง-ท่าเรือ | 26 | 10 |  | no_proposal | False |
| exat_expressway | E001S001/U | ดินแดง-ท่าเรือ | 39 | 7 |  | no_proposal | False |
| exat_expressway | E001S002/I | บางนา-ท่าเรือ | 15 | 5 |  | no_proposal | False |
| exat_expressway | E001S002/U | บางนา-ท่าเรือ | 8 | 3 |  | no_proposal | False |
| exat_expressway | E001S003/I | ดาวคะนอง-ท่าเรือ | 34 | 9 |  | no_proposal | False |
| exat_expressway | E001S003/U | ดาวคะนอง-ท่าเรือ | 13 | 6 |  | no_proposal | False |
| exat_expressway | E002S007/I | พญาไท-บางโคล่ | 42 | 11 |  | no_proposal | False |
| exat_expressway | E002S007/U | พญาไท-บางโคล่ | 45 | 14 |  | no_proposal | False |
| exat_expressway | E002S014/I | แจ้งวัฒนะ-พญาไท | 70 | 21 |  | no_proposal | False |
| exat_expressway | E002S014/U | แจ้งวัฒนะ-พญาไท | 75 | 23 |  | no_proposal | False |
| exat_expressway | E002S016/I | พญาไท-ศรีนครินทร์ | 70 | 24 |  | no_proposal | False |
| exat_expressway | E002S016/U | พญาไท-ศรีนครินทร์ | 46 | 25 |  | no_proposal | False |
| exat_expressway | E002S018/I | หมอชิต-กาญจนาฯ | 22 | 0 |  | no_proposal | False |
| exat_expressway | E002S018/U | หมอชิต-กาญจนาฯ | 11 | 0 |  | no_proposal | False |
| exat_expressway | E003S008/I | รามอินทรา-อาจณรงค์ | 46 | 9 |  | no_proposal | False |

## 5. ผล linkage (primary 50m, sensitivity 25m, 100m)
กฎ: agency ตรง + route ที่ยืนยัน + ระยะ ≤ tolerance; มีคู่แข่ง same-identity ภายใน 5 ม. ของระยะที่ใกล้สุด = ambiguous_multiple; geometry ไม่ simple/valid = ambiguous_unsafe_geometry; ระยะ diagnostic ไม่ถูกยอมรับโดยปริยาย

| tolerance_m | status | n | denominator_retained | share_of_retained | denominator_pilot | share_of_pilot |
|---|---|---|---|---|---|---|
| 25 | outside_pilot_envelope | 75219 | 106308 | 0.7076 |  |  |
| 25 | low_precision_unsuitable | 13 | 106308 | 0.0001223 | 31089 | 0.0004182 |
| 25 | route_missing | 2 | 106308 | 1.881e-05 | 31089 | 6.433e-05 |
| 25 | route_special_unverified | 548 | 106308 | 0.005155 | 31089 | 0.01763 |
| 25 | identity_unresolved | 1070 | 106308 | 0.01007 | 31089 | 0.03442 |
| 25 | route_not_in_snapshot | 19 | 106308 | 0.0001787 | 31089 | 0.0006111 |
| 25 | too_far | 2738 | 106308 | 0.02576 | 31089 | 0.08807 |
| 25 | ambiguous_unsafe_geometry | 29 | 106308 | 0.0002728 | 31089 | 0.0009328 |
| 25 | ambiguous_multiple | 203 | 106308 | 0.00191 | 31089 | 0.00653 |
| 25 | matched | 26467 | 106308 | 0.249 | 31089 | 0.8513 |
| 50 | outside_pilot_envelope | 75219 | 106308 | 0.7076 |  |  |
| 50 | low_precision_unsuitable | 13 | 106308 | 0.0001223 | 31089 | 0.0004182 |
| 50 | route_missing | 2 | 106308 | 1.881e-05 | 31089 | 6.433e-05 |
| 50 | route_special_unverified | 548 | 106308 | 0.005155 | 31089 | 0.01763 |
| 50 | identity_unresolved | 1070 | 106308 | 0.01007 | 31089 | 0.03442 |
| 50 | route_not_in_snapshot | 19 | 106308 | 0.0001787 | 31089 | 0.0006111 |
| 50 | too_far | 696 | 106308 | 0.006547 | 31089 | 0.02239 |
| 50 | ambiguous_unsafe_geometry | 29 | 106308 | 0.0002728 | 31089 | 0.0009328 |
| 50 | ambiguous_multiple | 236 | 106308 | 0.00222 | 31089 | 0.007591 |
| 50 | matched | 28476 | 106308 | 0.2679 | 31089 | 0.916 |
| 100 | outside_pilot_envelope | 75219 | 106308 | 0.7076 |  |  |
| 100 | low_precision_unsuitable | 13 | 106308 | 0.0001223 | 31089 | 0.0004182 |
| 100 | route_missing | 2 | 106308 | 1.881e-05 | 31089 | 6.433e-05 |
| 100 | route_special_unverified | 548 | 106308 | 0.005155 | 31089 | 0.01763 |
| 100 | identity_unresolved | 1070 | 106308 | 0.01007 | 31089 | 0.03442 |
| 100 | route_not_in_snapshot | 19 | 106308 | 0.0001787 | 31089 | 0.0006111 |
| 100 | too_far | 416 | 106308 | 0.003913 | 31089 | 0.01338 |
| 100 | ambiguous_unsafe_geometry | 29 | 106308 | 0.0002728 | 31089 | 0.0009328 |
| 100 | ambiguous_multiple | 239 | 106308 | 0.002248 | 31089 | 0.007688 |
| 100 | matched | 28753 | 106308 | 0.2705 | 31089 | 0.9249 |

## 6. คลัง segment ผู้สมัครจาก geometry
ID: rsv1-<snapshot>:<agency>:<OID>:p<part>:c<clipped piece>:r<target m>:<index> · segments run along the digitised direction of each clipped piece; interval [start, end) is half-open except the last segment of a piece, which is closed [start, piece_end]; a point exactly at a boundary belongs to the downstream segment

| resolution_m | source_id | segments | full_length_segments | short_final_segments | pieces | route_keys | total_utm_km | total_geod_km | median_length_m | min_length_m | segments_cut_at_envelope | segments_on_overlapping_piece | segments_on_duplicate_piece |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 500 | all | 25358 | 23646 | 1712 | 1713 | 733 | 12206.0 | 12204.1 | 500 | 0.03076 | 132 | 0 | 0 |
| 500 | doh_highway | 12196 | 11598 | 598 | 599 | 229 | 5947.7 | 5946.7 | 500 | 0.03076 | 65 | 0 | 0 |
| 500 | drr_rural | 12166 | 11619 | 547 | 547 | 504 | 5948.6 | 5947.6 | 500 | 1.142 | 65 | 0 | 0 |
| 500 | exat_expressway | 996 | 429 | 567 | 567 | 0 | 309.8 | 309.8 | 387.5 | 0.05937 | 2 | 0 | 0 |
| 1000 | all | 13197 | 11484 | 1713 | 1713 | 733 | 12206.0 | 12204.1 | 1000 | 0.03076 | 132 | 0 | 0 |
| 1000 | doh_highway | 6266 | 5667 | 599 | 599 | 229 | 5947.7 | 5946.7 | 1000 | 0.03076 | 65 | 0 | 0 |
| 1000 | drr_rural | 6218 | 5671 | 547 | 547 | 504 | 5948.6 | 5947.6 | 1000 | 1.142 | 65 | 0 | 0 |
| 1000 | exat_expressway | 713 | 146 | 567 | 567 | 0 | 309.8 | 309.8 | 319.7 | 0.05937 | 2 | 0 | 0 |
| 2000 | all | 7167 | 5454 | 1713 | 1713 | 733 | 12206.0 | 12204.1 | 2000.0 | 0.05937 | 130 | 0 | 0 |
| 2000 | doh_highway | 3301 | 2702 | 599 | 599 | 229 | 5947.7 | 5946.7 | 2000.0 | 1.684 | 64 | 0 | 0 |
| 2000 | drr_rural | 3247 | 2700 | 547 | 547 | 504 | 5948.6 | 5947.6 | 2000.0 | 1.142 | 64 | 0 | 0 |
| 2000 | exat_expressway | 619 | 52 | 567 | 567 | 0 | 309.8 | 309.8 | 266.4 | 0.05937 | 2 | 0 | 0 |

| source_id | features | multipart_features | features_with_clip | unsafe_features | unsafe_reasons | unsafe_full_geod_km | unsafe_clipped_geod_km | pieces_total | pieces_usable | usable_clipped_utm_km | usable_clipped_geod_km | usable_pieces_cut_at_envelope | route_status_counts |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| doh_highway | 599 | 0 | 599 | 2 | not_simple=2 | 44.03 | 9.99 | 601 | 599 | 5947.7 | 5946.7 | 61 | standard=599 |
| drr_rural | 547 | 0 | 547 | 4 | not_simple=4 | 38.99 | 38.99 | 551 | 547 | 5948.6 | 5947.6 | 63 | route_special_unverified=23;standard=524 |
| exat_expressway | 8 | 8 | 8 | 4 | not_simple=4 | 379.7 | 379.7 | 1417 | 567 | 309.8 | 309.8 | 2 | identity_unresolved=8 |

ความเพี้ยนของความยาว UTM เทียบ geodesic:
| source_id | pieces | ratio_min | ratio_median | ratio_max | max_abs_ppm | total_utm_km | total_geod_km |
|---|---|---|---|---|---|---|---|
| all | 1713 | 0.9998 | 1 | 1.001 | 897.2 | 12206.0 | 12204.1 |
| doh_highway | 599 | 0.9998 | 1 | 1.001 | 886.4 | 5947.7 | 5946.7 |
| drr_rural | 547 | 0.9998 | 1 | 1.001 | 897.2 | 5948.6 | 5947.6 |
| exat_expressway | 567 | 0.9999 | 1 | 1 | 180.8 | 309.8 | 309.8 |

## 7. สิ่งที่ทำได้ / ยังทำไม่ได้
- ทำได้: นับบันทึกที่เชื่อมโยงได้อย่างมั่นใจต่อ segment (ภายใต้ pipeline และ snapshot นี้) สำหรับ DOH/DRR ที่ route ยืนยันได้ ภายใน envelope นำร่อง
- ยังทำไม่ได้: EXAT (ไม่มี crosswalk), รหัสพิเศษ DRR, เหตุที่ ambiguous/too_far/low precision/นอก envelope; ไม่มีการพิสูจน์ความครบถ้วนการรายงาน ไม่มี topology ย้อนหลัง ไม่มี datum ที่ยืนยัน
- ไม่มีบันทึก ≠ ไม่มีอุบัติเหตุ; ไม่สร้าง zero-filled panel ไม่มี probability ระดับบุคคล ไม่อ้างว่าโมเดล V2 ระดับจังหวัดใช้กับจุดได้

## 8. ขั้นถัดไป
ดู next_stage_protocol_proposal.md (ข้อเสนอเท่านั้น)

## 9. คำสั่งที่ใช้รัน
- `.venv/bin/python backend/scripts/run_spatial_linkage_audit.py --output-dir backend/rerun-linkage-014-001`
- `.venv/bin/python -m pytest backend/tests/test_spatial_linkage_audit_notebook.py -q`

output root ของรันนี้: `/Users/earthnaja/Documents/GitHub/Work - Earth/Project Work/Source Code/RoadAware/backend/rerun-linkage-014-002`

## 10. Checks
| check | status |
|---|---|
| lineage rows equal the accepted readiness manifest | pass |
| event_uid unique (one row per event) | pass |
| scope reconciliation (all): pilot + outside_envelope + coord_not_usable == retained | pass |
| scope reconciliation (seen_diagnostic): pilot + outside_envelope + coord_not_usable == retained | pass |
| scope reconciliation (train): pilot + outside_envelope + coord_not_usable == retained | pass |
| status reconciliation at 25m: one status per retained event, pilot statuses sum to pilot | pass |
| status reconciliation at 50m: one status per retained event, pilot statuses sum to pilot | pass |
| eligible candidate counts monotone 25m -> 50m | pass |
| matched set nested 25m -> 50m | pass |
| status reconciliation at 100m: one status per retained event, pilot statuses sum to pilot | pass |
| eligible candidate counts monotone 50m -> 100m | pass |
| matched set nested 50m -> 100m | pass |
| an accepted road part is recorded iff matched (at most one per event) | pass |
| unknown never zero: non-matched rows carry no distance/offset/segment (missing, not 0) | pass |
| low-precision / lat==lon coordinates are never matched | pass |
| identity-unresolved agencies (EXAT) are never matched | pass |
| full-section geodesic length (pyproj Geod) equals accepted diagnostics within 0.05 m | pass |
| per-part envelope clip reproduces accepted clipped lengths within 0.05 m | pass |
| features with a non-empty clip equal the accepted clipped GeoJSON ids | pass |
| non-simple feature counts equal the independent review (kept in audit, excluded from segmentation) | pass |
| unsafe flag is feature-level and consistent across parts/pieces (matched on (source_id, oid), both directions) | pass |
| pairwise overlap computation completed for every intersecting piece pair | pass |
| length conservation per clipped piece < 0.01 m at 500 m | pass |
| segment IDs unique at 500 m | pass |
| no segment built on unsafe geometry at 500 m | pass |
| segment length equals its interval; only the final segment may exceed the target, by at most the zero-remainder eps (0.001 m), at 500 m | pass |
| every assigned event segment exists in the geometry inventory and belongs to the chosen OID at 500 m | pass |
| length conservation per clipped piece < 0.01 m at 1000 m | pass |
| segment IDs unique at 1000 m | pass |
| no segment built on unsafe geometry at 1000 m | pass |
| segment length equals its interval; only the final segment may exceed the target, by at most the zero-remainder eps (0.001 m), at 1000 m | pass |
| every assigned event segment exists in the geometry inventory and belongs to the chosen OID at 1000 m | pass |
| length conservation per clipped piece < 0.01 m at 2000 m | pass |
| segment IDs unique at 2000 m | pass |
| no segment built on unsafe geometry at 2000 m | pass |
| segment length equals its interval; only the final segment may exceed the target, by at most the zero-remainder eps (0.001 m), at 2000 m | pass |
| every assigned event segment exists in the geometry inventory and belongs to the chosen OID at 2000 m | pass |
| protected inputs/outputs unchanged (sha256 before == after) | pass |

## 11. ข้อจำกัด
- descriptive linkage evidence only: no model, probability, threshold, risk score or coloured warning is produced
- road geometry is the current service snapshot (task 013a capture); it does not prove 2021-2025 topology; segment IDs are valid only within the pinned snapshot
- event coordinates are assumed WGS84 without verification; no positional accuracy and no point-in-province validation is claimed (no province polygons registered)
- the envelope is a fixed predeclared scope filter, not an SPU-Khao Yai route, not all six provinces, and never road validation
- no record is not proof of no accident; unmatched, ambiguous, identity-unverified, low-precision and outside events are unknown, never zero
- linked counts are recorded+linked database counts conditional on the fixed collection and linkage pipeline, not physical accident counts or reporting completeness
- EXAT accident route codes have no verified crosswalk to geometry routes: every EXAT event stays identity_unresolved
- DRR special codes are unverified and never matched; no alias, padding, substring or fuzzy matching is used
- raw KM is diagnostic only (units unverified) and never a match criterion
- segment lengths are EPSG:32647 projected metres; projected vs geodesic distortion is reported, not corrected
- overlapping/duplicate road pieces are flagged, not merged: inventory length is not unique network mileage and no routable graph is built
- V2 province models are not claimed to transfer to points or segments
