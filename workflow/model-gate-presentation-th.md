# RoadAware — Model Gate สำหรับนำเสนอ

สถานะ12พฤศจิกายน2026: ตรวจรับ backendส่วนข้อมูล/ML/APIครบแล้ว พร้อมให้เริ่มFrontend/Dashboardภายใต้ขอบเขตวิจัย HTTP004ผ่าน73/73checks,finalbackend831passed/1conditional-skip ไม่มีการฝึก016-002ซ้ำ ไม่มีfrontend/deploy และproduction_ready=false

หลักฐานพร้อมใช้: [รายละเอียดโมเดล/ฟีเจอร์และ10สไลด์ OOF](../output/spatial-model-results/v3-evaluation-017-002/model_gate_presentation_th.md), [รายงาน runtime](../output/spatial-model-results/v3-serving-018-001/readiness_th.md), [รายงานปี2026](../output/spatial-model-results/v3-2026-diagnostics-023-002/report_2026_th.md) พร้อม CSV/PNG/SVG ของแต่ละรอบ ผลต้นทางทั้งหมดเก็บแยก ไม่เขียนทับ

## 1. Baseline และ Candidate Models

ทำนายค่าคาดหมายจำนวนรายการอุบัติเหตุที่ผ่านการคัดเลือกและเชื่อมกับถนนได้ต่อช่วงถนน×วัน หรือช่วงถนน×6ชั่วโมง ไม่ใช่จำนวนเหตุจริงทั้งหมด ไม่ใช่โอกาสชนต่อรถหรือคน Universeกำหนดจากgeometryก่อนดูผล:3,105ช่วงถนนDOHในพื้นที่ที่ศึกษา มี27,459รายการselectedปี2021–2025

Baselineครอบคลุมค่าเฉลี่ยรวม ค่าเฉลี่ยต่อกิโลเมตร/สายทาง ค่าเฉลี่ยช่วงถนนแบบshrinkage(k30/180/365) และกลุ่มweekday/month/recent90 โดยใช้ตัวหารจากปฏิทินtrainingเต็ม ไม่ใช่training sample. ตัวที่แข็งแรงที่สุดตามOOFคือsegment_mean_k365: (จำนวนtrainingของsegment +365×ค่าคาดหมายparentตามสายทาง/ความยาว)/(จำนวนtrainingcells+365). สายทางไม่เคยเห็นใช้global length-aware parent;parentอาจเป็น0เมื่อไม่มีtrainingrecords. Zero baselineเป็นตัวเปรียบเทียบเชิงวินิจฉัย ไม่เข้าเกณฑ์เลือก

Candidateสามกลุ่ม:Poisson regression(alpha1e-5/1e-4)เป็นความสัมพันธ์countแบบlog-linear;RandomForestใช้Poissoncriterionและการแบ่งกลุ่มแบบไม่เชิงเส้น;HistogramGradientBoostingใช้Poissonlossสร้างต้นไม้เพิ่มเพื่อแก้residual. ทั้งหมดใช้configที่ล็อกไว้ ไม่ค้นหาชุดใหญ่ใหม่

Coreใช้calendar/festival/seasonและroad geometry/routeตามfeatureallowlistที่ตรวจแล้ว Contextเพิ่มweatherที่มีข้อกำหนดavailabilityและAADTannualproxy. routed_contextใช้contextmodelเฉพาะเมื่อadditionalweather/AADTทุกค่าครบ มิฉะนั้นใช้coreของfamily/configเดียวกัน. ไม่มีeventcoordinates/target/accidentdescriptionsเป็นpredictors. AADTไม่ใช่livecongestion;historicalweatherไม่ใช่สภาพอากาศปัจจุบัน

Core มี33ฟีเจอร์รายวัน/34ฟีเจอร์แบบ6ชั่วโมง: รหัสสายทาง, ตำแหน่งกึ่งกลางและรูปทรงช่วงถนน, ความยาว/ทิศทาง/ความคดเคี้ยว, วันในสัปดาห์/เดือน/วันในเดือน, weekend, doy sin/cos, ระยะและช่วงก่อน–หลังปีใหม่/สงกรานต์, ฤดู และ bank_holiday_asof;6ชั่วโมงเพิ่ม time_block. Context เพิ่ม5/7ฟีเจอร์ ได้แก่ฝน/อุณหภูมิที่ใช้ได้ตามas-of และ AADT3ค่า รายชื่อคอลัมน์/parameters/preprocessingครบอยู่ในรายละเอียดที่ลิงก์ด้านบน HGBรับNaNตามวิธีเดิม;ไม่ลบคอลัมน์เพื่อให้ปี2026ทำนายได้

## 2. Evaluation Metrics และเกณฑ์เลือก

- MeanPoissondeviance: เฉลี่ย2×[y log(y/μ)−y+μ]บนทุกcell,นิยามส่วนylogเป็น0เมื่อy=0. ใช้μอย่างน้อย1e-12เฉพาะในmetric ไม่เปลี่ยนprediction. ยิ่งต่ำยิ่งดี;ไม่ใช่accuracyร้อยละ
- MAE:เฉลี่ย|μ−y| หน่วยรายการต่อsegment-dayหรือsegment-6h. RMSE:รากของค่าเฉลี่ยerrorยกกำลังสอง หน่วยเดียวกัน ให้น้ำหนักerrorใหญ่กว่า
- Signedbias:เฉลี่ย(μ−y),ลบหมายถึงทำนายต่ำ. WAPE:ผลรวมabsoluteerror/ผลรวมy;กลุ่มที่ไม่มีactualrecordsไม่มีค่าที่นิยามได้
- รวมOOFแบบrow-weightedโดยใช้ผลรวมloss/จำนวนcells ไม่เฉลี่ยfoldเท่ากัน. Dailyและ6hมีhorizonและpopulationต่างกัน ห้ามใช้คะแนนข้ามหน่วยจัดอันดับ
- Fourexpandingfolds2022H1/H2,2023H1/H2;ฝึกจากปี2021ถึงcutoffก่อนfirstissue30วัน โดยเทียบtargetendเวลา18:00วันก่อนtarget. ไม่มีrandomtimesplit.30วันเป็นresearchassumption ไม่ได้พิสูจน์reportingcomplete
- เลือกstrongestnonzerobaselineและbesteligiblecandidateจากpooledOOFdeviance. Candidateผ่านเมื่อdevianceลดอย่างน้อย1%,MAEratioไม่เกิน1.02และdevianceชนะอย่างน้อย3/4folds. เลือกก่อนdiagnostics2024/25;ไม่เปลี่ยนผู้ชนะจาก2026

ปี2026แสดงทั้ง raw deviance และ numerical-floor audit ตามสูตรเดิม1e-12 หาก y>0 แต่λ=0 ค่า raw deviance มีlimitเป็น+∞: JSONใช้nullพร้อมสถานะ infinite_due_zero_predictionและจำนวนแถว ไม่ใช่ข้อมูลหายหรือคะแนน0 คะแนนทั้งสองแบบคำนวณจากค่าทำนายเดิม;ไม่มีการใช้ปี2026เปลี่ยนเกณฑ์หรือเลือกโมเดลใหม่

## 3. Experiment Results

OOF2022–2023ทุกcell:daily2,266,650cellsและ6h9,066,600cells โดยทั้งสองหน่วยรวม10,701selectedrecords

| หน่วย | วิธี | Mean Poisson deviance | MAE | RMSE |
|---|---|---:|---:|---:|
| Daily | Strong baseline k365 |0.040956|0.008601|0.071517|
| Daily | Poisson routed |0.041921|0.008793|0.071887|
| Daily | RF routed |0.040064|0.008757|0.071496|
| Daily | HGB routed |0.039898|0.008662|0.071496|
| 6h | Strong baseline k365 |0.014299|0.002194|0.035226|
| 6h | Poisson routed |0.013787|0.002280|0.035281|
| 6h | RF routed |0.013167|0.002224|0.035219|
| 6h | HGB routed |0.013133|0.002203|0.035222|

HGBลดdeviance2.583%daily/8.152%6h,แต่MAEเพิ่ม0.710%/0.406%,ชนะ4/4folds. Paired7daybootstrap500resamplesให้ช่วง95%ของgain1.477–3.712%dailyและ6.755–9.552%6h;เป็นexploratorypostselectionไม่ใช่confirmatorysignificance

กราฟจริง016ที่ตรวจแล้วอยู่backend/rerun-spatial-model-016-002/reports/v3/spatial_experiments/figures/:oof_deviance_by_method.png,fold_deviance_candidate_vs_baseline.png,oof_calibration.png,spatial_transfer_deviance.png. PresentationPNG/SVGและgroupanalysisที่ตรวจรับอยู่output/spatial-model-results/v3-evaluation-017-002/;independent135checksผ่าน,metrics/thresholds/capture/floorเหมือน001ทุกbyte. กราฟgroupsแนวตั้งเป็นภาพรายละเอียดสำหรับappendix/SVG ส่วนfold/calibration/captureใช้เป็นภาพสไลด์ได้

2024/25เป็นpreviouslyseendiagnostics ไม่ใช่untouchedtest และcontextmaskเป็น0ทั้งหมด จึงประเมินselectedpolicyที่fallbackcoreทั้งช่วง. Spatialtransferเป็นheldoutnortheast410segmentsปี2023รวม483records;HGBcoredeviance0.034559daily/0.0106436h เทียบroute_length_rate0.035332/0.011240. เป็นunseen-sectionsdiagnosticหนึ่งพื้นที่ ไม่ใช่หลักฐานรองรับถนนใหม่ทุกประเภท

ตารางช่วงที่เคยเห็นแล้ว แยกจาก OOF ที่ใช้เลือกโมเดลและ diagnostic ปี2026: คัดจาก `scope=diag, dimension=period` ใน [metrics_by_group.csv](../output/spatial-model-results/v3-evaluation-017-002/metrics_by_group.csv) ไม่ใช้เลือกโมเดลใหม่

| ปี/หน่วย | cells ต่อวิธี | actual records | deviance HGB | deviance baseline | MAE HGB | MAE baseline |
|---|---:|---:|---:|---:|---:|---:|
| 2024 Daily |1,136,430|6,015|0.043462|0.044229|0.009537|0.009383|
| 2025 Daily |1,133,325|6,231|0.046263|0.047885|0.009693|0.009592|
| 2024 6h |4,545,720|6,015|0.014372|0.015493|0.002428|0.002409|
| 2025 6h |4,533,300|6,231|0.015223|0.016978|0.002468|0.002460|

HGBมีdevianceต่ำกว่า แต่baselineมีMAEต่ำกว่าทั้งสี่แถว เป็นข้อแลกเปลี่ยนตามเกณฑ์เดิม ไม่ใช่การชนะทุกmetric

### ปี2026: ขอบเขตข้อมูลและผลที่ตรวจสอบได้

Snapshotจาก [URLทางการของ MOT](https://datagov.mot.go.th/dataset/7e077ffd-dc4f-4dc6-a71c-0813726f3c12/resource/4625b7aa-99a4-4dfb-9a0f-6402814d0f2c/download/accident2026.csv) ตาม metadata แก้ล่าสุด2พ.ย.2026 มี18,448แถว วันที่เกิดเหตุถึง31ต.ค.;หน้าต่างประเมินกำหนด1ม.ค.–30ก.ย.ก่อนดูคะแนน เหลือ17,272แถวในช่วงนั้น ไม่มีACC_CODEจึงยืนยันเอกลักษณ์เหตุการณ์จริงไม่ได้ ตัดเฉพาะ exact full-row duplicates และกติกาคุณภาพ/ขอบเขต/การเชื่อมถนนที่ลงทะเบียนไว้

| เดือน2026 | ก่อนตัดในsnapshot | ผ่านกติกา | ตัดออก |
|---|---:|---:|---:|
| ม.ค. |2661|595|2066|
| ก.พ. |1933|501|1432|
| มี.ค. |1844|513|1331|
| เม.ย. |2733|642|2091|
| พ.ค. |1756|431|1325|
| มิ.ย. |1683|435|1248|
| ก.ค. |1663|409|1254|
| ส.ค. |1564|395|1169|
| ก.ย. |1435|415|1020|
| รวมม.ค.–ก.ย. |17272|4336|12936|

นอกหน้าต่างมีตุลาคม1,176แถว เหตุผล exclusive อื่นรวมม.ค.–ก.ย.: exactduplicate22,หน่วยงานนอกDOH1086,สายทางไม่ยืนยัน/ไม่อยู่snapshot7344,พิกัดหรือจังหวัดไม่ผ่าน250,นอกพื้นที่4052,ไกลกว่า50ม.96,ambiguous43,ไม่มีacceptedsegment43;invaliddate/time0 ทุกแถวมีเหตุผลเดียวและมีmulti-issue ledger แยก ตรวจรายจังหวัด/หน่วยงานได้ใน [ชุดรายงาน2026](../output/spatial-model-results/v3-2026-diagnostics-023-002/ledger_by_province.csv)

เหลือ4,336 raw observed records วันที่1ม.ค.–30ก.ย. ใน1,128ช่วงถนน/19จังหวัดตามที่บันทึกไว้ สร้าง4,116positive segment-day cells และ4,232positive segment-6h cells **ไม่เติม0ให้cellที่ไม่มีบันทึก** ทั้งHGBและbaselineใช้key/yเดียวกัน

| หน่วย | วิธี | positive cells | actual records | pred total | raw deviance | floor audit | MAE |
|---|---|---:|---:|---:|---:|---:|---:|
| Daily | HGBที่เลือก |4116|4336|153.575|7.197724|7.197724|1.016138|
| Daily | baseline k365 |4116|4336|144.022|+∞ (zero50cells)|8.011|1.018459|
| 6h | HGBที่เลือก |4232|4336|41.412|9.763288|9.763288|1.014789|
| 6h | baseline k365 |4232|4336|43.823|+∞ (zero175cells)|11.51|1.014220|

ตารางนี้มี outcome-conditioned selection bias เพราะเลือกเฉพาะcellที่y≥1 จึงไม่ใช้แทน full-population accuracy/annual calibration และห้ามเทียบระดับคะแนนกับOOFโดยตรง ยอดpredต่ำกว่ายอดจริงบนcohortนี้ไม่ใช่หลักฐานว่าโมเดลพลาดเหตุจริงทั้งประชากรในสัดส่วนเดียวกัน ปี2026เคยมีdataauditในโครงการ จึงไม่ใช่strictuntouchedtest

ความครบถ้วนยังไม่ยืนยันทุกเดือน:reportdates parseไม่ได้75แถว;ตัวอย่างม.ค./ก.พ./ก.ค.มีlagเกิน30วัน52.71%/51.46%/51.05%ของแถวที่lagทราบ ส่วนก.ย.median8วัน/P90=35วัน ถูกright-truncationด้วยsnapshot การอัปเดต2พ.ย.ไม่ได้พิสูจน์ว่ากันยายนครบ ค่าhashในCKANไม่ตรงกับMD5ไฟล์และmetadataไม่ระบุalgorithm จึงยังไม่ยืนยันproviderchecksum;SHA-256ของsnapshotที่เก็บตรงpinตลอดการตรวจ

ภาพสำหรับสไลด์: [ก่อน–หลังคัดรายเดือน](../output/spatial-model-results/v3-2026-diagnostics-023-002/fig_ledger_by_month.png), [รายงานล่าช้า](../output/spatial-model-results/v3-2026-diagnostics-023-002/fig_report_lag_by_month.png), [ผลรายวัน](../output/spatial-model-results/v3-2026-diagnostics-023-002/fig_metrics_by_month_daily.png), [ผล6ชั่วโมง](../output/spatial-model-results/v3-2026-diagnostics-023-002/fig_metrics_by_month_6h.png) มีSVGข้างไฟล์สำหรับขยาย

## 4. Error Analysis

ผลที่ตรวจแล้ว:ยอดOOFทำนายรวมdaily9,574.10และ6h9,446.02เทียบactual10,701 จึงต่ำกว่าจริง10.53%/11.73% ใช้binเดียวกับกราฟcalibrationของ21โดยไม่ปนรูปแบบbinอื่น:binquantileสูงสุดdailyมี2,269cells/pred399.465/actual428records;6hมี9,067cells/pred408.657/actual495records ทั้งคู่ยังทำนายต่ำ ส่วนbinช่วงกลางทำนายเกินได้ เช่นdailyช่วงλ0.004750..0.008909มี226,665cells/pred1450.988/actual1411records และ6hช่วงλ0.001175..0.002153มี906,664cells/pred1418.292/actual1400records จึงไม่กล่าวว่าbiasเหมือนกันทุกช่วง ดู [ข้อมูลbinที่ใช้ในกราฟ](../output/spatial-model-results/v3-evaluation-017-002/figure_calibration.csv)

Baselineทำนายต่ำกว่าmetricfloorใน168,780dailycellsซึ่งมีpositive48cells;6h1,953,307cellsซึ่งมีpositive217cells. กลุ่มเหล่านี้คิดเป็นประมาณ75.00%/73.46%ของdeviancegainรวม. Candidateไม่ติดmetricfloor;ส่วนที่baselineทำนายเป็นบวกก็มีdevianceดีขึ้นแต่gainน้อยกว่า. บนactualzerocells HGBdevianceแย่ลงเล็กน้อย;ห้ามอ้างชนะทุกกลุ่ม

ผล21ที่รับรอบ002คำนวณgroupsครบแล้วและtotalsผ่านindependentchecks. ตัวอย่างOOFdailyที่baselineมีdevianceดีกว่าHGB:

| กลุ่ม | จำนวน cells | จำนวน selected records | HGB deviance gain เทียบ baseline |
|---|---:|---:|---:|
| สุพรรณบุรี (province_code72) |13,870|34|−3.5754%|
| ชลบุรี (20) |10,220|29|−1.5434%|
| นครสวรรค์ (60) |32,120|127|−0.6320%|
| ฉะเชิงเทรา (24) |163,520|661|−0.3536%|
| 4–7วันหลังสงกรานต์ |24,840|103|−1.1829%|
| 4–7วันหลังปีใหม่ |24,840|116|−0.6186%|

Provinceเป็นจังหวัดของจุดกึ่งกลางsegmentตามgeometryปัจจุบัน ไม่ใช่การจัดจังหวัดใหม่จากเหตุการณ์แต่ละรายการ. เป็นpostselectiondescriptivegroups มีsupportsน้อยบางกลุ่ม ไม่ใช้เปลี่ยนwinnerหรือthresholdsย้อนหลัง. ทั้งdailyและ6hบนactualzerocells HGBdevianceแย่ลงเล็กน้อย

Captureที่งบความยาวถนนเท่ากันต้องแยกจากdeviancegate. ที่5%road-kmHGBจับselectedrecords50.16%daily/50.43%6h เทียบbaseline49.79%/48.31%. แต่dailybaselineดีกว่าที่1%,2%,10%,20%road-km;6hbaselineดีกว่าที่1%,2%. เป็นการจัดอันดับที่ไม่ชนะทุกงบ. Boundarysegmentถูกนับrecordsตามlengthfractionซึ่งเป็นสมมติฐาน ไม่ใช่ตำแหน่งเหตุจริงในเศษsegment

### Error analysis ปี2026 (แยกจากOOF)

ทุกกลุ่มที่support≥20positivecellsมีpred/actual<1:114กลุ่มรายวันและ117กลุ่ม6ชั่วโมงต่อวิธี ไม่มีกลุ่มoverpredictionในcohortนี้ อันดับที่ratioสูงที่สุดก็ยังทำนายต่ำกว่าจริง ห้ามเรียกว่าoverprediction กลุ่มเหล่านี้ซ้อนกันระหว่างจังหวัด/เดือน/เทศกาล จึงห้ามบวกจำนวนกลุ่มเป็นจำนวนตัวอย่างอิสระ

| กลุ่มปี2026ที่baselineมีMAEต่ำกว่า | cells | raw records | MAE HGB | MAE baseline |
|---|---:|---:|---:|---:|
| Daily ฉะเชิงเทรา |280|291|1.009710|1.007833|
| Daily สุพรรณบุรี |23|23|0.996579|0.995337|
| 6h สมุทรปราการ |397|411|1.019055|1.015345|
| 6h กรุงเทพมหานคร |1513|1565|1.016659|1.016218|

ช่วงวิเคราะห์ปีใหม่1–4ม.ค.มี155records(145daily/151six-hourcells),สงกรานต์11–17เม.ย.มี239records(229/235cells);เป็นหน้าต่างวิเคราะห์ที่กำหนดก่อนรัน ไม่ใช่การรับรองวันหยุดราชการ จังหวัดของcellปี2026ใช้modeของจังหวัดที่บันทึกในrecord(เสมอใช้ลำดับตัวอักษร) ต่างจากจังหวัดกึ่งกลางsegmentในOOF ไม่มีcellข้ามหลายจังหวัดในชุดนี้ ตารางครบทุกกลุ่มอยู่ใน [metrics2026](../output/spatial-model-results/v3-2026-diagnostics-023-002/metrics.csv) และ [comparison2026](../output/spatial-model-results/v3-2026-diagnostics-023-002/method_comparison.csv)

## 5. เหตุผลเลือกโมเดล

เลือกHGB routed_contextเพราะผ่านเกณฑ์ล็อกทั้งสองหน่วยโดยไม่เปลี่ยนthresholdหลังเห็นคะแนน:devianceดีขึ้นตามเกณฑ์,MAEยังอยู่ในtolerance,ชนะทุกfold. มีfallbackcoreที่สอดคล้องกับการขาดcontextในruntime. ข้อเสียคือMAEไม่ได้ดีที่สุด,Yรวมยังต่ำและcalibrationยังไม่สมบูรณ์. RFมี6hRMSEต่ำกว่าเล็กน้อย;baselineมีMAEต่ำกว่าHGBทั้งสองหน่วย. Zero baselineมีMAEต่ำมากในข้อมูลsparseแต่ทำนายทุกอย่าง0และไม่อยู่ในวิธีที่มีสิทธิ์ถูกเลือกตามเกณฑ์เดิม จึงไม่ใช่หลักฐานว่าไม่มีอุบัติเหตุ

ผลเกือบสามในสี่ของdeviancegainมาจากbaselinezero groups;รายงานตรงไปตรงมาโดยไม่เพิ่มpseudocountหรือเปลี่ยนเกณฑ์ย้อนหลัง. ขอบเขตที่ยังไม่รองรับให้APIตอบunsupported/unavailable ไม่สร้างprediction0ทดแทน. ยังไม่มีproduction/safetycertification

### Model Gate และความพร้อมของ backend

**รับงานส่วนวิจัยและ runtime ได้**:Catalogผ่าน67independentchecks;21ผ่าน135checks;22ผ่าน34checksและเทียบค่าทำนายกับผลเดิมทุกค่าได้maxerror0 บน2,269,755daily/9,079,020six-hourcells ทั้งselectedและbaseline;23ผ่าน36checksรวมsource/lag/ledger/metricsทุกกลุ่ม ชุดbackendล่าสุดก่อนAPI765testsผ่าน41.51s

Runtimeใช้benchmarkเดิมออกณ31ธ.ค.2023เวลา18:00 ใช้traininglabelsถึง1ธ.ค.2023เวลา18:00 ไม่มีextendedrefitและไม่มีOOFfoldmodelsให้replay รองรับtarget2024–2027สำหรับqualifiedDOH3,105segments หลัง2025เป็นresearchscenario;bankcalendarunknownคงmissingและcontextไม่ครบใช้coreตามกฎเดิม การตรงกับsaved2024/25เป็นnumericalparityบนปีที่เคยเห็นแล้ว ไม่ใช่การรับรองอนาคต

ตรวจรับAPIแล้ว:liveHTTP004ผ่าน73/73checksใน8.69s(startup5.14s) ครบactual13province/14history/22selected+baselineทั้งdailyและ6h128rowsต่อbatchตรงsavedทุกค่า,geometry3105IDs,unsupported/CORS/strictJSON,คะแนนOOF/seen32แถวตรงCSVและOpenAPIexamplesจริง กรณีcorrupt-sourceตอบhealth200/ready503/prediction503ไม่มีfakezero;78ไฟล์รวมchosenbundles/rootmanagerlockตรงtrustedpinsและไม่เปลี่ยน ตัวนับหมวดรองรับไฟล์เดียวในหลายchainโดยไม่ลดเกณฑ์ พร้อมregressionกรณีหมวดขาดและhashขัดแย้ง

Finalbackendรันพร้อมactualflag831passed/1skipped48.21s ข้อskipคือtestก่อนเติมmanagerpinsซึ่งไม่เข้าเงื่อนไขเมื่อpinsเติมแล้ว ไม่ได้ข้ามactualruntime. Targeted84passed/2conditional-skips0.86s ดู [acceptedrecordและsource/config/model-chainhashes](api/accepted-runtime-v3.json) และ [หลักฐานHTTP/OpenAPI/ตัวอย่างจริง](../output/spatial-model-results/v3-api-019-004/README_th.md)

**Backendพร้อมเริ่มFrontend/Dashboardแล้ว** คำสั่งเปิด `.venv/bin/python backend/scripts/run_api_server.py` (localhost:8000,หยุดCtrl+C) และ [runbookพร้อมตัวอย่างcurl](api/backend-api-runbook-v3-th.md) / [API contract](api/frontend-integration-contract-v3.md). เครื่องใหม่ต้องกู้ignoredartifactsที่ตรงpinsก่อน ยังไม่มีfrontend/deploy/authหรือproductionacceptance ขอบเขตที่ยังใช้งานไม่ได้คือถนนนอก3105segments/targetนอก2024–2027/ประวัติ2026/liveweatherและfullpopulation2026evaluation;APIตอบunsupported/unavailableหรือแสดงcorefallbackตามกรณี ไม่สร้างค่าทดแทน

### ลำดับสไลด์และประเด็นพูด

1. ปัญหาและtarget: “เราทำนายจำนวนรายการที่ฐานข้อมูลคัดเลือกและเชื่อมถนนได้ ไม่ใช่โอกาสชนส่วนบุคคล”
2. ข้อมูล/coverage:3105segments/27459selectedrecordsและเวลาdaily/6h;แยกrawmissingออกจากverifiedzero
3. Baselinesและ3candidatefamilies:อธิบายcore/contextและfallback;แสดงเหตุผลที่baselineแข็งแรงจำเป็นในข้อมูลsparse
4. Evaluationgate:temporalOOF/30dayassumption/pooleddeviance/MAEtolerance/foldwins;2026ไม่ใช้เลือก
5. OOFresults:ตารางแยกdaily/6hพร้อมdeviancegainและMAEtradeoff;ไม่เรียกaccuracy
6. ErroranalysisOOF:calibration/actualzeroและbaselinefloor,พื้นที่/ช่วงหลังเทศกาลพร้อมcells/recordsจากตารางหัวข้อ4 ภาพ [calibration](../output/spatial-model-results/v3-evaluation-017-002/figures/calibration.png) และ [floor](../output/spatial-model-results/v3-evaluation-017-002/figures/floor_audit.png). พูดว่า “devianceดีขึ้นแต่ผลส่วนใหญ่เกี่ยวกับbaselinezeroและไม่ชนะทุกกลุ่ม”
7. Capture/สี:ใช้ภาพ [capture](../output/spatial-model-results/v3-evaluation-017-002/figures/capture_curve.png) แสดงงบroad-kmเท่ากัน พูดว่า “สีเป็นอันดับdensityสัมพัทธ์ ไม่ใช่โอกาสชน และสีต่ำไม่เท่ากับปลอดภัย”
8. 2024/25และruntime:ตารางparitymaxerror0/ทั้งสองหน่วย,benchmarkversion/cutoffชัด พูดว่า “ผลทำนายตรงของเดิม แต่ปีนี้เคยเห็นแล้วและใช้coreทั้งหมด จึงไม่ใช่futurevalidation”
9. ข้อมูล2026:ตารางก่อน–หลังคัด9เดือนและภาพledger/lag พูดว่า “17,272รายการเหลือ4,336ที่เชื่อมได้ในขอบเขต19จังหวัด ความครบถ้วน/providerchecksumยังไม่ยืนยัน;missingไม่เป็นzero”
10. ผล2026:ตาราง4แถวแยกdaily/6h+ภาพmonthly MAE พูดว่า “นี่คือpositive-cell diagnostic;baseline6hMAEดีกว่าเล็กน้อย ส่วนrawdeviancebaselineเป็นอนันต์เพราะทำนาย0 เราเปิดเผยทั้งrawและfloor auditโดยไม่เลือกโมเดลใหม่”
11. เหตุผลเลือกและข้อจำกัด:HGBผ่านOOFgateทั้งสองหน่วย แต่MAE/capture/บางพื้นที่baselineเหมาะกว่า พูดว่า “ใช้HGBตามเกณฑ์เดิมสำหรับbackendวิจัย ยังไม่รับรองproductionหรือความเสี่ยงรายบุคคล”
12. Backenddemo/readiness:ใช้history→geometryID→prediction→unsupportedcaseตามrunbookจริง แสดงmodel/datahashและproduction_ready=false;ไม่มีfrontend/deploy พูดว่า “Backendวิจัยตรวจรับแล้ว HTTP73/73และ831testsผ่าน พร้อมให้ทำFrontend/Dashboard โดยต้องแสดงขอบเขตข้อมูลและข้อจำกัดทุกครั้ง”
