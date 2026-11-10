# แผนต่อยอด RoadAware: คาดการณ์รายพื้นที่/ช่วงถนนและระดับเฝ้าระวังสี

สถานะ 11 พฤศจิกายน 2026: **เตรียมข้อกำหนดและตรวจข้อมูลเบื้องต้นแล้ว ยังไม่มีโมเดลรายจุดที่ฝึกหรือผ่านการประเมิน** ผู้ใช้ต้องการเตรียมงานไว้ก่อนและรอ Claude พร้อมจึงเริ่ม implementation ไม่รัน worker ในรอบวางแผนนี้

## 1. สิ่งที่จะทำให้ผู้ใช้เห็น

เมื่อระบุต้นทาง ปลายทาง และวัน/เวลาเดินทาง ระบบในอนาคตจะเชื่อมเส้นทางเข้ากับพื้นที่/ช่วงถนนที่โมเดลรองรับ แล้วแสดงระดับเฝ้าระวังพร้อมคำอธิบาย ผู้ใช้แตะช่วงถนนเพื่อดูช่วงเวลาที่ทำนาย จำนวนเหตุที่คาดการณ์ ข้อมูลย้อนหลังที่เกี่ยวข้อง และความครบถ้วนของข้อมูลได้

คำว่า “จุด” ในหน้าจอหมายถึงพื้นที่/ช่วงถนนรอบจุดนั้น ไม่ใช่ทำนายพิกัดอุบัติเหตุถัดไปอย่างแม่นยำเป็นจุดเดียว วงกลมเป็นสัญลักษณ์บนแผนที่ ไม่ใช่หลักฐานว่าความเสี่ยงเท่ากันทุกตำแหน่งในรัศมีวงกลม

เป้าหมายหลักเริ่มจาก **expected recorded accident count ต่อช่วงถนน × ช่วงเวลาที่กำหนด** เป็น Regression เช่นเดียวกับงานเดิม แต่ต้องฝึกและประเมินใหม่ในหน่วยเชิงพื้นที่ใหม่ ห้ามนำค่าทำนายจังหวัดไปหารระยะทางหรือกระจายลงจุดแล้วเรียกว่าเป็นโมเดลรายจุด

## 2. สิ่งที่ตรวจจริงแล้วในรอบเตรียมงาน

เชื่อม event_uid ของ V2 กลับไปยัง lineage และข้อมูล CSV ดิบ ตรวจ source_row และ ACC_CODE ตรงกันครบ **106,308 เหตุการณ์ที่ V2 เก็บไว้ในปี 2021–2025**:

| รายการ | จำนวนที่พบ |
|---|---:|
| พิกัดเป็นตัวเลข finite และอยู่ในกรอบกว้างประเทศไทย | 106,308 |
| มีค่ารหัสสายทาง | 106,299 |
| มีค่าฟิลด์หลักกิโลเมตร | 105,991 |
| คู่พิกัดไม่ซ้ำเมื่อปัด 6 ตำแหน่งทศนิยม | 101,473 |

ตารางนี้เป็น **ชุดที่ผ่านตัวกรอง V2 แล้ว** ไม่ใช่คุณภาพพิกัดของทุกแถวใน raw การอยู่ใน bounding box ไม่ยืนยันว่าพิกัดถูกถนน ถูกจังหวัด ถูกฝั่ง หรือใช้ datum ที่ถูกต้อง การมีค่า route/KM ไม่ยืนยันว่าค่านั้นถูกต้อง/อ่านเป็นระยะทางได้ ข้อมูล V2 สำหรับฝึกจังหวัดไม่ได้เก็บ lat/lon จึงต้องสร้าง spatial lineage จาก raw ที่ตรวจ hash และ identity ก่อน

ดูหลักฐาน [coordinate_preflight.json](coordinate_preflight.json), [รายปี](coordinate_preflight_by_year.csv) และ [จังหวัดที่อาจอยู่ในแนวเส้นทางนำร่อง](candidate_corridor_preflight.csv) รายชื่อจังหวัดเป็นสมมติฐานพื้นที่ศึกษา ไม่ใช่เส้นทางที่ routing engine คำนวณแล้ว จำนวน events ในตารางเหล่านี้ยังไม่ใช่จำนวน label ที่ใช้ประเมินได้ เพราะ eligibility เดิมอาจตัดบาง province-days ออก

## 3. หน่วยพื้นที่และพื้นที่นำร่อง

**เป้าหมายผลิตภัณฑ์:** ช่วงถนนที่มี geometry และ stable segment ID เชื่อมเหตุย้อนหลังเข้าถนนจริง และสามารถตัดกับเส้นทางเดินทางได้ จุดตัด ทางแยก สะพาน ถนนคู่ขนานและทางต่างระดับต้องจัดการความกำกวม ไม่เลือกถนนที่ใกล้ที่สุดโดยไม่ตรวจรหัสสายทาง/ระยะ snap

แผนทดลองหลัง audit:

- เปรียบเทียบช่วงถนนประมาณ 0.5, 1 และ 2 กิโลเมตรในข้อมูลฝึก เลือกความละเอียดที่พิกัดและจำนวนเหตุรองรับก่อนล็อก protocol ไม่สัญญาว่าทุกจุด 100 เมตรจะประเมินได้
- ถ้ายังไม่มี road geometry ที่เชื่อมได้ ให้ทำ grid/H3 เป็น **การทดลองระดับพื้นที่** เพื่อวัดความเบาบางก่อน ไม่เรียกว่าโมเดลระดับถนน ไม่ใช้ cell centroid เป็นพิกัดเหตุที่จะเกิด
- หากใช้ H3 ให้รายงานพื้นที่จริงของ cell และ resolution; ไม่เรียกเซลล์ทั้งหมดว่ารัศมีคงที่ หากใช้กริด/ระยะทางแบบเมตรต้องเลือก CRS และตรวจ distortion หรือใช้ระยะ geodesic ห้ามคำนวณเมตรจาก degree ตรง ๆ
- เริ่ม study corridor จากแนวกรุงเทพฯ–เขาใหญ่เป็นข้อเสนอ ตรวจเส้นทางทางเลือกและขอบเขตก่อนล็อก study area รายชื่อ 6 จังหวัดใน preflight เป็นเพียง candidate envelope ไม่ใช่ถนนทุกสายในจังหวัดเหล่านั้น
- ยังต้องยืนยันสาขามหาวิทยาลัยศรีปทุมและปลายทาง/ประตูเข้าเขาใหญ่ก่อนใช้ตัวอย่างเส้นทางจริง แต่ไม่ต้องรอรายละเอียดนี้เพื่อเริ่ม audit คุณภาพข้อมูล

**หน่วยเวลา:** ตรวจความเป็นไปได้ของช่วงถนน×วันก่อน และตรวจ 6 ชั่วโมงเป็นเป้าหมายสำหรับการเดินทาง หาก sparse เกินไปให้เสนอสรุป/forecast 7 วันเป็นอีก target ที่แยกชัด ห้ามอ้างว่าโมเดล 7 วันเปลี่ยนความเสี่ยงตามชั่วโมงได้ ห้ามเลือกขนาดพื้นที่/หน่วยเวลาจากคะแนนปี diagnostic แล้วนำมารายงานเป็นผลทดสอบอิสระ

## 4. สีแปลว่าอะไร

ข้อเสนอ palette (ยังไม่ใช่เกณฑ์ที่ผ่านการทดสอบ):

| สี | ป้ายที่แสดง | ความหมาย |
|---|---|---|
| เทา | ข้อมูลไม่เพียงพอ / นอกพื้นที่รองรับ | ยังไม่จัดระดับ ไม่มีข้อมูลไม่ได้แปลว่าไม่มีอันตราย |
| ฟ้าอมเขียว | เฝ้าระวังระดับพื้นฐาน | ค่าคาดการณ์ต่ำกว่าเมื่อเทียบกับกลุ่มอ้างอิงที่กำหนด ไม่ใช้คำว่า “ปลอดภัย” |
| เหลือง | เฝ้าระวังเพิ่ม | ระดับค่าคาดการณ์สูงขึ้นในกลุ่มอ้างอิง |
| ส้ม | เฝ้าระวังสูง | ระดับค่าคาดการณ์สูง |
| แดง | เฝ้าระวังสูงมาก | ระดับค่าคาดการณ์สูงมาก ไม่ใช่คำยืนยันว่าจะเกิดเหตุ |

ตัวเลข cutoffs **ยังไม่กำหนด** ต้องคำนวณจากข้อมูลฝึก/OOF ตาม protocol แล้วล็อกพร้อม model version ตัวอย่างที่จะพิจารณาคือ quantile cutoffs ของกลุ่มอ้างอิงที่กำหนดล่วงหน้า ไม่ใช่ threshold ความปลอดภัยทางวิศวกรรม ห้ามปรับสีตามแต่ละ route/current viewport จนทุกเส้นทางต้องมีจุดแดง หาก cutoffs ซ้ำจากคะแนนเท่ากันต้องลดจำนวนระดับหรือใช้กฎที่บันทึกไว้ ไม่สร้างความแตกต่างเทียม

ต้องใช้ป้ายข้อความ/สัญลักษณ์ควบคู่สี เปรียบเทียบเฉพาะ horizon และหน่วยพื้นที่ที่เทียบกันได้ แสดง lambda และหน่วยด้วย สีไม่ปนกับความรุนแรงของการบาดเจ็บ ความมั่นใจ/ข้อมูลขาดมีสถานะแยก สีเทามี priority ก่อน color bin เมื่ออยู่นอก coverage หรือไม่มีหลักฐานรองรับ ส่วน history support ต่ำไม่ใช่เหตุให้ประกาศว่าไม่มีความเสี่ยง ต้องประเมิน fallback/pooled model สำหรับพื้นที่ใหม่ด้วย

## 5. “โอกาสเกิดอุบัติเหตุ” และ “อันตราย” ต้องแยกกัน

Regression ให้ค่าเฉลี่ยจำนวนบันทึก ไม่ได้ให้โอกาสเกิดอุบัติเหตุของรถผู้ใช้ หากจะรายงาน P(อย่างน้อย 1 เหตุใน segment/time window) ต้องมี probabilistic model/assumptions และประเมิน Brier/log loss/calibration ตามเวลาใหม่ HGB ที่ใช้ Poisson loss ให้ mean ไม่ได้ยืนยันโดยอัตโนมัติว่าจำนวนเหตุเป็น Poisson จึงห้ามนำ 1−exp(−lambda) มาแสดงเป็นเปอร์เซ็นต์จริงโดยไม่มีการตรวจนี้

แม้ทำนาย P(≥1 record) ได้ ก็ยังไม่ใช่โอกาสที่ผู้เดินทางหนึ่งคนจะชน อัตราที่ปรับ exposure ต้องมีปริมาณรถ/ระยะทางเดินทางในหน่วยถนนและเวลาเดียวกัน AADT เฉลี่ยจังหวัดเดิมใช้เป็นตัวหารรายจุดไม่ได้ จำนวนเหตุสูงอาจเกี่ยวกับจำนวนผู้ใช้ถนนมาก ไม่ได้แปลว่าโอกาสชนต่อรถสูงกว่าเสมอ

ความรุนแรง (บาดเจ็บ/เสียชีวิต) เป็นอีก outcome หนึ่ง ถ้าจะทำ severity forecast ต้องแยก target/evaluation ไม่ผสม weighted severity score ที่ตั้งน้ำหนักเองเข้ากับ count แล้วเรียกทั้งหมดว่า probability

แนวคิดการแยก crash frequency กับ exposure สอดคล้องกับ [FHWA Road Safety Fundamentals, Unit 4](https://highways.dot.gov/safety/learn-safety/road-safety-fundamentals-html-version/unit-4-solving-safety-problems) เอกสารนี้ใช้เป็นหลักวิธีการ ไม่ใช่การรับรองโมเดลของเรา

## 6. ข้อมูลที่ต้องเพิ่ม/ตรวจให้ครบ

| กลุ่ม | งานถัดไป | ข้อจำกัดที่ต้องบันทึก |
|---|---|---|
| พิกัดเหตุ + route/KM | กู้ทุก V2 UID จาก raw, ตรวจ datum/สลับ lat-lon/จุดซ้ำ/จังหวัด, ตรวจ road snapping | ไม่แก้/ขยับพิกัดเงียบ ๆ; ambiguous/unmatched ต้องมีสถานะ |
| Road inventory + geometry | หาเส้นถนนและ stable ID รวมช่วงที่ไม่มีบันทึกเหตุ, ความยาว/ประเภทถนน/ทางแยก | ต้องมี denominator ของพื้นที่ศึกษา ไม่สร้างเฉพาะจุดเคยเกิดเหตุ; WMS ภาพอย่างเดียวใช้สร้าง segment graph ไม่ได้ |
| Coverage / zero labels | แยก observed zero, unknown reporting, outside network; ทบทวน quarantine/eligibility ตามพื้นที่ | ไม่เติม NaN เป็น 0 ทุกที่ ไม่ใช้ outcome-derived eligibility เป็น feature/เงื่อนไขที่รู้ล่วงหน้า |
| Traffic | เชื่อม DOH station/route/control section/KM กับ segment ถ้าเชื่อมได้จริง และใช้ vintage as-of | ค่า station ไม่ใช่รถบนทุก segment; ไม่ทำ pseudo live congestion |
| Weather | จัดหาพยากรณ์เชิงพื้นที่พร้อม forecast issue time และ archive ที่ตรวจสอบได้ | observed weather ตอนเกิดเหตุเป็นผลประกอบย้อนหลัง ไม่ใช่ forecast feature; ไม่กระจายค่าจังหวัดแล้วอ้างว่าละเอียดรายจุด |
| Road context | ประเภทถนน/แยก/โค้งจาก geometry ที่ตรวจได้ | current geometry ไม่พิสูจน์ว่าเป็นสภาพถนนปี 2021; ต้อง audit vintage และการเปลี่ยนแปลง |
| ปฏิทิน | ใช้ festival/time/season rules เดิม และเพิ่มปฏิทินปีใหม่เมื่อมีหลักฐาน | BOT calendar เป็นวันหยุดธนาคาร ไม่เท่ากับวันหยุดทุกประเภท |
| Historical explanations | กู้ประเภทเหตุ/สาเหตุ/เวลาจาก raw แบบตรวจ identity ได้ ใช้เฉพาะประวัติก่อน cutoff ที่อ้าง | “มูลเหตุสันนิษฐาน” ไม่ใช่เหตุที่พิสูจน์แล้ว; sample น้อยต้องบอก n และ unknown |

แหล่งที่ตรวจ metadata แล้ว: [MOT แผนที่โครงข่ายถนนในความรับผิดชอบ](https://datagov.mot.go.th/th/dataset/transportgis) ระบุบริการ WMS ต้องตรวจต่อว่ามี vector/API ดาวน์โหลดและสิทธิ์ใช้ที่เหมาะสมหรือไม่ ยังไม่ได้ดาวน์โหลดหรือรับรอง geometry หากใช้ OSM เป็นทางเลือกให้บันทึก snapshot/coverage และ [attribution/ODbL ของ OSM](https://www.openstreetmap.org/copyright?locale=en-GB) ไม่เรียก OSM ว่าเป็นโครงข่ายครบถ้วนของแหล่งรายงาน MOT; [H3 cell statistics](https://h3geo.org/docs/core-library/restable/) ใช้ตรวจขนาดพื้นที่ตาม resolution

## 7. โมเดลและการทดสอบที่จะต้องทำใหม่

- ทดสอบ 3 ตระกูลเดิมใหม่บน spatial labels: Poisson Regression, Random Forest (Poisson), HGB (Poisson) HGB จังหวัดไม่ถือว่าชนะรายจุดล่วงหน้า
- Baselines: zero (รายงาน tradeoff), train-only global/road-type mean, smoothed segment/time mean พร้อม fallback ในจุดไม่เคยเกิดเหตุ ห้ามใช้ full-period history หรือ DBSCAN hotspot ที่ fit รวมปีหลังในการสร้าง feature/ขอบเขตฝึก
- ตรวจ zero proportion, support ต่อพื้นที่/เวลา, overdispersion, coordinate uncertainty ก่อนเลือกความละเอียด หากต้องเพิ่ม Negative Binomial/hierarchical model ให้เพิ่มใน protocol ก่อนดูผล ไม่อ้างว่าได้ทดลองแล้ว
- แยกสองคำถาม: future performance บนถนนเดิมใช้ expanding chronological folds; การถ่ายโอนไปถนน/พื้นที่ใหม่ใช้ spatial group holdout พร้อม buffer ที่กำหนดจาก training เท่านั้น ไม่ random split แถวใกล้กันข้าม train/test
- สร้าง road universe โดยไม่เลือกเฉพาะพื้นที่ที่เคยเกิดเหตุในอนาคต; target bins/normalization/imputation/feature selection fit เฉพาะ training ของ fold และ guard ทุก source ด้วย available_at <= issue_time
- คงปี 2024/2025 เป็น seen diagnostics, ปี 2026 ที่ไม่มี ID ไม่เลื่อนเป็น ground truth ใหม่ การมี spatial split ไม่ได้ล้างประวัติว่าเคยเห็นข้อมูลแล้ว
- Metrics หลัก mean Poisson deviance พร้อม MAE/RMSE/signed bias, calibration ของ count, error แยกเทศกาล/กลางวันกลางคืน/ถนนใหม่/coverage และ top-k recorded-event capture เทียบ baseline บน budget พื้นที่หรือความยาวถนนเท่ากัน ไม่ใช้ accuracy แบบ classification แทน regression
- ระดับสีประเมินความเป็นลำดับของ observed count บนกลุ่มประเมิน, stability/coverage และ calibration แยกจาก count loss; ถ้าเป็น quantile-relative ให้เรียก relative alert level ไม่ใช่ระดับความปลอดภัยที่รับรองแล้ว ขอบเขตสีของแต่ละ evaluation fold ต้อง fit จาก training ก่อน fold นั้น
- ถ้าไม่ชนะ strongest baseline อย่างน่าเชื่อถือ ให้เลือก baseline หรือปรับเป้าหมายที่ protocol รอบถัดไปอนุญาต ไม่แต่งคะแนน/บังคับให้ HGB ชนะ และไม่อ้างผล V2 7.16%/3.99% ว่าเป็นผลงานรายจุด

## 8. API contract ที่ต้องเตรียมหลังผ่าน spatial audit

ร่างผลลัพธ์ต่อ segment/area (ยังไม่ใช่ endpoint ที่ใช้งานได้): segment_id, geometry, spatial_unit/version, target_start/end/timezone, issued_at, expected_recorded_count, alert_level/label/color, color_threshold_version/reference_population, coverage_status/reasons, model_version, historical_summary พร้อมช่วงปี/n/unknown และแหล่งข้อมูล

ห้ามมี injury_probability หรือ personal_crash_probability ถ้ายังไม่มีโมเดลรองรับ; uncertainty interval มีได้เฉพาะวิธีที่ทดสอบ coverage แล้ว ห้ามแต่ง +/-20%; ปล่อย null พร้อมเหตุผลได้ สำหรับเส้นทางให้ส่ง geometry เข้า spatial join เพื่อคืนเฉพาะช่วงที่รองรับ ไม่บวกความน่าจะเป็นรายจุดเป็นโอกาสชนตลอดเส้นทาง และไม่ใช้ ETA รายชั่วโมงกับ daily model โดยไม่อธิบายความละเอียด

ต้องแยก layer ประวัติย้อนหลังกับ layer พยากรณ์อนาคต ส่วนคำแนะนำให้ผูกกับประวัติที่มี support และหลักความปลอดภัยที่ตรวจอ้างอิงได้ ไม่สร้างข้อกล่าวอ้างสดว่า “ฝนกำลังตก/รถกำลังติด” จากประวัติเก่า เมื่อเปลี่ยนเส้นทาง/วันเวลาให้คง color reference เดิมเพื่อให้เปรียบเทียบได้

## 9. ลำดับงานเมื่อ Claude พร้อม

1. **เริ่ม [task 012: Spatial Data Readiness](../tasks/012-spatial-data-readiness.md)** — สร้าง notebook audit และรายงาน feasibility ก่อน ยังไม่ fit โมเดล ไม่มี frontend
2. Codex ตรวจ notebook/lineage/geometry/zero-policy จริง แล้วจัดและล็อก spatial protocol/config ในงานแยก กำหนด study area, unit/horizon, folds, baselines, feature/as-of, selection/color gates และ resource budget
3. Claude สร้าง preparation → model experiments → evaluation/error analysis → spatial serving เป็น notebook แยก และ Codex รันตรวจทุกช่วง ผลรายจุดเก็บ V3 แยกจาก V2
4. ปรับงาน API/catalog 009a ให้มีขอบเขตจังหวัดและ spatial แยกชัด หลังมี spatial contract ที่ผ่านตรวจแล้ว งาน 009a ยังเป็นงานค้าง ไม่ลบทิ้ง ไม่ถือว่าเสร็จเพราะมีแผนนี้
5. ทดสอบ API จริง/GeoJSON/การเลือกพื้นที่/unknown behavior และจัดเอกสาร ก่อนเริ่ม frontend/mobile และ routing UX

ตอนนี้ห้ามเริ่มฝึก/สร้างสีตัวเลข/ซื้อบริการ/ทำหน้าเว็บอัตโนมัติ ข้อความร่างเหล่านี้เป็นข้อเสนอที่รอผล audit ไม่ใช่ผลทดลอง พอ Claude พร้อมเริ่ม 012 ได้โดยไม่ต้องถามยืนยันรายละเอียดเดิมซ้ำ งานบางส่วนอาจติด **login** แยกจาก **quota reset**: รอบล่าสุดของ bridge ตอบ Not logged in จึงต้องตรวจสถานะบัญชีด้วยก่อนเริ่ม worker
