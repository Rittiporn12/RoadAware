# ผลตรวจรับ Notebook18 — 11 พฤศจิกายน2026

ตรวจรับ **descriptive linkage audit และ candidate road segments** แล้ว ยังไม่มี spatial count labels,โมเดลรายถนนหรือเกณฑ์สี ผลนี้แยกจากผลโมเดลระดับจังหวัดเดิม

- รันข้อมูลจริงรอบแก้ไข002ใช้48.87วินาที ผ่าน38checks
- testsเฉพาะ61ผ่าน(0.69วินาที);backendทั้งหมด455ผ่าน(22.34วินาที) มี40pyproj/NumPy deprecation,1pandas futurewarningและ1joblib core-count warningที่บันทึกไว้ ไม่ได้ซ่อนwarning
- เหตุ106,308UIDเชื่อมกับlineageเดิมตรงทุกคอลัมน์: ในกรอบนำร่อง31,089;นอกกรอบ75,219 กระทบยอดyear/agency/splitตรงกับreferenceที่บันทึกก่อนเห็นผล
- เกณฑ์หลัก50เมตร matched28,476เหตุ;มีsegmentกำหนดได้28,353 อีก123ยังลงsegmentไม่ได้จากclip/tolerance ไม่ยืนยันว่าจุดอยู่นอกกรอบ ทั้ง123ต้องเป็นunknownในขั้นสร้างlabel
- DOH matched27,779จาก28,726;DRR697จาก1,290;EXATยังไม่verifiedcrosswalkจึงไม่บังคับจับคู่ จุดprecisionต่ำและรหัสDRRพิเศษแยกสถานะ
- inventoryจากgeometry:500เมตร25,358ช่วง;1กม.13,197ช่วง;2กม.7,167ช่วง รวม45,722ช่วง(เป็น3resolutionของถนนชุดเดียวกัน ห้ามบวกเป็นระยะทางโครงข่าย)
- ตรวจทุกช่วงด้วยการคำนวณใหม่:projectedlengthต่างสูงสุด3.31e-9เมตร,geodesiclength2.28e-13เมตร ตรวจchosenroad-distance28,753เหตุที่matchedอย่างน้อย1tolerance ตรงกับค่าที่บันทึก และตรวจidentityของทุกprimary-assignedsegment
- ตรวจSHA28reportfiles/8datafiles ไฟล์dataทั้ง8เหมือนรอบ001ทุกbyte การแก้เปลี่ยนเฉพาะvalidationchecks ไฟล์เดิม574ไฟล์ไม่เปลี่ยน ยกเว้นREADMEที่อนุญาตแก้
- ตรวจกราฟproducer3ภาพและinternalconsistencysample9ประเภท พร้อมตรวจsampleที่โปรแกรมส่งออก211UIDไม่ซ้ำ การดูภาพนี้ไม่ใช่groundtruthaccuracyหรือการรับรองถนนจริง

## สิ่งที่แก้และหลักฐานรอบไม่ผ่าน

รอบ001รัน52.11วินาทีและหยุดที่500mmax-lengthcheck เพราะsegmentationรวมเศษระยะต่ำกว่าepsilon0.001เมตร แต่ตัวตรวจใช้R+1e-9เมตร Codexสร้างcounterexampleและให้Claudeแก้เฉพาะvalidation พร้อมเพิ่มregressions

อีกจุดคือตัวตรวจunsafeต้องใช้identity `(source_id,oid)` และตรวจparts/piecesทั้งสองทิศ ไม่รวมOIDข้ามหน่วยงาน ผลรอบ001เก็บไว้ใน `backend/rerun-linkage-014-001`(ignored) และสำเนาmanifest/checks/runlogใน `backend/reports/v3/attempts/linkage_014_001_validation_failed/` ไม่ลบหรืออ้างว่าผ่าน

## ตรวจซ้ำใน VSCode

เปิด `backend/notebooks/18_spatial_linkage_audit.ipynb` เลือก `.venv`kernel ผลรันจริงอยู่ในnotebook ส่วนใช้Terminalรันใหม่ต้องตั้งoutputrootใหม่:

```bash
.venv/bin/python -m pytest backend/tests/test_spatial_linkage_audit_notebook.py -q
.venv/bin/python backend/scripts/run_spatial_linkage_audit.py --output-dir backend/rerun-linkage-review-NEW
```

Canonicalaggregates/figuresอยู่ `backend/reports/v3/linkage_audit/` หลักฐานอิสระ `backend/reports/v3/linkage_audit_independent_review.json` Row-level/GeoJSONอยู่ `backend/data/v3/linkage_audit/` ไม่ขึ้นGitHub เครื่องใหม่ต้องมีsourcecache/acceptedinputsที่ตรงhashก่อน

## ข้อกำหนดขั้นถัดไป

ใช้ `status_50m == matched AND segment_status == assigned` ก่อนนำเหตุเข้าlabel เพราะchosenID/segmentIDอาจมีค่าจาก100m-onlyด้วย CSVของchosenOID/partอาจ serialize เป็นเลขจำนวนเต็มในรูปfloat เช่น8.0 ต้องvalidatefinite/integralแล้วcastก่อนjoin ไม่เทียบformattedstring

Eventdatumยังไม่ยืนยัน;currentgeometryไม่รับรองtopologyย้อนหลัง;ไม่มีรายงานไม่เท่ากับไม่มีอุบัติเหตุ ต้องล็อกconditional recorded+linked-count cohort และmissing/zero policyใหม่ ไม่ใช้V2 outcome-derived eligibilityเป็นcoverageหรือfeature ก่อนฝึก3modelsและstrongbaselines
