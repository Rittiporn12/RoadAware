# หลักฐานตรวจรับ Notebook 19

Codex ตรวจรับ 11 พฤศจิกายน 2026 หลังแก้ขอบเขต population lookup ใน 015a โดยไม่ได้เปลี่ยนข้อมูลหรือฝึกโมเดล

- ทดสอบเฉพาะ 83 กรณีผ่าน และ backend ทั้งหมด 538 กรณีผ่าน มี warning เดิม 42 รายการ
- รันจริงด้วย kernel .venv ในโฟลเดอร์ใหม่ actual002 ใช้ 89.36 วินาที เปิด full-population feature audit และผ่าน 41 checks
- ประชากรจาก geometry: DOH 3,105 segments, 218 routes; selected+linked events 27,459 รายการ ปี 2021–25 จำนวนรายวันตรงกับผลรวมช่วง 6 ชั่วโมง
- ตรวจอิสระ midpoint/admin join ทั้ง 3,105 จุด, AADT 12,714 groups และวันเลือก vintage 2,556 วัน รวมทั้ง weather context 74,460 daily / 297,840 six-hour rows
- reference features 4,000 แถวตรงทุกค่าเมื่อโหลดกลับ; ความคลาดเคลื่อนการอ่าน weather ตัวเลขดิบไม่เกิน 1.43e-14
- data outputs 18 ไฟล์ตรงทุกไบต์กับรอบแรก; report hashes 21 ไฟล์ตรวจครบ; protected snapshot 545 ไฟล์ไม่เปลี่ยน ยกเว้น README ที่อนุญาต
- ตรวจภาพกราฟผลจริง 3 ภาพแล้ว เป็นผลเตรียมข้อมูล ไม่ใช่ผล forecast

หลักฐานเครื่องอ่านได้: `backend/reports/v3/spatial_preparation_independent_review.json`, `backend/reports/v3/spatial_preparation/spatial_preparation_manifest.json` และ executed notebook `backend/notebooks/19_spatial_count_preparation.ipynb`

ข้อจำกัด: target คือจำนวนบันทึกที่ผ่านการคัดเลือกและเชื่อมถนนได้ ไม่ใช่อุบัติเหตุจริงทั้งหมด; weather ปี 2024–27 ไม่มีใน snapshot; AADT เป็นข้อมูลสำรวจรายปี ไม่ใช่จราจรสด; calendar ปีอนาคตบางส่วนยังไม่ทราบ ต้องคง missing และทดสอบ fallback ก่อน serving
