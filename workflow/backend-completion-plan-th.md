# ขอบเขตปิดงาน backend/ML

ผู้ใช้สั่งให้ทำbackendและMLให้เสร็จก่อนfrontendเมื่อ10พ.ย.2026 ต่อจากV2ที่ตรวจรับแล้ว ขอบเขตรอบนี้คือ backendวิจัยที่รันจริงและพร้อมให้frontendเชื่อม ไม่ใช่การรับรองระบบความเสี่ยงรายเส้นทางเชิงปฏิบัติการ

1. Notebook13: ตรวจโหลดโมเดล/feature parity, robustnessเมื่อข้อมูลขาด, input validation, latency, serving contract และmodel registryที่ตรวจhashได้ โดยไม่ฝึกหรือเปลี่ยนตัวเลือกV2
2. Feature builderสำหรับคำขอจังหวัด/วัน/ช่วง6ชั่วโมง ใช้กฎและas-of snapshotsที่ตรวจรับแล้ว ไม่ใช้label/eligibilityเป็นinput ไม่เติมข้อมูลอากาศที่ไม่มีเอง วันนอกช่วงประเมินต้องระบุเป็นresearch scenarioพร้อมข้อจำกัดเรื่องความเก่าของโมเดล/แหล่งข้อมูล
3. Local API: health/readiness, metadata/provinces, predictแบบbatch, ข้อมูลผลประเมินและประวัติแบบรวมที่ตรวจสอบได้ OpenAPIและตัวอย่างสำหรับfrontend ยังไม่ทำหน้าจอ/แผนที่/route engine
4. ทดสอบAPIจริงทั้งsuccess/error/missing-artifact/tamperingและrequestขนาดเกินกำหนด ตรวจเวลาใช้งานและinput/output รันVS Codeได้ เก็บหลักฐานและpushGitHub

เกณฑ์จบรอบ: notebookรันสำเร็จ, testsผ่าน, predictionตรงกับbundle/ค่าที่บันทึก, APIเรียกจริงได้, manifest/คู่มือครบ, GitHubตรงเครื่อง สถานะbackendพร้อมเชื่อมแบบresearch ส่วนproduction_readyยังfalseตามหลักฐานเดิม

สิ่งที่ไม่อ้างว่าเสร็จ: untouched future evaluation, รายละเอียดถนน/ความเสี่ยงส่วนบุคคล, live traffic/weather ingestion, deployment, frontend/mobile UI ไม่มีการแต่งคะแนนหรือเปลี่ยนprotocolหลังเห็นผล
