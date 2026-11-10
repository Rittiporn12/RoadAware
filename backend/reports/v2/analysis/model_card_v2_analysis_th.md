# Model card V2 — มุมมองหลังวิเคราะห์ (Notebook 12, ร่างงานวิจัย)

- ใช้งาน: วิจัยเท่านั้น; production_ready = false; operational BLOCKED; ไม่ใช่ความเสี่ยงรายบุคคล/เส้นทาง, ไม่ใช่อุบัติเหตุทุกถนน, ไม่ใช่เว็บที่ deploy
- ข้อมูล: panel V2 ที่ตรวจรับแล้ว (notebook 10); ตัวเลือกล็อกใน `../models/selection_lock.json` ก่อนดูปีหลัง; 12 ไม่ได้เปลี่ยนตัวเลือก

## daily
- วิธีที่แนะนำ: `hgb_poisson__full` (candidate_passed_gate); gate ผ่าน = True
- best candidate: `hgb_poisson__full`; strongest baseline: `baseline_province_month_k30`
- เหตุผล: hgb_poisson__full passed all four gate checks against baseline_province_month_k30; recommended per protocol (research reference only)

| วิธี | ช่วง | n | deviance | MAE | bias |
|---|---|---|---|---|---|
| hgb_poisson__full | pooled OOF (เลือก) | 53,610 | 1.0643 | 0.6601 | -0.0182 |
| hgb_poisson__full | development_2024 (เคยเห็นแล้ว) | 7,885 | 1.0944 | 0.6938 | -0.0639 |
| hgb_poisson__full | reused_seen_2025 (เคยเห็นแล้ว) | 27,582 | 1.1319 | 0.7056 | -0.0528 |
| baseline_province_month_k30 | pooled OOF (เลือก) | 53,610 | 1.1464 | 0.6894 | -0.0052 |
| baseline_province_month_k30 | development_2024 (เคยเห็นแล้ว) | 7,885 | 1.1288 | 0.7067 | -0.0695 |
| baseline_province_month_k30 | reused_seen_2025 (เคยเห็นแล้ว) | 27,582 | 1.2117 | 0.7248 | -0.0894 |

## 6h
- วิธีที่แนะนำ: `hgb_poisson__calendar_traffic` (candidate_passed_gate); gate ผ่าน = True
- best candidate: `hgb_poisson__calendar_traffic`; strongest baseline: `baseline_province_block_mean`
- เหตุผล: hgb_poisson__calendar_traffic passed all four gate checks against baseline_province_block_mean; recommended per protocol (research reference only)

| วิธี | ช่วง | n | deviance | MAE | bias |
|---|---|---|---|---|---|
| hgb_poisson__calendar_traffic | pooled OOF (เลือก) | 214,440 | 0.5835 | 0.2578 | -0.0024 |
| hgb_poisson__calendar_traffic | development_2024 (เคยเห็นแล้ว) | 31,540 | 0.6159 | 0.2719 | -0.0271 |
| hgb_poisson__calendar_traffic | reused_seen_2025 (เคยเห็นแล้ว) | 110,328 | 0.6214 | 0.2725 | -0.0225 |
| baseline_province_block_mean | pooled OOF (เลือก) | 214,440 | 0.6078 | 0.2676 | -0.0000 |
| baseline_province_block_mean | development_2024 (เคยเห็นแล้ว) | 31,540 | 0.6223 | 0.2771 | -0.0227 |
| baseline_province_block_mean | reused_seen_2025 (เคยเห็นแล้ว) | 110,328 | 0.6461 | 0.2804 | -0.0222 |

## ข้อควรระวัง
- ไม่มี untouched test; 2024/2025 เป็น diagnostic ที่เคยเห็นแล้ว
- ตัวกรอง eligible ได้จากผลลัพธ์; ป้ายปี 2024 ทราบเพียงบางส่วน
- feature ที่ไม่ช่วย/ทำให้แย่ลงแสดงไว้ใน `analysis_report_th.md` และ `ablation_all_pairs.csv`
- รายละเอียด: `analysis_report_th.md`
