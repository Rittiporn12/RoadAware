# ขอบเขตส่งมอบรอบ 11 พฤศจิกายน 2026

ผู้ใช้อนุญาตปิด backend ข้อมูล/โมเดล/Catalog/API พร้อมรายงาน Model Gate ภาษาไทยและลำดับสไลด์ ไม่ทำ frontend/deploy ไม่เพิ่มโมเดลหรือจูนใหม่ Claude เขียน/แก้โค้ดทั้งหมดผ่าน tools/ai_team.py ครั้งละ worker; Codex วางแผน ตรวจ diff รันทดสอบและรับงาน

## ลำดับงานและหลักฐาน

1. 016-002 รับผลวิจัยแล้ว: .ai-team/references/016-002-independent-review.json, correction run20261111-174328-25998 review pass. ใช้ arrays/bundles เดิม;ไม่ฝึกซ้ำ ไม่มี serving/production acceptance
2. Catalog020/020a/020bตรวจรับแล้ว:actual0037.98s/18checks/61querycontrols,independent67checks,50targetedtests/642fullbackendtests. ภาพจริง2รูปตรวจแล้ว;manifest18report6datahashesตรง,669protectedsnapshotไม่เปลี่ยน. Pins workflow/catalog/accepted-runtime-v3.json;ไม่ทับcanonicalreports/data
3. Notebook21 evaluation/errors/coloursตรวจรับ017bแล้ว:actual017-00259.37s/36checks,independent135checks,40targeted/666backendtests. Metrics/thresholds/capture/floor byte-identical001;10PNG+SVGตรวจแล้ว;รายงานตรงห้าหัวข้อและมี10สไลด์พร้อมประเด็นพูด. Pins workflow/evaluation/accepted-runtime-v3.json;assets output/spatial-model-results/v3-evaluation-017-002. ข้อสังเกตเล็กน้อย:legendทับannotationbaseline0บางส่วนแต่ไม่ทับคะแนนcandidate;กราฟgroupsเป็นภาพรายละเอียดแนวตั้งสำหรับappendix/SVG
4. ส่งClaude018แล้ว23:30วันที่11พ.ย.:Notebook22 runtimeใช้benchmarkHGBbundlesเดิม ตรวจ hash/feature parity/prediction parity กับ saved2024/25. Baseline statsสร้างจาก pinned19เมื่อstartupไม่fitในrequest. ไม่ทำextendedrefit. Managerpins workflow/serving/input-pins-v3.json
   - 018รอบแรกตรวจจริง50passed/2failed:fixtureสมมติว่าปี2024/25มีcontextทั้งที่core-only;sourceพบการใช้ndarraytruthในerror.rows. ส่งแก้รวม018aโดยไม่แก้accepted19/20/21หรือเกณฑ์เลือก. 018a82targetedtestsผ่าน3.61s;actualkernel018-001เริ่ม12พ.ย.00:37และfullbackendregressionกำลังรัน ยังไม่รับruntimeจนfullparity/independentverifierผ่าน
   - ตรวจรับ018aแล้ว12พ.ย.:actual018-00184.35s/23checks/592protectedunchanged;independent34/34;731backendtests46.03s. Fullsaved2024/25daily2269755/6h9079020 selected+baselineตรงทุกค่า(maxerror0),core-onlyตามsavedmask;syntheticcontextfixtureแยกชัด. Pins workflow/serving/accepted-runtime-v3.json;aggregateexport output/spatial-model-results/v3-serving-018-001. ไม่ได้fit/refitหรือรัน016ซ้ำ
5. 2026 audit/evaluation:ใช้ snapshotใหม่ที่แยกเก็บ ไม่แก้ rawเดิม กำหนดกติกาก่อนดูคะแนนตามด้านล่าง
   - ส่งClaude023แล้ว12พ.ย.07:15ผ่านbridgeเดิม หลังaccepted22;source/linkage/runtimepinsพร้อม. ยังไม่มี2026scores/acceptanceจนactualrun+independentverificationผ่าน
   - Actual023-00120.72s complete;independent22/22;5PNGตรวจแล้ว. Raw18448/Jan–Sep17272/eligible4336;daily4116positivecells/6h4232/1128segments. ยังไม่รับ:42targetedผ่าน/1fixtureNaNvsNoneไม่ผ่าน;อันดับmost_over_predictedผิดทิศ;baselinezero-on-positive50daily/175six-hourทำให้rawdevianceไม่มีfinitevalueแต่ตารางเดิมแสดงn/aไม่ชัด. ส่ง023aแก้รวม08:15โดยคงcohort/predictions/กติกาเลือกเดิม เพิ่มแยกrawstatusกับoriginallocked-floor auditและตรวจlagอิสระ. ไม่ได้rerun016/refit
   - ตรวจรับ023aเชิงdiagnosticแล้ว:actual00221.91s/32checks,independent36/36,52targeted/765backendtests41.51s;rowledger/cells/predictions5CSVตรง001ทุกbyte;5PNGตรวจแล้ว. Scopeeligible1ม.ค.–30ก.ย.4336rawrecords/1128segments/19recordedprovinces. Pins workflow/evaluation-2026/accepted-diagnostics-v3.json;export output/spatial-model-results/v3-2026-diagnostics-023-002. ข้อจำกัดจริงเพิ่ม:CKANhashไม่ตรงMD5ไฟล์และmetadataไม่ระบุalgorithm จึงยังยืนยันproviderchecksumไม่ได้;localSHA256snapshotตรงpin. ไม่มีfullpopulationaccuracy/uniquephysicalevent/completeSeptemberclaim
6. Integrated local API019 ใช้ accepted14/21/22 พร้อม strict inputs/unsupported/unavailable/readiness, pytest และ live HTTP smoke
   - ส่งClaude019แล้ว12พ.ย.08:39;integrateaccepted13province/14Catalog/22spatial/23diagnosticพร้อมNEW24geometry/queryhelpers. Top-levelpins workflow/api/input-pins-v3.json;24/configpinsยังว่างโดยตั้งใจจนmanagerตรวจsource/fixtures. ไม่มีAPIacceptanceหรือactualHTTPผ่านจนกว่าจะรันจริง
7. รายงาน Model Gateห้าหัวข้อพร้อม actualCSV/PNG/SVG และลำดับสไลด์/ประเด็นพูด แยก OOF2022–23/seen2024–25/2026 diagnostic ชัดเจน ปิดด้วยrunbookและข้อจำกัด

## ตรวจแหล่ง2026ก่อนคะแนน

- Official CKAN package https://datagov.mot.go.th/api/3/action/package_show?id=roadaccident
- Resource4625b7aa-99a4-4dfb-9a0f-6402814d0f2c last_modified2026-11-02T03:23:45.994271
- URL https://datagov.mot.go.th/dataset/7e077ffd-dc4f-4dc6-a71c-0813726f3c12/resource/4625b7aa-99a4-4dfb-9a0f-6402814d0f2c/download/accident2026.csv
- เก็บignored backend/data/v3/evaluation_2026_source/20261111/{accident2026.csv,ckan_package.json} ไม่ทับ original
- RawCSV10098288bytes,sha25642cdd12055c5a1f26b965ec5dda3bf0d43684ecd1a21c3e976836d9a1a89d232;18448rows,38columns ไม่มีACC_CODE. วันที่เกิดเหตุ1ม.ค.–31ต.ค.;วันรายงานล่าสุด2พ.ย.;75reportdatesparseไม่ได้;22exactduplicates. Eventdatesทุกแถวparse exact%d/%m/%Yได้. มกราคม2661/กุมภาพันธ์1933/มีนาคม1844/เมษายน2733/พฤษภาคม1756/มิถุนายน1683/กรกฎาคม1663/สิงหาคม1564/กันยายน1435/ตุลาคม1176
- Lagเฉพาะreportdateparseได้ median18/P90 85/P95 102/P99 174/max293วัน. ดังนั้น30daylabelavailabilityของงานเดิมเป็นresearchassumption ไม่ใช่หลักฐานว่ารายงานครบจริง
- Original local15239rowsจบ7ก.ย.,กันยายน118rows จึงห้ามใช้ไฟล์เดิมอ้างครบกันยายน. ไม่แก้แหล่งเดิม

## กติกา2026ก่อนคะแนน (ยังไม่ได้คำนวณคะแนนปี2026)

1. เป้าหมายช่วงวันที่2026-01-01..2026-09-30เท่านั้น;กันตุลาคมออกด้วยกติกาวันที่ ไม่เลือกตามคะแนน. ตรวจวันที่แบบexact D/M/Y/เวลาที่ตรวจสอบได้/พื้นที่และการเชื่อมถนนตามaccepted geometry/rules. ไม่ใช้descriptionsหรือobservedweatherณเกิดเหตุเป็นprospectivefeatures
2. แยกจำนวนก่อน/หลังตัดและเหตุผลแบบexclusiveและmultiissueต่อเดือน/จังหวัด/หน่วยงาน. Missinginvaliddate/time/route/coordinatesหรือambiguouslinkageไม่กลายเป็นzero. คงmissingfeatureตามaccepted preprocessors/routedfallback ห้ามเปลี่ยนfeaturecolumns
3. ไม่มีACC_CODEจึงห้ามอ้างeventidentitydedupเทียบaccepted2021–25ได้สมบูรณ์. ตรวจexactduplicatesแบบfullrawrow fingerprintที่กำหนดก่อนคะแนน ไม่ใช้ตำแหน่ง/เวลาอย่างเดียวรวมเหตุ. ถ้าไม่มีหลักฐานพอ ให้รายงานrawrecord-count diagnostic พร้อมข้อจำกัด หรือ unavailable ในส่วนที่ต้องอาศัยuniqueeventidentity
4. ใช้selectedHGBpolicy/configจากOOFlockเดิมก่อนปี2026 กับstrongbaselineบนแถวและscopeเดียวกัน. ไม่มีgridsearch/retune/reselection. Candidatefamilyอื่นเทียบด้วยOOFเดิม;ไม่ฝึกโมเดลเพิ่มเพื่อสร้างตารางปี2026
5. แหล่งนี้ไม่มีหลักฐานรับรองfullcalendar×segment completeness. ห้ามเติมzeroให้unobservedcellsหรืออ้างfullpopulation2026metrics. หากตรวจได้เฉพาะcellที่มีobservedlinkedrecords ให้ประเมินpositive-observed-cell diagnosticสำหรับทุกวิธีบนidenticalcells เปิดเผยoutcomeconditionedselectionbiasและห้ามเทียบกับfullpopulationOOFโดยตรง;หากlabelsยังเชื่อถือไม่ได้ ให้ส่งdataaudit/availablepredictionsและระบุevaluationunavailableพร้อมเหตุผล
6. บันทึกreportlag/maturityแยกเดือน/พื้นที่ รวมlatearrivalsจากsnapshotเก่าเทียบใหม่แบบaggregate. วันอัปเดตไฟล์ไม่ใช่reportingcomplete;กันยายนยังอาจถูกแก้ย้อนหลัง. ไม่มีverifiedzeroไม่มีfullpopulationaccuracy
7. 2026เคยใช้diagnosticdataauditในโครงการและเคยตรวจdatecompletenessแล้ว ไม่เรียกstrictuntouchedtest. ไม่มี2026scoreใช้เลือกHGBนี้ รายงานstatusและข้อเท็จจริงแยกกัน

## การรับงาน

ทุกstageต้องactualchecksและreview. เก็บfailedrootsไม่ทับ;ไม่ถือworkerCLIจบว่าacceptance. บันทึกแต่สิ่งที่รันจริง ไม่อ้างpytestเก่าผ่านworkingtreeใหม่. หากClaudeขัดข้องแจ้งผู้ใช้และทำเฉพาะงานตรวจ/เอกสารต่อ ไม่เขียนโค้ดแทน

## สถานะ quota และจุดรับช่วงล่าสุด

- Claude run20261111-195459-56913หยุด19:55:12ด้วยsessionlimit,reset22:40วันที่11พ.ย.2026Asia/Bangkok. แก้เฉพาะsyntaxmetadataก่อนหยุด;Codexไม่ได้แก้โค้ดแทน
- Codexประกอบ21จากexactpayloadหลังหยุด รันทดสอบ/actual001/verifierและตรวจ9PNGครบแล้ว. ไม่retryClaudeก่อนreset ไม่เปลี่ยนmodel/criteria
- กลับมาทำต่อ23:12วันที่11พ.ย.หลังresetแล้ว:ส่ง workflow/tasks/017b-evaluation-final-correction-2.md ผ่านbridgeเดิมและClaudeตอบ/แก้ไฟล์ได้จริง. ครั้งละworker →ตรวจรับ21→เติมpinsและส่ง018→ตรวจรับ22→023dataaudit/observed-recorddiagnostic→019API→ปิดModelGate/presentation/runbook. APIยังไม่มี จึงยังไม่มีคำสั่งเปิดAPIที่ทดสอบผ่าน
- โค้ด/ผลที่รันจริงยังคงอยู่ ไม่มีการทับ016-002/rawเดิม/Catalog003. 2026snapshotใหม่เก็บignoredแยก;ไม่มี2026scoresจนกว่าระบบruntimeและlabelsผ่านตรวจ
