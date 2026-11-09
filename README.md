# Model stage — in progress

มี Notebook ทดลอง Baseline และ 3 อัลกอริทึมแล้ว แต่ **ยังไม่ผ่านการรับงานครบ**
ผลจริง จุดล้มเหลว และงานที่รอทำต่ออยู่ใน [รายงาน Model เบื้องต้น](workflow/model-preliminary-findings-th.md)
หลักฐาน Data Foundation ด้านล่างยังคงสถานะเดิม การเลือกโมเดลใน OOF ยังไม่เท่ากับพร้อมใช้งานจริง

# RoadAware

## โครงสร้าง

```
backend/    งานข้อมูล/ML: notebook 01–05, config, runner, tests  → ดู backend/README.md
frontend/   สงวนไว้สำหรับเว็บไซต์ในอนาคต (ยังไม่มีหน้าจอ)        → ดู frontend/README.md
workflow/   brief, ทิศทางผลิตภัณฑ์ และงานที่ส่งให้ AI team
tools/      ตัวเชื่อม AI team
.venv/      (ไม่อยู่ใน git) Python environment ของโปรเจกต์ ใช้ร่วมกับ backend
```

สถานะปัจจุบัน: วางรากฐานข้อมูล (นำเข้า, EDA, ทำความสะอาด, แบ่งข้อมูล, ตรวจ leakage) **ยังไม่มีการเทรนโมเดลและยังไม่มีเว็บไซต์** ชุด test ปี 2025 เคยถูกดูมาแล้ว (ไม่ใช่ test อิสระ) และความพร้อมของโมเดลจริงยังเป็น BLOCKED

เริ่มต้นเร็ว (ที่ root ของ repository):

```bash
python3 -m venv .venv && .venv/bin/pip install -r backend/requirements-data.txt
.venv/bin/python backend/scripts/run_data_notebooks.py   # รัน notebook 01–05 แบบ headless (ไม่เปิดเบราว์เซอร์)
.venv/bin/python -m pytest backend/tests -q
```

ใน VS Code: เปิด `backend/notebooks/*.ipynb` เลือก kernel `.venv` แล้ว *Run All* ตามลำดับ 01 → 05

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
