# จากข้อมูลถนนไปสู่โมเดลและสีเฝ้าระวัง

เอกสารตรวจความพร้อม ณ 11 พฤศจิกายน 2026 ไม่ใช่ผลทดลองโมเดลรายจุด

## ตรวจรับแล้ว

- Notebook16 เชื่อมเหตุที่ V2 เก็บไว้กับ raw lineage ครบ106,308UID โดยไม่ยืนยันความถูกต้องบนถนนจาก bounding box
- Notebook17 V3.1 เก็บ DOH599/DRR547/EXAT8 geometry ในกรอบนำร่อง ตรวจ OID/hash/ความยาว และรันซ้ำ offline แล้ว ข้อมูลเดิมไม่ถูกแทนที่
- หลักฐาน source code/aggregate reports/กราฟชุดนี้สำรอง GitHub ใน commit cb50a61; ข้อมูลดิบอยู่ใน backend/data ที่ไม่ขึ้น Git

## กำลังทำ: Notebook18

จับคู่ด้วยหน่วยงาน+รหัสเส้นทาง+ระยะเชิงเมตร เกณฑ์หลัก50เมตรและ sensitivity25/100เมตร แยก matched/ambiguous/too_far/identity_unresolved/outside/precision ไม่บังคับจับคู่ทางพิเศษที่ไม่มี crosswalk เตรียม inventory0.5/1/2กม.จากถนน ไม่สร้างเฉพาะจุดเคยเกิดเหตุ

เกณฑ์ตรวจรับคือ hash/จำนวน/identity ต้องตรง, เหตุเดียวไม่ถูกนับซ้ำ, unknown ไม่กลายเป็น zero, ความยาวหลังแบ่งช่วงอนุรักษ์ความยาวเดิม, ตรวจไฟล์และกราฟจริง พร้อมรัน tests/notebook ด้วย Codex งานนี้ยังไม่ผ่านจนมีผลรันและ review

## ต้องตกลงใน protocol หลังเห็น audit

| เรื่อง | หลักฐาน/การตัดสินใจที่ต้องมี |
|---|---|
| Cohort/target | ระบุว่าเป็นจำนวนรายการในฐานข้อมูลที่ผ่าน pipeline และเชื่อมได้ ไม่ใช่อุบัติเหตุจริงทุกเหตุ อธิบายผลของแถว quarantine/เวลาไม่ชัด/พิกัดหาย/จับคู่ไม่ได้ |
| V2 eligibility | ห้ามคัดวันจาก outcome-derived training_eligible ของ V2 มาเป็น coverage หรือ feature สำหรับ spatial model ต้องกำหนดนโยบาย cohort และ missing labels ใหม่ |
| Zero | ศูนย์ใน target แบบ conditional หมายถึงไม่มีรายการที่เข้าเกณฑ์ pipeline ที่ล็อกไว้ใน bin นั้น ไม่ยืนยันว่าไม่มีอุบัติเหตุจริง ส่วนข้อมูลขาด/นอกพื้นที่/identityไม่ชัดต้องแยกสถานะ |
| Road universe | เลือกจาก inventory ที่กำหนดก่อนดูผล ไม่เลือกเฉพาะถนนที่ปีหลังมีเหตุ ใช้ snapshotปัจจุบันย้อนหลังได้เฉพาะ research assumption ที่เปิดเผย |
| Unit/horizon | ใช้ train-only support และขนาด panel เลือก0.5/1/2กม.กับวัน/6ชั่วโมง/สัปดาห์ ไม่ใช้คะแนนปี2024/25ที่เคยเห็นมาปรับให้ดูดี |
| Resource budget | ประเมินจำนวนแถวก่อน materialize ทั้งพื้นที่อาจมีหลายสิบล้าน segment×time rows ต้องมีงบหรือ subsetจากถนนจริงที่กำหนดล่วงหน้า |
| Split | Expanding time foldsสำหรับอนาคตบนถนนเดิม; spatial holdoutสำหรับถนนใหม่ แยกคำถามและกันข้อมูลข้างเคียงตาม protocol |
| Features | ปฏิทิน/เวลา/ฤดูกาลรู้ล่วงหน้าได้ ส่วน weather/traffic ต้องมี spatial join+available_at ก่อน issue_time ไม่ใช้สภาพอากาศตอนเกิดเหตุหรือ AADT เก่าแทนรถติดสด |
| Baseline/3 models | Baseline train-onlyที่มี smoothing/fallback เทียบ Poisson/RF/HGB ใหม่ ผล HGBระดับจังหวัดไม่ใช่หลักฐานว่ารายจุดชนะ |
| Selection | Mean Poisson devianceหลัก ร่วม MAE/RMSE/bias/calibrationและerrorแยกกลุ่ม เลือก baselineได้ถ้าโมเดลไม่ดีกว่า ไม่บังคับคะแนน |
| สี | หลัง count modelผ่านการประเมิน จึง fit cutoffsจาก train/OOFและล็อกversion เทาเมื่อไม่รองรับ/ข้อมูลไม่พอ ใช้labelคู่สี ค่า countต่ำไม่เท่ากับปลอดภัย |
| คำอธิบาย | ใช้ประวัติก่อน cutoffพร้อมจำนวนตัวอย่าง/unknown แยกคำอธิบายย้อนหลังจากพยากรณ์ ไม่อ้างเหตุสันนิษฐานเป็นสาเหตุที่พิสูจน์แล้ว |

โมเดล count ยังไม่ใช่ความน่าจะเป็นชนส่วนบุคคล และยังไม่รองรับการบวกความเสี่ยงรายจุดเป็นโอกาสเกิดเหตุตลอดเส้นทาง การทำสีต้องยึดหน่วยเวลาเดียวกับโมเดลจริง เช่น โมเดลรายสัปดาห์ไม่อ้างว่าปรับความเสี่ยงรายชั่วโมงได้

## หลัง protocol ผ่าน

สร้าง preparation/experiments/evaluation/serving เป็น notebookแยก เก็บ V3ไม่เปลี่ยนV2 รันและเก็บหลักฐานทุกช่วง จากนั้นปิดงาน API/catalogที่ยังค้างและทดสอบคำขอจริง ก่อนเริ่ม frontend/mobile/routing ตามที่ผู้ใช้กำหนด
