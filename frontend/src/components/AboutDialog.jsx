// "ข้อมูลนี้มาจากไหน" — how RoadAware works and how far to trust it, in plain words.
import { useEffect, useRef } from "react";
import { LEVELS, UNKNOWN_HEX, ROUTE_HEX } from "../config.js";

const STEPS = [
  { title: "เก็บข้อมูลอุบัติเหตุจริง", text: "นำบันทึกอุบัติเหตุบนทางหลวงย้อนหลังตั้งแต่ปี 2564 มาวางบนแผนที่ แล้วแบ่งทางหลวงทั้งประเทศเป็นช่วงสั้น ๆ ช่วงละประมาณ 2 กม." },
  { title: "ให้คอมพิวเตอร์เรียนรู้", text: "ใช้ Machine Learning หาว่าช่วงถนนแบบไหน วันไหน และเวลาไหน มักเกิดอุบัติเหตุบ่อย โดยดูวันหยุด เทศกาล สภาพอากาศ และปริมาณรถประกอบด้วย" },
  { title: "คาดการณ์ให้ทริปของคุณ", text: "เมื่อคุณเลือกเส้นทางและเวลาออกเดินทาง ระบบคำนวณว่าคุณจะผ่านแต่ละช่วงตอนกี่โมง แล้วชี้ช่วงที่ควรระวังที่สุดในเวลานั้น" },
];

const LIMITS = [
  "ครอบคลุมเฉพาะทางหลวงของกรมทางหลวง ถนนในเมือง ถนนชนบท และทางด่วนยังไม่มีข้อมูล",
  "สีคือการเทียบกับถนนเส้นอื่น ไม่ใช่โอกาสที่คุณจะเกิดอุบัติเหตุ ช่วงที่ไม่มีหมายเลขก็ไม่ได้แปลว่าปลอดภัย",
  "“ส่วนใหญ่เกิดจาก” สรุปจากรายงานอุบัติเหตุที่ผ่านมาของจุดนั้น ไม่ได้พิสูจน์สาเหตุ และไม่ใช่สภาพอากาศวันที่คุณเดินทาง",
  "ระยะทางและเวลาขับเป็นค่าประมาณ ยังไม่รวมรถติดจริง",
  "ใช้วางแผนก่อนออกเดินทาง ไม่ใช่ระบบแจ้งเตือนเหตุแบบเรียลไทม์",
];

const SOURCES = [
  ["ข้อมูลอุบัติเหตุ · กระทรวงคมนาคม", "https://datagov.mot.go.th/dataset/roadaccident"],
  ["ข้อมูลถนน · Transport GIS", "https://datagov.mot.go.th/th/dataset/transportgis"],
  ["ปริมาณจราจร · กรมทางหลวง", "https://opendata.doh.go.th/dataset/ed101df4-f0a1-4d7f-b9d9-76859b2ca73e"],
  ["สภาพอากาศ · Open-Meteo", "https://open-meteo.com/"],
  ["แผนที่ · OpenStreetMap", "https://www.openstreetmap.org/copyright"],
  ["ค้นหาสถานที่ · Photon", "https://photon.komoot.io/"],
  ["คำนวณเส้นทาง · OSRM", "https://project-osrm.org/"],
  ["ขอบเขตประเทศ · geoBoundaries", "https://www.geoboundaries.org/"],
];

const Ext = () => <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M7 17 17 7M9 7h8v8" /></svg>;

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
        <div>
          <h2 id="aboutTitle">ข้อมูลนี้มาจากไหน</h2>
          <p className="about-lead">สรุปสั้น ๆ ว่า RoadAware คิดผลมาจากอะไร และควรอ่านผลอย่างไร</p>
        </div>
        <button type="button" className="icon-btn" aria-label="ปิด" onClick={onClose}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18" /></svg>
        </button>
      </div>

      <div className="about-body">
        <section className="about-sec">
          <h3>ระบบทำงานอย่างไร</h3>
          <ol className="about-steps">
            {STEPS.map((s, i) => (
              <li key={s.title}><span className="about-n">{i + 1}</span><div><b>{s.title}</b><p>{s.text}</p></div></li>
            ))}
          </ol>
        </section>

        <section className="about-sec about-trust">
          <h3>เชื่อถือได้แค่ไหน</h3>
          <p>เราฝึกโมเดลด้วยข้อมูลปี 2564–2566 ตรวจกับปี 2567–2568 แล้ว<b>ทดสอบจริงกับปี 2569</b> ซึ่งโมเดลไม่เคยเห็นมาก่อน</p>
          <div className="about-stats">
            <div><b>ทุกเดือน</b><span>ทายได้ดีกว่าวิธีเปรียบเทียบพื้นฐาน (ม.ค.–ก.ย. 2569)</span></div>
            <div><b>~30%</b><span>คลาดเคลื่อนน้อยลงช่วงสงกรานต์และปีใหม่ ซึ่งเป็นช่วงที่สำคัญที่สุด</span></div>
          </div>
        </section>

        <section className="about-sec">
          <h3>อ่านแผนที่อย่างไร</h3>
          <ul className="about-key">
            <li><span className="about-pin" style={{ background: LEVELS.red.hex }}>1</span><div><b>หมายเลขสีแดง</b><small>จุดที่ควรระวังมาก อยู่ใน 5% บนสุดของถนนทั้งประเทศ</small></div></li>
            <li><span className="about-pin" style={{ background: LEVELS.orange.hex }}>2</span><div><b>หมายเลขสีส้ม</b><small>จุดที่ควรระวัง อยู่ในกลุ่ม 5–20% บนสุด</small></div></li>
            <li><span className="about-line" style={{ background: ROUTE_HEX }} /><div><b>เส้นสีน้ำเงิน</b><small>ทางหลวงที่ระบบประเมินแล้ว</small></div></li>
            <li><span className="about-line" style={{ background: UNKNOWN_HEX }} /><div><b>เส้นสีเทา</b><small>ถนนที่ยังไม่มีข้อมูล (ไม่ได้แปลว่าปลอดภัย)</small></div></li>
          </ul>
        </section>

        <section className="about-sec">
          <h3>สิ่งที่ควรรู้</h3>
          <ul className="about-limits">
            {LIMITS.map((t) => <li key={t}>{t}</li>)}
          </ul>
        </section>

        <section className="about-sec">
          <h3>ข้อมูลและบริการที่ใช้</h3>
          <div className="about-src">
            {SOURCES.map(([name, url]) => <a key={url} href={url} target="_blank" rel="noopener noreferrer">{name}<Ext /></a>)}
          </div>
        </section>

        <p className="about-foot">RoadAware เป็นโครงงานเพื่อการศึกษาระดับมหาวิทยาลัย</p>
      </div>
    </dialog>
  );
}
