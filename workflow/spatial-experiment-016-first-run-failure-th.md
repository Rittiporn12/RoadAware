# ผลตรวจรอบ spatial model 016-001

11 พฤศจิกายน 2026: ยังไม่ตรวจรับการทดลอง Notebook20 รอบแรก

## สิ่งที่รันจริง

คำสั่ง `.venv/bin/python backend/scripts/run_spatial_experiments.py --output-dir backend/rerun-spatial-model-016-001` ใช้เวลา 3,286.74 วินาที เริ่ม 14:20:49 และจบ 15:15:35 น. กรุงเทพฯ

ฝึกและประเมิน temporal OOF, ตรึงตัวเลือกโมเดล, ประเมินปี 2024–25 ที่เคยเห็นแล้ว และ spatial-transfer diagnostic จบ แต่ cell14 ขั้น reports ล้มเหลว จึงไม่มี complete experiment manifest, final CSVs, arrays index หรือกราฟของรอบนี้ ห้ามนำผลบางส่วนไปอ้างว่าทั้ง pipeline ผ่านแล้ว

ตัวตรวจ `routing_trigger_excludes_bank_calendar_and_labels` ตรวจ substring `y_` ในชื่อคอลัมน์ จึงปฏิเสธ `aadt_mean_heavy_share_pct` ซึ่งเป็น predictor ที่อนุญาต เพราะคำว่า `heavy_share` มี substring ดังกล่าว ต้องให้ Claude แก้การตรวจโดยยังคงป้องกัน target leakage และเพิ่ม regression test ที่ครอบคลุมเส้นทางตรวจจริง

## หลักฐานในเครื่อง

- `backend/rerun-spatial-model-016-001/reports/v3/run_manifest_spatial_experiments.json`: status failed, CellExecutionError / ExperimentError, cell timings และ traceback
- `backend/rerun-spatial-model-016-001/notebooks/20_spatial_count_experiments.ipynb`: executed notebook พร้อม error
- `.ai-team/runs/20261111-140025-2040/`: รายงานและ review FAIL ของ worker เดิม
- `.ai-team/references/016-independent-*.json`: ผลตรวจอิสระบางส่วนก่อนล้มเหลว ไม่ทดแทนการตรวจ full pipeline

Source notebook SHA256 ก่อนและหลังรันตรงกัน: `e6428f9cc4d1cbaefbc81d6c163a870700eefd7c35847059af61d8b6a353a0e9`

Config SHA256 ก่อนและหลังรันตรงกัน: `fbd053cca837fa184f28f6b6839c6f538ce5c458bb9fc7368cfbc552afbf90b0`

ทดสอบ fixture เดิมซ้ำจริงด้วย `.venv/bin/python -m pytest backend/tests/test_spatial_experiments_notebook.py -q`: 27 passed, 12 warnings, 2.25 วินาที การผ่าน fixtures ไม่ครอบคลุมข้อผิดพลาดที่พบใน actual run นี้

## งานแก้ที่เตรียมแล้ว

[task016a](tasks/016a-spatial-reports-control-correction.md) เป็น correction รอบ1 ให้ Claude แก้โค้ดและเพิ่ม coverage โดยห้ามเปลี่ยนโมเดล baseline split feature sampling หรือเกณฑ์เลือกตามคะแนนที่เห็นแล้ว หลังแก้ Codex ต้องตรวจ diff รัน tests และ full experiment ใน root ใหม่ `backend/rerun-spatial-model-016-002` ไม่แก้ผลรอบที่ล้มเหลวให้กลายเป็นผ่าน

ผู้ใช้สั่งพักงานเวลาเดิม และกลับมาอนุญาตให้ทำต่อหลัง Claude reset เวลา17:42 น. เรียก Claude ผ่าน bridge แล้ว ใช้ worker ครั้งละหนึ่งราย ส่วน catalog14, evaluation/สี21, serving22 และ API ยังรอขั้นตอนที่เกี่ยวข้องผ่านก่อน ไม่มี frontend ในรอบนี้
