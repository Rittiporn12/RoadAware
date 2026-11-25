// Shared pieces for every page, so the home page, dashboard, model page and app look and move the same way:
// logo, top navigation (with the phone menu), footer, scroll reveal, number count-up, sliding segmented
// controls, and the loading skeletons shown while a page or its data is on the way.
import { useEffect, useRef, useState } from "react";

export const reducedMotion = () => typeof window !== "undefined" && window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

export function Logo({ size = 30, light = true }) {
  return (
    <svg width={size} height={size} viewBox="0 0 26 26" aria-hidden="true" className="logo">
      <circle cx="13" cy="13" r="12" fill={light ? "#FFFFFF" : "#0F1B2D"} />
      <path d="M7 18 C10 12, 13 15, 19 7" stroke="#E8821E" strokeWidth="2.6" fill="none" strokeLinecap="round" />
    </svg>
  );
}

// Go to a section of the home page from another page.
export const goHomeSection = (id) => {
  try { window.sessionStorage.setItem("roadaware.scrollTo", id); } catch (_) { /* ignore */ }
  window.location.hash = "#/";
};

const LINKS = [
  { key: "info", label: "ข้อมูล" },
  { key: "dashboard", label: "แดชบอร์ด", href: "#/dashboard" },
  { key: "model", label: "โมเดล", href: "#/model" },
];

// Top bar used by every page except the app. On the home page it starts see-through over the hero
// (overlay) and turns solid once the page scrolls; elsewhere it is always solid.
// onInfo / onStart / onBrand let the home page scroll in place and play its own exit.
export function SiteNav({ active, overlay = false, scrolled = true, onInfo, onStart, onBrand }) {
  const [open, setOpen] = useState(false);
  useEffect(() => {
    if (!open) return undefined;
    const esc = (e) => { if (e.key === "Escape") setOpen(false); };
    window.addEventListener("keydown", esc);
    return () => window.removeEventListener("keydown", esc);
  }, [open]);
  const scrollTop = () => {
    const el = document.querySelector(".dash, .landing");
    if (el) el.scrollTo({ top: 0, behavior: reducedMotion() ? "auto" : "smooth" });
  };
  const go = (l) => {
    setOpen(false);
    if (l.key === "info") { if (onInfo) onInfo(); else goHomeSection("ld-tech"); return; }
    if (l.key === active) { scrollTop(); return; }
    window.location.hash = l.href;
  };
  const start = () => { setOpen(false); if (onStart) onStart(); else window.location.hash = "#/app"; };
  const solid = !overlay || scrolled || open;
  return (
    <header className={"ld-nav" + (solid ? " is-solid" : "") + (open ? " is-open" : "")}>
      <div className="ld-wrap ld-nav-in">
        <a className="ld-brand" href="#/" onClick={(e) => { if (onBrand) { e.preventDefault(); setOpen(false); onBrand(); } else if (active === "home") { e.preventDefault(); scrollTop(); } }}>
          <Logo /> <span>RoadAware</span>
        </a>
        <nav className="ld-links" aria-label="เมนู">
          {LINKS.map((l) => (
            <button key={l.key} type="button" aria-current={active === l.key ? "page" : undefined} onClick={() => go(l)}>{l.label}</button>
          ))}
        </nav>
        <button type="button" className="ld-btn ld-btn-sm ld-nav-cta" onClick={start}>เริ่มใช้งาน</button>
        <button type="button" className="nav-burger" aria-label={open ? "ปิดเมนู" : "เปิดเมนู"} aria-expanded={open} aria-controls="nav-sheet" onClick={() => setOpen((o) => !o)}>
          <span /><span />
        </button>
      </div>
      <div id="nav-sheet" className="nav-sheet" hidden={!open}>
        <div className="ld-wrap">
          {LINKS.map((l, i) => (
            <button key={l.key} type="button" style={{ "--i": i }} aria-current={active === l.key ? "page" : undefined} onClick={() => go(l)}>
              <span>{l.label}</span>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M9 6l6 6-6 6" /></svg>
            </button>
          ))}
          <button type="button" className="ld-btn ld-btn-lg nav-sheet-cta" style={{ "--i": LINKS.length }} onClick={start}>เริ่มใช้งาน RoadAware</button>
        </div>
      </div>
      {open && <button type="button" className="nav-scrim" aria-label="ปิดเมนู" tabIndex={-1} onClick={() => setOpen(false)} />}
    </header>
  );
}

const TEAM = [
  ["66088346", "นายฤทธิพร ผึ่งผาย"],
  ["66088226", "นายกันณพิช เบ้าศรี"],
  ["66080740", "นางสาววรรณษา วงค์ดี"],
  ["66092559", "นายจริยธรรม มาสงค์"],
];

export function SiteFooter({ lane = true, onInfo }) {
  return (
    <footer className="site-foot">
      {lane && <div className="ld-lane" aria-hidden="true" />}
      <div className="ld-wrap site-foot-in">
        <div className="site-foot-brand">
          <span className="ld-brand"><Logo size={28} /> <span>RoadAware</span></span>
          <p>รู้ก่อนออกเดินทาง ว่าช่วงไหนควรระวัง</p>
        </div>
        <nav className="site-foot-nav" aria-label="ลิงก์ท้ายหน้า">
          <h3>เมนู</h3>
          <a href="#/">หน้าแรก</a>
          <a href="#/" onClick={(e) => { e.preventDefault(); if (onInfo) onInfo(); else goHomeSection("ld-tech"); }}>ข้อมูล</a>
          <a href="#/dashboard">แดชบอร์ด</a>
          <a href="#/model">โมเดล</a>
          <a href="#/app">เริ่มใช้งาน</a>
        </nav>
        <div>
          <h3>ผู้พัฒนา</h3>
          <ul className="ld-team">
            {TEAM.map(([id, name]) => <li key={id}><span>{name}</span><small>{id}</small></li>)}
          </ul>
        </div>
      </div>
    </footer>
  );
}

// Adds .in to .rv elements as they scroll into view (once). Call again when new .rv elements mount.
export function useReveal(deps = []) {
  useEffect(() => {
    const els = document.querySelectorAll(".rv:not(.in)");
    if (reducedMotion() || !("IntersectionObserver" in window)) { els.forEach((e) => e.classList.add("in")); return undefined; }
    const io = new IntersectionObserver((entries) => entries.forEach((e) => {
      if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); }
    }), { threshold: 0.1, rootMargin: "0px 0px -6% 0px" });
    els.forEach((e) => io.observe(e));
    return () => io.disconnect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
}

// A number that rolls to its new value (first show and every change). format turns the number into text.
export function CountUp({ value, format = (v) => Math.round(v).toLocaleString("en-US"), duration = 700 }) {
  const [shown, setShown] = useState(reducedMotion() ? value : 0);
  const from = useRef(reducedMotion() ? value : 0);
  useEffect(() => {
    if (reducedMotion()) { setShown(value); from.current = value; return undefined; }
    const a = from.current, b = value, t0 = performance.now();
    let raf;
    const tick = (t) => {
      const k = Math.min(1, (t - t0) / duration);
      const e = 1 - Math.pow(1 - k, 3);
      const v = a + (b - a) * e;
      setShown(v);
      from.current = v;
      if (k < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [value, duration]);
  return <>{format(shown)}</>;
}

// Segmented controls ([data-seg]) get a sliding highlight under the selected option (.is-on).
// One observer for the whole document; components only add the attribute.
export function installSegments() {
  if (typeof window === "undefined" || window.__segOn) return;
  window.__segOn = true;
  let raf = 0;
  const place = () => {
    raf = 0;
    document.querySelectorAll("[data-seg]").forEach((box) => {
      const on = box.querySelector(":scope > .is-on");
      if (!on) { box.style.setProperty("--seg-w", "0px"); return; }
      box.style.setProperty("--seg-x", on.offsetLeft + "px");
      box.style.setProperty("--seg-y", on.offsetTop + "px");
      box.style.setProperty("--seg-w", on.offsetWidth + "px");
      box.style.setProperty("--seg-h", on.offsetHeight + "px");
      if (!box.classList.contains("seg-ready")) requestAnimationFrame(() => box.classList.add("seg-ready"));
    });
  };
  const queue = () => { if (!raf) raf = requestAnimationFrame(place); };
  new MutationObserver(queue).observe(document.body, { subtree: true, childList: true, attributes: true, attributeFilter: ["class"] });
  window.addEventListener("resize", queue);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(queue);
  queue();
}

// Placeholder shapes shown while a page or its data loads, in the page's own layout.
export function PageSkeleton({ kind = "page" }) {
  if (kind === "app") {
    return (
      <div className="sk-app" aria-busy="true" aria-label="กำลังเปิด RoadAware">
        <div className="sk-topbar"><span className="ld-brand"><Logo size={28} /> <span>RoadAware</span></span></div>
        <div className="sk-app-body">
          <div className="sk-panel">
            <i className="sk sk-pill" /><i className="sk sk-h" /><i className="sk sk-t" /><i className="sk sk-box" /><i className="sk sk-row" /><i className="sk sk-btn" />
          </div>
          <div className="sk-map"><i className="sk" /></div>
        </div>
      </div>
    );
  }
  return (
    <div className="dash" aria-busy="true" aria-label="กำลังโหลด">
      <SiteNav active={kind} />
      <PageBody kind={kind} />
    </div>
  );
}
export function PageBody({ kind }) {
  return (
    <>
      <header className="page-hero">
        <div className="ld-wrap">
          <i className="sk sk-dark sk-eyebrow" /><i className="sk sk-dark sk-title" />
          {kind === "model" && <div className="sk-kpis">{[0, 1, 2, 3].map((i) => <i key={i} className="sk sk-dark sk-kpi" />)}</div>}
        </div>
        <div className="ld-lane" aria-hidden="true" />
      </header>
      <main className="ld-wrap sk-body">
        <i className="sk sk-bar" />
        <div className="sk-grid">{[0, 1, 2, 3].map((i) => <i key={i} className="sk sk-card" />)}</div>
        <i className="sk sk-wide" />
      </main>
    </>
  );
}

// Thailand with the accident hotspots glowing (same data as the home hero, no route). Decorative.
const HERO_URL = ((import.meta.env && import.meta.env.BASE_URL) || "./") + "data/hero-map.json";
let heroCache = null;
export function useHeroMap() {
  const [geo, setGeo] = useState(heroCache);
  useEffect(() => {
    if (heroCache) return undefined;
    let alive = true;
    fetch(HERO_URL).then((r) => (r.ok ? r.json() : null)).then((j) => { if (j) { heroCache = j; if (alive) setGeo(j); } }).catch(() => {});
    return () => { alive = false; };
  }, []);
  return geo;
}
export function NationGlow({ className = "", viewBox = "40 20 440 560" }) {
  const geo = useHeroMap();
  return (
    <div className={"ng " + className} aria-hidden="true">
      {geo && (
        <svg viewBox={viewBox} preserveAspectRatio="xMidYMid meet">
          <path className="ng-land" d={geo.path} />
          <path className="ng-r2" d={geo.roads.mid} />
          <path className="ng-r1" d={geo.roads.major} />
          <path className="ng-coast" d={geo.path} pathLength="1" />
        </svg>
      )}
    </div>
  );
}
