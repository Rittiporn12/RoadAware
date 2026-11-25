// Home page shown before the app: what RoadAware is, how to use it, how well it works, who made it.
// "เริ่มใช้งาน" opens the app at #/app (main.jsx switches pages on the hash). Works on phone, tablet and desktop.
import { useEffect, useRef, useState } from "react";
import { CONFIG, LEVELS, ROUTE_HEX, UNKNOWN_HEX, discoverServer } from "../config.js";

const goApp = () => { window.location.hash = "#/app"; };

function Logo({ size = 30 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 26 26" aria-hidden="true">
      <circle cx="13" cy="13" r="12" fill="#0F1B2D" />
      <path d="M7 18 C10 12, 13 15, 19 7" stroke="#E8821E" strokeWidth="2.6" fill="none" strokeLinecap="round" />
    </svg>
  );
}

// Is the demo server (the presenter's Mac) answering right now?
function useServerStatus() {
  const [status, setStatus] = useState("checking");
  useEffect(() => {
    let alive = true;
    (async () => {
      const d = await discoverServer();
      if (d.offline) { if (alive) setStatus("offline"); return; }
      try {
        const ctrl = new AbortController();
        const t = setTimeout(() => ctrl.abort(), 8000);
        const r = await fetch(CONFIG.apiBase + "/ready", { signal: ctrl.signal, cache: "no-store" });
        clearTimeout(t);
        if (alive) setStatus(r.ok ? "online" : "offline");
      } catch (_) { if (alive) setStatus("offline"); }
    })();
    return () => { alive = false; };
  }, []);
  return status;
}

const STATUS_TEXT = {
  checking: "กำลังตรวจสอบเซิร์ฟเวอร์…",
  online: "เซิร์ฟเวอร์พร้อมใช้งาน",
  offline: "เซิร์ฟเวอร์ปิดอยู่ — เปิดเฉพาะช่วงนำเสนอ",
};

// Original illustration of the app: a route with numbered points and a spoken warning.
function HeroPreview() {
  return (
    <div className="ld-preview" aria-hidden="true">
      <div className="ld-map">
        <svg viewBox="0 0 400 300" preserveAspectRatio="xMidYMid slice">
          <rect width="400" height="300" fill="#E9ECE6" />
          <path d="M-10 70 C80 60, 120 110, 210 90 S 360 40, 420 60" stroke="#fff" strokeWidth="7" fill="none" />
          <path d="M60 -10 C70 80, 40 160, 90 310" stroke="#fff" strokeWidth="5" fill="none" />
          <path d="M300 -10 C280 90, 330 200, 310 310" stroke="#fff" strokeWidth="5" fill="none" />
          <circle cx="330" cy="230" r="46" fill="#D7E5CF" />
          <circle cx="120" cy="40" r="30" fill="#D7E5CF" />
          <path d="M50 250 C110 230, 130 180, 190 170 S 290 120, 340 60" stroke="#fff" strokeWidth="12" fill="none" strokeLinecap="round" />
          <path d="M50 250 C110 230, 130 180, 190 170 S 290 120, 340 60" stroke={ROUTE_HEX} strokeWidth="6" fill="none" strokeLinecap="round" />
          <path d="M150 186 C165 178, 175 173, 190 170" stroke={LEVELS.red.hex} strokeWidth="7" fill="none" strokeLinecap="round" />
          <path d="M282 112 C292 100, 300 92, 308 86" stroke={LEVELS.orange.hex} strokeWidth="7" fill="none" strokeLinecap="round" />
          <g><circle cx="50" cy="250" r="11" fill="#0B6E69" stroke="#fff" strokeWidth="3" /><text x="50" y="254.5" textAnchor="middle" fontSize="12" fontWeight="700" fill="#fff">A</text></g>
          <g><circle cx="340" cy="60" r="11" fill="#E8821E" stroke="#fff" strokeWidth="3" /><text x="340" y="64.5" textAnchor="middle" fontSize="12" fontWeight="700" fill="#fff">B</text></g>
          <g><circle cx="170" cy="176" r="14" fill={LEVELS.red.hex} stroke="#fff" strokeWidth="3" /><text x="170" y="181" textAnchor="middle" fontSize="14" fontWeight="700" fill="#fff">1</text></g>
          <g><circle cx="295" cy="98" r="14" fill={LEVELS.orange.hex} stroke="#fff" strokeWidth="3" /><text x="295" y="103" textAnchor="middle" fontSize="14" fontWeight="700" fill="#fff">2</text></g>
        </svg>
      </div>
      <div className="ld-float ld-float-brief">
        <span className="ld-float-n">2</span>
        <span><b>จุดที่ควรระวัง</b><small>สูงมาก 1 จุด · สูง 1 จุด</small></span>
      </div>
      <div className="ld-float ld-float-voice">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M11 5 6 9H3v6h3l5 4z" /><path d="M15.5 8.5a5 5 0 0 1 0 7" /><path d="M18.5 5.5a9 9 0 0 1 0 13" /></svg>
        <span>“ระวัง! อีก 500 เมตร ถึงจุดที่ 1”</span>
      </div>
    </div>
  );
}

const Icon = {
  route: <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="6" cy="19" r="2.5" /><circle cx="18" cy="5" r="2.5" /><path d="M8.5 19H16a3.5 3.5 0 0 0 0-7H8a3.5 3.5 0 0 1 0-7h7.5" /></svg>,
  drive: <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 11 12 3l9 8" /><path d="M12 3v18" /><path d="M7 21h10" /></svg>,
  review: <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 12a9 9 0 1 0 3-6.7" /><path d="M3 4v5h5" /><path d="M12 7v5l3 2" /></svg>,
  arrow: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M13 6l6 6-6 6" /></svg>,
};

const FEATURES = [
  { icon: Icon.route, title: "วางแผนเดินทาง", text: "ใส่ต้นทาง ปลายทาง และเวลาออกเดินทาง ระบบชี้ช่วงทางหลวงที่ควรระวังที่สุดในเวลาที่คุณจะผ่าน พร้อมแนะนำเวลาออกหรือเส้นทางอื่นที่เสี่ยงน้อยกว่า" },
  { icon: Icon.drive, title: "โหมดขับขี่", text: "ติดตามตำแหน่งระหว่างขับ และพูดเตือนเป็นภาษาไทยก่อนถึงแต่ละจุด เช่น “ระวัง! อีก 500 เมตร ถึงจุดที่ 2” โดยไม่ต้องละสายตาจากถนน" },
  { icon: Icon.review, title: "ย้อนดูผล", text: "เลือกเส้นทางกับช่วงเวลาในอดีต เช่น สงกรานต์ 2569 แล้วดูว่าเหตุที่เกิดจริงตกอยู่ในจุดที่โมเดลชี้กี่ครั้ง เทียบกับการสุ่ม" },
];

const STEPS = [
  { title: "ใส่ต้นทางและปลายทาง", text: "พิมพ์ชื่อสถานที่ กดเลือกบนแผนที่ หรือใช้ “ตำแหน่งของฉัน” เป็นจุดเริ่มต้น" },
  { title: "เลือกวันและเวลาออกเดินทาง", text: "ความเสี่ยงเปลี่ยนตามวัน ช่วงเวลา และเทศกาล ระบบคิดให้ตามเวลาที่คุณจะผ่านแต่ละช่วงจริง" },
  { title: "ดูจุดที่ควรระวัง", text: "หมุดหมายเลขบนแผนที่คือจุดเด่นที่สุดของทริป แตะเพื่อดูรายละเอียดและเหตุที่เคยเกิด" },
  { title: "เริ่มขับ", text: "กด “เริ่มขับ” เพื่อเปิดเสียงเตือนล่วงหน้า (มือถือต้องอนุญาตตำแหน่ง)" },
];

const FLOW = [
  { title: "รวบรวมข้อมูล", text: "อุบัติเหตุ ถนน อากาศ จราจร ปฏิทิน" },
  { title: "คัดเลือกและจับคู่", text: "จับเหตุเข้ากับช่วงถนน แบ่งช่วงปี" },
  { title: "ฝึกโมเดล", text: "คาดจำนวนเหตุต่อช่วงถนน" },
  { title: "API", text: "คำนวณตามเส้นทางและเวลา" },
  { title: "เว็บแอป", text: "แผนที่ จุดที่ควรระวัง เสียงเตือน" },
];

const TECH = [
  {
    title: "ข้อมูลที่ใช้",
    items: [
      ["อุบัติเหตุทางถนน", "ข้อมูลเปิดของกระทรวงคมนาคม ปี 2564–2569"],
      ["ถนน", "ทางหลวงของกรมทางหลวง แบ่งเป็น 26,740 ช่วง (ช่วงละราว 2 กม.) รวมราว 51,900 กม."],
      ["สภาพอากาศ", "ปริมาณฝนและอากาศรายวัน จาก Open-Meteo"],
      ["ปริมาณจราจร", "ปริมาณจราจรเฉลี่ยรายปี (AADT) ของทางหลวง"],
      ["ปฏิทิน", "วันในสัปดาห์ ช่วงเวลา วันหยุด เทศกาลสงกรานต์และปีใหม่"],
    ],
  },
  {
    title: "การคัดเลือกข้อมูล",
    items: [
      ["จับคู่กับถนน", "ใช้เฉพาะเหตุบนทางหลวงที่มีพิกัด และอยู่ห่างช่วงถนนไม่เกิน 50 ม. ได้ 98,207 รายการ (2564–2568) ตัดรายการซ้ำและกำกวมออก"],
      ["ข้อมูลฝึก", "ปี 2564–2566 (ตัดที่ 1 ธ.ค. 2566)"],
      ["ข้อมูลตรวจ", "ปี 2567–2568 ไม่ได้ใช้ฝึก"],
      ["ข้อมูลทดสอบ", "ปี 2569 (ม.ค.–ก.ย.) 15,425 รายการ ที่โมเดลไม่เคยเห็น"],
      ["เลือกโมเดล", "ทดสอบย้อนหลัง 4 รอบในปี 2565–2566 เทียบค่าพื้นฐาน ตามเกณฑ์ที่กำหนดไว้ก่อนทดลอง"],
    ],
  },
  {
    title: "โมเดล",
    items: [
      ["อัลกอริทึม", "HistGradientBoosting (scikit-learn) แบบ Poisson regression คาดจำนวนอุบัติเหตุที่จะถูกบันทึกต่อช่วงถนน"],
      ["ระดับเวลา", "2 โมเดล: รายวัน และราย 6 ชั่วโมง"],
      ["ตัวแปร", "รูปทรงและตำแหน่งถนน ปฏิทินและเทศกาล อากาศย้อนหลัง ปริมาณจราจร (33–41 ตัว)"],
      ["ส่วนหลัก / ส่วนเสริม", "ใช้ตัวแปรถนน + ปฏิทินเสมอ และเพิ่มอากาศ / จราจรเมื่อมีข้อมูลของช่วงนั้น"],
      ["ระดับสี", "เทียบกับทุกช่วงถนน × ช่วงเวลาทั่วประเทศ: สูงมาก = 5% บนสุด · สูง = 5–20%"],
    ],
  },
  {
    title: "เครื่องมือและบริการ",
    items: [
      ["วิเคราะห์และฝึกโมเดล", "Python · pandas · scikit-learn · Jupyter"],
      ["เซิร์ฟเวอร์", "FastAPI"],
      ["หน้าเว็บ", "React · Vite · Leaflet"],
      ["แผนที่และเส้นทาง", "OpenStreetMap · Photon (ค้นหาสถานที่) · OSRM (คำนวณเส้นทาง) · geoBoundaries / Natural Earth (ขอบเขตประเทศ)"],
      ["เสียงเตือน", "เสียง Siri บน Mac · Gemini TTS · เสียงภาษาไทยของเบราว์เซอร์"],
      ["เผยแพร่", "GitHub Pages · Cloudflare Tunnel"],
    ],
  },
];

const TEAM = [
  ["66088346", "นายฤทธิพร ผึ่งผาย"],
  ["66088226", "นายกันณพิช เบ้าศรี"],
  ["66080740", "นางสาววรรณษา วงค์ดี"],
  ["66092559", "นายจริยธรรม มาสงค์"],
];

export default function Landing() {
  const status = useServerStatus();
  const rootRef = useRef(null);
  const scrollTo = (id) => { const el = document.getElementById(id); if (el) el.scrollIntoView({ behavior: "smooth", block: "start" }); };
  useEffect(() => { document.title = "RoadAware — รู้ก่อนออกเดินทาง ว่าช่วงไหนควรระวัง"; }, []);

  return (
    <div className="landing" ref={rootRef}>
      <header className="ld-nav">
        <div className="ld-wrap ld-nav-in">
          <a className="ld-brand" href="#/" onClick={(e) => { e.preventDefault(); rootRef.current && rootRef.current.scrollTo({ top: 0, behavior: "smooth" }); }}>
            <Logo /> <span>RoadAware</span>
          </a>
          <nav className="ld-links" aria-label="เมนู">
            <button type="button" onClick={() => scrollTo("ld-features")}>ความสามารถ</button>
            <button type="button" onClick={() => scrollTo("ld-how")}>วิธีใช้</button>
            <button type="button" onClick={() => scrollTo("ld-tech")}>เบื้องหลัง</button>
          </nav>
          <button type="button" className="btn btn-primary btn-sm ld-nav-cta" onClick={goApp}>เริ่มใช้งาน</button>
        </div>
      </header>

      <main>
        <section className="ld-hero">
          <div className="ld-wrap ld-hero-in">
            <div className="ld-hero-text">
              <span className={"ld-status ld-status-" + status} role="status"><i aria-hidden="true" />{STATUS_TEXT[status]}</span>
              <h1>รู้ก่อนออกเดินทาง<br />ว่าช่วงไหน<span className="ld-hl">ควรระวัง</span></h1>
              <p className="ld-lead">RoadAware คาดการณ์ความเสี่ยงอุบัติเหตุบนทางหลวงทั่วประเทศไทย ตามเส้นทางและเวลาที่คุณจะขับผ่าน แล้วชี้จุดที่ควรระวังให้ตั้งแต่ก่อนออกจากบ้าน</p>
              <div className="ld-cta">
                <button type="button" className="btn btn-primary btn-lg" onClick={goApp}>เริ่มใช้งาน {Icon.arrow}</button>
                <button type="button" className="btn btn-ghost btn-lg" onClick={() => scrollTo("ld-how")}>ดูวิธีใช้</button>
              </div>
              <p className="ld-small">ใช้ผ่านเว็บเบราว์เซอร์ได้ทันที บนคอมพิวเตอร์ แท็บเล็ต และมือถือ · ไม่ต้องสมัครสมาชิก</p>
            </div>
            <HeroPreview />
          </div>
        </section>

        <section className="ld-sec" id="ld-features">
          <div className="ld-wrap">
            <h2 className="ld-h2">ทำอะไรได้บ้าง</h2>
            <div className="ld-grid3">
              {FEATURES.map((f) => (
                <article key={f.title} className="ld-card">
                  <span className="ld-icon">{f.icon}</span>
                  <h3>{f.title}</h3>
                  <p>{f.text}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="ld-sec ld-sec-alt" id="ld-how">
          <div className="ld-wrap ld-how">
            <div>
              <h2 className="ld-h2">ใช้งานง่ายใน 4 ขั้นตอน</h2>
              <ol className="ld-steps">
                {STEPS.map((s, i) => (
                  <li key={s.title}><span className="ld-step-n">{i + 1}</span><div><h3>{s.title}</h3><p>{s.text}</p></div></li>
                ))}
              </ol>
            </div>
            <aside className="ld-legend" aria-label="ความหมายของสีบนแผนที่">
              <h3>อ่านแผนที่</h3>
              <ul>
                <li><span className="ld-pin" style={{ background: LEVELS.red.hex }}>1</span><div><b>จุดสีแดง — สูงมาก</b><small>อยู่ใน 5% บนสุดของถนนทั้งประเทศ</small></div></li>
                <li><span className="ld-pin" style={{ background: LEVELS.orange.hex }}>2</span><div><b>จุดสีส้ม — สูง</b><small>อยู่ในช่วง 5–20% บนสุด</small></div></li>
                <li><span className="ld-line" style={{ background: ROUTE_HEX }} /><div><b>เส้นน้ำเงิน</b><small>ทางหลวงที่ประเมินแล้ว</small></div></li>
                <li><span className="ld-line" style={{ background: UNKNOWN_HEX }} /><div><b>เส้นเทา</b><small>ถนนท้องถิ่น / ในเมืองที่ยังไม่มีข้อมูล (ไม่ได้แปลว่าปลอดภัย)</small></div></li>
              </ul>
            </aside>
          </div>
        </section>

        <section className="ld-sec" id="ld-tech">
          <div className="ld-wrap">
            <h2 className="ld-h2">เบื้องหลัง RoadAware</h2>
            <p className="ld-sub">ข้อมูล วิธีคัดเลือกข้อมูล โมเดล และเครื่องมือทั้งหมดที่ใช้ในงานนี้</p>
            <ol className="ld-flow" aria-label="ขั้นตอนการทำงานของระบบ">
              {FLOW.map((f, i) => (
                <li key={f.title}><span className="ld-flow-n">{i + 1}</span><div><b>{f.title}</b><small>{f.text}</small></div></li>
              ))}
            </ol>
            <div className="ld-tech">
              {TECH.map((g) => (
                <article key={g.title} className="ld-card ld-tech-card">
                  <h3>{g.title}</h3>
                  <dl>
                    {g.items.map(([k, v]) => (
                      <div key={k}><dt>{k}</dt><dd>{v}</dd></div>
                    ))}
                  </dl>
                </article>
              ))}
            </div>
            <p className="ld-note">ผลเป็นการคาดการณ์จากสถิติ ใช้ประกอบการวางแผนก่อนเดินทาง ไม่ได้รับประกันความปลอดภัย และไม่ใช่ระบบเตือนภัยแบบเรียลไทม์</p>
          </div>
        </section>

        <section className="ld-final">
          <div className="ld-wrap ld-final-in">
            <h2>พร้อมวางแผนทริปถัดไปแล้วหรือยัง</h2>
            <p>ใช้เวลาไม่ถึงนาที รู้ก่อนว่าช่วงไหนของเส้นทางควรขับอย่างระมัดระวัง</p>
            <button type="button" className="btn btn-lg ld-final-btn" onClick={goApp}>เริ่มใช้งาน RoadAware {Icon.arrow}</button>
          </div>
        </section>
      </main>

      <footer className="ld-foot">
        <div className="ld-wrap ld-foot-in">
          <div className="ld-foot-brand">
            <div className="ld-brand"><Logo size={26} /> <span>RoadAware</span></div>
          </div>
          <div>
            <h3>ผู้พัฒนา</h3>
            <ul className="ld-team">
              {TEAM.map(([id, name]) => <li key={id}><span>{name}</span><small>{id}</small></li>)}
            </ul>
          </div>
        </div>
      </footer>
    </div>
  );
}
