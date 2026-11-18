import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { DATE_MIN, DATE_MAX, LAST_OBSERVED_DATE, BLOCK_LABEL, CONFIG } from "./config.js";
import { api, fetchJson, bkkToEpoch, epochToBkk, pad2, isNum, techText, isServiceDown, routeLabel } from "./lib/util.js";
import { geocode } from "./lib/geocode.js";
import { buildRouteIndex } from "./lib/routeMatch.js";
import { runForecast, fetchHistory } from "./lib/forecast.js";
import MapView from "./components/MapView.jsx";
import PlaceField from "./components/PlaceField.jsx";
import RouteSummary from "./components/RouteSummary.jsx";
import Legend from "./components/Legend.jsx";
import SpotList from "./components/SpotList.jsx";
import { SpotPopup, SpotDetail } from "./components/SpotInfo.jsx";
import { ErrorBox, Loading, Progress } from "./components/common.jsx";

const IDLE = { status: "idle", places: [] };
const NO_SPOTS = [];
const isMobile = () => window.matchMedia("(max-width: 860px)").matches;

function defaultWhen() {
  const now = epochToBkk(Date.now() + 5 * 60 * 1000);
  let date = now.date;
  if (date < DATE_MIN) date = DATE_MIN;
  if (date > DATE_MAX) date = DATE_MAX;
  return { date, time: pad2(now.hour) + ":" + pad2(Math.floor(now.minute / 5) * 5) };
}
const whenValid = (w) => /^\d{4}-\d{2}-\d{2}$/.test(w.date) && w.date >= DATE_MIN && w.date <= DATE_MAX && /^\d{2}:\d{2}$/.test(w.time);
const histKey = (g) => g.primary.id + "|" + g.primary.eta.date;
const samePlace = (a, b) => a && b && Math.abs(a.lat - b.lat) < 1e-5 && Math.abs(a.lon - b.lon) < 1e-5;

export default function App() {
  // ML service readiness
  const [ready, setReady] = useState("checking");
  const readyRef = useRef("checking");
  readyRef.current = ready;
  const readyCtrl = useRef(null);
  const [provinces, setProvinces] = useState(() => new Map());

  // trip inputs
  const [texts, setTexts] = useState({ origin: "", dest: "" });
  const [places, setPlaces] = useState({ origin: null, dest: null });
  const [results, setResults] = useState({ origin: IDLE, dest: IDLE });
  const searchRef = useRef({ origin: { ctrl: null, gen: 0 }, dest: { ctrl: null, gen: 0 } });
  const [pick, setPick] = useState(null);
  const [when, setWhen] = useState(defaultWhen);

  // route + forecast
  const [trip, setTrip] = useState({ status: "idle" });
  const [route, setRoute] = useState(null);
  const tripGen = useRef(0);
  const routeCtrl = useRef(null);
  const [forecast, setForecast] = useState({ status: "idle" });
  const [retryNonce, setRetryNonce] = useState(0);

  // spots
  const [hidden, setHidden] = useState(() => new Set());
  const [selectedKey, setSelectedKey] = useState(null);
  const [focus, setFocus] = useState(null);
  const [history, setHistory] = useState({});
  const historyRef = useRef({});

  // chrome
  const [sheet, setSheet] = useState("default");
  const [toast, setToast] = useState(null);
  const [mapFailed, setMapFailed] = useState(false);
  const panelRef = useRef(null);
  const detailRef = useRef(null);

  // ---------------------------------------------------------------- readiness
  const checkReady = useCallback(async () => {
    if (readyCtrl.current) readyCtrl.current.abort();
    const ctrl = new AbortController();
    readyCtrl.current = ctrl;
    setReady("checking");
    let ok = false;
    try {
      const json = await api("/ready", { signal: ctrl.signal });
      ok = json.research_backend_ready === true;
    } catch (_) { ok = false; }
    if (readyCtrl.current !== ctrl) return ok;
    readyCtrl.current = null;
    setReady(ok ? "ready" : "down");
    return ok;
  }, []);

  useEffect(() => { checkReady(); }, [checkReady]);

  useEffect(() => {
    if (ready !== "ready" || provinces.size > 0) return;
    api("/api/v1/provinces")
      .then((json) => {
        const m = new Map();
        for (const p of Array.isArray(json.provinces) ? json.provinces : []) {
          const n = Number(p && p.province_code);
          if (Number.isFinite(n)) m.set(String(n), p);
        }
        setProvinces(m);
      })
      .catch(() => { /* names are optional context */ });
  }, [ready, provinces.size]);

  const titleOf = useCallback((g) => {
    const pr = g.primary.props;
    const n = Number(pr.province_code);
    const p = Number.isFinite(n) ? provinces.get(String(n)) : null;
    return routeLabel(pr.route_code) + (p && typeof p.name_th === "string" ? " · " + p.name_th : "");
  }, [provinces]);

  // ---------------------------------------------------------------- toast
  const showToast = useCallback((text) => setToast({ text, at: Date.now() }), []);
  useEffect(() => {
    if (!toast) return undefined;
    const t = setTimeout(() => setToast(null), 3500);
    return () => clearTimeout(t);
  }, [toast]);

  // ---------------------------------------------------------------- route lifecycle
  const invalidateRoute = useCallback(() => {
    tripGen.current += 1;
    if (routeCtrl.current) { routeCtrl.current.abort(); routeCtrl.current = null; }
    setRoute(null);
    setTrip({ status: "idle" });
    setSelectedKey(null);
  }, []);

  const runTrip = useCallback(async (o, d) => {
    if (!o || !d || samePlace(o, d)) return;
    invalidateRoute();
    setPick(null);
    const gen = tripGen.current;
    const ctrl = new AbortController();
    routeCtrl.current = ctrl;
    setTrip({ status: "loading" });
    let json;
    try {
      const url = CONFIG.osrmUrl + o.lon.toFixed(6) + "," + o.lat.toFixed(6) + ";" + d.lon.toFixed(6) + "," + d.lat.toFixed(6) +
        "?overview=full&geometries=geojson&steps=false&alternatives=false";
      json = await fetchJson(url, { signal: ctrl.signal, timeoutMs: 25000 });
    } catch (f) {
      if (gen !== tripGen.current || f.kind === "aborted") return;
      const code = f.body && f.body.code;
      let title = "หาเส้นทางไม่สำเร็จ", text = "บริการเส้นทางไม่ตอบสนอง ลองอีกครั้งในอีกสักครู่";
      if (code === "NoRoute") { title = "ไม่พบเส้นทางรถยนต์"; text = "ไม่พบเส้นทางขับรถระหว่างสองจุดนี้ ลองเลือกจุดที่อยู่ใกล้ถนนมากขึ้น"; }
      if (code === "NoSegment") { title = "จุดที่เลือกอยู่ไกลจากถนน"; text = "ไม่พบถนนใกล้จุดต้นทางหรือปลายทาง ลองเลือกจุดใหม่"; }
      setTrip({ status: "error", title, text, tech: techText(f) });
      return;
    } finally {
      if (routeCtrl.current === ctrl) routeCtrl.current = null;
    }
    if (gen !== tripGen.current) return;
    const r = json && json.code === "Ok" && Array.isArray(json.routes) ? json.routes[0] : null;
    const coords = r && r.geometry && Array.isArray(r.geometry.coordinates) ? r.geometry.coordinates : null;
    if (!r || !coords || coords.length < 2 || !isNum(r.distance) || !isNum(r.duration)) {
      setTrip({ status: "error", title: "ไม่พบเส้นทางรถยนต์", text: "บริการเส้นทางไม่ได้ส่งเส้นทางกลับมา", tech: json && json.code ? String(json.code) : null });
      return;
    }
    let index = null;
    try { index = buildRouteIndex(coords); } catch (_) { index = null; }
    const snaps = Array.isArray(json.waypoints) ? json.waypoints.map((w) => (isNum(w.distance) ? w.distance : 0)) : [0, 0];
    setTrip({ status: "idle" });
    setRoute({ coords, distance: r.distance, duration: r.duration, snaps, index, origin: o, dest: d });
    if (isMobile()) setSheet("default");
  }, [invalidateRoute]);

  // Forecast follows the route and the departure time; any change cancels the previous run.
  useEffect(() => {
    setSelectedKey(null);
    if (!route) { setForecast({ status: "idle" }); return undefined; }
    if (!whenValid(when)) { setForecast({ status: "needWhen" }); return undefined; }
    if (!route.index) { setForecast({ status: "tooShort" }); return undefined; }
    let alive = true;
    const ctrl = new AbortController();
    setForecast({ status: "loading", text: "กำลังเตรียมประเมินจุดเสี่ยง…", frac: 0 });
    const timer = setTimeout(async () => {
      try {
        if (readyRef.current !== "ready") {
          setForecast({ status: "loading", text: "กำลังเชื่อมต่อระบบประเมินความเสี่ยง…" });
          const ok = await checkReady();
          if (!alive) return;
          if (!ok) { setForecast({ status: "notReady" }); return; }
        }
        const res = await runForecast({
          route, date: when.date, time: when.time, signal: ctrl.signal,
          onProgress: (text, frac) => { if (alive) setForecast({ status: "loading", text, frac }); },
        });
        if (!alive) return;
        setForecast({ status: res.items.length ? "done" : "none", ...res });
      } catch (f) {
        if (!alive || (f && f.kind === "aborted")) return;
        if (isServiceDown(f)) setReady("down");
        setForecast({ status: "error", failure: f });
      }
    }, 300);
    return () => { alive = false; clearTimeout(timer); ctrl.abort(); };
  }, [route, when, retryNonce, checkReady]);

  const spots = forecast.status === "done" ? forecast.spots : NO_SPOTS;
  const selected = useMemo(() => spots.find((s) => s.key === selectedKey) || null, [spots, selectedKey]);

  // ---------------------------------------------------------------- history ("mostly caused by")
  const setHist = useCallback((key, entry) => {
    historyRef.current = { ...historyRef.current, [key]: entry };
    setHistory(historyRef.current);
  }, []);

  const loadHistory = useCallback(async (g, force) => {
    const key = histKey(g);
    const cur = historyRef.current[key];
    if (!force && cur && cur.status !== "error") return;
    setHist(key, { status: "loading" });
    try {
      const res = await fetchHistory(g);
      setHist(key, { status: "ok", ...res });
    } catch (f) {
      setHist(key, { status: "error", failure: f });
    }
  }, [setHist]);

  const selectSpot = useCallback((key, fromList) => {
    const g = spots.find((s) => s.key === key);
    if (!g) return;
    setSelectedKey(key);
    if (fromList) setFocus({ key, n: Date.now() });
    loadHistory(g);
  }, [spots, loadHistory]);

  const openDetail = useCallback(() => {
    if (isMobile()) setSheet("expanded");
    setTimeout(() => detailRef.current && detailRef.current.scrollIntoView({ behavior: "smooth", block: "start" }), 60);
  }, []);

  // ---------------------------------------------------------------- inputs
  const runSearch = useCallback(async (which, query) => {
    const q = (query ?? "").trim();
    const s = searchRef.current[which];
    if (s.ctrl) s.ctrl.abort();
    if (q.length < 2) { setResults((r) => ({ ...r, [which]: { status: "short", places: [] } })); return; }
    const ctrl = new AbortController();
    const gen = ++s.gen;
    s.ctrl = ctrl;
    setResults((r) => ({ ...r, [which]: { status: "loading", places: [] } }));
    try {
      const found = await geocode(q, ctrl.signal);
      if (gen !== s.gen) return;
      setResults((r) => ({ ...r, [which]: { status: "ok", places: found } }));
    } catch (f) {
      if (gen !== s.gen || (f && f.kind === "aborted")) return;
      setResults((r) => ({ ...r, [which]: { status: "error", places: [], tech: techText(f) } }));
    } finally {
      if (s.ctrl === ctrl) s.ctrl = null;
    }
  }, []);

  const choosePlace = useCallback((which, p) => {
    setPlaces((cur) => ({ ...cur, [which]: p }));
    setTexts((cur) => ({ ...cur, [which]: p.name }));
    setResults((r) => ({ ...r, [which]: IDLE }));
    invalidateRoute();
  }, [invalidateRoute]);

  const onText = useCallback((which, value) => {
    setTexts((cur) => ({ ...cur, [which]: value }));
    // Editing the text un-confirms the chosen place and the route built from it.
    if (places[which] && value.trim() !== places[which].name) {
      setPlaces((cur) => ({ ...cur, [which]: null }));
      invalidateRoute();
    }
    if (value.trim() === "") setResults((r) => ({ ...r, [which]: IDLE }));
  }, [places, invalidateRoute]);

  const onPickPoint = useCallback((lat, lon) => {
    const which = pick;
    if (!which) return;
    setPick(null);
    choosePlace(which, { id: "map", name: "จุดบนแผนที่ (" + lat.toFixed(4) + ", " + lon.toFixed(4) + ")", sub: "เลือกจากแผนที่", lat, lon, source: "map" });
    if (isMobile()) setSheet("default");
  }, [pick, choosePlace]);

  const togglePick = (which) => {
    const next = pick === which ? null : which;
    setPick(next);
    if (next && isMobile()) setSheet("collapsed");
  };

  const swap = () => {
    const o = places.dest, d = places.origin;
    const hadRoute = !!route;
    setPlaces({ origin: o, dest: d });
    setTexts((t) => ({ origin: t.dest, dest: t.origin }));
    setResults({ origin: IDLE, dest: IDLE });
    invalidateRoute();
    if (hadRoute && o && d) runTrip(o, d);
  };

  const runExample = async () => {
    const o = "มหาวิทยาลัยศรีปทุม", d = "อุทยานแห่งชาติเขาใหญ่";
    setTexts({ origin: o, dest: d });
    setPlaces({ origin: null, dest: null });
    invalidateRoute();
    setTrip({ status: "hint" });
    await runSearch("origin", o);
    await runSearch("dest", d);
  };

  useEffect(() => {
    const onKey = (e) => { if (e.key === "Escape") setPick(null); };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  const getPadding = useCallback(() => {
    if (isMobile() && panelRef.current) return { paddingTopLeft: [24, 70], paddingBottomRight: [24, panelRef.current.offsetHeight + 16] };
    return { padding: [40, 40] };
  }, []);

  const toggleLevel = (lv) => setHidden((cur) => {
    const n = new Set(cur);
    if (n.has(lv)) n.delete(lv); else n.add(lv);
    return n;
  });

  // ---------------------------------------------------------------- derived text
  const whenNote = useMemo(() => {
    if (!whenValid(when)) return "เลือกวันที่ระหว่าง 1 ม.ค. 2567 ถึง 31 ธ.ค. 2570 และเวลาออกเดินทาง";
    const e = epochToBkk(bkkToEpoch(when.date, when.time));
    let t = "ออกเดินทางช่วง " + BLOCK_LABEL[e.block] + " — แต่ละจุดประเมินตามช่วง 6 ชั่วโมงที่คาดว่าคุณจะผ่านจุดนั้น";
    if (e.date > LAST_OBSERVED_DATE) t += " · วันที่นี้เป็นการคาดการณ์เชิงวิจัย";
    return t;
  }, [when]);

  const canRoute = !!(places.origin && places.dest && whenValid(when)) && !samePlace(places.origin, places.dest) && trip.status !== "loading";
  const showResults = route !== null;
  const items = forecast.status === "done" ? forecast.items : null;
  const panelClass = "panel" + (sheet === "collapsed" ? " is-collapsed" : sheet === "expanded" ? " is-expanded" : "");

  return (
    <>
      <a className="skip-link" href="#panel">ข้ามไปยังแผงวางแผนการเดินทาง</a>
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true" />
          <span className="brand-name">RoadAware</span>
          <span className="badge" title="ผลลัพธ์มาจากแบบจำลองงานวิจัย ยังไม่ใช่บริการใช้งานจริง">ต้นแบบงานวิจัย</span>
        </div>
        <div className="status" role="status" aria-live="polite">
          <span className={"status-dot " + (ready === "ready" ? "is-ready" : ready === "down" ? "is-down" : "is-checking")} aria-hidden="true" />
          <span id="statusText">{ready === "ready" ? "ระบบประเมินความเสี่ยงพร้อม" : ready === "down" ? "ระบบประเมินยังไม่พร้อม (ดูเส้นทางได้)" : "กำลังเชื่อมต่อระบบประเมิน…"}</span>
          {ready === "down" && (
            <button type="button" className="btn btn-ghost btn-small" onClick={async () => { const ok = await checkReady(); if (ok && route) setRetryNonce((n) => n + 1); }}>ลองอีกครั้ง</button>
          )}
        </div>
      </header>

      <main className="workspace">
        <section className="map-pane" aria-label="แผนที่ประเทศไทย">
          {!mapFailed && (
            <MapView
              route={route} origin={places.origin} dest={places.dest} spots={spots} hiddenLevels={hidden}
              selectedKey={selected ? selected.key : null} focus={focus} pick={pick} getPadding={getPadding}
              onPick={onPickPoint} onOutside={() => showToast("เลือกได้เฉพาะพื้นที่ในประเทศไทย")}
              onSelectSpot={selectSpot} onFailed={() => setMapFailed(true)}
            >
              {selected && <SpotPopup spot={selected} title={titleOf(selected)} entry={history[histKey(selected)]} onMore={openDetail} />}
            </MapView>
          )}
          {mapFailed && (
            <div className="map-fallback">
              <div className="map-fallback-card">
                <h2>แผนที่ยังแสดงไม่ได้</h2>
                <p>โหลดแผนที่ไม่สำเร็จ ยังค้นหาสถานที่และดูรายการจุดเสี่ยงในแผงด้านข้างได้</p>
              </div>
            </div>
          )}
          {pick && (
            <div className="pick-banner" role="status">
              <span>{pick === "origin" ? "แตะบนแผนที่เพื่อเลือกต้นทาง (A)" : "แตะบนแผนที่เพื่อเลือกปลายทาง (B)"}</span>
              <button type="button" className="btn btn-ghost btn-small" onClick={() => { setPick(null); if (isMobile()) setSheet("default"); }}>ยกเลิก</button>
            </div>
          )}
          {forecast.status === "done" && !mapFailed && <Legend spots={spots} hidden={hidden} onToggle={toggleLevel} />}
          {toast && <p className="toast" role="status">{toast.text}</p>}
        </section>

        <aside id="panel" ref={panelRef} className={panelClass} tabIndex={-1} aria-label="วางแผนการเดินทาง">
          <button type="button" className="sheet-handle" aria-expanded={sheet !== "collapsed"} aria-controls="panelBody"
            onClick={() => setSheet((s) => (s === "collapsed" ? "default" : s === "expanded" ? "collapsed" : "expanded"))}>
            <span className="sheet-grip" aria-hidden="true" />
            <span className="visually-hidden">{sheet === "collapsed" ? "ขยายแผง" : "ย่อ/ขยายแผง"}</span>
          </button>

          <div id="panelBody" className="panel-body">
            <section className="trip" aria-labelledby="tripTitle">
              <h1 id="tripTitle">จะเดินทางไปไหน?</h1>
              <p className="lead">ค้นหาต้นทางและปลายทาง ระบบจะแสดงเส้นทางและวงกลมจุดที่ควรระวังตามเวลาที่คาดว่าจะผ่าน</p>

              <div className="places">
                <PlaceField which="origin" letter="A" label="ต้นทาง" placeholder="เช่น มหาวิทยาลัยศรีปทุม"
                  text={texts.origin} place={places.origin} results={results.origin} picking={pick === "origin"}
                  onText={(v) => onText("origin", v)} onSearch={() => runSearch("origin", texts.origin)}
                  onChoose={(p) => choosePlace("origin", p)} onPick={() => togglePick("origin")}
                  onCloseResults={() => setResults((r) => ({ ...r, origin: IDLE }))} />
                <button type="button" className="btn btn-swap" aria-label="สลับต้นทางและปลายทาง" title="สลับต้นทาง/ปลายทาง" onClick={swap}>⇅</button>
                <PlaceField which="dest" letter="B" label="ปลายทาง" placeholder="เช่น อุทยานแห่งชาติเขาใหญ่"
                  text={texts.dest} place={places.dest} results={results.dest} picking={pick === "dest"}
                  onText={(v) => onText("dest", v)} onSearch={() => runSearch("dest", texts.dest)}
                  onChoose={(p) => choosePlace("dest", p)} onPick={() => togglePick("dest")}
                  onCloseResults={() => setResults((r) => ({ ...r, dest: IDLE }))} />
              </div>

              <button type="button" className="link-btn example" onClick={runExample}>ลองตัวอย่าง: ม.ศรีปทุม → อุทยานแห่งชาติเขาใหญ่</button>

              <div className="when">
                <label className="field">
                  <span className="field-label">วันที่ออกเดินทาง</span>
                  <input type="date" min={DATE_MIN} max={DATE_MAX} required value={when.date} onChange={(e) => setWhen((w) => ({ ...w, date: e.target.value }))} />
                </label>
                <label className="field">
                  <span className="field-label">เวลาออกเดินทาง</span>
                  <input type="time" step={300} required value={when.time} onChange={(e) => setWhen((w) => ({ ...w, time: e.target.value }))} />
                </label>
              </div>
              <p className="help">{whenNote}</p>

              <button type="button" className="btn btn-primary btn-block" style={{ marginTop: 14 }} disabled={!canRoute}
                onClick={() => runTrip(places.origin, places.dest)}>
                ดูเส้นทางและจุดเสี่ยง
              </button>
              <div className="trip-status" aria-live="polite">
                {trip.status === "loading" && <Loading text="กำลังหาเส้นทาง…" />}
                {trip.status === "error" && <ErrorBox title={trip.title} text={trip.text} technical={trip.tech} onRetry={() => runTrip(places.origin, places.dest)} />}
                {trip.status === "hint" && <p className="notice is-info">เลือกผลการค้นหาที่ถูกต้องทั้งสองช่อง — ม.ศรีปทุมมีหลายวิทยาเขต และ “เขาใหญ่” มีหลายแห่งในประเทศไทย</p>}
              </div>
            </section>

            {showResults && (
              <section className="card-section" aria-labelledby="routeTitle">
                <h2 id="routeTitle">สรุปเส้นทาง</h2>
                <RouteSummary route={route} date={when.date} time={when.time} items={items} />
                <div className="forecast-status" aria-live="polite">
                  {forecast.status === "loading" && <Progress text={forecast.text} frac={forecast.frac} />}
                  {forecast.status === "needWhen" && <p className="notice">เลือกวันที่ (1 ม.ค. 2567 – 31 ธ.ค. 2570) และเวลาออกเดินทางเพื่อประเมินจุดเสี่ยง</p>}
                  {forecast.status === "tooShort" && <p className="notice">เส้นทางนี้สั้นเกินไปสำหรับการประเมินตามเส้นทาง</p>}
                  {forecast.status === "notReady" && (
                    <ErrorBox title="ระบบประเมินความเสี่ยงยังไม่พร้อม" text="เส้นทางยังใช้งานได้ตามปกติ แต่ยังแสดงจุดเสี่ยงไม่ได้ ตรวจว่าเปิด backend แล้ว แล้วลองอีกครั้ง" onRetry={() => setRetryNonce((n) => n + 1)} />
                  )}
                  {forecast.status === "error" && (
                    <ErrorBox title="ประเมินความเสี่ยงไม่สำเร็จ" text="ไม่แสดงผลบางส่วนเพื่อไม่ให้เข้าใจผิด เส้นทางยังใช้งานได้" technical={techText(forecast.failure)} onRetry={() => setRetryNonce((n) => n + 1)} />
                  )}
                  {forecast.status === "none" && (
                    <p className="notice">
                      {forecast.outOfRange > 0
                        ? "ช่วงถนนบนเส้นทางนี้จะผ่านในวันที่อยู่นอกช่วงที่แบบจำลองรองรับ จึงยังไม่มีข้อมูลประเมิน"
                        : "ยังไม่มีข้อมูลประเมินในเส้นทางนี้ — แบบจำลองตอนนี้ครอบคลุมเฉพาะทางหลวงในพื้นที่นำร่อง (ภาคกลางตอนบน–โคราช) ส่วนนี้ไม่ได้แปลว่าปลอดภัย"}
                    </p>
                  )}
                  {forecast.status === "done" && forecast.outOfRange > 0 && (
                    <p className="notice">{forecast.outOfRange} ช่วงถนนจะผ่านในวันที่อยู่นอกช่วงที่แบบจำลองรองรับ จึงแสดงเป็นไม่มีข้อมูล</p>
                  )}
                </div>
              </section>
            )}

            {selected && (
              <section ref={detailRef} className="card-section detail" aria-labelledby="detailTitle">
                <div className="detail-head">
                  <h2 id="detailTitle">รายละเอียดจุดที่เลือก</h2>
                  <button type="button" className="btn btn-ghost btn-small" onClick={() => setSelectedKey(null)}>ปิด</button>
                </div>
                <SpotDetail spot={selected} title={titleOf(selected)} entry={history[histKey(selected)]} onRetryHistory={() => loadHistory(selected, true)} />
              </section>
            )}

            {spots.length > 0 && (
              <section className="card-section" aria-labelledby="spotTitle">
                <h2 id="spotTitle">จุดที่ควรระวังบนเส้นทาง</h2>
                <p className="help">เรียงจากระดับสูงไปต่ำ แตะเพื่อดูบนแผนที่และดูว่าที่ผ่านมาส่วนใหญ่เกิดเหตุแบบไหน</p>
                <SpotList spots={spots} selectedKey={selectedKey} titleOf={titleOf} onSelect={(k) => selectSpot(k, true)} />
              </section>
            )}

            <section className="limits">
              <details>
                <summary>อ่านก่อนใช้: ตัวเลขและสีหมายถึงอะไร</summary>
                <ul>
                  <li>วงกลมคือ <strong>ช่วงถนนทางหลวงยาวราว 2 กม.</strong> ที่แบบจำลองรองรับ ขนาดวงกลมเป็นสัญลักษณ์บนจอ ไม่ใช่รัศมีอันตรายหรือตำแหน่งชนจริง</li>
                  <li>สีเป็นการจัดอันดับเชิงเปรียบเทียบของ <strong>จำนวนเหตุที่คาดว่าจะถูกบันทึก</strong> ในช่วง 6 ชั่วโมงที่คาดว่าคุณจะผ่าน ไม่ใช่โอกาสที่คุณจะเกิดอุบัติเหตุ และสีน้ำเงินไม่ได้แปลว่าปลอดภัย</li>
                  <li>ส่วนของเส้นทางที่เป็นสีเทาคือ <strong>ยังไม่มีข้อมูลประเมิน</strong> (ไม่ใช่ความเสี่ยงศูนย์) ตอนนี้แบบจำลองครอบคลุมทางหลวง 3,105 ช่วงในพื้นที่นำร่องภาคกลางตอนบน–โคราช</li>
                  <li>“ส่วนใหญ่เกิดจากอะไร” มาจากบันทึกอุบัติเหตุจริงปี 2564–2568 บนช่วงถนนนั้น เป็นข้อมูลที่บันทึกไว้ ไม่ใช่การพิสูจน์สาเหตุ และไม่ใช่สภาพอากาศวันนี้</li>
                  <li>วันที่หลัง 31 ธ.ค. 2568 เป็นการคาดการณ์เชิงวิจัย ยังไม่มีข้อมูลจริงให้เทียบ ระยะทาง/เวลาเดินทางมาจาก OSRM ไม่รวมสภาพจราจรจริง</li>
                </ul>
              </details>
            </section>

            <footer className="panel-foot">
              แผนที่ © OpenStreetMap contributors · ค้นหาสถานที่: Photon (komoot) · เส้นทาง: OSRM demo · ขอบเขตประเทศ: Natural Earth · ค่าประเมินจากระบบวิจัย RoadAware ในเครื่อง
            </footer>
          </div>
        </aside>
      </main>
    </>
  );
}
