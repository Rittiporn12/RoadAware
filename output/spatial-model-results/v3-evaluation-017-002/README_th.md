# spatial_evaluation (notebook 21) -- คำอธิบายไฟล์

- colour_contract_daily.json / colour_contract_6h.json: เกณฑ์สีคงที่ (P50/P80/P95 ของ density OOF 2022-23 ของ policy ที่เลือก) แยกตามหน่วยเวลา ห้ามแปลงข้ามหน่วย
- metrics_by_group.csv: metric เต็มประชากรตามกลุ่ม (aggregate เท่านั้น ไม่มีข้อมูลรายแถว); WAPE = ว่าง เมื่อกลุ่มไม่มีบันทึกจริง
- reconciliation.csv / selection_reason.csv: เทียบกับตารางของ notebook 20 และค่า gate ที่ล็อกไว้ (ยืนยันเท่านั้น ไม่เลือกใหม่)
- floor_audit*.csv: sensitivity หลังเห็นผล daily เบื้องต้น (ไม่ใช่ gate)
- province_reconciliation.csv: จำนวน cells ต่อจังหวัดเทียบกับ province_code ของ segment ที่เป็น input (unknown แยกกลุ่มเมื่อไม่มี code; ใช้ mapping เดียวกัน จึงไม่ใช่การตรวจอิสระ)
- figure_errors_by_group.csv: ใช้กับ errors_by_group (เวลา/เทศกาล/context/zero) และ errors_by_area_month (จังหวัด/เดือน) พร้อม cells/records ของแต่ละกลุ่ม
- capture_equal_road_km.csv / colour_exposure_capture.csv: capture ที่งบ road-km เท่ากันต่อวัน/ต่อ 6 ชม. และสัดส่วนตามสี (ไม่ใช่ผลด้านความปลอดภัยเชิงสาเหตุ)
- spatial_transfer.csv: ผล transfer แยกจากการเลือกเชิงเวลา; bootstrap_exploratory.json: จาก notebook 20 (exploratory หลังการเลือก)
- figures/*.png|svg + figure_*.csv: กราฟจากตัวเลขจริงในไฟล์ CSV เดียวกัน; results_th.md, model_gate_presentation_th.md: สรุปภาษาไทย
- 2026: รอการตรวจข้อมูลและประเมินแยกต่างหาก -- ยังไม่มีผล
