# ผลตรวจรับข้อมูลถนน V3.1 — 11 พฤศจิกายน 2026

เพิ่มข้อมูลการทางพิเศษจากแหล่ง MOT เพื่อเตรียมจับคู่พิกัดอุบัติเหตุกับถนน ทั้งหมดเป็นข้อมูลรูปทรงถนน ไม่ใช่แผนที่ทำนายความเสี่ยง ยังไม่มีการสร้าง spatial labels หรือฝึกโมเดลรายจุด

| แหล่ง | รายการจริง | หน้า geometry | OID | เส้นที่ไม่ simple |
|---|---:|---:|---|---:|
| กรมทางหลวง | 599 | 30 | objectid | 2 |
| กรมทางหลวงชนบท | 547 | 28 | OBJECTID | 4 |
| การทางพิเศษ | 8 | 1 | objectid_1 | 4 |

EXAT มีฟิลด์ objectid อีกตัวซึ่งไม่ใช่ identity ของ layer จึงมีการทดสอบว่าระบบใช้ objectid_1 จริง และปฏิเสธข้อมูลที่ขาด identity หรือมี OID กำกวม

- ชุดทดสอบเฉพาะผ่าน 66 tests; backend ทั้งหมดผ่าน 394 tests ใน 21.26 วินาที มี warning เดิมของ joblib เรื่องตรวจจำนวน physical cores
- รัน notebook ออนไลน์จริง 35.14 วินาที; offline 17.09 วินาที; หลังแก้หัวกราฟที่ถูกตัดขอบ รัน offline ใหม่ 18.03 วินาที
- ตรวจ SHA-256 raw 154 ครั้ง, reports 28 ครั้ง, derivatives 14 ครั้งในสองรอบแรก และ reports หลังแก้กราฟอีก 14 ครั้ง ผล raw/derivatives ตรงกันทุกครั้ง
- คำนวณความยาวทั้ง 1,154 geometry ใหม่ด้วย pyproj.Geod แยกจากฟังก์ชันหลัก ต่างสูงสุด 0.00428 เมตร
- DOH/DRR full GeoJSON ตรงกับชุด V3.0 ทุก byte; ไฟล์เดิม 469 ไฟล์ไม่เปลี่ยน นอกเหนือจาก 4 ไฟล์ที่อนุญาตแก้
- ตรวจภาพจริงทั้งสองภาพและภาพแผนที่หลังแก้หัวกราฟแล้ว สีแยกแหล่งถนน ไม่ใช่ระดับอันตราย

## ไฟล์และการรันตรวจ

Notebook ที่มีผลรันจริง: `backend/notebooks/17_spatial_road_collection.ipynb` เปิดใน VSCode และเลือก `.venv` Python kernel ได้ ส่วนรายงานอยู่ที่ `backend/reports/v3/road_collection_v3_1/` และหลักฐานตรวจอิสระ `backend/reports/v3/road_collection_v3_1_independent_review.json`

```bash
.venv/bin/python -m pytest backend/tests/test_spatial_road_collection_notebook.py -q
.venv/bin/python -m pytest backend/tests -q
.venv/bin/python backend/scripts/run_spatial_road_collection.py \
  --output-dir backend/rerun-road-review-NEW \
  --cache-from backend/data/v3/road_collection_v3_1 \
  --expect-manifest backend/reports/v3/road_collection_v3_1/road_collection_manifest.json
```

ใช้ output-dir ใหม่ทุกครั้ง ข้อมูลดิบและ geometry อยู่ใน `backend/data/` ที่ไม่ขึ้น GitHub; เครื่องใหม่ต้องเก็บข้อมูลจากแหล่งจริงด้วย `--online` หรือมีสำเนา cache ที่ตรง manifest ก่อน ส่วน source code, aggregate reports, กราฟและผลทดสอบตรวจผ่าน GitHub ได้

## ข้อจำกัดและขั้นต่อไป

กรอบพิกัด [100.2,13.5,102.0,15.3] เป็นพื้นที่นำร่อง ไม่ใช่เส้นทางนำทางจริง และไม่ครอบคลุมถนนทุกประเภท ยังต้องตรวจ road identity, พิกัด, ระยะห่าง, เส้นคู่ขนาน/ทางแยก และเส้นที่ไม่ simple ก่อนจัดสรรอุบัติเหตุให้ช่วงถนน วันเวลาของ geometry ไม่ยืนยันสภาพถนนย้อนหลัง และ datum ของพิกัดเหตุยังไม่ยืนยัน

การเก็บข้อมูลถนนครบตาม query ไม่ได้แปลว่ารายงานอุบัติเหตุครบทั้งหมด ไม่มีรายงานไม่เท่ากับไม่มีอุบัติเหตุหรือปลอดภัย ขั้นต่อไปคือ notebook18 สำหรับ linkage audit และเปรียบเทียบช่วงถนน 0.5/1/2 กม. ก่อนกำหนด target และทดลองโมเดลรายจุด

หมายเหตุเล็กน้อย: ข้อความ error hint เก่าสองจุดใน notebook ยังอ้าง path V3.0 แต่ค่าเริ่มต้น runtime ใช้ config V3.1 และคำสั่งในรายงาน/runner ใช้ path ใหม่ถูกต้อง ไม่กระทบผลข้อมูล
