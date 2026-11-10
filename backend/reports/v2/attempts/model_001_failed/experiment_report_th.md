# รายงานการทดลองโมเดล V2 (Notebook 11)

สถานะ: งานวิจัยเท่านั้น | production_ready = false | operational = BLOCKED | ไม่ใช่การพยากรณ์ความเสี่ยงรายบุคคล/เส้นทาง

ป้ายกำกับ = จำนวนบันทึก MOT ที่ถูกเลือก (เฉพาะเครือข่าย MOT ไม่ใช่อุบัติเหตุทั้งหมด). เซลล์ training_eligible = false เป็นป้ายที่ไม่ทราบ และถูกตัดออกจากทุกวิธีเหมือนกัน (ตัวกรองนี้ได้จากผลลัพธ์ ใช้แบบ offline เท่านั้น).

## 1. วิธีทดลอง

- หน่วย daily (จังหวัด-วัน, หลัก) และ 6h (จังหวัด x บล็อก 6 ชม.) ทดลองแยกกัน เลือกผู้ชนะแยกกัน ไม่เทียบ error ข้ามหน่วย
- 4 fold ขยายตามเวลา 2022H1, 2022H2, 2023H1, 2023H2; fit ได้เฉพาะเซลล์ Train ที่ target_end_local <= เวลา issue ของวันแรกที่ประเมิน (วันก่อนหน้า 18:00 +07)
- 3 ตระกูล: Poisson (alpha 0.001/0.01), Random Forest (poisson), HGB (poisson) x 5 ชุด feature (core, calendar, calendar_weather, calendar_traffic, full); ค่า config คงที่ตาม protocol ไม่มีการ tune
- preprocessing (one-hot/ordinal, imputer, scaler) fit จาก Train ของแต่ละ fold เท่านั้น; คอลัมน์ที่หายทั้งหมดใน Train ถูกเก็บไว้; ค่า feature ที่หายไม่ทำให้แถวหาย
- baseline fit จาก Train เท่านั้น; recent90 ถูกตรึง ณ เวลาเริ่ม fold (ไม่อัปเดตด้วยป้ายของช่วงประเมิน)
- metric หลัก: mean Poisson deviance แบบ pooled OOF (floor 1e-09 ใช้เฉพาะใน deviance และนับจำนวนครั้ง); baseline ศูนย์ไม่มี deviance จำกัด (null)

## 2.1 หน่วย daily

| วิธี | ตระกูล | deviance (OOF) | MAE | RMSE | bias | floored |
|---|---|---|---|---|---|---|
| poisson_a0.001__full | poisson | 1.0896 | 0.6792 | 0.9908 | -0.0167 | 0.0000 |
| rf_poisson__full | rf | 1.1278 | 0.7010 | 0.9854 | -0.0072 | 0.0000 |
| hgb_poisson__full **(best candidate)** | hgb | 1.0643 | 0.6601 | 0.9535 | -0.0182 | 0.0000 |
| baseline_zero | baseline | null | 0.6957 | 1.3796 | -0.6957 | null |
| baseline_global_mean | baseline | 1.5476 | 0.8303 | 1.1917 | 0.0090 | 0.0000 |
| baseline_province_mean | baseline | 1.1571 | 0.6927 | 1.0142 | -0.0023 | 0.0000 |
| baseline_province_weekday_k10 | baseline | 1.1636 | 0.6928 | 1.0154 | -0.0026 | 0.0000 |
| baseline_province_month_k30 **(strongest baseline)** | baseline | 1.1464 | 0.6894 | 1.0099 | -0.0052 | 0.0000 |
| baseline_recent90_province_mean | baseline | 1.1718 | 0.6966 | 1.0127 | 0.0174 | 0.0000 |

- ตัวแทนดีที่สุดของแต่ละตระกูล: {'poisson': 'poisson_a0.001__full', 'rf': 'rf_poisson__full', 'hgb': 'hgb_poisson__full'}
- วิธีที่ล้มเหลว/ไม่ครบทุก fold: ไม่มี
- stability gate (เทียบ strongest baseline): ผ่าน
  - relative_deviance_reduction: value=0.0716 threshold=0.01 -> pass
  - mae_ratio: value=0.9575 threshold=1.02 -> pass
  - fold_wins: value=4 threshold=3 -> pass
  - bootstrap_upper_ci_lt_0: value=-0.0423 threshold=0.0 -> pass
- bootstrap (สำรวจ, ไม่ปรับ multiple comparison): ผลต่าง deviance -0.08212 CI95 [-0.13628, -0.04229] จาก 104 บล็อก 7 วัน
- **ข้อเสนอ: hgb_poisson__full** (candidate_passed_gate)


### ผลของการเพิ่ม feature (identical keys; ลบ = ดีขึ้น, บวก = แย่ลง)

| config | เพิ่ม | เทียบกับ | Δ deviance | relative | fold ที่ดีขึ้น | ผล |
|---|---|---|---|---|---|---|
| poisson_a0.001 | calendar | core | -0.06875 | -5.912% | 4/4 | benefit |
| poisson_a0.001 | calendar_weather | calendar | -0.00085 | -0.078% | 3/4 | benefit |
| poisson_a0.001 | calendar_traffic | calendar | -0.00363 | -0.331% | 3/4 | benefit |
| poisson_a0.001 | full | calendar | -0.00466 | -0.426% | 4/4 | benefit |
| poisson_a0.001 | full | calendar_weather | -0.00381 | -0.349% | 3/4 | benefit |
| poisson_a0.001 | full | calendar_traffic | -0.00104 | -0.095% | 3/4 | benefit |
| poisson_a0.001 | full | core | -0.07342 | -6.313% | 4/4 | benefit |
| poisson_a0.01 | calendar | core | -0.06962 | -5.613% | 4/4 | benefit |
| poisson_a0.01 | calendar_weather | calendar | -0.00147 | -0.125% | 3/4 | benefit |
| poisson_a0.01 | calendar_traffic | calendar | -0.03273 | -2.796% | 3/4 | benefit |
| poisson_a0.01 | full | calendar | -0.03478 | -2.971% | 4/4 | benefit |
| poisson_a0.01 | full | calendar_weather | -0.03331 | -2.849% | 3/4 | benefit |
| poisson_a0.01 | full | calendar_traffic | -0.00205 | -0.180% | 4/4 | benefit |
| poisson_a0.01 | full | core | -0.10440 | -8.418% | 4/4 | benefit |
| rf_poisson | calendar | core | +0.00259 | +0.224% | 2/4 | harm |
| rf_poisson | calendar_weather | calendar | -0.00107 | -0.093% | 4/4 | benefit |
| rf_poisson | calendar_traffic | calendar | -0.02553 | -2.208% | 3/4 | benefit |
| rf_poisson | full | calendar | -0.02842 | -2.458% | 4/4 | benefit |
| rf_poisson | full | calendar_weather | -0.02734 | -2.367% | 4/4 | benefit |
| rf_poisson | full | calendar_traffic | -0.00289 | -0.256% | 4/4 | benefit |
| rf_poisson | full | core | -0.02583 | -2.239% | 3/4 | benefit |
| hgb_poisson | calendar | core | -0.00247 | -0.229% | 4/4 | benefit |
| hgb_poisson | calendar_weather | calendar | -0.00363 | -0.336% | 3/4 | benefit |
| hgb_poisson | calendar_traffic | calendar | -0.01141 | -1.057% | 3/4 | benefit |
| hgb_poisson | full | calendar | -0.01472 | -1.365% | 4/4 | benefit |
| hgb_poisson | full | calendar_weather | -0.01109 | -1.032% | 3/4 | benefit |
| hgb_poisson | full | calendar_traffic | -0.00331 | -0.311% | 3/4 | benefit |
| hgb_poisson | full | core | -0.01720 | -1.590% | 4/4 | benefit |

- harm (deviance เพิ่ม): 1 คู่; benefit: 27 คู่

## 2.2 หน่วย 6h

| วิธี | ตระกูล | deviance (OOF) | MAE | RMSE | bias | floored |
|---|---|---|---|---|---|---|
| poisson_a0.001__full | poisson | 0.5963 | 0.2677 | 0.4539 | 0.0019 | 0.0000 |
| rf_poisson__full | rf | 0.6018 | 0.2637 | 0.4523 | -0.0010 | 0.0000 |
| hgb_poisson__calendar_traffic **(best candidate)** | hgb | 0.5835 | 0.2578 | 0.4478 | -0.0024 | 0.0000 |
| baseline_zero | baseline | null | 0.1739 | 0.5152 | -0.1739 | null |
| baseline_global_mean | baseline | 0.7112 | 0.3008 | 0.4850 | 0.0028 | 0.0000 |
| baseline_province_block_mean **(strongest baseline)** | baseline | 0.6078 | 0.2676 | 0.4569 | -0.0000 | 0.0000 |
| baseline_province_block_weekday_k10 | baseline | 0.6163 | 0.2674 | 0.4580 | -0.0001 | 0.0000 |
| baseline_province_block_month_k30 | baseline | 0.6108 | 0.2658 | 0.4572 | -0.0011 | 0.0000 |
| baseline_recent90_province_block_mean | baseline | 0.6260 | 0.2709 | 0.4580 | 0.0074 | 1901.0000 |

- ตัวแทนดีที่สุดของแต่ละตระกูล: {'poisson': 'poisson_a0.001__full', 'rf': 'rf_poisson__full', 'hgb': 'hgb_poisson__calendar_traffic'}
- วิธีที่ล้มเหลว/ไม่ครบทุก fold: ไม่มี
- stability gate (เทียบ strongest baseline): ผ่าน
  - relative_deviance_reduction: value=0.0399 threshold=0.01 -> pass
  - mae_ratio: value=0.9633 threshold=1.02 -> pass
  - fold_wins: value=4 threshold=3 -> pass
  - bootstrap_upper_ci_lt_0: value=-0.0108 threshold=0.0 -> pass
- bootstrap (สำรวจ, ไม่ปรับ multiple comparison): ผลต่าง deviance -0.02423 CI95 [-0.04122, -0.01081] จาก 104 บล็อก 7 วัน
- **ข้อเสนอ: hgb_poisson__calendar_traffic** (candidate_passed_gate)


### ผลของการเพิ่ม feature (identical keys; ลบ = ดีขึ้น, บวก = แย่ลง)

| config | เพิ่ม | เทียบกับ | Δ deviance | relative | fold ที่ดีขึ้น | ผล |
|---|---|---|---|---|---|---|
| poisson_a0.001 | calendar | core | -0.01782 | -2.884% | 4/4 | benefit |
| poisson_a0.001 | calendar_weather | calendar | -0.00036 | -0.060% | 2/4 | benefit |
| poisson_a0.001 | calendar_traffic | calendar | -0.00329 | -0.548% | 3/4 | benefit |
| poisson_a0.001 | full | calendar | -0.00378 | -0.629% | 4/4 | benefit |
| poisson_a0.001 | full | calendar_weather | -0.00341 | -0.569% | 3/4 | benefit |
| poisson_a0.001 | full | calendar_traffic | -0.00049 | -0.082% | 4/4 | benefit |
| poisson_a0.001 | full | core | -0.02160 | -3.495% | 4/4 | benefit |
| poisson_a0.01 | calendar | core | -0.01832 | -2.750% | 4/4 | benefit |
| poisson_a0.01 | calendar_weather | calendar | -0.00031 | -0.047% | 4/4 | benefit |
| poisson_a0.01 | calendar_traffic | calendar | -0.02166 | -3.343% | 3/4 | benefit |
| poisson_a0.01 | full | calendar | -0.02222 | -3.428% | 4/4 | benefit |
| poisson_a0.01 | full | calendar_weather | -0.02191 | -3.383% | 3/4 | benefit |
| poisson_a0.01 | full | calendar_traffic | -0.00055 | -0.088% | 4/4 | benefit |
| poisson_a0.01 | full | core | -0.04054 | -6.084% | 4/4 | benefit |
| rf_poisson | calendar | core | +0.00179 | +0.295% | 0/4 | harm |
| rf_poisson | calendar_weather | calendar | -0.00039 | -0.064% | 4/4 | benefit |
| rf_poisson | calendar_traffic | calendar | -0.00925 | -1.514% | 3/4 | benefit |
| rf_poisson | full | calendar | -0.00931 | -1.523% | 4/4 | benefit |
| rf_poisson | full | calendar_weather | -0.00892 | -1.460% | 3/4 | benefit |
| rf_poisson | full | calendar_traffic | -0.00006 | -0.010% | 2/4 | benefit |
| rf_poisson | full | core | -0.00752 | -1.233% | 3/4 | benefit |
| hgb_poisson | calendar | core | -0.00025 | -0.042% | 3/4 | benefit |
| hgb_poisson | calendar_weather | calendar | -0.00004 | -0.007% | 2/4 | benefit |
| hgb_poisson | calendar_traffic | calendar | -0.00326 | -0.556% | 3/4 | benefit |
| hgb_poisson | full | calendar | -0.00299 | -0.510% | 3/4 | benefit |
| hgb_poisson | full | calendar_weather | -0.00295 | -0.503% | 3/4 | benefit |
| hgb_poisson | full | calendar_traffic | +0.00027 | +0.046% | 1/4 | harm |
| hgb_poisson | full | core | -0.00324 | -0.552% | 3/4 | benefit |

- harm (deviance เพิ่ม): 2 คู่; benefit: 26 คู่

## 3. Diagnostic ปีหลัง (fit เฉพาะ Train ถึง cutoff 2023-12-31 18:00 +07; ไม่ refit, ไม่เปลี่ยนตัวเลือก)

2024 = development diagnostic ที่เคยเห็นแล้ว; 2025 = reused/previously-seen diagnostic — **ไม่มีชุดใดเป็น untouched test**

| หน่วย | split | วิธี | deviance | MAE | n |
|---|---|---|---|---|---|
| daily | development_2024 | baseline_province_month_k30 | 1.1288 | 0.7067 | 7885 |
| daily | development_2024 | poisson_a0.001__full | 1.1246 | 0.7113 | 7885 |
| daily | development_2024 | rf_poisson__full | 1.1372 | 0.7044 | 7885 |
| daily | development_2024 | hgb_poisson__full | 1.0944 | 0.6938 | 7885 |
| daily | reused_seen_2025 | baseline_province_month_k30 | 1.2117 | 0.7248 | 27582 |
| daily | reused_seen_2025 | poisson_a0.001__full | 1.1349 | 0.7075 | 27582 |
| daily | reused_seen_2025 | rf_poisson__full | 1.1656 | 0.7184 | 27582 |
| daily | reused_seen_2025 | hgb_poisson__full | 1.1319 | 0.7056 | 27582 |
| 6h | development_2024 | baseline_province_block_mean | 0.6223 | 0.2771 | 31540 |
| 6h | development_2024 | poisson_a0.001__full | 0.6289 | 0.2827 | 31540 |
| 6h | development_2024 | rf_poisson__full | 0.6304 | 0.2717 | 31540 |
| 6h | development_2024 | hgb_poisson__calendar_traffic | 0.6159 | 0.2719 | 31540 |
| 6h | reused_seen_2025 | baseline_province_block_mean | 0.6461 | 0.2804 | 110328 |
| 6h | reused_seen_2025 | poisson_a0.001__full | 0.6258 | 0.2801 | 110328 |
| 6h | reused_seen_2025 | rf_poisson__full | 0.6334 | 0.2768 | 110328 |
| 6h | reused_seen_2025 | hgb_poisson__calendar_traffic | 0.6214 | 0.2725 | 110328 |

- เซลล์ Train ที่ถูกตัดเพราะสิ้นสุดหลัง cutoff: {'daily': 0, '6h': 0}
- reload ตรวจซ้ำ 18 artifact บนตัวอย่าง 2024 คงที่: ผ่านทั้งหมด = True

## 4. ข้อจำกัด

- เวลาเผยแพร่จริงของรายงานอุบัติเหตุยังไม่ได้ยืนยัน: ขอบเวลา issue ไม่ได้พิสูจน์ว่าใช้งานจริงได้
- อากาศ = พยากรณ์ JMA lead ~48 ชม. ที่จุดตัวแทนจังหวัด (ความล่าช้าการเผยแพร่ไม่ยืนยัน, ความครอบคลุมอาจไม่ครบ); จราจร = ค่าเฉลี่ย AADT จากจุดสำรวจ ไม่ใช่ exposure offset
- ไม่มี feature ประวัติอุบัติเหตุ (pending scenario แยก); cohort v2 ต่างจาก v1 จึงไม่อ้างตัวเลขเหนือกว่า v1
- bootstrap เป็นการสำรวจหลังเลือกโมเดล; การวิเคราะห์รายกลุ่ม/กราฟละเอียดอยู่ใน notebook 12

เวลารันรวม 1205.4 วินาที; timings: {'oof_daily_seconds': 139.1, 'oof_6h_seconds': 922.8, 'final_fit_and_diagnostics_seconds': 120.6, 'total_seconds': 1205.4}
