# ผลค้นหาแหล่ง geometry ระหว่าง Claude ทำ readiness audit

**กรอบเก็บข้อมูลนำร่อง:** EPSG4326 lon100.2..102.0, lat13.5..15.3 ใช้ envelope-intersects ได้ count DOH599 และ DRR547 ดู `pilot_query_manifest.json` ยังไม่ได้เก็บ geometry ครบ กรอบนี้ไม่ใช่เส้นทางที่คำนวณแล้วและไม่ครอบคลุม6จังหวัดทั้งหมด task013 จะตรวจครบเฉพาะประชากรใน query นี้ ภายใต้ขนาดข้อมูลที่จำกัดไว้

Codex ตรวจแบบ read-only วันที่ 11 พ.ย. 2026 จาก [MOT catalog](https://datagov.mot.go.th/th/dataset/transportgis) และติดตามลิงก์ทรัพยากรจริง พบว่าแม้คำอธิบาย catalog ระบุ WMS แต่ทรัพยากรทางหลวง/ทางหลวงชนบทชี้ไปที่ ArcGIS FeatureServer ซึ่งตอบ Query ได้

- DOH layer0: query count คืน 3,044 records, มี road_code/section_co/km_start/km_end/length และ polyline geometry ใช้ wkid4326 ทดสอบ query ขอ1รายการแบบ GeoJSON ได้ LineString จริง
- DRR layer2: query count คืน 3,700 records, metadata มี road_code/link_id/sublink_id/KM และวันที่สำรวจ ยังไม่ได้ตรวจ sample geometry ของ DRR
- จำนวนเหล่านี้เป็นจำนวน features/sections ณ เวลาคิวรี ไม่ใช่จำนวนถนนที่ไม่ซ้ำหรือช่วงถนนมาตรฐาน1กม.

เก็บ raw metadata6responses พร้อม hash ใน discovery_manifest.json ส่วน geometryตัวอย่าง1featureอยู่ใน local ignored reference เพื่อใช้ตรวจภายหลัง **ยังไม่มี full geometry snapshot, accepted spatial inventory, road matching หรือ zero-label evidence** ข้อมูลแหล่งนี้จึงไม่ทำให้ readiness audit ผ่านเกณฑ์ด้านถนนโดยอัตโนมัติ

งานถัดไปหลังตรวจรับ012: ให้ Claude เขียน notebook collection สำหรับ snapshot/pagination/object-ID reconciliation, hash/CRS/units/geometry checks และเก็บ road geometry ที่อาจไม่มีเหตุย้อนหลังด้วย ตรวจปีอ้างอิง/สิทธิ์ใช้ตามแหล่งข้อมูล พร้อมเลือก pilot envelope จากข้อมูลฝึกก่อนทำ labels แผนการเก็บข้อมูลไม่ใช่การรับรองว่าโครงข่ายครบตาม MOT accident coverage หรือสภาพถนนทุกปีตรงกับ snapshotปัจจุบัน
