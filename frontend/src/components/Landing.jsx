// Home page shown before the app : what RoadAware is, how to use it, what is behind it.
// "เริ่มใช้งาน" plays a short exit transition, then opens the app at #/app (main.jsx switches pages on the hash).
// Motion is kept to what explains the product: the route drawing, the car, the warnings; plus gentle scroll reveals.
// Everything respects prefers-reduced-motion. Works on phone, tablet and desktop.
import { useEffect, useRef, useState } from "react";
import { CONFIG, LEVELS, ROUTE_HEX, UNKNOWN_HEX, discoverServer } from "../config.js";
import { Logo, SiteFooter, SiteNav, reducedMotion, useReveal } from "./site.jsx";

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

const ROUTE_D = "M58 410 C130 396, 160 330, 236 312 S 352 268, 392 208 S 486 112, 548 64";
const VOICE = ["ข้างหน้าอีก 2 กิโลเมตร มีจุดที่ควรระวัง", "ระวัง! อีก 500 เมตร ถึงจุดที่ 1", "เข้าสู่จุดที่ควรระวังแล้ว ตั้งใจขับนะ"];

// Map illustration in the app's own map style: the route draws itself, the numbered points appear,
// a car drives along, and the spoken warning changes as it goes.
function Shield({ x, y, n }) {
  const w = 10 + String(n).length * 8;
  return (
    <g className="hm-shield" transform={`translate(${x} ${y})`}>
      <rect x={-w / 2} y="-9" width={w} height="18" rx="4" fill="#fff" stroke="#1D4F91" strokeWidth="2" />
      <text y="4.5" textAnchor="middle">{n}</text>
    </g>
  );
}

function HeroMap() {
  const pathRef = useRef(null);
  const [pts, setPts] = useState(null);
  const [voice, setVoice] = useState(0);
  const motion = !reducedMotion();
  useEffect(() => {
    const p = pathRef.current;
    if (p && p.getTotalLength) {
      const L = p.getTotalLength();
      const at = (f) => { const q = p.getPointAtLength(L * f); return [q.x, q.y]; };
      setPts({ red: at(0.42), orange: at(0.735) });
    }
    if (!motion) return undefined;
    const t = setInterval(() => setVoice((v) => (v + 1) % VOICE.length), 3400);
    return () => clearInterval(t);
  }, [motion]);
  return (
    <div className="hm" aria-hidden="true">
      <div className="hm-card">
        <svg viewBox="0 0 600 470" preserveAspectRatio="xMidYMid slice">
          <rect width="600" height="470" fill="#F2EFE9" />
          <path d="M380 0 C430 60, 520 40, 600 90 L600 0 Z" fill="#D6E7C9" />
          <path d="M0 330 C60 300, 110 340, 150 380 C180 410, 140 470, 60 470 L0 470 Z" fill="#D6E7C9" />
          <ellipse cx="470" cy="330" rx="70" ry="44" fill="#D6E7C9" />
          <path d="M-10 210 C80 230, 150 190, 230 220 S 360 300, 420 290 S 540 250, 620 270" stroke="#AAD3DF" strokeWidth="10" fill="none" strokeLinecap="round" />
          <g fill="none" strokeLinecap="round">
            <g stroke="#D8D2C6" strokeWidth="9">
              <path d="M-10 120 C120 140, 220 90, 330 130 S 520 170, 620 130" />
              <path d="M110 -10 C130 120, 80 260, 140 480" />
              <path d="M440 -10 C420 120, 470 280, 430 480" />
              <path d="M300 480 C320 400, 400 360, 620 380" />
            </g>
            <g stroke="#FFFFFF" strokeWidth="6">
              <path d="M-10 120 C120 140, 220 90, 330 130 S 520 170, 620 130" />
              <path d="M110 -10 C130 120, 80 260, 140 480" />
              <path d="M440 -10 C420 120, 470 280, 430 480" />
              <path d="M300 480 C320 400, 400 360, 620 380" />
            </g>
            <g stroke="#E4DFD5" strokeWidth="2">
              <path d="M180 0 L200 470" /><path d="M0 60 L600 30" /><path d="M260 470 L330 0" /><path d="M0 440 L600 420" />
            </g>
          </g>
          <path d={ROUTE_D} stroke="#FFFFFF" strokeWidth="13" fill="none" strokeLinecap="round" />
          <path ref={pathRef} id="hmRoute" className="hm-route" d={ROUTE_D} pathLength="1" stroke={ROUTE_HEX} strokeWidth="7" fill="none" strokeLinecap="round" />
          <path className="hm-hot hm-hot-r" d={ROUTE_D} pathLength="100" stroke={LEVELS.red.hex} strokeWidth="7" fill="none" strokeLinecap="butt" strokeDasharray="12 200" strokeDashoffset="-36" />
          <path className="hm-hot hm-hot-o" d={ROUTE_D} pathLength="100" stroke={LEVELS.orange.hex} strokeWidth="7" fill="none" strokeLinecap="butt" strokeDasharray="7 200" strokeDashoffset="-70" />
          <Shield x={300} y={112} n={304} />
          <Shield x={98} y={200} n={1} />
          <Shield x={462} y={370} n={33} />
          <text className="hm-place" x="214" y="372">นครนายก</text>
          <text className="hm-place" x="470" y="250">ปราจีนบุรี</text>
          {motion && (
            <g className="hm-car">
              <g>
                <animateMotion dur="10s" begin="1.8s" repeatCount="indefinite"><mpath href="#hmRoute" /></animateMotion>
                <circle r="9" fill="#0F1B2D" opacity=".18" />
                <circle r="6.5" fill="#fff" stroke="#0F1B2D" strokeWidth="2.5" />
                <circle r="2.5" fill="#0F1B2D" />
              </g>
            </g>
          )}
          <g className="hm-pin hm-pin-a"><circle cx="58" cy="410" r="13" fill="#0B6E69" stroke="#fff" strokeWidth="3" /><text x="58" y="415" textAnchor="middle">A</text></g>
          <g className="hm-pin hm-pin-b"><circle cx="548" cy="64" r="13" fill="#E8821E" stroke="#fff" strokeWidth="3" /><text x="548" y="69" textAnchor="middle">B</text></g>
          {pts && (
            <>
              <g className="hm-mark hm-mark-1" transform={`translate(${pts.red[0]} ${pts.red[1]})`}>
                <circle className="hm-ring" r="15" fill="none" stroke={LEVELS.red.hex} strokeWidth="2.5" />
                <circle r="15" fill={LEVELS.red.hex} stroke="#fff" strokeWidth="3" /><text y="5" textAnchor="middle">1</text>
              </g>
              <g className="hm-mark hm-mark-2" transform={`translate(${pts.orange[0]} ${pts.orange[1]})`}>
                <circle className="hm-ring" r="15" fill="none" stroke={LEVELS.orange.hex} strokeWidth="2.5" />
                <circle r="15" fill={LEVELS.orange.hex} stroke="#fff" strokeWidth="3" /><text y="5" textAnchor="middle">2</text>
              </g>
            </>
          )}
        </svg>
      </div>
      <div className="hm-float hm-brief">
        <span className="hm-brief-n">2</span>
        <span><b>จุดที่ควรระวัง</b><small>สูงมาก 1 จุด · สูง 1 จุด</small></span>
      </div>
      <div className="hm-float hm-voice">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M11 5 6 9H3v6h3l5 4z" /><path d="M15.5 8.5a5 5 0 0 1 0 7" /><path d="M18.5 5.5a9 9 0 0 1 0 13" /></svg>
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

const BKK = { id: "preset-bkk", name: "กรุงเทพฯ (อนุสาวรีย์ชัยสมรภูมิ)", sub: "กรุงเทพมหานคร", lat: 13.7649, lon: 100.5383, source: "preset" };
const SAMPLES = [
  { to: "เชียงใหม่", note: "ทางไกลขึ้นเหนือ", dest: { id: "preset-cnx", name: "ประตูท่าแพ เชียงใหม่", sub: "เชียงใหม่", lat: 18.7877, lon: 98.9933, source: "preset" } },
  { to: "เขาใหญ่", note: "เที่ยววันหยุด", dest: { id: "preset-khaoyai", name: "อุทยานแห่งชาติเขาใหญ่", sub: "นครราชสีมา", lat: 14.4393, lon: 101.3725, source: "preset" } },
  { to: "หัวหิน", note: "ทะเลฝั่งตะวันตก", dest: { id: "preset-huahin", name: "สถานีรถไฟหัวหิน", sub: "ประจวบคีรีขันธ์", lat: 12.5684, lon: 99.9577, source: "preset" } },
  { to: "พัทยา", note: "ทะเลฝั่งตะวันออก", dest: { id: "preset-pattaya", name: "พัทยา", sub: "ชลบุรี", lat: 12.9236, lon: 100.8825, source: "preset" } },
];

const FLOW = [
  { title: "รวบรวมข้อมูล", text: "อุบัติเหตุ ถนน อากาศ จราจร ปฏิทิน" },
  { title: "คัดเลือกและจับคู่", text: "จับเหตุเข้ากับช่วงถนน แบ่งช่วงปี" },
  { title: "ฝึกโมเดล", text: "คาดจำนวนเหตุต่อช่วงถนน" },
  { title: "API", text: "คำนวณตามเส้นทางและเวลา" },
  { title: "เว็บแอป", text: "แผนที่ จุดที่ควรระวัง เสียงเตือน" },
];

// [label, text, links]: links open the original source in a new tab.
const TECH = [
  {
    title: "ข้อมูลที่ใช้",
    items: [
      ["อุบัติเหตุทางถนน", "ข้อมูลเปิดของกระทรวงคมนาคม ปี 2564–2569", [["ข้อมูลอุบัติเหตุ (datagov.mot.go.th)", "https://datagov.mot.go.th/dataset/roadaccident"]]],
      ["ถนน", "ทางหลวงของกรมทางหลวง แบ่งเป็น 26,740 ช่วง (ช่วงละราว 2 กม.) รวมราว 51,900 กม.", [["ข้อมูลภูมิสารสนเทศคมนาคม (Transport GIS)", "https://datagov.mot.go.th/th/dataset/transportgis"]]],
      ["สภาพอากาศ", "ปริมาณฝนและอากาศรายวัน", [["Open-Meteo", "https://open-meteo.com/en/docs/previous-runs-api"]]],
      ["ปริมาณจราจร", "ปริมาณจราจรเฉลี่ยรายปี (AADT) ของทางหลวง", [["กรมทางหลวง (opendata.doh.go.th)", "https://opendata.doh.go.th/dataset/ed101df4-f0a1-4d7f-b9d9-76859b2ca73e"]]],
      ["ปฏิทิน", "วันในสัปดาห์ ช่วงเวลา วันหยุด เทศกาลสงกรานต์และปีใหม่", [["วันหยุดตามประกาศธนาคารแห่งประเทศไทย", "https://www.bot.or.th/th/financial-institutions-holiday.html"]]],
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
      ["อัลกอริทึม", "HistGradientBoosting แบบ Poisson regression คาดจำนวนอุบัติเหตุที่จะถูกบันทึกต่อช่วงถนน", [["scikit-learn: HistGradientBoostingRegressor", "https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.HistGradientBoostingRegressor.html"]]],
      ["ระดับเวลา", "2 โมเดล: รายวัน และราย 6 ชั่วโมง"],
      ["ตัวแปร", "รูปทรงและตำแหน่งถนน ปฏิทินและเทศกาล อากาศย้อนหลัง ปริมาณจราจร (33–41 ตัว)"],
      ["ส่วนหลัก / ส่วนเสริม", "ใช้ตัวแปรถนน + ปฏิทินเสมอ และเพิ่มอากาศ / จราจรเมื่อมีข้อมูลของช่วงนั้น"],
      ["ระดับสี", "เทียบกับทุกช่วงถนน × ช่วงเวลาทั่วประเทศ: สูงมาก = 5% บนสุด · สูง = 5–20%"],
    ],
  },
  {
    title: "เครื่องมือและบริการ",
    items: [
      ["วิเคราะห์และฝึกโมเดล", null, [["Python", "https://www.python.org/"], ["pandas", "https://pandas.pydata.org/"], ["scikit-learn", "https://scikit-learn.org/"], ["Jupyter", "https://jupyter.org/"]]],
      ["เซิร์ฟเวอร์", null, [["FastAPI", "https://fastapi.tiangolo.com/"]]],
      ["หน้าเว็บ", null, [["React", "https://react.dev/"], ["Vite", "https://vite.dev/"], ["Leaflet", "https://leafletjs.com/"]]],
      ["แผนที่และเส้นทาง", null, [["OpenStreetMap", "https://www.openstreetmap.org/copyright"], ["Photon (ค้นหาสถานที่)", "https://photon.komoot.io/"], ["OSRM (คำนวณเส้นทาง)", "https://project-osrm.org/"], ["geoBoundaries", "https://www.geoboundaries.org/"], ["Natural Earth", "https://www.naturalearthdata.com/"]]],
      ["เสียงเตือน", "เสียง Siri บน Mac"],
      ["เผยแพร่", null, [["GitHub Pages", "https://pages.github.com/"], ["Cloudflare Tunnel", "https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/do-more-with-tunnels/trycloudflare/"]]],
    ],
  },
];

export default function Landing() {
  const online = useServerOnline();
  const rootRef = useRef(null);
  const [scrolled, setScrolled] = useState(false);
  const [leaving, setLeaving] = useState(false);
  useReveal();
  useEffect(() => { document.title = "RoadAware — รู้ก่อนออกเดินทาง ว่าช่วงไหนควรระวัง"; }, []);
  // arriving from the dashboard's menu: jump to the section that was clicked
  const [jumpTo] = useState(() => {
    try { const id = window.sessionStorage.getItem("roadaware.scrollTo"); window.sessionStorage.removeItem("roadaware.scrollTo"); return id; } catch (_) { return null; }
  });
  useEffect(() => {
    if (!jumpTo) return undefined;
    const t = setTimeout(() => { const el = document.getElementById(jumpTo); if (el) el.scrollIntoView({ block: "start" }); }, 60);
    return () => clearTimeout(t);
  }, [jumpTo]);

  const goApp = () => {
    if (leaving) return;
    // the page swap itself animates (view transition) where the browser supports it
    if (reducedMotion() || document.startViewTransition) { window.location.hash = "#/app"; return; }
    setLeaving(true);
    setTimeout(() => { window.location.hash = "#/app"; }, 380);
  };
  const tryTrip = (t) => {
    try { window.sessionStorage.setItem("roadaware.preset", JSON.stringify({ origin: BKK, dest: t.dest })); } catch (_) { /* storage blocked: the app opens empty */ }
    goApp();
  };
  const scrollTo = (id) => { const el = document.getElementById(id); if (el) el.scrollIntoView({ behavior: reducedMotion() ? "auto" : "smooth", block: "start" }); };
  const onScroll = (e) => { const s = e.currentTarget.scrollTop > 24; if (s !== scrolled) setScrolled(s); };

  return (
    <div className={"landing" + (leaving ? " is-leaving" : "")} ref={rootRef} onScroll={onScroll}>
      <SiteNav active="home" overlay scrolled={scrolled} onInfo={() => scrollTo("ld-tech")} onStart={goApp}
        onBrand={() => rootRef.current && rootRef.current.scrollTo({ top: 0, behavior: reducedMotion() ? "auto" : "smooth" })} />

      <main>
        <section className="ld-hero">
          <div className="ld-wrap ld-hero-in">
            <div className="ld-hero-text">
              {online && <span className="ld-online ld-in" style={{ "--d": "0ms" }} role="status"><i aria-hidden="true" />เซิร์ฟเวอร์พร้อมใช้งาน</span>}
              <h1>
                <span className="ld-line ld-in" style={{ "--d": "80ms" }}>รู้ก่อนออกเดินทาง</span>
                <span className="ld-line ld-in" style={{ "--d": "220ms" }}>ว่าช่วงไหน<span className="ld-accent">ควรระวัง</span></span>
              </h1>
              <p className="ld-lead ld-in" style={{ "--d": "380ms" }}>RoadAware คาดการณ์ความเสี่ยงอุบัติเหตุบนทางหลวงทั่วประเทศไทย ตามเส้นทางและเวลาที่คุณจะขับผ่าน แล้วชี้จุดที่ควรระวังให้ตั้งแต่ก่อนออกจากบ้าน</p>
              <div className="ld-cta ld-in" style={{ "--d": "520ms" }}>
                <button type="button" className="ld-btn ld-btn-lg" onClick={goApp}><span>เริ่มใช้งาน</span>{Icon.arrow}</button>
                <button type="button" className="ld-btn-ghost ld-btn-lg" onClick={() => scrollTo("ld-how")}>ดูวิธีใช้</button>
              </div>
              <button type="button" className="ld-small ld-deep ld-in" style={{ "--d": "640ms" }} onClick={() => scrollTo("ld-tech")}>เจาะลึกการทำงานของ RoadAware: จากข้อมูลอุบัติเหตุจริงบนทางหลวงทั่วประเทศ สู่การพยากรณ์ความเสี่ยงรายช่วงถนนด้วย Machine Learning <span aria-hidden="true">→</span></button>
            </div>
            <div className="ld-in ld-in-r" style={{ "--d": "300ms" }}><HeroMap /></div>
          </div>
          <div className="ld-wrap">
            <div className="ld-samples rv">
              <p className="ld-samples-h">ลองเส้นทางตัวอย่าง <span>กดแล้วเข้าแอปพร้อมต้นทาง–ปลายทาง เลือกเวลาแล้วตรวจได้ทันที</span></p>
              <div className="ld-samples-row">
                {SAMPLES.map((t) => (
                  <button key={t.to} type="button" className="ld-sample" onClick={() => tryTrip(t)}>
                    <span className="ld-sample-r">กรุงเทพฯ <i aria-hidden="true">→</i> <b>{t.to}</b></span>
                    <small>{t.note}</small>
                  </button>
                ))}
              </div>
            </div>
          </div>
          <div className="ld-lane" aria-hidden="true" />
        </section>

        <section className="ld-sec" id="ld-features">
          <div className="ld-wrap">
            <p className="eyebrow eyebrow-ink rv">ความสามารถ</p>
            <h2 className="ld-h2 rv">ทำอะไรได้บ้าง</h2>
            <div className="ld-grid3">
              {FEATURES.map((f, i) => (
                <article key={f.title} className="ld-card ld-feat rv" style={{ "--d": i * 120 + "ms" }}>
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
              <p className="eyebrow eyebrow-ink rv">วิธีใช้</p>
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
            <p className="eyebrow eyebrow-ink rv">ข้อมูล</p>
            <h2 className="ld-h2 rv">เบื้องหลัง RoadAware</h2>
            <p className="ld-sub rv">ข้อมูล วิธีคัดเลือกข้อมูล โมเดล และเครื่องมือทั้งหมดที่ใช้ในงานนี้ · กดชื่อเพื่อเปิดแหล่งที่มา</p>
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
                    {g.items.map(([k, v, links]) => (
                      <div key={k}>
                        <dt>{k}</dt>
                        <dd>
                          {v && <span>{v}</span>}
                          {links && (
                            <span className="ld-src">
                              {links.map(([name, url]) => (
                                <a key={url} href={url} target="_blank" rel="noopener noreferrer">{name}<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M7 17 17 7M9 7h8v8" /></svg></a>
                              ))}
                            </span>
                          )}
                        </dd>
                      </div>
                    ))}
                  </dl>
                </article>
              ))}
            </div>
            <p className="ld-note rv">ผลเป็นการคาดการณ์จากสถิติ ใช้ประกอบการวางแผนก่อนเดินทาง ไม่ได้รับประกันความปลอดภัย และไม่ใช่ระบบเตือนภัยแบบเรียลไทม์</p>
          </div>
        </section>

        <section className="ld-final">
          <div className="ld-lane ld-lane-top" aria-hidden="true" />
          <div className="ld-wrap ld-final-in">
            <h2 className="rv">พร้อมวางแผนทริปถัดไปแล้วหรือยัง</h2>
            <p className="rv" style={{ "--d": "100ms" }}>ใช้เวลาไม่ถึงนาที รู้ก่อนว่าช่วงไหนของเส้นทางควรขับอย่างระมัดระวัง</p>
            <div className="rv" style={{ "--d": "200ms" }}>
              <button type="button" className="ld-btn ld-btn-lg" onClick={goApp}><span>เริ่มใช้งาน RoadAware</span>{Icon.arrow}</button>
            </div>
          </div>
        </section>
      </main>

      <SiteFooter lane={false} onInfo={() => scrollTo("ld-tech")} />

      <div className="ld-exit" aria-hidden="true"><Logo size={64} /></div>
    </div>
  );
}
