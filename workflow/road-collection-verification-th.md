# ตรวจรับการเก็บเส้นถนนทางการ V3.0 (DOH/DRR)

Notebook17 ตรวจรับเฉพาะการเก็บ snapshot ในกรอบ EPSG4326 lon100.2..102.0,lat13.5..15.3 ไม่ใช่การตรวจรับโมเดลรายจุดหรือ labels

- Road-specific offline fixtures: **57passed,1.12s**
- Full backend: **385passed,19.89s**, joblibphysical-corewarningเดิม1รายการ
- Online kernelจริง: **37.99s**, DOH599features/30pages,DRR547features/28pages count/IDsก่อนหลังตรงกัน ไม่พบmissing/duplicate/unexpectedOID
- Offline kernelจริง: **15.8s**, อ่านcacheรอบonlineโดยปักacceptedmanifest raw/derivedhashesตรงกันทั้งหมด
- Codexตรวจ70rawresponses,28reporthashes(online+offline),10derivedhashes(สองรอบ) และคำนวณความยาวด้วยpyproj.Geodอิสระครบ1146features คลาดจากVincentyสูงสุด0.00294เมตร ตรวจ2figuresจริงแล้ว
- 373จาก374ไฟล์ก่อนเริ่มไม่เปลี่ยน อีก1ไฟล์คือbackend/.gitignoreที่อนุญาตให้เพิ่มguardป้องกันข้อมูลรายแถว/GeoJSONหลุดไปreports ไม่แตะV2/Notebook16

[รายงานจริง](../backend/reports/v3/road_collection/road_collection_report_th.md) · [Manifest](../backend/reports/v3/road_collection/road_collection_manifest.json) · [ตรวจอิสระ](../backend/reports/v3/road_collection_independent_review.json) · [Notebook17](../backend/notebooks/17_spatial_road_collection.ipynb)

ข้อมูลดิบ/cache/GeoJSONอยู่backend/data/v3/road_collection(ignored) และมีconfigเดิมสำรองbackend/config/archive/spatial_road_sources_v3_0.json รันซ้ำต้องใช้outputrootใหม่; rawdataไม่ได้ขึ้นGit ต้องกู้cacheหรือเก็บonlineใหม่อย่างชัดเจน

## ประเด็นที่ต้องตรวจต่อ

เส้น6featuresไม่simple (DOH2,DRR4) เก็บflagไว้ไม่ซ่อมหรือทิ้งเงียบๆ หน่วยattributeเป็นhypothesisรอเอกสาร,sourceเป็นsnapshotปัจจุบันไม่ยืนยันถนนทุกปี2021–25 และยังไม่ยืนยันการรายงานเหตุ/zero counts/road matching

ManagerตรวจจุดV2ในกรอบเดียวกัน:31089events,16910train แบ่งหน่วยงานDOH28726/DRR1290/EXAT1073 จึงเตรียม [013aเพิ่มEXAT](tasks/013a-exat-source-coverage-extension.md) เป็นส่วนขยายแหล่งข้อมูล แยกversion/outputdirsจากV3.0 ไม่ใช่การเปลี่ยนคะแนนโมเดล พบMOT-linked EXATFeatureServerlayer0ตอบcount8ในกรอบจริงแล้ว; geometryยังไม่ถูกเก็บครบจนกว่า013aจะรันและตรวจรับ

pyproj3.6.1ติดตั้งโดยCodexเพื่อcross-checkจริง (Python3.9-compatible);shapely2.0.7/scikit-learn1.6.1/pandas2.3.3/numpy2.0.2/joblib1.5.3เดิมไม่อัปเกรด พิสูจน์ค่าความยาวจากGeodได้ แต่ไม่ยืนยันdatumของพิกัดอุบัติเหตุโดยอัตโนมัติ
