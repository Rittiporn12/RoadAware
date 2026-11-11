# Notebook 19 — เตรียมข้อมูล spatial CountRegression (ไม่ใช่โมเดล ไม่ใช่การพยากรณ์)

สถานะ: **complete (preparation only)** · เวอร์ชัน spatial_preparation_v3.0 · snapshot rc31f3d87fc7

## 1. ขอบเขตเป้าหมาย (target)
y = number of retained 2021-25 MOT records with status_50m == matched AND segment_status == assigned to a universe segment, per segment x local day (or 6 h block). Zero means zero such SELECTED+LINKED records in the defined conditional population, NOT zero real accidents or complete reporting. Unknown / unmatched / unassigned / outside records are audited separately and never allocated as zero events.

## 2. จักรวาล segment (กำหนดจาก geometry เท่านั้น ก่อนมีคะแนนโมเดลใด)
geometry-only predicate fixed before any model score: source DOH AND geometry route_status standard AND 2000 m resolution AND projected length >= 500 m AND present in the accepted (safe-geometry) 18 inventory. Every qualifying segment is included whether or not it has records. Stable 18 segment IDs, never re-segmented. DRR/EXAT/nonstandard routes/short tails are unsupported (no prediction, never a fake zero).

ค่าที่วัดจริงในรันนี้ (preflight ของผู้จัดการเป็นบริบทเท่านั้น: {'segments': 3105, 'routes': 218, 'projected_km': 5900.233, 'note': 'manager geometry preflight: reported beside the actual counts only, never used as a guard'}):
| segments | routes | projected_km | geodesic_km | utm_over_geodesic_min | utm_over_geodesic_max | short_final_segments | piece_overlap_segments | piece_duplicate_segments | chord_zero_guard_segments | aadt_identity_ok | preflight_segments_context | preflight_routes_context | preflight_km_context |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3105 | 218 | 5900.233 | 5899.307 | 0.9998060745886163 | 1.0008970517882472 | 403 | 0 | 0 | 0 | 3105 | 3105 | 218 | 5900.233 |

segment ที่ไม่รองรับ (ไม่มีการทำนาย ไม่ใช่ศูนย์):
| source_id | unsupported_reason | segments | km |
| --- | --- | --- | --- |
| doh_highway | short_lt_min_length | 196 | 47.431 |
| drr_rural | unsupported_source_drr_rural | 3247 | 5948.55 |
| exat_expressway | unsupported_source_exat_expressway | 619 | 309.788 |

## 3. การคัดเลือกบันทึก (reconciled ทุกแถว)
| ce_year | split | selection | records |
| --- | --- | --- | --- |
| 2021 | train | matched_50m_no_segment_assignment | 20 |
| 2021 | train | outside_pilot_envelope | 14797 |
| 2021 | train | selected | 4512 |
| 2021 | train | unknown_status_50m_ambiguous_multiple | 14 |
| 2021 | train | unknown_status_50m_ambiguous_unsafe_geometry | 5 |
| 2021 | train | unknown_status_50m_identity_unresolved | 124 |
| 2021 | train | unknown_status_50m_low_precision_unsuitable | 4 |
| 2021 | train | unknown_status_50m_route_not_in_snapshot | 7 |
| 2021 | train | unknown_status_50m_route_special_unverified | 124 |
| 2021 | train | unknown_status_50m_too_far | 122 |
| 2021 | train | unsupported_segment_short_lt_min_length | 20 |
| 2021 | train | unsupported_segment_unsupported_source_drr_rural | 247 |
| 2022 | train | matched_50m_no_segment_assignment | 24 |
| 2022 | train | outside_pilot_envelope | 14854 |
| 2022 | train | selected | 4908 |
| 2022 | train | unknown_status_50m_ambiguous_multiple | 32 |
| 2022 | train | unknown_status_50m_ambiguous_unsafe_geometry | 3 |
| 2022 | train | unknown_status_50m_identity_unresolved | 181 |
| 2022 | train | unknown_status_50m_route_not_in_snapshot | 7 |
| 2022 | train | unknown_status_50m_route_special_unverified | 163 |
| 2022 | train | unknown_status_50m_too_far | 104 |
| 2022 | train | unsupported_segment_short_lt_min_length | 32 |
| 2022 | train | unsupported_segment_unsupported_source_drr_rural | 184 |
| 2023 | train | matched_50m_no_segment_assignment | 26 |
| 2023 | train | outside_pilot_envelope | 14417 |
| 2023 | train | selected | 5793 |
| 2023 | train | unknown_status_50m_ambiguous_multiple | 57 |
| 2023 | train | unknown_status_50m_ambiguous_unsafe_geometry | 6 |
| 2023 | train | unknown_status_50m_low_precision_unsuitable | 1 |
| 2023 | train | unknown_status_50m_too_far | 148 |
| 2023 | train | unsupported_segment_short_lt_min_length | 42 |
| 2024 | seen_diagnostic | matched_50m_no_segment_assignment | 20 |
| 2024 | seen_diagnostic | outside_pilot_envelope | 14852 |
| 2024 | seen_diagnostic | selected | 6015 |
| 2024 | seen_diagnostic | unknown_status_50m_ambiguous_multiple | 67 |
| 2024 | seen_diagnostic | unknown_status_50m_ambiguous_unsafe_geometry | 7 |
| 2024 | seen_diagnostic | unknown_status_50m_identity_unresolved | 355 |
| 2024 | seen_diagnostic | unknown_status_50m_low_precision_unsuitable | 3 |
| 2024 | seen_diagnostic | unknown_status_50m_route_not_in_snapshot | 4 |
| 2024 | seen_diagnostic | unknown_status_50m_route_special_unverified | 104 |
| 2024 | seen_diagnostic | unknown_status_50m_too_far | 180 |
| 2024 | seen_diagnostic | unsupported_segment_short_lt_min_length | 60 |
| 2024 | seen_diagnostic | unsupported_segment_unsupported_source_drr_rural | 121 |
| 2025 | seen_diagnostic | matched_50m_no_segment_assignment | 33 |
| 2025 | seen_diagnostic | outside_pilot_envelope | 16299 |
| 2025 | seen_diagnostic | selected | 6231 |
| 2025 | seen_diagnostic | unknown_status_50m_ambiguous_multiple | 66 |
| 2025 | seen_diagnostic | unknown_status_50m_ambiguous_unsafe_geometry | 8 |
| 2025 | seen_diagnostic | unknown_status_50m_identity_unresolved | 410 |
| 2025 | seen_diagnostic | unknown_status_50m_low_precision_unsuitable | 5 |
| 2025 | seen_diagnostic | unknown_status_50m_route_missing | 2 |
| 2025 | seen_diagnostic | unknown_status_50m_route_not_in_snapshot | 1 |
| 2025 | seen_diagnostic | unknown_status_50m_route_special_unverified | 157 |
| 2025 | seen_diagnostic | unknown_status_50m_too_far | 142 |
| 2025 | seen_diagnostic | unsupported_segment_short_lt_min_length | 43 |
| 2025 | seen_diagnostic | unsupported_segment_unsupported_source_drr_rural | 145 |

## 4. จำนวนนับ sparse และประชากรเสมือน
| unit | split | date_start | date_end | segments | days | population_cells | positive_cells | selected_records | zero_cells_conditional | max_cell_count | segments_with_any_record | mean_count_per_cell |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| daily | train | 2021-01-01 | 2023-12-31 | 3105 | 1095 | 3399975 | 14448 | 15213 | 3385527 | 4 | 1928 | 0.004474444665034302 |
| daily | seen_2024 | 2024-01-01 | 2024-12-31 | 3105 | 366 | 1136430 | 5699 | 6015 | 1130731 | 6 | 1320 | 0.005292890895171722 |
| daily | seen_2025 | 2025-01-01 | 2025-12-31 | 3105 | 365 | 1133325 | 5917 | 6231 | 1127408 | 6 | 1391 | 0.005497981602805903 |
| 6h | train | 2021-01-01 | 2023-12-31 | 3105 | 1095 | 13599900 | 14805 | 15213 | 13585095 | 4 | 1928 | 0.0011186111662585755 |
| 6h | seen_2024 | 2024-01-01 | 2024-12-31 | 3105 | 366 | 4545720 | 5868 | 6015 | 4539852 | 6 | 1320 | 0.0013232227237929305 |
| 6h | seen_2025 | 2025-01-01 | 2025-12-31 | 3105 | 365 | 4533300 | 6099 | 6231 | 4527201 | 6 | 1391 | 0.0013744954007014758 |

| unit | rows | batches | max_batch_rows | count_sum | positive_cells | first_key | last_key |
| --- | --- | --- | --- | --- | --- | --- | --- |
| daily | 5669730 | 57 | 100000 | 27459 | 26064 | {"segment_id": "rsv1-rc31f3d87fc7:doh:1036:p0:c0:r2000:00000", "target_date": "2021-01-01"} | {"segment_id": "rsv1-rc31f3d87fc7:doh:985:p0:c0:r2000:00005", "target_date": "2025-12-31"} |
| 6h | 22678920 | 227 | 100000 | 27459 | 26772 | {"segment_id": "rsv1-rc31f3d87fc7:doh:1036:p0:c0:r2000:00000", "target_date": "2021-01-01", "time_block": "00-06"} | {"segment_id": "rsv1-rc31f3d87fc7:doh:985:p0:c0:r2000:00005", "target_date": "2025-12-31", "time_block": "18-24"} |

## 5. จังหวัดจากจุดกึ่งกลาง segment (geoBoundaries 2017/OSM ไม่ใช่ขอบเขตทางการปัจจุบัน)
| province_join_status | n_covering_polygons | segments | km |
| --- | --- | --- | --- |
| mapped | 1 | 3105 | 5900.233 |

ความสอดคล้องจังหวัดของเหตุกับจังหวัดของ segment (เชิงพรรณนาเท่านั้น):
| split | agreement | selected_records |
| --- | --- | --- |
| train | same_province | 14945 |
| seen_diagnostic | same_province | 12006 |
| train | different_province | 268 |
| seen_diagnostic | different_province | 240 |

## 6. ความครอบคลุมของ feature บริบท และ as-of
| scope | unit | year | rows | feature | non_missing | share |
| --- | --- | --- | --- | --- | --- | --- |
| population_2021_2025 | daily | 2021 | 1133325 | bank_holiday_asof | 1111590 | 0.9808219178082191 |
| population_2021_2025 | daily | 2021 | 1133325 | wx_rain_sum_mm_d2 | 1133325 | 1.0 |
| population_2021_2025 | daily | 2021 | 1133325 | wx_temp_mean_c_d2 | 1133325 | 1.0 |
| population_2021_2025 | daily | 2021 | 1133325 | aadt_mean_total | 0 | 0.0 |
| population_2021_2025 | daily | 2021 | 1133325 | aadt_median_total | 0 | 0.0 |
| population_2021_2025 | daily | 2021 | 1133325 | aadt_mean_heavy_share_pct | 0 | 0.0 |
| population_2021_2025 | daily | 2022 | 1133325 | bank_holiday_asof | 1133325 | 1.0 |
| population_2021_2025 | daily | 2022 | 1133325 | wx_rain_sum_mm_d2 | 1133186 | 0.9998773520393532 |
| population_2021_2025 | daily | 2022 | 1133325 | wx_temp_mean_c_d2 | 1133325 | 1.0 |
| population_2021_2025 | daily | 2022 | 1133325 | aadt_mean_total | 680863 | 0.6007658879844705 |
| population_2021_2025 | daily | 2022 | 1133325 | aadt_median_total | 680863 | 0.6007658879844705 |
| population_2021_2025 | daily | 2022 | 1133325 | aadt_mean_heavy_share_pct | 680863 | 0.6007658879844705 |
| population_2021_2025 | daily | 2023 | 1133325 | bank_holiday_asof | 1133325 | 1.0 |
| population_2021_2025 | daily | 2023 | 1133325 | wx_rain_sum_mm_d2 | 1090355 | 0.9620850153309951 |
| population_2021_2025 | daily | 2023 | 1133325 | wx_temp_mean_c_d2 | 1094270 | 0.9655394524959743 |
| population_2021_2025 | daily | 2023 | 1133325 | aadt_mean_total | 884395 | 0.780354267310789 |
| population_2021_2025 | daily | 2023 | 1133325 | aadt_median_total | 884395 | 0.780354267310789 |
| population_2021_2025 | daily | 2023 | 1133325 | aadt_mean_heavy_share_pct | 884395 | 0.780354267310789 |
| population_2021_2025 | daily | 2024 | 1136430 | bank_holiday_asof | 1136430 | 1.0 |
| population_2021_2025 | daily | 2024 | 1136430 | wx_rain_sum_mm_d2 | 0 | 0.0 |
| population_2021_2025 | daily | 2024 | 1136430 | wx_temp_mean_c_d2 | 0 | 0.0 |
| population_2021_2025 | daily | 2024 | 1136430 | aadt_mean_total | 895338 | 0.7878514294765185 |
| population_2021_2025 | daily | 2024 | 1136430 | aadt_median_total | 895338 | 0.7878514294765185 |
| population_2021_2025 | daily | 2024 | 1136430 | aadt_mean_heavy_share_pct | 895338 | 0.7878514294765185 |
| population_2021_2025 | daily | 2025 | 1133325 | bank_holiday_asof | 1133325 | 1.0 |
| population_2021_2025 | daily | 2025 | 1133325 | wx_rain_sum_mm_d2 | 0 | 0.0 |
| population_2021_2025 | daily | 2025 | 1133325 | wx_temp_mean_c_d2 | 0 | 0.0 |
| population_2021_2025 | daily | 2025 | 1133325 | aadt_mean_total | 892975 | 0.7879249112125825 |
| population_2021_2025 | daily | 2025 | 1133325 | aadt_median_total | 892975 | 0.7879249112125825 |
| population_2021_2025 | daily | 2025 | 1133325 | aadt_mean_heavy_share_pct | 892975 | 0.7879249112125825 |
| population_2021_2025 | 6h | 2021 | 4533300 | bank_holiday_asof | 4446360 | 0.9808219178082191 |
| population_2021_2025 | 6h | 2021 | 4533300 | wx_rain_sum_mm_d2 | 4533300 | 1.0 |
| population_2021_2025 | 6h | 2021 | 4533300 | wx_temp_mean_c_d2 | 4533300 | 1.0 |
| population_2021_2025 | 6h | 2021 | 4533300 | wx_block_rain_sum_mm_d2 | 4533300 | 1.0 |
| population_2021_2025 | 6h | 2021 | 4533300 | wx_block_temp_mean_c_d2 | 4533300 | 1.0 |
| population_2021_2025 | 6h | 2021 | 4533300 | aadt_mean_total | 0 | 0.0 |
| population_2021_2025 | 6h | 2021 | 4533300 | aadt_median_total | 0 | 0.0 |
| population_2021_2025 | 6h | 2021 | 4533300 | aadt_mean_heavy_share_pct | 0 | 0.0 |
| population_2021_2025 | 6h | 2022 | 4533300 | bank_holiday_asof | 4533300 | 1.0 |
| population_2021_2025 | 6h | 2022 | 4533300 | wx_rain_sum_mm_d2 | 4532744 | 0.9998773520393532 |
| population_2021_2025 | 6h | 2022 | 4533300 | wx_temp_mean_c_d2 | 4533300 | 1.0 |
| population_2021_2025 | 6h | 2022 | 4533300 | wx_block_rain_sum_mm_d2 | 4533129 | 0.9999622791344054 |
| population_2021_2025 | 6h | 2022 | 4533300 | wx_block_temp_mean_c_d2 | 4533300 | 1.0 |
| population_2021_2025 | 6h | 2022 | 4533300 | aadt_mean_total | 2723452 | 0.6007658879844705 |
| population_2021_2025 | 6h | 2022 | 4533300 | aadt_median_total | 2723452 | 0.6007658879844705 |
| population_2021_2025 | 6h | 2022 | 4533300 | aadt_mean_heavy_share_pct | 2723452 | 0.6007658879844705 |
| population_2021_2025 | 6h | 2023 | 4533300 | bank_holiday_asof | 4533300 | 1.0 |
| population_2021_2025 | 6h | 2023 | 4533300 | wx_rain_sum_mm_d2 | 4361420 | 0.9620850153309951 |
| population_2021_2025 | 6h | 2023 | 4533300 | wx_temp_mean_c_d2 | 4377080 | 0.9655394524959743 |
| population_2021_2025 | 6h | 2023 | 4533300 | wx_block_rain_sum_mm_d2 | 4372404 | 0.9645079743233406 |
| population_2021_2025 | 6h | 2023 | 4533300 | wx_block_temp_mean_c_d2 | 4377080 | 0.9655394524959743 |
| population_2021_2025 | 6h | 2023 | 4533300 | aadt_mean_total | 3537580 | 0.780354267310789 |
| population_2021_2025 | 6h | 2023 | 4533300 | aadt_median_total | 3537580 | 0.780354267310789 |
| population_2021_2025 | 6h | 2023 | 4533300 | aadt_mean_heavy_share_pct | 3537580 | 0.780354267310789 |
| population_2021_2025 | 6h | 2024 | 4545720 | bank_holiday_asof | 4545720 | 1.0 |
| population_2021_2025 | 6h | 2024 | 4545720 | wx_rain_sum_mm_d2 | 0 | 0.0 |
| population_2021_2025 | 6h | 2024 | 4545720 | wx_temp_mean_c_d2 | 0 | 0.0 |
| population_2021_2025 | 6h | 2024 | 4545720 | wx_block_rain_sum_mm_d2 | 0 | 0.0 |
| population_2021_2025 | 6h | 2024 | 4545720 | wx_block_temp_mean_c_d2 | 0 | 0.0 |
| population_2021_2025 | 6h | 2024 | 4545720 | aadt_mean_total | 3581352 | 0.7878514294765185 |

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
| daily | 2000 | 200 | True | True | True | True | 38 | 4392 |
| 6h | 2000 | 200 | True | True | True | True | 41 | 6351 |

## 9. คำสั่งรัน
- `.venv/bin/python backend/scripts/run_spatial_preparation.py --output-dir backend/rerun-spatial-prep-<id>`
- output root ของรันนี้: `/Users/earthnaja/Documents/GitHub/Work - Earth/Project Work/Source Code/RoadAware/backend/rerun-spatial-prep-015-002`

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
