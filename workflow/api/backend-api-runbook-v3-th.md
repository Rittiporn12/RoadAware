# คู่มือ backend API แบบ local (V3, research only, task 019)

สถานะ12พ.ย.2026: **ตรวจรับแล้วและพร้อมต่อFrontend/Dashboardในขอบเขตวิจัย** HTTP00473/73checks;finalbackend831passed/1conditional-skip ดู [acceptedrecord](accepted-runtime-v3.json) และ [หลักฐาน/OpenAPIจริง](../../output/spatial-model-results/v3-api-019-004/README_th.md). research_backend_ready=true;production_ready=false ไม่มีdeploy/auth/routingengine/frontend

## สิ่งที่ทำงานได้ในเครื่อง (manager เติม pin และตรวจรับแล้ว)
- `GET /health` (liveness) และ `GET /ready` (200 หรือ 503 พร้อมรหัสสถานะของแต่ละ component)
- พยากรณ์ระดับช่วงถนน `POST /api/v1/spatial/predictions` (และ baseline เปรียบเทียบ) จาก runtime ที่ยอมรับแล้วของ notebook 22 เท่านั้น
- endpoint province เดิม `POST /api/v1/predictions` ผ่าน notebook 13 (`load_registry`/`predict_batch`) — ระดับจังหวัด ไม่ถูกแปลงเป็นถนน
- ประวัติ: `GET /api/v1/history` (จังหวัด 2021-01..2025-12) และ `POST /api/v1/spatial/history` (ช่วงถนน ก่อน issue/cutoff ของวันเป้าหมายเดียวกัน) จาก catalog 14
- geometry: `GET /api/v1/segments?bbox=...` และ `GET /api/v1/segments/{segment_id}` (3105 ช่วงถนน DOH ที่ผ่านเกณฑ์ ของ notebook 19, EPSG:4326)
- `GET /api/v1/metadata`, `GET /api/v1/evaluation` (สรุป 21 + diagnostic ปี 2026 ของ 23 แบบ aggregate เท่านั้น)

## บันทึกขั้นตอนตรวจรับสำหรับผู้ดูแล (ทำแล้ว ไม่ต้องทำซ้ำเพื่อเปิดserver)

ผู้ใช้งานเริ่มที่หัวข้อ “เริ่ม/หยุด server” ได้เลย canonicalnotebooks/pinsถูกเก็บไว้แล้ว ไม่ต้องประกอบจากignoredhandoffใหม่ ขั้นตอนด้านล่างบันทึกวิธีตรวจรับ;ห้ามrefreshpinsหรือรันpipelineเดิมเพื่อให้ผ่าน
1. Codex assemble notebook 24: `.venv/bin/python tools/assemble_notebook_payloads.py --spec .ai-team/handoffs/019/notebook_cells.json --target backend/notebooks/24_backend_api_contract.ipynb`
2. ตรวจ/ทดสอบ: `.venv/bin/python -m pytest backend/tests/test_backend_api.py backend/tests/test_assemble_notebook_payloads.py -q`
3. คำนวณค่า pin (ห้าม worker เขียน pin เอง):
   ```
   .venv/bin/python - <<'EOF'
   import hashlib, json
   nb = json.load(open('backend/notebooks/24_backend_api_contract.ipynb'))
   f = [''.join(c['source']) for c in nb['cells'] if c['cell_type'] == 'code' and ''.join(c['source']).lstrip().startswith('# FUNCTIONS')]
   print('notebook24_functions', {'cells': len(f), 'join': '\n\n', 'sha256': hashlib.sha256('\n\n'.join(f).encode()).hexdigest()})
   for p in ('backend/notebooks/24_backend_api_contract.ipynb', 'backend/config/backend_api_v3.json'):
       print(p, hashlib.sha256(open(p, 'rb').read()).hexdigest())
   EOF
   ```
4. Manager เติม `files` (สองไฟล์ข้างบน) และ `notebook24_functions` ใน `workflow/api/input-pins-v3.json` หลังตรวจแล้วเท่านั้น ก่อนหน้านั้น `/ready` = 503 `api_pins_pending`
5. ทดสอบจริง: `ROADAWARE_API_ACTUAL=1 .venv/bin/python -m pytest backend/tests/test_backend_api.py -q -k actual`
6. Live HTTP smoke ตรวจรับใช้root004แล้ว หากตรวจใหม่ต้องใช้rootใหม่เสมอ เช่น `.venv/bin/python backend/scripts/smoke_api_live.py --run-root backend/rerun-api-019-005 --port 8765 --fixture-port 8766` (เริ่ม/หยุดเฉพาะserverของคำสั่ง,bind127.0.0.1;ห้ามใช้001/002/003/004ซ้ำ)
   ผลอยู่ใน run root ใหม่: `smoke_evidence.json`, `read_only_evidence.json`, `openapi.json`, `sample_responses.json`, `server.log`, `fixture_wrong_source_hash/` (ignored)
   - `read_only_evidence.json`: hash ก่อน/หลังของชุดไฟล์ที่ API ใช้จริงแบบจำกัดขอบเขต (manager lock เป็น root trust anchor ใช้ sha ตอนเริ่มรัน ไม่ได้ pin ตัวเอง, records/config/source, baseline NPZ 2 ไฟล์, chosen bundle ของ 22 สี่ไฟล์ที่ `models/<unit>/<file>`, chosen selected+baseline ของ 13 สี่ไฟล์, catalog/evaluation/2026 diagnostics) ถ้า chain hash ไม่ตรง ไฟล์หาย หรือหมวดที่ต้องมีไม่ครบ check จะ fail
   - `fixture_wrong_source_hash/`: TEST FIXTURE เท่านั้น (สำเนา lock ที่ใส่ hash ของ notebook 24 ผิดโดยตั้งใจ) ต้องได้ `/health` 200, `/ready` 503, prediction 503 ไม่มีค่า 0 ปลอม ไม่ใช่ config production

## เริ่ม/หยุด server (VS Code Integrated Terminal, ที่ root ของ repo)
```
.venv/bin/python backend/scripts/run_api_server.py             # http://127.0.0.1:8000  รอจน log แสดง "Application startup complete"
# หยุด: กด Ctrl+C ใน terminal เดียวกัน (ไม่ต้อง kill process อื่น)
```
startup จะตรวจ hash ทั้งหมดและ self-test ของ bundle ก่อนรับ request (อาจใช้เวลาหลายสิบวินาที) ระหว่างนั้น port ยังไม่เปิด

## ตัวอย่าง curl (คำตอบจริงให้ดูจาก `sample_responses.json` ของ smoke)
```
curl -s http://127.0.0.1:8000/ready
curl -s 'http://127.0.0.1:8000/api/v1/segments?bbox=100.4,13.6,100.8,14.0&limit=50'
curl -s -X POST http://127.0.0.1:8000/api/v1/spatial/predictions -H 'Content-Type: application/json' \
  -d '{"unit":"daily","requests":[{"segment_id":"rsv1-rc31f3d87fc7:doh:64:p0:c0:r2000:00003","target_date":"2024-03-01"}]}'
curl -s -X POST http://127.0.0.1:8000/api/v1/spatial/predictions -H 'Content-Type: application/json' \
  -d '{"unit":"6h","requests":[{"segment_id":"<id>","target_date":"2026-04-09","time_block":"18-24"}]}'
curl -s -X POST http://127.0.0.1:8000/api/v1/spatial/history -H 'Content-Type: application/json' \
  -d '{"segment_id":"<id>","target_date":"2024-03-01","unit":"daily"}'
curl -s 'http://127.0.0.1:8000/api/v1/history?province_key=<key จาก /provinces>&start_month=2024-01&end_month=2024-12'
curl -s -X POST http://127.0.0.1:8000/api/v1/predictions -H 'Content-Type: application/json' \
  -d '{"requests":[{"province_key":"กรุงเทพมหานคร","target_date":"2024-05-01","unit":"daily"}]}'
```
รหัสสถานะ: 400 invalid, 404 coverage (ถนน/จังหวัดนอก universe — ไม่ใช่ศูนย์), 413 body เกิน 64 KiB, 415 Content-Type ผิด, 503 unavailable (ข้อความทั่วไป ไม่มี path)

## การกู้คืน artifact (Git เก็บเฉพาะ source; ข้อมูลใหญ่ถูก ignore)
clone จาก GitHub อย่างเดียว **ไม่พอ** ต้องกู้ไฟล์ ignored เหล่านี้จาก snapshot ภายใน (hash ต้องตรงกับ pin/manifest ไม่เช่นนั้น server จะ 503):
- `backend/data/v3/spatial_preparation/` (universe_geometry.geojson, universe_segments.csv, counts/context ที่ manifest 19 อ้างถึง)
- `backend/rerun-spatial-model-016-002/data/v3/spatial_experiments/` (bundles `.joblib`, `.meta.json`, `.reference.csv`, arrays) และ reports ของ run นี้
- `backend/rerun-spatial-eval-017-002/reports/`, `backend/rerun-spatial-serving-018-001/` (serving record, baseline_stats_*.npz, prediction_fixtures.json)
- `backend/rerun-historical-catalog-020-003/` (reports + data ของ catalog), `backend/rerun-2026-eval-023-002/reports/`
- V2: `backend/reports/v2/`, `backend/data/v2/` และ bundles/configs ที่ notebook 13 ตรวจผ่าน `config/inference_v2.json`
ห้าม commit raw dataset/bundles ลง Git; ห้าม rerun notebook 13/14/19–23 เพื่อ "สร้างใหม่" (ผลจะไม่ตรง hash ที่ยอมรับ)

## ข้อจำกัดเชิงปฏิบัติการ (ยังไม่ทำ)
- ไม่มี untouched future test; ปี 2026 เป็น diagnostic แบบ outcome-conditioned เฉพาะ cell ที่มีบันทึก (4336 records / 4116 daily / 4232 6h cells / 1128 segments / 19 จังหวัด) ไม่ใช่การประเมินทั้งประเทศหรือเดือนกันยายนที่สมบูรณ์; provider checksum ยังไม่ยืนยัน
- ประวัติปี 2026 ไม่อยู่ใน catalog 14: แสดงเป็นช่วง unsupported ไม่ใช่ศูนย์
- ไม่มีสภาพอากาศ/AADT แบบ live: วันอนาคตใช้ core component (แจ้งต่อแถว)
- latency ที่วัดไว้ใน 22 ไม่ใช่ SLA; ไม่มี auth, rate limit ภายนอก, HTTPS, deploy, routing, frontend
- geometry คือ snapshot ปัจจุบันของ DOH ที่ผ่านเกณฑ์ ไม่ใช่โครงข่ายถนนในอดีต และไม่ใช่กราฟเส้นทาง
