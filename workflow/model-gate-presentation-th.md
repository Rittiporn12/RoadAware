# RoadAware — Model Gate สำหรับนำเสนอ

สถานะเอกสาร: ผลทดลอง016-002และCatalogตรวจรับแล้ว;21รันจริง61.36sและindependent127checksผ่าน แต่ยังไม่รับทั้งstageเพราะtest1ข้อและpresentation/controlข้อค้าง. Runtime/API/2026scoresยังไม่ได้ทำ ตัวเลขด้านล่างมาจากผลจริงที่ตรวจแล้ว ห้ามถือช่องที่ยังไม่เสร็จว่าเป็นผลผ่าน

## 1. Baseline และ Candidate Models

ทำนายค่าคาดหมายจำนวนรายการอุบัติเหตุที่ผ่านการคัดเลือกและเชื่อมกับถนนได้ต่อช่วงถนน×วัน หรือช่วงถนน×6ชั่วโมง ไม่ใช่จำนวนเหตุจริงทั้งหมด ไม่ใช่โอกาสชนต่อรถหรือคน Universeกำหนดจากgeometryก่อนดูผล:3,105ช่วงถนนDOHในพื้นที่ที่ศึกษา มี27,459รายการselectedปี2021–2025

Baselineครอบคลุมค่าเฉลี่ยรวม ค่าเฉลี่ยต่อกิโลเมตร/สายทาง ค่าเฉลี่ยช่วงถนนแบบshrinkage(k30/180/365) และกลุ่มweekday/month/recent90 โดยใช้ตัวหารจากปฏิทินtrainingเต็ม ไม่ใช่training sample. ตัวที่แข็งแรงที่สุดตามOOFคือsegment_mean_k365: (จำนวนtrainingของsegment +365×ค่าคาดหมายparentตามสายทาง/ความยาว)/(จำนวนtrainingcells+365). สายทางไม่เคยเห็นใช้global length-aware parent;parentอาจเป็น0เมื่อไม่มีtrainingrecords. Zero baselineเป็นตัวเปรียบเทียบเชิงวินิจฉัย ไม่เข้าเกณฑ์เลือก

Candidateสามกลุ่ม:Poisson regression(alpha1e-5/1e-4)เป็นความสัมพันธ์countแบบlog-linear;RandomForestใช้Poissoncriterionและการแบ่งกลุ่มแบบไม่เชิงเส้น;HistogramGradientBoostingใช้Poissonlossสร้างต้นไม้เพิ่มเพื่อแก้residual. ทั้งหมดใช้configที่ล็อกไว้ ไม่ค้นหาชุดใหญ่ใหม่

Coreใช้calendar/festival/seasonและroad geometry/routeตามfeatureallowlistที่ตรวจแล้ว Contextเพิ่มweatherที่มีข้อกำหนดavailabilityและAADTannualproxy. routed_contextใช้contextmodelเฉพาะเมื่อadditionalweather/AADTทุกค่าครบ มิฉะนั้นใช้coreของfamily/configเดียวกัน. ไม่มีeventcoordinates/target/accidentdescriptionsเป็นpredictors. AADTไม่ใช่livecongestion;historicalweatherไม่ใช่สภาพอากาศปัจจุบัน

## 2. Evaluation Metrics และเกณฑ์เลือก

- MeanPoissondeviance: เฉลี่ย2×[y log(y/μ)−y+μ]บนทุกcell,นิยามส่วนylogเป็น0เมื่อy=0. ใช้μอย่างน้อย1e-12เฉพาะในmetric ไม่เปลี่ยนprediction. ยิ่งต่ำยิ่งดี;ไม่ใช่accuracyร้อยละ
- MAE:เฉลี่ย|μ−y| หน่วยรายการต่อsegment-dayหรือsegment-6h. RMSE:รากของค่าเฉลี่ยerrorยกกำลังสอง หน่วยเดียวกัน ให้น้ำหนักerrorใหญ่กว่า
- Signedbias:เฉลี่ย(μ−y),ลบหมายถึงทำนายต่ำ. WAPE:ผลรวมabsoluteerror/ผลรวมy;กลุ่มที่ไม่มีactualrecordsไม่มีค่าที่นิยามได้
- รวมOOFแบบrow-weightedโดยใช้ผลรวมloss/จำนวนcells ไม่เฉลี่ยfoldเท่ากัน. Dailyและ6hมีhorizonและpopulationต่างกัน ห้ามใช้คะแนนข้ามหน่วยจัดอันดับ
- Fourexpandingfolds2022H1/H2,2023H1/H2;ฝึกจากปี2021ถึงcutoffก่อนfirstissue30วัน โดยเทียบtargetendเวลา18:00วันก่อนtarget. ไม่มีrandomtimesplit.30วันเป็นresearchassumption ไม่ได้พิสูจน์reportingcomplete
- เลือกstrongestnonzerobaselineและbesteligiblecandidateจากpooledOOFdeviance. Candidateผ่านเมื่อdevianceลดอย่างน้อย1%,MAEratioไม่เกิน1.02และdevianceชนะอย่างน้อย3/4folds. เลือกก่อนdiagnostics2024/25;ไม่เปลี่ยนผู้ชนะจาก2026

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

กราฟจริง016ที่ตรวจแล้วอยู่backend/rerun-spatial-model-016-002/reports/v3/spatial_experiments/figures/:oof_deviance_by_method.png,fold_deviance_candidate_vs_baseline.png,oof_calibration.png,spatial_transfer_deviance.png. PresentationPNG/SVGและgroupanalysisรอบ21อยู่backend/rerun-spatial-eval-017-001/reports/v3/spatial_evaluation/;ตัวเลขผ่าน127independentchecksแล้วแต่ภาพบางรูปยังต้องแก้titlelayoutจึงยังไม่รับpackage

2024/25เป็นpreviouslyseendiagnostics ไม่ใช่untouchedtest และcontextmaskเป็น0ทั้งหมด จึงประเมินselectedpolicyที่fallbackcoreทั้งช่วง. Spatialtransferเป็นheldoutnortheast410segmentsปี2023รวม483records;HGBcoredeviance0.034559daily/0.0106436h เทียบroute_length_rate0.035332/0.011240. เป็นunseen-sectionsdiagnosticหนึ่งพื้นที่ ไม่ใช่หลักฐานรองรับถนนใหม่ทุกประเภท

ปี2026แยกจากตารางนี้:downloadใหม่ถึง31ต.ค.แต่requestedwindowคือม.ค.–ก.ย. ไม่มีACC_CODEและยังพิสูจน์fullpopulationcompletenessไม่ได้. จะรายงานcoverage/lag/eligibilityและคะแนนเฉพาะscopeที่ตรวจสอบได้ ห้ามกรอก0ให้missingcells ห้ามใช้คะแนนปีนี้เปลี่ยนwinner

## 4. Error Analysis

ผลที่ตรวจแล้ว:ยอดOOFทำนายรวมdaily9,574.10และ6h9,446.02เทียบactual10,701 จึงต่ำกว่าจริง10.53%/11.73%. กราฟcalibrationแสดงว่ากลุ่มทำนายสูงสุดทำนายเกินโดยเฉลี่ย:dailymeanpred0.3963/actual0.2791;6h0.11875/0.09756 ทั้งนี้ต้องแสดงsupportของbinจาก21ก่อนใช้เป็นสไลด์สรุป

Baselineทำนายต่ำกว่าmetricfloorใน168,780dailycellsซึ่งมีpositive48cells;6h1,953,307cellsซึ่งมีpositive217cells. กลุ่มเหล่านี้คิดเป็นประมาณ75.00%/73.46%ของdeviancegainรวม. Candidateไม่ติดmetricfloor;ส่วนที่baselineทำนายเป็นบวกก็มีdevianceดีขึ้นแต่gainน้อยกว่า. บนactualzerocells HGBdevianceแย่ลงเล็กน้อย;ห้ามอ้างชนะทุกกลุ่ม

ผล21รอบ001คำนวณgroupsครบแล้วและtotalsผ่านindependentchecks. ตัวอย่างOOFdailyที่baselineมีdevianceดีกว่าHGB:

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

ยังรอ2026:ledgerก่อน/หลังตัดแยกเดือน/พื้นที่และscopeจริง ไม่สมมุติว่ามีผลแล้ว. ไม่มี2026modelscoreในรายงานนี้

## 5. เหตุผลเลือกโมเดล

เลือกHGB routed_contextเพราะผ่านเกณฑ์ล็อกทั้งสองหน่วยโดยไม่เปลี่ยนthresholdหลังเห็นคะแนน:devianceดีขึ้นตามเกณฑ์,MAEยังอยู่ในtolerance,ชนะทุกfold. มีfallbackcoreที่สอดคล้องกับการขาดcontextในruntime. ข้อเสียคือMAEไม่ได้ดีที่สุด,Yรวมยังต่ำและcalibrationยังไม่สมบูรณ์. RFมี6hRMSEต่ำกว่าเล็กน้อย;baselineมีMAEต่ำกว่าHGBทั้งสองหน่วย. Zero baselineมีMAEต่ำมากในข้อมูลsparseแต่ทำนายทุกอย่าง0และไม่ผ่านเกณฑ์deployment จึงไม่ใช่หลักฐานว่าไม่มีอุบัติเหตุ

ผลเกือบสามในสี่ของdeviancegainมาจากbaselinezero groups;รายงานตรงไปตรงมาโดยไม่เพิ่มpseudocountหรือเปลี่ยนเกณฑ์ย้อนหลัง. ขอบเขตที่ยังไม่รองรับให้APIตอบunsupported/unavailable ไม่สร้างprediction0ทดแทน. ยังไม่มีproduction/safetycertification

## ลำดับสไลด์และประเด็นพูด

1. ปัญหาและtarget: “เราทำนายจำนวนรายการที่ฐานข้อมูลคัดเลือกและเชื่อมถนนได้ ไม่ใช่โอกาสชนส่วนบุคคล”
2. ข้อมูล/coverage:3105segments/27459selectedrecordsและเวลาdaily/6h;แยกrawmissingออกจากverifiedzero
3. Baselinesและ3candidatefamilies:อธิบายcore/contextและfallback;แสดงเหตุผลที่baselineแข็งแรงจำเป็นในข้อมูลsparse
4. Evaluationgate:temporalOOF/30dayassumption/pooleddeviance/MAEtolerance/foldwins;2026ไม่ใช้เลือก
5. OOFresults:ตารางแยกdaily/6hพร้อมdeviancegainและMAEtradeoff;ไม่เรียกaccuracy
6. Erroranalysis:calibration/actualzeroและbaselinefloor,groupพื้นที่เวลาเทศกาลพร้อมsupportเมื่อ21ผ่าน
7. 2026:sourceversion/date/lag,ก่อนหลังคัด,scopeที่มีจริง,เทียบHGB/baselineบนkeysเดียวกัน;แสดงunknowncoverageชัด
8. เหตุผลเลือกและข้อจำกัด:HGBผ่านgateแต่ไม่ชนะทุกmetric/ทุกscope;ไม่claimuntouchedtest
9. Backenddemoและreadiness:history/predictionAPIตัวอย่างจริงเมื่อผ่านintegration,unsupported/unavailableและproductionfalse;ไม่มีfrontend/deploy
