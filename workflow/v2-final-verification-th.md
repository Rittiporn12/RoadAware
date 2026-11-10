# หลักฐานตรวจ V2 — 10 พฤศจิกายน 2026

Codex ตรวจแยกจากรายงานของ Claude: ข้อมูลและโมเดลนี้เป็นงานวิจัยระดับจังหวัด ยังไม่พร้อมใช้งานจริง และยังไม่มีเว็บ/API/Dashboard

## ข้อมูลและการทำให้แต่ละปีตรงกัน

Notebook09 ทำ registry ของแหล่งข้อมูลจริงและหลักฐานวันที่รายปี; Notebook10 ใช้ schema กลางและเก็บ lineage/คอลัมน์ตรวจสอบ แยกคอลัมน์ที่ใช้เป็น feature ออกจาก label/ข้อมูลหลังอุบัติเหตุ ไม่ได้บังคับให้คอลัมน์ที่หายไปกลายเป็นศูนย์

- ซ่อมวันที่จากหลักฐานต้นฉบับ 22,052 รายการ; retained events เพิ่มจาก84,296เป็น106,308 (บางรายการยังถูกตัดด้วยเงื่อนไขอื่น)
- panel140,602จังหวัด×วัน และ562,408จังหวัด×6ชั่วโมง; ผลรวม4ช่วงตรงกับรายวัน
- Notebook10 รัน96.92วินาที; รันซ้ำแยก97.95วินาที ผล8data/24report hashesตรงกัน
- AADT ปี2020–2025ครบ77จังหวัดต่อปี ใช้ vintage ที่พร้อมก่อน issue time เป็นค่าเฉลี่ยจุดสำรวจรายปี ไม่ใช่ความหนาแน่นรถสดหรือ exposure
- อากาศใช้ archived forecast previous_day2: มีข้อมูลอย่างน้อยบางส่วน204/385 province-years (ครบช่วง172) ปี2024/2025ไม่มีอากาศ ไม่เติมข้อมูลจากอนาคต
- ปฏิทินBOTเป็นวันหยุดธนาคารตามข้อมูลที่ประกาศแล้ว ไม่ใช่วันหยุดราชการทั้งหมด; เทศกาลสงกรานต์/ปีใหม่ ฤดูกาล และช่วง6ชั่วโมงแยก feature ชัดเจน
- ปี2024 label eligible7,885/28,182เซลล์; eligibility เป็นตัวกรองจากผลย้อนหลัง จึงยังใช้กับอนาคตเชิงปฏิบัติการไม่ได้

## การทดลองและตัวเลือก

Protocol/config/data ถูกล็อกก่อน fit: 4 expanding folds ใน2022–2023, 3families, 5feature variants, baseline6แบบต่อหน่วย เลือกด้วย pooled OOF mean Poisson deviance แล้วล็อกก่อนดู2024/2025ซึ่งเป็น previously-seen diagnostics

| หน่วย | Poisson | Random Forest | HGB | strongest baseline | HGBลดdeviance | HGB MAE / baseline |
|---|---:|---:|---:|---:|---:|---:|
|daily|1.089593|1.127834|1.064258|1.146383|7.1638%|0.660085 / 0.689391|
|6h|0.596262|0.601836|0.583525|0.607755|3.9868%|0.257759 / 0.267592|

ตัวเลือกวิจัยคือ **HGB Poisson**: daily=`full`, 6h=`calendar_traffic` ทั้งคู่ชนะ4/4foldและผ่าน gate ที่ล็อกไว้ CI95%ของผลต่างdevianceเทียบbaseline: daily[-0.136283,-0.042289], 6h[-0.041223,-0.010806] เป็น paired7-day block bootstrap500ครั้ง seed42 แบบ exploratoryหลังเลือก ไม่ปรับ multiple comparison

ไม่อ้างว่าชนะทุกbaselineทุกmetric: zero baseline มี MAE ต่ำกว่าในข้อมูล6hที่มีศูนย์มาก ไม่เปรียบเทียบerrorข้ามหน่วยหรือเปอร์เซ็นต์ดีขึ้นเทียบV1เพราะcohortต่างกัน

## หลักฐานการรันและการตรวจอิสระ

- Notebook11 clean run สำเร็จใน VS Code Integrated Terminal: 22:38:32–23:01:14, notebook1361.44วินาที,11code cellsสำเร็จ และV1protected filesไม่เปลี่ยน
- รอบแรกฝึกสำเร็จแต่ final check ล้มเหลวเพราะ hash ของ runner log ที่ยังเปลี่ยนอยู่ เก็บหลักฐานไว้ใน `backend/reports/v2/attempts/model_001_failed/` ไม่ทับหรือแก้ให้ดูผ่าน
- Correction006aแก้เฉพาะการรายงาน/การตรวจ runner log แยกออกจาก immutable outputs ทุกfit/selection cellและconfigเดิมไม่เปลี่ยน มี [report-only amendment](model-protocol-v2-report-amendment.json)
- ตรวจhash9inputs,4predictionfiles,18bundles,12modelreports; independent scikit-learn oracle ตรวจ52OOF methods ทุกmetricภายใน1e-12
- Poissonมี RuntimeWarning จากmatmulบนเครื่องนี้ จึงไม่ถือว่าคำสั่งสำเร็จเพียงอย่างเดียว: คำนวณด้วยeinsumอิสระเทียบ2,000แถวต่อหน่วย ผลต่างสูงสุด1.25e-14/1.34e-15 และgradientเต็มTrainต่ำกว่าtol1e-6 ดู [ผลตรวจตัวเลข](../backend/reports/v2/reviews/poisson_numeric_verified_run.json) ไม่ได้ปิดwarningหรือเปลี่ยนenvironmentเพื่อให้ผ่าน
- Notebook12 รัน23:08:03–23:08:22 (18.36วินาที) กระทบยอด2,664metric values/392ablation values, ตรวจslice totals,240calibration bins,14PNG; isolated replay18.6วินาที ตารางCSV18ไฟล์เหมือนกันทุกbyte
- พบ title/axis disclosure ของกราฟเปรียบเทียบวิธีถูกตัด จึงส่ง correction007aเฉพาะlayoutก่อนตรวจรับขั้นสุดท้าย รายละเอียดผลรอบแก้อยู่ท้ายเอกสาร
- Full suiteก่อนแก้layout: **237passed in16.41s** (`.venv/bin/python -m pytest backend/tests tools/test_ai_team_review.py -q`)

[ผลตรวจอิสระแบบJSON](../backend/reports/v2/reviews/independent_final_review.json) · [รายงานError Analysis](../backend/reports/v2/analysis/analysis_report_th.md) · [Model card](../backend/reports/v2/analysis/model_card_v2_analysis_th.md) · [คู่มือรันใน VS Code](v2-vscode-run-guide-th.md)

## ข้อจำกัดและงานถัดไป

ยังไม่มี untouched test และยังไม่ทราบ publication latency ของรายงานอุบัติเหตุแน่ชัด Weather coverageสัมพันธ์กับปีจึงไม่ใช่หลักฐานเชิงสาเหตุว่าฝนเพิ่มความเสี่ยง แบบจำลองยังทำนายจำนวนบันทึก MOT ของจังหวัด ไม่ใช่โอกาสเกิดอุบัติเหตุของคนหนึ่งหรือจุดถนน ต้องมีข้อมูลหน่วยถนน/exposureและการทดสอบอนาคตก่อนนำไปใช้กับเส้นทาง หน้าเว็บresponsiveและDashboardเป็นงานถัดไปตามที่ผู้ใช้กำหนด

## ผลตรวจ correction007a

แก้เฉพาะcell `nb12-16` สำหรับlayoutกราฟสองรูป: oldsha=`db933be1eeeeca9627fb55713dd6372d85d259b66f0455c62c8c65ee0db6fb15`, newsha=`21b22bb81af3a673c815d51d89bbb626955dbbfd0e3897f19b689012fcd03f9a` ทุกcellอื่นเหมือนเดิม ผลรันใหม่17.95วินาทีสำเร็จ12code cells ตรวจรูปใหม่แล้วชื่อวิธี/title/ข้อความแจ้งแกนไม่ได้เริ่ม0แสดงครบ ตารางCSV18ไฟล์เหมือนก่อนแก้และisolated replayทุกbyte; hash outputs36ไฟล์ผ่าน Testsที่เกี่ยวข้อง20passed in0.51s ไม่refitหรือเปลี่ยนwinner

ไฟล์analysisรอบแรกถูกย้ายเก็บใน `backend/reports/v2/attempts/analysis_001_layout_review/` โดยไม่แก้เนื้อหา pathในmanifestเดิมยังอ้างตำแหน่งตอนรัน ต้องแทนprefixด้วยarchiveเมื่อตรวจไฟล์ที่ย้าย ส่วนrow diagnosticsรอบแรกอยู่ในignored `backend/data/v2/analysis_attempts/analysis_001_layout_review/` เช่นเดียวกับmodel attemptแรก ไฟล์รายแถว/bundleของmodel attemptแรกอยู่ในignored `backend/data/v2/model_attempts/model_001_failed/`

Notebook11เปิดรันและสังเกตผลสำเร็จในVS Codeจริง Notebook12รอบแรกเริ่ม23:08:03หลังส่งคำสั่งผ่านUI แม้computer-useส่งerrorภายหลัง; ตรวจmanifestพบรันสำเร็จแล้วจึงไม่รันทับ การตรวจreplayและcorrectionใช้local CLI runnerเดียวกัน คู่มือระบุคำสั่งเพื่อให้ผู้ใช้รันซ้ำในVS Code Terminalได้ การควบคุมUIที่ล้มเหลวไม่ใช่หลักฐานว่าMLรันล้มเหลว
