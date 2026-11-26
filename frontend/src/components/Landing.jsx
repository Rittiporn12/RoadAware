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

const VOICE = ["ข้างหน้าอีก 2 กิโลเมตร มีจุดที่ควรระวัง", "ระวัง! อีก 500 เมตร ถึงจุดที่ 1", "เข้าสู่จุดที่ควรระวังแล้ว ตั้งใจขับนะ"];

// Hero visual: an app-style map card of Thailand — the real boundary and DOH highway network (main routes as white
// roads), a Bangkok → Chiang Mai trip on highways 1/32/11 that draws itself, the points RoadAware would flag,
// a car driving it, and the spoken warning changing as it goes. Data: public/data/hero-map.json
// (backend/scripts/build_hero_map.py). The trip and its points are an illustration, not a live forecast.
const HERO_URL = ((import.meta.env && import.meta.env.BASE_URL) || "./") + "data/hero-map.json";
const MARKS = [[0.2, "red", 1], [0.52, "orange", 2], [0.8, "red", 3]];
const PRJ = (lon, lat) => [(lon - 97.2) * 60 * Math.cos((13 * Math.PI) / 180), (20.6 - lat) * 60];
const PLACES = [["พิษณุโลก", 100.55, 16.82], ["ขอนแก่น", 102.83, 16.43], ["นครราชสีมา", 102.1, 14.97], ["อุดรธานี", 102.79, 17.41], ["น่าน", 100.77, 18.78]];
const SHIELDS = [["1", 99.0, 16.7], ["32", 100.62, 14.7], ["11", 99.85, 18.05], ["2", 102.0, 15.55]];
function HeroMap() {
  const [geo, setGeo] = useState(null);
  const [pts, setPts] = useState(null);
  const [voice, setVoice] = useState(0);
  const routeRef = useRef(null);
  const motion = !reducedMotion();
  useEffect(() => {
    let alive = true;
    fetch(HERO_URL).then((r) => (r.ok ? r.json() : null)).then((j) => { if (alive && j) setGeo(j); }).catch(() => {});
    return () => { alive = false; };
  }, []);
  useEffect(() => {
    const p = routeRef.current;
    if (p && p.getTotalLength) {
      const L = p.getTotalLength();
      setPts(MARKS.map(([f]) => { const q = p.getPointAtLength(L * f); return [q.x, q.y]; }));
    }
  }, [geo]);
  useEffect(() => {
    if (!motion) return undefined;
    const t = setInterval(() => setVoice((v) => (v + 1) % VOICE.length), 3400);
    return () => clearInterval(t);
  }, [motion]);
  const routeD = geo ? "M" + geo.route.map(([x, y]) => x + " " + y).join(" L") : "";
  const start = geo && geo.route[0], end = geo && geo.route[geo.route.length - 1];
  return (
    <div className="hm nm" aria-hidden="true">
      <div className="nm-tilt"><div className="hm-card nm-card">
        {geo && (
          <svg viewBox="44 52 436 488" preserveAspectRatio="xMidYMid slice">
            <defs>
              <filter id="nmBlur" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="4" /></filter>
              <radialGradient id="nmVig" cx="50%" cy="45%" r="70%"><stop offset="55%" stopColor="#0B1422" stopOpacity="0" /><stop offset="100%" stopColor="#0B1422" stopOpacity=".85" /></radialGradient>
            </defs>
            <rect x="0" y="0" width="600" height="600" className="nm-out" />
            <path className="nm-land" d={geo.path} />
            <path className="nm-r3" d={geo.roads.minor} />
            <path className="nm-r2c" d={geo.roads.mid} /><path className="nm-r1c" d={geo.roads.major} />
            <path className="nm-r2" d={geo.roads.mid} /><path className="nm-r1" d={geo.roads.major} />
            <path className="nm-coast" d={geo.path} />
            {PLACES.map(([n, lon, lat]) => { const [x, y] = PRJ(lon, lat); return <text key={n} x={x} y={y} className="nm-place">{n}</text>; })}
            {SHIELDS.map(([n, lon, lat]) => { const [x, y] = PRJ(lon, lat); const w = n.length > 1 ? 20 : 15; return <g key={n} className="nm-shield" transform={`translate(${x} ${y})`}><rect x={-w / 2} y="-7.5" width={w} height="15" rx="3" /><text y="4" textAnchor="middle">{n}</text></g>; })}
            <path d={routeD} className="nm-route-glow" filter="url(#nmBlur)" />
            <path d={routeD} className="nm-route-under" />
            <path ref={routeRef} id="nmRoute" d={routeD} className="nm-route" pathLength="1" />
            {motion && (
              <g className="nm-car">
                <animateMotion dur="10s" begin="2.8s" repeatCount="indefinite"><mpath href="#nmRoute" /></animateMotion>
                <circle r="8" fill="#0F1B2D" opacity=".18" /><circle r="5.5" fill="#fff" stroke="#0F1B2D" strokeWidth="2.2" /><circle r="2" fill="#0F1B2D" />
              </g>
            )}
            {pts && MARKS.map(([, lvl, n], i) => (
              <g key={n} className={"nm-mark nm-mark-" + (i + 1)} transform={`translate(${pts[i][0]} ${pts[i][1]})`}>
                <circle className="hm-ring" r="11" fill="none" stroke={LEVELS[lvl].hex} strokeWidth="2.2" />
                <circle r="11" fill={LEVELS[lvl].hex} stroke="#fff" strokeWidth="2.6" /><text y="4" textAnchor="middle">{n}</text>
              </g>
            ))}
            <g className="nm-pin nm-pin-a" transform={`translate(${start[0]} ${start[1]})`}><circle r="11" fill="#24497A" stroke="#fff" strokeWidth="2.6" /><text y="4" textAnchor="middle">A</text></g>
            <g className="nm-pin nm-pin-b" transform={`translate(${end[0]} ${end[1]})`}><circle r="11" fill="#E8821E" stroke="#fff" strokeWidth="2.6" /><text y="4" textAnchor="middle">B</text></g>
            <rect x="0" y="0" width="600" height="600" fill="url(#nmVig)" pointerEvents="none" />
            <text x={start[0] + 16} y={start[1] + 5} className="nm-city nm-city-a">กรุงเทพฯ</text>
            <text x={end[0] + 16} y={end[1] + 5} className="nm-city nm-city-b">เชียงใหม่</text>
          </svg>
        )}
      </div></div>
      <div className="hm-float hm-brief">
        <span className="hm-brief-n">3</span>
        <span><b>จุดที่ควรระวัง</b><small>กรุงเทพฯ → เชียงใหม่ · สูงมาก 2 · สูง 1</small></span>
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
  { icon: Icon.review, title: "ที่ผ่านมาเกิดอะไรบ้าง", text: "กดที่จุดที่ควรระวังเพื่อดูว่าที่ผ่านมาส่วนใหญ่เกิดเหตุแบบไหน ช่วงเวลาไหน เกิดตอนฝนตกบ่อยแค่ไหน พร้อมคำแนะนำก่อนถึงจุดนั้น" },
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
      ["อัลกอริทึม", "HistGradientBoosting (ตั้ง loss เป็น Poisson) คาดจำนวนอุบัติเหตุที่จะถูกบันทึกต่อช่วงถนน", [["scikit-learn: HistGradientBoostingRegressor", "https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.HistGradientBoostingRegressor.html"]]],
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
                <span className="ld-line ld-mask"><span style={{ "--d": "80ms" }}>รู้ก่อนออกเดินทาง</span></span>
                <span className="ld-line ld-mask"><span style={{ "--d": "220ms" }}>ว่าช่วงไหน<span className="ld-accent">ควรระวัง</span></span></span>
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
