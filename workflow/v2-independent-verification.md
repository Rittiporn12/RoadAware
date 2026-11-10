# หลักฐานตรวจรับ V2 — 10 พฤศจิกายน 2026

Codex ตรวจผลจริงแยกจากรายงานของ Claude; การตรวจรับแต่ละขั้นเป็นงานวิจัย
ไม่ได้หมายถึงระบบพยากรณ์พร้อมใช้งาน ข้อมูลและรายงาน V1 ไม่ถูกแก้ไข

## Notebook 09: ผ่านการตรวจรับ (004c)

- คำสั่งจริง: `.venv/bin/python backend/scripts/run_v2_notebooks.py --stage collect`
  รอบออนไลน์ใช้ 972.28 วินาที ผ่าน final checks และป้องกันไฟล์ V1 จำนวน 135 ไฟล์
- AADT กรมทางหลวง 2020–2025: 6 ปี × 77 จังหวัด = 462 จังหวัด-ปี;
  ปี 2024 แยกบรรทัดว่างทั้งหมด 2,130 บรรทัดจากจุดสำรวจ 2,736 แถวอย่างชัดเจน
- ชื่อจังหวัดเชื่อมแบบตรงตัวด้วย alias ที่ตรวจแล้ว จุดภูมิศาสตร์ครบ 77 จังหวัด
  และทุกจุดอยู่ภายในขอบเขต ปฏิทินธนาคารที่ตรวจหลักฐานครบ 95 actions
  (ไม่ได้อ้างว่าเป็นปฏิทินวันหยุดราชการทั้งหมด)
- อากาศย้อนหลัง: 42/80 ชุด; มีข้อมูล 204/385 จังหวัด-ปี, ครบทุกค่ารายชั่วโมง
  172 จังหวัด-ปี; เก็บ 2021–2022 ครบจังหวัดและ 2023 จำนวน 50 จังหวัด
  ยังไม่มีอากาศ 2024–2025 รอบนี้หยุดตามงบคำขอ 4,407.4 จากเพดาน 4,500
  (35 คำขอใหม่) ไม่ใช่การเก็บครบ 5 ปี
- ฝนติดลบ 222 ชั่วโมงถูก mask เฉพาะค่านั้นเป็น NaN โดยเก็บ JSON ดิบไว้
  อุณหภูมิยังใช้ได้ ช่วงฝน 6/24 ชั่วโมงที่ไม่ครบไม่ถูกบวกรวมบางส่วน
- ตรวจอิสระเทียบ JSON เดิม 306,600 ชั่วโมงจากแคชเดิม 7 ชุด:
  อุณหภูมิและฝนที่ถูกต้องตรงเดิมทั้งหมด เปลี่ยนเฉพาะฝนติดลบ 24 ค่า
  SHA256 ของ JSON เดิมทั้ง 7 ไฟล์ไม่เปลี่ยน
- รัน offline ในสำเนาแยกทั้งก่อนและหลังเก็บเพิ่ม รอบเต็ม 42 ชุดใช้ 53.59 วินาที
  ใช้เครือข่าย 0 ครั้ง; derived outputs ทั้ง 6 ไฟล์มี SHA256 ตรงรอบออนไลน์
- รายงานจริง: `backend/reports/v2/sources/sources_manifest.json`,
  `source_audit_th.md`, `weather_value_quality.csv`, `weather_coverage.csv`

## Notebook 10: ผ่านการตรวจรับ (005)

- คำสั่งจริง: `.venv/bin/python backend/scripts/run_v2_notebooks.py --stage prepare --offline`
  ใช้ 96.92 วินาที; รันซ้ำด้วย `--output-dir /private/tmp/roadaware-005-repro`
  ใช้ 97.95 วินาที ข้อมูล 8 ไฟล์และรายงาน 24 ไฟล์มี SHA256 ตรงทุกไฟล์
- นำเข้า 127,375 แถว; retained เพิ่มจาก 84,296 เป็น 106,308 (+22,012)
  วันที่กำกวมที่มีหลักฐานและบริบทผ่าน 22,052 แถว แต่ 40 แถวยังมีข้อจำกัดอื่น
  จึงไม่ได้เพิ่มเป็น retained ทั้งหมด; อีก 5 แถวไม่มีบริบทจังหวัดครบจึงไม่ซ่อม
- วันที่และสถานะ retained เดิม 84,296 แถวไม่เปลี่ยน กลุ่ม strict conflict
  2,309 แถวยังกักกัน ปี 2026 จำนวน 15,239 แถวเป็น diagnostic ไม่เป็น label
- สร้าง 140,602 province-day cells และ 562,408 province × 6h cells
  ตรวจอิสระว่า sum ของ 4 บล็อกตรงรายวันทุก key และยอดรวมตรง 106,308
  มี eligible daily cells 116,973; eligibility เป็นตัวกรองย้อนหลังจากคุณภาพ
  label ไม่ใช่ feature หรือหลักฐานว่าทราบล่วงหน้า
- ชุด 2024 เหลือ eligible 7,885/28,182 cells (ประมาณ 28%) จึงเป็น diagnostic
  ที่มี selection สูง ต้องแสดงข้อจำกัดเมื่อรายงานโมเดล
- จราจรทุก 1,377 วันที่มี vintage ผ่านการตรวจอิสระว่า survey year < target year
  และเวลา available-from ไม่เกิน issue; 2022-03-25 ยังไม่ใช้ AADT2021,
  เริ่มใช้ได้ในเป้าหมาย 2022-03-26 ตาม metadata proxy
- Leakage negative controls ปฏิเสธข้อมูลรั่ว 13/13 กรณี ตรวจภาพ EDA ทั้ง 3 ภาพแล้ว
- รายงานจริง: `backend/reports/v2/preparation/data_preparation_v2_th.md`,
  `preparation_manifest.json`, `row_reconciliation_v2.csv`, `leakage_audit.json`

## การทดสอบและขั้นโมเดล

- V1 data/model + bridge review tests: 146 passed (8.66 วินาที)
- V2 source/preparation fixtures: 50 passed (รอบล่าสุด 0.90 วินาที)
- V2 model fixtures: 19 passed (2.42 วินาที); Notebook 11 ประกอบและตรวจ
  nbformat แล้ว แต่ยังไม่ตรวจรับผลฝึกจริง
- ล็อก protocol/config/manifest และ data hashes ก่อน fit ครั้งแรกใน
  `workflow/model-protocol-v2-lock.json`; สาม candidate families,
  5 feature variants, 4 expanding folds และ baseline ใช้ keys เดียวกัน
- สถานะ ณ บันทึกนี้: กำลังรัน Notebook 11 จริง ยังไม่มีข้อสรุป V2 ว่าโมเดลใดชนะ
  ไม่มี untouched test: 2024/2025 เคยใช้พัฒนาแล้ว; production_ready=false

ประวัติการตรวจรับรายงาน worker อยู่ใน local `.ai-team/runs/` (gitignored)
โดย 004c = `20261110-175342-94403`, 005 = `20261110-150447-82585`;
ไฟล์ข้อมูลรายแถวอยู่ใน `backend/data/` (gitignored) และรันตรวจได้บนเครื่องนี้
รายงานที่อยู่ใน Git เป็นผลสรุป ไม่ใช้แทน raw snapshot ที่ตรวจ SHA256

## การแก้ส่วนบันทึกผลหลังทดลองครั้งแรก (ยังรอตรวจรับโมเดล)

การทดลองครั้งแรกใช้ 1,209.99 วินาที โดย candidate OOF fits ทั้ง 160 ครั้ง
และ baseline fits 48 ครั้งมีสถานะ ok, convergence warning 0 แต่ final check
พบว่า `run_manifest_model.json` ซึ่ง runner แก้ทุกเซลล์ถูกนับเป็น immutable
report ทำให้ hash ไม่ตรง จึงบันทึกครั้งแรกเป็น **failed** และไม่ตรวจรับ
หลักฐานอยู่ใน `backend/reports/v2/attempts/model_001_failed/`; ข้อมูลรายแถว/
bundle ถูกเก็บแยกใน `backend/data/v2/model_attempts/model_001_failed/` (ignored)

Claude แก้เฉพาะ REPORT cell 16 ให้แยกไฟล์ log ดังกล่าว และย้ายตำแหน่ง log
ของ runner ไปที่ `reports/v2/run_manifest_model.json` นอก model report folder
FUNCTIONS, fit/selection/diagnostic cells, configuration และ protocol ไม่เปลี่ยน
บันทึก hash ก่อน/หลังใน `model-protocol-v2-report-amendment.json`;
manager lock แก้เพียง notebook-source hash และอ้างอิงบันทึกการแก้นี้
ชุดทดสอบ source/model/analysis หลังแก้ผ่าน 91 ข้อ (2.83 วินาที)

รอบใหม่เริ่มจาก Terminal ภายใน VS Code เวลา 22:38 น. ใช้ข้อมูล/ค่าทดลองเดิม
ภาพหน้าจอและหน้าต่าง Terminal แสดงคำสั่งและ daily OOF 53,610 แถว/26 methods
เสร็จใน 157.0 วินาที ณ บันทึกนี้กำลังคำนวณ 6h OOF; ยังไม่ตรวจรับรอบใหม่

การตรวจคำเตือน NumPy แยกจากโมเดล: บน NumPy2.0.2/Accelerate ของเครื่องนี้
matrix-vector ปกติมีคำเตือน divide/overflow/invalid แต่ผลตรงกับ `einsum`
ภายใน 1.60e-14 (`reviews/numpy_matmul_probe.json`)
มีรายงานอาการคล้ายกันใน [NumPy #28687](https://github.com/numpy/numpy/issues/28687)
และ [#29820](https://github.com/numpy/numpy/issues/29820); ใช้เป็นบริบทประกอบ
ไม่ใช่หลักฐานว่าทุก warning ปลอดภัยหรือเป็นสาเหตุเดียวกันแน่นอน

จึงตรวจ bundle Poisson ของครั้งแรกด้วย contraction ที่ไม่ใช้ BLAS จริง:
ตัวอย่าง diagnostic 2,000 แถวต่อหน่วยต่างจากค่าที่บันทึกสูงสุด 1.25e-14
(daily) และ 1.34e-15 (6h); gradient สูงสุดใน train เท่ากับ 9.96e-7 และ
8.52e-7 ตามลำดับ ต่ำกว่า tol1e-6 ที่ล็อกไว้ และ coefficient finite ทุกค่า
ผลละเอียด `backend/reports/v2/reviews/poisson_numeric_attempt1.json`;
ยังต้องยืนยันผลรอบใหม่และวิเคราะห์ error ด้วย Notebook12 ก่อนสรุปโมเดล
