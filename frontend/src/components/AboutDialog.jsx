// "ข้อมูลนี้มาจากไหน" — all transparency in one place instead of warnings on every card.
import { useEffect, useRef } from "react";
import { LEVELS, LEVEL_ORDER, UNKNOWN_HEX, ROUTE_HEX, HOT_HEX } from "../config.js";

export default function AboutDialog({ open, onClose }) {
  const ref = useRef(null);
  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (open && !d.open) { try { d.showModal(); } catch (_) { d.setAttribute("open", ""); } }
    if (!open && d.open) d.close();
  }, [open]);
  return (
    <dialog ref={ref} className="about" onClose={onClose} onCancel={onClose} aria-labelledby="aboutTitle">
      <div className="about-head">
        <h2 id="aboutTitle">ข้อมูลนี้มาจากไหน</h2>
        <button type="button" className="icon-btn" aria-label="ปิด" onClick={onClose}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18" /></svg>
        </button>
      </div>
      <div className="about-body">
        <p className="about-lead">เราบอกตรง ๆ ว่าระบบรู้อะไรและไม่รู้อะไร เพื่อให้คุณตัดสินใจได้เอง</p>
        <div className="about-grid">
          <div>
            <h3>ข้อมูลที่ใช้</h3>
            <p>บันทึกอุบัติเหตุบนทางหลวงปี 2564–2568 ที่เชื่อมกับช่วงถนนยาวราว 2 กม. ร่วมกับปฏิทิน ฤดูกาล และปริมาณจราจรเฉลี่ยรายปี</p>
          </div>
          <div>
            <h3>แบบจำลอง</h3>
            <p>ใช้ HistGradientBoosting (ตัวที่ชนะเมื่อเทียบ Poisson Regression, Random Forest และ HistGradientBoosting ในพื้นที่นำร่อง) และต้องชนะค่าพื้นฐานตามเกณฑ์ที่ล็อกไว้ก่อนทดลอง ตรวจกับช่วงข้อมูลที่ไม่ได้ใช้ฝึก ผลประเมินเป็นการคาดจำนวนเหตุที่จะถูกบันทึกในช่วง 6 ชั่วโมง</p>
          </div>
          <div>
            <h3>พื้นที่ที่ครอบคลุม</h3>
            <p>ประเมินได้บนทางหลวงกรมทางหลวงทั่วประเทศ 26,740 ช่วง (ยาวรวมราว 51,900 กม.) ถนนชนบท ทางพิเศษ และถนนในเมืองยังไม่มีข้อมูล ส่วนนั้นของเส้นทางแสดงเป็นเส้นสีเทาอ่อน “ถนนท้องถิ่น (ยังไม่ประเมิน)” และบอกเปอร์เซ็นต์ที่ประเมินได้ทุกครั้ง</p>
          </div>
          <div>
            <h3>สิ่งที่ระดับสีไม่ได้บอก</h3>
            <p>ระดับคือการจัดอันดับเทียบกับช่วงถนนอื่น ไม่ใช่โอกาสที่คุณจะเกิดอุบัติเหตุ ระดับ “ปกติ” ไม่ได้แปลว่าปลอดภัย ไม่มีการรวมค่าหลายช่วงเป็น “ความเสี่ยงของเส้นทาง”</p>
          </div>
        </div>
        <h3>อ่านแผนที่ยังไง</h3>
        <ul className="about-levels">
          <li><i style={{ background: HOT_HEX }} />หมายเลข 1–5 (มุมมอง “จุดเสี่ยงของทริป”) — ช่วงที่ค่าคาดสูงที่สุดของเส้นทางนี้ ในเวลาที่คุณผ่าน (20% บนสุดของทริป และระดับประเทศ “สูง” ขึ้นไป)</li>
          <li><i style={{ background: ROUTE_HEX }} />เส้นสีน้ำเงิน — ช่วงที่ประเมินแล้ว สีอ่อน → เข้ม = ครึ่งล่าง / กลาง / 20% บนสุดของทริปนี้</li>
          <li><i style={{ background: UNKNOWN_HEX }} />ถนนท้องถิ่น / ในเมือง — เส้นสีเทาอ่อน ยังไม่ประเมิน (ไม่ได้แปลว่าปลอดภัย)</li>
        </ul>
        <h3>ระดับเทียบทั้งประเทศ (มุมมอง “เทียบทั้งประเทศ”)</h3>
        <ul className="about-levels">
          {LEVEL_ORDER.map((k) => (
            <li key={k}><i style={{ background: LEVELS[k].hex }} />{LEVELS[k].label} — {LEVELS[k].nat} ของช่วงถนน × ช่วงเวลาทั่วประเทศ (ปี 2565–66)</li>
          ))}
        </ul>
        <h3>“ส่วนใหญ่เกิดจาก” และคำแนะนำ</h3>
        <p>มาจากหมวดที่บันทึกไว้ในรายงานอุบัติเหตุของช่วงถนนนั้น (ลักษณะเหตุ สภาพอากาศขณะเกิดเหตุ สาเหตุที่สันนิษฐาน) ไม่ใช่การพิสูจน์สาเหตุ และไม่ใช่สภาพอากาศวันเดินทาง คำแนะนำเป็นข้อแนะนำทั่วไปจากลักษณะเหตุที่พบบ่อย</p>
        <h3>บริการภายนอก</h3>
        <p>แผนที่ © ผู้ร่วมพัฒนา OpenStreetMap · ค้นหาสถานที่ Photon (komoot) · เส้นทาง OSRM · ขอบเขตประเทศ geoBoundaries (CC BY 4.0) · Natural Earth ระยะทางและเวลาขับไม่รวมสภาพจราจรจริง</p>
        <p className="fine">RoadAware เป็นต้นแบบงานวิจัย (production_ready = false) ใช้เพื่อเตรียมตัวและวางแผนก่อนเดินทาง ไม่ใช่ระบบเตือนภัยแบบเรียลไทม์</p>
      </div>
    </dialog>
  );
}
