# แผนขยาย RoadAware เป็นทั้งประเทศ (V4 national) — 18 พ.ย. 2569

**เป้าหมาย:** ให้แบบจำลองรายช่วงถนนและ API ครอบคลุมทางหลวงทั้งประเทศ แทนกรอบนำร่อง `[100.2, 13.5, 102.0, 15.3]` (3,105 ช่วงถนน)

**สถานะ:** ขั้น 0 เสร็จแล้ว · ขั้น 1 เตรียมพร้อม รอรันบน Mac (ต้องใช้อินเทอร์เน็ต) · ขั้น 2–7 ยังไม่เริ่ม

## การป้องกันของเดิม
- ของเดิมทั้งหมด: git tag `pilot-v3-20261118` และ branch `checkpoint/pilot-v3-20261118` ข้อมูลที่ git ไม่เก็บอยู่ใน `backups/pilot-v3-20261118/` (มีวิธีกู้คืนในไฟล์ README ในโฟลเดอร์นั้น)
- งานใหม่ทำบน branch `national-coverage` เท่านั้น
- ใช้ config ไฟล์ใหม่เสมอ (`*_v4.json`) ไม่แก้ไฟล์ `*_v3*.json`
- ผลลัพธ์เขียนลง `reports/v4/...`, `data/v4/...` และ output root ใหม่ (`backend/rerun-*-national-*`)
- path ของพื้นที่นำร่องอยู่ใน `protected_paths` notebook จะไม่ยอมเขียนทับ
- API ที่ตรวจรับแล้ว (V3) ใช้งานได้ต่อจนกว่า V4 จะผ่านการตรวจครบทุกขั้น

## ขั้นตอน
| ขั้น | งาน | สถานะ |
|---|---|---|
| 0 | สำรองของเดิม (git tag + archive ข้อมูล) | เสร็จ |
| 1 | Notebook 17: เก็บ geometry DOH / DRR / EXAT ทั้งประเทศ (`config/spatial_road_sources_v4.json`, กรอบ = `thailand_broad_bbox`) | พร้อมรัน |
| 2 | Notebook 18: ตรวจการเชื่อมจุดอุบัติเหตุ (50 ม.) กับช่วงถนนทั้งประเทศ + สรุปอัตราการเชื่อมรายภาค | รอขั้น 1 |
| 3 | Notebook 19: จักรวาลช่วงถนนใหม่, target รายวัน/6 ชม., feature builder (อากาศ, AADT, ปฏิทิน) — ต้องตรวจความครอบคลุมอากาศทั่วประเทศก่อน | รอขั้น 2 |
| 4 | Notebook 20: ล็อก protocol ใหม่ก่อน fit แล้วทดลอง Poisson / RF / HGB เทียบ baseline เหมือน V3 + ประเมินแยกภาค | รอขั้น 3 |
| 5 | Notebook 21–23: evaluation, ระดับสี, diagnostic ปี 2026 | รอขั้น 4 |
| 6 | Notebook 22 → 14 → 24: serving bundle, catalog ประวัติ, API V4 + pin/hash ใหม่ | รอขั้น 5 |
| 7 | Frontend: ชี้ไป API V4 (ไม่ต้องแก้หน้าเว็บ) | รอขั้น 6 |

## ความเสี่ยงที่รู้แล้ว
- **ขนาดข้อมูล:** จาก 3,105 ช่วง อาจเป็นหลักหมื่นช่วง และ panel ราย 6 ชม. ใหญ่ขึ้นหลายเท่า อาจต้องสุ่มตัวอย่างช่วงที่ไม่มีเหตุ หรือแยกโมเดลตามภาค (ตัดสินที่ขั้น 3–4 จาก `panel_size_estimates`)
- **อากาศ:** archive เดิมครบไม่ทุกจังหวัด/ปี (V2: 204/385 จังหวัด-ปี) ต้องหาแหล่งเพิ่ม หรือให้ model fallback แบบ core (มีอยู่แล้ว) และรายงานชัด
- **คุณภาพพิกัดต่างกันตามจังหวัด:** อัตราการเชื่อมต่ำ = ช่วงนั้นยังเป็น "ไม่มีข้อมูล" รายงานรายภาค
- **โมเดล V3 ใช้นอกพื้นที่นำร่องโดยตรงไม่ได้:** ต้องฝึกและประเมินใหม่ตาม protocol

## ขั้น 1 — คำสั่ง (รันบน Mac ที่ root ของ repo)
```
.venv/bin/python backend/scripts/run_spatial_road_collection.py --online --config spatial_road_sources_v4.json --output-dir backend/rerun-road-national-001
```
- ผล: `backend/rerun-road-national-001/reports/v4/road_collection/` (รายงานไทย, manifest, status) และ `.../data/v4/road_collection/` (raw + GeoJSON, git ไม่เก็บ)
- งบ request/ขนาด/เวลาใน config v4 ตั้งเผื่อทั้งประเทศ (หลังรันนำร่อง ทางการบอกจำนวนทั้งประเทศราว DOH 3,044 / DRR 3,700 สาย)
- ตรวจรับเมื่อ: `road_collection_status.json` = complete, ไม่มี `exceededTransferLimit`, count/IDs ก่อนและหลังตรงกัน, ไฟล์ที่ protect ไม่เปลี่ยน
