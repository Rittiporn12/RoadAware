# รันและตรวจซ้ำ V2 ใน VS Code

คู่มือนี้ใช้ข้อมูลที่ตรวจรับแล้วบนเครื่อง RoadAware ปัจจุบัน เปิดโฟลเดอร์ root
ใน VS Code แล้วเลือก **Terminal → New Terminal** คำสั่งด้านล่างใช้ Python
จาก `.venv` และประมวลผลเซลล์ใน `.ipynb` ด้วย kernel ในเครื่อง ไม่เปิดเว็บ Jupyter
ส่วนโค้ด ML ทั้งหมดอยู่ใน Notebook; `.py` เป็น runner และการทดสอบ

เปิดอ่านโค้ดและผลที่บันทึกไว้ได้ใน `backend/notebooks/09…12*.ipynb`
เลือก interpreter/kernel `.venv` ของ RoadAware เมื่อต้องใช้งาน notebook editor
การตรวจรับ Notebook12 ต้องมี runner log จากการรัน `--stage model` ที่จบจริง
จึงแนะนำ workflow ผ่าน Terminal ใน VS Code ด้านล่าง

## ตรวจชุดทดสอบ

จาก root ของ repository:

```sh
.venv/bin/python -m pytest backend/tests tools/test_ai_team_review.py -q
```

ตรวจได้ทั้ง parsing/การซ่อมวันที่, panel, as-of joins/leakage, การประเมินและ
เลือกโมเดล, hash/lock, การคำนวณซ้ำ และระบบบันทึกผล ไม่ใช้เครือข่ายใน fixtures

## ตรวจการเตรียมข้อมูลซ้ำ

```sh
.venv/bin/python backend/scripts/run_v2_notebooks.py --stage prepare --offline --output-dir backend/rerun-prepare-001
```

อ่าน source09 และ V1 เดิมโดยไม่แก้ไข เขียนผลใหม่ใต้โฟลเดอร์ที่กำหนด
เปรียบเทียบ `data_outputs` ใน manifest ใหม่กับ
`backend/reports/v2/preparation/preparation_manifest.json` ได้ด้วย SHA256
ผลที่ตรวจไว้แล้วมีข้อมูล 8 ไฟล์และรายงาน 24 ไฟล์ตรงกันทุกไฟล์เมื่อรันซ้ำ
ด้วย input และ software versions เดิม

## ทดลองโมเดลซ้ำด้วยกติกาที่ล็อกไว้

```sh
.venv/bin/python backend/scripts/run_v2_notebooks.py --stage model --output-dir backend/rerun-model-001
```

ใช้ accepted10 และ manager lock เดิมโดยปริยาย ทุกวิธีใช้ข้อมูล/เวลา cutoff
และ hyperparameters เดียวกับ protocol ไม่มีการเลือกใหม่จากคะแนน 2024/2025
การรันเต็มประกอบด้วย 160 candidate OOF fits และ 48 baseline OOF fits
รวมทั้ง final fit และ diagnostic ทั้งสองหน่วย จึงต้องรอให้กระบวนการจบ

ตรวจ `<output>/reports/v2/run_manifest_model.json` ว่า `status = ok`,
ทุก notebook entry เป็น `ok` และ `v1_protected_unchanged = true`
จากนั้นอ่าน `<output>/reports/v2/models/model_manifest.json` และ model card
ตัวเลขเลือกโมเดลและ selection lock อยู่ในโฟลเดอร์เดียวกัน ส่วน predictions
รายแถวและ bundles อยู่ `<output>/data/v2/models/`

## วิเคราะห์ผลการทดลองซ้ำ

เมื่อ model stage จบและตรวจผลแล้ว:

```sh
.venv/bin/python backend/scripts/run_v2_notebooks.py --stage evaluate --model-dir backend/rerun-model-001/reports/v2/models --model-data-dir backend/rerun-model-001/data/v2/models --output-dir backend/rerun-analysis-001
```

Notebook12 ตรวจ log และ hashes ของ11, คำนวณ metrics/selection gate ซ้ำจาก
predictions และเขียนตาราง error slices/ablation/calibration พร้อม PNG และ
รายงานไทยใต้ `backend/rerun-analysis-001/reports/v2/analysis/`
เปิด executed notebook ใน `backend/rerun-analysis-001/notebooks/` ด้วย VS Code
เพื่อตรวจผลเซลล์ได้โดยตรง

หากชื่อ output เคยรันแล้ว ให้ใช้ชื่อใหม่ เช่น `002` การปฏิเสธเขียนทับช่วยรักษา
ประวัติผลทดลอง `backend/rerun*/` และ `backend/data/` ถูก ignore ใน Git เพื่อ
ไม่อัปโหลดข้อมูลรายแถวหรือ bundles ส่วนผลสรุปที่ตรวจรับแล้วอยู่ใน
`backend/reports/v2/` และประวัติ GitHub

## ขอบเขตการทำซ้ำ

- เปลี่ยน source/preparation/config แล้วต้องตรวจรับและสร้าง planning lock ใหม่
  ห้ามเปลี่ยน hash เพียงเพื่อผ่านการตรวจ ผลเดิมมีหลักฐาน input versions ชัดเจน
- บนเครื่องใหม่ต้องจัดหา raw/cache snapshots ที่ตรง SHA256 หรือดำเนินการเก็บ
  และเตรียมข้อมูลเป็น run ใหม่ repository เก็บโค้ดและผลสรุป ไม่ได้แนบ raw ทั้งหมด
- ข้อมูลอากาศใน experiment นี้ยังไม่ครบ 5 ปี รายงานแสดงช่องว่างจริง
  2024/2025 เป็นปีที่เคยใช้พัฒนาแล้ว ไม่มี untouched test และยังเป็นงานวิจัย
