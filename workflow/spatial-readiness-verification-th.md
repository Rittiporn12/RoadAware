# ตรวจรับ Spatial Data Readiness (Notebook16)

11พฤศจิกายน2026: ตรวจรับเฉพาะ **audit/feasibility** แล้ว ไม่ใช่ spatial model, road matching, zero-label policy หรือสีความเสี่ยงที่ใช้งานจริง

## หลักฐานที่รันจริง

- `.venv/bin/python -m pytest backend/tests/test_spatial_readiness_notebook.py backend/tests/test_inference_notebook.py -q` → **94passed in12.28s** (spatial37 + inferenceเดิม57) มีjoblibwarningเดิมเรื่องphysical-corefallback ไม่ได้ซ่อนwarning
- `.venv/bin/python backend/scripts/run_spatial_readiness.py --output-dir backend/rerun-spatial-012-003` → **15code cells,11.03s,27checksผ่าน** ใช้project.venvkernelจริง
- เชื่อม retainedV2กลับ raw **106308events** auditrawทั้งหมด127375records; พิกัด/ถนน/KMเป็นflagไม่แก้ค่า;2026ยังdiagnostic
- ตรวจhash30reportoutputsและ2rowoutputs; protected345filesไม่เปลี่ยนในรอบรัน และbackend302trackedfilesเดิมไม่เปลี่ยนจากก่อนเริ่มงาน
- คำนวณอิสระตรงpreflight:routeมีค่า106299,KMมีค่า105991,คู่พิกัดปัด6dpไม่ซ้ำ101473 การมีค่า/อยู่ในกรอบกว้างไม่รับรองพิกัดหรือถนน
- 25aggregateCSVตรงกับรอบแรกแบบbitwise หลังแก้ไม่มีการเปลี่ยนค่าข้อมูลหรือผลaudit ดู4figuresแล้ว (2ภาพแก้ใหม่,2ภาพbyte-identicalกับภาพที่ตรวจรอบแรก)

[Notebookพร้อมผลจริง](../backend/notebooks/16_spatial_data_readiness.ipynb) · [รายงานไทย](../backend/reports/v3/spatial_readiness/spatial_readiness_report_th.md) · [Manifest](../backend/reports/v3/spatial_readiness/spatial_readiness_manifest.json) · [Independent review](../backend/reports/v3/spatial_readiness_independent_review.json)

## พบและแก้ก่อนตรวจรับ

012รอบแรก90testsผ่านและ27checksผ่าน แต่reviewพบrunnerสร้างsetupdirsก่อนkernelตรวจoutputทับprotectedinputs จึงreject เพิ่มguardก่อนทุกmkdir/writeพร้อมnegativefixturesที่เรียกmainจริง ตรวจsymlink/ancestor/validdefaultrootโดยไม่แก้ไฟล์จริง ส่วนกราฟstackedlogซ่อนส่วนประกอบบางกลุ่ม เปลี่ยนเป็นmatrixระบุจำนวนจริงและแก้legendจังหวัดให้อ่านได้

Claude012aแก้runner/testsและส่งsourcecellรูปผ่านfinalreportเพราะReadtoolติดขนาดnotebookที่มีภาพ Codexประกอบpayloadนั้นตรงตามsourceที่Claudeเขียนโดยไม่เพิ่มlogic แล้วรันตรวจรอบใหม่ ผลเดิมเก็บในreports/v3/attempts/spatial_readiness_012_review_pendingห้ามเรียกว่าacceptedlatest

Sandboxรอบ001เริ่มkernelไม่ได้(permission) จึงเก็บหลักฐานไว้และใช้สิทธิ์ที่อนุญาตรัน002/003 การเรียกClaudeในsandboxภายหลังแจ้งNot logged inแม้Terminalconnectionผ่านแล้ว เรียกbridgeด้วยrequire_escalatedแล้วทำงานต่อสำเร็จ ไม่ใช่หลักฐานว่าquotaหมด

## ผลที่ได้และงานต่อ

- มีevent-levelrawlineageและตารางตรวจพิกัด/route/KM/ความเบาบางตามproxy groupsที่รันตรวจได้ ไม่สร้างzeroโดยไม่มีuniverse/coverage ไม่ถือprovinceeligibilityเป็นข้อมูลที่รู้ก่อนเกิดเหตุ
- ยังไม่มีregisteredgeometryที่ตรวจcontent/coverageแล้ว จึงยังไม่ยืนยันpoint-in-province,road snapping,stable segments,zero labelsหรือความสามารถforecastรายจุด
- ต้องทำ [task013](tasks/013-spatial-road-snapshot-collection.md): เก็บofficialroadgeometrysnapshotในกรอบนำร่องจากMOT/DRR พร้อมID/page/CRS/hashchecks ก่อนสร้างspatiallabelsและล็อกmodelprotocol แหล่งทางการQueryได้จริง ดู [discovery](spatial/source_discovery/README_th.md)
- มี4กราฟdescriptiveจากข้อมูลจริง แต่แผนที่ความหนาแน่นย้อนหลัง **ไม่ใช่แผนที่พยากรณ์ความเสี่ยง** ไม่มีตัวเลขสีหรือaccuracyรายจุดที่แต่งขึ้น

ข้อมูลรายแถวอยู่backend/data/v3/spatial_readiness(ignored) หลังcloneต้องกู้source snapshotตามhashก่อนรัน ใช้outputrootใหม่ทุกครั้งและเปิดnotebookในVSCodeด้วยkernel.venv
