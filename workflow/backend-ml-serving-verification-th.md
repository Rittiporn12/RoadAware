# ตรวจรับ ML serving — 10 พฤศจิกายน 2026

Notebook13ตรวจรับแล้วสำหรับbackendวิจัย ส่วนAPI/Notebook14เป็นขั้นต่อไป ไม่ใช่การรับรองproductionหรือความเสี่ยงรายเส้นทาง

## สิ่งที่เสร็จ

- โหลดเฉพาะHGBที่เลือกไว้: daily full และ6h calendar_traffic ตรวจmanifest/config/code/bundlehashและเวอร์ชันก่อนdeserialize
- รับจังหวัด/วันที่/หน่วย/ช่วงเวลา batch1–128 สร้างfeatureจากกฎและsourceas-ofที่ตรวจรับแล้ว ไม่อ่านlabelหรือeligibilityในprediction path
- คำตอบมีค่าคาดการณ์เป็นทศนิยม หน่วยขอบเขตเวลา issueก่อนวันเป้าหมาย18:00Bangkok baseline comparator และสถานะsource/modelage/research
- รองรับresearch scenario2024–2030 วันนอก2024/25แสดงout_of_evaluated_period; อนาคตไม่มีliveweatherและไม่ถูกเรียกว่าผ่านการประเมินเชิงปฏิบัติการ
- ตรวจpublicbatch order, alias, inputผิด, filetampering, missingartifactsและเวอร์ชันผิด

## ผลรันจริงและการตรวจอิสระ

Notebook13ครบ10code cellsใน27.32วินาที ผ่าน18checks Tests57passed in9.40s มีwarningjoblibตรวจจำนวนphysicalcoresบนเครื่องนี้ไม่ได้แต่คืนlogicalcores ไม่มีการปิดwarningเพื่อให้ดูผ่าน

ค่าทำนายผ่านrequest builderเทียบค่าที่11บันทึกไว้ทุกแถว: daily35,467และ6h141,868 รวม177,335แถว ทั้งselectedmodelและbaselineตรงภายใน1e-12 รายการfeatureของทุกdiagnosticrowตรงกับ10แบบbitwiseทั้งหมด ตัวอย่างgridครอบคลุมปี2021–2025 leapday/เทศกาล/ข้อมูลขาด/eligibleและunknown-label

Codexตรวจhash16outputsและFUNCTIONS13ซ้ำ คำนวณstressmetrics16แถวด้วยscikit-learnอิสระ และตรวจ164ไฟล์V1/V2เดิมไม่เปลี่ยน ดู [หลักฐานJSON](../backend/reports/v2/reviews/serving_independent_review.json) และ [รายงานจริง](../backend/reports/v2/serving/serving_report_th.md)

## ข้อผิดพลาดที่ตรวจพบและแก้ก่อนรับงาน

008รอบแรกhelperdictถูกเรียกเหมือนobjectและตัววนbatchอ้างunitก่อนกำหนด Tests7failed/3errors แก้ใน008a จากนั้นtestจริงยังพบtrain-serving skew จึงไม่รับผลเพียงเพราะโหลดโมเดลได้

10เขียนfeatureเป็นCSVแล้ว11อ่านด้วยpandasdefaultparser แต่builderใหม่เคยส่งค่าในหน่วยความจำตรงเข้าโมเดล ค่าdoy_sin/cosต่างเพียง1.11e-16ทำให้treeบางแขนงเปลี่ยน คำทำนายต่างได้สูงสุด4.445918daily/1.4344856h แก้008bโดยทำnumericrepresentationให้เหมือนtraining ไม่มีการลดความเข้มของtolerance เปลี่ยนโมเดล หรือใช้labelเลือกวิธีแก้

เก็บรอบที่ล้มเหลวใน `backend/reports/v2/attempts/serving_001_numeric_failed/` โดยไม่แก้log ส่วนexecutednotebookของรอบล้มเหลวเก็บในlocalignoredreferences; manifestเก่าอ้างpathตอนรัน ต้องเปลี่ยนprefixเป็นarchiveหากจะตรวจไฟล์ที่ย้าย

## ข้อมูลขาดและประสิทธิภาพ

เมื่อทำให้AADTขาดบนkeysเดิม ค่าdevianceแย่ลงทุกunit/split: dailyเพิ่ม0.04447ใน2024/0.02353ใน2025;6hเพิ่ม0.01502/0.00731 จึงส่งcoverageให้ผู้เรียกเห็นแทนการถือว่าข้อมูลยังครบ ผลเหล่านี้เป็นmissing-input sensitivityบนปีที่เคยเห็นแล้ว ไม่ใช่เหตุและผลหรือการประเมินอนาคตใหม่

Weathermissing stressไม่เปลี่ยนผล เพราะ2024/25ไม่มีอากาศอยู่แล้ว และ6hที่เลือกไม่ใช้อากาศ จึงไม่อ้างว่าweatherไม่สำคัญหรือทนการหายได้จากหลักฐานนี้

เวลาfunctionบนเครื่องนี้ (ยังไม่รวมHTTP): coldregistryประมาณ1.60วินาที; warmmedian batch1ประมาณ18.6–18.8ms,32ประมาณ49.6–49.7ms,128ประมาณ110.6–111.1ms ดู [ตารางเวลาจริง](../backend/reports/v2/serving/latency_benchmark.csv) เป็นค่าของเครื่องนี้ไม่ใช่SLA

## วิธีรันใน VS Code

เปิดnotebook13เพื่อดูโค้ดและผล และใช้Integrated Terminalจากroot:

```sh
.venv/bin/python -m pytest backend/tests/test_inference_notebook.py -q
.venv/bin/python backend/scripts/run_v2_notebooks.py --stage serve-check --output-dir backend/rerun-serving-002
```

ใช้outputrootใหม่ทุกครั้ง ผลรับรองในreports/v2/servingห้ามทับ ข้อมูลsource/prediction/bundlesอยู่ในignoreddataต้องกู้snapshotเดิมก่อนรันบนเครื่องใหม่
