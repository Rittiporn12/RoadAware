# ผลประเมิน notebook 21: ความคลาดเคลื่อนและเกณฑ์สีความหนาแน่นสัมพัทธ์ (V3)

ข้อมูลทั้งหมดคำนวณใหม่จาก array OOF 2022-23 ของ notebook 20 ที่ผ่านการยอมรับแล้ว (ไม่ฝึกใหม่ ไม่เลือกโมเดลใหม่ ไม่ใช้ข้อมูล 2026)
label = จำนวนบันทึก MOT ที่ถูกเลือกและเชื่อมกับช่วงถนน DOH ได้ ไม่ใช่จำนวนอุบัติเหตุจริงทั้งหมด และไม่ใช่ความน่าจะเป็นต่อคันรถ

## 1. เหตุผลการเลือก (gate ที่ล็อกไว้)

- daily: เลือก `hgb_poisson_fixed::routed_context` เทียบ baseline `segment_mean_k365`; deviance ลดลง 2.5832%, MAE ratio 1.007095, ชนะ 4/4 fold, ทุก gate ผ่าน = True, คง baseline = False
- 6h: เลือก `hgb_poisson_fixed::routed_context` เทียบ baseline `segment_mean_k365`; deviance ลดลง 8.1523%, MAE ratio 1.004063, ชนะ 4/4 fold, ทุก gate ผ่าน = True, คง baseline = False

## 2. ข้อจำกัด: กลุ่มที่ baseline ทำนายต่ำกว่า floor ของ metric

- daily (oof): ส่วนแบ่งของ gain จากเซลล์ที่ baseline < floor = 74.9983%; gain ในเซลล์ที่เหลือ = 0.6641% -- ไม่ใช่หลักฐานว่าโมเดลดีกว่าในทุกกรณี
- daily (diag): ส่วนแบ่งของ gain จากเซลล์ที่ baseline < floor = 25.6706%; gain ในเซลล์ที่เหลือ = 1.9468% -- ไม่ใช่หลักฐานว่าโมเดลดีกว่าในทุกกรณี
- 6h (oof): ส่วนแบ่งของ gain จากเซลล์ที่ baseline < floor = 73.4598%; gain ในเซลล์ที่เหลือ = 2.3754% -- ไม่ใช่หลักฐานว่าโมเดลดีกว่าในทุกกรณี
- 6h (diag): ส่วนแบ่งของ gain จากเซลล์ที่ baseline < floor = 74.1992%; gain ในเซลล์ที่เหลือ = 2.5488% -- ไม่ใช่หลักฐานว่าโมเดลดีกว่าในทุกกรณี

audit นี้ลงทะเบียนหลังเห็นผล daily เบื้องต้น จึงเป็น sensitivity เท่านั้น ไม่เปลี่ยน baseline/metric/การเลือก

## 3. เกณฑ์สี (คงที่ทุกเส้นทาง/ทุกมุมมอง, แยก daily กับ 6h)

- daily: cutoffs P50/P80/P95 = 0.0006725354451004399, 0.0024847083769593244, 0.008116725169221255 (records per km per local day); สีที่ใช้จริง: base, yellow, orange, red
- 6h: cutoffs P50/P80/P95 = 0.00016821819247103556, 0.0006134508738015898, 0.002003535309983658 (records per km per 6 h block); สีที่ใช้จริง: base, yellow, orange, red

สี base = ความหนาแน่นที่คาดการณ์ "ต่ำกว่าเชิงสัมพัทธ์" เท่านั้น ไม่ได้แปลว่าปลอดภัย; สีเทา = ไม่มีข้อมูล/ไม่รองรับ

## 4. Capture ที่งบ road-km เท่ากัน (OOF 2022-23, รวมทุกช่วงเวลา)

| unit | role | road_km_fraction | capture_share | lift_vs_uniform |
|---|---|---|---|---|
| daily | selected | 0.01 | 0.1918 | 19.18 |
| daily | selected | 0.02 | 0.3012 | 15.06 |
| daily | selected | 0.05 | 0.5016 | 10.03 |
| daily | selected | 0.1 | 0.6181 | 6.181 |
| daily | selected | 0.2 | 0.7508 | 3.754 |
| daily | baseline | 0.01 | 0.2007 | 20.07 |
| daily | baseline | 0.02 | 0.3074 | 15.37 |
| daily | baseline | 0.05 | 0.4979 | 9.958 |
| daily | baseline | 0.1 | 0.6253 | 6.253 |
| daily | baseline | 0.2 | 0.7594 | 3.797 |
| 6h | selected | 0.01 | 0.1912 | 19.12 |
| 6h | selected | 0.02 | 0.2963 | 14.82 |
| 6h | selected | 0.05 | 0.5043 | 10.09 |
| 6h | selected | 0.1 | 0.622 | 6.22 |
| 6h | selected | 0.2 | 0.7522 | 3.761 |
| 6h | baseline | 0.01 | 0.193 | 19.3 |
| 6h | baseline | 0.02 | 0.3003 | 15.01 |
| 6h | baseline | 0.05 | 0.4831 | 9.662 |
| 6h | baseline | 0.1 | 0.606 | 6.06 |
| 6h | baseline | 0.2 | 0.7306 | 3.653 |

## 5. ความเสถียร 2024/25 (เคยเห็นแล้ว, ไม่ใช่ holdout) และ spatial transfer

| unit | group | role | mean_poisson_deviance | mae | pred_over_actual |
|---|---|---|---|---|---|
| daily | seen_2024 | selected | 0.04346 | 0.009537 | 0.8748 |
| daily | seen_2025 | selected | 0.04626 | 0.009693 | 0.8326 |
| daily | seen_2024 | baseline | 0.04423 | 0.009383 | 0.8408 |
| daily | seen_2025 | baseline | 0.04789 | 0.009592 | 0.8095 |
| 6h | seen_2024 | selected | 0.01437 | 0.002428 | 0.8548 |
| 6h | seen_2025 | selected | 0.01522 | 0.002468 | 0.815 |
| 6h | seen_2024 | baseline | 0.01549 | 0.002409 | 0.8409 |
| 6h | seen_2025 | baseline | 0.01698 | 0.00246 | 0.8095 |

| unit | method | mean_poisson_deviance | relative_to_best_baseline |
|---|---|---|---|
| daily | poisson_a1e-05::core | 0.03627 | -0.02664 |
| daily | rf_poisson_fixed::core | 0.03691 | -0.04461 |
| daily | hgb_poisson_fixed::core | 0.03456 | 0.02188 |
| daily | global_mean | 0.03872 | -0.09587 |
| daily | global_length_rate | 0.03849 | -0.08942 |
| daily | route_length_rate | 0.03533 | 0 |
| daily | segment_mean_k30 | 0.03533 | 0 |
| daily | segment_mean_k180 | 0.03533 | 0 |
| daily | segment_mean_k365 | 0.03533 | 0 |
| daily | segment_weekday_k10 | 0.03533 | 0 |
| daily | segment_month_k30 | 0.03533 | 0 |
| daily | recent90_segment | 0.03533 | 0 |
| 6h | poisson_a1e-05::core | 0.01176 | -0.04615 |
| 6h | rf_poisson_fixed::core | 0.0114 | -0.01379 |
| 6h | hgb_poisson_fixed::core | 0.01064 | 0.05309 |
| 6h | global_mean | 0.0118 | -0.05003 |
| 6h | global_length_rate | 0.01175 | -0.04497 |
| 6h | route_length_rate | 0.01124 | 0 |
| 6h | segment_mean_k30 | 0.01124 | 0 |
| 6h | segment_mean_k180 | 0.01124 | 0 |
| 6h | segment_mean_k365 | 0.01124 | 0 |
| 6h | segment_weekday_k10 | 0.01124 | 0 |
| 6h | segment_month_k30 | 0.01124 | 0 |
| 6h | recent90_segment | 0.01124 | 0 |

Transfer ประเมินเฉพาะ core config บนช่วงถนนที่ไม่ได้ใช้ฝึก (2023) แยกจากการเลือกเชิงเวลา; ถ้าผลแย่ต้องรายงานตามจริง

## ความไม่แน่นอน (exploratory, หลังการเลือก)

- daily: paired day-block bootstrap ของ notebook 20: 1.4767% ถึง 3.7116% (ok (exploratory, post-selection, not confirmatory))
- 6h: paired day-block bootstrap ของ notebook 20: 6.7547% ถึง 9.5516% (ok (exploratory, post-selection, not confirmatory))

2026: รอการตรวจข้อมูลและการประเมินแยกต่างหาก (ยังไม่มีผล ไม่มีการเติมตัวเลขสมมติ)
