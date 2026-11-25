import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { CONFIG, DATE_MIN, DATE_MAX, DEPART_OPTIONS, ENVELOPE } from "./config.js";
import { api, fetchJson, bkkToEpoch, epochToBkk, pad2, isNum, fmtKm, techText, isServiceDown } from "./lib/util.js";
import { geocode } from "./lib/geocode.js";
import { buildRouteIndex } from "./lib/routeMatch.js";
import { loadRouteMatches, predictMatches, fetchSegmentHistory } from "./lib/forecast.js";
import { buildZones, buildRibbon, aggregateHistory, levelKm } from "./lib/zones.js";
import MapView from "./components/MapView.jsx";
import TripForm from "./components/TripForm.jsx";
import Briefing from "./components/Briefing.jsx";
import { MapKey } from "./components/RouteRibbon.jsx";
import AboutDialog from "./components/AboutDialog.jsx";
import DriveMode, { DriveStart, DriveBanner } from "./components/DriveMode.jsx";
import ReviewResult, { reviewSummary } from "./components/ReviewResult.jsx";
import { REVIEW_PERIODS, periodProblem, reviewForecast, reviewActuals } from "./lib/review.js";
import { pointAt, locate, nextZone, warningText, speak, stopSpeech, checkVoiceProxy, prefetchSpeech } from "./lib/drive.js";

const IDLE = { status: "idle", places: [] };
const NO_ITEMS = [];
const MOBILE_Q = "(max-width: 900px)";
const isMobile = () => window.matchMedia(MOBILE_Q).matches;
function useIsMobile() {
  const [m, setM] = useState(isMobile);
  useEffect(() => {
    const mq = window.matchMedia(MOBILE_Q);
    const on = () => setM(mq.matches);
    mq.addEventListener("change", on);
    return () => mq.removeEventListener("change", on);
  }, []);
  return m;
}

function defaultWhen() {
  const now = epochToBkk(Date.now() + 10 * 60 * 1000);
  let date = now.date;
  if (date < DATE_MIN) date = DATE_MIN;
  if (date > DATE_MAX) date = DATE_MAX;
  return { date, time: pad2(now.hour) + ":" + pad2(Math.floor(now.minute / 5) * 5) };
}
const whenValid = (w) => /^\d{4}-\d{2}-\d{2}$/.test(w.date) && w.date >= DATE_MIN && w.date <= DATE_MAX && /^\d{2}:\d{2}$/.test(w.time);
const samePlace = (a, b) => a && b && Math.abs(a.lat - b.lat) < 1e-5 && Math.abs(a.lon - b.lon) < 1e-5;
const histKey = (z) => z.key + "|" + z.eta.date;
let routeSeq = 0;

export default function App() {
  // ---- ML service readiness
  const [ready, setReady] = useState("checking");
  const readyRef = useRef("checking");
  readyRef.current = ready;
  const readyCtrl = useRef(null);
  const [provinces, setProvinces] = useState(() => new Map());

  // ---- trip inputs
  const [texts, setTexts] = useState({ origin: "", dest: "" });
  const [places, setPlaces] = useState({ origin: null, dest: null });
  const [results, setResults] = useState({ origin: IDLE, dest: IDLE });
  const searchRef = useRef({ origin: { ctrl: null, gen: 0 }, dest: { ctrl: null, gen: 0 } });
  const [pick, setPick] = useState(null);
  const [when, setWhen] = useState(defaultWhen);

  // ---- route + forecast
  const [view, setView] = useState("plan");
  const [trip, setTrip] = useState({ status: "idle" });
  const [route, setRoute] = useState(null);
  const tripGen = useRef(0);
  const routeCtrl = useRef(null);
  const matchCache = useRef(new Map());
  const [matchesFor, setMatchesFor] = useState(null);
  const [forecast, setForecast] = useState({ status: "idle" });
  const [retryNonce, setRetryNonce] = useState(0);
  const [compare, setCompare] = useState({ status: "idle", key: null, results: {} });

  // ---- zones
  const [selectedKey, setSelectedKey] = useState(null);
  const [focus, setFocus] = useState(null);
  const [historyAll, setHistoryAll] = useState({});
  const historyRef = useRef({});

  // ---- chrome
  const mobile = useIsMobile();
  const [sheet, setSheet] = useState("full");
  const dragRef = useRef(null);
  const [toast, setToast] = useState(null);
  const [mapFailed, setMapFailed] = useState(false);
  const [about, setAbout] = useState(false);
  const [mode, setMode] = useState("trip"); // trip = this trip's hotspots · national = colours vs. all of Thailand
  // appMode: "plan" = forecast a trip you are about to take · "review" = ย้อนดูผล (model vs recorded accidents, past period)
  const [appMode, setAppMode] = useState("plan");
  const [reviewPeriod, setReviewPeriod] = useState(REVIEW_PERIODS[0]);
  const [review, setReview] = useState({ status: "idle" });
  const panelRef = useRef(null);

  // ================================================================ readiness
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
          if (Number.isFinite(n) && typeof p.name_th === "string") m.set(String(n), p.name_th.replace(/^จังหวัด/, ""));
        }
        setProvinces(m);
      })
      .catch(() => { /* names are optional */ });
  }, [ready, provinces.size]);

  const provinceName = useCallback((code) => {
    const n = Number(code);
    return Number.isFinite(n) ? provinces.get(String(n)) || null : null;
  }, [provinces]);

  // ================================================================ toast
  const showToast = useCallback((text) => setToast({ text, at: Date.now() }), []);
  useEffect(() => {
    if (!toast) return undefined;
    const t = setTimeout(() => setToast(null), 3200);
    return () => clearTimeout(t);
  }, [toast]);

  // ================================================================ route
  const invalidateRoute = useCallback(() => {
    tripGen.current += 1;
    if (routeCtrl.current) { routeCtrl.current.abort(); routeCtrl.current = null; }
    setRoute(null);
    setTrip({ status: "idle" });
    setSelectedKey(null);
    setView("plan");
  }, []);

  const goPlan = useCallback(() => { setView("plan"); setSelectedKey(null); if (isMobile()) setSheet("full"); }, []);

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
        "?overview=full&geometries=geojson&steps=false&alternatives=true";
      json = await fetchJson(url, { signal: ctrl.signal, timeoutMs: 25000 });
    } catch (f) {
      if (gen !== tripGen.current || f.kind === "aborted") return;
      const code = f.body && f.body.code;
      let title = "หาเส้นทางไม่สำเร็จ", text = "บริการเส้นทางไม่ตอบสนอง ลองอีกครั้งในอีกสักครู่";
      if (code === "NoRoute") { title = "ไม่พบเส้นทางรถยนต์"; text = "ไม่พบเส้นทางขับรถระหว่างสองจุดนี้ ลองเลือกจุดที่ใกล้ถนนมากขึ้น"; }
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
    const far = snaps.map((dist, i) => (dist > CONFIG.snapWarnM ? (i === 0 ? "ต้นทาง" : "ปลายทาง") + "อยู่ห่างถนนราว " + fmtKm(dist) : null)).filter(Boolean);
    // Alternatives with a similar driving time (OSRM gives 0–2). Each keeps its own id so matches are cached per line.
    const alternatives = [];
    for (const a of (json.routes || []).slice(1)) {
      const ac = a && a.geometry && Array.isArray(a.geometry.coordinates) ? a.geometry.coordinates : null;
      if (!ac || ac.length < 2 || !isNum(a.distance) || !isNum(a.duration) || a.duration > r.duration * CONFIG.altMaxTimeRatio) continue;
      let aidx = null;
      try { aidx = buildRouteIndex(ac); } catch (_) { aidx = null; }
      alternatives.push({ id: ++routeSeq, coords: ac, distance: a.distance, duration: a.duration, index: aidx });
    }
    setTrip({ status: "idle" });
    setRoute({
      id: ++routeSeq, coords, distance: r.distance, duration: r.duration, index, origin: o, dest: d, alternatives,
      snapNote: far.length ? far.join(" · ") + " — เส้นทางเริ่ม/สิ้นสุดที่ถนนนั้น" : null,
    });
    setView("brief");
    if (isMobile()) setSheet("half");
  }, [invalidateRoute]);

  // ---- forecast for the chosen departure (matches are loaded once per route)
  useEffect(() => {
    setSelectedKey(null);
    if (!route || appMode === "review") { setForecast({ status: "idle" }); return undefined; }
    if (!whenValid(when)) { setForecast({ status: "needWhen" }); return undefined; }
    if (!route.index) { setForecast({ status: "done", items: [], outOfRange: 0 }); return undefined; }
    let alive = true;
    const ctrl = new AbortController();
    setForecast({ status: "loading", text: "กำลังเตรียมประเมินเส้นทาง…", frac: 0.02 });
    const onProgress = (text, frac) => { if (alive) setForecast({ status: "loading", text, frac }); };
    const timer = setTimeout(async () => {
      try {
        if (readyRef.current !== "ready") {
          onProgress("กำลังเชื่อมต่อระบบประเมินความเสี่ยง…");
          const ok = await checkReady();
          if (!alive) return;
          if (!ok) { setForecast({ status: "notReady" }); return; }
        }
        let matches = matchCache.current.get(route.id);
        if (!matches) {
          matches = await loadRouteMatches(route, { signal: ctrl.signal, onProgress });
          if (!alive) return;
          matchCache.current.set(route.id, matches);
          setMatchesFor(matches.length ? route.id : null);
        }
        if (!matches.length) { setForecast({ status: "done", items: [], outOfRange: 0 }); return; }
        const res = await predictMatches(matches, route, { date: when.date, time: when.time, signal: ctrl.signal, onProgress });
        if (!alive) return;
        setForecast({ status: "done", ...res });
      } catch (f) {
        if (!alive || (f && f.kind === "aborted")) return;
        if (isServiceDown(f)) setReady("down");
        setForecast({ status: "error", failure: f });
      }
    }, 250);
    return () => { alive = false; clearTimeout(timer); ctrl.abort(); };
  }, [route, when, retryNonce, checkReady, appMode]);

  // ---- ย้อนดูผล: the model's points for a past period vs the accidents recorded on the same road segments
  useEffect(() => {
    setSelectedKey(null);
    if (!route || appMode !== "review") { setReview({ status: "idle" }); return undefined; }
    if (!route.index) { setReview({ status: "done", items: [], bySeg: new Map() }); return undefined; }
    let alive = true;
    const ctrl = new AbortController();
    const onProgress = (text, frac) => { if (alive) setReview({ status: "loading", text, frac }); };
    onProgress("กำลังเตรียมย้อนดูผล…", 0.02);
    (async () => {
      try {
        if (readyRef.current !== "ready" && !(await checkReady())) { if (alive) setReview({ status: "error", failure: { kind: "network" } }); return; }
        let matches = matchCache.current.get(route.id);
        if (!matches) {
          matches = await loadRouteMatches(route, { signal: ctrl.signal, onProgress });
          if (!alive) return;
          matchCache.current.set(route.id, matches);
        }
        if (!matches.length) { setReview({ status: "done", items: [], bySeg: new Map() }); return; }
        const { items: rItems } = await reviewForecast(matches, { start: reviewPeriod.start, end: reviewPeriod.end, signal: ctrl.signal, onProgress });
        if (!alive) return;
        onProgress("กำลังดูเหตุที่เกิดจริงในช่วงนี้…", 0.97);
        const { bySeg } = await reviewActuals(matches, { start: reviewPeriod.start, end: reviewPeriod.end, signal: ctrl.signal });
        if (!alive) return;
        setReview({ status: "done", items: rItems, bySeg });
      } catch (f) {
        if (!alive || (f && f.kind === "aborted")) return;
        if (isServiceDown(f)) setReady("down");
        setReview({ status: "error", failure: f });
      }
    })();
    return () => { alive = false; ctrl.abort(); };
  }, [route, appMode, reviewPeriod, retryNonce, checkReady]);

  // ---- departure comparison: 4 options for the same route and date (zone counts only)
  const compareKey = appMode === "plan" && route && matchesFor === route.id && whenValid(when) ? route.id + "|" + when.date : null;
  useEffect(() => {
    if (!compareKey || !route) { setCompare({ status: "idle", key: null, results: {} }); return undefined; }
    const matches = matchCache.current.get(route.id);
    let alive = true;
    const ctrl = new AbortController();
    setCompare({ status: "loading", key: compareKey, results: {} });
    (async () => {
      for (const o of DEPART_OPTIONS) {
        if (!alive) return;
        setCompare((c) => ({ ...c, results: { ...c.results, [o.time]: { status: "loading" } } }));
        try {
          const { items } = await predictMatches(matches, route, { date: when.date, time: o.time, signal: ctrl.signal });
          if (!alive) return;
          const { counts } = buildZones(items, () => null);
          setCompare((c) => ({ ...c, results: { ...c.results, [o.time]: { status: "ok", ...counts } } }));
        } catch (f) {
          if (!alive || (f && f.kind === "aborted")) return;
          setCompare((c) => ({ ...c, results: { ...c.results, [o.time]: { status: "error" } } }));
        }
      }
      if (alive) setCompare((c) => ({ ...c, status: "done" }));
    })();
    return () => { alive = false; ctrl.abort(); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [compareKey]);

  // ---- alternative routes: evaluated after the main forecast, same date and departure time (lengths/counts only)
  const [alts, setAlts] = useState({ key: null, list: [] });
  const [altFocus, setAltFocus] = useState(null);
  const altKey = route && forecast.status === "done" && whenValid(when) && (route.alternatives || []).length ? route.id + "|" + when.date + "|" + when.time : null;
  useEffect(() => {
    setAltFocus(null);
    if (!altKey || !route) { setAlts({ key: null, list: [] }); return undefined; }
    let alive = true;
    const ctrl = new AbortController();
    const list = route.alternatives.map((a) => ({ id: a.id, duration: a.duration, distance: a.distance, status: "loading" }));
    setAlts({ key: altKey, list });
    (async () => {
      for (let i = 0; i < route.alternatives.length; i++) {
        const a = route.alternatives[i];
        let entry;
        try {
          if (!a.index) throw new Error("no index");
          let matches = matchCache.current.get(a.id);
          if (!matches) {
            matches = await loadRouteMatches(a, { signal: ctrl.signal, onProgress: () => {} });
            matchCache.current.set(a.id, matches);
          }
          const { items: ai } = matches.length ? await predictMatches(matches, a, { date: when.date, time: when.time, signal: ctrl.signal }) : { items: [] };
          const zr = buildZones(ai, () => null);
          entry = { status: "ok", redKm: levelKm(ai).red, points: zr.zones.length + zr.hidden, coverage: buildRibbon(ai, a.distance).coverage };
        } catch (f) {
          if (!alive || (f && f.kind === "aborted")) return;
          entry = { status: "error" };
        }
        if (!alive) return;
        setAlts((cur) => (cur.key !== altKey ? cur : { ...cur, list: cur.list.map((x, j) => (j === i ? { ...x, ...entry } : x)) }));
      }
    })();
    return () => { alive = false; ctrl.abort(); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [altKey]);

  const pickAlternative = useCallback((altId) => {
    setRoute((cur) => {
      if (!cur) return cur;
      const a = (cur.alternatives || []).find((x) => x.id === altId);
      if (!a) return cur;
      const asAlt = { id: cur.id, coords: cur.coords, distance: cur.distance, duration: cur.duration, index: cur.index };
      return { ...cur, ...a, alternatives: [asAlt, ...cur.alternatives.filter((x) => x.id !== altId)], snapNote: cur.snapNote };
    });
    setAltFocus(null);
    setSelectedKey(null);
  }, []);

  // ================================================================ drive mode (voice warnings while travelling)
  const [drive, setDrive] = useState(null); // null | { phase: "start" } | { phase: "on", source, alongM, lat, lon, heading, ... }
  const driveRef = useRef(null);
  driveRef.current = drive;
  const spokenRef = useRef(new Set());
  const wakeRef = useRef(null);
  const hasVoice = typeof window !== "undefined" && !!window.speechSynthesis;

  const stopDrive = useCallback(() => {
    stopSpeech();
    if (wakeRef.current) { try { wakeRef.current.release(); } catch (_) { /* ignore */ } wakeRef.current = null; }
    setDrive(null);
  }, []);

  const startDrive = useCallback(async (source) => {
    if (!route || !route.index) return;
    spokenRef.current = new Set();
    try { if (navigator.wakeLock) wakeRef.current = await navigator.wakeLock.request("screen"); } catch (_) { wakeRef.current = null; }
    const p = pointAt(route, 0);
    setDrive({ phase: "on", source, alongM: source === "sim" ? 0 : null, lat: p.lat, lon: p.lon, heading: p.heading, speedX: 5, muted: false, off: false, misses: 0, arrived: false, lastSaid: null });
    setSelectedKey(null);
    setAltFocus(null);
    if (isMobile()) setSheet("half");
    checkVoiceProxy().then((v) => setDrive((d) => (d && d.phase === "on" ? { ...d, voice: v } : d)));
    speak(source === "sim" ? "เริ่มจำลองการเดินทาง ระบบจะเตือนก่อนถึงจุดที่ควรระวัง" : "เริ่มเดินทาง ระบบจะเตือนก่อนถึงจุดที่ควรระวัง", false);
  }, [route]); // eslint-disable-line react-hooks/exhaustive-deps

  // leaving the trip ends drive mode
  useEffect(() => { if (!route) stopDrive(); }, [route, stopDrive]);

  // simulation: advance along the route at speedX × the planned average speed
  const driveOn = drive && drive.phase === "on";
  const driveSource = driveOn ? drive.source : null;
  useEffect(() => {
    if (driveSource !== "sim" || !route) return undefined;
    const avg = route.distance / Math.max(route.duration, 1);
    const t = setInterval(() => {
      setDrive((d) => {
        if (!d || d.phase !== "on" || d.arrived) return d;
        const alongM = Math.min(route.distance, d.alongM + avg * 0.25 * d.speedX);
        const p = pointAt(route, alongM);
        return { ...d, alongM, lat: p.lat, lon: p.lon, heading: p.heading, t: performance.now(), arrived: alongM >= route.distance - 1 };
      });
    }, 250);
    return () => clearInterval(t);
  }, [driveSource, route]);

  // real GPS
  useEffect(() => {
    if (driveSource !== "gps" || !route) return undefined;
    if (!navigator.geolocation) { showToast("อุปกรณ์นี้ไม่รองรับตำแหน่ง GPS"); return undefined; }
    const id = navigator.geolocation.watchPosition((pos) => {
      const { latitude: lat, longitude: lon, heading } = pos.coords;
      const hit = locate(route, lat, lon);
      setDrive((d) => {
        if (!d || d.phase !== "on") return d;
        if (!hit) { const misses = d.misses + 1; return { ...d, lat, lon, misses, off: misses >= 3 }; }
        const alongM = d.alongM == null ? hit.alongM : Math.max(d.alongM - 200, hit.alongM); // ignore small backwards jitter
        return { ...d, lat, lon, heading: Number.isFinite(heading) ? heading : d.heading, alongM, t: performance.now(), misses: 0, off: false, arrived: alongM >= route.distance - 150 };
      });
    }, (err) => {
      showToast(err && err.code === 1 ? "ไม่ได้รับอนุญาตให้ใช้ตำแหน่ง — ลองโหมดจำลองการขับ" : "หาตำแหน่งไม่สำเร็จ");
    }, { enableHighAccuracy: true, maximumAge: 2000, timeout: 20000 });
    return () => navigator.geolocation.clearWatch(id);
  }, [driveSource, route, showToast]);

  const items = appMode === "review" ? (review.status === "done" ? review.items : NO_ITEMS) : (forecast.status === "done" ? forecast.items : NO_ITEMS);
  const zoneRes = useMemo(() => buildZones(items, provinceName), [items, provinceName]);
  const zones = zoneRes.zones;
  const reviewSum = useMemo(() => (appMode === "review" && review.status === "done" ? reviewSummary(items, zones, review.bySeg) : null), [appMode, review, items, zones]);
  const actuals = useMemo(() => {
    if (!reviewSum || !route || !route.index) return null;
    const out = [];
    for (const it of items) {
      const n = review.bySeg.get(it.id) || 0;
      if (!n) continue;
      const p = pointAt(route, it.alongM);
      out.push({ key: it.id, lat: p.lat, lon: p.lon, count: n });
    }
    return out;
  }, [reviewSum, items, route, review]);
  const ribbon = useMemo(() => (route ? buildRibbon(items, route.distance, zoneRes.hotIds, zoneRes.rankById) : { pieces: [], coverage: 0 }), [items, route, zoneRes]);
  const history = useMemo(() => {
    const out = {};
    for (const z of zones) out[z.key] = historyAll[histKey(z)];
    return out;
  }, [zones, historyAll]);

  // ---- drive warnings: 2 km, 500 m and on entering each numbered point (each spoken once)
  const driveAlong = driveOn ? drive.alongM : null;
  const driveArrived = driveOn && drive.arrived;
  useEffect(() => {
    if (driveAlong == null) return;
    const d = driveRef.current;
    const say = (key, text) => {
      if (spokenRef.current.has(key)) return;
      spokenRef.current.add(key);
      speak(text, d && d.muted, key.split("|")[0]);
      setDrive((x) => (x ? { ...x, lastSaid: text } : x));
    };
    if (driveArrived) { say("arrived", "ถึงปลายทางแล้ว ขอบคุณที่เดินทางอย่างระมัดระวัง"); return; }
    const nz = nextZone(zones, driveAlong);
    if (!nz) return;
    const z = nz.zone;
    const entry = historyAll[histKey(z)];
    const agg = entry && entry.status === "ok" ? entry.agg : null;
    if (nz.inside) { spokenRef.current.add(z.key + "|2000"); spokenRef.current.add(z.key + "|500"); say(z.key + "|in", warningText(z, "inside", agg)); }
    else if (nz.distM <= 500) { spokenRef.current.add(z.key + "|2000"); say(z.key + "|500", warningText(z, 500, agg)); }
    else if (nz.distM <= 2000) say(z.key + "|2000", warningText(z, 2000, agg));
  }, [driveAlong, driveArrived, zones, historyAll]);

  // ================================================================ zone history
  const setHist = useCallback((key, entry) => {
    historyRef.current = { ...historyRef.current, [key]: entry };
    setHistoryAll(historyRef.current);
  }, []);

  const loadZoneHistory = useCallback(async (z, force) => {
    const key = histKey(z);
    const cur = historyRef.current[key];
    if (!force && cur && cur.status !== "error") return;
    setHist(key, { status: "loading" });
    try {
      const hs = await Promise.all(z.members.map((m) => fetchSegmentHistory(m.id, m.eta.date)));
      setHist(key, { status: "ok", agg: aggregateHistory(hs) });
    } catch (f) {
      setHist(key, { status: "error", failure: f });
    }
  }, [setHist]);

  // drive mode: load "mostly caused by" for every numbered point up front (used in the spoken warnings)
  useEffect(() => { if (driveOn) for (const z of zones) loadZoneHistory(z); }, [driveOn, zones, loadZoneHistory]);
  // …and prepare every warning sentence in advance, so the Gemini voice plays instantly when it is due
  const driveVoice = driveOn ? drive.voice : null;
  useEffect(() => {
    if (driveVoice !== "ok") return;
    const texts = [];
    for (const z of zones) {
      const e = historyAll[histKey(z)];
      if (e && e.status === "loading") continue;
      const agg = e && e.status === "ok" ? e.agg : null;
      texts.push(warningText(z, 2000, agg), warningText(z, 500, agg), warningText(z, "inside", agg));
    }
    texts.push("ถึงปลายทางแล้ว ขอบคุณที่เดินทางอย่างระมัดระวัง");
    prefetchSpeech(texts);
  }, [driveVoice, zones, historyAll]);

  const selectZone = useCallback((key, fromMap) => {
    setSelectedKey(key);
    if (!key) return;
    const z = zones.find((x) => x.key === key);
    if (!z) return;
    if (!fromMap) setFocus({ key, n: Date.now() });
    loadZoneHistory(z);
    setView("brief");
    if (isMobile()) {
      setSheet("half");
      setFocus({ key, n: Date.now() });
      const body = panelRef.current && panelRef.current.querySelector(".panel-body");
      if (body) body.scrollTop = 0;
    } else {
      setTimeout(() => {
        const elx = document.getElementById("zone-" + z.n);
        if (elx) elx.scrollIntoView({ behavior: "smooth", block: "nearest" });
      }, 80);
    }
  }, [zones, loadZoneHistory]);

  // ================================================================ inputs
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
    if (isMobile()) setSheet("full");
  }, [pick, choosePlace]);

  // "ใช้ตำแหน่งของฉัน": the device's current position becomes the origin (needs https or localhost and the user's OK)
  const [locating, setLocating] = useState(false);
  const locateMe = useCallback(() => {
    if (!navigator.geolocation) { showToast("เบราว์เซอร์นี้หาตำแหน่งไม่ได้"); return; }
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLocating(false);
        const { latitude: lat, longitude: lon, accuracy } = pos.coords;
        if (lon < ENVELOPE.west || lon > ENVELOPE.east || lat < ENVELOPE.south || lat > ENVELOPE.north) { showToast("ตำแหน่งปัจจุบันอยู่นอกประเทศไทย"); return; }
        choosePlace("origin", { id: "gps", name: "ตำแหน่งของฉัน", sub: accuracy ? "แม่นยำราว " + Math.round(accuracy) + " ม." : "จาก GPS", lat, lon, source: "gps" });
      },
      (err) => {
        setLocating(false);
        showToast(err && err.code === 1 ? "ยังไม่ได้อนุญาตให้ใช้ตำแหน่ง — กดอนุญาตในเบราว์เซอร์แล้วลองใหม่" : "หาตำแหน่งไม่สำเร็จ ลองใหม่อีกครั้ง");
      },
      { enableHighAccuracy: true, timeout: 15000, maximumAge: 60000 },
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [choosePlace]);

  const togglePick = (which) => {
    const next = pick === which ? null : which;
    setPick(next);
    if (next && isMobile()) setSheet("peek");
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
    if (isMobile()) {
      const h = Math.min(panelRef.current ? panelRef.current.offsetHeight : 0, Math.round(window.innerHeight * 0.55));
      return { paddingTopLeft: [28, 84], paddingBottomRight: [28, h + 20] };
    }
    return { paddingTopLeft: [48, 48], paddingBottomRight: [48, 48] };
  }, []);

  // ---- bottom sheet: tap the handle to cycle, or drag it to the nearest stop
  const sheetStops = () => {
    const H = panelRef.current && panelRef.current.parentElement ? panelRef.current.parentElement.clientHeight : window.innerHeight;
    return { peek: 132, half: Math.round(H * 0.52), full: H - 12 };
  };
  const onHandleDown = (e) => {
    if (!panelRef.current) return;
    dragRef.current = { y: e.clientY, h: panelRef.current.offsetHeight, moved: false };
    e.currentTarget.setPointerCapture(e.pointerId);
  };
  const onHandleMove = (e) => {
    const d = dragRef.current;
    if (!d || !panelRef.current) return;
    const dy = d.y - e.clientY;
    if (Math.abs(dy) > 4) d.moved = true;
    if (!d.moved) return;
    const st = sheetStops();
    panelRef.current.style.height = Math.max(st.peek, Math.min(st.full, d.h + dy)) + "px";
    panelRef.current.classList.add("is-dragging");
  };
  const onHandleUp = () => {
    const d = dragRef.current;
    dragRef.current = null;
    if (!panelRef.current || !d) return;
    panelRef.current.classList.remove("is-dragging");
    if (!d.moved) {
      setSheet((s) => (s === "peek" ? "half" : s === "half" ? "full" : "peek"));
      return;
    }
    const h = panelRef.current.offsetHeight;
    const st = sheetStops();
    const best = Object.entries(st).reduce((a, b) => (Math.abs(b[1] - h) < Math.abs(a[1] - h) ? b : a))[0];
    panelRef.current.style.height = "";
    setSheet(best);
  };

  // ================================================================ derived

  const canRoute = !!(places.origin && places.dest && (appMode === "review" ? !periodProblem(reviewPeriod) : whenValid(when))) && !samePlace(places.origin, places.dest) && trip.status !== "loading";
  const showBrief = view === "brief" && route;

  const showRibbon = route && (appMode === "review" ? review.status === "done" : forecast.status === "done") && items.length > 0;
  const selectedZone = zones.find((z) => z.key === selectedKey) || null;

  return (
    <div className={"app" + (showBrief ? " is-brief" : " is-plan")}>
      <a className="skip-link" href="#panel">ข้ามไปยังแผงวางแผนการเดินทาง</a>
      <header className="topbar">
        <div className="brand">
          <svg width="28" height="28" viewBox="0 0 26 26" aria-hidden="true"><circle cx="13" cy="13" r="12" fill="#0F1B2D" /><path d="M7 18 C10 12, 13 15, 19 7" stroke="#E8821E" strokeWidth="2.6" fill="none" strokeLinecap="round" /></svg>
          <span className="brand-name">RoadAware</span>
        </div>
        <div className="topbar-right">
          <span className={"status status-" + ready} role="status" aria-live="polite" title={ready === "ready" ? "ระบบประเมินพร้อม" : ready === "down" ? "ระบบประเมินไม่พร้อม" : "กำลังเชื่อมต่อ"}>
            <i aria-hidden="true" />
            <span className="status-text">{ready === "ready" ? "ระบบประเมินพร้อม" : ready === "down" ? "ระบบประเมินไม่พร้อม" : "กำลังเชื่อมต่อ…"}</span>
          </span>
          {ready === "down" && (
            <button type="button" className="btn btn-ghost btn-sm" onClick={async () => { const ok = await checkReady(); if (ok && route) setRetryNonce((n) => n + 1); }}>ลองใหม่</button>
          )}
          <button type="button" className="btn btn-ghost btn-sm about-btn" onClick={() => setAbout(true)} aria-label="ข้อมูลนี้มาจากไหน">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true"><circle cx="12" cy="12" r="9" /><path d="M12 11v5" /><path d="M12 7.5v.5" /></svg>
            <span className="about-text">ข้อมูลนี้มาจากไหน</span>
          </button>
        </div>
      </header>

      <main className="workspace">
        <section className="map-pane" aria-label="แผนที่">
          <div className="map-card">
            {!mapFailed && (
              <MapView
                route={route} origin={places.origin} dest={places.dest} items={items} zones={zones} actuals={appMode === "review" ? actuals : null} hotIds={zoneRes.hotIds} rankById={zoneRes.rankById} mode={mode} altFocus={altFocus} onSelectAlt={setAltFocus} drivePos={driveOn && drive.alongM != null ? drive : null}
                selectedKey={selectedKey} focus={focus} pick={pick} getPadding={getPadding}
                onPick={onPickPoint} onOutside={() => showToast("เลือกได้เฉพาะพื้นที่ในประเทศไทย")}
                onSelectZone={(k) => selectZone(k, true)} onFailed={() => setMapFailed(true)}
              />
            )}
            {mapFailed && <div className="map-fallback"><div><h2>แผนที่ยังแสดงไม่ได้</h2><p>ยังค้นหาและดูสรุปทริปในแผงได้ตามปกติ</p></div></div>}

            {mobile && showBrief && (
              <div className="map-trip">
                <button type="button" className="map-trip-back" aria-label={selectedZone ? "กลับไปสรุปทริป" : "แก้ไขเส้นทาง"}
                  onClick={() => (selectedZone ? setSelectedKey(null) : goPlan())}>
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M15 18l-6-6 6-6" /></svg>
                </button>
                <button type="button" className="map-trip-pill" onClick={goPlan}>
                  <span className="mtp-route">{route.origin.name} → {route.dest.name}</span>
                  <span className="mtp-time">{appMode === "review" ? reviewPeriod.label : when.time}</span>
                </button>
              </div>
            )}

            {pick && (
              <div className="pick-banner" role="status">
                <span>{pick === "origin" ? "แตะบนแผนที่เพื่อเลือกต้นทาง (A)" : "แตะบนแผนที่เพื่อเลือกปลายทาง (B)"}</span>
                <button type="button" className="btn btn-ghost btn-sm" onClick={() => { setPick(null); if (isMobile()) setSheet("full"); }}>ยกเลิก</button>
              </div>
            )}
            {toast && <p className="toast" role="status">{toast.text}</p>}
            {driveOn && route && <DriveBanner drive={drive} zones={zones} route={route} />}
            {!driveOn && showRibbon && altFocus && route.alternatives && (() => {
              const i = route.alternatives.findIndex((x) => x.id === altFocus);
              if (i < 0) return null;
              const st = alts.list.find((x) => x.id === altFocus);
              const dt = Math.round((route.alternatives[i].duration - route.duration) / 60);
              return (
                <div className="alt-chip alt-chip-on" role="status">
                  <span><i className="alt-swatch alt-swatch-on" /><b>เส้นประสีม่วง = ทางเลือก {i + 1}</b> · {dt === 0 ? "เวลาเท่ากัน" : (dt > 0 ? "ช้ากว่า " : "เร็วกว่า ") + Math.abs(dt) + " นาที"}</span>
                  {st && st.status === "ok" && <button type="button" className="btn btn-sm alt-chip-use" onClick={() => pickAlternative(altFocus)}>ใช้เส้นนี้</button>}
                  <button type="button" className="btn btn-ghost btn-sm" onClick={() => setAltFocus(null)}>ปิด</button>
                </div>
              );
            })()}
            {!driveOn && showRibbon && <MapKey mode={mode} onTrip={() => setMode("trip")} mobile={mobile} review={appMode === "review"} />}
          </div>


        </section>

        <aside id="panel" ref={panelRef} className={"panel sheet-" + sheet} tabIndex={-1} aria-label="วางแผนการเดินทาง">
          <button type="button" className="sheet-handle" aria-label="ลากหรือแตะเพื่อย่อ/ขยายแผง"
            onPointerDown={onHandleDown} onPointerMove={onHandleMove} onPointerUp={onHandleUp} onPointerCancel={onHandleUp}>
            <span className="sheet-grip" aria-hidden="true" />
          </button>
          <div className="panel-body">
            {showBrief && drive && drive.phase === "start" ? (
              <DriveStart hasVoice={hasVoice} onStart={startDrive} onCancel={() => setDrive(null)} />
            ) : showBrief && driveOn ? (
              <DriveMode drive={drive} zones={zones} route={route} history={history} onStop={stopDrive}
                onMute={() => setDrive((d) => { if (!d.muted) stopSpeech(); return { ...d, muted: !d.muted }; })}
                onSpeed={(x) => setDrive((d) => ({ ...d, speedX: x }))}
                onTestVoice={() => { stopSpeech(); if (!speak("ระวัง! อีก 500 เมตร ถึงจุดที่ควรระวัง นี่คือเสียงเตือนของ RoadAware", false, "test")) showToast("เบราว์เซอร์นี้ไม่มีเสียงภาษาไทย"); }} />
            ) : showBrief && appMode === "review" ? (
              <ReviewResult route={route} period={reviewPeriod} review={review} zones={zones} summary={reviewSum}
                selectedKey={selectedKey} onSelectZone={(k) => selectZone(k, false)} onEdit={goPlan}
                onRetry={() => setRetryNonce((n) => n + 1)} onAbout={() => setAbout(true)} />
            ) : showBrief ? (
              <Briefing
                route={route} when={when} forecast={forecast} zones={zones} hidden={zoneRes.hidden} counts={zoneRes.counts} mode={mode} onMode={setMode} ribbon={ribbon}
                compare={compare} selectedKey={selectedKey} history={history} mobile={mobile}
                alts={alts.list} altFocus={altFocus} onFocusAlt={setAltFocus} onUseAlt={pickAlternative}
                onDrive={zones.length && route.index ? () => setDrive({ phase: "start" }) : null}
                onEdit={goPlan} onSelectZone={(k) => selectZone(k, false)}
                onPickTime={(t) => setWhen((w) => ({ ...w, time: t }))}
                onRetry={() => setRetryNonce((n) => n + 1)} onRetryHistory={(z) => loadZoneHistory(z, true)}
                onAbout={() => setAbout(true)}
              />
            ) : (
              <>
                {route && (
                  <button type="button" className="back-link" onClick={() => { setView("brief"); if (isMobile()) setSheet("half"); }}>
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M15 18l-6-6 6-6" /></svg>
                    กลับไปดูสรุปทริป
                  </button>
                )}
                <TripForm appMode={appMode} onAppMode={(m) => { setAppMode(m); invalidateRoute(); }} reviewPeriod={reviewPeriod} onReviewPeriod={setReviewPeriod}
                  texts={texts} places={places} results={results} pick={pick} when={when}
                  canRoute={canRoute} trip={trip}
                  onText={onText} onSearch={(w) => runSearch(w, texts[w])} onChoose={choosePlace}
                  onCloseResults={(w) => setResults((r) => ({ ...r, [w]: IDLE }))}
                  onPick={togglePick} onMyLocation={locateMe} locating={locating} onSwap={swap} onWhen={(patch) => setWhen((w) => ({ ...w, ...patch }))}
                  onSubmit={() => runTrip(places.origin, places.dest)} onExample={runExample}
                />
              </>
            )}
          </div>
        </aside>
      </main>
      <AboutDialog open={about} onClose={() => setAbout(false)} />
    </div>
  );
}
