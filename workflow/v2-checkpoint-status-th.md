# สถานะ V2: งานกำลังทำ ยังไม่ผ่านการรับรอง

ตรวจเมื่อ 10 พฤศจิกายน 2026 เวลา08:52น. (Asia/Bangkok)

ผู้ใช้เพิ่มข้อกำหนดฟีเจอร์: วันสำคัญ/เทศกาล อากาศ ฤดูกาล ช่วงเวลา และปริมาณ
จราจร เป้าหมายคือทดสอบว่าช่วยเหนือ baseline จริงหรือไม่ ยังไม่มีผลโมเดล V2
และยังไม่ได้เปลี่ยนโมเดลที่เลือกใน V1

## ทำแล้ว / หลักฐาน

- เก็บไฟล์ต้นทางจริงไว้ local ใต้ backend/data/external_v2/evidence (Gitignored):
  MOT XLSX2021-23, DOH AADT2021/metadata, ตัวอย่างJMA forecast48hย้อนหลัง2021,
  ขอบเขต77จังหวัด/รหัสจังหวัด, BOTปฏิทิน2022-25PDF/2021ภาพทางการ และประกาศ
  แก้ไขวันหยุดปลาย2023 ดูURL/ผลตรวจภาพใน calendar-source-verification.md
- ตรวจวันที่เบื้องต้นด้วยรหัสACC_CODE:2021เทียบMM/DDตรง20,062รายการ;
  2022ต่าง7,268รายการจากรูปแบบผสม ต้องใช้หลักฐานต่อID;
  2023มีIDซ้ำขัดแย้ง ห้ามเลือกแถวแรกมาแก้โดยไม่ตรวจ
- บันทึกกติกาฟีเจอร์/cohortก่อนเทรนใน v2-feature-policy.md และงาน005
- Claude เขียน config/ส่วนหนึ่งของnotebook09แล้ว แต่หยุดเพราะAPI429โควตารอบ
  session แจ้งรีเซ็ต12:20น. ยังไม่ได้เขียนsetupcell,runner,fixturetestsครบ
  และยังไม่ได้รวมผลตรวจปฏิทินล่าสุด จึงยังไม่ใช่notebookที่RunAllได้
- Codexตรวจsyntaxทุกcodecell09:ผ่านการcompile (ไม่เท่ากับรันจริงผ่าน)
- ตรวจSHA256ไฟล์V1ที่แช่ไว้112ไฟล์:ไม่เปลี่ยนทั้งหมด
- รันจริง `.venv/bin/python -m pytest backend/tests/test_data_notebooks.py backend/tests/test_model_notebooks.py -q`
  ผล143passedใน8.28วินาที เป็นการตรวจV1 ไม่ใช่การรับรองV2

## ยังไม่ทำ / ห้ามอ้างว่าผ่าน

- 09ยังไม่รันจริงครบ ไม่มีผลcollection77จังหวัดทุกปีที่ตรวจรับแล้ว
- configตัวอย่างweatherprobeURLยังต้องแก้latitude14.0เป็น13.75ให้ตรงไฟล์จริง
- ปฏิทินต้องรวมรายการที่ตรวจด้วยตาและamendmentadd/removeพร้อมknown_from
- trafficavailabilityต้องใช้created/modifiedอย่างระมัดระวังตามpolicy
- notebook10ยังไม่มี:แก้dateด้วยหลักฐาน,featurejoin,panelรายวัน/6h,EDA,leakage
- notebookโมเดลV2ยังไม่มี:3families/strongbaselines/ablations/metrics/erroranalysis
- ยังไม่มีผลว่าฟีเจอร์ใหม่ช่วยหรือโมเดลV2ชนะbaseline
- Frontend/Dashboardยังพักตามคำสั่งผู้ใช้

## จุดต่อ

1. ทำ004ให้ครบและตรวจรับจริง:setup+runner+tests+calendarreview,รันcollection,
   รายงานcoverage/hashและตรวจว่าV1ไม่เปลี่ยน
2. ทำ005ตามtaskfileโดยClaude (หรือCodexเมื่อผู้ใช้อนุญาตเปลี่ยนบทบาทเท่านั้น)
3. ล็อกprotocolV2ก่อนfit แล้วทดสอบPoisson,RF,HGB/strongbaselinesในchronological
   foldsเดียวกัน;2024/25เป็นข้อมูลเคยเห็น ไม่ใช่untouchedtest
4. สรุปผลจริง/ข้อจำกัดและpushGitHubเป็นช่วง;ห้ามบอกว่าเป็นoperationalforecast

AGENTS.mdกำหนดClaudeแก้code/Codexวางแผนตรวจงาน จึงขอการตัดสินใจจากผู้ใช้
ก่อนเปลี่ยนผู้เขียนimplementation การหมดโควตาไม่ใช่ผลตรวจรับงานผ่าน
Bridge review commandใช้ได้เฉพาะawaiting_codex_review;รอบนี้stagefailedจึง
บันทึกไม่รับงานในtimelineและเอกสารนี้แทน ไม่ปลอมสถานะให้reviewpass
