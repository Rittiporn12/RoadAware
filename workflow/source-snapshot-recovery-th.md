# การนำข้อมูลชุดเดิมกลับมารันตรวจหลัง clone GitHub

เนื้อหาเก่าถูกลบจากเวอร์ชันล่าสุดตามคำสั่งผู้ใช้ แต่ประวัติ Git ยังคงอยู่ ข้อมูลดิบขนาดใหญ่ไม่จำเป็นต้องใส่ซ้ำในทุก checkpoint

Codex ตรวจ SHA256 แล้วเมื่อ 9 พฤศจิกายน 2569: CSV ทั้งหกไฟล์ใน commit `c94af1635f17cbc85d5b4d03cbed765aa054f2df` ตรงกับไฟล์ใน `RoadAware_2rd/data/raw/accidents/` ที่ใช้ตรวจ Notebook ครั้งนี้ทุกไบต์ การตรงกันนี้ยืนยันรุ่นไฟล์ ไม่ใช่ความถูกต้องหรือความครบถ้วนของข้อมูลต้นทาง

## บนเครื่องปัจจุบัน

Notebook 01 อ่านไฟล์จาก RoadAware_2rd ตาม config แล้วสร้างสำเนาใน backend/data/raw/accidents แบบตรวจ hash ห้ามเขียนทับสำเนาที่ไม่ตรงกับต้นทางโดยเงียบ ๆ

## บนเครื่องใหม่หลัง clone แบบมีประวัติครบ

จากโฟลเดอร์ repository เปิด Terminal ใน VS Code แล้วเตรียมโฟลเดอร์ใหม่ที่ยังไม่มีไฟล์ และดึงเฉพาะข้อมูลรุ่นที่ตรวจไว้:

```sh
mkdir -p /tmp/roadaware-source-snapshot
git archive c94af1635f17cbc85d5b4d03cbed765aa054f2df data/raw/accidents | tar -x -C /tmp/roadaware-source-snapshot
```

ถ้า clone แบบ shallow ต้องดึงประวัติที่มี commit นี้ก่อน คำสั่ง archive ไม่เปลี่ยน branch หรือย้อนเวอร์ชันโค้ดปัจจุบัน

ใช้ source override กับ runner สำหรับตรวจซ้ำโดยไม่เปิดเว็บ Jupyter:

```sh
.venv/bin/python backend/scripts/run_data_notebooks.py --source-dir /tmp/roadaware-source-snapshot/data/raw/accidents
```

หรือรันจาก VS Code Notebook โดยแก้ `source_dir` ใน `backend/config/data_pipeline.json` ให้ชี้ไปยังโฟลเดอร์ที่นำออกมา แล้วเลือก kernel `.venv` และ Run All ตามลำดับ 01–05 ดูวิธีติดตั้ง environment และคำอธิบายเพิ่มเติมใน README ของ backend

วันรับไฟล์ดั้งเดิมจากผู้เผยแพร่ยังไม่ทราบ การนำออกจาก Git หรือ import เข้าโปรเจกต์ไม่ใช่วันดาวน์โหลดต้นฉบับ ต้องรักษาความต่างนี้ในทะเบียนข้อมูล
