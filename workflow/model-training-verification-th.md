# ผลตรวจรับ Notebook 06 — 10 พฤศจิกายน 2569

รับงานเฉพาะ Baseline/Candidate training (task002/002a) แล้ว ส่วน Evaluation และ Error Analysis ใน07/08 ยังอยู่ระหว่างทำ ไม่ใช่การรับรองระบบจริง

## หลักฐานที่รันโดย Codex

- `.venv/bin/python backend/scripts/run_model_notebooks.py --timeout 900`: ผ่าน13 code cells ใน42.45วินาที ด้วย kernel จริง ไม่เปิด Jupyter บนเว็บ
- Baseline4แบบ + configuration ของ Poisson3, Random Forest2, HGB2:44 fold fits และ11 full-Train fits ผ่านทั้งหมด ไม่มี fit warnings
- `.venv/bin/python -m pytest backend/tests -q`:97 passed ใน5.77วินาที (รวมข้อมูลเดิม54กรณีและโมเดล43กรณี) หลัง Claude แก้ assertion ของข้อความ error ที่ไม่ตรงในรอบแรก96pass/1fail
- คำนวณคะแนนทุก11วิธีซ้ำด้วย sklearn: MAE/RMSE/Poisson deviance/bias/totals ตรงภายใน1e-12; zero baseline deviance เป็นnull
- OOF42,058จังหวัด–วันเดียวกันทุกวิธี รวมจำนวนเหตุ24,448; Train63,757แถว; ไม่มี key ซ้ำ
- ตรวจ source semantic hash, model manifest และทุก output/bundle hash ผ่าน; โหลดจริงทั้ง11bundleใน Python process ใหม่ ผลรวม prediction ตรงภายใน tolerance
- RF reload ความต่างสูงสุด8.88e-16; repeat1.33e-15 ใน notebook ผ่าน rtol=atol1e-12; process ตรวจอิสระพบ repeatสูงสุด1.78e-15
- ข้อมูลและรายงานเดิมที่เฝ้าตรวจ33ไฟล์ hashไม่เปลี่ยน; leakage/readinessเดิมยังBLOCKED

## ผลเลือกที่ล็อกไว้

Poisson `poisson_alpha_1e-4` ชนะ pooled OOF Poisson deviance0.937128 เทียบ Baselineรายจังหวัด1.112497 (ดีขึ้น15.76%) ผ่านเกณฑ์ที่ระบุไว้ก่อนฝึกทั้ง4foldและbootstrap ช่วง95%ของผลต่าง[-0.23534,-0.09267] เป็น exploratory ไม่ปรับผลการเลือกหลายโมเดล

Random Forestที่ดีที่สุดคือ `rf_t120_d16_l128_m100` (deviance1.071341); HGBคือ `hgb_i120_l15_m50_r1` (0.974299) โดย HGBมี MAE/RMSE ดีกว่า Poisson จึงต้องรายงาน tradeoff

decision_sha256 `63aeb27230f9e439ecda7d6f07243510d7ff292c85d411eea6f45d8008ecc787`

choice_sha256 `4781bb5adcf649b0ff8e5cd278067a10d80cd1bd569cea5c39dc336bf7ffb30e`

## ข้อจำกัดและงานถัดไป

ผล precheckปี2024/2025ให้ Baselineดีกว่าทั้งสามตระกูลตามคะแนนหลัก และพบความต่างตามช่วงวันในเดือน/รูปแบบวันที่หลังcleaning ต้องทำ07/08เพื่อแสดงผลและerror analysisที่ตรวจได้ โดยไม่เปลี่ยนตัวเลือก OOFหรือtuneจากปีที่เคยเห็น

`production_enabled=false`; คะแนนเป็น retrospective conditional province-day research ไม่ใช่ความน่าจะเป็นของผู้เดินทางหรือโมเดลรายเส้นทาง ปี2024ขาดeligibleQ4 และ2025เคยถูกดูแล้ว ไม่มี independent untouched test

ไฟล์จริง: [Notebook06](../backend/notebooks/06_baseline_candidate_models.ipynb), [tests](../backend/tests/test_model_notebooks.py), [manifest](../backend/reports/models/experiment_manifest.json), [lock](../backend/reports/models/selection_lock.json), [metrics](../backend/reports/models/oof_metrics.csv)

การเปิดและRun Allผ่าน VS Code UI ยังไม่ได้ตรวจโดยอัตโนมัติ; ยืนยันการรันด้วย root `.venv` ผ่าน nbclient และ metadata/kernel สำหรับ VS Code เท่านั้น

Claudeเขียนโค้ดทั้งหมด; Codexถ่ายโอนไฟล์ส่งต่อของ Claude แบบไม่แก้ source เมื่อเครื่องมือ Read/Writeติดขนาด notebook จากนั้นตรวจ diff/รัน/ตรวจรับอิสระ รายงานworkerอยู่ `.ai-team/runs/20261110-015059-34260/result.json` (local/ignored)
