# RoadAware backend — data foundation + model research (ML research only)

โฟลเดอร์นี้เก็บงานข้อมูล/ML ของ RoadAware: notebook ข้อมูล 01–05, notebook โมเดล 06–07, config, runner และ tests **ยังไม่มี API/เว็บ และไม่มีโมเดลที่พร้อมใช้งานจริง** (`production_enabled = false`)

```
backend/
  config/data_pipeline.json        ค่าตั้งต้น, alias ของ schema, split, allowlist, blocker ที่ยังไม่แก้
  config/model_experiment_v1.json  ค่าที่ล็อกตาม workflow/model-protocol-v1.md (แก้แล้ว 06 จะปฏิเสธการรัน)
  notebooks/01..07_*.ipynb         business logic ทั้งหมดอยู่ใน notebook (ดู notebooks/README.md)
  scripts/run_data_notebooks.py    runner ข้อมูลแบบ headless (nbclient + kernel จริง, ไม่เปิดเบราว์เซอร์)
  scripts/run_model_notebooks.py   runner โมเดลแบบ headless (--stage train = 06, analysis = 07, all = 06 → 07)
  tests/test_data_notebooks.py     fixture tests ของเซลล์ "# FUNCTIONS" ใน 01–05
  tests/test_model_notebooks.py    fixture tests ของเซลล์ "# FUNCTIONS" ใน 06–07 และ stage ของ runner (ข้อมูลสังเคราะห์ขนาดเล็ก)
  requirements-data.txt            แพ็กเกจที่จำเป็น (รวม scikit-learn, scipy, joblib, threadpoolctl)
  data/                            (ไม่อยู่ใน git) raw snapshot, interim, processed, data/model (OOF รายแถว, bundles *.joblib)
  reports/data/                    (อยู่ใน git) หลักฐานสรุปขนาดเล็ก JSON/CSV/PNG ของ data foundation
  reports/models/                  (อยู่ใน git) ตาราง metric/selection lock/manifest ของโมเดล (ไม่มีข้อมูลรายแถว)
```

## Model stage — 06 ตรวจรับแล้ว; 07 Codex รันจริงผ่านแล้ว รอการตรวจรับขั้นสุดท้าย; 08 ยังไม่ทำ

```bash
.venv/bin/python backend/scripts/run_model_notebooks.py                                  # --stage all (ค่าเริ่มต้น): 06 → 07
.venv/bin/python backend/scripts/run_model_notebooks.py --stage train                    # 06 เท่านั้น (fit + lock)
.venv/bin/python backend/scripts/run_model_notebooks.py --stage analysis                 # 07 เท่านั้น บนผลของ 06 ที่มีอยู่ (ไม่ refit)
.venv/bin/python backend/scripts/run_model_notebooks.py --output-dir /tmp/ra-model       # rerun อิสระ อ่าน data ชุดเดิม เขียนผลแยก
.venv/bin/python -m pytest backend/tests/test_model_notebooks.py -q                      # fixture tests ของโมเดล
```

`--stage analysis` ตรวจว่า manifest ของ 06 ใน output dir มี `status == ok` แล้วหา hash ของไฟล์/bundle/lock ของ 06 ก่อนและหลังรัน (ต้องไม่เปลี่ยน) และบันทึก log ที่ `reports/models/run_manifest_analysis.json` เพื่อไม่ทับ `run_manifest.json` ของการรัน 06

**Notebook 07 (Evaluation Metrics / Experiment Results):** ตรวจ hash ของ data/config/protocol, semantic hash ของ 06 และเซลล์ FUNCTIONS, manifest ของ 06 (`status == ok`) และทุกไฟล์/bundle **ก่อน** unpickle ตรวจ `selection_lock.json` ทั้งก่อนและหลังให้คะแนน จากนั้นทำนายทั้ง 11 วิธีบนเซลล์ eligible ปี 2024/2025 ชุดเดียวกัน (ไม่ใช้ปี 2026) คำนวณ metric จากไฟล์ prediction ที่บันทึกแล้วคำนวณซ้ำด้วย scikit-learn ผลอยู่ที่ `reports/models/diagnostics/` (ตารางผลหลัก = ตัวดีที่สุดของแต่ละตระกูลจาก OOF + Baseline ที่แข็งที่สุด + Zero baseline แยกแถว, ตารางทุก configuration, coverage ครบ 60 เดือนรวมตัวหาร, อันดับปีหลัง, คะแนน Train in-sample แยกไฟล์) และ `diagnostic_manifest.json` มี `next_stage_contract` สำหรับ 08 provenance ของ runner บันทึกแยก (runner เปลี่ยนเพื่อรองรับ stage จึงไม่บังคับให้ตรงกับตอนรัน 06)

- ฝึก Baseline 4 แบบ + 3 ตระกูลจริง (Poisson 3, Random Forest 2, HGB 2 configuration) ด้วย backtest 4 fold ภายใน Train แล้วล็อกการเลือกจาก OOF (`reports/models/selection_lock.json`) ก่อน fit บน eligible Train ทั้งหมด 06 **ไม่** ให้คะแนนปี 2024/2025
- การตรวจ reload ของ bundle ใช้ `compare_predictions` ที่ rtol = atol = 1e-12 และบันทึก `reload_max_abs_diff` ที่วัดได้ เพราะ Random Forest แบบ `n_jobs=2` รวมผลต้นไม้ในลำดับที่ต่างกันได้ (ความต่างระดับ 1e-15) ส่วน ID ที่เลือก (`choice_sha256`) และ hash ของไฟล์ยังตรวจแบบเท่ากันทุกบิต
- **หลักฐาน 06 (ตรวจรับแล้ว):** Codex รัน 06 จริงครบทุกเซลล์ fit 44 fold + 11 full และตรวจ hash/reload/metric — ดู [`workflow/model-training-verification-th.md`](../workflow/model-training-verification-th.md)
- **หลักฐาน 07 (รันจริงและตรวจแล้ว รอตรวจรับขั้นสุดท้าย):** Codex รัน `--stage analysis` ผ่าน 12 cells, `pytest backend/tests` 128 ผ่าน, metric ตรงกับ sklearn oracle อิสระ 22 คู่ภายใน 1e-12 และไฟล์ upstream 61 ไฟล์ไม่เปลี่ยน — ดู [`workflow/model-evaluation-verification-th.md`](../workflow/model-evaluation-verification-th.md)
- **คำเตือน (ยืนยันด้วยการรัน 07 จริง):** บนเซลล์ eligible ปี 2024, 2025 และสองปีรวมกัน Baseline ค่าเฉลี่ยรายจังหวัดมี Poisson deviance ต่ำกว่าตัวดีที่สุดของทั้งสามตระกูล และในปีหลัง HGB อยู่อันดับดีกว่า Poisson ที่ถูกเลือกจาก OOF ตัวเลือกที่ล็อกไว้ **ไม่เปลี่ยน** ผลนี้เป็นข้อจำกัดของการข้ามช่วงเวลา (มี regime shift จาก cleaning/รูปแบบวันที่) คะแนนอธิบายเฉพาะ province-day ที่ผ่าน quality filter (มี selection bias) ปี 2024 มีเซลล์ eligible เพียง 28% ของ province-day และไม่มีเลยในเดือน ต.ค.–ธ.ค. ส่วนปี 2025 เคยถูกดูแล้ว จึงไม่ใช่ test อิสระ ไม่ใช้ labels ปี 2026 และ `production_enabled = false`
- สัญญาสำหรับ 07 อยู่ใน `next_stage_contract` ของ `reports/models/experiment_manifest.json` ส่วนสัญญาสำหรับ 08 อยู่ใน `reports/models/diagnostics/diagnostic_manifest.json` (ทั้งสองไฟล์ต้องมี `status == ok`)

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
