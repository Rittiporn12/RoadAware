# RoadAware data notebooks

รันตามลำดับ (VS Code: เลือก kernel `.venv` ที่ root แล้ว *Run All*; หรือ headless ด้วย `backend/scripts/run_data_notebooks.py`) เปิดได้ทั้งจาก root ของ repository หรือจากโฟลเดอร์นี้ notebook จะค้นหา `backend/config/data_pipeline.json` เอง

| # | Notebook | อินพุต (ตรวจ SHA256 ก่อนใช้) | เอาต์พุตหลัก |
|---|---|---|---|
| 01 | `01_data_collection.ipynb` | ไฟล์ดิบ 6 ไฟล์จาก `source_dir` | `data/raw/accidents/*.csv`, `source_manifest.json`, `reports/data/collection_schema_diff.csv` |
| 02 | `02_eda.ipynb` | raw snapshot + `source_manifest.json` | `reports/data/eda/*.csv`, `*.png`, `eda_summary.json` |
| 03 | `03_cleaning_preparation.ipynb` | raw snapshot + `source_manifest.json` | `data/interim/*` (cleaned events, quarantine, diagnostic, lineage, row audit, undercount flags), `artifact_manifest.json`, `reports/data/quality_report.json` |
| 04 | `04_split_strategy.ipynb` | `source_manifest.json` + `artifact_manifest.json` | `data/processed/event_split_assignments.csv`, `province_day_panel.csv`, `split_artifact_manifest.json`, `reports/data/split/*` |
| 05 | `05_data_leakage.ipynb` | manifests ทั้งสามชั้น (lineage) | `reports/data/leakage/*` |
| 06 | `06_baseline_candidate_models.ipynb` | panel + manifests + leakage report (อ่านอย่างเดียว) + `config/model_experiment_v1.json` | `data/model/oof_predictions.csv`, `data/model/bundles/*.joblib` (ไม่อยู่ใน git), `reports/models/*` (metric, fold, support, bootstrap, `selection_lock.json`, `experiment_manifest.json`, `model_artifact_manifest.json`) |

แต่ละ notebook มีส่วนเป้าหมาย/อินพุต/การแปลง/เอาต์พุต/การตรวจ/ข้อจำกัด/สัญญาขั้นถัดไปเป็นภาษาไทย และมีเซลล์ `# FUNCTIONS` ที่ไม่พึ่ง state อื่น ซึ่ง `backend/tests/test_data_notebooks.py` (01–05) และ `backend/tests/test_model_notebooks.py` (06) นำไปรันกับ fixture โดยตรง

ข้อตกลงสำคัญ: ไม่มีการเติมค่าที่ไม่ทราบเป็น 0; วันที่กำกวมถูกกักกันและวันที่ผู้สมัครถูกธง `possibly_undercounted`; ธงและ `training_eligible` เป็นคอลัมน์ตรวจสอบเท่านั้น ห้ามเป็น feature; การผ่าน assertion ไม่ได้แปลว่าข้อมูลครบถ้วนหรือ "ไม่มี leakage" โดยรวม

Notebook 06 เป็นงานวิจัยย้อนหลังแบบมีเงื่อนไข (`production_enabled = false`): เลือกโมเดลจาก OOF ปี 2022–2023 เท่านั้น ไม่ให้คะแนนปี 2024/2025 (เป็นงานของ 07/08 ที่ยังไม่ได้ทำ) precheck พบว่า Baseline ค่าเฉลี่ยรายจังหวัดดีกว่าทั้งสามตระกูลบนเซลล์ปีถัดไป และพบ regime shift จาก cleaning/รูปแบบวันที่ — ดู `workflow/model-preliminary-findings-th.md` สถานะรับงานขั้นสุดท้ายรอ Codex
