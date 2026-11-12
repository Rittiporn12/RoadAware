# RoadAware: Model Gate และหลักฐานส่งมอบ

เริ่มอ่านที่ [Model Gate ภาษาไทย 5 หัวข้อ พร้อมลำดับสไลด์12หน้าและประเด็นพูด](../../workflow/model-gate-presentation-th.md)

- [Evaluation OOF/seen diagnostics: โมเดล ฟีเจอร์ เกณฑ์เลือก ตารางและกราฟ](v3-evaluation-017-002/model_gate_presentation_th.md)
- [Runtime: โหลดโมเดลเดิม ตรวจ prediction parity และข้อจำกัด](v3-serving-018-001/readiness_th.md)
- [ปี2026: แหล่งข้อมูล จำนวนก่อน–หลังตัด lag และ positive-cell diagnostic](v3-2026-diagnostics-023-002/report_2026_th.md)
- [วิธีเปิด API และตัวอย่างเรียก](../../workflow/api/backend-api-runbook-v3-th.md) — ตรวจรับแล้วHTTP00473/73checks;finalbackend831passed/1conditional-skip พร้อมต่อFrontend/Dashboard
- [หลักฐาน HTTP / OpenAPI / ตัวอย่างผลจริง / hashก่อน–หลัง](v3-api-019-004/README_th.md) และ [acceptedrecordรุ่นไฟล์](../../workflow/api/accepted-runtime-v3.json)
- [สัญญาการเชื่อม API สำหรับผู้พัฒนาฝั่งผู้ใช้](../../workflow/api/frontend-integration-contract-v3.md) — ไม่มีfrontendในงานนี้

แต่ละโฟลเดอร์ผลมีCSVต้นทางของตารางและกราฟ PNG/SVG ที่สร้างจากผลจริง พร้อมmanifest/hash ผลOOF,ปีที่เคยเห็น2024–25 และ diagnostic2026เป็นคนละขอบเขต ห้ามเทียบระดับคะแนนข้ามชุดโดยตรง

ปี2026ไม่มีACC_CODE ความครบถ้วน/zero labels/เอกลักษณ์เหตุการณ์จริงยังไม่ยืนยัน และproviderchecksumยังไม่ผ่านการยืนยัน ข้อมูลที่ไม่มีรายการไม่ถูกเติมเป็นศูนย์ เอกสารหลักระบุข้อจำกัดและขอบเขต19จังหวัดที่มีeligible observed recordsไว้ชัดเจน

ไฟล์ที่ติดตามในGitเป็นsourceและรายงานaggregate ไม่รวมrawrows/modelbundles/cache/dataทั้งหมด เครื่องใหม่ต้องกู้artifactsnapshotที่ตรงmanagerpinsตามrunbookก่อน APIจึงพร้อมบริการ ไม่มีการdeployหรือรับรองproduction/safety
