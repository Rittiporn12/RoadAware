# รายงานตรวจการเชื่อมโยงอุบัติเหตุกับถนนและคลัง segment (V3 notebook 18)

> **หลักฐานเชิงพรรณนาของการเชื่อมโยงข้อมูลเท่านั้น ไม่ใช่การพยากรณ์ ไม่ใช่ระดับความเสี่ยง** ไม่มีการ train โมเดล ไม่มี probability/threshold/สีเตือน

สถานะการตรวจรับอัตโนมัติ: **complete** (38/38 checks pass) · config spatial_linkage_v4.0 · snapshot rc315c7c508f

## 1. ขอบเขตและวันที่
envelope ที่ลงทะเบียนไว้ EPSG4326 [97.3, 5.5, 105.7, 20.5] (ไม่ใช่เส้นทาง SPU-เขาใหญ่ ไม่ครอบคลุม 6 จังหวัด ใช้เป็นตัวกรองขอบเขต ไม่ใช่การยืนยันว่าอยู่บนถนน)

| split | event_date | retained | pilot_in_envelope | outside_envelope | coord_not_usable | matched_50m | matched_with_segment_50m |
|---|---|---|---|---|---|---|---|
| all | 2021-01-01..2025-12-31 | 106308 | 106308 | 0 | 0 | 101739 | 101739 |
| train | 2021-01-01..2023-12-30 | 60978 | 60978 | 0 | 0 | 58769 | 58769 |
| seen_diagnostic | 2024-01-01..2025-12-31 | 45330 | 45330 | 0 | 0 | 42970 | 42970 |

train = 2021-2023 · seen_diagnostic = 2024-2025 (ข้อมูลที่เคยเห็นแล้ว ใช้รายงาน linkage เท่านั้น ไม่ใช้เลือก resolution)

## 2. Input ที่ตรวจ hash แล้ว
| input | sha256 | rule | status |
|---|---|---|---|
| road_manifest | 5efe53140f81c7747d31153c4f74a433efe13bc353d7417cf74177bf4c917956 | config pin | pass |
| road_review | dd784728d724b255b28cc66395307714fd814e4d6c44dbb810cd5318f26c3487 | config pin | pass |
| readiness_manifest | 0004b14460fef8af8a5de69f0b0d1711faf27c9acfeb897087ebaba03ad6e243 | config pin | pass |
| doh_highway_clipped.geojson | 69365ad13217e6452e47e0bc6f219e6a92cda90c5f6438f636296035f5119c38 | config pin == road manifest derived_files | pass |
| doh_highway_full.geojson | ad7876c27e112b13c31047b617226267a653eca937ec3956f2980cb9f4b1b0f7 | config pin == road manifest derived_files | pass |
| drr_rural_clipped.geojson | 079f6340d24cd04fd40cf9deee2e6676e3eb78d16a0c4c39d0a8011576aca109 | config pin == road manifest derived_files | pass |
| drr_rural_full.geojson | 7b90c4f1ee53065156a760bebaf9319995716ee040dc244c8df8be273a9a9da8 | config pin == road manifest derived_files | pass |
| exat_expressway_clipped.geojson | f82a03980c28b73b01ec1288c9f36152a5cc9e1fd917104e7ef662e900a95650 | config pin == road manifest derived_files | pass |
| exat_expressway_full.geojson | 8e54d2e567356979727fc33ac4f101bfac188cbf53d07ef697ce2ccb7e3cb3e8 | config pin == road manifest derived_files | pass |
| feature_diagnostics.csv | 6725e02f36a60b2b1d9f3489eef72a2fa0fc407826a2fc1796004f032e91f58f | config pin == road manifest derived_files | pass |
| lineage | 78ded7939a327e5cbd45132e297b5a1bfbe76bef117ac3ac5da9b4a90352da2c | config pin == readiness manifest row_level_outputs_gitignored | pass |

## 3. พิกัด (ไม่ซ่อม)
พิกัดที่ swap/หาย/ไม่เป็นตัวเลข/นอกกรอบประเทศ ถูก flag ตามสถานะจาก notebook 16 และไม่ถูกแก้ ค่าความละเอียดต่ำ (ทศนิยม ≤ 3) หรือ lat==lon = ไม่เหมาะกับการกำหนดถนนแบบมั่นใจ

| dimension | value | split | n |
|---|---|---|---|
| retained | all | all | 106308 |
| scope | pilot | all | 106308 |
| pilot_raw_agency_exact | กรมทางหลวง | all | 101373 |
| pilot_raw_agency_exact | กรมทางหลวงชนบท | all | 3852 |
| pilot_raw_agency_exact | การทางพิเศษแห่งประเทศไทย | all | 1083 |
| pilot_event_date_range | 2021-01-01..2025-12-31 | all | 106308 |

## 4. กฎ identity ของสายทาง (exact, ไม่มี alias)
| source_id | agency_exact | normalizer | rule | alias_entries |
|---|---|---|---|---|
| doh_highway | กรมทางหลวง | doh_numeric_zfill4 | NFKC + strip; must match ^[0-9]{1,4}$ (ASCII digits only), then zfill(4); anything else is route_nonstandard | 0 |
| drr_rural | กรมทางหลวงชนบท | drr_prefix_digits | NFKC, remove all whitespace, collapse repeated dots, strip leading/trailing dots; standard = exactly two Thai consonants + '.' + exactly four ASCII digits (e.g. นบ.3021), leading zeros and prefix kept verbatim. Codes 'ส.' + digits are special_unverified; anything else nonstandard. No padding, no inserted dot, no alias | 0 |
| exat_expressway | การทางพิเศษแห่งประเทศไทย | exat_unresolved | no verified crosswalk between accident route codes (e.g. E007S013/I) and geometry routes (RAE, FES, ...): every EXAT event is identity_unresolved; exact name equalities are listed as unadopted proposals only | 0 |

| source_label | identity_status | n |
|---|---|---|
| doh_highway | route_missing | 9 |
| doh_highway | route_not_in_snapshot | 15 |
| doh_highway | verified | 101349 |
| drr_rural | route_not_in_snapshot | 46 |
| drr_rural | route_special_unverified | 548 |
| drr_rural | verified | 3258 |
| exat_expressway | identity_unresolved | 1083 |

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
| 25 | low_precision_unsuitable | 36 | 106308 | 0.0003386 | 106308 | 0.0003386 |
| 25 | route_missing | 9 | 106308 | 8.466e-05 | 106308 | 8.466e-05 |
| 25 | route_special_unverified | 548 | 106308 | 0.005155 | 106308 | 0.005155 |
| 25 | identity_unresolved | 1080 | 106308 | 0.01016 | 106308 | 0.01016 |
| 25 | route_not_in_snapshot | 61 | 106308 | 0.0005738 | 106308 | 0.0005738 |
| 25 | too_far | 4920 | 106308 | 0.04628 | 106308 | 0.04628 |
| 25 | ambiguous_unsafe_geometry | 769 | 106308 | 0.007234 | 106308 | 0.007234 |
| 25 | ambiguous_multiple | 345 | 106308 | 0.003245 | 106308 | 0.003245 |
| 25 | matched | 98540 | 106308 | 0.9269 | 106308 | 0.9269 |
| 50 | low_precision_unsuitable | 36 | 106308 | 0.0003386 | 106308 | 0.0003386 |
| 50 | route_missing | 9 | 106308 | 8.466e-05 | 106308 | 8.466e-05 |
| 50 | route_special_unverified | 548 | 106308 | 0.005155 | 106308 | 0.005155 |
| 50 | identity_unresolved | 1080 | 106308 | 0.01016 | 106308 | 0.01016 |
| 50 | route_not_in_snapshot | 61 | 106308 | 0.0005738 | 106308 | 0.0005738 |
| 50 | too_far | 1673 | 106308 | 0.01574 | 106308 | 0.01574 |
| 50 | ambiguous_unsafe_geometry | 777 | 106308 | 0.007309 | 106308 | 0.007309 |
| 50 | ambiguous_multiple | 385 | 106308 | 0.003622 | 106308 | 0.003622 |
| 50 | matched | 101739 | 106308 | 0.957 | 106308 | 0.957 |
| 100 | low_precision_unsuitable | 36 | 106308 | 0.0003386 | 106308 | 0.0003386 |
| 100 | route_missing | 9 | 106308 | 8.466e-05 | 106308 | 8.466e-05 |
| 100 | route_special_unverified | 548 | 106308 | 0.005155 | 106308 | 0.005155 |
| 100 | identity_unresolved | 1080 | 106308 | 0.01016 | 106308 | 0.01016 |
| 100 | route_not_in_snapshot | 61 | 106308 | 0.0005738 | 106308 | 0.0005738 |
| 100 | too_far | 890 | 106308 | 0.008372 | 106308 | 0.008372 |
| 100 | ambiguous_unsafe_geometry | 777 | 106308 | 0.007309 | 106308 | 0.007309 |
| 100 | ambiguous_multiple | 390 | 106308 | 0.003669 | 106308 | 0.003669 |
| 100 | matched | 102517 | 106308 | 0.9643 | 106308 | 0.9643 |

## 6. คลัง segment ผู้สมัครจาก geometry
ID: rsv1-<snapshot>:<agency>:<OID>:p<part>:c<clipped piece>:r<target m>:<index> · segments run along the digitised direction of each clipped piece; interval [start, end) is half-open except the last segment of a piece, which is closed [start, piece_end]; a point exactly at a boundary belongs to the downstream segment

| resolution_m | source_id | segments | full_length_segments | short_final_segments | pieces | route_keys | total_utm_km | total_geod_km | median_length_m | min_length_m | segments_cut_at_envelope | segments_on_overlapping_piece | segments_on_duplicate_piece |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 500 | all | 210665 | 203404 | 7261 | 7266 | 5096 | 103480.1 | 103399.5 | 500 | 0.02925 | 0 | 0 | 0 |
| 500 | doh_highway | 105686 | 102661 | 3025 | 3030 | 1522 | 52079.1 | 52044.7 | 500 | 0.02925 | 0 | 0 | 0 |
| 500 | drr_rural | 103957 | 100292 | 3665 | 3665 | 3574 | 51079.3 | 51033.2 | 500 | 0.4767 | 0 | 0 | 0 |
| 500 | exat_expressway | 1022 | 451 | 571 | 571 | 0 | 321.7 | 321.7 | 390.8 | 0.05937 | 0 | 0 | 0 |
| 1000 | all | 107255 | 99993 | 7262 | 7266 | 5096 | 103480.1 | 103399.5 | 1000 | 0.02925 | 0 | 0 | 0 |
| 1000 | doh_highway | 53632 | 50606 | 3026 | 3030 | 1522 | 52079.1 | 52044.7 | 1000 | 0.02925 | 0 | 0 | 0 |
| 1000 | drr_rural | 52896 | 49231 | 3665 | 3665 | 3574 | 51079.3 | 51033.2 | 1000 | 0.6932 | 0 | 0 | 0 |
| 1000 | exat_expressway | 727 | 156 | 571 | 571 | 0 | 321.7 | 321.7 | 321.8 | 0.05937 | 0 | 0 | 0 |
| 2000 | all | 55657 | 48395 | 7262 | 7266 | 5096 | 103480.1 | 103399.5 | 2000.0 | 0.05937 | 0 | 0 | 0 |
| 2000 | doh_highway | 27663 | 24637 | 3026 | 3030 | 1522 | 52079.1 | 52044.7 | 2000.0 | 1.684 | 0 | 0 | 0 |
| 2000 | drr_rural | 27368 | 23703 | 3665 | 3665 | 3574 | 51079.3 | 51033.2 | 2000.0 | 0.6932 | 0 | 0 | 0 |
| 2000 | exat_expressway | 626 | 55 | 571 | 571 | 0 | 321.7 | 321.7 | 270.4 | 0.05937 | 0 | 0 | 0 |

| source_id | features | multipart_features | features_with_clip | unsafe_features | unsafe_reasons | unsafe_full_geod_km | unsafe_clipped_geod_km | pieces_total | pieces_usable | usable_clipped_utm_km | usable_clipped_geod_km | usable_pieces_cut_at_envelope | route_status_counts |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| doh_highway | 3044 | 0 | 3044 | 14 | not_simple=14 | 339.7 | 339.7 | 3044 | 3030 | 52079.1 | 52044.7 | 0 | standard=3044 |
| drr_rural | 3700 | 0 | 3700 | 35 | not_simple=35 | 377.8 | 377.8 | 3700 | 3665 | 51079.3 | 51033.2 | 0 | route_special_unverified=23;standard=3677 |
| exat_expressway | 8 | 8 | 8 | 4 | not_simple=4 | 379.7 | 379.7 | 1421 | 571 | 321.7 | 321.7 | 0 | identity_unresolved=8 |

ความเพี้ยนของความยาว UTM เทียบ geodesic:
| source_id | pieces | ratio_min | ratio_median | ratio_max | max_abs_ppm | total_utm_km | total_geod_km |
|---|---|---|---|---|---|---|---|
| all | 7266 | 0.9996 | 1 | 1.006 | 5667.8 | 103480.1 | 103399.5 |
| doh_highway | 3030 | 0.9996 | 1 | 1.006 | 5635.7 | 52079.1 | 52044.7 |
| drr_rural | 3665 | 0.9996 | 1 | 1.006 | 5667.8 | 51079.3 | 51033.2 |
| exat_expressway | 571 | 0.9999 | 1 | 1 | 181.6 | 321.7 | 321.7 |

## 7. สิ่งที่ทำได้ / ยังทำไม่ได้
- ทำได้: นับบันทึกที่เชื่อมโยงได้อย่างมั่นใจต่อ segment (ภายใต้ pipeline และ snapshot นี้) สำหรับ DOH/DRR ที่ route ยืนยันได้ ภายใน envelope นำร่อง
- ยังทำไม่ได้: EXAT (ไม่มี crosswalk), รหัสพิเศษ DRR, เหตุที่ ambiguous/too_far/low precision/นอก envelope; ไม่มีการพิสูจน์ความครบถ้วนการรายงาน ไม่มี topology ย้อนหลัง ไม่มี datum ที่ยืนยัน
- ไม่มีบันทึก ≠ ไม่มีอุบัติเหตุ; ไม่สร้าง zero-filled panel ไม่มี probability ระดับบุคคล ไม่อ้างว่าโมเดล V2 ระดับจังหวัดใช้กับจุดได้

## 8. ขั้นถัดไป
ดู next_stage_protocol_proposal.md (ข้อเสนอเท่านั้น)

## 9. คำสั่งที่ใช้รัน
- `.venv/bin/python backend/scripts/run_spatial_linkage_audit.py --output-dir backend/rerun-linkage-014-001`
- `.venv/bin/python -m pytest backend/tests/test_spatial_linkage_audit_notebook.py -q`

output root ของรันนี้: `/Users/earthnaja/Documents/GitHub/Work - Earth/Project Work/Source Code/RoadAware/backend/rerun-linkage-national-001`

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
