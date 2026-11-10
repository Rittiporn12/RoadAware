# หลักฐานตรวจ Notebook 07 — 10 พฤศจิกายน 2569

Codex ตรวจโค้ดและรันจริงด้วย `.venv/bin/python backend/scripts/run_model_notebooks.py --stage analysis --timeout 900`: ผ่าน12 code cells ใน8.3วินาที ไม่มี refit โมเดล ส่วนสถานะรับงาน worker บันทึกแยกใน timeline หลังอ่านรายงานสุดท้าย

สถานะ: ACCEPTED เวลา07:49 หลังตรวจ diff เอกสารและ semantic hash สุดท้าย อ่านรายงาน `.ai-team/runs/20261110-074654-48257/result.json` แล้ว รอบแรกชนtimeoutขณะปิดREADME จึงมีcorrection1เฉพาะเอกสาร ไม่มีการเปลี่ยนโค้ดที่ตรวจผ่าน

ชุดทดสอบรวม `.venv/bin/python -m pytest backend/tests -q`:128 passed ใน7.97วินาที ครอบคลุม source/hash tampering, lock mutation, แถวและ labels เดียวกัน, เดือนว่างเป็นnull, frozen picksไม่เปลี่ยนตามคะแนนปีหลัง และ runner stages

## ตรวจอิสระ

- Codex คำนวณ sklearn oracle ก่อนรัน07ครบ22คู่ของวิธี/ปี จาก11bundlesที่ตรวจhashแล้ว ผล MAE/RMSE/deviance/bias/WAPE/totalsตรงกับ07ภายใน1e-12
- ทุกวิธีใช้35,391เซลล์เดียวกัน:ปี2024มี7,885เซลล์/103วันที่ผ่านเกณฑ์ และปี2025มี27,506เซลล์/359วัน; รวมเหตุ27,530
- ตาราง coverage ครบ60เดือนของ Train/validation/reused_test;2024Q4eligible0และคะแนนnullตามจริง
- ตรวจhashทั้ง61ไฟล์ข้อมูล/รายงาน/โมเดล/Notebook06ที่เฝ้าไว้ ไม่เปลี่ยน; selectionlock byte-identical และchoiceเดิม
- manifest07สถานะokและไฟล์ผลลัพธ์ทุกhashตรง ตรวจกราฟ `diagnostic_main_deviance.png` ด้วยสายตาแล้วอ่านได้และแสดงอันดับที่กลับกัน

## ผลสำคัญ (Poisson deviance; ต่ำดีกว่า)

| วิธีที่เลือก configuration จาก OOF | 2024 | 2025 ที่เคยดูแล้ว |
| --- | ---: | ---: |
| Poisson alpha0.0001 | 2.170024 | 2.254645 |
| Random Forest120ต้น | 2.029973 | 2.055843 |
| HGB120iterations | 1.665437 | 1.712138 |
| Baselineค่าเฉลี่ยรายจังหวัด | **1.153515** | **1.245343** |

ตัวเลือก OOFยังเป็นPoissonตามprotocol ห้ามเปลี่ยนผู้ชนะย้อนหลังจากคะแนนที่เห็นนี้ แต่ทั้งสาม candidate แพ้Baselineในprimarymetricปีถัดไป จึงต้องระงับการนำโมเดลไปใช้งานจริงและตรวจข้อมูลต่อ

## ขอบเขต

คะแนนอธิบายเฉพาะreportedจังหวัด–วันที่ผ่าน offline quality filter ซึ่งมีselection bias ไม่ใช่ทุกถนน/ทั้งปี/ความน่าจะเป็นส่วนบุคคล ปี2025ไม่ใช่ untouchedtest;2026ไม่ได้ใช้labels;production_enabledfalse/readinessBLOCKED

Notebook08จะวิเคราะห์ความผิดพลาดรายกลุ่มและการเปลี่ยนcohort พร้อมmodelcard ขณะนี้07ยังไม่เป็นDashboardหรือrouteforecast

ไฟล์: [Notebook07](../backend/notebooks/07_evaluation_experiment_results.ipynb), [ตารางหลัก](../backend/reports/models/diagnostics/diagnostic_main_results.csv), [coverage](../backend/reports/models/diagnostics/coverage_by_split_month.csv), [manifest](../backend/reports/models/diagnostics/diagnostic_manifest.json)
