# ผลตรวจรับขั้น Model ครบชุด — 10 พฤศจิกายน 2569

สถานะ ACCEPTED สำหรับงานวิจัยย้อนหลัง Baseline/Candidate Models, Evaluation Metrics, Experiment Results, Error Analysis และเหตุผลการเลือกโมเดล ไม่ใช่การรับรอง forecast รายเส้นทางหรือ production

Claudeเขียนโค้ด Notebook06–08/runner/tests; Codexตรวจdiffและรันอิสระทั้งหมด อ่านรายงานworkerสุดท้าย `.ai-team/runs/20261110-074927-49289/result.json` แล้ว รายการที่workerยังระบุว่าค้างในรายงานถูกดำเนินการต่อโดยCodexตามหลักฐานด้านล่าง

## การตรวจที่รันจริง

- `.venv/bin/python -m pytest backend/tests -q`: **143 passed, 0 failed ใน8.36วินาที** (Data Foundation54 + Model89กรณี รวม parametrization)
- หลังถ่ายโอนคำสั่งแก้ของClaudeตามต้นฉบับ: `--stage analysis --timeout 900` รัน07/08ผ่านใน8.54/4.86วินาที (ดูrun manifestสำหรับเวลาจริงแต่ละเซลล์)
- รันใหม่ครบชุดด้วย `.venv/bin/python backend/scripts/run_model_notebooks.py --stage all --output-dir /private/tmp/roadaware-model-final-rerun-20261110 --timeout 900`:06ผ่าน42.63วินาที,07ผ่าน8.11วินาที,08ผ่าน6.16วินาที ทุกไฟล์statusok/fresh kernel
- เทียบ30CSV/524คอลัมน์ รวมOOF/diagnostic/error-analysis predictions และตารางคะแนน:ค่าตัวเลขตรงภายในrtol=atol1e-12; ความต่างabsoluteสูงสุด2.27e-13; keys/ข้อความ/nullpatternและตัวเลือกตรงกัน
- choice_sha256ตรงทุกค่า `4781bb5adcf649b0ff8e5cd278067a10d80cd1bd569cea5c39dc336bf7ffb30e`;decisionตัวเลขเทียบด้วยtoleranceเพราะRFบวกผลขนานต่างบิตสุดท้ายได้ จึงไม่คาดว่าhashของfloatทุกค่าเหมือนกันข้ามrun
- คำนวณอิสระด้วยsklearnครบ22คู่ของวิธี/ปีและ618กลุ่มerror analysisตรง1e-12 ตรวจจำนวนแถวและtargetsupportตรงกัน
- ตรวจhashของแหล่งข้อมูล/รายงานเดิม33ไฟล์ไม่เปลี่ยน;06โมเดลและlockไม่เปลี่ยนตลอดanalysis;07ไฟล์ไม่เปลี่ยนระหว่าง08 (07จะสร้างruntimeใหม่เมื่อถูกเรียกรันก่อน08ตามปกติ)
- ตรวจartifact/source/bundlehashทั้งหมดและโมเดลโหลดกลับในprocessใหม่;ภาพprovince scatter,calibration,cleaning-regime shiftอ่านได้ ป้ายกราฟที่ซ้อนแก้แล้ว

## ข้อค้นพบและคำตอบการเลือกโมเดล

เลือก **PoissonRegressor alpha0.0001** จากprimarymetric pooled OOF Poisson deviance0.937128 (Baselineรายจังหวัด1.112497,RF1.071341,HGB0.974299) ตามprotocolที่บันทึกก่อนฝึก ผ่านgateทั้ง4เกณฑ์/4fold โดยbootstrapผลต่างdeviance95%ประมาณ[-0.2353,-0.0927] เป็นexploratoryไม่ปรับสำหรับการเลือกหลายโมเดล

HGB120iterationsมีMAE/RMSEดีกว่าPoissonในสามconfigurationที่เลือกจากแต่ละตระกูลตามprimarymetric;หากดูทุก7configuration HGB160มีMAEต่ำสุด ข้อเท็จจริงทั้งสองแสดงแยกชัดในmodelcard ไม่เปลี่ยนselectionย้อนหลัง

แต่ปี2024/2025 **ทั้งสามfamilybestแพ้BaselineรายจังหวัดในPoisson deviance** จึงยังไม่นำPoissonหรือHGBไปใช้งานจริง แม้PoissonชนะOOF พบcohort shiftสอดคล้องกับการกักกันวันที่slash:Trainต้นเดือนmean0.1719เทียบปลายเดือน0.6864 ขณะที่ปีหลังทั้งสองกลุ่มประมาณ0.77–0.79;Trainต้นเดือนที่มีเหตุ1168แถวมีday==monthทั้งหมด เป็นข้อสังเกตselectionbiasไม่ใช่เหตุเชิงสาเหตุ

## ขอบเขตและงานถัดไป

`production_enabled=false`, `final_model_readiness=BLOCKED`, deploymentwithhold คะแนนเฉพาะreportedจังหวัด–วันที่ผ่านofflinequalityfilter;ปี2024ไม่มีeligibleQ4,ปี2025เคยดูแล้ว,ไม่มีuntouchedtest,ไม่ใช้labels2026 ปัจจุบันไม่มีweather/traffic/festival/routefeaturesหรือpersonalcrashprobability

ต้องยืนยันรูปแบบวันที่และเวลาข้อมูลพร้อมใช้กับต้นทาง ตรวจprovince mapping/หน่วยสายทาง และออกแบบprospectivetestที่ยังไม่เคยเห็นก่อนทดลองรุ่นถัดไป แผนDashboard/DataVisualization/frontendมือถือยังคงบันทึกไว้ ไม่มีการสร้างUI/API/deployในขั้นนี้

เปิดnotebooksในVSCodeเลือกroot`.venv`แล้วRunAllตาม01→08ได้;การตรวจอัตโนมัติครั้งนี้ใช้nbclientกับlocalPythonkernels ไม่ได้ยืนยันการกดRunAllผ่านVSCodeUI จึงไม่อ้างว่าได้ทดสอบUI

## การถ่ายโอนโค้ดจากworker

เครื่องมือEditไม่รองรับ.ipynbและReadติดขนาดไฟล์ Codexจึงถ่ายโอน06.continuationของClaudeแบบตรงต้นฉบับ และใช้4failedEditpayloads+8JSONpatchesที่Claudeเขียนกับ08โดยไม่เขียนlogicMLเอง บันทึกต้นฉบับและtimelineอยู่.ai-team (local/ignored) จากนั้นรันตรวจใหม่ทั้งหมด รายงาน/ป้ายกราฟ/วันที่Trainactualแก้ครบก่อนตรวจรับ

## จุดเปิดตรวจ

- [Model Card ภาษาไทย](../backend/reports/models/model_card_th.md)
- [สรุปการตัดสินใจ JSON](../backend/reports/models/model_decision_summary.json)
- [หลักฐานตรวจอิสระรอบสุดท้าย](../backend/reports/models/independent_final_review.json)
- [Notebook08พร้อมผลรัน](../backend/notebooks/08_error_analysis_model_selection.ipynb)
- [ชุดทดสอบ](../backend/tests/test_model_notebooks.py)

ไฟล์รายแถวและbundlesอยู่backend/data/modelซึ่งignoreจากGit สามารถสร้างใหม่จากsnapshotและnotebooks;Gitเก็บsource/aggregateevidence/รูป/configครบ
