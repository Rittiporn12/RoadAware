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

// Chrome / Edge / Android offer "install as app"; iPhone uses Share → Add to Home Screen (explained below).
function useInstallPrompt() {
  const [evt, setEvt] = useState(null);
  useEffect(() => {
    const on = (e) => { e.preventDefault(); setEvt(e); };
    window.addEventListener("beforeinstallprompt", on);
    return () => window.removeEventListener("beforeinstallprompt", on);
  }, []);
  return evt ? async () => { evt.prompt(); try { await evt.userChoice; } catch (_) { /* ignore */ } setEvt(null); } : null;
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
  desktop: <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="4" width="18" height="12" rx="2" /><path d="M8 20h8M12 16v4" /></svg>,
  phone: <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><rect x="7" y="2.5" width="10" height="19" rx="2.5" /><path d="M11 18.5h2" /></svg>,
  tablet: <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><rect x="4" y="2.5" width="16" height="19" rx="2.5" /><path d="M11 18.5h2" /></svg>,
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

const STATS = [
  { value: "9/9", label: "เดือน", text: "ทำนายดีกว่าค่าเทียบทุกเดือน (ม.ค.–ก.ย. 2569)" },
  { value: "24%", label: "สงกรานต์", text: "ความคลาดเคลื่อนต่ำกว่าค่าเทียบ ช่วงสงกรานต์ 2569" },
  { value: "70/76", label: "จังหวัด", text: "จังหวัดที่โมเดลทำได้ดีกว่าค่าเทียบ" },
  { value: "15,425", label: "เหตุ", text: "อุบัติเหตุจริงปี 2569 บนทางหลวง ที่ใช้ทดสอบ" },
];

const TEAM = [
  ["66088346", "นายฤทธิพร ผึ่งผาย"],
  ["66088226", "นายกันณพิช เบ้าศรี"],
  ["66080740", "นางสาววรรณษา วงค์ดี"],
  ["66092559", "นายจริยธรรม มาสงค์"],
];

export default function Landing() {
  const status = useServerStatus();
  const install = useInstallPrompt();
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
            <button type="button" onClick={() => scrollTo("ld-model")}>ผลทดสอบ</button>
            <button type="button" onClick={() => scrollTo("ld-devices")}>อุปกรณ์</button>
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

        <section className="ld-sec" id="ld-model">
          <div className="ld-wrap">
            <h2 className="ld-h2">ทดสอบกับข้อมูลที่โมเดลไม่เคยเห็น</h2>
            <p className="ld-sub">โมเดลเรียนรู้จากอุบัติเหตุบนทางหลวงปี 2564–2566 ตรวจกับปี 2567–2568 แล้วทดสอบจริงกับข้อมูลปี 2569 ซึ่งไม่ได้ใช้ระหว่างพัฒนาโมเดล</p>
            <div className="ld-stats">
              {STATS.map((s) => (
                <div key={s.text} className="ld-stat">
                  <b>{s.value}</b><span className="ld-stat-l">{s.label}</span>
                  <p>{s.text}</p>
                </div>
              ))}
            </div>
            <div className="ld-howit">
              <div><h3>ข้อมูลที่ใช้</h3><p>ตำแหน่งและรูปทรงถนน ปฏิทินวันหยุดและเทศกาล สภาพอากาศ ปริมาณจราจร และสถิติอุบัติเหตุย้อนหลัง</p></div>
              <div><h3>โมเดล</h3><p>Histogram Gradient Boosting คาดการณ์จำนวนเหตุต่อช่วงถนน รายวันและราย 6 ชั่วโมง ครอบคลุมทางหลวงกรมทางหลวงทั่วประเทศ</p></div>
              <div><h3>ข้อควรรู้</h3><p>เป็นการคาดการณ์จากสถิติ ใช้ประกอบการวางแผน ไม่ได้รับประกันความปลอดภัย และไม่ใช่ระบบเตือนภัยแบบเรียลไทม์</p></div>
            </div>
          </div>
        </section>

        <section className="ld-sec ld-sec-alt" id="ld-devices">
          <div className="ld-wrap">
            <h2 className="ld-h2">ใช้ได้ทุกอุปกรณ์</h2>
            <p className="ld-sub">เปิดผ่านเว็บเบราว์เซอร์ได้เลย ไม่ต้องติดตั้ง และเพิ่มไอคอนลงหน้าจอเพื่อเปิดเหมือนแอปได้</p>
            <div className="ld-grid3">
              <article className="ld-card ld-device">
                <span className="ld-icon">{Icon.desktop}</span>
                <h3>คอมพิวเตอร์</h3>
                <p>Windows · macOS · Linux<br />Chrome, Edge, Safari, Firefox</p>
                <p className="ld-tip">เหมาะกับการวางแผนเส้นทางและดูรายละเอียดบนจอใหญ่</p>
              </article>
              <article className="ld-card ld-device">
                <span className="ld-icon">{Icon.phone}</span>
                <h3>iPhone / iPad</h3>
                <p>เปิดด้วย Safari</p>
                <p className="ld-tip">กดปุ่ม <b>แชร์</b> → <b>เพิ่มไปยังหน้าจอโฮม</b> เพื่อเปิดแบบเต็มจอ</p>
              </article>
              <article className="ld-card ld-device">
                <span className="ld-icon">{Icon.tablet}</span>
                <h3>Android</h3>
                <p>เปิดด้วย Chrome</p>
                <p className="ld-tip">กดเมนู <b>⋮</b> → <b>เพิ่มลงในหน้าจอหลัก</b> หรือ <b>ติดตั้งแอป</b></p>
              </article>
            </div>
            {install && (
              <div className="ld-install">
                <span>เบราว์เซอร์นี้ติดตั้ง RoadAware เป็นแอปได้</span>
                <button type="button" className="btn btn-ghost btn-sm" onClick={install}>ติดตั้งแอป</button>
              </div>
            )}
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
            <p>โครงงานเพื่อการศึกษาในระดับมหาวิทยาลัย</p>
            <p className="ld-credit">นำข้อมูลและบริการแบบเปิดมาใช้: OpenStreetMap · Photon (komoot) · OSRM · geoBoundaries · Natural Earth</p>
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
