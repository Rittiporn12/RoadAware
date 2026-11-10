# Model card — RoadAware แบบจำลองวิจัยย้อนหลังระดับจังหวัด–วัน (roadaware_model_experiment_v1)

> สร้างโดย Notebook 08 จากผลจริงที่ตรวจ hash แล้ว | `production_enabled = false` | `final_model_readiness = BLOCKED` | โหมด `retrospective_conditional_research`

## ⚠️ ข้อค้นพบสำคัญที่สุด: ผลในปีหลังกลับอันดับ และข้อมูลเปลี่ยน regime

- Poisson ถูกเลือกและผ่าน gate ที่ล็อกไว้บน OOF 2022–2023 แต่บนเซลล์ eligible ปีหลัง strongest baseline (`baseline_province_mean`) มี Poisson deviance 1.1535 (2024) และ 1.2453 (2025) เทียบกับ selected candidate 2.1700 และ 2.2546
- จำนวนตัวดีที่สุดของตระกูล (จาก 3) ที่ชนะ baseline ใน primary metric: diagnostic_validation_2024 = 0, diagnostic_reused_test_2025 = 0, diagnostic_pooled_2024_2025 = 0; **ทั้งสาม candidate แพ้ baseline ค่าเฉลี่ยรายจังหวัด** ใน diagnostic_validation_2024, diagnostic_reused_test_2025, diagnostic_pooled_2024_2025
- cohort หลัง cleaning ต่างกัน: ใน Train วันที่ 1–12 มีค่าเฉลี่ย 0.1719 เหตุต่อ province-day (eligible 0.4209 ของ panel) เทียบวันที่ 13–31 = 0.6864 ขณะที่ปี 2024 เป็น 0.7933 / 0.7752 และปี 2025 เป็น 0.7727 / 0.7792
- แถว eligible ที่มีเหตุในวันที่ 1–12 ของ Train: 1168 แถว ในนี้ 1168 แถวมีเลขวันเท่ากับเลขเดือน (สัดส่วน 1.0000) สอดคล้องกับการกักกันวันที่ slash ที่กำกวม ต่างจากปีหลังที่เป็นวันที่แบบ Excel — เป็นหลักฐาน cohort/selection bias ไม่ใช่สาเหตุของอุบัติเหตุ
- ดังนั้นชัยชนะใน OOF อาจไม่ข้าม regime ได้ การเลือกจาก OOF ยังคงตาม protocol แต่ผลปีหลังเป็นข้อจำกัดหลัก

## คำตอบการเลือกโมเดล (ล็อกจาก OOF ก่อนให้คะแนนปีหลัง)

- ตัวดีที่สุดของสามตระกูล: poisson = `poisson_alpha_1e-4` {"alpha": 0.0001, "max_iter": 1000, "tol": 1e-06}; random_forest = `rf_t120_d16_l128_m100` {"n_estimators": 120, "max_depth": 16, "max_leaf_nodes": 128, "min_samples_leaf": 100, "max_features": 0.7, "criterion": "poisson", "random_state": 42, "n_jobs": 2}; hist_gradient_boosting = `hgb_i120_l15_m50_r1` {"max_iter": 120, "max_leaf_nodes": 15, "min_samples_leaf": 50, "l2_regularization": 1.0, "learning_rate": 0.05, "loss": "poisson", "early_stopping": false, "random_state": 42}
- **selected candidate:** `poisson_alpha_1e-4` | **strongest baseline:** `baseline_province_mean` | **recommended reference ตาม protocol OOF:** `poisson_alpha_1e-4` (candidate, stable_gain = True)
- recommended reference นี้เป็นผลของกติกาเปรียบเทียบ OOF ที่ล็อกไว้เท่านั้น **ไม่ใช่การอนุมัติให้ใช้งานจริง**

| family | spec_id | selected | OOF deviance | OOF MAE | OOF RMSE | bootstrap CI low | bootstrap CI high | fit s (06) | predict us/cell (07) |
|---|---|---|---|---|---|---|---|---|---|
| poisson | poisson_alpha_1e-4 | True | 0.9371 | 0.5665 | 0.9243 | -0.2353 | -0.0927 | 0.2370 | 0.3166 |
| random_forest | rf_t120_d16_l128_m100 | False | 1.0713 | 0.6154 | 0.9433 | -0.1074 | 0.0314 | 6.6540 | 2.8979 |
| hist_gradient_boosting | hgb_i120_l15_m50_r1 | False | 0.9743 | 0.5634 | 0.9090 | -0.2168 | -0.0585 | 0.2780 | 1.5951 |
| baseline | baseline_province_mean | False | 1.1125 | 0.6202 | 0.9633 | null | null | 0.0050 | 0.0994 |

- ข้อแลกเปลี่ยนบน OOF ในสาม configuration ที่ล็อกจากแต่ละตระกูลตาม primary metric: deviance ต่ำสุด = `poisson_alpha_1e-4`, MAE ต่ำสุด = `hgb_i120_l15_m50_r1`, RMSE ต่ำสุด = `hgb_i120_l15_m50_r1`; ถ้าดูทุก candidate configuration ที่ทดลอง (รายงานเท่านั้น ไม่ใช่เกณฑ์เลือก) MAE ต่ำสุด = `hgb_i160_l31_m100_r5` และ RMSE ต่ำสุด = `hgb_i120_l15_m50_r1` — Poisson ตีความได้ง่ายกว่า (log-linear one-hot) ส่วน Random Forest/HGB จับความไม่เป็นเส้นตรงได้ เวลา fit/predict เป็นค่าที่วัดจริงแต่ไม่ deterministic
- bootstrap: paired 7-day calendar block, 500 รอบ, seed 42; ผลต่าง = deviance ของ candidate − baseline (ติดลบ = candidate ดีกว่า) เป็นการสำรวจ ไม่ปรับสำหรับการเลือกหลายตัว

### Gate ที่ล็อกไว้ (OOF)

| criterion | value | rule | passed |
|---|---|---|---|
| relative_deviance_improvement | 0.1576 | >= 0.01 | True |
| mae_ratio_candidate_over_baseline | 0.9135 | <= 1.02 | True |
| folds_with_lower_deviance | 4 | >= 3 | True |
| bootstrap_ci_upper_deviance_difference | -0.0927 | < 0 | True |

| fold | selected deviance | baseline deviance |
|---|---|---|
| 1 | 0.9682 | 1.2087 |
| 2 | 0.9830 | 1.1476 |
| 3 | 0.9261 | 1.0897 |
| 4 | 0.8674 | 0.9988 |

## ผลปีหลัง (เซลล์ eligible เท่านั้น; การวินิจฉัย ไม่ใช่การเลือกใหม่)

| scope | n | spec_id | deviance | MAE | RMSE | bias |
|---|---|---|---|---|---|---|
| diagnostic_validation_2024 | 7885 | poisson_alpha_1e-4 (selected) | 2.1700 | 0.7252 | 1.2374 | -0.3553 |
| diagnostic_validation_2024 | 7885 | rf_t120_d16_l128_m100 | 2.0300 | 0.7645 | 1.2393 | -0.3372 |
| diagnostic_validation_2024 | 7885 | hgb_i120_l15_m50_r1 | 1.6654 | 0.7011 | 1.1545 | -0.3048 |
| diagnostic_validation_2024 | 7885 | baseline_province_mean | 1.1535 | 0.6873 | 1.0463 | -0.1686 |
| diagnostic_reused_test_2025 | 27506 | poisson_alpha_1e-4 (selected) | 2.2546 | 0.7303 | 1.2614 | -0.3290 |
| diagnostic_reused_test_2025 | 27506 | rf_t120_d16_l128_m100 | 2.0558 | 0.7622 | 1.2632 | -0.3149 |
| diagnostic_reused_test_2025 | 27506 | hgb_i120_l15_m50_r1 | 1.7121 | 0.7018 | 1.1761 | -0.2848 |
| diagnostic_reused_test_2025 | 27506 | baseline_province_mean | 1.2453 | 0.7047 | 1.1176 | -0.1598 |
| diagnostic_pooled_2024_2025 | 35391 | poisson_alpha_1e-4 (selected) | 2.2358 | 0.7292 | 1.2561 | -0.3349 |
| diagnostic_pooled_2024_2025 | 35391 | rf_t120_d16_l128_m100 | 2.0501 | 0.7628 | 1.2580 | -0.3199 |
| diagnostic_pooled_2024_2025 | 35391 | hgb_i120_l15_m50_r1 | 1.7017 | 0.7017 | 1.1713 | -0.2892 |
| diagnostic_pooled_2024_2025 | 35391 | baseline_province_mean | 1.2249 | 0.7008 | 1.1021 | -0.1618 |

## Error analysis โดยสรุป

ช่วงจำนวนจริง (outcome bins เป็นการวินิจฉัย ไม่ใช่ input):

| evaluation_scope | level | role | n_rows | observed_total | predicted_total | mae | rmse | bias |
|---|---|---|---|---|---|---|---|---|
| oof_train_backtest | 0 | selected_candidate | 28038 | 0 | 9854.6472 | 0.3515 | 0.5052 | 0.3515 |
| oof_train_backtest | 0 | strongest_baseline | 28038 | 0 | 11613.8587 | 0.4142 | 0.5299 | 0.4142 |
| oof_train_backtest | 1 | selected_candidate | 8612 | 8612 | 5905.1929 | 0.5238 | 0.6320 | -0.3143 |
| oof_train_backtest | 1 | strongest_baseline | 8612 | 8612 | 5626.0625 | 0.5419 | 0.6317 | -0.3467 |
| oof_train_backtest | 2-3 | selected_candidate | 4264 | 9669 | 4563.5870 | 1.3506 | 1.4955 | -1.1973 |
| oof_train_backtest | 2-3 | strongest_baseline | 4264 | 9669 | 4292.3604 | 1.3733 | 1.5116 | -1.2609 |
| oof_train_backtest | >=4 | selected_candidate | 1144 | 6167 | 2912.3566 | 3.2368 | 3.7159 | -2.8450 |
| oof_train_backtest | >=4 | strongest_baseline | 1144 | 6167 | 2220.6162 | 3.4502 | 3.9636 | -3.4496 |
| diagnostic_validation_2024 | 0 | selected_candidate | 4457 | 0 | 1353.1169 | 0.3036 | 0.4341 | 0.3036 |
| diagnostic_validation_2024 | 0 | strongest_baseline | 4457 | 0 | 1859.6712 | 0.4172 | 0.5211 | 0.4172 |
| diagnostic_validation_2024 | 1 | selected_candidate | 2030 | 2030 | 887.4214 | 0.6493 | 0.7208 | -0.5628 |
| diagnostic_validation_2024 | 1 | strongest_baseline | 2030 | 2030 | 1251.9541 | 0.5205 | 0.5916 | -0.3833 |
| diagnostic_validation_2024 | 2-3 | selected_candidate | 1105 | 2516 | 725.3269 | 1.6505 | 1.7808 | -1.6205 |
| diagnostic_validation_2024 | 2-3 | strongest_baseline | 1105 | 2516 | 1078.3598 | 1.3826 | 1.5096 | -1.3010 |
| diagnostic_validation_2024 | >=4 | selected_candidate | 293 | 1622 | 400.3999 | 4.1736 | 4.7730 | -4.1693 |
| diagnostic_validation_2024 | >=4 | strongest_baseline | 293 | 1622 | 648.7527 | 3.3289 | 3.7828 | -3.3217 |
| diagnostic_reused_test_2025 | 0 | selected_candidate | 15722 | 0 | 4944.6820 | 0.3145 | 0.4642 | 0.3145 |
| diagnostic_reused_test_2025 | 0 | strongest_baseline | 15722 | 0 | 6782.9367 | 0.4314 | 0.5404 | 0.4314 |
| diagnostic_reused_test_2025 | 1 | selected_candidate | 7164 | 7164 | 3110.0421 | 0.6677 | 0.7432 | -0.5659 |
| diagnostic_reused_test_2025 | 1 | strongest_baseline | 7164 | 7164 | 4434.8559 | 0.5321 | 0.6106 | -0.3810 |
| diagnostic_reused_test_2025 | 2-3 | selected_candidate | 3575 | 8191 | 2503.1598 | 1.6669 | 1.8095 | -1.5910 |
| diagnostic_reused_test_2025 | 2-3 | strongest_baseline | 3575 | 8191 | 3509.0434 | 1.4004 | 1.5344 | -1.3096 |
| diagnostic_reused_test_2025 | >=4 | selected_candidate | 1045 | 6007 | 1754.0238 | 4.2119 | 4.8635 | -4.0698 |
| diagnostic_reused_test_2025 | >=4 | strongest_baseline | 1045 | 6007 | 2239.8665 | 3.6192 | 4.2273 | -3.6049 |

การเปลี่ยน cohort แยกวันที่ 1–12 / 13–31 (คำนวณจาก panel; error ของ Train มาจากแถว OOF 2022–2023):

| split | day_group | panel_rows | eligible_rows | eligible_share_of_panel | eligible_observed_mean | eligible_positive_share | error_rows | selected MAE | baseline MAE |
|---|---|---|---|---|---|---|---|---|---|
| train | days01-12 | 33264 | 14001 | 0.4209 | 0.1719 | 0.0834 | 9125 | 0.1733 | 0.4416 |
| train | days13-31 | 51051 | 49756 | 0.9746 | 0.6864 | 0.3985 | 32933 | 0.6755 | 0.6697 |
| validation | days01-12 | 11088 | 3067 | 0.2766 | 0.7933 | 0.4376 | 3067 | 0.7791 | 0.6948 |
| validation | days13-31 | 17094 | 4818 | 0.2819 | 0.7752 | 0.4330 | 4818 | 0.6908 | 0.6826 |
| reused_test_2025 | days01-12 | 11088 | 10801 | 0.9741 | 0.7727 | 0.4309 | 10801 | 0.7601 | 0.6936 |
| reused_test_2025 | days13-31 | 17017 | 16705 | 0.9817 | 0.7792 | 0.4268 | 16705 | 0.7111 | 0.7119 |

ตารางรายเดือน/จังหวัด/วันในสัปดาห์, กลุ่มที่ทำนายเกิน/ขาดมากที่สุด, calibration-style bins และกราฟอยู่ที่ `reports/models/error_analysis/`

## ขอบเขต ข้อมูล และ feature

- หน่วย: `province_day_recorded_count` (provisional_data_readiness_demo_not_route_model); ออกพยากรณ์ 18:00 local (Asia/Bangkok), 1 day(s) before the target day; horizon หนึ่ง province-day ล่วงหน้า (งานวิจัยย้อนหลัง ไม่ใช่ as-of forecast ที่ยืนยันแล้ว)
- feature: `province`, `day_of_week`, `month`, `day_of_month`, `day_of_year`, `is_weekend` (จังหวัด + ปฏิทินเท่านั้น); encoding ตาม config ที่ล็อก
- Train: ช่วง split ตาม config 2021-01-01–2023-12-31; วันที่จริงของเซลล์ eligible 2021-01-01–2023-12-29 จำนวน 63757 province-day; OOF 4 fold ปี 2022–2023 42058 แถว; ปี 2024 7885 แถว; ปี 2025 27506 แถว

## ข้อเสนอเชิงปฏิบัติ

- **ระงับการนำไปใช้งาน (deployment = withhold)** และ prospective_forecast_allowed = False เหตุผล:
  - production_enabled is false under the locked research protocol
  - final model readiness is BLOCKED (data foundation reports 'BLOCKED')
  - later-year reversal: no frozen family best beats the strongest baseline on diagnostic_validation_2024, diagnostic_reused_test_2025, diagnostic_pooled_2024_2025
  - the selected candidate passed the OOF gate but does not beat the strongest baseline on diagnostic_validation_2024, diagnostic_reused_test_2025, diagnostic_pooled_2024_2025
  - no untouched independent test exists (2025 was seen before)
  - scores cover selection-biased training_eligible cells only
- งานข้อมูลถัดไป (ก่อนพยากรณ์ล่วงหน้าใดๆ):
  - ยืนยัน convention ของวันที่แบบ slash ต่อไฟล์กับผู้เผยแพร่/เอกสารต้นทาง แล้วกู้คืนแถวที่ถูกกักกันอย่างมีหลักฐาน (ลด selection bias ช่วงวันที่ 1–12 ของ Train)
  - ตรวจเวลาที่ข้อมูลรายงานพร้อมใช้จริง (reporting availability) เพื่อยืนยันว่า feature/label สอดคล้องกับเวลาออกพยากรณ์ 18:00 ของวันก่อนหน้า
  - ตรวจการจับคู่จังหวัด/พื้นที่ และกำหนดหน่วยสายทางจริงก่อนทำ route model
  - กำหนดช่วงทดสอบล่วงหน้า (prospective) ที่ยังไม่เคยเห็น แล้วรัน 06–08 ใหม่ภายใต้ protocol เวอร์ชันใหม่ ห้าม tune บนปี 2024/2025
  - blocker จาก data foundation: {'blocker': 'publication_availability', 'detail': 'reporting delay / when records become available is unknown, so historical lags are blocked and labels may be incomplete at evaluation time'}
  - blocker จาก data foundation: {'blocker': 'date_ambiguity', 'detail': 'ambiguous D/M vs M/D slash dates are quarantined; their candidate province-days are flagged, not resolved'}
  - blocker จาก data foundation: {'blocker': 'coverage_completeness', 'detail': 'MOT road network only; completeness unknown; zero = no selected recorded event; unlocalized excluded rows may undercount unknown days'}
  - blocker จาก data foundation: {'blocker': 'reused_test', 'detail': '2025 was previously inspected and 2024-2026 were explored in EDA; no untouched independent test set exists'}
  - blocker จาก data foundation: {'blocker': 'route_precision', 'detail': 'province-day is a provisional demo unit; reported province unverified vs coordinates; coordinates only checked against a broad bbox; route-segment unit not agreed'}
  - blocker จาก data foundation: {'blocker': 'no_id_2026', 'detail': '2569/2026 lacks ACC_CODE and is diagnostic only'}

## ข้อจำกัดที่ทราบ

- คะแนนทั้งหมดเป็นของเซลล์ province-day ที่ training_eligible (ตัวกรองคุณภาพที่รู้หลังเห็นปัญหา) จึงมี selection bias ไม่ใช่ทั้งปี ทั้งประเทศ หรือรายสายทาง
- ปี 2024 ไม่มีเซลล์ eligible ในเดือน ต.ค.–ธ.ค.; ปี 2025 เคยถูกดูแล้ว จึงไม่มี test อิสระ; ไม่ใช้ label ปี 2026
- feature มีเพียงจังหวัดและปฏิทิน (ไม่มี lag สภาพอากาศ วันหยุด/เทศกาล หรือการจราจร) จึงไม่อ้างผลของปัจจัยเหล่านั้น
- ค่าทำนายเป็นจำนวนเหตุที่บันทึกต่อ province-day ไม่ใช่ความน่าจะเป็นรายบุคคล และไม่มีการ calibrate
- bootstrap เป็นการสำรวจ ไม่ปรับสำหรับการเลือกหลายโมเดล; Random Forest แบบขนานอาจต่างกันระดับ 1e-15 ระหว่างการรัน

- ไม่รองรับการอ้างเรื่อง: weather effects, festival/holiday effects, traffic effects, route-level or hourly accuracy, personal crash probability, full-year or whole-country accuracy
- เลื่อนไปขั้นถัดไป: route-level model, API, UI / dashboard, weather/festival/traffic features
- grouped permutation sensitivity (ข้อ 8 ของงาน): ไม่ได้ทำ — Optional task item omitted: notebook 08 deliberately loads no model bundle and works only from hash-verified saved predictions, while grouped permutation needs fresh predictions from the bundles; the required error analysis was prioritised, and with every family best losing to the strongest baseline on later years a feature-sensitivity ranking would not change the selection or deployment answer. Deferred to a later protocol version.

## ที่มา

- decision_sha256 `63aeb27230f9e439ecda7d6f07243510d7ff292c85d411eea6f45d8008ecc787`; choice_sha256 `4781bb5adcf649b0ff8e5cd278067a10d80cd1bd569cea5c39dc336bf7ffb30e`; selection_lock.json sha256 `630f329d1681f63f2edd66f71e4f1a84d0c946545357843c29efbfec9e874231`
- OOF predictions sha256 `b3543ab1d461f8f8e9c61bdfc618f16221f255f5fd9cf91543bd7c5576503190`; diagnostic predictions sha256 `81a3b9a70c4ef0c276a1a58a593d42ce062d0b85575dc12d7f7cd2d62c39024a`
- package versions: {"python": "3.9.6", "numpy": "2.0.2", "pandas": "2.3.3", "scikit-learn": "1.6.1", "scipy": "1.13.1", "joblib": "1.5.3", "threadpoolctl": "3.7.0", "matplotlib": "3.9.4"}
