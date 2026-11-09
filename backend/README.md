# RoadAware backend — data foundation (ML research only)

โฟลเดอร์นี้เก็บงานข้อมูล/ML ของ RoadAware: notebook 5 ตัว, config, runner และ tests **ยังไม่มีการเทรนโมเดลและยังไม่มี API/เว็บ**

```
backend/
  config/data_pipeline.json      ค่าตั้งต้น, alias ของ schema, split, allowlist, blocker ที่ยังไม่แก้
  notebooks/01..05_*.ipynb       business logic ทั้งหมดอยู่ใน notebook (ดู notebooks/README.md)
  scripts/run_data_notebooks.py  runner แบบ headless (nbclient + kernel จริง, ไม่เปิดเบราว์เซอร์)
  tests/test_data_notebooks.py   fixture tests ที่รันโค้ดจากเซลล์ "# FUNCTIONS" ของ notebook
  requirements-data.txt          แพ็กเกจที่จำเป็น (pandas, numpy, matplotlib, nbformat, nbclient, ipykernel, pytest)
  data/                          (ไม่อยู่ใน git) raw snapshot, interim, processed — ข้อมูลรายแถว
  reports/data/                  (อยู่ใน git) หลักฐานสรุปขนาดเล็ก JSON/CSV/PNG
```

## ติดตั้ง (ครั้งเดียว, ที่ root ของ repository)

```bash
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements-data.txt
```

`.venv` อยู่ที่ root ของ repository เสมอ runner จะปฏิเสธ Python ตัวอื่น (ไม่มี fallback ไปยัง Python ของระบบ)

## ข้อมูลต้นทาง

ค่าเริ่มต้น `source_dir` = `../../RoadAware_2rd/data/raw/accidents` (อ้างอิงจากโฟลเดอร์ `backend/`) ต้องมี `accidents_2564_original.csv` ถึง `accidents_2569_original.csv` ครบ 6 ไฟล์ ถ้าไม่ครบ Notebook 01 จะหยุดพร้อมรายชื่อไฟล์ที่ขาด เปลี่ยนตำแหน่งได้ 3 วิธี: แก้ `source_dir` ใน config, ตั้ง env `ROADAWARE_SOURCE_DIR`, หรือใช้ `--source-dir` ของ runner ไฟล์ต้นทางถูกอ่านอย่างเดียว ไม่ถูกแก้ไข

## วิธีรัน

**A. ใน VS Code (แบบโต้ตอบ):** เปิดโฟลเดอร์ repository → ติดตั้ง extension Python และ Jupyter → เปิด `backend/notebooks/01_data_collection.ipynb` → *Select Kernel* → *Python Environments* → `.venv` → *Run All* แล้วทำซ้ำตามลำดับ 01 → 02 → 03 → 04 → 05 (แต่ละตัวอ่านเฉพาะไฟล์ที่ตัวก่อนหน้าบันทึกไว้และตรวจ hash ก่อนใช้) ไม่ต้องเปิด Jupyter ในเบราว์เซอร์

**B. ตรวจแบบ headless คำสั่งเดียว (ไม่มีเบราว์เซอร์):**

```bash
.venv/bin/python backend/scripts/run_data_notebooks.py                       # เขียนผลลงใน backend/ และบันทึก output ใน notebook
.venv/bin/python backend/scripts/run_data_notebooks.py --output-dir /tmp/ra  # rerun อิสระ: /tmp/ra/{data,reports,notebooks}
.venv/bin/python -m pytest backend/tests -q                                  # fixture tests (ไม่ต้องใช้ข้อมูลจริง)
```

runner หยุดที่ notebook แรกที่ล้มเหลว บันทึก notebook ที่รันบางส่วนพร้อม error และเขียน `reports/data/run_manifest.json` (เวลา, hash, สถานะ, error)

## หลักฐาน (หลังรันจริง)

| ไฟล์ | เนื้อหา |
|---|---|
| `data/raw/accidents/source_manifest.json` | hash, จำนวนแถว, schema, ที่มา (ไม่อยู่ใน git) |
| `reports/data/eda/` | ตาราง/กราฟ EDA บนข้อมูลดิบ |
| `reports/data/quality_report.json` | บัญชีแถว retained/collapsed/quarantined/diagnostic และเหตุผล |
| `reports/data/split/` | `split_summary.json/csv`, `province_scope.csv`, กราฟรายวัน |
| `reports/data/leakage/` | `leakage_audit.json`, `feature_availability_matrix.csv`, `negative_controls.csv`, `readiness_summary.json` |
| `reports/data/run_manifest.json` | log ของ runner |

## สถานะ

- **ตรวจจริงแล้ว 9 พฤศจิกายน 2569:** Notebook ทั้ง 5 รันครบด้วย Python kernel ของโปรเจกต์ และรันซ้ำในโฟลเดอร์ใหม่ผ่าน; fixture tests 54 กรณีผ่าน, leakage checks 12 รายการผ่าน และ negative controls 9 กรณีถูกปฏิเสธตามคาด ไฟล์ CSV 26 ไฟล์ตรงกันทุกไบต์ระหว่างสองรอบ ดู [หลักฐานตรวจอิสระ](reports/data/independent_review.json)
- ข้อมูลดิบ 127,375 แถว → retained 84,296, quarantined 27,840, diagnostic ไม่มีรหัส 15,239; collapsed 0 ภายใต้กฎเคร่งครัดรอบนี้ การกันข้อมูลออกอาจทำให้เกิด selection bias จึงยังไม่ใช่ข้อมูลที่รับรองพร้อมฝึกโมเดลจริง
- รันจริงผ่าน nbclient แบบไม่มีเบราว์เซอร์และบันทึก output ใน `.ipynb`; ยังไม่ได้ยืนยันการกด Run All ผ่านหน้าต่าง VS Code โดยเครื่องมืออัตโนมัติ วิธีรันใน VS Code อยู่ด้านบน
- ปี 2025 เคยถูกใช้/ดูมาแล้ว → `reused_test_2025` **ไม่ใช่ test อิสระ**; ปี 2026 (2569) ไม่มี ACC_CODE → ใช้วินิจฉัยเท่านั้น
- panel จังหวัด×วันเป็นการสาธิตความพร้อมของข้อมูล **ไม่ใช่หน่วยสายทางของโมเดลจริง**
- **ความพร้อมของโมเดลจริง: BLOCKED** (ดู `unresolved_blockers` ใน config และ `reports/data/leakage/readiness_summary.json`)

หลัง clone ใหม่ ดู [วิธีนำ source snapshot กลับมารัน](../workflow/source-snapshot-recovery-th.md) และ [แผน Analytics/Dashboard ที่ยังไม่เริ่มทำ](../workflow/analytics-and-dashboard-plan-th.md)
