// Home page shown before the app ("night highway" theme): what RoadAware is, how to use it, what is behind it.
// "เริ่มใช้งาน" plays a short exit transition, then opens the app at #/app (main.jsx switches pages on the hash).
// Motion: drawn route + moving car in the hero, scroll reveals, count-ups, marquee, cursor spotlight.
// Everything respects prefers-reduced-motion. Works on phone, tablet and desktop.
import { useEffect, useRef, useState } from "react";
import { CONFIG, LEVELS, ROUTE_HEX, UNKNOWN_HEX, discoverServer } from "../config.js";

const reducedMotion = () => typeof window !== "undefined" && window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

function Logo({ size = 30, dark = true }) {
  return (
    <svg width={size} height={size} viewBox="0 0 26 26" aria-hidden="true">
      <circle cx="13" cy="13" r="12" fill={dark ? "#0F1B2D" : "#FFFFFF"} />
      <path d="M7 18 C10 12, 13 15, 19 7" stroke="#E8821E" strokeWidth="2.6" fill="none" strokeLinecap="round" />
    </svg>
  );
}

// true only when the demo server (the presenter's Mac) answers; nothing is shown otherwise.
function useServerOnline() {
  const [online, setOnline] = useState(false);
  useEffect(() => {
    let alive = true;
    (async () => {
      const d = await discoverServer();
      if (d.offline) return;
      try {
        const ctrl = new AbortController();
        const t = setTimeout(() => ctrl.abort(), 8000);
        const r = await fetch(CONFIG.apiBase + "/ready", { signal: ctrl.signal, cache: "no-store" });
        clearTimeout(t);
        if (alive && r.ok) setOnline(true);
      } catch (_) { /* stays hidden */ }
    })();
    return () => { alive = false; };
  }, []);
  return online;
}

// Adds .in to every .rv element inside root when it scrolls into view (once).
function useReveal(rootRef) {
  useEffect(() => {
    const root = rootRef.current;
    if (!root) return undefined;
    const els = root.querySelectorAll(".rv");
    if (reducedMotion() || !("IntersectionObserver" in window)) { els.forEach((e) => e.classList.add("in")); return undefined; }
    const io = new IntersectionObserver((entries) => entries.forEach((e) => {
      if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); }
    }), { root, threshold: 0.12, rootMargin: "0px 0px -6% 0px" });
    els.forEach((e) => io.observe(e));
    return () => io.disconnect();
  }, [rootRef]);
}

// Number that counts up when it first becomes visible.
function CountUp({ to, rootRef, duration = 1600 }) {
  const ref = useRef(null);
  const [val, setVal] = useState(reducedMotion() ? to : 0);
  useEffect(() => {
    if (reducedMotion() || !ref.current) return undefined;
    let raf = 0;
    const io = new IntersectionObserver(([e]) => {
      if (!e.isIntersecting) return;
      io.disconnect();
      const t0 = performance.now();
      const step = (t) => {
        const k = Math.min(1, (t - t0) / duration);
        setVal(Math.round(to * (1 - Math.pow(1 - k, 3))));
        if (k < 1) raf = requestAnimationFrame(step);
      };
      raf = requestAnimationFrame(step);
    }, { root: rootRef.current, threshold: 0.4 });
    io.observe(ref.current);
    return () => { io.disconnect(); cancelAnimationFrame(raf); };
  }, [to, duration, rootRef]);
  return <span ref={ref}>{val.toLocaleString("en-US")}</span>;
}

const ROUTE_D = "M58 410 C130 396, 160 330, 236 312 S 352 268, 392 208 S 486 112, 548 64";
const VOICE = ["ข้างหน้าอีก 2 กิโลเมตร มีจุดที่ควรระวัง", "ระวัง! อีก 500 เมตร ถึงจุดที่ 1", "เข้าสู่จุดที่ควรระวังแล้ว ตั้งใจขับนะ"];

// Night-map illustration: the route draws itself, hot spots glow, a car drives along, the voice speaks.
function HeroMap() {
  const pathRef = useRef(null);
  const [pts, setPts] = useState(null);
  const [voice, setVoice] = useState(0);
  const [tilt, setTilt] = useState({ x: 0, y: 0 });
  const motion = !reducedMotion();
  useEffect(() => {
    const p = pathRef.current;
    if (p && p.getTotalLength) {
      const L = p.getTotalLength();
      const at = (f) => { const q = p.getPointAtLength(L * f); return [q.x, q.y]; };
      setPts({ red: at(0.42), orange: at(0.735) });
    }
    if (!motion) return undefined;
    const t = setInterval(() => setVoice((v) => (v + 1) % VOICE.length), 3200);
    return () => clearInterval(t);
  }, [motion]);
  const onMove = (e) => {
    if (!motion || e.pointerType !== "mouse") return;
    const r = e.currentTarget.getBoundingClientRect();
    setTilt({ x: ((e.clientY - r.top) / r.height - 0.5) * -6, y: ((e.clientX - r.left) / r.width - 0.5) * 8 });
  };
  return (
    <div className="hm" aria-hidden="true" onPointerMove={onMove} onPointerLeave={() => setTilt({ x: 0, y: 0 })}>
      <div className="hm-card" style={{ transform: `perspective(1200px) rotateX(${tilt.x}deg) rotateY(${tilt.y}deg)` }}>
        <svg viewBox="0 0 600 470" preserveAspectRatio="xMidYMid slice">
          <defs>
            <radialGradient id="hmBg" cx="70%" cy="20%" r="90%"><stop offset="0" stopColor="#1B2D4A" /><stop offset="1" stopColor="#0A1424" /></radialGradient>
            <filter id="hmGlow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="6" /></filter>
            <filter id="hmSoft" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="2.2" /></filter>
            <radialGradient id="hmCar"><stop offset="0" stopColor="#FFE2B0" /><stop offset=".35" stopColor="#F2A245" stopOpacity=".9" /><stop offset="1" stopColor="#E8821E" stopOpacity="0" /></radialGradient>
          </defs>
          <rect width="600" height="470" fill="url(#hmBg)" />
          <g className="hm-grid" stroke="#22344F" strokeWidth="1">
            {Array.from({ length: 13 }, (_, i) => <line key={"v" + i} x1={i * 50} y1="0" x2={i * 50} y2="470" />)}
            {Array.from({ length: 10 }, (_, i) => <line key={"h" + i} x1="0" y1={i * 50} x2="600" y2={i * 50} />)}
          </g>
          <g stroke="#2B4366" strokeWidth="3" fill="none" strokeLinecap="round" opacity=".9">
            <path d="M-10 120 C120 140, 220 90, 330 130 S 520 170, 620 130" />
            <path d="M110 -10 C130 120, 80 260, 140 480" />
            <path d="M-10 300 C90 260, 200 280, 300 250" />
            <path d="M440 -10 C420 120, 470 280, 430 480" />
            <path d="M300 480 C320 400, 400 360, 620 380" />
          </g>
          <path d={ROUTE_D} stroke={ROUTE_HEX} strokeWidth="16" fill="none" strokeLinecap="round" filter="url(#hmGlow)" opacity=".75" />
          <path ref={pathRef} id="hmRoute" className="hm-route" d={ROUTE_D} pathLength="1" stroke="#9CC0EA" strokeWidth="5" fill="none" strokeLinecap="round" />
          <path className="hm-hot hm-hot-r" d={ROUTE_D} pathLength="100" stroke={LEVELS.red.hex} strokeWidth="7" fill="none" strokeLinecap="round" strokeDasharray="12 200" strokeDashoffset="-36" />
          <path className="hm-hot hm-hot-r" d={ROUTE_D} pathLength="100" stroke={LEVELS.red.hex} strokeWidth="16" fill="none" strokeLinecap="round" strokeDasharray="12 200" strokeDashoffset="-36" filter="url(#hmGlow)" />
          <path className="hm-hot hm-hot-o" d={ROUTE_D} pathLength="100" stroke={LEVELS.orange.hex} strokeWidth="7" fill="none" strokeLinecap="round" strokeDasharray="7 200" strokeDashoffset="-70" />
          <path className="hm-hot hm-hot-o" d={ROUTE_D} pathLength="100" stroke={LEVELS.orange.hex} strokeWidth="16" fill="none" strokeLinecap="round" strokeDasharray="7 200" strokeDashoffset="-70" filter="url(#hmGlow)" />
          {motion && (
            <g className="hm-car">
              <circle r="22" fill="url(#hmCar)"><animateMotion dur="9s" begin="1.6s" repeatCount="indefinite" rotate="auto"><mpath href="#hmRoute" /></animateMotion></circle>
              <circle r="5.5" fill="#FFF4E0"><animateMotion dur="9s" begin="1.6s" repeatCount="indefinite"><mpath href="#hmRoute" /></animateMotion></circle>
            </g>
          )}
          <g className="hm-pin hm-pin-a"><circle cx="58" cy="410" r="13" fill="#0B6E69" stroke="#fff" strokeWidth="3" /><text x="58" y="415" textAnchor="middle">A</text></g>
          <g className="hm-pin hm-pin-b"><circle cx="548" cy="64" r="13" fill="#E8821E" stroke="#fff" strokeWidth="3" /><text x="548" y="69" textAnchor="middle">B</text></g>
          {pts && (
            <>
              <g className="hm-mark hm-mark-1" transform={`translate(${pts.red[0]} ${pts.red[1]})`}>
                <circle className="hm-ring" r="16" fill="none" stroke={LEVELS.red.hex} strokeWidth="3" />
                <circle r="16" fill={LEVELS.red.hex} stroke="#fff" strokeWidth="3" /><text y="5.5" textAnchor="middle">1</text>
              </g>
              <g className="hm-mark hm-mark-2" transform={`translate(${pts.orange[0]} ${pts.orange[1]})`}>
                <circle className="hm-ring" r="16" fill="none" stroke={LEVELS.orange.hex} strokeWidth="3" />
                <circle r="16" fill={LEVELS.orange.hex} stroke="#fff" strokeWidth="3" /><text y="5.5" textAnchor="middle">2</text>
              </g>
            </>
          )}
        </svg>
        <div className="hm-scan" />
      </div>
      <div className="hm-float hm-brief">
        <span className="hm-brief-n">2</span>
        <span><b>จุดที่ควรระวัง</b><small><i style={{ background: LEVELS.red.hex }} />สูงมาก 1 · <i style={{ background: LEVELS.orange.hex }} />สูง 1</small></span>
      </div>
      <div className="hm-float hm-voice">
        <span className="hm-wave"><i /><i /><i /><i /></span>
        <span key={voice} className="hm-voice-t">“{VOICE[voice]}”</span>
      </div>
    </div>
  );
}

const Icon = {
  route: <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="6" cy="19" r="2.5" /><circle cx="18" cy="5" r="2.5" /><path d="M8.5 19H16a3.5 3.5 0 0 0 0-7H8a3.5 3.5 0 0 1 0-7h7.5" /></svg>,
  drive: <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M11 5 6 9H3v6h3l5 4z" /><path d="M15.5 8.5a5 5 0 0 1 0 7" /><path d="M18.5 5.5a9 9 0 0 1 0 13" /></svg>,
  review: <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 12a9 9 0 1 0 3-6.7" /><path d="M3 4v5h5" /><path d="M12 7v5l3 2" /></svg>,
  arrow: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M13 6l6 6-6 6" /></svg>,
  down: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M6 9l6 6 6-6" /></svg>,
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

const COVER = [
  { to: 26740, unit: "ช่วง", text: "ช่วงทางหลวงที่ประเมิน" },
  { to: 51900, unit: "กม.", text: "ความยาวทางหลวงรวม" },
  { to: 98207, unit: "รายการ", text: "อุบัติเหตุที่จับคู่กับถนน (2564–2568)" },
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

const STACK = ["Python", "pandas", "scikit-learn", "HistGradientBoosting", "Jupyter", "FastAPI", "React", "Vite", "Leaflet", "OpenStreetMap", "OSRM", "Photon", "Open-Meteo", "GitHub Pages", "Cloudflare Tunnel"];

const TEAM = [
  ["66088346", "นายฤทธิพร ผึ่งผาย"],
  ["66088226", "นายกันณพิช เบ้าศรี"],
  ["66080740", "นางสาววรรณษา วงค์ดี"],
  ["66092559", "นายจริยธรรม มาสงค์"],
];

export default function Landing() {
  const online = useServerOnline();
  const rootRef = useRef(null);
  const [scrolled, setScrolled] = useState(false);
  const [leaving, setLeaving] = useState(false);
  useReveal(rootRef);
  useEffect(() => { document.title = "RoadAware — รู้ก่อนออกเดินทาง ว่าช่วงไหนควรระวัง"; }, []);

  const goApp = () => {
    if (leaving) return;
    if (reducedMotion()) { window.location.hash = "#/app"; return; }
    setLeaving(true);
    setTimeout(() => { window.location.hash = "#/app"; }, 650);
  };
  const scrollTo = (id) => { const el = document.getElementById(id); if (el) el.scrollIntoView({ behavior: reducedMotion() ? "auto" : "smooth", block: "start" }); };
  const onScroll = (e) => { const s = e.currentTarget.scrollTop > 30; if (s !== scrolled) setScrolled(s); };
  const spot = (e) => {
    if (e.pointerType !== "mouse") return;
    const r = e.currentTarget.getBoundingClientRect();
    e.currentTarget.style.setProperty("--mx", ((e.clientX - r.left) / r.width) * 100 + "%");
    e.currentTarget.style.setProperty("--my", ((e.clientY - r.top) / r.height) * 100 + "%");
  };

  return (
    <div className={"landing" + (leaving ? " is-leaving" : "")} ref={rootRef} onScroll={onScroll}>
      <header className={"ld-nav" + (scrolled ? " is-scrolled" : "")}>
        <div className="ld-wrap ld-nav-in">
          <a className="ld-brand" href="#/" onClick={(e) => { e.preventDefault(); rootRef.current && rootRef.current.scrollTo({ top: 0, behavior: "smooth" }); }}>
            <Logo dark={scrolled} /> <span>RoadAware</span>
          </a>
          <nav className="ld-links" aria-label="เมนู">
            <button type="button" onClick={() => scrollTo("ld-features")}>ความสามารถ</button>
            <button type="button" onClick={() => scrollTo("ld-how")}>วิธีใช้</button>
            <button type="button" onClick={() => scrollTo("ld-tech")}>เบื้องหลัง</button>
          </nav>
          <button type="button" className="ld-btn ld-btn-sm" onClick={goApp}>เริ่มใช้งาน</button>
        </div>
      </header>

      <main>
        <section className="ld-hero" onPointerMove={spot}>
          <div className="ld-hero-bg" aria-hidden="true"><i className="b1" /><i className="b2" /><i className="b3" /><i className="ld-stars" /></div>
          <div className="ld-wrap ld-hero-in">
            <div className="ld-hero-text">
              {online && <span className="ld-online ld-in" style={{ "--d": "0ms" }} role="status"><i aria-hidden="true" />เซิร์ฟเวอร์พร้อมใช้งาน</span>}
              <h1>
                <span className="ld-line ld-in" style={{ "--d": "80ms" }}>รู้ก่อนออกเดินทาง</span>
                <span className="ld-line ld-in" style={{ "--d": "220ms" }}>ว่าช่วงไหน<span className="ld-grad">ควรระวัง</span></span>
              </h1>
              <p className="ld-lead ld-in" style={{ "--d": "380ms" }}>RoadAware คาดการณ์ความเสี่ยงอุบัติเหตุบนทางหลวงทั่วประเทศไทย ตามเส้นทางและเวลาที่คุณจะขับผ่าน แล้วชี้จุดที่ควรระวังให้ตั้งแต่ก่อนออกจากบ้าน</p>
              <div className="ld-cta ld-in" style={{ "--d": "520ms" }}>
                <button type="button" className="ld-btn ld-btn-lg" onClick={goApp}><span>เริ่มใช้งาน</span>{Icon.arrow}</button>
                <button type="button" className="ld-btn-ghost ld-btn-lg" onClick={() => scrollTo("ld-how")}>ดูวิธีใช้</button>
              </div>
              <p className="ld-small ld-in" style={{ "--d": "640ms" }}>ใช้ผ่านเว็บเบราว์เซอร์ได้ทันที บนคอมพิวเตอร์ แท็บเล็ต และมือถือ · ไม่ต้องสมัครสมาชิก</p>
            </div>
            <div className="ld-in ld-in-r" style={{ "--d": "300ms" }}><HeroMap /></div>
          </div>
          <div className="ld-wrap">
            <div className="ld-cover rv">
              {COVER.map((c) => (
                <div key={c.text}><b><CountUp to={c.to} rootRef={rootRef} /><small>{c.unit}</small></b><span>{c.text}</span></div>
              ))}
            </div>
          </div>
          <button type="button" className="ld-scroll" onClick={() => scrollTo("ld-features")} aria-label="เลื่อนลง">{Icon.down}</button>
        </section>

        <div className="ld-marquee" aria-label="เทคโนโลยีที่ใช้">
          <div className="ld-marquee-mask">
            <div className="ld-marquee-in">
              {[0, 1].map((k) => (
                <span key={k} aria-hidden={k === 1}>{STACK.map((s) => <em key={s}>{s}</em>)}</span>
              ))}
            </div>
          </div>
        </div>

        <section className="ld-sec" id="ld-features">
          <div className="ld-wrap">
            <p className="ld-eyebrow rv">ความสามารถ</p>
            <h2 className="ld-h2 rv">ทำอะไรได้บ้าง</h2>
            <div className="ld-grid3">
              {FEATURES.map((f, i) => (
                <article key={f.title} className="ld-card ld-feat rv" style={{ "--d": i * 120 + "ms" }}>
                  <span className="ld-feat-n">0{i + 1}</span>
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
              <p className="ld-eyebrow rv">วิธีใช้</p>
              <h2 className="ld-h2 rv">ใช้งานง่ายใน 4 ขั้นตอน</h2>
              <ol className="ld-steps">
                {STEPS.map((s, i) => (
                  <li key={s.title} className="rv" style={{ "--d": i * 120 + "ms" }}><span className="ld-step-n">{i + 1}</span><div><h3>{s.title}</h3><p>{s.text}</p></div></li>
                ))}
              </ol>
            </div>
            <aside className="ld-legend rv" style={{ "--d": "200ms" }} aria-label="ความหมายของสีบนแผนที่">
              <h3>อ่านแผนที่</h3>
              <ul>
                <li><span className="ld-pin ld-pin-pulse" style={{ background: LEVELS.red.hex, "--c": LEVELS.red.hex }}>1</span><div><b>จุดสีแดง — สูงมาก</b><small>อยู่ใน 5% บนสุดของถนนทั้งประเทศ</small></div></li>
                <li><span className="ld-pin ld-pin-pulse" style={{ background: LEVELS.orange.hex, "--c": LEVELS.orange.hex }}>2</span><div><b>จุดสีส้ม — สูง</b><small>อยู่ในช่วง 5–20% บนสุด</small></div></li>
                <li><span className="ld-line-key" style={{ background: ROUTE_HEX }} /><div><b>เส้นน้ำเงิน</b><small>ทางหลวงที่ประเมินแล้ว</small></div></li>
                <li><span className="ld-line-key" style={{ background: UNKNOWN_HEX }} /><div><b>เส้นเทา</b><small>ถนนท้องถิ่น / ในเมืองที่ยังไม่มีข้อมูล (ไม่ได้แปลว่าปลอดภัย)</small></div></li>
              </ul>
            </aside>
          </div>
        </section>

        <section className="ld-sec" id="ld-tech">
          <div className="ld-wrap">
            <p className="ld-eyebrow rv">เบื้องหลัง</p>
            <h2 className="ld-h2 rv">เบื้องหลัง RoadAware</h2>
            <p className="ld-sub rv">ข้อมูล วิธีคัดเลือกข้อมูล โมเดล และเครื่องมือทั้งหมดที่ใช้ในงานนี้</p>
            <ol className="ld-flow" aria-label="ขั้นตอนการทำงานของระบบ">
              {FLOW.map((f, i) => (
                <li key={f.title} className="rv" style={{ "--d": i * 100 + "ms" }}><span className="ld-flow-n">{i + 1}</span><div><b>{f.title}</b><small>{f.text}</small></div></li>
              ))}
            </ol>
            <div className="ld-tech">
              {TECH.map((g, i) => (
                <article key={g.title} className="ld-card ld-tech-card rv" style={{ "--d": (i % 2) * 120 + "ms" }}>
                  <h3>{g.title}</h3>
                  <dl>
                    {g.items.map(([k, v]) => (
                      <div key={k}><dt>{k}</dt><dd>{v}</dd></div>
                    ))}
                  </dl>
                </article>
              ))}
            </div>
            <p className="ld-note rv">ผลเป็นการคาดการณ์จากสถิติ ใช้ประกอบการวางแผนก่อนเดินทาง ไม่ได้รับประกันความปลอดภัย และไม่ใช่ระบบเตือนภัยแบบเรียลไทม์</p>
          </div>
        </section>

        <section className="ld-final" onPointerMove={spot}>
          <div className="ld-final-bg" aria-hidden="true"><i className="b1" /><i className="b2" /></div>
          <div className="ld-wrap ld-final-in">
            <h2 className="rv">พร้อมวางแผนทริปถัดไปแล้วหรือยัง</h2>
            <p className="rv" style={{ "--d": "100ms" }}>ใช้เวลาไม่ถึงนาที รู้ก่อนว่าช่วงไหนของเส้นทางควรขับอย่างระมัดระวัง</p>
            <div className="rv" style={{ "--d": "200ms" }}>
              <button type="button" className="ld-btn ld-btn-lg ld-btn-glow" onClick={goApp}><span>เริ่มใช้งาน RoadAware</span>{Icon.arrow}</button>
            </div>
          </div>
        </section>
      </main>

      <footer className="ld-foot">
        <div className="ld-wrap ld-foot-in">
          <div className="ld-brand"><Logo size={26} /> <span>RoadAware</span></div>
          <div>
            <h3>ผู้พัฒนา</h3>
            <ul className="ld-team">
              {TEAM.map(([id, name]) => <li key={id}><span>{name}</span><small>{id}</small></li>)}
            </ul>
          </div>
        </div>
      </footer>

      <div className="ld-exit" aria-hidden="true"><Logo size={64} dark={false} /></div>
    </div>
  );
}
