# RoadAware Model Gate: เนื้อหานำเสนอ 5 หัวข้อ (เนื้อหา/asset ไม่ใช่ไฟล์ PowerPoint)

สร้างอัตโนมัติจากผลจริงของรอบนี้ (notebook 21) บน OOF 2022-23 (ใช้เลือก) และ 2024/25 (previously seen diagnostics ไม่ใช่ holdout) ของ notebook 20 ที่ตรวจรับแล้ว; ไม่ฝึกใหม่ ไม่เลือกใหม่. **2026: รอการตรวจข้อมูลและการประเมินแยกต่างหาก ไม่มีคะแนน 2026 ในเอกสารนี้**

ลำดับสไลด์: (1) target และพื้นที่ -> (2) baselines -> (3) candidates/features -> (4) metrics และ gate -> (5) ผล OOF -> (6) folds / 2024-25 / transfer -> (7) error: totals, calibration, floor -> (8) กลุ่มที่ baseline ดีกว่า -> (9) capture และสี -> (10) เหตุผลเลือกและข้อจำกัด

## Baseline และ Candidate Models

### สไลด์ 1: target และขอบเขตพื้นที่ที่รองรับ

y = count of SELECTED+LINKED retained MOT database records (status_50m == matched AND segment_status == assigned) per qualified DOH segment x local day (daily) or x 6 h block. Zero means zero such recorded+linked records, NOT zero physical accidents. Predictions are expected recorded counts, not per-vehicle or per-person probabilities.

- Universe: 3,105 ช่วงถนน DOH (5,900.2 km จาก geom_length_m); OOF 2022-23: daily 2,266,650 cells / 10,701 records; 6h 9,066,600 cells / 10,701 records

ตัวอย่างพื้นที่ที่รองรับ (province ของจุดกึ่งกลาง segment ตาม geometry ปัจจุบัน ไม่ใช่การจัดจังหวัดจากเหตุการณ์; ชื่อจาก province_points.csv ตาม province_code):

| province_code | จังหวัด | Province | segments | OOF records (daily) |
|---|---|---|---|---|
| 16 | ลพบุรี | Lop Buri | 420 | 428 |
| 30 | นครราชสีมา | Nakhon Ratchasima | 377 | 977 |
| 19 | สระบุรี | Saraburi | 335 | 472 |
| 14 | พระนครศรีอยุธยา | Phra Nakhon Si Ayutthaya | 306 | 656 |
| 25 | ปราจีนบุรี | Prachin Buri | 246 | 456 |
| 24 | ฉะเชิงเทรา | Chachoengsao | 224 | 661 |
| 10 | กรุงเทพมหานคร | Bangkok | 219 | 3,444 |
| 13 | ปทุมธานี | Pathum Thani | 199 | 862 |
| 11 | สมุทรปราการ | Samut Prakan | 127 | 780 |
| 15 | อ่างทอง | Ang Thong | 127 | 403 |
| 17 | สิงห์บุรี | Sing Buri | 124 | 246 |
| 26 | นครนายก | Nakhon Nayok | 113 | 129 |
| 12 | นนทบุรี | Nonthaburi | 86 | 192 |
| 73 | นครปฐม | Nakhon Pathom | 56 | 101 |
| 60 | นครสวรรค์ | Nakhon Sawan | 44 | 127 |
| 18 | ชัยนาท | Chai Nat | 35 | 45 |
| 74 | สมุทรสาคร | Samut Sakhon | 32 | 659 |
| 72 | สุพรรณบุรี | Suphan Buri | 19 | 34 |
| 20 | ชลบุรี | Chon Buri | 14 | 29 |
| 36 | ชัยภูมิ | Chaiyaphum | 2 | 0 |

- segment นอก universe / ไม่รองรับ / prediction หรือความยาวไม่ถูกต้อง = สีเทา unavailable; ไม่สร้าง prediction 0 ทดแทน

> ประเด็นพูด: เราทำนายค่าคาดหมายจำนวนรายการที่ฐานข้อมูลคัดเลือกและเชื่อมถนนได้ ไม่ใช่โอกาสชนรายบุคคล; ศูนย์ = ไม่มีบันทึก ไม่ใช่ไม่มีอุบัติเหตุ

### สไลด์ 2: Baselines (ตัวหาร = ปฏิทิน training เต็ม ไม่ใช่ training sample)

b = time block (daily: the single block); T_b = number of training target dates whose block b ends <= training cutoff (exact full calendar, every universe segment counted, NOT sampled rows); C = training record counts from the sparse index; L_s = segment projected length km; S_train = training segment set

| baseline | นิยาม | daily OOF deviance | daily OOF MAE | 6h OOF deviance | 6h OOF MAE |
|---|---|---|---|---|---|
| `zero` (ineligible) | 0 (diagnostic only, never eligible) | 0.252193 | 0.004721 | 0.062959 | 0.001180 |
| `global_mean` | C_b / (|S_train| * T_b) | 0.051381 | 0.008810 | 0.015997 | 0.002209 |
| `global_length_rate` | rate_g_b = C_b / (sum_{s in S_train} L_s * T_b) records per km per cell; prediction rate_g_b * L_s | 0.051149 | 0.008809 | 0.015939 | 0.002209 |
| `route_length_rate` | rate_r_b = C_rb / (sum_{s in S_train, route r} L_s * T_b) (may be 0 when the route has no training records: no pseudocounts); prediction rate_r_b * L_s; route absent from S_train -> global_length_rate | 0.042780 | 0.008670 | 0.014539 | 0.002199 |
| `segment_mean_k30` | (C_sb + k * P_sb) / (N_sb + k), N_sb = T_b for training segments, 0 for unseen segments (-> exactly P_sb) with k = 30 | 0.042012 | 0.008565 | 0.015210 | 0.002191 |
| `segment_mean_k180` | (C_sb + k * P_sb) / (N_sb + k), N_sb = T_b for training segments, 0 for unseen segments (-> exactly P_sb) with k = 180 | 0.041036 | 0.008585 | 0.014463 | 0.002193 |
| `segment_mean_k365` | (C_sb + k * P_sb) / (N_sb + k), N_sb = T_b for training segments, 0 for unseen segments (-> exactly P_sb) with k = 365 | 0.040956 | 0.008601 | 0.014299 | 0.002194 |
| `segment_weekday_k10` | (C_s,wd,b + 10 * M30_sb) / (N_wd,b + 10), N_wd,b = number of training dates with that weekday for block b (0 for unseen segments), M30 = segment_mean_k30 | 0.047900 | 0.008547 | 0.017855 | 0.002189 |
| `segment_month_k30` | (C_s,m,b + 30 * M30_sb) / (N_m,b + 30), N_m,b = training dates in calendar month m for block b | 0.044863 | 0.008523 | 0.016404 | 0.002182 |
| `recent90_segment` | C_sb(last 90 calendar days ending at the last eligible training date of block b, clipped at train_start) / N_recent_b; segment_mean_k30 when N_recent_b == 0 or the segment is unseen | 0.106602 | 0.008728 | 0.041179 | 0.002250 |

- strongest nonzero baseline ตาม pooled OOF deviance: daily `segment_mean_k365`; 6h `segment_mean_k365`
- parent: P_sb = route_length_rate prediction for s (global_length_rate when the route is unseen); no floor is applied to predictions; zero predictions are allowed (route/global rate 0) and are floored at 1e-12 ONLY inside the Poisson deviance metric; negative means are refused

> ประเด็นพูด: ข้อมูล sparse มาก baseline ที่ shrink ไปหา parent ของสายทางจึงแข็งแรง; zero baseline เป็นตัวเปรียบเทียบเชิงวินิจฉัยเท่านั้น

### สไลด์ 3: Candidate models, policies และ features

| config | family | locked params |
|---|---|---|
| `poisson_a1e-05` | poisson | `{"alpha": 1e-05, "max_iter": 1000, "tol": 1e-06}` |
| `poisson_a1e-04` | poisson | `{"alpha": 0.0001, "max_iter": 1000, "tol": 1e-06}` |
| `rf_poisson_fixed` | random_forest | `{"criterion": "poisson", "max_depth": 16, "max_features": 0.8, "max_leaf_nodes": 128, "min_samples_leaf": 100, "n_estimators": 80, "n_jobs": 2, "random_state": 42}` |
| `hgb_poisson_fixed` | hist_gradient_boosting | `{"early_stopping": false, "l2_regularization": 5.0, "learning_rate": 0.05, "loss": "poisson", "max_bins": 255, "max_iter": 160, "max_leaf_nodes": 15, "min_samples_leaf": 100, "random_state": 42}` |

- poisson: Poisson regression (GLM, log link): log μ = β0 + Σ βj·xj; ผลของแต่ละ feature เป็นแบบทวีคูณต่อค่าคาดหมาย; alpha = L2 penalty; preprocessing: OneHotEncoder(handle_unknown='ignore') on categoricals; numeric SimpleImputer(median, keep_empty_features=True) + StandardScaler; all fitted on the fold training sample only
- random_forest: Random Forest (criterion=poisson): μ = ค่าเฉลี่ยของหลายต้นไม้ที่แบ่งกลุ่มแบบไม่เชิงเส้น; แต่ละต้นใช้ bootstrap ของแถวและสุ่ม feature; preprocessing: OneHotEncoder(handle_unknown='ignore') on categoricals; numeric SimpleImputer(median, keep_empty_features=True); training sample only
- hist_gradient_boosting: Histogram Gradient Boosting (loss=poisson): log μ = ผลรวมของต้นไม้ที่เพิ่มทีละต้นเพื่อลด Poisson loss ที่เหลือ; learning_rate คุมขนาดก้าว; preprocessing: OrdinalEncoder(handle_unknown='use_encoded_value', unknown_value=NaN, encoded_missing_value=NaN) on categoricals with categorical mask; numeric NaN native
- policy `core`: calendar_geometry fit (deployment eligible)
- policy `routed_context`: context fit iff ALL of weather daily (+ weather block for 6h) and the 3 AADT features are finite, else the SAME config calendar_geometry fit (deployment eligible; requires both component fits in every fold)
- policy `context`: pure calendar_geometry_context fit (ablation only, never eligible) (ไม่ eligible)
- daily core features (33): route_code, geom_mid_x_m, geom_mid_y_m, geom_mid_lon, geom_mid_lat, geom_length_m, geom_log_length_m, geom_bearing_sin, geom_bearing_cos, geom_straightness, geom_turning_rad_per_km, day_of_week, month, day_of_month, is_weekend, doy_sin, doy_cos, fest_songkran_dist, fest_songkran_in, fest_songkran_pre_1_3, fest_songkran_pre_4_7, fest_songkran_post_1_3, fest_songkran_post_4_7, fest_new_year_dist, fest_new_year_in, fest_new_year_pre_1_3, fest_new_year_pre_4_7, fest_new_year_post_1_3, fest_new_year_post_4_7, season_hot, season_wet, season_cool, bank_holiday_asof
- daily context เพิ่ม (5): wx_rain_sum_mm_d2, wx_temp_mean_c_d2, aadt_mean_total, aadt_median_total, aadt_mean_heavy_share_pct; routed trigger (ต้องครบทุกค่า): wx_rain_sum_mm_d2, wx_temp_mean_c_d2, aadt_mean_total, aadt_median_total, aadt_mean_heavy_share_pct
- 6h core features (34): route_code, geom_mid_x_m, geom_mid_y_m, geom_mid_lon, geom_mid_lat, geom_length_m, geom_log_length_m, geom_bearing_sin, geom_bearing_cos, geom_straightness, geom_turning_rad_per_km, day_of_week, month, day_of_month, is_weekend, doy_sin, doy_cos, fest_songkran_dist, fest_songkran_in, fest_songkran_pre_1_3, fest_songkran_pre_4_7, fest_songkran_post_1_3, fest_songkran_post_4_7, fest_new_year_dist, fest_new_year_in, fest_new_year_pre_1_3, fest_new_year_pre_4_7, fest_new_year_post_1_3, fest_new_year_post_4_7, season_hot, season_wet, season_cool, bank_holiday_asof, time_block
- 6h context เพิ่ม (7): wx_rain_sum_mm_d2, wx_temp_mean_c_d2, wx_block_rain_sum_mm_d2, wx_block_temp_mean_c_d2, aadt_mean_total, aadt_median_total, aadt_mean_heavy_share_pct; routed trigger (ต้องครบทุกค่า): wx_rain_sum_mm_d2, wx_temp_mean_c_d2, wx_block_rain_sum_mm_d2, wx_block_temp_mean_c_d2, aadt_mean_total, aadt_median_total, aadt_mean_heavy_share_pct
- training sample: model training ONLY (never baselines, evaluation metrics, prevalence, calibration or colour cutoffs); weights positive=1.0, zero=Nzero / Nsampled
- ไม่มี segment_id / target / event coordinates / province เป็น predictor (allowlist ของ notebook 19/20); AADT = annual survey proxy ไม่ใช่ live congestion

> ประเด็นพูด: สามตระกูล Poisson/RF/HGB ใช้ config ที่ล็อกก่อนดูคะแนน; routed_context ใช้ context เมื่อ weather+AADT ครบ มิฉะนั้นใช้ core ของ config เดียวกัน

## Evaluation Metrics

### สไลด์ 4: นิยาม metric และ gate ที่ล็อก

- Mean Poisson deviance = (1/N) Σ 2[y·ln(y/m) − (y − m)], m = max(μ, 1e-12) เฉพาะใน metric (y·ln = 0 เมื่อ y = 0); ยิ่งต่ำยิ่งดี ไม่ใช่ accuracy
- MAE = (1/N) Σ|μ − y|; RMSE = √((1/N) Σ(μ − y)²) หน่วย records ต่อ segment-period; bias = (1/N) Σ(μ − y) (ลบ = ทำนายต่ำ)
- WAPE = Σ|μ − y| / Σy; กลุ่มที่ Σy = 0 → undefined (ไม่ใช่ 0 หรือ ∞)
- pooled OOF = ผลรวม loss / จำนวน cells ทั้งหมด (row-weighted ไม่เฉลี่ย fold เท่ากัน); daily และ 6h คนละ horizon/population ห้ามเทียบคะแนนข้ามหน่วย
- folds: 2022H1 (2022-01-01..2022-06-30), 2022H2 (2022-07-01..2022-12-31), 2023H1 (2023-01-01..2023-06-30), 2023H2 (2023-07-01..2023-12-31); label latency 30 วัน (30-day label availability embargo is a RESEARCH ASSUMPTION, not a verified publication delay)
- Gate: deviance ลด ≥ 1.0%, MAE ratio ≤ 1.02, ชนะ deviance ≥ 3/4 folds; per unit: best deployment-eligible candidate policy by pooled OOF deviance vs strongest NONZERO baseline by pooled OOF deviance; recommend candidate only if relative reduction >= 1% AND MAE ratio <= 1.02 AND strictly lower deviance in >= 3/4 folds, otherwise the baseline. Frozen before any 2024/25 metric is computed.
- density สี = expected records / segment km ต่อ horizon เดียวกัน; cutoffs = P50/P80/P95 (type 7) ของ OOF ทั้งหมดแบบ unweighted; calibration = ผลรวม pred / ผลรวม actual ต่อ exposure (segment-km-periods)
- capture: stable sort by descending density, ties by ascending segment index; the boundary segment contributes the fraction of its length inside the budget; its actual records are allocated proportionally to that length fraction (disclosed assumption)
- 2024/25 ใช้หลังเลือกแล้วเป็น diagnostics เท่านั้น; 2026 จะไม่ใช้เปลี่ยน winner

> ประเด็นพูด: เลือกด้วย temporal OOF เท่านั้น ไม่มี random split; ค่า gate ถูกล็อกก่อนเห็นคะแนน

## Experiment Results

### สไลด์ 5: ผล OOF 2022-23 (ใช้เลือก)

**daily (per local day)** (n = 2,266,650 cells ต่อ method)

| method | kind | eligible | deviance | MAE | RMSE | deviance reduction vs strongest baseline |
|---|---|---|---|---|---|---|
| `hgb_poisson_fixed::context` | context | False | 0.039871 | 0.008719 | 0.071502 | +2.649% |
| `hgb_poisson_fixed::routed_context` | routed_context | True | 0.039898 | 0.008662 | 0.071496 | +2.583% |
| `rf_poisson_fixed::context` | context | False | 0.039946 | 0.008804 | 0.071464 | +2.466% |
| `rf_poisson_fixed::routed_context` | routed_context | True | 0.040064 | 0.008757 | 0.071496 | +2.177% |
| `hgb_poisson_fixed::core` | core | True | 0.040076 | 0.008624 | 0.071535 | +2.149% |
| `rf_poisson_fixed::core` | core | True | 0.040308 | 0.008658 | 0.071518 | +1.583% |
| `segment_mean_k365` | baseline | True | 0.040956 | 0.008601 | 0.071517 | +0.000% |
| `poisson_a1e-05::routed_context` | routed_context | True | 0.041921 | 0.008793 | 0.071887 | -2.355% |
| `poisson_a1e-05::context` | context | False | 0.041922 | 0.008779 | 0.071891 | -2.358% |
| `poisson_a1e-05::core` | core | True | 0.042171 | 0.008587 | 0.071928 | -2.968% |
| `poisson_a1e-04::context` | context | False | 0.043253 | 0.009049 | 0.071967 | -5.608% |
| `poisson_a1e-04::routed_context` | routed_context | True | 0.043301 | 0.009073 | 0.071965 | -5.725% |
| `poisson_a1e-04::core` | core | True | 0.043950 | 0.008638 | 0.072058 | -7.311% |

**6 h (per 6 h block)** (n = 9,066,600 cells ต่อ method)

| method | kind | eligible | deviance | MAE | RMSE | deviance reduction vs strongest baseline |
|---|---|---|---|---|---|---|
| `hgb_poisson_fixed::context` | context | False | 0.013113 | 0.002214 | 0.035220 | +8.291% |
| `hgb_poisson_fixed::routed_context` | routed_context | True | 0.013133 | 0.002203 | 0.035222 | +8.152% |
| `rf_poisson_fixed::context` | context | False | 0.013163 | 0.002230 | 0.035217 | +7.944% |
| `rf_poisson_fixed::routed_context` | routed_context | True | 0.013167 | 0.002224 | 0.035219 | +7.915% |
| `hgb_poisson_fixed::core` | core | True | 0.013170 | 0.002186 | 0.035226 | +7.893% |
| `rf_poisson_fixed::core` | core | True | 0.013219 | 0.002194 | 0.035222 | +7.552% |
| `poisson_a1e-05::context` | context | False | 0.013784 | 0.002275 | 0.035282 | +3.597% |
| `poisson_a1e-05::routed_context` | routed_context | True | 0.013787 | 0.002280 | 0.035281 | +3.578% |
| `poisson_a1e-05::core` | core | True | 0.013895 | 0.002186 | 0.035290 | +2.824% |
| `segment_mean_k365` | baseline | True | 0.014299 | 0.002194 | 0.035226 | +0.000% |
| `poisson_a1e-04::context` | context | False | 0.014301 | 0.002359 | 0.035300 | -0.017% |
| `poisson_a1e-04::routed_context` | routed_context | True | 0.014334 | 0.002370 | 0.035301 | -0.248% |
| `poisson_a1e-04::core` | core | True | 0.014666 | 0.002192 | 0.035325 | -2.571% |

| unit | selected | baseline | deviance reduction | MAE ratio | fold wins | all gates pass | baseline retained |
|---|---|---|---|---|---|---|---|
| daily | `hgb_poisson_fixed::routed_context` | `segment_mean_k365` | +2.583% | 1.007095 | 4/4 | True | False |
| 6h | `hgb_poisson_fixed::routed_context` | `segment_mean_k365` | +8.152% | 1.004063 | 4/4 | True | False |

- daily: paired 7-day block bootstrap (500 resamples) ช่วง +1.477% ถึง +3.712% — ok (exploratory, post-selection, not confirmatory)
- 6h: paired 7-day block bootstrap (500 resamples) ช่วง +6.755% ถึง +9.552% — ok (exploratory, post-selection, not confirmatory)

รูป: [method_comparison.png](figures/method_comparison.png), [method_comparison.svg](figures/method_comparison.svg)

> ประเด็นพูด: บอก gain พร้อม MAE trade-off; context (สีเทา) เป็น ablation ไม่ eligible; ไม่เรียกว่า accuracy

### สไลด์ 6: ความเสถียร: folds, 2024/25 ที่เคยเห็นแล้ว และ spatial transfer

**OOF folds (ใช้เลือก)**

| unit | period | cells | records | baseline deviance | selected deviance | reduction |
|---|---|---|---|---|---|---|
| daily | 2022H1 | 562,005 | 2,392 | 0.040698 | 0.038990 | +4.196% |
| daily | 2022H2 | 571,320 | 2,516 | 0.038119 | 0.037134 | +2.582% |
| daily | 2023H1 | 562,005 | 3,016 | 0.045977 | 0.044803 | +2.554% |
| daily | 2023H2 | 571,320 | 2,777 | 0.039108 | 0.038730 | +0.968% |
| 6h | 2022H1 | 2,248,020 | 2,392 | 0.014472 | 0.012633 | +12.707% |
| 6h | 2022H2 | 2,285,280 | 2,516 | 0.013322 | 0.012217 | +8.297% |
| 6h | 2023H1 | 2,248,020 | 3,016 | 0.016036 | 0.014794 | +7.744% |
| 6h | 2023H2 | 2,285,280 | 2,777 | 0.013396 | 0.012907 | +3.650% |

**2024/25: previously seen diagnostics (ไม่ใช่ untouched test; ไม่ใช้เลือก)**

| unit | period | cells | records | baseline deviance | selected deviance | reduction |
|---|---|---|---|---|---|---|
| daily | seen_2024 | 1,136,430 | 6,015 | 0.044229 | 0.043462 | +1.735% |
| daily | seen_2025 | 1,133,325 | 6,231 | 0.047885 | 0.046263 | +3.389% |
| 6h | seen_2024 | 4,545,720 | 6,015 | 0.015493 | 0.014372 | +7.240% |
| 6h | seen_2025 | 4,533,300 | 6,231 | 0.016978 | 0.015223 | +10.337% |

- context-available cells 2024/25: daily 0; 6h 0 (0 = selected routed policy ใช้ core fallback ตลอดช่วง)

**Spatial transfer 2023 (held-out sections; แยกจากการเลือกเชิงเวลา)**

| unit | method | cells | records | deviance | vs best transfer baseline |
|---|---|---|---|---|---|
| daily | `poisson_a1e-05::core` | 149,650 | 483 | 0.036273 | -2.664% |
| daily | `rf_poisson_fixed::core` | 149,650 | 483 | 0.036908 | -4.461% |
| daily | `hgb_poisson_fixed::core` | 149,650 | 483 | 0.034559 | +2.188% |
| daily | `global_mean` | 149,650 | 483 | 0.038719 | -9.587% |
| daily | `global_length_rate` | 149,650 | 483 | 0.038491 | -8.942% |
| daily | `route_length_rate` | 149,650 | 483 | 0.035332 | +0.000% |
| daily | `segment_mean_k30` | 149,650 | 483 | 0.035332 | +0.000% |
| daily | `segment_mean_k180` | 149,650 | 483 | 0.035332 | +0.000% |
| daily | `segment_mean_k365` | 149,650 | 483 | 0.035332 | +0.000% |
| daily | `segment_weekday_k10` | 149,650 | 483 | 0.035332 | +0.000% |
| daily | `segment_month_k30` | 149,650 | 483 | 0.035332 | +0.000% |
| daily | `recent90_segment` | 149,650 | 483 | 0.035332 | +0.000% |
| 6h | `poisson_a1e-05::core` | 598,600 | 483 | 0.011759 | -4.615% |
| 6h | `rf_poisson_fixed::core` | 598,600 | 483 | 0.011395 | -1.379% |
| 6h | `hgb_poisson_fixed::core` | 598,600 | 483 | 0.010643 | +5.309% |
| 6h | `global_mean` | 598,600 | 483 | 0.011803 | -5.003% |
| 6h | `global_length_rate` | 598,600 | 483 | 0.011746 | -4.497% |
| 6h | `route_length_rate` | 598,600 | 483 | 0.011240 | +0.000% |
| 6h | `segment_mean_k30` | 598,600 | 483 | 0.011240 | +0.000% |
| 6h | `segment_mean_k180` | 598,600 | 483 | 0.011240 | +0.000% |
| 6h | `segment_mean_k365` | 598,600 | 483 | 0.011240 | +0.000% |
| 6h | `segment_weekday_k10` | 598,600 | 483 | 0.011240 | +0.000% |
| 6h | `segment_month_k30` | 598,600 | 483 | 0.011240 | +0.000% |
| 6h | `recent90_segment` | 598,600 | 483 | 0.011240 | +0.000% |

รูป: [fold_performance.png](figures/fold_performance.png), [fold_performance.svg](figures/fold_performance.svg), [seen_2024_2025.png](figures/seen_2024_2025.png), [seen_2024_2025.svg](figures/seen_2024_2025.svg), [spatial_transfer.png](figures/spatial_transfer.png), [spatial_transfer.svg](figures/spatial_transfer.svg)

> ประเด็นพูด: 2024/25 และ transfer เป็นหลักฐานเสริม ไม่ใช่ holdout; transfer ประเมิน core เท่านั้นในพื้นที่เดียว. 2026 ยังรอการตรวจข้อมูล

## Error Analysis

### สไลด์ 7: ยอดรวม, calibration และ metric floor

| unit | role | total predicted | total actual | pred / actual | bias per cell |
|---|---|---|---|---|---|
| daily | selected | 9574.10 | 10,701 | 0.8947 | -0.0004972 |
| daily | baseline | 9352.69 | 10,701 | 0.8740 | -0.0005948 |
| 6h | selected | 9446.02 | 10,701 | 0.8827 | -0.0001384 |
| 6h | baseline | 9352.17 | 10,701 | 0.8740 | -0.0001488 |

calibration bin สูงสุด (support จริงของ bin):

| unit | role | predicted-count bin | cells | records | mean predicted | mean actual |
|---|---|---|---|---|---|---|
| daily | selected | [np.float64(0.12917820382553857), np.float64(0.7739901594483467)) | 2,269 | 428 | 0.17605 | 0.18863 |
| daily | baseline | [np.float64(0.10977642509438672), np.float64(0.17371831674004742)) | 2,377 | 499 | 0.13037 | 0.20993 |
| 6h | selected | [np.float64(0.0331654524045979), np.float64(0.19029009679343553)) | 9,067 | 495 | 0.04507 | 0.05459 |
| 6h | baseline | [np.float64(0.028003411895316233), np.float64(0.0888270697479011)) | 9,134 | 507 | 0.03835 | 0.05551 |

| unit | floor group | cells | actual-positive cells | records | share of pooled gain |
|---|---|---|---|---|---|
| daily | both_positive_mean | 2,097,870 | 10,068 | 10,653 | 25.00% |
| daily | baseline_floor_only | 168,780 | 48 | 48 | 75.00% |
| daily | candidate_floor_only | 0 | 0 | 0 | 0.00% |
| daily | both_floor | 0 | 0 | 0 | 0.00% |
| 6h | both_positive_mean | 7,113,293 | 10,180 | 10,484 | 26.54% |
| 6h | baseline_floor_only | 1,953,307 | 217 | 217 | 73.46% |
| 6h | candidate_floor_only | 0 | 0 | 0 | 0.00% |
| 6h | both_floor | 0 | 0 | 0 | 0.00% |

- daily: gain จากเซลล์ที่ baseline < floor = 75.00%; reduction ในเซลล์ที่เหลือ = +0.664% (sensitivity ที่ลงทะเบียนหลังเห็นผล daily เบื้องต้น ไม่ใช่ gate)
- 6h: gain จากเซลล์ที่ baseline < floor = 73.46%; reduction ในเซลล์ที่เหลือ = +2.375% (sensitivity ที่ลงทะเบียนหลังเห็นผล daily เบื้องต้น ไม่ใช่ gate)

รูป: [calibration.png](figures/calibration.png), [calibration.svg](figures/calibration.svg), [floor_audit.png](figures/floor_audit.png), [floor_audit.svg](figures/floor_audit.svg)

> ประเด็นพูด: ยอดรวมยังทำนายต่ำ; gain ส่วนใหญ่มาจากเซลล์ที่ baseline ทำนาย 0 — รายงานตรงไปตรงมา ไม่เปลี่ยน baseline/metric ย้อนหลัง

### สไลด์ 8: กลุ่มที่ baseline ดีกว่า (OOF 2022-23, descriptive หลังการเลือก ไม่ใช่ gate ใหม่)

| unit | dimension | group | cells | records | baseline deviance | selected deviance | reduction |
|---|---|---|---|---|---|---|---|
| 6h | actual_zero | zero | 9,056,203 | 0 | 0.002048 | 0.002067 | -0.9419% |
| daily | province | 72 Suphan Buri | 13,870 | 34 | 0.027601 | 0.028587 | -3.5754% |
| daily | actual_zero | zero | 2,256,534 | 0 | 0.008042 | 0.008201 | -1.9823% |
| daily | province | 20 Chon Buri | 10,220 | 29 | 0.031068 | 0.031547 | -1.5434% |
| daily | festival | songkran_post_4_7 | 24,840 | 103 | 0.036725 | 0.037159 | -1.1829% |
| daily | province | 60 Nakhon Sawan | 32,120 | 127 | 0.038354 | 0.038597 | -0.6320% |
| daily | festival | new_year_post_4_7 | 24,840 | 116 | 0.039645 | 0.039890 | -0.6186% |
| daily | province | 24 Chachoengsao | 163,520 | 661 | 0.035860 | 0.035987 | -0.3536% |
| daily | month | 7 | 192,510 | 891 | 0.040009 | 0.040048 | -0.0970% |
| daily | month | 8 | 192,510 | 866 | 0.037134 | 0.037151 | -0.0445% |
| daily | month | 3 | 192,510 | 862 | 0.038954 | 0.038968 | -0.0347% |

- daily: route_code ที่ baseline ดีกว่า 81/218 สายทาง (support ต่อสายทางน้อย; ดู metrics_by_group.csv)
- 6h: route_code ที่ baseline ดีกว่า 54/218 สายทาง (support ต่อสายทางน้อย; ดู metrics_by_group.csv)
- province = จุดกึ่งกลาง segment ตาม geometry ปัจจุบัน ไม่ใช่ province ของเหตุการณ์; กลุ่ม support น้อยมีความไม่แน่นอนสูง

รูป: [errors_by_group.png](figures/errors_by_group.png), [errors_by_group.svg](figures/errors_by_group.svg), [errors_by_area_month.png](figures/errors_by_area_month.png), [errors_by_area_month.svg](figures/errors_by_area_month.svg)

> ประเด็นพูด: โมเดลชนะโดยรวมแต่ไม่ชนะทุกกลุ่ม; แสดงจำนวน cells/records ทุกกลุ่ม ห้ามใช้กลุ่มเหล่านี้เปลี่ยน winner หรือ threshold

### สไลด์ 9: capture ที่งบ road-km เท่ากัน และสีความหนาแน่นสัมพัทธ์

| unit | top road-km | selected capture | baseline capture | uniform | better |
|---|---|---|---|---|---|
| daily | 1% | 19.18% | 20.07% | 1% | baseline |
| daily | 2% | 30.12% | 30.74% | 2% | baseline |
| daily | 5% | 50.16% | 49.79% | 5% | selected |
| daily | 10% | 61.81% | 62.53% | 10% | baseline |
| daily | 20% | 75.08% | 75.94% | 20% | baseline |
| 6h | 1% | 19.12% | 19.30% | 1% | baseline |
| 6h | 2% | 29.63% | 30.03% | 2% | baseline |
| 6h | 5% | 50.43% | 48.31% | 5% | selected |
| 6h | 10% | 62.20% | 60.60% | 10% | selected |
| 6h | 20% | 75.22% | 73.06% | 20% | selected |

- boundary segment ถูกนับ records ตามสัดส่วนความยาว (สมมติฐาน ไม่ใช่ตำแหน่งเหตุจริงในเศษ segment); ไม่ใช่ผลด้านความปลอดภัยเชิงสาเหตุ

| unit | P50 / P80 / P95 cutoffs | density unit | labels in use | reference cells per band |
|---|---|---|---|---|
| daily | 0.000672535 / 0.00248471 / 0.00811673 | records per km per local day | base, yellow, orange, red | base 1,133,328, yellow 679,992, orange 339,997, red 113,333 |
| 6h | 0.000168218 / 0.000613451 / 0.00200354 | records per km per 6 h block | base, yellow, orange, red | base 4,533,300, yellow 2,719,981, orange 1,360,003, red 453,316 |

| unit | colour | cells | cell share | exposure share | record share | observed records per km-period |
|---|---|---|---|---|---|---|
| daily | base | 1,133,328 | 50.00% | 49.86% | 6.42% | 0.000320 |
| daily | yellow | 679,992 | 30.00% | 29.89% | 16.41% | 0.001364 |
| daily | orange | 339,997 | 15.00% | 15.14% | 27.47% | 0.004508 |
| daily | red | 113,333 | 5.00% | 5.11% | 49.70% | 0.024184 |
| daily | grey | 0 | 0.00% | 0.00% | 0.00% | n/a |
| 6h | base | 4,533,300 | 50.00% | 49.87% | 6.41% | 0.000080 |
| 6h | yellow | 2,719,981 | 30.00% | 29.92% | 16.48% | 0.000342 |
| 6h | orange | 1,360,003 | 15.00% | 15.10% | 26.45% | 0.001088 |
| 6h | red | 453,316 | 5.00% | 5.10% | 50.66% | 0.006164 |
| 6h | grey | 0 | 0.00% | 0.00% | 0.00% | n/a |

รูป: [colour_exposure_capture.png](figures/colour_exposure_capture.png), [colour_exposure_capture.svg](figures/colour_exposure_capture.svg), [capture_curve.png](figures/capture_curve.png), [capture_curve.svg](figures/capture_curve.svg)

> ประเด็นพูด: base = ต่ำกว่าเชิงสัมพัทธ์ ไม่ใช่ปลอดภัย; cutoffs คงที่ทุกเส้นทาง/มุมมอง ไม่แปลงข้าม daily/6h; การจัดอันดับไม่ชนะทุกงบ road-km

## เหตุผลเลือกโมเดล

### สไลด์ 10: เหตุผลเลือกและข้อจำกัด

- **daily**: `hgb_poisson_fixed::routed_context` เทียบ `segment_mean_k365` — ผ่านทุก gate จึงเลือก candidate: deviance +2.583%, MAE ratio 1.007095 (MAE เปลี่ยน +0.710%), ชนะ 4/4 folds
  - trade-off: eligible methods ที่ MAE ต่ำกว่า: `poisson_a1e-05::core`, `poisson_a1e-04::core`, `rf_poisson_fixed::core`, `hgb_poisson_fixed::core`, `segment_mean_k30`, `segment_mean_k180`, `segment_mean_k365`, `segment_weekday_k10`, `segment_month_k30`; RMSE ต่ำกว่า: `segment_mean_k30`, `segment_mean_k180`
  - gain จากเซลล์ baseline < floor: 75.00%; กลุ่ม (ไม่รวม route) ที่ baseline ดีกว่า: 10
  - capture: selected ดีกว่าที่ 5% road-km; baseline ดีกว่าที่ 1%, 2%, 10%, 20%
- **6h**: `hgb_poisson_fixed::routed_context` เทียบ `segment_mean_k365` — ผ่านทุก gate จึงเลือก candidate: deviance +8.152%, MAE ratio 1.004063 (MAE เปลี่ยน +0.406%), ชนะ 4/4 folds
  - trade-off: eligible methods ที่ MAE ต่ำกว่า: `poisson_a1e-05::core`, `poisson_a1e-04::core`, `rf_poisson_fixed::core`, `hgb_poisson_fixed::core`, `route_length_rate`, `segment_mean_k30`, `segment_mean_k180`, `segment_mean_k365`, `segment_weekday_k10`, `segment_month_k30`; RMSE ต่ำกว่า: `rf_poisson_fixed::core`, `rf_poisson_fixed::routed_context`
  - gain จากเซลล์ baseline < floor: 73.46%; กลุ่ม (ไม่รวม route) ที่ baseline ดีกว่า: 1
  - capture: selected ดีกว่าที่ 5%, 10%, 20% road-km; baseline ดีกว่าที่ 1%, 2%

- ไม่อ้างว่าดีที่สุดสำหรับทุก ranking task / ทุก metric / ทุกกลุ่ม; ไม่ใช่ untouched test และยังไม่มี production/safety certification
- ขอบเขตที่ไม่รองรับตอบ unsupported/unavailable (สีเทา) ไม่สร้าง prediction 0 ทดแทน; แนะนำ benchmark-only serving ของ bundle notebook 20 จนกว่าจะมีความต้องการผู้ใช้แยก
- 2026: รอการตรวจข้อมูล (coverage/lag/eligibility) และการประเมินแยก — ยังไม่มีผล ห้ามเติมตัวเลข และจะไม่ใช้เปลี่ยน winner

> ประเด็นพูด: เลือกตาม gate ที่ล็อกโดยไม่ปรับเกณฑ์หลังเห็นคะแนน; ระบุจุดอ่อน (MAE, ยอดรวมต่ำ, floor share, กลุ่มที่แพ้) ให้ชัด
