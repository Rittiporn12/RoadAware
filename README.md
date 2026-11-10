# Model stage — 06–08 ตรวจรับแล้ว (งานวิจัยย้อนหลัง)

- **Notebook 06** (Baseline 4 แบบ + Poisson, Random Forest, HGB): Codex ตรวจรับอิสระแล้ว — ดู [หลักฐานตรวจ 06](workflow/model-training-verification-th.md)
- **Notebook 07** (Evaluation Metrics / Experiment Results): Codex ตรวจรับแล้ว (metric ตรงกับ oracle อิสระ 22 คู่ภายใน 1e-12)
  — ดู [หลักฐานตรวจ 07](workflow/model-evaluation-verification-th.md)
  และผลจริงใน [`backend/reports/models/diagnostics/`](backend/reports/models/diagnostics/)
  ([ตารางหลัก](backend/reports/models/diagnostics/diagnostic_main_results.csv), [coverage 60 เดือน](backend/reports/models/diagnostics/coverage_by_split_month.csv),
  [อันดับปีหลัง](backend/reports/models/diagnostics/later_year_rank_comparison.csv), [manifest](backend/reports/models/diagnostics/diagnostic_manifest.json))
- **Notebook 08** (Error analysis / เหตุผลการเลือกโมเดล): วิเคราะห์จาก prediction ที่ตรวจ hash แล้ว (ไม่โหลด bundle, ไม่เลือกใหม่) และสร้าง
  [model card](backend/reports/models/model_card_th.md), [สรุปการตัดสินใจ](backend/reports/models/model_decision_summary.json) และ
  [`error_analysis/`](backend/reports/models/error_analysis/) ตรวจรับแล้ว: 143 tests ผ่าน และรัน 06–08 ซ้ำในโฟลเดอร์แยกผ่าน
  ข้อเสนอคือ **ระงับการนำไปใช้** จนกว่าจะแก้ blocker ของข้อมูล; recommended reference ตาม protocol OOF ไม่ใช่การอนุมัติใช้งาน

หลักฐานตรวจรับรอบสุดท้าย: [รายงานตรวจโมเดลครบชุด](workflow/model-final-verification-th.md) และ [ผลตรวจอิสระ](backend/reports/models/independent_final_review.json)

**คำเตือน:** การเลือกจาก OOF (ปี 2022–2023) ล็อกให้ Poisson เป็นตัวเลือก และ **ไม่เปลี่ยนย้อนหลัง** จากคะแนนปีหลัง
แต่ใน 07 Baseline ค่าเฉลี่ยรายจังหวัดมี Poisson deviance ต่ำกว่าตัวดีที่สุดของทั้งสามตระกูลทั้งปี 2024 (1.1535 เทียบ Poisson 2.1700)
และปี 2025 (1.2453 เทียบ 2.2546) ซึ่งสอดคล้องกับ regime shift จาก cleaning/รูปแบบวันที่ คะแนนอธิบายเฉพาะ province-day ที่ผ่าน
quality filter (มี selection bias) ปี 2024 ไม่มีเซลล์ eligible ในเดือน ต.ค.–ธ.ค. ปี 2025 เคยถูกดูแล้วจึงไม่ใช่ test อิสระ
และไม่ใช้ labels ปี 2026 ดังนั้น `production_enabled = false` และความพร้อมของโมเดลจริงยัง BLOCKED
หลักฐาน Data Foundation ด้านล่างยังคงสถานะเดิม

# RoadAware

## โครงสร้าง

```
backend/    งานข้อมูล/ML: notebook 01–08, config, runner, tests  → ดู backend/README.md
frontend/   สงวนไว้สำหรับเว็บไซต์ในอนาคต (ยังไม่มีหน้าจอ)        → ดู frontend/README.md
workflow/   brief, ทิศทางผลิตภัณฑ์ และงานที่ส่งให้ AI team
tools/      ตัวเชื่อม AI team
.venv/      (ไม่อยู่ใน git) Python environment ของโปรเจกต์ ใช้ร่วมกับ backend
```

สถานะปัจจุบัน: รากฐานข้อมูล (นำเข้า, EDA, ทำความสะอาด, แบ่งข้อมูล, ตรวจ leakage) เสร็จแล้ว มีโมเดลวิจัยย้อนหลังและ error analysis ใน 06–08 (ดูด้านบน) **ยังไม่มีเว็บไซต์และไม่มีโมเดลที่พร้อมใช้งานจริง** ชุด test ปี 2025 เคยถูกดูมาแล้ว (ไม่ใช่ test อิสระ) และความพร้อมของโมเดลจริงยังเป็น BLOCKED

เริ่มต้นเร็ว (ที่ root ของ repository):

```bash
python3 -m venv .venv && .venv/bin/pip install -r backend/requirements-data.txt
.venv/bin/python backend/scripts/run_data_notebooks.py   # รัน notebook 01–05 แบบ headless (ไม่เปิดเบราว์เซอร์)
.venv/bin/python backend/scripts/run_model_notebooks.py --stage train      # 06 เท่านั้น (fit + lock)
.venv/bin/python backend/scripts/run_model_notebooks.py --stage analysis   # 07 → 08 บนผลของ 06 (ไม่ refit)
.venv/bin/python backend/scripts/run_model_notebooks.py                    # --stage all (ค่าเริ่มต้น): 06 → 07 → 08
.venv/bin/python -m pytest backend/tests -q
```

ใน VS Code: เปิด `backend/notebooks/*.ipynb` เลือก kernel `.venv` แล้ว *Run All* ตามลำดับ 01 → 08 (ข้อมูล 01–05 แล้วโมเดล 06–08)

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
