# RoadAware data notebooks

**สถานะปัจจุบัน V2:** Notebook09–12รันจริงแล้ว HGBรายวันfullและราย6ชั่วโมงcalendar_trafficผ่านbaseline gate ดู [หลักฐาน V2](../../workflow/v2-final-verification-th.md) และ [คู่มือรันใน VS Code](../../workflow/v2-vscode-run-guide-th.md) ใช้runnerในIntegrated Terminalเพื่อให้ขั้น12ตรวจprovenanceของ11ได้ครบ ข้อความสถานะpendingด้านล่างเก็บเป็นประวัติระหว่างพัฒนา ให้ยึดหลักฐานล่าสุดที่ลิงก์ไว้

รันตามลำดับ 01 → 08 (ข้อมูล 01–05 แล้วโมเดล 06–08; VS Code: เลือก kernel `.venv` ที่ root แล้ว *Run All* ทีละไฟล์; หรือ headless ด้วย `backend/scripts/run_data_notebooks.py` และ `backend/scripts/run_model_notebooks.py`) เปิดได้ทั้งจาก root ของ repository หรือจากโฟลเดอร์นี้ notebook จะค้นหา `backend/config/data_pipeline.json` เอง

| # | Notebook | อินพุต (ตรวจ SHA256 ก่อนใช้) | เอาต์พุตหลัก |
|---|---|---|---|
| 01 | `01_data_collection.ipynb` | ไฟล์ดิบ 6 ไฟล์จาก `source_dir` | `data/raw/accidents/*.csv`, `source_manifest.json`, `reports/data/collection_schema_diff.csv` |
| 02 | `02_eda.ipynb` | raw snapshot + `source_manifest.json` | `reports/data/eda/*.csv`, `*.png`, `eda_summary.json` |
| 03 | `03_cleaning_preparation.ipynb` | raw snapshot + `source_manifest.json` | `data/interim/*` (cleaned events, quarantine, diagnostic, lineage, row audit, undercount flags), `artifact_manifest.json`, `reports/data/quality_report.json` |
| 04 | `04_split_strategy.ipynb` | `source_manifest.json` + `artifact_manifest.json` | `data/processed/event_split_assignments.csv`, `province_day_panel.csv`, `split_artifact_manifest.json`, `reports/data/split/*` |
| 05 | `05_data_leakage.ipynb` | manifests ทั้งสามชั้น (lineage) | `reports/data/leakage/*` |
| 06 | `06_baseline_candidate_models.ipynb` | panel + manifests + leakage report (อ่านอย่างเดียว) + `config/model_experiment_v1.json` | `data/model/oof_predictions.csv`, `data/model/bundles/*.joblib` (ไม่อยู่ใน git), `reports/models/*` (metric, fold, support, bootstrap, `selection_lock.json`, `experiment_manifest.json`, `model_artifact_manifest.json`) |
| 07 | `07_evaluation_experiment_results.ipynb` | ผลของ 06 ที่ `status == ok` (ตรวจ hash ของทุกไฟล์/bundle/lock และเซลล์ FUNCTIONS ของ 06 ก่อนใช้) + panel ที่ตรวจแล้ว | `data/model/diagnostic_predictions.csv` (รายแถว ไม่อยู่ใน git), `reports/models/diagnostics/*` (ตารางผลหลัก, ทุก configuration, coverage 60 เดือน, รายเดือน, อันดับปีหลัง, `diagnostic_manifest.json`) |
| 08 | `08_error_analysis_model_selection.ipynb` | ผลของ 06 และ `diagnostic_manifest.json` ของ 07 ที่ `status == ok` (ตรวจ hash ของไฟล์ทั้งหมด, lock, เซลล์ FUNCTIONS ของ 06/07) + OOF/diagnostic predictions ที่บันทึกไว้ + panel; **ไม่** โหลด bundle | `reports/models/error_analysis/*` (slice ราย เดือน/วันในสัปดาห์/ช่วงจำนวน/จังหวัด, กลุ่มทำนายเกิน/ขาด, calibration-style bins, cohort วันที่ 1–12 กับ 13–31, กราฟ, `error_analysis_manifest.json`), `reports/models/model_card_th.md`, `reports/models/model_decision_summary.json`, `data/model/error_analysis_rows.csv` (ไม่อยู่ใน git) |

แต่ละ notebook มีส่วนเป้าหมาย/อินพุต/การแปลง/เอาต์พุต/การตรวจ/ข้อจำกัด/สัญญาขั้นถัดไปเป็นภาษาไทย และมีเซลล์ `# FUNCTIONS` ที่ไม่พึ่ง state อื่น ซึ่ง `backend/tests/test_data_notebooks.py` (01–05) และ `backend/tests/test_model_notebooks.py` (06–08) นำไปรันกับ fixture โดยตรง Notebook 07 ใช้ฟังก์ชันของ 06 โดย exec เซลล์ `# FUNCTIONS` ของ 06 เฉพาะเมื่อ SHA256 ตรงกับ manifest ของ 06 ส่วน 08 exec เซลล์ของ 06 แล้ว 07 เฉพาะเมื่อ hash ตรงกับ manifest ของ 06 และ `diagnostic_manifest.json` ของ 07 ตามลำดับ

ข้อตกลงสำคัญ: ไม่มีการเติมค่าที่ไม่ทราบเป็น 0; วันที่กำกวมถูกกักกันและวันที่ผู้สมัครถูกธง `possibly_undercounted`; ธงและ `training_eligible` เป็นคอลัมน์ตรวจสอบเท่านั้น ห้ามเป็น feature; การผ่าน assertion ไม่ได้แปลว่าข้อมูลครบถ้วนหรือ "ไม่มี leakage" โดยรวม

Notebook 06 เป็นงานวิจัยย้อนหลังแบบมีเงื่อนไข (`production_enabled = false`): เลือกโมเดลจาก OOF ปี 2022–2023 เท่านั้น และไม่ให้คะแนนปี 2024/2025 (Codex ตรวจรับแล้ว ดู `workflow/model-training-verification-th.md`)

Notebook 07 ให้คะแนนโมเดลทั้ง 11 วิธีที่ล็อกไว้บนเซลล์ eligible ปี 2024 (7,885 เซลล์ 103 วัน ไม่มี support ในเดือน ต.ค.–ธ.ค.) และปี 2025 (27,506 เซลล์ เคยถูกดูแล้ว) โดยไม่ refit/tune/calibrate และไม่เปลี่ยนตัวเลือกจาก OOF ผลจากการรันจริง: Baseline ค่าเฉลี่ยรายจังหวัดมี Poisson deviance ต่ำกว่าตัวดีที่สุดของทั้งสามตระกูลในทุก scope และในปีหลัง HGB อยู่อันดับดีที่สุดในสามตระกูล ไม่ใช่ Poisson ที่ถูกเลือกไว้ — รายงานเป็นข้อจำกัด ไม่ใช่ผู้ชนะใหม่ สถานะ 07: Codex ตรวจรับแล้ว ดู `workflow/model-evaluation-verification-th.md`

Notebook 08 วิเคราะห์ความผิดพลาดของ selected candidate และ strongest baseline ที่ล็อกไว้จาก prediction ที่ตรวจ hash แล้วเท่านั้น (ไม่ refit/tune/calibrate และไม่เปลี่ยนตัวเลือก) คำนวณ metric OOF/fold/ปีหลังซ้ำเทียบตารางและ lock, ทำ calibration-style bins ที่ขอบมาจาก OOF เท่านั้น, ตรวจ cohort shift หลัง cleaning แล้วเขียน model card ภาษาไทยที่แสดงการกลับอันดับในปีหลังอย่างเด่นชัด และเสนอให้ **ระงับการนำไปใช้** จนกว่าจะแก้ blocker ของข้อมูล (recommended reference ตาม protocol OOF ไม่ใช่การอนุมัติใช้งาน) grouped permutation sensitivity (ทางเลือก) ไม่ได้ทำ โดยระบุเหตุผลไว้ `run_model_notebooks.py --stage analysis` runs 07 -> 08. Review: ACCEPTED; 143 tests passed and full 06-08 rerun verified. [Final verification](../../workflow/model-final-verification-th.md)

## V2 notebooks - current research evidence

| Notebook | Purpose | Outputs |
|---|---|---|
|09_external_collection_date_evidence.ipynb|External sources, date evidence, availability registry|reports/v2/sources|
|10_v2_preparation_features_leakage.ipynb|Repair, preparation, features, leakage checks|reports/v2/preparation; data/v2|
|11_v2_model_experiments.ipynb|Three candidate families, baselines, frozen time backtest and selection|reports/v2/models; data/v2/models|
|12_v2_evaluation_error_analysis.ipynb|Metric reconciliation, ablations, slices, calibration and drift|reports/v2/analysis; data/v2/analysis|

09-12 independently reviewed as research work. 11 selected HGB full (daily) and HGB calendar_traffic (6h), both passed the frozen baseline gate. 12 does not fit or reselect models. Follow the [VS Code guide](../../workflow/v2-vscode-run-guide-th.md) and [final evidence](../../workflow/v2-final-verification-th.md). Data/raw/predictions/bundles are ignored; aggregate reports and plots are tracked. Existing accepted outputs cannot be overwritten: use a fresh output root for replay. No untouched test and production_ready=false; frontend/API/Dashboard deferred.
