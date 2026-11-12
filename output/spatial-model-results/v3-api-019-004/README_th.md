# Local research API ตรวจรับแล้ว

รอบ004ผ่าน73/73checksใน8.69วินาที (startup5.14วินาที) และfinalbackend831passed/1conditional-skip48.21วินาที พร้อมส่งต่อFrontend/Dashboardตามขอบเขตวิจัย ไม่มีfrontend/deploy/productionacceptance

- [smoke_evidence.json](smoke_evidence.json): checksจริง รวมข้อมูลประวัติ/geometry3105IDs/ผลselectedและbaselineทั้งสองหน่วย128แถวต่อชุดตรงsaved22/32แถวmetricsตรงCSV/OpenAPI/strictJSON/CORS/unsupported และlivecorrupt-source503
- [read_only_evidence.json](read_only_evidence.json):78ไฟล์จริงตรงtrustedpinsและไม่เปลี่ยน รวม4spatialbundles/4provincebundles/2baselineNPZ/rootmanagerlock;origin_countsนับทุกmembershipจึงอาจรวมมากกว่าจำนวนไฟล์จริง
- [openapi.json](openapi.json): schemaและตัวอย่างที่ตรวจเทียบHTTPจริงแล้ว
- [sample_responses.json](sample_responses.json): ตัวอย่างaggregate/publicresponsesจริง (บางรายการตัดให้สั้น) ไม่ใช่eventrows

[วิธีเปิดและcurl](../../../workflow/api/backend-api-runbook-v3-th.md) · [API contract](../../../workflow/api/frontend-integration-contract-v3.md) · [acceptedrecord/sourcehashes](../../../workflow/api/accepted-runtime-v3.json) · [Model Gate/สไลด์](../../../workflow/model-gate-presentation-th.md)

Gitเก็บsource/aggregateevidence;bundle/raw/artifactdataยังอยู่ในsnapshotภายในตามrunbook. ปี2026เป็นpositive-cell diagnosticเฉพาะ4,336observedrecords/19จังหวัด ไม่ใช่fullpopulationaccuracy;ความครบถ้วน/providerchecksumยังไม่ยืนยัน ประวัติ2026unsupported ไม่มีfakezero. serverทั้งhealthyและfixtureหยุดแล้วหลังตรวจ ให้เปิดใหม่ตามrunbookเมื่อใช้งาน
