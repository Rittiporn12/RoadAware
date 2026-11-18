# Notebook 19 — เตรียมข้อมูล spatial CountRegression (ไม่ใช่โมเดล ไม่ใช่การพยากรณ์)

สถานะ: **complete (preparation only)** · เวอร์ชัน spatial_preparation_v4.0 · snapshot rc315c7c508f

## 1. ขอบเขตเป้าหมาย (target)
y = number of retained 2021-25 MOT records with status_50m == matched AND segment_status == assigned to a universe segment, per segment x local day (or 6 h block). Zero means zero such SELECTED+LINKED records in the defined conditional population, NOT zero real accidents or complete reporting. Unknown / unmatched / unassigned / outside records are audited separately and never allocated as zero events.

## 2. จักรวาล segment (กำหนดจาก geometry เท่านั้น ก่อนมีคะแนนโมเดลใด)
geometry-only predicate fixed before any model score: source DOH AND geometry route_status standard AND 2000 m resolution AND projected length >= 500 m AND present in the accepted (safe-geometry) 18 inventory. Every qualifying segment is included whether or not it has records. Stable 18 segment IDs, never re-segmented. DRR/EXAT/nonstandard routes/short tails are unsupported (no prediction, never a fake zero).

ค่าที่วัดจริงในรันนี้ (preflight ของผู้จัดการเป็นบริบทเท่านั้น: {'segments': 27663, 'routes': None, 'projected_km': None, 'note': 'national: DOH 2000 m segments in the accepted V4 linkage inventory (all statuses/lengths); context only, never a guard'}):
| segments | routes | projected_km | geodesic_km | utm_over_geodesic_min | utm_over_geodesic_max | short_final_segments | piece_overlap_segments | piece_duplicate_segments | chord_zero_guard_segments | aadt_identity_ok | preflight_segments_context | preflight_routes_context | preflight_km_context |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 26740 | 1440 | 51857.778 | 51823.446 | 0.9996000000566733 | 1.0057204427274542 | 2103 | 0 | 0 | 0 | 26740 | 27663 | None | None |

segment ที่ไม่รองรับ (ไม่มีการทำนาย ไม่ใช่ศูนย์):
| source_id | unsupported_reason | segments | km |
| --- | --- | --- | --- |
| doh_highway | short_lt_min_length | 923 | 221.356 |
| drr_rural | unsupported_source_drr_rural | 27368 | 51079.335 |
| exat_expressway | unsupported_source_exat_expressway | 626 | 321.663 |

## 3. การคัดเลือกบันทึก (reconciled ทุกแถว)
| ce_year | split | selection | records |
| --- | --- | --- | --- |
| 2021 | train | selected | 18063 |
| 2021 | train | unknown_status_50m_ambiguous_multiple | 39 |
| 2021 | train | unknown_status_50m_ambiguous_unsafe_geometry | 153 |
| 2021 | train | unknown_status_50m_identity_unresolved | 126 |
| 2021 | train | unknown_status_50m_low_precision_unsuitable | 9 |
| 2021 | train | unknown_status_50m_route_not_in_snapshot | 31 |
| 2021 | train | unknown_status_50m_route_special_unverified | 124 |
| 2021 | train | unknown_status_50m_too_far | 355 |
| 2021 | train | unsupported_segment_short_lt_min_length | 84 |
| 2021 | train | unsupported_segment_unsupported_source_drr_rural | 1012 |
| 2022 | train | selected | 18698 |
| 2022 | train | unknown_status_50m_ambiguous_multiple | 60 |
| 2022 | train | unknown_status_50m_ambiguous_unsafe_geometry | 148 |
| 2022 | train | unknown_status_50m_identity_unresolved | 184 |
| 2022 | train | unknown_status_50m_route_not_in_snapshot | 18 |
| 2022 | train | unknown_status_50m_route_special_unverified | 163 |
| 2022 | train | unknown_status_50m_too_far | 286 |
| 2022 | train | unsupported_segment_short_lt_min_length | 83 |
| 2022 | train | unsupported_segment_unsupported_source_drr_rural | 852 |
| 2023 | train | selected | 19895 |
| 2023 | train | unknown_status_50m_ambiguous_multiple | 87 |
| 2023 | train | unknown_status_50m_ambiguous_unsafe_geometry | 133 |
| 2023 | train | unknown_status_50m_low_precision_unsuitable | 5 |
| 2023 | train | unknown_status_50m_too_far | 288 |
| 2023 | train | unsupported_segment_short_lt_min_length | 82 |
| 2024 | seen_diagnostic | selected | 19904 |
| 2024 | seen_diagnostic | unknown_status_50m_ambiguous_multiple | 97 |
| 2024 | seen_diagnostic | unknown_status_50m_ambiguous_unsafe_geometry | 153 |
| 2024 | seen_diagnostic | unknown_status_50m_identity_unresolved | 358 |
| 2024 | seen_diagnostic | unknown_status_50m_low_precision_unsuitable | 10 |
| 2024 | seen_diagnostic | unknown_status_50m_route_missing | 2 |
| 2024 | seen_diagnostic | unknown_status_50m_route_not_in_snapshot | 6 |
| 2024 | seen_diagnostic | unknown_status_50m_route_special_unverified | 104 |
| 2024 | seen_diagnostic | unknown_status_50m_too_far | 385 |
| 2024 | seen_diagnostic | unsupported_segment_short_lt_min_length | 91 |
| 2024 | seen_diagnostic | unsupported_segment_unsupported_source_drr_rural | 678 |
| 2025 | seen_diagnostic | selected | 21647 |
| 2025 | seen_diagnostic | unknown_status_50m_ambiguous_multiple | 102 |
| 2025 | seen_diagnostic | unknown_status_50m_ambiguous_unsafe_geometry | 190 |
| 2025 | seen_diagnostic | unknown_status_50m_identity_unresolved | 412 |
| 2025 | seen_diagnostic | unknown_status_50m_low_precision_unsuitable | 12 |
| 2025 | seen_diagnostic | unknown_status_50m_route_missing | 7 |
| 2025 | seen_diagnostic | unknown_status_50m_route_not_in_snapshot | 6 |
| 2025 | seen_diagnostic | unknown_status_50m_route_special_unverified | 157 |
| 2025 | seen_diagnostic | unknown_status_50m_too_far | 359 |
| 2025 | seen_diagnostic | unsupported_segment_short_lt_min_length | 92 |
| 2025 | seen_diagnostic | unsupported_segment_unsupported_source_drr_rural | 558 |

## 4. จำนวนนับ sparse และประชากรเสมือน
| unit | split | date_start | date_end | segments | days | population_cells | positive_cells | selected_records | zero_cells_conditional | max_cell_count | segments_with_any_record | mean_count_per_cell |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| daily | train | 2021-01-01 | 2023-12-31 | 26740 | 1095 | 29280300 | 55133 | 56656 | 29225167 | 7 | 13522 | 0.0019349528522590274 |
| daily | seen_2024 | 2024-01-01 | 2024-12-31 | 26740 | 366 | 9786840 | 19349 | 19904 | 9767491 | 6 | 8145 | 0.0020337514458190794 |
| daily | seen_2025 | 2025-01-01 | 2025-12-31 | 26740 | 365 | 9760100 | 21057 | 21647 | 9739043 | 6 | 8680 | 0.002217907603405703 |
| 6h | train | 2021-01-01 | 2023-12-31 | 26740 | 1095 | 117121200 | 55803 | 56656 | 117065397 | 6 | 13522 | 0.00048373821306475686 |
| 6h | seen_2024 | 2024-01-01 | 2024-12-31 | 26740 | 366 | 39147360 | 19611 | 19904 | 39127749 | 6 | 8145 | 0.0005084378614547699 |
| 6h | seen_2025 | 2025-01-01 | 2025-12-31 | 26740 | 365 | 39040400 | 21351 | 21647 | 39019049 | 6 | 8680 | 0.0005544769008514257 |

| unit | rows | batches | max_batch_rows | count_sum | positive_cells | first_key | last_key |
| --- | --- | --- | --- | --- | --- | --- | --- |
| daily | 48827240 | 489 | 100000 | 98207 | 95539 | {"segment_id": "rsv1-rc315c7c508f:doh:1000:p0:c0:r2000:00000", "target_date": "2021-01-01"} | {"segment_id": "rsv1-rc315c7c508f:doh:9:p0:c0:r2000:00002", "target_date": "2025-12-31"} |
| 6h | 195308960 | 1954 | 100000 | 98207 | 96765 | {"segment_id": "rsv1-rc315c7c508f:doh:1000:p0:c0:r2000:00000", "target_date": "2021-01-01", "time_block": "00-06"} | {"segment_id": "rsv1-rc315c7c508f:doh:9:p0:c0:r2000:00002", "target_date": "2025-12-31", "time_block": "18-24"} |

## 5. จังหวัดจากจุดกึ่งกลาง segment (geoBoundaries 2017/OSM ไม่ใช่ขอบเขตทางการปัจจุบัน)
| province_join_status | n_covering_polygons | segments | km |
| --- | --- | --- | --- |
| mapped | 1 | 26739 | 51855.778 |
| unmapped | 0 | 1 | 2.0 |

ความสอดคล้องจังหวัดของเหตุกับจังหวัดของ segment (เชิงพรรณนาเท่านั้น):
| split | agreement | selected_records |
| --- | --- | --- |
| train | same_province | 55923 |
| seen_diagnostic | same_province | 40950 |
| train | different_province | 730 |
| seen_diagnostic | different_province | 597 |
| seen_diagnostic | segment_midpoint_unmapped | 4 |
| train | segment_midpoint_unmapped | 3 |

## 6. ความครอบคลุมของ feature บริบท และ as-of
| scope | unit | year | rows | feature | non_missing | share |
| --- | --- | --- | --- | --- | --- | --- |
| population_2021_2025 | daily | 2021 | 9760100 | bank_holiday_asof | 9572920 | 0.9808219178082191 |
| population_2021_2025 | daily | 2021 | 9760100 | wx_rain_sum_mm_d2 | 9757876 | 0.9997721334822389 |
| population_2021_2025 | daily | 2021 | 9760100 | wx_temp_mean_c_d2 | 9759735 | 0.999962602842184 |
| population_2021_2025 | daily | 2021 | 9760100 | aadt_mean_total | 0 | 0.0 |
| population_2021_2025 | daily | 2021 | 9760100 | aadt_median_total | 0 | 0.0 |
| population_2021_2025 | daily | 2021 | 9760100 | aadt_mean_heavy_share_pct | 0 | 0.0 |
| population_2021_2025 | daily | 2022 | 9760100 | bank_holiday_asof | 9760100 | 1.0 |
| population_2021_2025 | daily | 2022 | 9760100 | wx_rain_sum_mm_d2 | 9747007 | 0.9986585178430549 |
| population_2021_2025 | daily | 2022 | 9760100 | wx_temp_mean_c_d2 | 9759735 | 0.999962602842184 |
| population_2021_2025 | daily | 2022 | 9760100 | aadt_mean_total | 6698759 | 0.6863412260120285 |
| population_2021_2025 | daily | 2022 | 9760100 | aadt_median_total | 6698759 | 0.6863412260120285 |
| population_2021_2025 | daily | 2022 | 9760100 | aadt_mean_heavy_share_pct | 6698759 | 0.6863412260120285 |
| population_2021_2025 | daily | 2023 | 9760100 | bank_holiday_asof | 9760100 | 1.0 |
| population_2021_2025 | daily | 2023 | 9760100 | wx_rain_sum_mm_d2 | 6553906 | 0.6714998821733383 |
| population_2021_2025 | daily | 2023 | 9760100 | wx_temp_mean_c_d2 | 6582775 | 0.6744577412116679 |
| population_2021_2025 | daily | 2023 | 9760100 | aadt_mean_total | 8701235 | 0.8915108451757666 |
| population_2021_2025 | daily | 2023 | 9760100 | aadt_median_total | 8701235 | 0.8915108451757666 |
| population_2021_2025 | daily | 2023 | 9760100 | aadt_mean_heavy_share_pct | 8701235 | 0.8915108451757666 |
| population_2021_2025 | daily | 2024 | 9786840 | bank_holiday_asof | 9786840 | 1.0 |
| population_2021_2025 | daily | 2024 | 9786840 | wx_rain_sum_mm_d2 | 0 | 0.0 |
| population_2021_2025 | daily | 2024 | 9786840 | wx_temp_mean_c_d2 | 0 | 0.0 |
| population_2021_2025 | daily | 2024 | 9786840 | aadt_mean_total | 8787057 | 0.8978441458121313 |
| population_2021_2025 | daily | 2024 | 9786840 | aadt_median_total | 8787057 | 0.8978441458121313 |
| population_2021_2025 | daily | 2024 | 9786840 | aadt_mean_heavy_share_pct | 8787057 | 0.8978441458121313 |
| population_2021_2025 | daily | 2025 | 9760100 | bank_holiday_asof | 9760100 | 1.0 |
| population_2021_2025 | daily | 2025 | 9760100 | wx_rain_sum_mm_d2 | 0 | 0.0 |
| population_2021_2025 | daily | 2025 | 9760100 | wx_temp_mean_c_d2 | 0 | 0.0 |
| population_2021_2025 | daily | 2025 | 9760100 | aadt_mean_total | 8795625 | 0.9011818526449524 |
| population_2021_2025 | daily | 2025 | 9760100 | aadt_median_total | 8795625 | 0.9011818526449524 |
| population_2021_2025 | daily | 2025 | 9760100 | aadt_mean_heavy_share_pct | 8795625 | 0.9011818526449524 |
| population_2021_2025 | 6h | 2021 | 39040400 | bank_holiday_asof | 38291680 | 0.9808219178082191 |
| population_2021_2025 | 6h | 2021 | 39040400 | wx_rain_sum_mm_d2 | 39031504 | 0.9997721334822389 |
| population_2021_2025 | 6h | 2021 | 39040400 | wx_temp_mean_c_d2 | 39038940 | 0.999962602842184 |
| population_2021_2025 | 6h | 2021 | 39040400 | wx_block_rain_sum_mm_d2 | 39036142 | 0.9998909334945338 |
| population_2021_2025 | 6h | 2021 | 39040400 | wx_block_temp_mean_c_d2 | 39038940 | 0.999962602842184 |
| population_2021_2025 | 6h | 2021 | 39040400 | aadt_mean_total | 0 | 0.0 |
| population_2021_2025 | 6h | 2021 | 39040400 | aadt_median_total | 0 | 0.0 |
| population_2021_2025 | 6h | 2021 | 39040400 | aadt_mean_heavy_share_pct | 0 | 0.0 |
| population_2021_2025 | 6h | 2022 | 39040400 | bank_holiday_asof | 39040400 | 1.0 |
| population_2021_2025 | 6h | 2022 | 39040400 | wx_rain_sum_mm_d2 | 38988028 | 0.9986585178430549 |
| population_2021_2025 | 6h | 2022 | 39040400 | wx_temp_mean_c_d2 | 39038940 | 0.999962602842184 |
| population_2021_2025 | 6h | 2022 | 39040400 | wx_block_rain_sum_mm_d2 | 39024434 | 0.9995910390262395 |
| population_2021_2025 | 6h | 2022 | 39040400 | wx_block_temp_mean_c_d2 | 39038940 | 0.999962602842184 |
| population_2021_2025 | 6h | 2022 | 39040400 | aadt_mean_total | 26795036 | 0.6863412260120285 |
| population_2021_2025 | 6h | 2022 | 39040400 | aadt_median_total | 26795036 | 0.6863412260120285 |
| population_2021_2025 | 6h | 2022 | 39040400 | aadt_mean_heavy_share_pct | 26795036 | 0.6863412260120285 |
| population_2021_2025 | 6h | 2023 | 39040400 | bank_holiday_asof | 39040400 | 1.0 |
| population_2021_2025 | 6h | 2023 | 39040400 | wx_rain_sum_mm_d2 | 26215624 | 0.6714998821733383 |
| population_2021_2025 | 6h | 2023 | 39040400 | wx_temp_mean_c_d2 | 26331100 | 0.6744577412116679 |
| population_2021_2025 | 6h | 2023 | 39040400 | wx_block_rain_sum_mm_d2 | 26296348 | 0.6735675863976803 |
| population_2021_2025 | 6h | 2023 | 39040400 | wx_block_temp_mean_c_d2 | 26331100 | 0.6744577412116679 |
| population_2021_2025 | 6h | 2023 | 39040400 | aadt_mean_total | 34804940 | 0.8915108451757666 |
| population_2021_2025 | 6h | 2023 | 39040400 | aadt_median_total | 34804940 | 0.8915108451757666 |
| population_2021_2025 | 6h | 2023 | 39040400 | aadt_mean_heavy_share_pct | 34804940 | 0.8915108451757666 |
| population_2021_2025 | 6h | 2024 | 39147360 | bank_holiday_asof | 39147360 | 1.0 |
| population_2021_2025 | 6h | 2024 | 39147360 | wx_rain_sum_mm_d2 | 0 | 0.0 |
| population_2021_2025 | 6h | 2024 | 39147360 | wx_temp_mean_c_d2 | 0 | 0.0 |
| population_2021_2025 | 6h | 2024 | 39147360 | wx_block_rain_sum_mm_d2 | 0 | 0.0 |
| population_2021_2025 | 6h | 2024 | 39147360 | wx_block_temp_mean_c_d2 | 0 | 0.0 |
| population_2021_2025 | 6h | 2024 | 39147360 | aadt_mean_total | 35148228 | 0.8978441458121313 |

| source | year | detail |
| --- | --- | --- |
| bank_calendar | 2021 | {"reviewed_annual_base_known_later_amendments_unknown": 358, "unknown_annual_source_not_yet_known": 7} |
| aadt_vintage | 2021 | {"-1": 365} |
| bank_calendar | 2022 | {"reviewed_annual_base_known_later_amendments_unknown": 365} |
| aadt_vintage | 2022 | {"-1": 84, "2021": 281} |
| bank_calendar | 2023 | {"reviewed_annual_base_known_later_amendments_unknown": 365} |
| aadt_vintage | 2023 | {"2021": 365} |
| bank_calendar | 2024 | {"reviewed_annual_base_known_later_amendments_unknown": 366} |
| aadt_vintage | 2024 | {"2021": 153, "2022": 213} |
| bank_calendar | 2025 | {"reviewed_annual_base_known_later_amendments_unknown": 365} |
| aadt_vintage | 2025 | {"2022": 150, "2024": 215} |
| bank_calendar | 2026 | {"unknown_no_applied_reviewed_annual_source": 365} |
| aadt_vintage | 2026 | {"2024": 21, "2025": 344} |
| bank_calendar | 2027 | {"unknown_no_applied_reviewed_annual_source": 365} |
| aadt_vintage | 2027 | {"2025": 365} |
| weather_daily | all | {"rows": 74460, "rows_guard_ok": 74460, "rows_rain_complete_and_guard_ok": 74335, "rows_temp_complete_and_guard_ok": 74460, "rows_guard_failed": 0, "issue_minus_latest_bound_hours_min": 18.0, "issue_minus_latest_bound_hours_median": 18.0, "issue_minus_latest_bound_hours_max": 19.0, "kind": "daily", "temp_out_of_plausible_range": 0} |
| weather_6h | all | {"rows": 297840, "rows_guard_ok": 297840, "rows_rain_complete_and_guard_ok": 297690, "rows_temp_complete_and_guard_ok": 297840, "rows_guard_failed": 0, "issue_minus_latest_bound_hours_min": 18.0, "issue_minus_latest_bound_hours_median": 27.0, "issue_minus_latest_bound_hours_max": 36.0, "kind": "6h", "temp_out_of_plausible_range": 0} |
| aadt_stations | all | {"rows": 16296, "by_row_class": {"station": 16296}, "station_rows_identity_nonstandard": 0, "station_rows_used": 16296, "groups": 12714, "vintages": [{"survey_year_ce": 2020, "available_from_proxy_utc": "2024-06-01T07:41:10.140471+00:00", "nunique": 1}, {"survey_year_ce": 2021, "available_from_proxy_utc": "2022-03-25T06:10:50.811162+00:00", "nunique": 1}, {"survey_year_ce": 2022, "available_from_proxy_utc": "2024-06-01T07:48:05.556631+00:00", "nunique": 1}, {"survey_year_ce": 2023, "available_from_proxy_utc": "2025-05-30T06:56:57.278942+00:00", "nunique": 1}, {"survey_year_ce": 2024, "available_from_proxy_utc": "2025-05-30T07:05:03.742919+00:00", "nunique": 1}, {"survey_year_ce": 2025, "available_from_proxy_utc": "2026-01-21T04:28:53.557666+00:00", "nunique": 1}]} |

## 7. Negative controls การรั่วไหล
| control | rejected |
| --- | --- |
| nb10_traffic_future_or_same_year_vintage | True |
| nb10_bank_holiday_late_announcement | True |
| nb10_bank_holiday_removal_after_issue_not_applied_early | True |
| nb10_unknown_calendar_not_ordinary_day | True |
| nb10_weather_hour_after_issue | True |
| nb10_weather_09_guard_tampered_true | True |
| nb10_allowlist_rejects_accident_type | True |
| nb10_allowlist_rejects_y_recorded_count | True |
| nb10_allowlist_rejects_training_eligible | True |
| nb10_allowlist_rejects_event_uid | True |
| nb10_allowlist_rejects_target_date | True |
| nb10_allowlist_rejects_wx_rain_missing | True |
| nb10_allowlist_rejects_deaths | True |
| allowlist_rejects_segment_id | True |
| allowlist_rejects_oid | True |
| allowlist_rejects_piece | True |
| allowlist_rejects_province_code | True |
| allowlist_rejects_aadt_n_station_rows | True |
| allowlist_rejects_aadt_vintage_survey_year_ce | True |
| allowlist_rejects_bank_calendar_known_asof | True |
| allowlist_rejects_y_count | True |
| allowlist_rejects_event_lat | True |
| allowlist_rejects_wx_rain_reason | True |
| allowlist_rejects_beyond_evaluated_period | True |
| allowlist_rejects_split | True |
| aadt_future_publication_or_same_year | True |
| aadt_prior_year_after_publication_used | True |
| request_label_field | True |
| request_unknown_segment | True |
| request_date_out_of_range | True |
| request_invalid_block | True |
| request_invalid_unit | True |

## 8. Parity ของ feature builder (in-memory = reload context = CSV round-trip)
| unit | rows | beyond_evaluated_rows | memory_equals_reloaded_context | memory_equals_csv_round_trip | permuted_requests_permute_rows | base_variant_is_prefix_subset | columns | nan_cells |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| daily | 2000 | 200 | True | True | True | True | 38 | 4168 |
| 6h | 2000 | 200 | True | True | True | True | 41 | 6258 |

## 9. คำสั่งรัน
- `.venv/bin/python backend/scripts/run_spatial_preparation.py --output-dir backend/rerun-spatial-prep-<id>`
- output root ของรันนี้: `/Users/earthnaja/Documents/GitHub/Work - Earth/Project Work/Source Code/RoadAware/backend/rerun-spatial-prep-national-001`

## 10. Checks
| check | status |
| --- | --- |
| every pinned input equals its manager pin and producer-manifest hash | pass |
| calendar/festival/season/issue/weather-buffer policy identical to the accepted notebook-10 config (no changed as-of rules) | pass |
| 2000 m GeoJSON feature ids equal the 2000 m inventory ids (stable 18 IDs, no re-segmentation) | pass |
| every 2000 m inventory segment is either in the universe or explicitly unsupported | pass |
| ADM1 registered before the join: 77 valid unrepaired polygons, unique ISO/ID, ISO <-> province_points mapping consistent | pass |
| universe segment ids unique and equal to the geometry predicate (zero-record segments included) | pass |
| one selection category per retained record (selected + every exclusion == retained) | pass |
| selected records are primary 50 m matched AND assigned; 100 m-only matches never selected | pass |
| every label year has selected records (a missing year fails closed, never a zero-filled year) | pass |
| sparse counts: daily_keys_unique | pass |
| sparse counts: block_keys_unique | pass |
| sparse counts: counts_integer_ge_1 | pass |
| sparse counts: daily_equals_sum_of_blocks | pass |
| sparse counts: daily_total_equals_selected | pass |
| sparse counts: block_total_equals_selected | pass |
| virtual population: rows == segments x dates (x blocks), count sum == selected records, batches <= limit | pass |
| AADT vintage strictly prior to the target year and available by the issue time (no future/current-year backfill) | pass |
| bank holiday is NaN exactly when reviewed coverage is unknown at issue (never an ordinary day) | pass |
| every leakage / invalid-request negative control is rejected by the production functions | pass |
| reference parity daily: same builder, reload and CSV round-trip identical, order preserved, no multiplication | pass |
| reference parity 6h: same builder, reload and CSV round-trip identical, order preserved, no multiplication | pass |
| protected inputs/outputs unchanged (sha256 before == after) | pass |
| source notebook and config unchanged during the run | pass |

## 11. ข้อจำกัด
- label = SELECTED+LINKED retained MOT records (status_50m matched AND segment assigned) per segment x local day / 6 h block; a zero is exact only inside this conditional target, never zero real accidents or complete reporting
- unknown / unmatched / unassigned / outside-envelope / unsupported-segment records are audited separately and never allocated as zero events
- current road snapshot applied retrospectively; historical topology, control sections and event datum are unverified
- geoBoundaries ADM1 (OSM-derived, year represented 2017, ODbL) is not a current official boundary; ambiguous/unmapped midpoints have no province context
- weather = coarse province representative-point JMA GSM previous_day2 archive (nominal issue bound + 6 h buffer); not road weather; historical delivery unverified
- AADT = DOH annual survey-point proxy by current route/control section from the newest prior vintage with catalog proxy availability <= issue; not live traffic or segment exposure
- bank calendar = reviewed BOT records as of issue; unknown coverage is NaN, never an ordinary day; bank holiday != public holiday
- dates 2024-2025 are previously seen diagnostics; 2026-2027 are beyond the evaluated period (features only, no labels)
- preparation only: no model was fitted, no score, threshold or risk colour exists

ยังไม่มีการฝึกโมเดล ไม่มี negative sampling ไม่มีคะแนน ไม่มีเกณฑ์สี; การผ่าน check ไม่ใช่การยอมรับผลิตภัณฑ์
