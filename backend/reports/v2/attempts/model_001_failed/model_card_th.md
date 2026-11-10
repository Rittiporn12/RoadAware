# Model card V2 (ร่างงานวิจัย, Notebook 11)

- ใช้งาน: วิจัยเท่านั้น, operational BLOCKED, ไม่ใช่ความเสี่ยงรายบุคคล/เส้นทาง
- ข้อมูล: panel v2 ที่ตรวจรับแล้วจาก notebook 10 (hash ล็อกใน selection_lock.json); ป้าย = บันทึก MOT ที่ถูกเลือก

## daily
- วิธีที่แนะนำ: hgb_poisson__full (candidate_passed_gate)
- strongest baseline: baseline_province_month_k30
- ตัวแทนแต่ละตระกูล: {'poisson': 'poisson_a0.001__full', 'rf': 'rf_poisson__full', 'hgb': 'hgb_poisson__full'}
- gate ผ่าน: True

## 6h
- วิธีที่แนะนำ: hgb_poisson__calendar_traffic (candidate_passed_gate)
- strongest baseline: baseline_province_block_mean
- ตัวแทนแต่ละตระกูล: {'poisson': 'poisson_a0.001__full', 'rf': 'rf_poisson__full', 'hgb': 'hgb_poisson__calendar_traffic'}
- gate ผ่าน: True

## ข้อควรระวัง
- 2024/2025 เคยเห็นแล้ว ไม่ใช่ test อิสระ; ห้ามเลือกใหม่จากผลปีหลัง
- ตัวกรอง eligible ได้จากผลลัพธ์ ใช้ล่วงหน้าไม่ได้
- traffic ไม่ใช่ตัวหาร exposure; weather มีความไม่แน่นอนเรื่องการเผยแพร่ย้อนหลัง
