# ผลตรวจขั้น Data Foundation

วันที่ 9 พฤศจิกายน 2569 | Codex ตรวจอิสระหลัง Claude ส่งมอบงาน

## ขอบเขตที่รับงาน

Python Notebook 01–05 สำหรับ Data Collection, EDA, Cleaning/Preparation, Split Strategy และ Data Leakage พร้อมโครงสร้าง backend/frontend เอกสาร และหลักฐานตรวจซ้ำ ไม่มีการฝึกโมเดล ทำ API หน้าจอเว็บ หรือ Dashboard

## คำสั่งที่รันจริงและผล

```sh
.venv/bin/python -m pytest backend/tests -q
.venv/bin/python backend/scripts/run_data_notebooks.py --timeout 300
.venv/bin/python backend/scripts/run_data_notebooks.py --output-dir /private/tmp/roadaware-independent-final-20261109 --timeout 300
```

- pytest: **54 passed, 0 failed**
- Notebook 01–05: ผ่านทั้งหมดทั้งสองรอบ ใช้ kernel จริงจาก `.venv` และบันทึก output แล้ว ไม่เปิดเว็บ Jupyter
- ตรวจ nbformat และ Python syntax ของทุก code cell ผ่าน; code cells ทุกเซลล์มี execution count และไม่มี error output
- ตรวจ source SHA256 กับไฟล์ต้นฉบับและนับ CSV records อิสระครบทั้ง 6 ไฟล์ รวม **127,375 แถว**
- ตรวจ lineage ครบทุก source_file/source_row ไม่มีแถวหายหรือซ้ำในบัญชีแถว และ retained ตรงกับแถวที่ export จริง
- CSV **26 ไฟล์** ตรงกันทุกไบต์ระหว่างการรันหลักและโฟลเดอร์ใหม่ รายงาน JSON ที่ควรคงที่ให้ผลเหมือนกัน
- ไม่เปรียบเทียบ timestamp, runtime, absolute path, import status และ hash ของ manifest ที่รวม timestamp ว่าต้องเท่ากัน
- Leakage audits **12 รายการผ่าน**, negative controls **9 กรณีถูกปฏิเสธ** รวมข้อมูลผลลัพธ์หลังเหตุ ข้อมูลอนาคต รอยต่อเวลา รหัสซ้ำ พื้นที่นอก Train และ hash ไม่ตรง
- ตรวจ `frontend/` มี README เท่านั้น ไม่มีหน้าจอหรือ scaffold

## ผลจัดข้อมูลภายใต้กฎรอบนี้

| สถานะ | แถว |
| --- | ---: |
| retained identified records | 84,296 |
| quarantined | 27,840 |
| diagnostic ไม่มีรหัสเหตุ | 15,239 |
| collapsed duplicates | 0 |
| รวม | 127,375 |

Panel สาธิตระดับจังหวัด–วันมี 140,602 แถว ครอบคลุม 77 จังหวัดที่มีใน Train ไม่ใช่โมเดลระดับช่วงถนน ขอบเขตจังหวัดอิงชื่อที่รายงานและยังไม่ตรวจเทียบพิกัด

## ข้อจำกัดที่ยังเปิดอยู่

ความพร้อมฝึกโมเดลจริงยังเป็น **BLOCKED**: นิยามวันที่กำกวม เวลาเผยแพร่/รายงานล่าช้า ความครอบคลุมและความครบถ้วนของเหตุ จังหวัดที่ขาดหรือยังไม่ตรวจพิกัด ชุดทดสอบที่เคยเห็นแล้ว ปี 2569 ไม่มีรหัส และความละเอียดพื้นที่สำหรับเส้นทางที่ยังไม่ได้ตกลง การกันข้อมูลออกอาจทำให้ข้อมูลที่เหลือไม่เป็นตัวแทน ต้องแก้/ประเมินก่อนอ้างผลพยากรณ์จริง

ตรวจการติดตั้งส่วนขยายและ workspace interpreter ของ VS Code แล้ว แต่เครื่องมือควบคุม UI ยังไม่สามารถยืนยันการกด Run All ในแอปได้ การรันที่รับรองในรายงานนี้คือ nbclient ด้วย kernel จริงโดยไม่ใช้เว็บ Notebook เปิดต่อใน VS Code และเลือก `.venv` ตาม README ได้

## จุดตรวจหลักฐาน

- [รายงานตรวจอิสระแบบ JSON](../backend/reports/data/independent_review.json)
- [รายการแหล่งข้อมูลและ hash ที่ตรวจแล้ว](../backend/reports/data/source_inventory_verified.json)
- [รายงานการรัน](../backend/reports/data/run_manifest.json)
- [รายงานคุณภาพข้อมูล](../backend/reports/data/quality_report.json)
- [รายงาน Split](../backend/reports/data/split/split_summary.json)
- [Leakage Audit](../backend/reports/data/leakage/leakage_audit.json)
- [วิธีเปิดและรัน Notebook](../backend/notebooks/README.md)
- [วิธีนำข้อมูลจาก snapshot ที่เก็บใน Git กลับมารัน](source-snapshot-recovery-th.md)

การรับงานนี้หมายถึงขอบเขต Data Foundation ผ่านการตรวจตามข้างต้น ไม่ใช่การรับรองความแม่นยำของโมเดล ความปลอดภัยของเส้นทาง หรือความพร้อม production
