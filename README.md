# RoadAware — ผล V2 ล่าสุด

**ML serving ล่าสุด:** Notebook13ตรวจรับแล้ว โหลดHGBและสร้างfeatureสำหรับคำขอใหม่ได้ ตรวจค่าทำนายตรงกับผลเดิม177,335แถว มี57testsผ่านและผลทดสอบข้อมูลขาด/เวลาใช้งาน ดู [หลักฐานML backend](workflow/backend-ml-serving-verification-th.md)

**API/catalog ยังไม่เสร็จ:** ดู [checkpoint](workflow/wip/009-api-quota-checkpoint/README.md) และ [task009a](workflow/tasks/009a-resume-api-after-quota.md) ยังไม่มี API ที่รันและตรวจรับแล้ว ส่วน frontend ยังไม่ทำ


**งานรายจุด/ช่วงถนน:** ผู้ใช้ยืนยันให้ต่อยอดการพยากรณ์และระดับเฝ้าระวังสี เตรียม [แผน Spatial V3](workflow/spatial/README_th.md) และ [task012 สำหรับ Claude](workflow/tasks/012-spatial-data-readiness.md) แล้ว ตรวจเชื่อมพิกัดกลับ raw ได้ครบ 106,308 retained V2 events แต่ยังไม่ตรวจ road matching/zero coverage และยังไม่มี spatial model หรือเกณฑ์สีที่ผ่านการประเมิน ผลจังหวัดด้านล่างไม่ใช่ผลรายจุด

**Spatial readiness ตรวจรับแล้ว:** Notebook16 รันจริงผ่าน 27 checks และ tests รวม 94 ผ่าน แก้ output-path guard และกราฟแล้ว ดู [หลักฐานตรวจรับ](workflow/spatial-readiness-verification-th.md) และ [รายงานจริง](backend/reports/v3/spatial_readiness/spatial_readiness_report_th.md) ขั้นต่อไปคือเก็บ geometry ถนนในพื้นที่นำร่อง ยังไม่มี spatial model หรือเกณฑ์สี

**ผลสำหรับ Presentation:** [10 กราฟ PNG/SVG พร้อม CSV และคำอธิบายไทย](output/model-results/README_th.md) · [ดาวน์โหลด ZIP](output/RoadAware_model_results.zip) เป็นผล V2 จริง ไม่ใช่การทดลอง spatial ใหม่

ทดลองจริง 3 ตระกูล: Poisson Regression, Random Forest (Poisson), HistGradientBoosting (Poisson) พร้อม baseline 6 แบบต่อหน่วย และ feature 5 ชุด เลือกจาก expanding time backtest 4 fold ในปี2022–2023 ตาม protocol ที่ล็อกก่อน fit

| หน่วย | Poisson Regression | Random Forest | HGB ที่เลือก | strongest baseline | ลด deviance |
|---|---:|---:|---:|---:|---:|
|จังหวัด×วัน|1.089593|1.127834|**1.064258**|1.146383|**7.16%**|
|จังหวัด×6ชั่วโมง|0.596262|0.601836|**0.583525**|0.607755|**3.99%**|

ค่าต่ำดีกว่า แสดงตัวดีที่สุดของแต่ละตระกูลในแต่ละหน่วย ไม่เทียบerrorข้ามหน่วย HGBชนะbaselineครบ4/4foldทั้งสองหน่วยและผ่านgateที่ล็อกไว้ รายวันเลือก `hgb_poisson__full` ราย6ชั่วโมงเลือก `hgb_poisson__calendar_traffic`

[รายงานวิเคราะห์จริง](backend/reports/v2/analysis/analysis_report_th.md) · [Model card](backend/reports/v2/analysis/model_card_v2_analysis_th.md) · [หลักฐานตรวจอิสระ](workflow/v2-final-verification-th.md) · [คู่มือรัน V2 ใน VS Code](workflow/v2-vscode-run-guide-th.md)

**Research only; production_ready=false.** ยังไม่มี untouched test: ปี2024เป็นdevelopmentและปี2025เคยเห็นแล้ว อากาศมีบางส่วน (204/385 province-years; ปี2024/2025ไม่มี) AADTเป็นปริมาณรถเฉลี่ยจากจุดสำรวจรายปี ไม่ใช่รถติดสด ผลนี้ยังระบุความเสี่ยงส่วนบุคคล/จุดถนน/เส้นทางไม่ได้

MLอยู่ใน `backend/notebooks/01–13` รันด้วยkernelในเครื่องผ่าน **VS Code Integrated Terminal** ตามคู่มือ ไม่ต้องเปิดเว็บJupyter `frontend/`ยังเป็นโครงสร้างสำรอง ไม่มีหน้าจอ/API/Dashboard ผลเดิมห้ามทับ ใช้output rootใหม่ในการรันซ้ำ ข้อมูลรายแถว/raw/bundleไม่อยู่ในGit หลังcloneต้องกู้snapshotและตรวจhash/lock

## ประวัติ V1 และเอกสารเดิม

ข้อความด้านล่างเป็นสถานะของ V1 ก่อนเริ่ม V2 ให้ใช้ผล V2 ด้านบนเป็นสถานะปัจจุบัน V1เก็บไว้ไม่แก้ย้อนหลังและcohortต่างกัน จึงไม่อ้างเปอร์เซ็นต์ดีขึ้นเทียบV1

## AI team

ระบบส่งงาน: คุณ → Codex วางแผน → Claude Code แก้ไฟล์ → Codex ตรวจและทดสอบ → รายงานคุณ

1. เปิด `Monitor AI Team.command` เพื่อดูขั้นตอนสด ปิดหน้าต่างนี้ได้โดยไม่หยุดงาน หรือกด Control+C
2. เปิด `Start Codex.command` เพื่อคุยกับ Codex ในโครงการนี้ หรือเปิดโฟลเดอร์นี้ใน Codex desktop
3. บอกงานที่ต้องการ Codex จะอ่าน AGENTS.md และส่งงานให้ Claude ผ่านตัวเชื่อม

ทั้งสอง CLI ต้องเข้าสู่ระบบไว้ก่อน หาก Claude แจ้งว่าเซสชันหมดอายุ ให้เปิด `Login Claude.command` แล้วเข้าสู่ระบบด้วยบัญชีของคุณ ตัวช่วยจะทดสอบการเชื่อมต่อแบบอ่านไฟล์ให้อัตโนมัติหลังเข้าสู่ระบบสำเร็จ จากนั้นให้ Codex ตรวจรายงานอีกครั้ง

```bash
python3 tools/ai_team.py monitor
python3 tools/ai_team.py note "Codex: กำลังตรวจแผน"
python3 tools/ai_team.py run workflow/tasks/000-connection-check.md
```

หน้าจอสดแสดงบันทึกขั้นตอนของ Codex ข้อความความคืบหน้าของ Claude และการเรียกเครื่องมือ เช่น อ่านหรือแก้ไฟล์ ไม่ใช่ความคิดภายในของโมเดล และไม่มีเปอร์เซ็นต์ความคืบหน้าที่คาดเดาขึ้น

ค่าตั้งต้นอยู่ใน `workflow/team.json` และให้ Claude ใช้เครื่องมืออ่าน/แก้ไฟล์ Codex เป็นผู้รันคำสั่งทดสอบ สถานะและผลอยู่ใน `.ai-team/` ซึ่งไม่ถูกเก็บใน Git ไฟล์ result.json เป็นรายงานจาก Claude และต้องให้ Codex ตรวจจริงอีกครั้ง ตัวเชื่อมไม่วนแก้งานเองและไม่เผยแพร่เว็บไซต์อัตโนมัติ

หากสิทธิ์ macOS ไม่ยอมเปิดไฟล์ .command ให้ใช้คำสั่ง `python3 tools/ai_team.py monitor` หรือ `codex` ผ่าน Terminal ในโฟลเดอร์นี้แทน
