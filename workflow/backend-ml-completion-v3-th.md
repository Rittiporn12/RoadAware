# เกณฑ์ปิดงาน backend/ML ก่อน frontend

ผู้ใช้อนุญาตให้ทำให้ครบเมื่อ11พฤศจิกายน2026 และแจ้งClaudeรีเซ็ตแล้ว รอบนี้ทำ backend/ML ต่อจนมีหลักฐานพร้อมเชื่อม frontend โดยไม่สร้างหน้าจอหรือ deploy

## ลำดับและเกณฑ์จบ

| ขั้น | สิ่งที่ต้องตรวจจริง | สถานะเริ่มรอบ |
|---|---|---|
| Spatial lineage/road snapshot | UID/hash/geometry/ความยาวและoffline replay | Notebook16/17ตรวจรับแล้ว |
| Linkage/segment inventory | exactagency+route+ระยะ,unknown/ambiguous,0.5/1/2กม.,ไม่จัดเหตุซ้ำ,อนุรักษ์ความยาว | ตรวจรับแล้วที่bbdea89:61testsเฉพาะ/455backendtests,actual00248.87s/38checks |
| Protocol/preparation | targetแบบconditional recorded+linked count,roaduniverseก่อนดูผล,train-onlyเลือกความละเอียด/horizon,missinglabel/zero policy,featureavailability,chronological/spatialfolds,resourcebudget | ตรวจรับ015/015aแล้ว: 83 fixtures, 538 backend tests; actual002 89.36s, 41 checks; ยังไม่มีคะแนนโมเดลรายถนน |
| Experiments | Poisson/RF/HGBและstrongtrain-onlybaselinesบนlabelเดียวกัน,ไม่มีrandomtimesplit,selectionlockก่อนseen2024/25diagnostics | รับ016-002แล้ว:3416.75s/52checks,6labeloracles/254metrics+45calibrationcomparisons;HGB routedทั้งสองหน่วยผ่านเกณฑ์เดิม ไม่มีtrainingซ้ำ |
| Evaluation/colours | Deviance/MAE/RMSE/bias/calibration/errorgroups,thresholdsจากtrain/OOF,เทาเมื่อunknown,outofscopeไม่เป็นปลอดภัย | ส่งClaude017แล้ว ใช้accepted20arraysเดิม;ยังไม่ตรวจรับ21 |
| Serving | โหลดbundleที่ตรวจhash,predictตรงsavedresults,featureparity,finiteJSON,coverage/fallback/researchflags,historyก่อนcutoff,ไม่fitในrequest | V2มีหลักฐานแล้ว;V3ยังไม่มี |
| API/catalog | prediction/geometry/metadata/evaluation/history,readinessจริง,missing/tampered/invalidinputs,limits,CORS,OpenAPIและliveHTTPsmoke | รับCatalog020/020a/020bแล้ว:actual0037.98s,18checks/61controls,independent67checks,50targeted/642backendtests;APIยังไม่เริ่ม งาน009เดิมยังWIP |
| Delivery | .ipynbเปิดVSCodeรันได้,runnerและdependencies,กราฟ/metricsจริง,runbookและfrontendcontract,GitHubตรงเครื่อง | สำรองทุกช่วงสำคัญ |

## ข้อกำหนดตลอดงาน

- รันClaudeครั้งละหนึ่งworkerตามAGENTS.md Codexตรวจdiffและรันทดสอบเอง CLIจบสำเร็จไม่เท่ากับตรวจรับ
- ไม่บังคับให้HGBชนะ หากstrongbaselineดีกว่าให้เลือกตามเกณฑ์ที่ล็อกและรายงานจริง ผลระดับจังหวัดไม่ย้ายไปเป็นคะแนนรายถนน
- Targetคือค่าคาดหมายจำนวนรายการที่เข้าเกณฑ์ฐานข้อมูลและเชื่อมได้ในพื้นที่/ช่วงเวลาที่ระบุ ไม่ใช่โอกาสชนส่วนบุคคลหรือจำนวนอุบัติเหตุจริงทั้งหมด
- หน่วยเวลาที่ข้อมูลรองรับต้องตรงกับคำขอAPIและความหมายสี ไม่มีการแปลงweeklymodelเป็นhourlyriskโดยไม่มีโมเดลรองรับ
- ข้อมูลweather/trafficจะใช้ต่อเมื่อjoinได้จริงและมีavailability/vintageที่อธิบายได้ ไม่มีlivecongestionจากAADTหรือobservedweatherตอนเกิดเหตุเป็นforecastfeature
- ป้องกันV2/acceptedspatialinputsทุกขั้น ไม่เขียนทับผลที่ตรวจรับ การทดลองใหม่อยู่outputrootใหม่ Raw/row-level/bundlesเก็บignoreddata;GitHubเก็บsourceและaggregateevidence
- แยกresearch_backend_readyจากproduction_ready: ปิดงานวิจัยและfrontendintegrationได้โดยเปิดเผยข้อจำกัด แต่ไม่รับรองoperationalsafetyหรือuntouchedfutureaccuracyที่ยังไม่เคยทดสอบ

รายละเอียดการเปลี่ยนจากauditไปโมเดลอยู่ [linkage-to-model-gates-th.md](spatial/linkage-to-model-gates-th.md) ความคืบหน้าจะปรับตามผลรันจริง ไม่ถือแผนเป็นหลักฐานว่าทำเสร็จ
