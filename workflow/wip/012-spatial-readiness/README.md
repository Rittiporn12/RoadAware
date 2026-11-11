# Spatial readiness 012 — งานจริงที่รันแล้ว แต่ยังรอแก้ก่อนตรวจรับ

**สถานะภายหลัง:** แก้และตรวจรับ audit แล้ว: 94 tests / 27 checks, notebook รอบ003สำเร็จ 11.03s ดู [หลักฐานใหม่](../../spatial-readiness-verification-th.md) ข้อความด้านล่างและ archive คงเป็นประวัติรอบก่อนแก้ ปัญหา login ใน sandbox แก้โดยเรียก bridge ด้วย require_escalated หลัง Terminal connection ผ่านแล้ว

- Notebook16, config, runner และ tests มี source จริงแล้ว ไม่มี spatial model fit หรือเกณฑ์สี
- รัน `.venv/bin/python -m pytest backend/tests/test_spatial_readiness_notebook.py backend/tests/test_inference_notebook.py -q`: **90 passed** (spatial33 + inferenceเดิม57), 11.31s, joblib warningเดิมเรื่อง physical-core fallback
- รัน notebook ด้วย kernel .venv จริง: **15 code cells, 9.87s, 27 checksผ่าน** เชื่อม retained106308, auditraw127375, input protected345ไม่เปลี่ยน และตรวจ backend302 trackedfilesเดิมไม่เปลี่ยน
- Notebookใน backend/notebooks มีผลรันจริงจากรอบนี้แล้ว; aggregate30outputs/4figures, run log และ independent review เก็บใน [archiveรอตรวจรับ](../../../backend/reports/v3/attempts/spatial_readiness_012_review_pending/independent_review_pending.json) ไม่ใช่ accepted final reports
- แถวข้อมูล2CSV.gzอยู่ local ignored `backend/rerun-spatial-012-002/data/v3/spatial_readiness/`; ไม่อัปข้อมูลรายแถวขึ้นGit

## เหตุผลที่ยังไม่รับงาน

1. runner.preconditions(BACKEND/data/v2) คืนNone ทำให้ mainสร้าง output setup dirs ก่อน notebookจะปฏิเสธ outputที่ทับเขตข้อมูลเดิม ต้องตรวจทุกwritepathก่อนmkdirใดๆ (Codexตรวจ probeแบบอ่านอย่างเดียว ไม่ได้ทดลองเขียนในข้อมูลจริง)
2. กราฟ raw coordinate status แบบ stacked logซ่อนส่วนแรกบางกลุ่ม ต้องเปลี่ยนการแสดงcountที่ตรงไปตรงมา และปรับlabelจังหวัดในNNfigureให้อ่านได้

ส่งแก้ผ่าน [012a](../../tasks/012a-spatial-readiness-correction-1.md) แล้ว แต่ run20261111-082455-61421 ตอบ **Not logged in · Please run /login** ก่อนเริ่มทำงาน ไม่ใช่quotaresetและไม่ใช่ข้อผิดพลาดในโค้ดที่แก้แล้ว เปิด Login Claude.command ให้ผู้ใช้แล้ว จึงยังไม่มีผลแก้หรือผลรันทดสอบรอบใหม่ และรอบ authfailureนี้ไม่นับเป็นcorrectionที่ตรวจโค้ดแล้ว

## ทำต่อหลังloginพร้อม

ตรวจว่าไม่มีworkerอื่นกำลังรัน (Login scriptอาจทดสอบconnectionอัตโนมัติ) → run012a → ตรวจdiff/pytest/รันnotebookที่outputrootใหม่ → ดู4figuresและhash/reconciliation → reviewpassเมื่อแก้จริงแล้ว → ย้ายผล accepted ไป finalV3พร้อมสรุปหลักฐาน → task013เก็บroadgeometry snapshot ก่อนสร้างspatiallabels/fitmodels ห้ามรับรองโมเดลรายจุดจาก90testsนี้

แหล่งข้อมูลถนนทางการที่ตรวจระหว่างรอ: [metadata6responses + manifest](../../spatial/source_discovery/README_th.md) DOHcount3044และsample1LineString,DRRcount3700 ยังไม่ใช่fullgeometrysnapshotหรือverifiedroadinventory
