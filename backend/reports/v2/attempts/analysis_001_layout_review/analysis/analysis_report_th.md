# รายงานวิเคราะห์ผลการทดลอง V2 และ error analysis (Notebook 12)

**สถานะ: งานวิจัยเท่านั้น | production_ready = false | operational = BLOCKED.** ไม่ใช่ Dashboard/เว็บที่ deploy, ไม่ใช่ความเสี่ยงรายบุคคลหรือรายเส้นทาง, ไม่ใช่อุบัติเหตุทุกถนน (ป้าย = จำนวนบันทึก MOT ที่ถูกเลือก) และ **ไม่มี untouched test**

ช่วงข้อมูล 3 แบบแยกกันเสมอ ไม่รวมกัน: (1) **pooled OOF 2022–2023** = หลักฐานที่ใช้เลือกโมเดล; (2) **2024 development** = เคยเห็นแล้วระหว่างพัฒนา; (3) **2025 reused** = เคยใช้/เคยเห็นแล้ว — (2)(3) เป็น diagnostic ไม่ได้ใช้เปลี่ยนตัวเลือก, daily และ 6h วิเคราะห์แยกกัน ไม่เทียบ error ข้ามหน่วย

## 1. การตรวจสอบที่รันจริงก่อน/ระหว่างวิเคราะห์

- experiment_lock: protocol/config/10-manifest/data-output hashes equal the manager lock
- notebook11_completed: manifest status completed; runner log ok (canonical: /Users/earthnaja/Documents/GitHub/Work - Earth/Project Work/Source Code/RoadAware/backend/reports/v2/run_manifest_model.json)
- notebook11_report_hashes: 12 report files equal model_manifest.report_outputs (only the runner-owned log run_manifest_model.json is never hashed: mutable)
- notebook11_prediction_hashes: 4 prediction files equal model_data_outputs and next_stage_interface
- notebook11_code_hashes: FUNCTIONS f163f65a7523 and every code cell equal the manifest
- selection_lock: selection_lock.json sha fef0a1c93efb; 6 locked files unchanged; choices equal in lock/manifest/interface; recommendation follows the locked gate
- notebook11_inputs_unchanged: 9 11 input roles hash-equal; 10 panels/features match the 10 manifest
- read_only_snapshot_before: 28 read-only files hashed
- metric_reconciliation: 2664 recomputed values equal 11 within rtol 1e-09 / atol 1e-09; labels equal the 10 panel
- selection_and_gate_recheck: locked family winners / best candidate / strongest baseline follow from recomputed OOF; gate outcome and bootstrap interval reproduced
- ablation_reconciliation: 392 protocol ablation values equal 11; benefit/harm labels equal; 72 paired comparisons on identical keys (2 additional vs-core pairs per configuration)
- slice_totals: 3176 slice rows; every dimension's level totals add up to its period total (n, actual, predicted)
- calibration_bins: 240 bins from OOF-only unique quantile edges (ties collapse; empty bins kept with n = 0)
- figures_written: 14 PNG files (visual inspection is a separate manual check, not done by the notebook)

ไม่มีการ fit, tune, calibrate หรือเลือกใหม่; ค่าที่คำนวณซ้ำทั้งหมดต้องตรงกับ notebook 11 ภายใน rtol 1e-09 / atol 1e-09 (ไม่ตรง = หยุดทำงาน) ดู `metric_reconciliation.csv`, `ablation_reconciliation.csv`

## 2.1 หน่วย daily: ตัวเลือกและเหตุผล

- **ข้อเสนอตาม protocol: `hgb_poisson__full`** (candidate_passed_gate)
- best candidate จาก 3 ตระกูล: `hgb_poisson__full`; strongest baseline: `baseline_province_month_k30`; ตัวแทนแต่ละตระกูล: {'poisson': 'poisson_a0.001__full', 'rf': 'rf_poisson__full', 'hgb': 'hgb_poisson__full'}
- วิธีที่ล้มเหลว/ไม่ครบ fold: ไม่มี

| วิธี | บทบาท | deviance OOF | MAE | RMSE | bias | ลด deviance vs baseline | ชนะ fold | boot ล่าง | boot บน |
|---|---|---|---|---|---|---|---|---|---|
| poisson_a0.001__full | family_best:poisson | 1.0896 | 0.6792 | 0.9908 | -0.0167 | 0.0495 | 4 | -0.0980 | -0.0241 |
| rf_poisson__full | family_best:rf | 1.1278 | 0.7010 | 0.9854 | -0.0072 | 0.0162 | 3 | -0.0619 | 0.0147 |
| hgb_poisson__full | family_best:hgb best_candidate RECOMMENDED | 1.0643 | 0.6601 | 0.9535 | -0.0182 | 0.0716 | 4 | -0.1363 | -0.0423 |
| baseline_zero |  | null | 0.6957 | 1.3796 | -0.6957 | null | null | null | null |
| baseline_global_mean |  | 1.5476 | 0.8303 | 1.1917 | 0.0090 | -0.3500 | 0.0000 | null | null |
| baseline_province_mean |  | 1.1571 | 0.6927 | 1.0142 | -0.0023 | -0.0093 | 1 | null | null |
| baseline_province_weekday_k10 |  | 1.1636 | 0.6928 | 1.0154 | -0.0026 | -0.0150 | 0.0000 | null | null |
| baseline_province_month_k30 | strongest_baseline | 1.1464 | 0.6894 | 1.0099 | -0.0052 | 0.0000 | 0.0000 | null | null |
| baseline_recent90_province_mean |  | 1.1718 | 0.6966 | 1.0127 | 0.0174 | -0.0221 | 0.0000 | null | null |

boot = ช่วง 95% ของผลต่าง deviance (วิธี − strongest baseline) แบบ paired 7-day block bootstrap; ใช้ใน gate เฉพาะ best candidate, ของตระกูลอื่นเป็นข้อมูลสำรวจเพิ่ม ไม่ปรับ multiple comparison

**Gate (ค่าที่ล็อกไว้และคำนวณซ้ำได้ตรงกัน):**

| เกณฑ์ | ค่า | เกณฑ์ผ่าน | ผ่าน |
|---|---|---|---|
| relative_deviance_reduction | 0.0716 | 0.0100 | True |
| mae_ratio | 0.9575 | 1.0200 | True |
| fold_wins | 4 | 3 | True |
| bootstrap_upper_ci_lt_0 | -0.0423 | 0.0000 | True |

- hgb_poisson__full passed all four gate checks against baseline_province_month_k30; recommended per protocol (research reference only)

ต่อ fold (ดู `fold_comparison.csv`):

| fold | วิธี | n | deviance | MAE | ชนะ baseline |
|---|---|---|---|---|---|
| 2022H1 | poisson_a0.001__full | 13,750 | 1.1165 | 0.7111 | True |
| 2022H2 | poisson_a0.001__full | 14,136 | 1.0954 | 0.6692 | True |
| 2023H1 | poisson_a0.001__full | 12,676 | 1.1129 | 0.7060 | True |
| 2023H2 | poisson_a0.001__full | 13,048 | 1.0323 | 0.6302 | True |
| 2022H1 | rf_poisson__full | 13,750 | 1.1970 | 0.7496 | True |
| 2022H2 | rf_poisson__full | 14,136 | 1.1169 | 0.6949 | True |
| 2023H1 | rf_poisson__full | 12,676 | 1.1786 | 0.7253 | False |
| 2023H2 | rf_poisson__full | 13,048 | 1.0175 | 0.6327 | True |
| 2022H1 | hgb_poisson__full | 13,750 | 1.1150 | 0.7059 | True |
| 2022H2 | hgb_poisson__full | 14,136 | 1.0684 | 0.6435 | True |
| 2023H1 | hgb_poisson__full | 12,676 | 1.0747 | 0.6743 | True |
| 2023H2 | hgb_poisson__full | 13,048 | 0.9961 | 0.6159 | True |
| 2022H1 | baseline_province_month_k30 | 13,750 | 1.2217 | 0.7280 | null |
| 2022H2 | baseline_province_month_k30 | 14,136 | 1.1505 | 0.6829 | null |
| 2023H1 | baseline_province_month_k30 | 12,676 | 1.1667 | 0.7115 | null |
| 2023H2 | baseline_province_month_k30 | 13,048 | 1.0428 | 0.6343 | null |

### การเพิ่ม feature (daily; keys เดียวกันทุกคู่; ลบ = ดีขึ้น, บวก = แย่ลง; แสดงทุกคู่ ไม่คัดเลือก)

- benefit 34 คู่, harm 2 คู่, no_change 0 คู่; ช่วง bootstrap คร่อม 0 จำนวน 7/36 คู่ (แยกไม่ออกจากศูนย์); ไม่ครบ 0 คู่

| config | variant | เทียบกับ | ที่มา | Δ deviance | relative | Δ MAE | fold ดีขึ้น | boot ล่าง | boot บน | ผล |
|---|---|---|---|---|---|---|---|---|---|---|
| hgb_poisson | calendar_traffic | core | additional_vs_core | -0.0139 | -0.0128 | -0.0047 | 4 | -0.0177 | -0.0105 | benefit |
| hgb_poisson | calendar_weather | core | additional_vs_core | -0.0061 | -0.0056 | -0.0010 | 4 | -0.0098 | -0.0026 | benefit |
| hgb_poisson | calendar | core | protocol | -0.0025 | -0.0023 | -0.0007 | 4 | -0.0041 | -0.0010 | benefit |
| hgb_poisson | calendar_traffic | calendar | protocol | -0.0114 | -0.0106 | -0.0039 | 3 | -0.0151 | -0.0087 | benefit |
| hgb_poisson | calendar_weather | calendar | protocol | -0.0036 | -0.0034 | -0.0003 | 3 | -0.0069 | -0.0002 | benefit |
| hgb_poisson | full | calendar | protocol | -0.0147 | -0.0136 | -0.0055 | 4 | -0.0198 | -0.0098 | benefit |
| hgb_poisson | full | calendar_traffic | protocol | -0.0033 | -0.0031 | -0.0016 | 3 | -0.0065 | 0.0003 | benefit |
| hgb_poisson | full | calendar_weather | protocol | -0.0111 | -0.0103 | -0.0053 | 3 | -0.0146 | -0.0081 | benefit |
| hgb_poisson | full | core | protocol | -0.0172 | -0.0159 | -0.0062 | 4 | -0.0229 | -0.0120 | benefit |
| poisson_a0.001 | calendar_traffic | core | additional_vs_core | -0.0724 | -0.0622 | -0.0210 | 4 | -0.1180 | -0.0367 | benefit |
| poisson_a0.001 | calendar_weather | core | additional_vs_core | -0.0696 | -0.0598 | -0.0228 | 4 | -0.1154 | -0.0338 | benefit |
| poisson_a0.001 | calendar | core | protocol | -0.0688 | -0.0591 | -0.0209 | 4 | -0.1140 | -0.0324 | benefit |
| poisson_a0.001 | calendar_traffic | calendar | protocol | -0.0036 | -0.0033 | -0.0001 | 3 | -0.0052 | -0.0017 | benefit |
| poisson_a0.001 | calendar_weather | calendar | protocol | -0.0009 | -0.0008 | -0.0020 | 3 | -0.0030 | 0.0013 | benefit |
| poisson_a0.001 | full | calendar | protocol | -0.0047 | -0.0043 | -0.0020 | 4 | -0.0073 | -0.0017 | benefit |
| poisson_a0.001 | full | calendar_traffic | protocol | -0.0010 | -0.0010 | -0.0019 | 3 | -0.0031 | 0.0012 | benefit |
| poisson_a0.001 | full | calendar_weather | protocol | -0.0038 | -0.0035 | -0.0001 | 3 | -0.0054 | -0.0019 | benefit |
| poisson_a0.001 | full | core | protocol | -0.0734 | -0.0631 | -0.0229 | 4 | -0.1187 | -0.0380 | benefit |
| poisson_a0.01 | calendar_traffic | core | additional_vs_core | -0.1023 | -0.0825 | -0.0255 | 4 | -0.1470 | -0.0679 | benefit |
| poisson_a0.01 | calendar_weather | core | additional_vs_core | -0.0711 | -0.0573 | -0.0209 | 4 | -0.1166 | -0.0349 | benefit |
| poisson_a0.01 | calendar | core | protocol | -0.0696 | -0.0561 | -0.0191 | 4 | -0.1149 | -0.0328 | benefit |
| poisson_a0.01 | calendar_traffic | calendar | protocol | -0.0327 | -0.0280 | -0.0064 | 3 | -0.0391 | -0.0250 | benefit |
| poisson_a0.01 | calendar_weather | calendar | protocol | -0.0015 | -0.0013 | -0.0018 | 3 | -0.0033 | 0.0005 | benefit |
| poisson_a0.01 | full | calendar | protocol | -0.0348 | -0.0297 | -0.0083 | 4 | -0.0414 | -0.0272 | benefit |
| poisson_a0.01 | full | calendar_traffic | protocol | -0.0020 | -0.0018 | -0.0020 | 4 | -0.0037 | -0.0001 | benefit |
| poisson_a0.01 | full | calendar_weather | protocol | -0.0333 | -0.0285 | -0.0066 | 3 | -0.0398 | -0.0256 | benefit |
| poisson_a0.01 | full | core | protocol | -0.1044 | -0.0842 | -0.0275 | 4 | -0.1489 | -0.0704 | benefit |
| rf_poisson | calendar_traffic | core | additional_vs_core | -0.0229 | -0.0199 | -0.0089 | 3 | -0.0349 | -0.0107 | benefit |
| rf_poisson | calendar_weather | core | additional_vs_core | 0.0015 | 0.0013 | 0.0021 | 2 | -0.0069 | 0.0100 | harm |
| rf_poisson | calendar | core | protocol | 0.0026 | 0.0022 | 0.0020 | 2 | -0.0060 | 0.0114 | harm |
| rf_poisson | calendar_traffic | calendar | protocol | -0.0255 | -0.0221 | -0.0108 | 3 | -0.0337 | -0.0180 | benefit |
| rf_poisson | calendar_weather | calendar | protocol | -0.0011 | -0.0009 | 0.0001 | 4 | -0.0028 | 0.0009 | benefit |
| rf_poisson | full | calendar | protocol | -0.0284 | -0.0246 | -0.0116 | 4 | -0.0366 | -0.0204 | benefit |
| rf_poisson | full | calendar_traffic | protocol | -0.0029 | -0.0026 | -0.0008 | 4 | -0.0044 | -0.0012 | benefit |
| rf_poisson | full | calendar_weather | protocol | -0.0273 | -0.0237 | -0.0117 | 4 | -0.0357 | -0.0197 | benefit |
| rf_poisson | full | core | protocol | -0.0258 | -0.0224 | -0.0096 | 3 | -0.0378 | -0.0140 | benefit |

- ความไวต่อความครอบคลุมของแหล่งข้อมูล (40 แถว, `ablation_coverage_sensitivity.csv`): เทียบคู่เดิมเฉพาะเซลล์ที่มี/ไม่มี weather หรือ traffic (สองวิธีใช้ keys เดียวกันเสมอ) — ความครอบคลุมเป็นผลของการเก็บข้อมูลย้อนหลังและสัมพันธ์กับปี จึง **ไม่ใช่หลักฐานว่า feature มีผล**

### Error slice ของ `hgb_poisson__full` (daily) — ไฟล์เต็ม `slices_daily.csv` (เดือน/จังหวัด/ทุกวิธีที่สนใจ)

กลุ่มที่มีน้อยกว่า 200 เซลล์หรือน้อยกว่า 30 เหตุการณ์ถูกระบุว่า "ข้อมูลน้อย"; กลุ่มว่างแสดง n = 0; กลุ่มตามผลลัพธ์ (0 เหตุการณ์ / high count >= 5 จาก OOF quantile 0.99) เป็นการวินิจฉัยย้อนหลัง ไม่ใช่ตัวทำนายหรือสาเหตุ; สถานะ missing ของ weather/traffic/bank calendar ใช้เพื่อวินิจฉัยเท่านั้น ไม่ใช่ input และไม่ใช่ข้ออ้างเชิงสาเหตุ

**pooled OOF 2022-2023 (selection evidence)**

| มิติ | กลุ่ม | n | จริง | ทำนาย | bias | MAE | RMSE | deviance | support |
|---|---|---|---|---|---|---|---|---|---|
| year | 2022 | 27,886 | 19,926 | 19269.7697 | -0.0235 | 0.6743 | 0.9821 | 1.0914 | พอใช้ |
| year | 2023 | 25,724 | 17,371 | 17052.0633 | -0.0124 | 0.6447 | 0.9216 | 1.0349 | พอใช้ |
| weekday | Mon | 7,740 | 5,566 | 5465.5178 | -0.0130 | 0.6674 | 0.9434 | 1.0616 | พอใช้ |
| weekday | Tue | 7,740 | 4,996 | 5230.2187 | 0.0303 | 0.6419 | 0.8980 | 1.0404 | พอใช้ |
| weekday | Wed | 7,646 | 5,171 | 5045.3525 | -0.0164 | 0.6541 | 0.9455 | 1.0701 | พอใช้ |
| weekday | Thu | 7,706 | 5,401 | 5104.9634 | -0.0384 | 0.6598 | 0.9476 | 1.0646 | พอใช้ |
| weekday | Fri | 7,590 | 5,674 | 5219.9960 | -0.0598 | 0.6804 | 1.0241 | 1.0816 | พอใช้ |
| weekday | Sat | 7,654 | 5,577 | 5347.6037 | -0.0300 | 0.6731 | 0.9900 | 1.0826 | พอใช้ |
| weekday | Sun | 7,534 | 4,912 | 4908.1808 | -0.0005 | 0.6439 | 0.9212 | 1.0491 | พอใช้ |
| festival | songkran_in | 388 | 956 | 787.9226 | -0.4332 | 1.5021 | 2.0502 | 1.7568 | พอใช้ |
| festival | songkran_pre_1_3 | 405 | 738 | 971.2750 | 0.5760 | 1.3612 | 1.7683 | 1.6813 | พอใช้ |
| festival | songkran_pre_4_7 | 600 | 372 | 449.2475 | 0.1287 | 0.6756 | 0.9282 | 1.1172 | พอใช้ |
| festival | songkran_post_1_3 | 366 | 585 | 447.1222 | -0.3767 | 1.1979 | 1.6951 | 1.8919 | พอใช้ |
| festival | songkran_post_4_7 | 606 | 401 | 406.7827 | 0.0095 | 0.6381 | 0.8668 | 1.0333 | พอใช้ |
| festival | new_year_in | 196 | 641 | 617.2605 | -0.1211 | 1.7015 | 2.2759 | 1.6220 | **ข้อมูลน้อย ห้ามตีความเป็นผล** |
| festival | new_year_pre_1_3 | 359 | 840 | 667.6056 | -0.4802 | 1.3081 | 1.9848 | 1.5080 | พอใช้ |
| festival | new_year_pre_4_7 | 607 | 391 | 369.3711 | -0.0356 | 0.6396 | 0.8818 | 1.0380 | พอใช้ |
| festival | new_year_post_1_3 | 321 | 640 | 796.5471 | 0.4877 | 1.3472 | 1.6931 | 1.4547 | พอใช้ |
| festival | new_year_post_4_7 | 600 | 377 | 400.3109 | 0.0389 | 0.6237 | 0.8814 | 1.0072 | พอใช้ |
| festival | none | 49,162 | 31,356 | 30408.3877 | -0.0193 | 0.6311 | 0.8967 | 1.0403 | พอใช้ |
| festival | unknown | 0 | 0.0000 | 0.0000 | null | null | null | null | ว่าง (ไม่มีเซลล์) |
| bank_calendar | known_asof | 53,610 | 37,297 | 36321.8329 | -0.0182 | 0.6601 | 0.9535 | 1.0643 | พอใช้ |
| bank_calendar | not_known_asof | 0 | 0.0000 | 0.0000 | null | null | null | null | ว่าง (ไม่มีเซลล์) |
| bank_calendar | missing | 0 | 0.0000 | 0.0000 | null | null | null | null | ว่าง (ไม่มีเซลล์) |
| weather | available | 44,390 | 31,224 | 30470.4761 | -0.0170 | 0.6654 | 0.9657 | 1.0692 | พอใช้ |
| weather | partial | 59 | 77 | 94.7210 | 0.3004 | 0.8197 | 1.1009 | 0.8735 | **ข้อมูลน้อย ห้ามตีความเป็นผล** |
| weather | missing | 9,161 | 5,996 | 5756.6358 | -0.0261 | 0.6332 | 0.8911 | 1.0416 | พอใช้ |
| traffic | available | 47,306 | 32,676 | 31126.8578 | -0.0327 | 0.6535 | 0.9425 | 1.0579 | พอใช้ |
| traffic | partial | 0 | 0.0000 | 0.0000 | null | null | null | null | ว่าง (ไม่มีเซลล์) |
| traffic | missing | 6,304 | 4,621 | 5194.9751 | 0.0910 | 0.7092 | 1.0327 | 1.1116 | พอใช้ |
| outcome_bin | 0 | 31,919 | 0.0000 | 14907.2542 | 0.4670 | 0.4670 | 0.5953 | 0.9341 | **ข้อมูลน้อย ห้ามตีความเป็นผล** |
| outcome_bin | 1 | 13,435 | 13,435 | 9487.5651 | -0.2938 | 0.5362 | 0.6381 | 0.5774 | พอใช้ |
| outcome_bin | 2-3 | 6,556 | 14,840 | 7627.1443 | -1.1002 | 1.2875 | 1.4337 | 1.9626 | พอใช้ |
| outcome_bin | 4-6 | 1,381 | 6,314 | 3158.9352 | -2.2846 | 2.3643 | 2.6268 | 3.3214 | พอใช้ |
| outcome_bin | 7-9 | 247 | 1,888 | 843.8971 | -4.2271 | 4.2367 | 4.4713 | 5.2179 | พอใช้ |
| outcome_bin | 10+ | 72 | 820 | 297.0370 | -7.2634 | 7.2634 | 7.4700 | 10.2790 | **ข้อมูลน้อย ห้ามตีความเป็นผล** |
| high_count | high_ge_5 | 904 | 5,838 | 2729.8902 | -3.4382 | 3.4681 | 3.9403 | 4.4471 | พอใช้ |
| high_count | below_5 | 52,706 | 31,459 | 33591.9427 | 0.0405 | 0.6119 | 0.8115 | 1.0062 | พอใช้ |

**2024 development diagnostic (เคยเห็นแล้วตอนพัฒนา ไม่ใช่ test อิสระ)**

| มิติ | กลุ่ม | n | จริง | ทำนาย | bias | MAE | RMSE | deviance | support |
|---|---|---|---|---|---|---|---|---|---|
| year | 2024 | 7,885 | 6,168 | 5664.1315 | -0.0639 | 0.6938 | 1.0113 | 1.0944 | พอใช้ |
| weekday | Mon | 1,145 | 806 | 779.0941 | -0.0235 | 0.6646 | 0.9198 | 1.0705 | พอใช้ |
| weekday | Tue | 993 | 747 | 666.9604 | -0.0806 | 0.6749 | 0.9917 | 1.0858 | พอใช้ |
| weekday | Wed | 1,535 | 1,258 | 1192.6615 | -0.0426 | 0.7418 | 1.0908 | 1.1794 | พอใช้ |
| weekday | Thu | 844 | 704 | 627.3275 | -0.0908 | 0.7081 | 1.0082 | 1.1004 | พอใช้ |
| weekday | Fri | 1,222 | 1,007 | 872.7459 | -0.1099 | 0.6991 | 0.9795 | 1.0763 | พอใช้ |
| weekday | Sat | 997 | 819 | 720.6935 | -0.0986 | 0.7341 | 1.1739 | 1.1663 | พอใช้ |
| weekday | Sun | 1,149 | 827 | 804.6486 | -0.0195 | 0.6240 | 0.8789 | 0.9643 | พอใช้ |
| festival | songkran_in | 0 | 0.0000 | 0.0000 | null | null | null | null | ว่าง (ไม่มีเซลล์) |
| festival | songkran_pre_1_3 | 77 | 72 | 123.4713 | 0.6685 | 1.0934 | 1.3390 | 1.6477 | **ข้อมูลน้อย ห้ามตีความเป็นผล** |
| festival | songkran_pre_4_7 | 77 | 69 | 60.1683 | -0.1147 | 0.7933 | 1.8064 | 1.2389 | **ข้อมูลน้อย ห้ามตีความเป็นผล** |
| festival | songkran_post_1_3 | 154 | 240 | 181.7582 | -0.3782 | 1.1380 | 1.5789 | 1.8130 | **ข้อมูลน้อย ห้ามตีความเป็นผล** |
| festival | songkran_post_4_7 | 230 | 207 | 170.9786 | -0.1566 | 0.6822 | 0.9342 | 1.0427 | พอใช้ |
| festival | new_year_in | 0 | 0.0000 | 0.0000 | null | null | null | null | ว่าง (ไม่มีเซลล์) |
| festival | new_year_pre_1_3 | 0 | 0.0000 | 0.0000 | null | null | null | null | ว่าง (ไม่มีเซลล์) |
| festival | new_year_pre_4_7 | 0 | 0.0000 | 0.0000 | null | null | null | null | ว่าง (ไม่มีเซลล์) |
| festival | new_year_post_1_3 | 0 | 0.0000 | 0.0000 | null | null | null | null | ว่าง (ไม่มีเซลล์) |
| festival | new_year_post_4_7 | 77 | 44 | 54.5834 | 0.1374 | 0.6272 | 0.8311 | 0.9799 | **ข้อมูลน้อย ห้ามตีความเป็นผล** |
| festival | none | 7,270 | 5,536 | 5073.1717 | -0.0637 | 0.6802 | 0.9838 | 1.0746 | พอใช้ |
| festival | unknown | 0 | 0.0000 | 0.0000 | null | null | null | null | ว่าง (ไม่มีเซลล์) |
| bank_calendar | known_asof | 7,885 | 6,168 | 5664.1315 | -0.0639 | 0.6938 | 1.0113 | 1.0944 | พอใช้ |
| bank_calendar | not_known_asof | 0 | 0.0000 | 0.0000 | null | null | null | null | ว่าง (ไม่มีเซลล์) |
| bank_calendar | missing | 0 | 0.0000 | 0.0000 | null | null | null | null | ว่าง (ไม่มีเซลล์) |
| weather | available | 0 | 0.0000 | 0.0000 | null | null | null | null | ว่าง (ไม่มีเซลล์) |
| weather | partial | 0 | 0.0000 | 0.0000 | null | null | null | null | ว่าง (ไม่มีเซลล์) |
| weather | missing | 7,885 | 6,168 | 5664.1315 | -0.0639 | 0.6938 | 1.0113 | 1.0944 | พอใช้ |
| traffic | available | 7,885 | 6,168 | 5664.1315 | -0.0639 | 0.6938 | 1.0113 | 1.0944 | พอใช้ |
| traffic | partial | 0 | 0.0000 | 0.0000 | null | null | null | null | ว่าง (ไม่มีเซลล์) |
| traffic | missing | 0 | 0.0000 | 0.0000 | null | null | null | null | ว่าง (ไม่มีเซลล์) |
| outcome_bin | 0 | 4,457 | 0.0000 | 2245.9143 | 0.5039 | 0.5039 | 0.6132 | 1.0078 | **ข้อมูลน้อย ห้ามตีความเป็นผล** |
| outcome_bin | 1 | 2,030 | 2,030 | 1470.8508 | -0.2754 | 0.4515 | 0.5392 | 0.4683 | พอใช้ |
| outcome_bin | 2-3 | 1,105 | 2,516 | 1212.4282 | -1.1797 | 1.2812 | 1.4099 | 1.7873 | พอใช้ |
| outcome_bin | 4-6 | 226 | 1,035 | 469.3293 | -2.5030 | 2.5269 | 2.7588 | 3.6979 | พอใช้ |
| outcome_bin | 7-9 | 50 | 382 | 181.2666 | -4.0147 | 4.0147 | 4.3243 | 4.8864 | **ข้อมูลน้อย ห้ามตีความเป็นผล** |
| outcome_bin | 10+ | 17 | 205 | 84.3424 | -7.0975 | 7.0975 | 7.4609 | 7.7378 | **ข้อมูลน้อย ห้ามตีความเป็นผล** |
| high_count | high_ge_5 | 163 | 1,102 | 509.9450 | -3.6322 | 3.6497 | 4.1462 | 4.6700 | **ข้อมูลน้อย ห้ามตีความเป็นผล** |
| high_count | below_5 | 7,722 | 5,066 | 5154.1865 | 0.0114 | 0.6314 | 0.8254 | 1.0189 | พอใช้ |

**2025 reused / previously-seen diagnostic (เคยใช้แล้ว ไม่ใช่ test อิสระ)**

| มิติ | กลุ่ม | n | จริง | ทำนาย | bias | MAE | RMSE | deviance | support |
|---|---|---|---|---|---|---|---|---|---|
| year | 2025 | 27,582 | 21,603 | 20146.2403 | -0.0528 | 0.7056 | 1.0608 | 1.1319 | พอใช้ |
| weekday | Mon | 3,907 | 2,876 | 2823.6239 | -0.0134 | 0.6843 | 0.9749 | 1.1119 | พอใช้ |
| weekday | Tue | 3,992 | 3,143 | 2984.1728 | -0.0398 | 0.6984 | 1.0627 | 1.1105 | พอใช้ |
| weekday | Wed | 3,983 | 3,036 | 2935.7915 | -0.0252 | 0.6849 | 0.9923 | 1.0766 | พอใช้ |
| weekday | Thu | 3,903 | 2,724 | 2751.0190 | 0.0069 | 0.6737 | 0.9451 | 1.0878 | พอใช้ |
| weekday | Fri | 3,903 | 3,194 | 2864.5749 | -0.0844 | 0.7304 | 1.1216 | 1.1718 | พอใช้ |
| weekday | Sat | 3,982 | 3,462 | 3000.4286 | -0.1159 | 0.7620 | 1.2221 | 1.2330 | พอใช้ |
| weekday | Sun | 3,912 | 3,168 | 2786.6296 | -0.0975 | 0.7052 | 1.0786 | 1.1316 | พอใช้ |
| festival | songkran_in | 154 | 454 | 342.6414 | -0.7231 | 1.6608 | 2.4191 | 1.8454 | **ข้อมูลน้อย ห้ามตีความเป็นผล** |
| festival | songkran_pre_1_3 | 231 | 599 | 484.8220 | -0.4943 | 1.5095 | 2.1909 | 1.6318 | พอใช้ |
| festival | songkran_pre_4_7 | 305 | 228 | 224.1307 | -0.0127 | 0.6795 | 0.9108 | 1.0630 | พอใช้ |
| festival | songkran_post_1_3 | 229 | 358 | 328.9014 | -0.1271 | 1.0935 | 1.5688 | 1.4747 | พอใช้ |
| festival | songkran_post_4_7 | 308 | 210 | 227.9475 | 0.0583 | 0.6613 | 0.8732 | 1.0556 | พอใช้ |
| festival | new_year_in | 76 | 241 | 228.6868 | -0.1620 | 1.7712 | 2.3055 | 1.7124 | **ข้อมูลน้อย ห้ามตีความเป็นผล** |
| festival | new_year_pre_1_3 | 231 | 605 | 519.2310 | -0.3713 | 1.6116 | 2.2252 | 2.1047 | พอใช้ |
| festival | new_year_pre_4_7 | 306 | 493 | 219.2705 | -0.8945 | 1.4204 | 2.2722 | 3.0341 | พอใช้ |
| festival | new_year_post_1_3 | 76 | 147 | 154.6757 | 0.1010 | 1.1743 | 1.3772 | 1.2561 | **ข้อมูลน้อย ห้ามตีความเป็นผล** |
| festival | new_year_post_4_7 | 307 | 298 | 219.3821 | -0.2561 | 0.8001 | 1.2302 | 1.3677 | พอใช้ |
| festival | none | 25,359 | 17,970 | 17196.5513 | -0.0305 | 0.6672 | 0.9777 | 1.0849 | พอใช้ |
| festival | unknown | 0 | 0.0000 | 0.0000 | null | null | null | null | ว่าง (ไม่มีเซลล์) |
| bank_calendar | known_asof | 27,582 | 21,603 | 20146.2403 | -0.0528 | 0.7056 | 1.0608 | 1.1319 | พอใช้ |
| bank_calendar | not_known_asof | 0 | 0.0000 | 0.0000 | null | null | null | null | ว่าง (ไม่มีเซลล์) |
| bank_calendar | missing | 0 | 0.0000 | 0.0000 | null | null | null | null | ว่าง (ไม่มีเซลล์) |
| weather | available | 0 | 0.0000 | 0.0000 | null | null | null | null | ว่าง (ไม่มีเซลล์) |
| weather | partial | 0 | 0.0000 | 0.0000 | null | null | null | null | ว่าง (ไม่มีเซลล์) |
| weather | missing | 27,582 | 21,603 | 20146.2403 | -0.0528 | 0.7056 | 1.0608 | 1.1319 | พอใช้ |
| traffic | available | 27,582 | 21,603 | 20146.2403 | -0.0528 | 0.7056 | 1.0608 | 1.1319 | พอใช้ |
| traffic | partial | 0 | 0.0000 | 0.0000 | null | null | null | null | ว่าง (ไม่มีเซลล์) |
| traffic | missing | 0 | 0.0000 | 0.0000 | null | null | null | null | ว่าง (ไม่มีเซลล์) |
| outcome_bin | 0 | 15,732 | 0.0000 | 7972.5093 | 0.5068 | 0.5068 | 0.6255 | 1.0135 | **ข้อมูลน้อย ห้ามตีความเป็นผล** |
| outcome_bin | 1 | 7,185 | 7,185 | 5195.3358 | -0.2769 | 0.4869 | 0.5851 | 0.5491 | พอใช้ |
| outcome_bin | 2-3 | 3,591 | 8,233 | 4161.9768 | -1.1337 | 1.2746 | 1.4121 | 1.8304 | พอใช้ |
| outcome_bin | 4-6 | 807 | 3,741 | 1800.6670 | -2.4044 | 2.4612 | 2.7376 | 3.5729 | พอใช้ |
| outcome_bin | 7-9 | 182 | 1,414 | 638.9755 | -4.2584 | 4.2584 | 4.4863 | 5.2500 | **ข้อมูลน้อย ห้ามตีความเป็นผล** |
| outcome_bin | 10+ | 85 | 1,030 | 376.7760 | -7.6850 | 7.6850 | 8.0818 | 10.8092 | **ข้อมูลน้อย ห้ามตีความเป็นผล** |
| high_count | high_ge_5 | 653 | 4,501 | 1992.0557 | -3.8422 | 3.8587 | 4.4521 | 5.2659 | พอใช้ |
| high_count | below_5 | 26,929 | 17,102 | 18154.1847 | 0.0391 | 0.6292 | 0.8197 | 1.0317 | พอใช้ |

### Calibration และ residual (daily)

- `calibration_bins_daily.csv`: ขอบ bin จาก quantile ของ prediction OOF เท่านั้น (ค่าซ้ำรวม bin, bin ว่างคงไว้) แล้วใช้ขอบเดิมกับ 2024/2025
- `largest_residuals_daily.csv`: residual รวมสูงสุด (ทำนาย − จริง) ตาม จังหวัด×เดือน, วันที่ และจังหวัด ของแต่ละช่วงแยกกัน

| ช่วง | bin | ขอบล่าง | ขอบบน | n | ทำนายเฉลี่ย | จริงเฉลี่ย | จริง/ทำนาย | support |
|---|---|---|---|---|---|---|---|---|
| oof | 0 | 0.0621 | 0.1843 | 5,361 | 0.1314 | 0.1323 | 1.0067 | พอใช้ |
| oof | 1 | 0.1843 | 0.2584 | 5,361 | 0.2234 | 0.2462 | 1.1019 | พอใช้ |
| oof | 2 | 0.2584 | 0.3321 | 5,361 | 0.2920 | 0.3147 | 1.0775 | พอใช้ |
| oof | 3 | 0.3321 | 0.3987 | 5,361 | 0.3662 | 0.3994 | 1.0905 | พอใช้ |
| oof | 4 | 0.3987 | 0.4701 | 5,361 | 0.4327 | 0.4570 | 1.0562 | พอใช้ |
| oof | 5 | 0.4701 | 0.5452 | 5,361 | 0.5073 | 0.5270 | 1.0388 | พอใช้ |
| oof | 6 | 0.5452 | 0.6480 | 5,361 | 0.5903 | 0.6260 | 1.0605 | พอใช้ |
| oof | 7 | 0.6480 | 0.8744 | 5,361 | 0.7472 | 0.7715 | 1.0325 | พอใช้ |
| oof | 8 | 0.8744 | 1.3901 | 5,361 | 1.0976 | 1.0767 | 0.9810 | พอใช้ |
| oof | 9 | 1.3901 | 8.5541 | 5,361 | 2.3871 | 2.4065 | 1.0081 | พอใช้ |
| development_2024 | 0 | 0.0621 | 0.1843 | 770 | 0.1258 | 0.1558 | 1.2390 | พอใช้ |
| development_2024 | 1 | 0.1843 | 0.2584 | 465 | 0.2248 | 0.1914 | 0.8515 | พอใช้ |
| development_2024 | 2 | 0.2584 | 0.3321 | 928 | 0.2954 | 0.3588 | 1.2147 | พอใช้ |
| development_2024 | 3 | 0.3321 | 0.3987 | 633 | 0.3691 | 0.3349 | 0.9074 | พอใช้ |
| development_2024 | 4 | 0.3987 | 0.4701 | 413 | 0.4299 | 0.4334 | 1.0083 | พอใช้ |
| development_2024 | 5 | 0.4701 | 0.5452 | 540 | 0.5130 | 0.5407 | 1.0541 | พอใช้ |
| development_2024 | 6 | 0.5452 | 0.6480 | 838 | 0.6003 | 0.6396 | 1.0656 | พอใช้ |
| development_2024 | 7 | 0.6480 | 0.8744 | 1,442 | 0.7409 | 0.7240 | 0.9772 | พอใช้ |
| development_2024 | 8 | 0.8744 | 1.3901 | 1,169 | 1.1206 | 1.2352 | 1.1023 | พอใช้ |
| development_2024 | 9 | 1.3901 | 8.5541 | 687 | 2.3568 | 2.7933 | 1.1852 | พอใช้ |
| reused_seen_2025 | 0 | 0.0621 | 0.1843 | 2,728 | 0.1238 | 0.2251 | 1.8180 | พอใช้ |
| reused_seen_2025 | 1 | 0.1843 | 0.2584 | 1,955 | 0.2258 | 0.2614 | 1.1575 | พอใช้ |
| reused_seen_2025 | 2 | 0.2584 | 0.3321 | 3,048 | 0.2927 | 0.2927 | 0.9997 | พอใช้ |
| reused_seen_2025 | 3 | 0.3321 | 0.3987 | 2,083 | 0.3667 | 0.3495 | 0.9532 | พอใช้ |
| reused_seen_2025 | 4 | 0.3987 | 0.4701 | 1,413 | 0.4300 | 0.3539 | 0.8230 | พอใช้ |
| reused_seen_2025 | 5 | 0.4701 | 0.5452 | 2,114 | 0.5106 | 0.4976 | 0.9747 | พอใช้ |
| reused_seen_2025 | 6 | 0.5452 | 0.6480 | 3,387 | 0.5983 | 0.6398 | 1.0693 | พอใช้ |
| reused_seen_2025 | 7 | 0.6480 | 0.8744 | 4,570 | 0.7364 | 0.7374 | 1.0014 | พอใช้ |
| reused_seen_2025 | 8 | 0.8744 | 1.3901 | 3,626 | 1.1275 | 1.1867 | 1.0525 | พอใช้ |
| reused_seen_2025 | 9 | 1.3901 | 8.5541 | 2,658 | 2.4619 | 2.8089 | 1.1410 | พอใช้ |

residual รวมสูงสุด 5 อันดับ (จังหวัด×เดือน) ของ `hgb_poisson__full`:

| ช่วง | จังหวัด | เดือน | n | จริง | ทำนาย | residual | support |
|---|---|---|---|---|---|---|---|
| oof | กรุงเทพมหานคร | 2022-08 | 28 | 158 | 84.4375 | -73.5625 | **ข้อมูลน้อย ห้ามตีความเป็นผล** |
| oof | กรุงเทพมหานคร | 2022-11 | 23 | 143 | 77.4718 | -65.5282 | **ข้อมูลน้อย ห้ามตีความเป็นผล** |
| oof | นครราชสีมา | 2022-01 | 30 | 126 | 66.6530 | -59.3470 | **ข้อมูลน้อย ห้ามตีความเป็นผล** |
| oof | ชลบุรี | 2023-03 | 30 | 141 | 85.4627 | -55.5373 | **ข้อมูลน้อย ห้ามตีความเป็นผล** |
| oof | กรุงเทพมหานคร | 2022-12 | 28 | 151 | 98.7299 | -52.2701 | **ข้อมูลน้อย ห้ามตีความเป็นผล** |
| development_2024 | กรุงเทพมหานคร | 2024-02 | 12 | 104 | 64.7328 | -39.2672 | **ข้อมูลน้อย ห้ามตีความเป็นผล** |
| development_2024 | นครราชสีมา | 2024-03 | 20 | 89 | 51.9184 | -37.0816 | **ข้อมูลน้อย ห้ามตีความเป็นผล** |
| development_2024 | กรุงเทพมหานคร | 2024-03 | 9 | 79 | 47.4649 | -31.5351 | **ข้อมูลน้อย ห้ามตีความเป็นผล** |
| development_2024 | ชลบุรี | 2024-03 | 20 | 98 | 73.1124 | -24.8876 | **ข้อมูลน้อย ห้ามตีความเป็นผล** |
| development_2024 | กรุงเทพมหานคร | 2024-04 | 6 | 57 | 33.2023 | -23.7977 | **ข้อมูลน้อย ห้ามตีความเป็นผล** |
| reused_seen_2025 | กรุงเทพมหานคร | 2025-09 | 24 | 190 | 103.4212 | -86.5788 | **ข้อมูลน้อย ห้ามตีความเป็นผล** |
| reused_seen_2025 | กรุงเทพมหานคร | 2025-08 | 23 | 167 | 94.2675 | -72.7325 | **ข้อมูลน้อย ห้ามตีความเป็นผล** |
| reused_seen_2025 | กรุงเทพมหานคร | 2025-12 | 24 | 189 | 121.0405 | -67.9595 | **ข้อมูลน้อย ห้ามตีความเป็นผล** |
| reused_seen_2025 | กรุงเทพมหานคร | 2025-04 | 17 | 141 | 81.2901 | -59.7099 | **ข้อมูลน้อย ห้ามตีความเป็นผล** |
| reused_seen_2025 | กรุงเทพมหานคร | 2025-07 | 18 | 126 | 69.9624 | -56.0376 | **ข้อมูลน้อย ห้ามตีความเป็นผล** |

## 2.2 หน่วย 6h: ตัวเลือกและเหตุผล

- **ข้อเสนอตาม protocol: `hgb_poisson__calendar_traffic`** (candidate_passed_gate)
- best candidate จาก 3 ตระกูล: `hgb_poisson__calendar_traffic`; strongest baseline: `baseline_province_block_mean`; ตัวแทนแต่ละตระกูล: {'poisson': 'poisson_a0.001__full', 'rf': 'rf_poisson__full', 'hgb': 'hgb_poisson__calendar_traffic'}
- วิธีที่ล้มเหลว/ไม่ครบ fold: ไม่มี

| วิธี | บทบาท | deviance OOF | MAE | RMSE | bias | ลด deviance vs baseline | ชนะ fold | boot ล่าง | boot บน |
|---|---|---|---|---|---|---|---|---|---|
| poisson_a0.001__full | family_best:poisson | 0.5963 | 0.2677 | 0.4539 | 0.0019 | 0.0189 | 3 | -0.0274 | 0.0006 |
| rf_poisson__full | family_best:rf | 0.6018 | 0.2637 | 0.4523 | -0.0010 | 0.0097 | 3 | -0.0214 | 0.0057 |
| hgb_poisson__calendar_traffic | family_best:hgb best_candidate RECOMMENDED | 0.5835 | 0.2578 | 0.4478 | -0.0024 | 0.0399 | 4 | -0.0412 | -0.0108 |
| baseline_zero |  | null | 0.1739 | 0.5152 | -0.1739 | null | null | null | null |
| baseline_global_mean |  | 0.7112 | 0.3008 | 0.4850 | 0.0028 | -0.1702 | 0.0000 | null | null |
| baseline_province_block_mean | strongest_baseline | 0.6078 | 0.2676 | 0.4569 | -0.0000 | 0.0000 | 0.0000 | null | null |
| baseline_province_block_weekday_k10 |  | 0.6163 | 0.2674 | 0.4580 | -0.0001 | -0.0140 | 0.0000 | null | null |
| baseline_province_block_month_k30 |  | 0.6108 | 0.2658 | 0.4572 | -0.0011 | -0.0050 | 1 | null | null |
| baseline_recent90_province_block_mean |  | 0.6260 | 0.2709 | 0.4580 | 0.0074 | -0.0300 | 0.0000 | null | null |

boot = ช่วง 95% ของผลต่าง deviance (วิธี − strongest baseline) แบบ paired 7-day block bootstrap; ใช้ใน gate เฉพาะ best candidate, ของตระกูลอื่นเป็นข้อมูลสำรวจเพิ่ม ไม่ปรับ multiple comparison

**Gate (ค่าที่ล็อกไว้และคำนวณซ้ำได้ตรงกัน):**

| เกณฑ์ | ค่า | เกณฑ์ผ่าน | ผ่าน |
|---|---|---|---|
| relative_deviance_reduction | 0.0399 | 0.0100 | True |
| mae_ratio | 0.9633 | 1.0200 | True |
| fold_wins | 4 | 3 | True |
| bootstrap_upper_ci_lt_0 | -0.0108 | 0.0000 | True |

- hgb_poisson__calendar_traffic passed all four gate checks against baseline_province_block_mean; recommended per protocol (research reference only)

ต่อ fold (ดู `fold_comparison.csv`):

| fold | วิธี | n | deviance | MAE | ชนะ baseline |
|---|---|---|---|---|---|
| 2022H1 | poisson_a0.001__full | 55,000 | 0.6155 | 0.2856 | True |
| 2022H2 | poisson_a0.001__full | 56,544 | 0.5934 | 0.2596 | True |
| 2023H1 | poisson_a0.001__full | 50,704 | 0.6127 | 0.2798 | True |
| 2023H2 | poisson_a0.001__full | 52,192 | 0.5632 | 0.2458 | False |
| 2022H1 | rf_poisson__full | 55,000 | 0.6350 | 0.2807 | True |
| 2022H2 | rf_poisson__full | 56,544 | 0.5956 | 0.2594 | True |
| 2023H1 | rf_poisson__full | 50,704 | 0.6209 | 0.2714 | False |
| 2023H2 | rf_poisson__full | 52,192 | 0.5551 | 0.2429 | True |
| 2022H1 | hgb_poisson__calendar_traffic | 55,000 | 0.6091 | 0.2762 | True |
| 2022H2 | hgb_poisson__calendar_traffic | 56,544 | 0.5806 | 0.2477 | True |
| 2023H1 | hgb_poisson__calendar_traffic | 50,704 | 0.5949 | 0.2678 | True |
| 2023H2 | hgb_poisson__calendar_traffic | 52,192 | 0.5487 | 0.2394 | True |
| 2022H1 | baseline_province_block_mean | 55,000 | 0.6452 | 0.2763 | null |
| 2022H2 | baseline_province_block_mean | 56,544 | 0.6044 | 0.2683 | null |
| 2023H1 | baseline_province_block_mean | 50,704 | 0.6173 | 0.2703 | null |
| 2023H2 | baseline_province_block_mean | 52,192 | 0.5626 | 0.2550 | null |

### การเพิ่ม feature (6h; keys เดียวกันทุกคู่; ลบ = ดีขึ้น, บวก = แย่ลง; แสดงทุกคู่ ไม่คัดเลือก)

- benefit 33 คู่, harm 3 คู่, no_change 0 คู่; ช่วง bootstrap คร่อม 0 จำนวน 9/36 คู่ (แยกไม่ออกจากศูนย์); ไม่ครบ 0 คู่

| config | variant | เทียบกับ | ที่มา | Δ deviance | relative | Δ MAE | fold ดีขึ้น | boot ล่าง | boot บน | ผล |
|---|---|---|---|---|---|---|---|---|---|---|
| hgb_poisson | calendar_traffic | core | additional_vs_core | -0.0035 | -0.0060 | 0.0006 | 3 | -0.0047 | -0.0024 | benefit |
| hgb_poisson | calendar_weather | core | additional_vs_core | -0.0003 | -0.0005 | 0.0011 | 3 | -0.0015 | 0.0012 | benefit |
| hgb_poisson | calendar | core | protocol | -0.0002 | -0.0004 | -0.0001 | 3 | -0.0009 | 0.0004 | benefit |
| hgb_poisson | calendar_traffic | calendar | protocol | -0.0033 | -0.0056 | 0.0007 | 3 | -0.0041 | -0.0026 | benefit |
| hgb_poisson | calendar_weather | calendar | protocol | -0.0000 | -0.0001 | 0.0013 | 2 | -0.0012 | 0.0013 | benefit |
| hgb_poisson | full | calendar | protocol | -0.0030 | -0.0051 | 0.0008 | 3 | -0.0045 | -0.0013 | benefit |
| hgb_poisson | full | calendar_traffic | protocol | 0.0003 | 0.0005 | 0.0001 | 1 | -0.0009 | 0.0016 | harm |
| hgb_poisson | full | calendar_weather | protocol | -0.0030 | -0.0050 | -0.0004 | 3 | -0.0038 | -0.0022 | benefit |
| hgb_poisson | full | core | protocol | -0.0032 | -0.0055 | 0.0007 | 3 | -0.0049 | -0.0016 | benefit |
| poisson_a0.001 | calendar_traffic | core | additional_vs_core | -0.0211 | -0.0342 | -0.0060 | 4 | -0.0329 | -0.0121 | benefit |
| poisson_a0.001 | calendar_weather | core | additional_vs_core | -0.0182 | -0.0294 | -0.0089 | 4 | -0.0304 | -0.0086 | benefit |
| poisson_a0.001 | calendar | core | protocol | -0.0178 | -0.0288 | -0.0079 | 4 | -0.0301 | -0.0084 | benefit |
| poisson_a0.001 | calendar_traffic | calendar | protocol | -0.0033 | -0.0055 | 0.0019 | 3 | -0.0042 | -0.0023 | benefit |
| poisson_a0.001 | calendar_weather | calendar | protocol | -0.0004 | -0.0006 | -0.0010 | 2 | -0.0009 | 0.0001 | benefit |
| poisson_a0.001 | full | calendar | protocol | -0.0038 | -0.0063 | 0.0009 | 4 | -0.0047 | -0.0027 | benefit |
| poisson_a0.001 | full | calendar_traffic | protocol | -0.0005 | -0.0008 | -0.0010 | 4 | -0.0010 | -0.0000 | benefit |
| poisson_a0.001 | full | calendar_weather | protocol | -0.0034 | -0.0057 | 0.0019 | 3 | -0.0043 | -0.0024 | benefit |
| poisson_a0.001 | full | core | protocol | -0.0216 | -0.0350 | -0.0070 | 4 | -0.0335 | -0.0124 | benefit |
| poisson_a0.01 | calendar_traffic | core | additional_vs_core | -0.0400 | -0.0600 | -0.0052 | 4 | -0.0519 | -0.0308 | benefit |
| poisson_a0.01 | calendar_weather | core | additional_vs_core | -0.0186 | -0.0280 | -0.0105 | 4 | -0.0310 | -0.0089 | benefit |
| poisson_a0.01 | calendar | core | protocol | -0.0183 | -0.0275 | -0.0096 | 4 | -0.0306 | -0.0086 | benefit |
| poisson_a0.01 | calendar_traffic | calendar | protocol | -0.0217 | -0.0334 | 0.0044 | 3 | -0.0249 | -0.0185 | benefit |
| poisson_a0.01 | calendar_weather | calendar | protocol | -0.0003 | -0.0005 | -0.0009 | 4 | -0.0007 | 0.0001 | benefit |
| poisson_a0.01 | full | calendar | protocol | -0.0222 | -0.0343 | 0.0034 | 4 | -0.0255 | -0.0191 | benefit |
| poisson_a0.01 | full | calendar_traffic | protocol | -0.0006 | -0.0009 | -0.0010 | 4 | -0.0009 | -0.0001 | benefit |
| poisson_a0.01 | full | calendar_weather | protocol | -0.0219 | -0.0338 | 0.0043 | 3 | -0.0252 | -0.0187 | benefit |
| poisson_a0.01 | full | core | protocol | -0.0405 | -0.0608 | -0.0062 | 4 | -0.0525 | -0.0313 | benefit |
| rf_poisson | calendar_traffic | core | additional_vs_core | -0.0075 | -0.0122 | 0.0002 | 3 | -0.0103 | -0.0041 | benefit |
| rf_poisson | calendar_weather | core | additional_vs_core | 0.0014 | 0.0023 | 0.0002 | 0 | -0.0004 | 0.0035 | harm |
| rf_poisson | calendar | core | protocol | 0.0018 | 0.0029 | 0.0003 | 0 | 0.0002 | 0.0039 | harm |
| rf_poisson | calendar_traffic | calendar | protocol | -0.0093 | -0.0151 | -0.0001 | 3 | -0.0112 | -0.0074 | benefit |
| rf_poisson | calendar_weather | calendar | protocol | -0.0004 | -0.0006 | -0.0001 | 4 | -0.0009 | 0.0002 | benefit |
| rf_poisson | full | calendar | protocol | -0.0093 | -0.0152 | 0.0002 | 4 | -0.0115 | -0.0072 | benefit |
| rf_poisson | full | calendar_traffic | protocol | -0.0001 | -0.0001 | 0.0003 | 2 | -0.0009 | 0.0007 | benefit |
| rf_poisson | full | calendar_weather | protocol | -0.0089 | -0.0146 | 0.0003 | 3 | -0.0110 | -0.0068 | benefit |
| rf_poisson | full | core | protocol | -0.0075 | -0.0123 | 0.0005 | 3 | -0.0101 | -0.0050 | benefit |

- ความไวต่อความครอบคลุมของแหล่งข้อมูล (40 แถว, `ablation_coverage_sensitivity.csv`): เทียบคู่เดิมเฉพาะเซลล์ที่มี/ไม่มี weather หรือ traffic (สองวิธีใช้ keys เดียวกันเสมอ) — ความครอบคลุมเป็นผลของการเก็บข้อมูลย้อนหลังและสัมพันธ์กับปี จึง **ไม่ใช่หลักฐานว่า feature มีผล**

### Error slice ของ `hgb_poisson__calendar_traffic` (6h) — ไฟล์เต็ม `slices_6h.csv` (เดือน/จังหวัด/ทุกวิธีที่สนใจ)

กลุ่มที่มีน้อยกว่า 200 เซลล์หรือน้อยกว่า 30 เหตุการณ์ถูกระบุว่า "ข้อมูลน้อย"; กลุ่มว่างแสดง n = 0; กลุ่มตามผลลัพธ์ (0 เหตุการณ์ / high count >= 2 จาก OOF quantile 0.99) เป็นการวินิจฉัยย้อนหลัง ไม่ใช่ตัวทำนายหรือสาเหตุ; สถานะ missing ของ weather/traffic/bank calendar ใช้เพื่อวินิจฉัยเท่านั้น ไม่ใช่ input และไม่ใช่ข้ออ้างเชิงสาเหตุ

**pooled OOF 2022-2023 (selection evidence)**

| มิติ | กลุ่ม | n | จริง | ทำนาย | bias | MAE | RMSE | deviance | support |
|---|---|---|---|---|---|---|---|---|---|
| year | 2022 | 111,544 | 19,926 | 19685.3083 | -0.0022 | 0.2618 | 0.4553 | 0.5946 | พอใช้ |
| year | 2023 | 102,896 | 17,371 | 17086.4919 | -0.0028 | 0.2534 | 0.4395 | 0.5715 | พอใช้ |
| weekday | Mon | 30,960 | 5,566 | 5491.5646 | -0.0024 | 0.2651 | 0.4534 | 0.5992 | พอใช้ |
| weekday | Tue | 30,960 | 4,996 | 5364.5975 | 0.0119 | 0.2506 | 0.4262 | 0.5627 | พอใช้ |
| weekday | Wed | 30,584 | 5,171 | 5099.3486 | -0.0023 | 0.2536 | 0.4414 | 0.5769 | พอใช้ |
| weekday | Thu | 30,824 | 5,401 | 5163.2865 | -0.0077 | 0.2568 | 0.4461 | 0.5835 | พอใช้ |
| weekday | Fri | 30,360 | 5,674 | 5298.8028 | -0.0124 | 0.2656 | 0.4683 | 0.5969 | พอใช้ |
| weekday | Sat | 30,616 | 5,577 | 5406.8928 | -0.0056 | 0.2631 | 0.4647 | 0.5949 | พอใช้ |
| weekday | Sun | 30,136 | 4,912 | 4947.3073 | 0.0012 | 0.2494 | 0.4330 | 0.5706 | พอใช้ |
| festival | songkran_in | 1,552 | 956 | 854.4505 | -0.0654 | 0.6511 | 0.9097 | 1.1697 | พอใช้ |
| festival | songkran_pre_1_3 | 1,620 | 738 | 1032.3389 | 0.1817 | 0.5957 | 0.7833 | 1.0263 | พอใช้ |
| festival | songkran_pre_4_7 | 2,400 | 372 | 479.2829 | 0.0447 | 0.2726 | 0.4336 | 0.6009 | พอใช้ |
| festival | songkran_post_1_3 | 1,464 | 585 | 492.9830 | -0.0629 | 0.4772 | 0.7162 | 1.0173 | พอใช้ |
| festival | songkran_post_4_7 | 2,424 | 401 | 410.4541 | 0.0039 | 0.2550 | 0.4242 | 0.5768 | พอใช้ |
| festival | new_year_in | 784 | 641 | 665.1274 | 0.0308 | 0.7326 | 0.9714 | 1.1364 | พอใช้ |
| festival | new_year_pre_1_3 | 1,436 | 840 | 720.2500 | -0.0834 | 0.5662 | 0.8428 | 0.9971 | พอใช้ |
| festival | new_year_pre_4_7 | 2,428 | 391 | 401.0181 | 0.0041 | 0.2529 | 0.4217 | 0.5724 | พอใช้ |
| festival | new_year_post_1_3 | 1,284 | 640 | 812.2783 | 0.1342 | 0.6058 | 0.7755 | 1.0235 | พอใช้ |
| festival | new_year_post_4_7 | 2,400 | 377 | 413.9414 | 0.0154 | 0.2524 | 0.4202 | 0.5468 | พอใช้ |
| festival | none | 196,648 | 31,356 | 30489.6758 | -0.0044 | 0.2438 | 0.4260 | 0.5644 | พอใช้ |
| festival | unknown | 0 | 0.0000 | 0.0000 | null | null | null | null | ว่าง (ไม่มีเซลล์) |
| bank_calendar | known_asof | 214,440 | 37,297 | 36771.8002 | -0.0024 | 0.2578 | 0.4478 | 0.5835 | พอใช้ |
| bank_calendar | not_known_asof | 0 | 0.0000 | 0.0000 | null | null | null | null | ว่าง (ไม่มีเซลล์) |
| bank_calendar | missing | 0 | 0.0000 | 0.0000 | null | null | null | null | ว่าง (ไม่มีเซลล์) |
| weather | available | 177,560 | 31,224 | 31040.8208 | -0.0010 | 0.2591 | 0.4516 | 0.5855 | พอใช้ |
| weather | partial | 236 | 77 | 102.6476 | 0.1087 | 0.3992 | 0.5880 | 0.6947 | พอใช้ |
| weather | missing | 36,644 | 5,996 | 5628.3317 | -0.0100 | 0.2504 | 0.4277 | 0.5734 | พอใช้ |
| traffic | available | 189,224 | 32,676 | 31700.0251 | -0.0052 | 0.2553 | 0.4450 | 0.5820 | พอใช้ |
| traffic | partial | 0 | 0.0000 | 0.0000 | null | null | null | null | ว่าง (ไม่มีเซลล์) |
| traffic | missing | 25,216 | 4,621 | 5071.7750 | 0.0179 | 0.2761 | 0.4679 | 0.5947 | พอใช้ |
| outcome_bin | 0 | 184,176 | 0.0000 | 27150.8784 | 0.1474 | 0.1474 | 0.2063 | 0.2948 | **ข้อมูลน้อย ห้ามตีความเป็นผล** |
| outcome_bin | 1 | 25,069 | 25,069 | 6796.1299 | -0.7289 | 0.7461 | 0.7764 | 1.8447 | พอใช้ |
| outcome_bin | 2-3 | 4,817 | 10,494 | 2461.2975 | -1.6676 | 1.6707 | 1.7431 | 4.3931 | พอใช้ |
| outcome_bin | 4-6 | 362 | 1,611 | 346.7922 | -3.4923 | 3.4923 | 3.5942 | 8.5378 | พอใช้ |
| outcome_bin | 7-9 | 15 | 112 | 16.4927 | -6.3672 | 6.3672 | 6.4216 | 17.7833 | **ข้อมูลน้อย ห้ามตีความเป็นผล** |
| outcome_bin | 10+ | 1 | 11 | 0.2094 | -10.7906 | 10.7906 | 10.7906 | 65.5656 | **ข้อมูลน้อย ห้ามตีความเป็นผล** |
| high_count | high_ge_2 | 5,195 | 12,228 | 2824.7919 | -1.8100 | 1.8130 | 1.9644 | 4.7323 | พอใช้ |
| high_count | below_2 | 209,245 | 25,069 | 33947.0083 | 0.0424 | 0.2191 | 0.3312 | 0.4805 | พอใช้ |
| time_block | 00-06 | 53,610 | 7,240 | 6607.0930 | -0.0118 | 0.2094 | 0.3817 | 0.5146 | พอใช้ |
| time_block | 06-12 | 53,610 | 9,949 | 9656.3033 | -0.0055 | 0.2729 | 0.4720 | 0.6151 | พอใช้ |
| time_block | 12-18 | 53,610 | 11,385 | 11301.7585 | -0.0016 | 0.2991 | 0.5015 | 0.6469 | พอใช้ |
| time_block | 18-24 | 53,610 | 8,723 | 9206.6453 | 0.0090 | 0.2496 | 0.4266 | 0.5575 | พอใช้ |

**2024 development diagnostic (เคยเห็นแล้วตอนพัฒนา ไม่ใช่ test อิสระ)**

| มิติ | กลุ่ม | n | จริง | ทำนาย | bias | MAE | RMSE | deviance | support |
|---|---|---|---|---|---|---|---|---|---|
| year | 2024 | 31,540 | 6,168 | 5313.8432 | -0.0271 | 0.2719 | 0.4744 | 0.6159 | พอใช้ |
| weekday | Mon | 4,580 | 806 | 733.6115 | -0.0158 | 0.2573 | 0.4435 | 0.5899 | พอใช้ |
| weekday | Tue | 3,972 | 747 | 633.5865 | -0.0286 | 0.2648 | 0.4810 | 0.6136 | พอใช้ |
| weekday | Wed | 6,140 | 1,258 | 1119.8528 | -0.0225 | 0.2848 | 0.4977 | 0.6319 | พอใช้ |
| weekday | Thu | 3,376 | 704 | 582.5070 | -0.0360 | 0.2801 | 0.4804 | 0.6282 | พอใช้ |
| weekday | Fri | 4,888 | 1,007 | 817.3502 | -0.0388 | 0.2793 | 0.4759 | 0.6361 | พอใช้ |
| weekday | Sat | 3,988 | 819 | 673.7686 | -0.0364 | 0.2792 | 0.5133 | 0.6380 | พอใช้ |
| weekday | Sun | 4,596 | 827 | 753.1666 | -0.0161 | 0.2551 | 0.4229 | 0.5728 | พอใช้ |
| festival | songkran_in | 0 | 0.0000 | 0.0000 | null | null | null | null | ว่าง (ไม่มีเซลล์) |
| festival | songkran_pre_1_3 | 308 | 72 | 107.3969 | 0.1149 | 0.4134 | 0.6164 | 0.7640 | พอใช้ |
| festival | songkran_pre_4_7 | 308 | 69 | 57.2643 | -0.0381 | 0.2916 | 0.5854 | 0.6148 | พอใช้ |
| festival | songkran_post_1_3 | 616 | 240 | 180.0501 | -0.0973 | 0.4484 | 0.7115 | 0.9642 | พอใช้ |
| festival | songkran_post_4_7 | 920 | 207 | 162.3078 | -0.0486 | 0.2967 | 0.4898 | 0.6855 | พอใช้ |
| festival | new_year_in | 0 | 0.0000 | 0.0000 | null | null | null | null | ว่าง (ไม่มีเซลล์) |
| festival | new_year_pre_1_3 | 0 | 0.0000 | 0.0000 | null | null | null | null | ว่าง (ไม่มีเซลล์) |
| festival | new_year_pre_4_7 | 0 | 0.0000 | 0.0000 | null | null | null | null | ว่าง (ไม่มีเซลล์) |
| festival | new_year_post_1_3 | 0 | 0.0000 | 0.0000 | null | null | null | null | ว่าง (ไม่มีเซลล์) |
| festival | new_year_post_4_7 | 308 | 44 | 52.6738 | 0.0282 | 0.2414 | 0.3579 | 0.5235 | พอใช้ |
| festival | none | 29,080 | 5,536 | 4754.1503 | -0.0269 | 0.2660 | 0.4656 | 0.6058 | พอใช้ |
| festival | unknown | 0 | 0.0000 | 0.0000 | null | null | null | null | ว่าง (ไม่มีเซลล์) |
| bank_calendar | known_asof | 31,540 | 6,168 | 5313.8432 | -0.0271 | 0.2719 | 0.4744 | 0.6159 | พอใช้ |
| bank_calendar | not_known_asof | 0 | 0.0000 | 0.0000 | null | null | null | null | ว่าง (ไม่มีเซลล์) |
| bank_calendar | missing | 0 | 0.0000 | 0.0000 | null | null | null | null | ว่าง (ไม่มีเซลล์) |
| weather | available | 0 | 0.0000 | 0.0000 | null | null | null | null | ว่าง (ไม่มีเซลล์) |
| weather | partial | 0 | 0.0000 | 0.0000 | null | null | null | null | ว่าง (ไม่มีเซลล์) |
| weather | missing | 31,540 | 6,168 | 5313.8432 | -0.0271 | 0.2719 | 0.4744 | 0.6159 | พอใช้ |
| traffic | available | 31,540 | 6,168 | 5313.8432 | -0.0271 | 0.2719 | 0.4744 | 0.6159 | พอใช้ |
| traffic | partial | 0 | 0.0000 | 0.0000 | null | null | null | null | ว่าง (ไม่มีเซลล์) |
| traffic | missing | 0 | 0.0000 | 0.0000 | null | null | null | null | ว่าง (ไม่มีเซลล์) |
| outcome_bin | 0 | 26,622 | 0.0000 | 3838.4894 | 0.1442 | 0.1442 | 0.1902 | 0.2884 | **ข้อมูลน้อย ห้ามตีความเป็นผล** |
| outcome_bin | 1 | 4,021 | 4,021 | 1020.3210 | -0.7463 | 0.7573 | 0.7801 | 1.8358 | พอใช้ |
| outcome_bin | 2-3 | 817 | 1,775 | 373.1826 | -1.7158 | 1.7158 | 1.7662 | 4.5157 | พอใช้ |
| outcome_bin | 4-6 | 73 | 322 | 73.5784 | -3.4030 | 3.4030 | 3.4932 | 7.8155 | **ข้อมูลน้อย ห้ามตีความเป็นผล** |
| outcome_bin | 7-9 | 7 | 50 | 8.2718 | -5.9612 | 5.9612 | 5.9797 | 15.4035 | **ข้อมูลน้อย ห้ามตีความเป็นผล** |
| outcome_bin | 10+ | 0 | 0.0000 | 0.0000 | null | null | null | null | ว่าง (ไม่มีเซลล์) |
| high_count | high_ge_2 | 897 | 2,147 | 455.0328 | -1.8863 | 1.8863 | 2.0281 | 4.8692 | พอใช้ |
| high_count | below_2 | 30,643 | 4,021 | 4858.8104 | 0.0273 | 0.2246 | 0.3336 | 0.4914 | พอใช้ |
| time_block | 00-06 | 7,885 | 1,181 | 1020.9044 | -0.0203 | 0.2240 | 0.3980 | 0.5445 | พอใช้ |
| time_block | 06-12 | 7,885 | 1,698 | 1405.9040 | -0.0370 | 0.2909 | 0.5025 | 0.6481 | พอใช้ |
| time_block | 12-18 | 7,885 | 1,926 | 1622.4048 | -0.0385 | 0.3191 | 0.5476 | 0.6975 | พอใช้ |
| time_block | 18-24 | 7,885 | 1,363 | 1264.6301 | -0.0125 | 0.2535 | 0.4354 | 0.5736 | พอใช้ |

**2025 reused / previously-seen diagnostic (เคยใช้แล้ว ไม่ใช่ test อิสระ)**

| มิติ | กลุ่ม | n | จริง | ทำนาย | bias | MAE | RMSE | deviance | support |
|---|---|---|---|---|---|---|---|---|---|
| year | 2025 | 110,328 | 21,603 | 19120.0501 | -0.0225 | 0.2725 | 0.4852 | 0.6214 | พอใช้ |
| weekday | Mon | 15,628 | 2,876 | 2680.6575 | -0.0125 | 0.2635 | 0.4590 | 0.6036 | พอใช้ |
| weekday | Tue | 15,968 | 3,143 | 2893.7051 | -0.0156 | 0.2736 | 0.4947 | 0.6134 | พอใช้ |
| weekday | Wed | 15,932 | 3,036 | 2790.8525 | -0.0154 | 0.2679 | 0.4646 | 0.6029 | พอใช้ |
| weekday | Thu | 15,612 | 2,724 | 2594.3178 | -0.0083 | 0.2593 | 0.4470 | 0.5953 | พอใช้ |
| weekday | Fri | 15,612 | 3,194 | 2710.9400 | -0.0309 | 0.2811 | 0.5054 | 0.6463 | พอใช้ |
| weekday | Sat | 15,928 | 3,462 | 2821.0141 | -0.0402 | 0.2883 | 0.5232 | 0.6580 | พอใช้ |
| weekday | Sun | 15,648 | 3,168 | 2628.5631 | -0.0345 | 0.2733 | 0.4971 | 0.6300 | พอใช้ |
| festival | songkran_in | 616 | 454 | 346.1176 | -0.1751 | 0.7110 | 1.0589 | 1.2768 | พอใช้ |
| festival | songkran_pre_1_3 | 924 | 599 | 465.0725 | -0.1449 | 0.6398 | 0.9333 | 1.1246 | พอใช้ |
| festival | songkran_pre_4_7 | 1,220 | 228 | 219.5437 | -0.0069 | 0.2747 | 0.4482 | 0.6079 | พอใช้ |
| festival | songkran_post_1_3 | 916 | 358 | 333.7704 | -0.0265 | 0.4679 | 0.6825 | 0.8892 | พอใช้ |
| festival | songkran_post_4_7 | 1,232 | 210 | 217.0942 | 0.0058 | 0.2537 | 0.4369 | 0.5664 | พอใช้ |
| festival | new_year_in | 304 | 241 | 226.5973 | -0.0474 | 0.7484 | 0.9799 | 1.1496 | พอใช้ |
| festival | new_year_pre_1_3 | 924 | 605 | 534.9948 | -0.0758 | 0.6373 | 0.8948 | 1.2017 | พอใช้ |
| festival | new_year_pre_4_7 | 1,224 | 493 | 206.2038 | -0.2343 | 0.4490 | 0.8523 | 1.2804 | พอใช้ |
| festival | new_year_post_1_3 | 304 | 147 | 146.4586 | -0.0018 | 0.5653 | 0.7401 | 0.9721 | พอใช้ |
| festival | new_year_post_4_7 | 1,228 | 298 | 207.1706 | -0.0740 | 0.3090 | 0.5518 | 0.7542 | พอใช้ |
| festival | none | 101,436 | 17,970 | 16217.0266 | -0.0173 | 0.2567 | 0.4562 | 0.5938 | พอใช้ |
| festival | unknown | 0 | 0.0000 | 0.0000 | null | null | null | null | ว่าง (ไม่มีเซลล์) |
| bank_calendar | known_asof | 110,328 | 21,603 | 19120.0501 | -0.0225 | 0.2725 | 0.4852 | 0.6214 | พอใช้ |
| bank_calendar | not_known_asof | 0 | 0.0000 | 0.0000 | null | null | null | null | ว่าง (ไม่มีเซลล์) |
| bank_calendar | missing | 0 | 0.0000 | 0.0000 | null | null | null | null | ว่าง (ไม่มีเซลล์) |
| weather | available | 0 | 0.0000 | 0.0000 | null | null | null | null | ว่าง (ไม่มีเซลล์) |
| weather | partial | 0 | 0.0000 | 0.0000 | null | null | null | null | ว่าง (ไม่มีเซลล์) |
| weather | missing | 110,328 | 21,603 | 19120.0501 | -0.0225 | 0.2725 | 0.4852 | 0.6214 | พอใช้ |
| traffic | available | 110,328 | 21,603 | 19120.0501 | -0.0225 | 0.2725 | 0.4852 | 0.6214 | พอใช้ |
| traffic | partial | 0 | 0.0000 | 0.0000 | null | null | null | null | ว่าง (ไม่มีเซลล์) |
| traffic | missing | 0 | 0.0000 | 0.0000 | null | null | null | null | ว่าง (ไม่มีเซลล์) |
| outcome_bin | 0 | 93,362 | 0.0000 | 13705.0491 | 0.1468 | 0.1468 | 0.1988 | 0.2936 | **ข้อมูลน้อย ห้ามตีความเป็นผล** |
| outcome_bin | 1 | 13,772 | 13,772 | 3635.9729 | -0.7360 | 0.7477 | 0.7763 | 1.8639 | พอใช้ |
| outcome_bin | 2-3 | 2,887 | 6,352 | 1468.5243 | -1.6915 | 1.6936 | 1.7637 | 4.4040 | พอใช้ |
| outcome_bin | 4-6 | 281 | 1,264 | 278.7894 | -3.5061 | 3.5061 | 3.5833 | 7.8947 | พอใช้ |
| outcome_bin | 7-9 | 20 | 150 | 26.5960 | -6.1702 | 6.1702 | 6.2123 | 15.2035 | **ข้อมูลน้อย ห้ามตีความเป็นผล** |
| outcome_bin | 10+ | 6 | 65 | 5.1185 | -9.9803 | 9.9803 | 10.2083 | 40.3153 | **ข้อมูลน้อย ห้ามตีความเป็นผล** |
| high_count | high_ge_2 | 3,194 | 7,831 | 1779.0281 | -1.8948 | 1.8966 | 2.0925 | 4.8462 | พอใช้ |
| high_count | below_2 | 107,134 | 13,772 | 17341.0220 | 0.0333 | 0.2240 | 0.3345 | 0.4954 | พอใช้ |
| time_block | 00-06 | 27,582 | 4,128 | 3678.5716 | -0.0163 | 0.2257 | 0.4044 | 0.5444 | พอใช้ |
| time_block | 06-12 | 27,582 | 5,918 | 5064.1910 | -0.0310 | 0.2912 | 0.5197 | 0.6594 | พอใช้ |
| time_block | 12-18 | 27,582 | 6,721 | 5779.6044 | -0.0341 | 0.3172 | 0.5562 | 0.6963 | พอใช้ |
| time_block | 18-24 | 27,582 | 4,836 | 4597.6831 | -0.0086 | 0.2558 | 0.4458 | 0.5855 | พอใช้ |

### Calibration และ residual (6h)

- `calibration_bins_6h.csv`: ขอบ bin จาก quantile ของ prediction OOF เท่านั้น (ค่าซ้ำรวม bin, bin ว่างคงไว้) แล้วใช้ขอบเดิมกับ 2024/2025
- `largest_residuals_6h.csv`: residual รวมสูงสุด (ทำนาย − จริง) ตาม จังหวัด×เดือน, วันที่ และจังหวัด ของแต่ละช่วงแยกกัน

| ช่วง | bin | ขอบล่าง | ขอบบน | n | ทำนายเฉลี่ย | จริงเฉลี่ย | จริง/ทำนาย | support |
|---|---|---|---|---|---|---|---|---|
| oof | 0 | 0.0134 | 0.0437 | 21,444 | 0.0315 | 0.0303 | 0.9595 | พอใช้ |
| oof | 1 | 0.0437 | 0.0650 | 21,444 | 0.0550 | 0.0608 | 1.1064 | พอใช้ |
| oof | 2 | 0.0650 | 0.0813 | 21,444 | 0.0729 | 0.0771 | 1.0569 | พอใช้ |
| oof | 3 | 0.0813 | 0.0996 | 21,444 | 0.0908 | 0.0991 | 1.0915 | พอใช้ |
| oof | 4 | 0.0996 | 0.1177 | 21,444 | 0.1083 | 0.1160 | 1.0709 | พอใช้ |
| oof | 5 | 0.1177 | 0.1389 | 21,444 | 0.1282 | 0.1283 | 1.0006 | พอใช้ |
| oof | 6 | 0.1389 | 0.1648 | 21,444 | 0.1505 | 0.1461 | 0.9711 | พอใช้ |
| oof | 7 | 0.1648 | 0.2148 | 21,444 | 0.1860 | 0.1870 | 1.0056 | พอใช้ |
| oof | 8 | 0.2148 | 0.3522 | 21,444 | 0.2711 | 0.2793 | 1.0302 | พอใช้ |
| oof | 9 | 0.3522 | 3.3527 | 21,444 | 0.6204 | 0.6152 | 0.9916 | พอใช้ |
| development_2024 | 0 | 0.0134 | 0.0437 | 3,230 | 0.0312 | 0.0384 | 1.2311 | พอใช้ |
| development_2024 | 1 | 0.0437 | 0.0650 | 2,428 | 0.0560 | 0.0482 | 0.8607 | พอใช้ |
| development_2024 | 2 | 0.0650 | 0.0813 | 3,290 | 0.0730 | 0.0921 | 1.2610 | พอใช้ |
| development_2024 | 3 | 0.0813 | 0.0996 | 3,247 | 0.0904 | 0.0949 | 1.0489 | พอใช้ |
| development_2024 | 4 | 0.0996 | 0.1177 | 2,833 | 0.1084 | 0.1232 | 1.1362 | พอใช้ |
| development_2024 | 5 | 0.1177 | 0.1389 | 3,070 | 0.1287 | 0.1502 | 1.1665 | พอใช้ |
| development_2024 | 6 | 0.1389 | 0.1648 | 3,333 | 0.1512 | 0.1548 | 1.0236 | พอใช้ |
| development_2024 | 7 | 0.1648 | 0.2148 | 3,339 | 0.1859 | 0.2078 | 1.1179 | พอใช้ |
| development_2024 | 8 | 0.2148 | 0.3522 | 3,987 | 0.2696 | 0.3165 | 1.1743 | พอใช้ |
| development_2024 | 9 | 0.3522 | 3.3527 | 2,783 | 0.5897 | 0.7309 | 1.2393 | พอใช้ |
| reused_seen_2025 | 0 | 0.0134 | 0.0437 | 11,337 | 0.0310 | 0.0530 | 1.7074 | พอใช้ |
| reused_seen_2025 | 1 | 0.0437 | 0.0650 | 9,157 | 0.0561 | 0.0588 | 1.0473 | พอใช้ |
| reused_seen_2025 | 2 | 0.0650 | 0.0813 | 11,029 | 0.0728 | 0.0794 | 1.0907 | พอใช้ |
| reused_seen_2025 | 3 | 0.0813 | 0.0996 | 11,653 | 0.0905 | 0.0915 | 1.0105 | พอใช้ |
| reused_seen_2025 | 4 | 0.0996 | 0.1177 | 10,136 | 0.1083 | 0.1115 | 1.0290 | พอใช้ |
| reused_seen_2025 | 5 | 0.1177 | 0.1389 | 11,170 | 0.1286 | 0.1509 | 1.1735 | พอใช้ |
| reused_seen_2025 | 6 | 0.1389 | 0.1648 | 11,773 | 0.1510 | 0.1660 | 1.0992 | พอใช้ |
| reused_seen_2025 | 7 | 0.1648 | 0.2148 | 10,618 | 0.1867 | 0.2050 | 1.0984 | พอใช้ |
| reused_seen_2025 | 8 | 0.2148 | 0.3522 | 12,525 | 0.2714 | 0.2881 | 1.0618 | พอใช้ |
| reused_seen_2025 | 9 | 0.3522 | 3.3527 | 10,930 | 0.6133 | 0.7289 | 1.1885 | พอใช้ |

residual รวมสูงสุด 5 อันดับ (จังหวัด×เดือน) ของ `hgb_poisson__calendar_traffic`:

| ช่วง | จังหวัด | เดือน | n | จริง | ทำนาย | residual | support |
|---|---|---|---|---|---|---|---|
| oof | กรุงเทพมหานคร | 2022-08 | 112 | 158 | 87.7563 | -70.2437 | **ข้อมูลน้อย ห้ามตีความเป็นผล** |
| oof | กรุงเทพมหานคร | 2022-11 | 92 | 143 | 76.7060 | -66.2940 | **ข้อมูลน้อย ห้ามตีความเป็นผล** |
| oof | นครราชสีมา | 2022-01 | 120 | 126 | 72.9084 | -53.0916 | **ข้อมูลน้อย ห้ามตีความเป็นผล** |
| oof | ชลบุรี | 2023-03 | 120 | 141 | 90.4464 | -50.5536 | **ข้อมูลน้อย ห้ามตีความเป็นผล** |
| oof | กรุงเทพมหานคร | 2022-07 | 116 | 137 | 87.7751 | -49.2249 | **ข้อมูลน้อย ห้ามตีความเป็นผล** |
| development_2024 | กรุงเทพมหานคร | 2024-02 | 48 | 104 | 62.8583 | -41.1417 | **ข้อมูลน้อย ห้ามตีความเป็นผล** |
| development_2024 | นครราชสีมา | 2024-03 | 80 | 89 | 52.8128 | -36.1872 | **ข้อมูลน้อย ห้ามตีความเป็นผล** |
| development_2024 | กรุงเทพมหานคร | 2024-03 | 36 | 79 | 47.2226 | -31.7774 | **ข้อมูลน้อย ห้ามตีความเป็นผล** |
| development_2024 | ชลบุรี | 2024-03 | 80 | 98 | 71.4090 | -26.5910 | **ข้อมูลน้อย ห้ามตีความเป็นผล** |
| development_2024 | กรุงเทพมหานคร | 2024-04 | 24 | 57 | 31.3808 | -25.6192 | **ข้อมูลน้อย ห้ามตีความเป็นผล** |
| reused_seen_2025 | กรุงเทพมหานคร | 2025-09 | 96 | 190 | 106.2507 | -83.7493 | **ข้อมูลน้อย ห้ามตีความเป็นผล** |
| reused_seen_2025 | กรุงเทพมหานคร | 2025-08 | 92 | 167 | 89.0814 | -77.9186 | **ข้อมูลน้อย ห้ามตีความเป็นผล** |
| reused_seen_2025 | กรุงเทพมหานคร | 2025-12 | 96 | 189 | 119.6357 | -69.3643 | **ข้อมูลน้อย ห้ามตีความเป็นผล** |
| reused_seen_2025 | กรุงเทพมหานคร | 2025-04 | 68 | 141 | 81.1150 | -59.8850 | **ข้อมูลน้อย ห้ามตีความเป็นผล** |
| reused_seen_2025 | ชลบุรี | 2025-11 | 120 | 149 | 92.1926 | -56.8074 | **ข้อมูลน้อย ห้ามตีความเป็นผล** |

## 3. Drift ปีหลังและการเปลี่ยนแปลงความครอบคลุมของแหล่งข้อมูล

| หน่วย | ช่วง | เซลล์ eligible | วัน | เริ่ม | สิ้นสุด | y เฉลี่ย | สัดส่วน 0 | weather มี | traffic มี | bank รู้ | bias ที่แนะนำ | ทำนาย/จริง |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| daily | oof | 53,610 | 713 | 2022-01-01 | 2023-12-29 | 0.6957 | 0.5954 | 0.8280 | 0.8824 | 1 | -0.0182 | 0.9739 |
| daily | development_2024 | 7,885 | 103 | 2024-01-07 | 2024-09-30 | 0.7822 | 0.5653 | 0.0000 | 1 | 1 | -0.0639 | 0.9183 |
| daily | reused_seen_2025 | 27,582 | 360 | 2025-01-04 | 2025-12-31 | 0.7832 | 0.5704 | 0.0000 | 1 | 1 | -0.0528 | 0.9326 |
| 6h | oof | 214,440 | 713 | 2022-01-01 | 2023-12-29 | 0.1739 | 0.8589 | 0.8280 | 0.8824 | 1 | -0.0024 | 0.9859 |
| 6h | development_2024 | 31,540 | 103 | 2024-01-07 | 2024-09-30 | 0.1956 | 0.8441 | 0.0000 | 1 | 1 | -0.0271 | 0.8615 |
| 6h | reused_seen_2025 | 110,328 | 360 | 2025-01-04 | 2025-12-31 | 0.1958 | 0.8462 | 0.0000 | 1 | 1 | -0.0225 | 0.8851 |

- daily: เซลล์ panel/eligible ต่อ split = {'development_2024': {'cells': 28182, 'eligible': 7885}, 'reused_seen_2025': {'cells': 28105, 'eligible': 27582}, 'train': {'cells': 84315, 'eligible': 81506}}; province-year ที่มี weather อย่างน้อยบางส่วน 204/385 (รายปี {'2021': 77, '2022': 77, '2023': 50, '2024': 0, '2025': 0})
- 6h: เซลล์ panel/eligible ต่อ split = {'development_2024': {'cells': 112728, 'eligible': 31540}, 'reused_seen_2025': {'cells': 112420, 'eligible': 110328}, 'train': {'cells': 337260, 'eligible': 326024}}; province-year ที่มี weather อย่างน้อยบางส่วน 204/385 (รายปี {'2021': 77, '2022': 77, '2023': 50, '2024': 0, '2025': 0})
- ป้ายปี 2024 ถูกตัดเป็น eligible เพียงส่วนน้อยของเซลล์ (ตัวกรองนี้ได้จากผลลัพธ์ย้อนหลัง ใช้ล่วงหน้าไม่ได้) ผลปี 2024 จึงแทนเฉพาะวันที่ป้ายทราบ ไม่ใช่ทั้งปี
- 2024/2025 ไม่มีข้อมูลอากาศ: ทุกแถวปีหลังเป็น weather missing ดังนั้นความต่างระหว่าง variant ที่มี/ไม่มี weather ในปีหลังสะท้อนการเติมค่าที่หายไป ไม่ใช่ผลของอากาศ
- ความครอบคลุมรายเดือน: `coverage_by_month_<unit>.csv`, กราฟ `fig_coverage_<unit>.png`

## 4. ข้อจำกัด

- 2024 = development ที่เคยเห็นแล้ว, 2025 = reused/previously-seen: ไม่มีชุดใดเป็น untouched test; ห้ามเลือกใหม่จากผลปีหลัง
- bootstrap เป็นการสำรวจหลังการเลือก ไม่ปรับ multiple comparison; slice/กลุ่มย่อยเป็นการบรรยาย ไม่ใช่การประมาณผลเชิงสาเหตุ
- เวลาเผยแพร่จริงของรายงานอุบัติเหตุและ weather ย้อนหลังยังไม่ยืนยัน; traffic เป็นค่าเฉลี่ยจุดสำรวจ ไม่ใช่ exposure
- ผลทั้งหมดไม่อนุญาตการพยากรณ์เชิงปฏิบัติการ, เว็บที่ deploy, หรือการประเมินความเสี่ยงรายบุคคล/เส้นทาง

## 5. ไฟล์

- ตาราง: `decision_summary.csv`, `gate_checks.csv`, `fold_comparison.csv`, `ablation_all_pairs.csv`, `ablation_coverage_sensitivity.csv`, `slices_<unit>.csv`, `calibration_bins_<unit>.csv`, `largest_residuals_<unit>.csv`, `weekly_actual_vs_predicted_<unit>.csv`, `coverage_by_month_<unit>.csv`, `drift_summary.csv`, `metric_reconciliation.csv`, `ablation_reconciliation.csv`
- ผล notebook 11 (อ่านอย่างเดียว): `../models/oof_metrics_pooled.csv`, `../models/oof_metrics_by_fold.csv`, `../models/fold_boundaries.csv`, `../models/diagnostic_metrics.csv`, `../models/selection_lock.json`
- กราฟ: `fig_oof_methods_daily.png`, `fig_fold_deviance_daily.png`, `fig_ablation_daily.png`, `fig_calibration_daily.png`, `fig_weekly_daily.png`, `fig_bias_by_month_daily.png`, `fig_coverage_daily.png`, `fig_oof_methods_6h.png`, `fig_fold_deviance_6h.png`, `fig_ablation_6h.png`, `fig_calibration_6h.png`, `fig_weekly_6h.png`, `fig_bias_by_month_6h.png`, `fig_coverage_6h.png`
- แถวรายเซลล์ (ไม่อยู่ใน git): `data/v2/analysis/analysis_rows_<unit>.csv.gz`
