# รายงานความพร้อมเชิงวิจัยของ runtime การพยากรณ์เชิงพื้นที่ (V3, notebook 22)

**สิ่งที่พยากรณ์:** จำนวนบันทึกที่คาดหมาย (lambda) ของบันทึก SELECTED+LINKED ต่อช่วงถนน x วัน หรือ x ช่วง 6 ชั่วโมง ไม่ใช่ความน่าจะเป็นเกิดอุบัติเหตุรายบุคคล ไม่ใช่ความเสี่ยงต่อยานพาหนะ และห้ามรวมเป็นความน่าจะเป็นของเส้นทาง

- เวอร์ชันโมเดล: `roadaware-spatial-v3-benchmark-issue-2023-12-31T18` (benchmark, ออก ณ 2023-12-31 18:00:00, ใช้ label ถึง 2023-12-01 18:00:00)
- ช่วงวันที่เป้าหมายที่รองรับ: 2024-01-01 ถึง 2027-12-31 (หลัง 2025-12-31 เป็น research scenario ไม่มีค่าจริงให้เทียบ)
- ไม่มี extended refit และไม่มีโมเดล OOF fold จึงไม่อ้างการ replay OOF

## ความตรงกันกับผล notebook 20 ที่บันทึกไว้ (ทั้งประชากร 2024/25 ที่เคยเห็นแล้ว)

- daily `hgb_poisson_fixed::routed_context`: 2269755 แถว, max abs error 0, เกิน tolerance 0 แถว, routing mask ไม่ตรง 0 แถว; ขอบเขตจริงจาก mask ที่บันทึกไว้: core_only_no_observed_context (context 0 / core 2269755)
- daily `segment_mean_k365`: 2269755 แถว, max abs error 0, เกิน tolerance 0 แถว, routing mask ไม่ตรง 0 แถว; ขอบเขตจริงจาก mask ที่บันทึกไว้: core_only_no_observed_context (context 0 / core 2269755)
- 6h `hgb_poisson_fixed::routed_context`: 9079020 แถว, max abs error 0, เกิน tolerance 0 แถว, routing mask ไม่ตรง 0 แถว; ขอบเขตจริงจาก mask ที่บันทึกไว้: core_only_no_observed_context (context 0 / core 9079020)
- 6h `segment_mean_k365`: 9079020 แถว, max abs error 0, เกิน tolerance 0 แถว, routing mask ไม่ตรง 0 แถว; ขอบเขตจริงจาก mask ที่บันทึกไว้: core_only_no_observed_context (context 0 / core 9079020)

## ตรวจการ routing ด้วยข้อมูลสังเคราะห์ (SYNTHETIC fixture — ไม่ใช่หลักฐานจากข้อมูลจริงปี 2024/25)

- daily: 6 แถวสังเคราะห์ (context 2 / core 4), ผ่านทั้งหมด: True
- 6h: 6 แถวสังเคราะห์ (context 2 / core 4), ผ่านทั้งหมด: True

## ตรวจตัวแบบด้วย reference requests ภายใน (รวมปี 2021 จึงไม่ใช่การพยากรณ์ล่วงหน้า)

- daily core: 1000 แถว, max abs error 0
- daily context: 1000 แถว, max abs error 0
- 6h core: 1000 แถว, max abs error 0
- 6h context: 1000 แถว, max abs error 0

## คำขอสาธารณะที่ติดตามได้

- rows: 1536
- seen_rows_traced_to_20_arrays: 1152
- research_scenario_rows: 384
- max_abs_error_seen: 0
- context_rows: 0
- core_rows: 768
- future_core_rows: 192
- seen_selected_saved_mask_context_rows: 0
- observed_routing_scope_seen: core_only_no_observed_context
- bank_calendar_unknown_rows: 384

## ความทนทาน

- กรณีคำขอผิด/นอกขอบเขต/ผลไม่ถูกต้อง ผ่าน 87/87
- กรณีไฟล์ถูกแก้/ขาดหาย ถูกปฏิเสธอย่างชัดเจน 12/12

## เวลาตอบสนองที่วัดจริง (ไม่ใช่ SLA)

- daily selected batch 1: median 14.1 ms, p95 14.5 ms
- daily baseline batch 1: median 7.83 ms, p95 9.63 ms
- daily selected batch 128: median 21.2 ms, p95 28.3 ms
- daily baseline batch 128: median 13.8 ms, p95 14.6 ms
- 6h selected batch 1: median 15.5 ms, p95 15.9 ms
- 6h baseline batch 1: median 8.66 ms, p95 8.84 ms
- 6h selected batch 128: median 23.5 ms, p95 23.8 ms
- 6h baseline batch 128: median 15.4 ms, p95 15.9 ms

## สถานะ

- research_ready: **True**
- production_ready: **False** (ยังไม่ deploy, ยังไม่มี API019)
- checks ที่ไม่ผ่าน: ไม่มี

## แหล่งข้อมูลและข้อจำกัด

- weather: coarse province-point daily (and 6 h block) archive aggregated to target day - 2; not station-level, not observed at the event; missing for future dates -> routed to the core component
- aadt: annual DOH survey-point proxy from the latest vintage available before the target year; not live traffic
- geometry: current qualified DOH 2000 m segment snapshot applied retrospectively; event datum/linkage assumptions of notebooks 18/19
- bank_calendar: bank-holiday flag is known only where the as-of calendar covers the date; unknown stays missing (native HGB NaN handling, never imputed as 0)
- labels: 30-day label availability is a research assumption, not a verified publication delay
- Expected SELECTED+LINKED recorded-count rate per segment and horizon; not an individual accident probability, not per-vehicle risk; never sum into a route probability.
- 2024/25 are PREVIOUSLY SEEN diagnostics; target dates after 2025-12-31 are research scenarios with no observed ground truth.
- Colour is relative to the 2022-23 OOF reference density of the selected policy; 'base' (lowest band) is NOT safe.
- Only the 3105 qualified DOH segments are supported; other roads are outside coverage (no snapping, no fake zero).
- Research readiness only: production_ready is false; nothing is deployed.
