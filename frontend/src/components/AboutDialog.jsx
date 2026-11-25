// "ข้อมูลนี้มาจากไหน" — all transparency in one place instead of warnings on every card.
import { useEffect, useRef } from "react";
import { LEVELS, UNKNOWN_HEX, ROUTE_HEX, HOT_HEX } from "../config.js";

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
            <p>บันทึกอุบัติเหตุบนทางหลวงที่จับคู่กับช่วงถนนยาวราว 2 กม. ร่วมกับวันและเวลา ฤดูกาล เทศกาลสงกรานต์และปีใหม่ สภาพอากาศ และปริมาณจราจรเฉลี่ยรายปี</p><p>ฝึกแบบจำลองด้วยปี 2564–2566 · ตรวจกับปี 2567–2568 · ทดสอบกับปี 2569 (ม.ค.–ก.ย.) ที่แบบจำลองไม่เคยเห็น · สถิติ “ที่ผ่านมา” ของแต่ละจุดใช้ปี 2564–2568</p>
          </div>
          <div>
            <h3>แบบจำลอง</h3>
            <p>HistGradientBoosting คาดจำนวนเหตุที่จะถูกบันทึกของแต่ละช่วงถนน ในช่วง 6 ชั่วโมงที่คุณจะผ่าน ต้องชนะค่าพื้นฐานตามเกณฑ์ที่ล็อกไว้ก่อนทดลอง</p><p>กับข้อมูลปี 2569 ทำได้ดีกว่าค่าพื้นฐานทุกเดือน (ดีกว่า 13.5% และช่วงสงกรานต์–ปีใหม่ดีกว่า 29–32%)</p>
          </div>
          <div>
            <h3>พื้นที่ที่ครอบคลุม</h3>
            <p>ประเมินได้บนทางหลวงกรมทางหลวงทั่วประเทศ 26,740 ช่วง (ยาวรวมราว 51,900 กม.) ถนนชนบท ทางพิเศษ และถนนในเมืองยังไม่มีข้อมูล ส่วนนั้นของเส้นทางแสดงเป็นเส้นสีเทา</p>
          </div>
          <div>
            <h3>สิ่งที่ระดับสีไม่ได้บอก</h3>
            <p>ระดับคือการจัดอันดับเทียบกับช่วงถนนอื่น ไม่ใช่โอกาสที่คุณจะเกิดอุบัติเหตุ ช่วงที่ระดับต่ำหรือไม่มีหมายเลขก็ไม่ได้แปลว่าปลอดภัย ไม่มีการรวมค่าหลายช่วงเป็น “ความเสี่ยงของเส้นทาง”</p>
          </div>
        </div>
        <h3>อ่านแผนที่ยังไง</h3>
        <ul className="about-levels">
          <li><i style={{ background: LEVELS.red.hex }} />หมายเลขสีแดง — จุดที่ควรระวัง ระดับสูงมาก (5% บนสุดของประเทศ)</li>
          <li><i style={{ background: LEVELS.orange.hex }} />หมายเลขสีส้ม — จุดที่ควรระวัง ระดับสูง (5–20% บนสุด) · หมายเลขขึ้นเฉพาะช่วงที่ค่าคาดสูงที่สุดของเส้นทางในเวลาที่คุณผ่าน</li>
          <li><i style={{ background: ROUTE_HEX }} />เส้นสีน้ำเงิน — ทางหลวงที่ประเมินแล้ว</li>
          <li><i style={{ background: UNKNOWN_HEX }} />เส้นสีเทา — ถนนท้องถิ่น / ในเมืองที่ยังไม่มีข้อมูล (ไม่ได้แปลว่าปลอดภัย)</li>
        </ul>
        <h3>“ส่วนใหญ่เกิดจาก” และคำแนะนำ</h3>
        <p>มาจากหมวดที่บันทึกไว้ในรายงานอุบัติเหตุของช่วงถนนนั้น (ลักษณะเหตุ สภาพอากาศขณะเกิดเหตุ สาเหตุที่สันนิษฐาน) ไม่ใช่การพิสูจน์สาเหตุ และไม่ใช่สภาพอากาศวันเดินทาง คำแนะนำเป็นข้อแนะนำทั่วไปจากลักษณะเหตุที่พบบ่อย</p>
        <h3>ข้อมูลและบริการที่นำมาใช้</h3>
        <p>โครงงานนี้นำข้อมูลและบริการแบบเปิดต่อไปนี้มาใช้ในการพัฒนาและศึกษา:</p>
        <ul>
          <li>แผนที่ — OpenStreetMap (© OpenStreetMap contributors, ODbL)</li>
          <li>ค้นหาสถานที่ — Photon (komoot)</li>
          <li>คำนวณเส้นทาง — OSRM (ระยะทางและเวลาขับไม่รวมสภาพจราจรจริง)</li>
          <li>ขอบเขตประเทศ — geoBoundaries (CC BY 4.0) และ Natural Earth</li>
        </ul>
        <p className="fine">RoadAware เป็นโครงงานเพื่อการศึกษาในระดับมหาวิทยาลัย ใช้เพื่อเตรียมตัวและวางแผนก่อนเดินทาง ไม่ใช่ระบบเตือนภัยแบบเรียลไทม์</p>
      </div>
    </dialog>
  );
}
