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

## ขั้น 3–4 (National Step 3.command — รันข้ามคืน)
- Notebook ต้นฉบับของพื้นที่นำร่อง (19–24, 14) **ไม่ถูกแก้** เพราะ API ปัจจุบันตรวจ hash ของ notebook 13/14/22/24 ตอนเปิด — งานทั่วประเทศใช้สำเนา `notebooks/*_national.ipynb` ที่เลือก config ผ่าน `ROADAWARE_STAGE_CONFIG`
- runner ทุกตัวรับ `--config <ชื่อไฟล์>` และรัน notebook ตามฟิลด์ `notebook` ใน config (v3 = ต้นฉบับ, v4 = สำเนา national)
- `config/spatial_preparation_v4.json`: กติกา v3 เดิมทั้งหมด เปลี่ยนเฉพาะ input → ผลขั้น 1–2 ระดับประเทศ (snapshot `rc315c7c508f`), output → `reports|data/v4/spatial_preparation`
- `scripts/national_prep_gate.py` (รันระหว่าง 19 กับ 20): ตรวจผล 19 ครบทุก hash/check → คัดลอกขึ้น v4 (ไม่เขียนทับ) → review อัตโนมัติ → แบ่ง transfer split จาก geometry อย่างเดียว (อีสานตอนบน lon ≥ 103.0, lat ≥ 15.5) → เขียน pins และ `config/spatial_experiment_v4.json` (ขนาด OOF ตามจำนวนช่วงถนนจริง, artifact budget 64 GiB, threads 6)
- โมเดล/ตัวชี้วัด/เกณฑ์เลือก เหมือน v3 ทุกอย่าง

### ผลขั้น 3 (2026-11-18)
- Notebook 19 ระดับประเทศผ่าน 41 checks: ช่วงถนน DOH 26,740 ช่วง (51,858 กม., 1,440 สายทาง), บันทึกอุบัติเหตุที่ใช้ได้ 98,207 จาก 106,308
- transfer split (geometry อย่างเดียว): eval 3,070 / train 23,458
- รอบแรกของ Notebook 20 รันผิดตัว (config v4 ชี้ไป notebook ต้นฉบับ ซึ่งอ่าน config v3) จึงได้ผลซ้ำของพื้นที่นำร่อง — เก็บไว้ที่ `backend/rerun-spatial-model-pilot-repro-001` (ไม่ใช้ต่อ) แก้ config แล้ว รันใหม่ด้วย National Step 4.command → `rerun-spatial-model-national-002`
- รอบ `rerun-spatial-model-national-002`: ข้อมูลถูกต้อง (OOF 19.5M/78.1M แถว) แต่โมเดลทุกตัวถูกปฏิเสธเพราะ route_code มี 1,440 สายทาง เกินเพดาน 255 ของกติกา v3 → ผลเลือกเป็น baseline เท่านั้น (ไม่ใช้ต่อ)
- แก้ในสำเนา national: encoder รวมสายทางที่พบน้อยเป็นระดับ "infrequent" เดียว (เรียนจาก training sample ของแต่ละ fold เท่านั้น) แล้วรันใหม่ → `rerun-spatial-model-national-003` (National Step 4b.command)
- `rerun-spatial-model-national-003` หยุดกลางทาง (ผู้ใช้ปิดเครื่องเพราะร้อน หลังรัน ~6 ชม.) ไม่ใช้ต่อ · ลด threads เป็น 4 (ไม่เปลี่ยนผล) แล้วรันใหม่ → `rerun-spatial-model-national-004` (National Step 4c.command)
- `rerun-spatial-model-national-004` หยุดหลัง ~11 ชม. (ยังไม่จบ cell 10): สาเหตุคือ one-hot แบบ dense ของ 6 h sample (3.47M แถว × ~300 คอลัมน์) ใช้ RAM เกิน 16 GB → swap
- แก้ในสำเนา national: one-hot แบบ sparse (Poisson/RF), progress.log, fit cache (`backend/rerun-fitcache-spatial_experiment_v4.0`) ให้หยุด/รันต่อได้ → `National Step 4d.command` (root ใหม่ทุกครั้งตามเวลา)
- 2026-11-20: ผู้ใช้เลือกใช้โมเดลเดียวเพื่อลดเวลา → ฝึกเฉพาะ hgb_poisson_fixed (ตัวที่ถูกเลือกในพื้นที่นำร่อง) ยังต้องผ่านเกณฑ์เทียบ baseline เดิม
