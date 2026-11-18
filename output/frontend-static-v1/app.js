"use strict";

// RoadAware route planner. Route planning (place search + driving route) works for any routable
// point in Thailand and never depends on the research API. Forecast circles are added only for
// actual RoadAware segments matched to the route and actual prediction responses.
// Untrusted text is always rendered with textContent / DOM nodes (never innerHTML).

// ---------------------------------------------------------------- configuration

// Photon and OSRM are public demo services used only for this local prototype: moderate use,
// no availability guarantee, not production infrastructure. Each is limited to <= 1 request/s.
const CONFIG = {
  apiBase: resolveApiBase(),
  photonUrl: "https://photon.komoot.io/api/",
  photonBbox: "97,5,106,21",
  photonLimit: 6,
  osrmRouteUrl: "https://router.project-osrm.org/route/v1/driving/",
  boundaryUrl: "assets/thailand-boundary.geojson",
  tileUrl: "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
};

const API_TIMEOUT_MS = 30000;
const EXTERNAL_TIMEOUT_MS = 15000;
const EXTERNAL_MIN_INTERVAL_MS = 1100;
const SEGMENT_PAGE_SIZE = 500;
const MAX_SEGMENT_PAGES = 40;
const PREDICTION_BATCH = 128;
const DATE_MIN = "2024-01-01";
const DATE_MAX = "2027-12-31";
const LAST_OBSERVED_DATE = "2025-12-31";
// Backend geometry limits (bbox must stay inside this envelope, <= 20 degrees per axis).
const ENVELOPE = { west: 97.0, south: 5.0, east: 106.0, north: 21.0 };
const MAX_SPAN_DEG = 20.0;
// Map may not be panned beyond this box; the country polygon mask hides the rest.
const VIEW_BOUNDS = [[5.1, 96.9], [20.95, 106.1]];
const THAILAND_FIT = [[5.6, 97.35], [20.45, 105.65]];
// Route/segment comparison rule (approximate candidate linkage, not navigation-grade):
// sample each segment every <= 100 m along its length; the segment is "on the route" when at
// least 50% of its samples lie within 50 m of the route line.
const MATCH_SAMPLE_M = 100;
const MATCH_MAX_DIST_M = 50;
const MATCH_MIN_SHARE = 0.5;
const GRID_CELL_M = 250;
const SNAP_NOTE_M = 100;

const BLOCKS = ["00-06", "06-12", "12-18", "18-24"];
const BLOCK_LABEL = { "00-06": "00:00–06:00 น.", "06-12": "06:00–12:00 น.", "12-18": "12:00–18:00 น.", "18-24": "18:00–24:00 น." };
const BAND_ORDER = ["red", "orange", "yellow", "base", "grey"];
const BAND_TH = {
  base: { title: "ต่ำกว่าค่ากลาง (เชิงเปรียบเทียบ)", text: "ต่ำกว่าค่ามัธยฐานของค่าอ้างอิง — ไม่ได้หมายความว่าปลอดภัย" },
  yellow: { title: "สูงกว่าค่ากลาง (เชิงเปรียบเทียบ)", text: "อยู่ช่วงเปอร์เซ็นไทล์ที่ 50–80 ของค่าอ้างอิง" },
  orange: { title: "สูง (เชิงเปรียบเทียบ)", text: "อยู่ช่วงเปอร์เซ็นไทล์ที่ 80–95 ของค่าอ้างอิง" },
  red: { title: "สูงที่สุด (เชิงเปรียบเทียบ)", text: "อยู่ใน 5% บนของค่าอ้างอิง — เป็นการจัดอันดับ ไม่ใช่ความเสี่ยงสัมบูรณ์" },
  grey: { title: "ไม่มีข้อมูล", text: "ไม่สามารถให้ค่าประเมินสำหรับช่วงถนนหรือช่วงเวลานี้" },
};
const CATEGORY_TH = { accident_type: "ลักษณะเหตุที่บันทึก", presumed_cause: "สาเหตุที่สันนิษฐานในบันทึก", weather: "สภาพอากาศที่บันทึก" };
const PLACE_KIND_TH = {
  university: "มหาวิทยาลัย", college: "วิทยาลัย", school: "โรงเรียน", hospital: "โรงพยาบาล",
  peak: "ยอดเขา", national_park: "อุทยานแห่งชาติ", protected_area: "พื้นที่คุ้มครอง",
  city: "เมือง", town: "เมือง", village: "หมู่บ้าน", suburb: "ย่าน", province: "จังหวัด",
  station: "สถานี", aerodrome: "สนามบิน", temple: "วัด", place_of_worship: "ศาสนสถาน",
  mall: "ห้างสรรพสินค้า", attraction: "สถานที่ท่องเที่ยว", viewpoint: "จุดชมวิว",
  waterfall: "น้ำตก", beach: "ชายหาด", island: "เกาะ", hotel: "ที่พัก", fuel: "ปั๊มน้ำมัน",
};
const ROUTE_STYLE = { color: "#3f5566", weight: 6, opacity: 0.9 };
const ROUTE_CASING = { color: "#ffffff", weight: 10, opacity: 0.95 };
const SELECTED_SEGMENT_STYLE = { color: "#0a4f53", weight: 9, opacity: 0.9 };
const NEUTRAL_DOT = "#8a949c";
const HEX_RE = /^#[0-9a-fA-F]{6}$/;

const $ = (id) => document.getElementById(id);
const WHICH = ["origin", "destination"];
const WHICH_TH = { origin: "ต้นทาง", destination: "ปลายทาง" };

const state = {
  ready: "checking",          // research API: "checking" | "ready" | "down"
  readyController: null,
  provinces: new Map(),
  boundary: null,             // array of polygons (arrays of [lon, lat] rings) once loaded
  boundaryStatus: "loading",  // "loading" | "ready" | "failed"
  fields: {
    origin: { place: null, results: null, searchGen: 0, controller: null, status: "", error: false },
    destination: { place: null, results: null, searchGen: 0, controller: null, status: "", error: false },
  },
  picking: null,              // "origin" | "destination" while choosing on the map
  routeGen: 0,
  routeController: null,
  route: null,                // { status: "loading"|"ready"|"error", ... }
  forecastGen: 0,
  forecastController: null,
  forecast: { status: "idle" },
  forecastKey: null,          // time context key of the latest forecast run
  forecastTimer: null,
  selectedId: null,
  detailGen: 0,
  detailController: null,
  sheetOpen: true,
};

const map = {
  leaflet: null, mask: null, outline: null, endpoints: { origin: null, destination: null },
  routeLayers: [], connectors: [], dots: new Map(), selectedLayer: null, tileErrors: 0,
};

const geocodeCache = new Map();
const lastServiceStart = { photon: 0, osrm: 0 };

// ---------------------------------------------------------------- helpers

function resolveApiBase() {
  const param = new URLSearchParams(window.location.search).get("api");
  if (param) {
    try {
      const url = new URL(param);
      if (url.protocol === "http:" || url.protocol === "https:") {
        return url.origin + url.pathname.replace(/\/+$/, "");
      }
    } catch (_) { /* fall through to default */ }
  }
  return "http://127.0.0.1:8000";
}

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined && text !== null) node.textContent = String(text);
  return node;
}

function isNum(v) {
  return typeof v === "number" && Number.isFinite(v);
}

function fmtNum(v) {
  if (!isNum(v)) return "ไม่มีข้อมูล";
  if (v === 0) return "0";
  return v.toLocaleString("th-TH", { maximumSignificantDigits: 3 });
}

function fmtInt(v) {
  return isNum(v) ? v.toLocaleString("th-TH") : "ไม่มีข้อมูล";
}

function fmtDate(iso) {
  if (typeof iso !== "string" || !/^\d{4}-\d{2}-\d{2}/.test(iso)) return String(iso ?? "ไม่มีข้อมูล");
  const d = new Date(iso.slice(0, 10) + "T00:00:00");
  return d.toLocaleDateString("th-TH", { year: "numeric", month: "long", day: "numeric" });
}

function fmtKm(m) {
  if (!isNum(m)) return "—";
  const km = m / 1000;
  return (km < 10 ? km.toFixed(1) : Math.round(km).toLocaleString("th-TH")) + " กม.";
}

function fmtMeters(m) {
  if (!isNum(m)) return "—";
  return m < 1000 ? Math.round(m) + " ม." : (m / 1000).toFixed(1) + " กม.";
}

function fmtDuration(s) {
  if (!isNum(s)) return "—";
  const totalMin = Math.max(1, Math.round(s / 60));
  const h = Math.floor(totalMin / 60);
  const m = totalMin % 60;
  return h > 0 ? h + " ชม. " + m + " นาที" : m + " นาที";
}

function fmtCoord(lat, lon) {
  return lat.toFixed(5) + ", " + lon.toFixed(5);
}

function pad2(n) {
  return String(n).padStart(2, "0");
}

function provinceKey(code) {
  const n = Number(code);
  return Number.isFinite(n) ? String(n) : null;
}

function provinceName(code) {
  const key = provinceKey(code);
  const p = key ? state.provinces.get(key) : null;
  return p && p.name_th ? p.name_th : null;
}

function routeLabel(code) {
  if (typeof code !== "string" || code === "") return "ทางหลวง (ไม่ระบุหมายเลข)";
  const digits = /^\d+$/.test(code) ? String(Number(code)) : code;
  return "ทางหลวงหมายเลข " + digits;
}

function insideEnvelope(lat, lon) {
  return lon >= ENVELOPE.west && lon <= ENVELOPE.east && lat >= ENVELOPE.south && lat <= ENVELOPE.north;
}

function clampBbox(b) {
  let west = Math.max(ENVELOPE.west, b.west);
  let east = Math.min(ENVELOPE.east, b.east);
  let south = Math.max(ENVELOPE.south, b.south);
  let north = Math.min(ENVELOPE.north, b.north);
  if (east - west > MAX_SPAN_DEG || north - south > MAX_SPAN_DEG) return null;
  if (!(east > west) || !(north > south)) return null;
  const r = (x) => Math.round(x * 10000) / 10000;
  return { west: r(west), south: r(south), east: r(east), north: r(north) };
}

function isMobile() {
  return window.matchMedia("(max-width: 760px)").matches;
}

// ---------------------------------------------------------------- Thailand boundary

function ringContains(ring, lon, lat) {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const xi = ring[i][0]; const yi = ring[i][1];
    const xj = ring[j][0]; const yj = ring[j][1];
    if ((yi > lat) !== (yj > lat) && lon < ((xj - xi) * (lat - yi)) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
}

function pointInThailand(lat, lon) {
  if (!state.boundary) return false;
  for (const polygon of state.boundary) {
    if (!ringContains(polygon[0], lon, lat)) continue;
    let inHole = false;
    for (let k = 1; k < polygon.length; k += 1) if (ringContains(polygon[k], lon, lat)) inHole = true;
    if (!inHole) return true;
  }
  return false;
}

// Accept a coordinate as a Thai endpoint. Before the boundary loads, only the envelope is known.
function acceptablePoint(lat, lon) {
  if (!isNum(lat) || !isNum(lon) || !insideEnvelope(lat, lon)) return false;
  return state.boundaryStatus === "ready" ? pointInThailand(lat, lon) : true;
}

function parseBoundary(json) {
  const polygons = [];
  const feats = json && Array.isArray(json.features) ? json.features : [];
  for (const f of feats) {
    const g = f && f.geometry;
    if (!g) continue;
    if (g.type === "Polygon") polygons.push(g.coordinates);
    else if (g.type === "MultiPolygon") for (const p of g.coordinates) polygons.push(p);
  }
  const ok = polygons.length > 0 && polygons.every((p) => Array.isArray(p) && Array.isArray(p[0]) && p[0].length >= 4);
  return ok ? polygons : null;
}

async function loadBoundary() {
  let polygons = null;
  try {
    const { status, json } = await fetchJson(CONFIG.boundaryUrl, { timeoutMs: API_TIMEOUT_MS });
    if (status === 200) polygons = parseBoundary(json);
  } catch (_) {
    polygons = null;
  }
  if (!polygons) {
    state.boundaryStatus = "failed";
    showMapNotice("โหลดขอบเขตประเทศไม่สำเร็จ จึงปิดการเลือกจุดบนแผนที่ชั่วคราว ยังค้นหาสถานที่ด้วยชื่อได้ตามปกติ");
    refreshControls();
    return;
  }
  state.boundary = polygons;
  state.boundaryStatus = "ready";
  addMask();
  refreshControls();
}

// ---------------------------------------------------------------- HTTP

class RequestFailure extends Error {
  constructor(kind, status, body) {
    super(kind);
    this.kind = kind;       // "aborted" | "timeout" | "network" | "http" | "invalid"
    this.status = status;
    this.body = body;
  }
}

function sleep(ms, signal) {
  return new Promise((resolve, reject) => {
    if (signal && signal.aborted) { reject(new RequestFailure("aborted")); return; }
    const onAbort = () => { clearTimeout(timer); reject(new RequestFailure("aborted")); };
    const timer = setTimeout(() => {
      if (signal) signal.removeEventListener("abort", onAbort);
      resolve();
    }, ms);
    if (signal) signal.addEventListener("abort", onAbort, { once: true });
  });
}

const nextTick = () => new Promise((resolve) => setTimeout(resolve, 0));

// Public demo services: start at most one request per EXTERNAL_MIN_INTERVAL_MS per service.
async function takeTurn(service, signal) {
  const now = Date.now();
  const at = Math.max(now, lastServiceStart[service] + EXTERNAL_MIN_INTERVAL_MS);
  lastServiceStart[service] = at;
  if (at > now) await sleep(at - now, signal);
}

// One real HTTP request. Resolves { status, json } (json null when unparsable);
// throws RequestFailure only for aborted / timeout / network.
async function fetchJson(url, { method = "GET", body, controller, timeoutMs = API_TIMEOUT_MS, noStore = false } = {}) {
  const ctrl = controller || new AbortController();
  let timedOut = false;
  const timer = setTimeout(() => { timedOut = true; ctrl.abort(); }, timeoutMs);
  const init = { method, signal: ctrl.signal };
  if (noStore) init.cache = "no-store";
  if (body !== undefined) {
    init.headers = { "Content-Type": "application/json" };
    init.body = JSON.stringify(body);
  }
  let response;
  let text;
  try {
    response = await fetch(url, init);
    text = await response.text();
  } catch (err) {
    if (err && err.name === "AbortError") throw new RequestFailure(timedOut ? "timeout" : "aborted");
    throw new RequestFailure("network");
  } finally {
    clearTimeout(timer);
  }
  let json = null;
  try { json = JSON.parse(text); } catch (_) { json = null; }
  return { status: response.status, json };
}

// Research API request: parsed JSON object for 2xx, otherwise RequestFailure.
async function apiFetch(path, { method = "GET", body, controller } = {}) {
  const { status, json } = await fetchJson(CONFIG.apiBase + path, { method, body, controller, noStore: true });
  if (status >= 200 && status < 300) {
    if (json === null || typeof json !== "object") throw new RequestFailure("invalid", status, null);
    return json;
  }
  throw new RequestFailure("http", status, json);
}

function isServiceDown(failure) {
  return failure.kind === "network" || failure.kind === "timeout" || (failure.kind === "http" && failure.status === 503);
}

function describeFailure(failure) {
  const err = failure.body && failure.body.error ? failure.body.error : null;
  if (failure.kind === "timeout") return { title: "บริการผลประเมินตอบช้าเกินไป", text: "โปรดลองอีกครั้ง เส้นทางยังใช้งานได้ตามปกติ", err };
  if (failure.kind === "network") return { title: "เชื่อมต่อบริการผลประเมินไม่ได้", text: "บริการอาจยังไม่เปิดหรือกำลังเริ่มทำงาน เส้นทางยังใช้งานได้ตามปกติ", err };
  if (failure.kind === "invalid") return { title: "ได้รับข้อมูลที่อ่านไม่ได้", text: "ระบบตอบกลับในรูปแบบที่ไม่คาดไว้ จึงไม่แสดงผล", err };
  const s = failure.status;
  if (s === 503) return { title: "บริการผลประเมินไม่พร้อมชั่วคราว", text: "โปรดลองอีกครั้งในภายหลัง เส้นทางยังใช้งานได้ตามปกติ", err };
  if (s === 404) return { title: "ไม่มีข้อมูลสำหรับรายการนี้", text: "ช่วงถนนนี้อยู่นอกขอบเขตข้อมูลที่รองรับ (ไม่มีข้อมูล ไม่ใช่ศูนย์)", err };
  if (s === 400) return { title: "คำขอไม่ถูกต้อง", text: "โปรดตรวจสอบวันที่อีกครั้ง (รองรับ 1 ม.ค. 2024 – 31 ธ.ค. 2027)", err };
  return { title: "เกิดข้อผิดพลาดจากบริการผลประเมิน", text: "ไม่แสดงผลบางส่วน โปรดลองอีกครั้ง", err };
}

function errorBox(info, onRetry, failure) {
  const box = el("div", "error-box");
  box.setAttribute("role", "alert");
  box.append(el("strong", null, info.title), el("span", null, info.text));
  if (info.err && (info.err.code || info.err.message)) {
    const det = el("details");
    det.append(el("summary", null, "รายละเอียดทางเทคนิค"));
    if (failure && failure.status) det.append(el("div", null, "HTTP " + failure.status));
    if (info.err.code) det.append(el("div", "mono", info.err.code));
    if (info.err.message) det.append(el("div", null, info.err.message));
    box.append(det);
  }
  if (onRetry) {
    const btn = el("button", "btn btn-ghost btn-touch", "ลองอีกครั้ง");
    btn.type = "button";
    btn.addEventListener("click", onRetry);
    box.append(btn);
  }
  return box;
}

function apiErrorBox(failure, onRetry) {
  return errorBox(describeFailure(failure), onRetry, failure);
}

function loadingRow(text) {
  const row = el("div", "loading");
  row.append(el("span", "spinner"), el("span", null, text));
  return row;
}

// ---------------------------------------------------------------- research API readiness

async function checkReady() {
  if (state.readyController) state.readyController.abort();
  const controller = new AbortController();
  state.readyController = controller;
  setReady("checking");
  let ok = false;
  try {
    const json = await apiFetch("/ready", { controller });
    ok = json.research_backend_ready === true;
  } catch (_) {
    ok = false;
  }
  if (state.readyController !== controller) return;
  state.readyController = null;
  setReady(ok ? "ready" : "down");
  if (ok) loadProvinces();
}

function setReady(next) {
  state.ready = next;
  $("statusDot").className = "status-dot " + (next === "ready" ? "is-ready" : next === "down" ? "is-down" : "is-checking");
  $("statusText").textContent = next === "ready" ? "ผลประเมินพร้อม" : next === "down" ? "ผลประเมินไม่พร้อม" : "กำลังเชื่อมต่อผลประเมิน…";
  $("btnRetry").hidden = next !== "down";
  // Route planning never depends on readiness; only the forecast layer waits for it.
  const f = state.forecast.status;
  const serviceFailed = f === "error" && isServiceDown(state.forecast.failure);
  if (next === "ready" && state.route && state.route.status === "ready" && (f === "waiting" || f === "down" || serviceFailed)) {
    runForecast();
  } else if (next === "down" && (f === "waiting")) {
    state.forecast = { status: "down" };
    renderForecast();
  }
}

function retryService() {
  checkReady();
}

async function loadProvinces() {
  if (state.provinces.size > 0) return;
  try {
    const json = await apiFetch("/api/v1/provinces");
    const list = Array.isArray(json.provinces) ? json.provinces : [];
    for (const p of list) {
      const key = p ? provinceKey(p.province_code) : null;
      if (key && typeof p.name_th === "string") state.provinces.set(key, p);
    }
    if (state.forecast.status === "done") renderForecast();
    if (state.selectedId) renderDetailMeta();
  } catch (_) {
    // Province names are optional labels only.
  }
}

// ---------------------------------------------------------------- time inputs

function todayIso() {
  const d = new Date();
  return d.getFullYear() + "-" + pad2(d.getMonth() + 1) + "-" + pad2(d.getDate());
}

function validDate(d) {
  return /^\d{4}-\d{2}-\d{2}$/.test(d) && d >= DATE_MIN && d <= DATE_MAX;
}

function hourToBlock(h) {
  return BLOCKS[Math.min(3, Math.floor(h / 6))];
}

// The captured forecast request context for the current inputs.
function timeContext() {
  const date = $("tripDate").value;
  const time = $("tripTime").value;
  const unit = document.querySelector('input[name="unit"]:checked').value;
  const m = /^(\d{2}):(\d{2})/.exec(time || "");
  const hour = m ? Number(m[1]) : NaN;
  const valid = validDate(date) && (unit === "daily" || (hour >= 0 && hour <= 23));
  const block = unit === "6h" && valid ? hourToBlock(hour) : null;
  return { date, time, unit, block, valid, key: valid ? unit + "|" + date + "|" + (block || "") : null };
}

function updateTimeNote() {
  const ctx = timeContext();
  const parts = [];
  if (!validDate(ctx.date)) {
    parts.push("เลือกวันที่ระหว่าง 1 ม.ค. 2024 ถึง 31 ธ.ค. 2027 (ช่วงที่แบบจำลองรองรับ)");
  } else {
    if (ctx.unit === "6h" && ctx.block) {
      parts.push("ออกเดินทาง " + ctx.time + " น. → ใช้ผลประเมินช่วง " + BLOCK_LABEL[ctx.block]
        + " (แบบจำลองประเมินราย 6 ชั่วโมง ไม่ได้แยกรายชั่วโมง)");
    } else if (ctx.unit === "daily") {
      parts.push("ใช้ผลประเมินภาพรวมทั้งวัน " + fmtDate(ctx.date));
    } else {
      parts.push("กรอกเวลาออกเดินทาง");
    }
    parts.push(ctx.date > LAST_OBSERVED_DATE ? "วันที่นี้เป็นฉากทัศน์วิจัย ยังไม่มีข้อมูลจริงให้เทียบ" : "ช่วงที่เคยใช้ตรวจสอบแบบจำลองย้อนหลัง");
    const r = state.route;
    if (ctx.unit === "6h" && ctx.block && r && r.status === "ready" && isNum(r.duration)) {
      const m = /^(\d{2}):(\d{2})/.exec(ctx.time);
      const arriveMin = Number(m[1]) * 60 + Number(m[2]) + Math.round(r.duration / 60);
      const arriveBlock = arriveMin >= 1440 ? null : hourToBlock(Math.floor(arriveMin / 60));
      if (arriveBlock !== ctx.block) {
        parts.push("การเดินทางอาจกินเวลาข้ามไปช่วงเวลาถัดไป แต่ทุกจุดยังแสดงผลของช่วงเวลาออกเดินทาง");
      }
    }
  }
  $("timeNote").textContent = parts.join(" · ");
}

function onTimeChanged() {
  updateTimeNote();
  const ctx = timeContext();
  if (!state.route || state.route.status !== "ready") return;
  // Same date + 6h block (or daily) as the running/finished forecast: nothing to refresh.
  const settled = ["segments", "matching", "predicting", "none", "done"].includes(state.forecast.status);
  if (ctx.key && ctx.key === state.forecastKey && settled) return;
  // Clear colours for the old inputs immediately; refresh after the user pauses.
  invalidateForecast();
  state.forecast = { status: ctx.valid ? "pending" : "invalid-time" };
  renderForecast();
  if (state.forecastTimer) clearTimeout(state.forecastTimer);
  if (ctx.valid) state.forecastTimer = setTimeout(() => { state.forecastTimer = null; runForecast(); }, 450);
}

// ---------------------------------------------------------------- place search (Photon)

function placeFromPhoton(feature) {
  const p = feature && feature.properties;
  const c = feature && feature.geometry && feature.geometry.coordinates;
  if (!p || !Array.isArray(c) || c.length < 2) return null;
  const lon = c[0];
  const lat = c[1];
  if (p.countrycode !== "TH" || !acceptablePoint(lat, lon)) return null;
  const str = (v) => (typeof v === "string" && v.trim() ? v.trim() : null);
  const street = str(p.street) ? str(p.street) + (str(p.housenumber) ? " " + str(p.housenumber) : "") : null;
  const name = str(p.name) || street || str(p.locality) || str(p.district) || str(p.city) || str(p.county) || str(p.state);
  if (!name) return null;
  const detailParts = [];
  for (const v of [street, str(p.locality), str(p.district), str(p.city), str(p.county), str(p.state)]) {
    if (v && v !== name && !detailParts.includes(v)) detailParts.push(v);
  }
  return {
    key: String(p.osm_type || "") + String(p.osm_id || "") + "@" + lat + "," + lon,
    name,
    detail: detailParts.join(" · "),
    kind: PLACE_KIND_TH[p.osm_value] || null,
    lat,
    lon,
    source: "search",
  };
}

async function searchPlaces(which) {
  const f = state.fields[which];
  const input = $(which + "Input");
  const q = input.value.trim().replace(/\s+/g, " ");
  if (f.controller) f.controller.abort();
  f.controller = null;
  const gen = ++f.searchGen;
  f.results = null;
  if (q.length < 2) {
    setFieldStatus(which, "พิมพ์ชื่อสถานที่อย่างน้อย 2 ตัวอักษร แล้วกดค้นหา", true);
    renderField(which);
    return;
  }
  if (geocodeCache.has(q)) {
    showResults(which, q, geocodeCache.get(q));
    return;
  }
  const controller = new AbortController();
  f.controller = controller;
  setFieldStatus(which, "กำลังค้นหา “" + q + "”…", false);
  renderField(which);
  let places = null;
  let problem = null;
  try {
    await takeTurn("photon", controller.signal);
    const params = new URLSearchParams({ q, limit: String(CONFIG.photonLimit), bbox: CONFIG.photonBbox });
    const { status, json } = await fetchJson(CONFIG.photonUrl + "?" + params.toString(), { controller, timeoutMs: EXTERNAL_TIMEOUT_MS });
    if (status === 200 && json && Array.isArray(json.features)) {
      const seen = new Set();
      places = [];
      for (const feature of json.features) {
        const place = placeFromPhoton(feature);
        if (place && !seen.has(place.key)) { seen.add(place.key); places.push(place); }
      }
    } else {
      problem = status === 429 ? "busy" : "http";
    }
  } catch (failure) {
    if (failure && failure.kind === "aborted") return;
    problem = (failure && failure.kind) || "invalid";
  }
  if (gen !== f.searchGen) return;
  f.controller = null;
  if (problem) {
    const text = problem === "busy" ? "บริการค้นหาสถานที่มีผู้ใช้มาก รอสักครู่แล้วกดค้นหาอีกครั้ง"
      : problem === "timeout" ? "บริการค้นหาสถานที่ตอบช้าเกินไป กดค้นหาอีกครั้ง หรือเลือกจุดบนแผนที่"
        : "ค้นหาสถานที่ไม่สำเร็จ (บริการค้นหาสาธารณะอาจไม่พร้อม) กดค้นหาอีกครั้ง หรือเลือกจุดบนแผนที่";
    setFieldStatus(which, text, true);
    renderField(which);
    return;
  }
  geocodeCache.set(q, places);
  showResults(which, q, places);
}

function showResults(which, q, places) {
  const f = state.fields[which];
  f.results = places;
  if (places.length === 0) {
    setFieldStatus(which, "ไม่พบสถานที่ในประเทศไทยที่ตรงกับ “" + q + "” ลองพิมพ์ชื่ออื่น หรือเลือกจุดบนแผนที่", true);
  } else {
    setFieldStatus(which, "พบ " + places.length + " ผลลัพธ์ — เลือกรายการที่ตรงกับ" + WHICH_TH[which] + "ของคุณ (ชื่อซ้ำกันได้ ตรวจดูอำเภอ/จังหวัด)", false);
  }
  renderField(which);
}

function setFieldStatus(which, text, isError) {
  state.fields[which].status = text;
  state.fields[which].error = isError;
}

function renderField(which) {
  const f = state.fields[which];
  const status = $(which + "Status");
  status.textContent = f.status;
  status.classList.toggle("is-error", !!f.error);
  status.hidden = !f.status;

  const sel = $(which + "Selected");
  sel.replaceChildren();
  if (f.place) {
    sel.append(el("span", "selected-check", "✓"));
    const text = el("span", "selected-text");
    text.append(el("strong", null, f.place.name));
    const sub = [f.place.kind, f.place.detail].filter(Boolean).join(" · ");
    if (sub) text.append(el("span", null, sub));
    sel.append(text);
    sel.hidden = false;
  } else {
    sel.hidden = true;
  }

  const list = $(which + "Results");
  list.replaceChildren();
  if (f.results && f.results.length && !f.place) {
    for (const place of f.results) {
      const li = el("li");
      const btn = el("button", "result-btn");
      btn.type = "button";
      btn.append(el("span", "result-name", place.name));
      const sub = [place.kind, place.detail].filter(Boolean).join(" · ");
      if (sub) btn.append(el("span", "result-sub", sub));
      btn.addEventListener("click", () => selectPlace(which, place));
      li.append(btn);
      list.append(li);
    }
    list.hidden = false;
  } else {
    list.hidden = true;
  }
}

function selectPlace(which, place) {
  const f = state.fields[which];
  if (f.controller) f.controller.abort();
  f.controller = null;
  f.searchGen += 1;
  f.place = place;
  $(which + "Input").value = place.name;
  setFieldStatus(which, "", false);
  invalidateRoute();
  renderField(which);
  updateEndpointMarker(which);
  if (map.leaflet && !state.fields.origin.place !== !state.fields.destination.place) {
    map.leaflet.setView([place.lat, place.lon], Math.max(map.leaflet.getZoom(), 11));
  } else {
    fitEndpoints();
  }
  refreshControls();
}

// Any edit of the text invalidates the selected place and the current route.
function onFieldInput(which) {
  const f = state.fields[which];
  if (f.controller) f.controller.abort();
  f.controller = null;
  f.searchGen += 1;
  f.results = null;
  setFieldStatus(which, "", false);
  if (f.place) {
    f.place = null;
    updateEndpointMarker(which);
    invalidateRoute();
  }
  renderField(which);
  refreshControls();
}

function swapEndpoints() {
  const hadRoute = !!state.route && state.route.status === "ready";
  const a = state.fields.origin;
  const b = state.fields.destination;
  for (const f of [a, b]) { if (f.controller) f.controller.abort(); f.controller = null; f.searchGen += 1; }
  [a.place, b.place] = [b.place, a.place];
  [a.results, b.results] = [b.results, a.results];
  [a.status, b.status] = [b.status, a.status];
  [a.error, b.error] = [b.error, a.error];
  const oi = $("originInput");
  const di = $("destinationInput");
  [oi.value, di.value] = [di.value, oi.value];
  invalidateRoute();
  for (const which of WHICH) { renderField(which); updateEndpointMarker(which); }
  refreshControls();
  if (hadRoute && a.place && b.place) requestRoute();
}

function fillExample() {
  cancelPicking();
  const examples = { origin: "มหาวิทยาลัยศรีปทุม", destination: "อุทยานแห่งชาติเขาใหญ่" };
  for (const which of WHICH) {
    $(which + "Input").value = examples[which];
    onFieldInput(which);
  }
  // Real searches (rate-limited); the user still chooses the correct result in each list.
  searchPlaces("origin");
  searchPlaces("destination");
  $("originInput").focus();
}

// ---------------------------------------------------------------- map picking

function startPicking(which) {
  if (!map.leaflet || state.boundaryStatus !== "ready") return;
  state.picking = which;
  $("pickText").textContent = "แตะหรือคลิกบนแผนที่เพื่อเลือก" + WHICH_TH[which] + " (ภายในประเทศไทย)";
  $("pickBanner").hidden = false;
  $("map").classList.add("is-picking");
  if (isMobile()) setSheet(false);
  refreshControls();
  $("btnCancelPick").focus();
}

function cancelPicking() {
  if (!state.picking) return;
  const which = state.picking;
  state.picking = null;
  $("pickBanner").hidden = true;
  $("map").classList.remove("is-picking");
  refreshControls();
  if (isMobile()) setSheet(true);
  $(which + "Pick").focus();
}

function rejectPick() {
  $("pickText").textContent = "ตำแหน่งนี้อยู่นอกประเทศไทย — เลือกจุดภายในประเทศไทยเท่านั้น";
}

function onMapClick(e) {
  if (!state.picking) return;
  const { lat, lng } = e.latlng;
  if (!acceptablePoint(lat, lng) || state.boundaryStatus !== "ready") {
    rejectPick();
    return;
  }
  const which = state.picking;
  state.picking = null;
  $("pickBanner").hidden = true;
  $("map").classList.remove("is-picking");
  const place = {
    key: "map@" + lat + "," + lng,
    name: "จุดที่เลือก " + fmtCoord(lat, lng),
    detail: "เลือกจากแผนที่ (พิกัด)",
    kind: null,
    lat,
    lon: lng,
    source: "map",
  };
  state.fields[which].results = null;
  selectPlace(which, place);
  if (isMobile()) setSheet(true);
  $(which + "Pick").focus();
}

// ---------------------------------------------------------------- map

function initMap() {
  if (typeof window.L === "undefined" || !L.map) {
    $("mapFallbackText").textContent = "โหลดชุดแผนที่ไม่สำเร็จ (แผนที่ต้องใช้อินเทอร์เน็ต) ยังค้นหาสถานที่และดูสรุปเส้นทางได้ตามปกติ";
    $("mapFallback").hidden = false;
    $("btnResetView").disabled = true;
    return;
  }
  try {
    const m = L.map("map", {
      zoomControl: true, minZoom: 5, maxZoom: 18, zoomSnap: 0.5,
      maxBounds: VIEW_BOUNDS, maxBoundsViscosity: 1.0, worldCopyJump: false,
    });
    m.createPane("maskPane").style.zIndex = 350;
    m.createPane("forecastPane").style.zIndex = 590;
    const tiles = L.tileLayer(CONFIG.tileUrl, {
      maxZoom: 19,
      bounds: VIEW_BOUNDS,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).addTo(m);
    tiles.on("tileload", () => { if (map.tileErrors >= 4) hideMapNotice(); map.tileErrors = 0; });
    tiles.on("tileerror", () => {
      map.tileErrors += 1;
      if (map.tileErrors >= 4) showMapNotice("โหลดภาพแผนที่พื้นหลังบางส่วนไม่สำเร็จ ตรวจสอบอินเทอร์เน็ต — การค้นหาและเส้นทางยังใช้งานได้");
    });
    m.on("click", onMapClick);
    map.leaflet = m;
    fitThailand();
    updateMapLayout();
    m.on("resize", updateMapLayout);
    if (state.boundaryStatus === "ready") addMask();
  } catch (_) {
    map.leaflet = null;
    $("mapFallback").hidden = false;
  }
}

function fitThailand() {
  if (!map.leaflet) return;
  map.leaflet.fitBounds(THAILAND_FIT, fitPadding());
}

// The user may not zoom out beyond the zoom that shows the whole country in this viewport.
// On mobile the attribution moves to the top so the bottom sheet never covers it.
function updateMapLayout() {
  const m = map.leaflet;
  if (!m) return;
  const z = m.getBoundsZoom(THAILAND_FIT, false);
  if (isNum(z)) m.setMinZoom(Math.max(4, z));
  if (m.attributionControl) m.attributionControl.setPosition(isMobile() ? "topright" : "bottomright");
}

function fitPadding() {
  if (isMobile()) {
    const sheet = $("sheet");
    const bottom = state.sheetOpen ? Math.min(sheet.offsetHeight, window.innerHeight * 0.6) : sheet.offsetHeight;
    return { paddingTopLeft: [16, 64], paddingBottomRight: [16, bottom + 16] };
  }
  return { padding: [36, 36] };
}

// Opaque mask over every non-Thai area: a world polygon with the country polygons as holes.
function addMask() {
  if (!map.leaflet || !state.boundary || map.mask) return;
  const world = [[-85, -180], [-85, 180], [85, 180], [85, -180]];
  const holes = state.boundary.map((polygon) => polygon[0].map(([lon, lat]) => [lat, lon]));
  map.mask = L.polygon([world, ...holes], {
    pane: "maskPane", stroke: false, fillColor: "#ece6da", fillOpacity: 1,
    interactive: true, bubblingMouseEvents: false, className: "country-mask",
  }).addTo(map.leaflet);
  map.mask.on("click", () => { if (state.picking) rejectPick(); });
  map.outline = L.polyline(holes.map((ring) => ring.concat([ring[0]])), {
    pane: "maskPane", color: "#9a8f7c", weight: 1.5, opacity: 0.9, interactive: false,
  }).addTo(map.leaflet);
}

function showMapNotice(text) {
  $("mapNotice").textContent = text;
  $("mapNotice").hidden = false;
}

function hideMapNotice() {
  $("mapNotice").hidden = true;
}

function endpointIcon(which) {
  const node = el("span", "endpoint-pin " + (which === "origin" ? "pin-a" : "pin-b"), which === "origin" ? "A" : "B");
  return L.divIcon({ html: node, className: "endpoint-icon", iconSize: [32, 32], iconAnchor: [16, 16] });
}

function updateEndpointMarker(which) {
  if (!map.leaflet) return;
  if (map.endpoints[which]) { map.endpoints[which].remove(); map.endpoints[which] = null; }
  const place = state.fields[which].place;
  if (!place) return;
  map.endpoints[which] = L.marker([place.lat, place.lon], {
    icon: endpointIcon(which), interactive: false, keyboard: false, zIndexOffset: 1000,
  }).addTo(map.leaflet);
}

function fitEndpoints() {
  if (!map.leaflet) return;
  const pts = WHICH.map((w) => state.fields[w].place).filter(Boolean).map((p) => [p.lat, p.lon]);
  if (pts.length === 2) map.leaflet.fitBounds(pts, { ...fitPadding(), maxZoom: 13 });
}

function clearRouteLayers() {
  for (const layer of map.routeLayers.concat(map.connectors)) layer.remove();
  map.routeLayers = [];
  map.connectors = [];
}

function drawRoute(route) {
  clearRouteLayers();
  if (!map.leaflet) return;
  const latlngs = route.coords.map(([lon, lat]) => [lat, lon]);
  map.routeLayers.push(L.polyline(latlngs, { ...ROUTE_CASING, interactive: false }).addTo(map.leaflet));
  map.routeLayers.push(L.polyline(latlngs, { ...ROUTE_STYLE, interactive: false }).addTo(map.leaflet));
  // Disclose the connector between a chosen point and the road the router snapped it to.
  WHICH.forEach((which, i) => {
    const snap = route.snaps[i];
    const place = route[which];
    if (snap && isNum(snap.distance) && snap.distance > SNAP_NOTE_M) {
      map.connectors.push(L.polyline([[place.lat, place.lon], [snap.location[1], snap.location[0]]], {
        color: "#7a3c10", weight: 3, opacity: 0.85, dashArray: "4 8", interactive: false,
      }).addTo(map.leaflet));
    }
  });
  map.leaflet.fitBounds(L.latLngBounds(latlngs), fitPadding());
}

// ---------------------------------------------------------------- routing (OSRM)

function invalidateRoute() {
  state.routeGen += 1;
  if (state.routeController) state.routeController.abort();
  state.routeController = null;
  state.route = null;
  clearRouteLayers();
  invalidateForecast();
  state.forecast = { status: "idle" };
  state.forecastKey = null;
  renderRoute();
  renderForecast();
  updateTimeNote();
  updateSheetSummary();
}

async function requestRoute() {
  const origin = state.fields.origin.place;
  const destination = state.fields.destination.place;
  if (!origin || !destination) return;
  cancelPicking();
  invalidateRoute();
  const gen = state.routeGen;
  const controller = new AbortController();
  state.routeController = controller;
  state.route = { status: "loading", origin, destination };
  renderRoute();
  refreshControls();

  const finish = (route) => {
    if (gen !== state.routeGen) return;
    state.routeController = null;
    state.route = route;
    renderRoute();
    refreshControls();
    updateTimeNote();
    updateSheetSummary();
  };

  if (Math.abs(origin.lat - destination.lat) < 1e-6 && Math.abs(origin.lon - destination.lon) < 1e-6) {
    finish({ status: "error", origin, destination, problem: { title: "ต้นทางและปลายทางเป็นจุดเดียวกัน", text: "เลือกปลายทางอื่นแล้วกด “ดูเส้นทาง” อีกครั้ง" } });
    return;
  }

  let status = 0;
  let json = null;
  try {
    await takeTurn("osrm", controller.signal);
    const pair = origin.lon.toFixed(6) + "," + origin.lat.toFixed(6) + ";" + destination.lon.toFixed(6) + "," + destination.lat.toFixed(6);
    ({ status, json } = await fetchJson(CONFIG.osrmRouteUrl + pair + "?overview=full&geometries=geojson&steps=false",
      { controller, timeoutMs: EXTERNAL_TIMEOUT_MS }));
  } catch (failure) {
    if (failure.kind === "aborted" || gen !== state.routeGen) return;
    finish({
      status: "error", origin, destination,
      problem: failure.kind === "timeout"
        ? { title: "ระบบคำนวณเส้นทางตอบช้าเกินไป", text: "ระบบเส้นทางสาธารณะอาจมีผู้ใช้มาก โปรดลองอีกครั้ง" }
        : { title: "เชื่อมต่อระบบคำนวณเส้นทางไม่ได้", text: "ตรวจสอบอินเทอร์เน็ต แล้วลองอีกครั้ง (ต้นทางและปลายทางยังถูกเก็บไว้)" },
    });
    return;
  }
  if (gen !== state.routeGen) return;
  const code = json && typeof json.code === "string" ? json.code : null;
  const r = json && Array.isArray(json.routes) ? json.routes[0] : null;
  const coords = r && r.geometry && Array.isArray(r.geometry.coordinates) ? r.geometry.coordinates : null;
  if (status === 200 && code === "Ok" && coords && coords.length >= 2 && isNum(r.distance) && isNum(r.duration)) {
    const wps = Array.isArray(json.waypoints) ? json.waypoints : [];
    const snaps = [0, 1].map((i) => {
      const w = wps[i];
      return w && Array.isArray(w.location) && isNum(w.distance) ? { distance: w.distance, location: w.location } : null;
    });
    const route = { status: "ready", origin, destination, coords, distance: r.distance, duration: r.duration, snaps, matches: null };
    finish(route);
    drawRoute(route);
    runForecast();
    return;
  }
  let problem;
  if (code === "NoRoute") problem = { title: "ไม่พบเส้นทางขับรถระหว่างสองจุดนี้", text: "จุดใดจุดหนึ่งอาจอยู่บนเกาะหรือไม่มีถนนเชื่อมกัน ลองเลือกจุดที่ใกล้ถนนมากขึ้น" };
  else if (code === "NoSegment") problem = { title: "ไม่พบถนนใกล้จุดที่เลือก", text: "ระบบเส้นทางหาถนนใกล้ต้นทางหรือปลายทางไม่ได้ ลองเลือกจุดอื่น" };
  else if (status === 429) problem = { title: "ระบบเส้นทางสาธารณะมีผู้ใช้มาก", text: "รอสักครู่แล้วลองอีกครั้ง" };
  else problem = { title: "คำนวณเส้นทางไม่สำเร็จ", text: "ระบบเส้นทางสาธารณะตอบกลับผิดปกติ โปรดลองอีกครั้ง" };
  finish({ status: "error", origin, destination, problem });
}

function renderRoute() {
  const section = $("routeSection");
  const body = $("routeBody");
  body.replaceChildren();
  const r = state.route;
  if (!r) { section.hidden = true; return; }
  section.hidden = false;
  const od = el("p", "route-od");
  od.append(el("span", "pin pin-a", "A"), el("span", null, r.origin.name), el("span", "route-arrow", "→"),
    el("span", "pin pin-b", "B"), el("span", null, r.destination.name));
  body.append(od);
  if (r.status === "loading") {
    body.append(loadingRow("กำลังคำนวณเส้นทางขับรถ…"));
    return;
  }
  if (r.status === "error") {
    body.append(errorBox({ title: r.problem.title, text: r.problem.text }, requestRoute));
    return;
  }
  const grid = el("div", "stat-grid");
  grid.append(stat("ระยะทาง", fmtKm(r.distance)), stat("เวลาขับโดยประมาณ", fmtDuration(r.duration)));
  body.append(grid);
  body.append(el("p", "help", "เส้นทางและเวลาประมาณจากระบบเส้นทางสาธารณะ ไม่รวมสภาพจราจรจริง และไม่ใช่การนำทางแบบเลี้ยวต่อเลี้ยว"));
  WHICH.forEach((which, i) => {
    const snap = r.snaps[i];
    if (snap && snap.distance > SNAP_NOTE_M) {
      body.append(el("div", "note-box",
        WHICH_TH[which] + "ที่เลือกอยู่ห่างจากถนนที่ระบบเส้นทางใช้ประมาณ " + fmtMeters(snap.distance)
        + " เส้นทางจึงเริ่ม/สิ้นสุดที่ถนนใกล้ที่สุด (เส้นประบนแผนที่) ไม่ได้หมายความว่าขับรถเข้าถึงจุดนั้นได้โดยตรง"));
    }
  });
}

// ---------------------------------------------------------------- route geometry index

function buildRouteIndex(coords) {
  let minLat = Infinity; let maxLat = -Infinity; let minLon = Infinity; let maxLon = -Infinity;
  for (const [lon, lat] of coords) {
    if (lat < minLat) minLat = lat; if (lat > maxLat) maxLat = lat;
    if (lon < minLon) minLon = lon; if (lon > maxLon) maxLon = lon;
  }
  const lat0 = (minLat + maxLat) / 2;
  const lon0 = (minLon + maxLon) / 2;
  // Local equirectangular metres around the route centre (adequate for a 50 m comparison).
  const kx = 111320 * Math.cos((lat0 * Math.PI) / 180);
  const ky = 110574;
  const n = coords.length;
  const xs = new Float64Array(n);
  const ys = new Float64Array(n);
  const cum = new Float64Array(n);
  for (let i = 0; i < n; i += 1) {
    xs[i] = (coords[i][0] - lon0) * kx;
    ys[i] = (coords[i][1] - lat0) * ky;
    if (i > 0) cum[i] = cum[i - 1] + Math.hypot(xs[i] - xs[i - 1], ys[i] - ys[i - 1]);
  }
  const grid = new Map();
  const cellKey = (cx, cy) => (cx + 100000) * 1000000 + (cy + 100000);
  const add = (x0, y0, x1, y1, seg) => {
    const ax = Math.floor((Math.min(x0, x1) - MATCH_MAX_DIST_M) / GRID_CELL_M);
    const bx = Math.floor((Math.max(x0, x1) + MATCH_MAX_DIST_M) / GRID_CELL_M);
    const ay = Math.floor((Math.min(y0, y1) - MATCH_MAX_DIST_M) / GRID_CELL_M);
    const by = Math.floor((Math.max(y0, y1) + MATCH_MAX_DIST_M) / GRID_CELL_M);
    for (let cx = ax; cx <= bx; cx += 1) {
      for (let cy = ay; cy <= by; cy += 1) {
        const k = cellKey(cx, cy);
        let list = grid.get(k);
        if (!list) { list = []; grid.set(k, list); }
        if (list[list.length - 1] !== seg) list.push(seg);
      }
    }
  };
  for (let i = 0; i < n - 1; i += 1) {
    // Long straight pieces are inserted in short steps so each step touches few cells.
    const len = cum[i + 1] - cum[i];
    const steps = Math.max(1, Math.ceil(len / GRID_CELL_M));
    for (let s = 0; s < steps; s += 1) {
      const t0 = s / steps; const t1 = (s + 1) / steps;
      add(xs[i] + (xs[i + 1] - xs[i]) * t0, ys[i] + (ys[i + 1] - ys[i]) * t0,
        xs[i] + (xs[i + 1] - xs[i]) * t1, ys[i] + (ys[i + 1] - ys[i]) * t1, i);
    }
  }
  return {
    lat0, lon0, kx, ky, xs, ys, cum, grid, cellKey,
    bbox: { west: minLon, south: minLat, east: maxLon, north: maxLat },
  };
}

// Distance (m) from a projected point to the route, and position along the route; null if > limit.
function nearestOnRoute(index, x, y) {
  const list = index.grid.get(index.cellKey(Math.floor(x / GRID_CELL_M), Math.floor(y / GRID_CELL_M)));
  if (!list) return null;
  let best = null;
  for (const i of list) {
    const x0 = index.xs[i]; const y0 = index.ys[i];
    const dx = index.xs[i + 1] - x0; const dy = index.ys[i + 1] - y0;
    const len2 = dx * dx + dy * dy;
    let t = len2 > 0 ? ((x - x0) * dx + (y - y0) * dy) / len2 : 0;
    t = Math.max(0, Math.min(1, t));
    const d = Math.hypot(x - (x0 + t * dx), y - (y0 + t * dy));
    if (d <= MATCH_MAX_DIST_M && (!best || d < best.d)) {
      best = { d, along: index.cum[i] + t * Math.sqrt(len2) };
    }
  }
  return best;
}

function featureLines(geometry) {
  if (!geometry) return [];
  if (geometry.type === "LineString") return [geometry.coordinates];
  if (geometry.type === "MultiLineString") return geometry.coordinates;
  return [];
}

// Evenly spaced samples (each representing an equal share of the line length).
function sampleLine(index, line) {
  const pts = [];
  for (const c of line) if (Array.isArray(c) && isNum(c[0]) && isNum(c[1])) pts.push([(c[0] - index.lon0) * index.kx, (c[1] - index.lat0) * index.ky]);
  if (pts.length < 2) return { length: 0, samples: [] };
  const cum = [0];
  for (let i = 1; i < pts.length; i += 1) cum.push(cum[i - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]));
  const length = cum[cum.length - 1];
  if (length <= 0) return { length: 0, samples: [] };
  const n = Math.max(1, Math.ceil(length / MATCH_SAMPLE_M));
  const samples = [];
  let j = 0;
  for (let s = 0; s < n; s += 1) {
    const target = ((s + 0.5) * length) / n;
    while (j < cum.length - 2 && cum[j + 1] < target) j += 1;
    const segLen = cum[j + 1] - cum[j];
    const t = segLen > 0 ? (target - cum[j]) / segLen : 0;
    samples.push([pts[j][0] + (pts[j + 1][0] - pts[j][0]) * t, pts[j][1] + (pts[j + 1][1] - pts[j][1]) * t]);
  }
  return { length, samples };
}

function featureBbox(lines) {
  let w = Infinity; let s = Infinity; let e = -Infinity; let n = -Infinity;
  for (const line of lines) {
    for (const c of line) {
      if (!Array.isArray(c)) continue;
      if (c[0] < w) w = c[0]; if (c[0] > e) e = c[0];
      if (c[1] < s) s = c[1]; if (c[1] > n) n = c[1];
    }
  }
  return { west: w, south: s, east: e, north: n };
}

// Match actual RoadAware segments to the route (approximate candidate linkage). Yields to the UI.
async function matchSegments(route, features, isStale, onProgress) {
  const index = buildRouteIndex(route.coords);
  const margin = 0.001; // ~100 m, covers the 50 m tolerance at Thai latitudes
  const rb = index.bbox;
  const matches = [];
  const CHUNK = 150;
  for (let start = 0; start < features.length; start += CHUNK) {
    if (isStale()) throw new RequestFailure("aborted");
    const end = Math.min(features.length, start + CHUNK);
    for (let k = start; k < end; k += 1) {
      const f = features[k];
      const id = f && f.properties ? String(f.properties.segment_id ?? f.id) : null;
      if (!id) continue;
      const lines = featureLines(f.geometry);
      if (!lines.length) continue;
      const fb = featureBbox(lines);
      if (fb.east < rb.west - margin || fb.west > rb.east + margin || fb.north < rb.south - margin || fb.south > rb.north + margin) continue;
      let total = 0;
      let length = 0;
      const hits = [];
      for (const line of lines) {
        const { length: len, samples } = sampleLine(index, line);
        length += len;
        for (const [x, y] of samples) {
          total += 1;
          const near = nearestOnRoute(index, x, y);
          if (near) hits.push({ x, y, along: near.along });
        }
      }
      if (total === 0 || hits.length / total < MATCH_MIN_SHARE) continue;
      const anchor = hits[Math.floor(hits.length / 2)];
      matches.push({
        id,
        feature: f,
        lat: anchor.y / index.ky + index.lat0,
        lon: anchor.x / index.kx + index.lon0,
        alongM: anchor.along,
        share: hits.length / total,
        lengthM: length,
      });
    }
    onProgress(end, features.length);
    await nextTick();
  }
  if (isStale()) throw new RequestFailure("aborted");
  matches.sort((a, b) => a.alongM - b.alongM);
  return matches;
}

// ---------------------------------------------------------------- forecast pipeline

function invalidateForecast() {
  state.forecastGen += 1;
  if (state.forecastController) state.forecastController.abort();
  state.forecastController = null;
  if (state.forecastTimer) { clearTimeout(state.forecastTimer); state.forecastTimer = null; }
  clearDots();
  clearSelection();
}

function setForecast(next) {
  state.forecast = next;
  renderForecast();
}

async function runForecast() {
  const route = state.route;
  if (!route || route.status !== "ready") return;
  invalidateForecast();
  const gen = state.forecastGen;
  const ctx = timeContext();
  state.forecastKey = ctx.key;
  if (!ctx.valid) { setForecast({ status: "invalid-time" }); return; }
  if (state.ready === "checking") { setForecast({ status: "waiting" }); return; }
  if (state.ready !== "ready") { setForecast({ status: "down" }); return; }
  const controller = new AbortController();
  state.forecastController = controller;
  const isStale = () => gen !== state.forecastGen || state.route !== route;
  let stage = "segments";
  try {
    if (!route.matches) {
      const features = await loadRouteSegments(route, controller, isStale);
      if (isStale()) return;
      stage = "matching";
      setForecast({ status: "matching", done: 0, total: features.length });
      const matches = await matchSegments(route, features, isStale, (done, total) => {
        if (!isStale()) setForecast({ status: "matching", done, total });
      });
      if (isStale()) return;
      route.matches = matches;
    }
    const matches = route.matches;
    if (matches.length === 0) {
      state.forecastController = null;
      setForecast({ status: "none", ctx });
      return;
    }
    stage = "predictions";
    const results = new Map();
    let caveats = null;
    for (let i = 0; i < matches.length; i += PREDICTION_BATCH) {
      setForecast({ status: "predicting", done: i, total: matches.length });
      const batch = matches.slice(i, i + PREDICTION_BATCH);
      const requests = batch.map((m) => {
        const row = { segment_id: m.id, target_date: ctx.date };
        if (ctx.block) row.time_block = ctx.block;
        return row;
      });
      const json = await apiFetch("/api/v1/spatial/predictions", { method: "POST", body: { unit: ctx.unit, requests }, controller });
      if (isStale()) return;
      const rows = Array.isArray(json.results) ? json.results : null;
      if (!rows || rows.length !== batch.length) throw new RequestFailure("invalid");
      rows.forEach((row, k) => {
        if (!row || row.segment_id !== batch[k].id || row.target_date !== ctx.date) throw new RequestFailure("invalid");
        results.set(batch[k].id, row);
      });
      if (!caveats && Array.isArray(json.caveats)) caveats = json.caveats;
    }
    if (isStale()) return;
    state.forecastController = null;
    setForecast({ status: "done", ctx, results, caveats });
    drawDots();
  } catch (failure) {
    if (isStale() || failure.kind === "aborted") return;
    state.forecastController = null;
    // Nothing partial is kept: a failed batch means no colours are shown for these inputs.
    clearDots();
    if (isServiceDown(failure) && state.ready === "ready") setReady("down");
    setForecast({ status: "error", stage, failure });
  }
}

async function loadRouteSegments(route, controller, isStale) {
  const rb = buildBboxFromCoords(route.coords);
  const bbox = clampBbox({ west: rb.west - 0.01, south: rb.south - 0.01, east: rb.east + 0.01, north: rb.north + 0.01 });
  if (!bbox) return [];
  const features = [];
  const seen = new Set();
  let cursor = null;
  let total = null;
  for (let page = 0; page < MAX_SEGMENT_PAGES; page += 1) {
    setForecast({ status: "segments", loaded: features.length, total });
    const params = new URLSearchParams({ bbox: [bbox.west, bbox.south, bbox.east, bbox.north].join(","), limit: String(SEGMENT_PAGE_SIZE) });
    if (cursor) params.set("cursor", cursor);
    const json = await apiFetch("/api/v1/segments?" + params.toString(), { controller });
    if (isStale()) throw new RequestFailure("aborted");
    const list = Array.isArray(json.features) ? json.features : null;
    const info = json.page && typeof json.page === "object" ? json.page : null;
    if (!list || !info) throw new RequestFailure("invalid");
    for (const f of list) {
      const id = f && f.properties ? String(f.properties.segment_id ?? f.id) : null;
      if (id && !seen.has(id)) { seen.add(id); features.push(f); }
    }
    if (isNum(info.total_matched)) total = info.total_matched;
    const next = info.next_cursor ?? null;
    if (next === null) return features;
    if (next === cursor) throw new RequestFailure("invalid");
    cursor = String(next);
  }
  // Coverage could not be loaded completely within the page limit: do not treat it as complete.
  throw new RequestFailure("invalid");
}

function buildBboxFromCoords(coords) {
  return featureBbox([coords]);
}

function retryForecast() {
  if (state.ready !== "ready") {
    setForecast({ status: "waiting" });
    checkReady();
    return;
  }
  runForecast();
}

function validHex(v) {
  return typeof v === "string" && HEX_RE.test(v) ? v : null;
}

function dotIcon(colour, selected) {
  const node = el("span", "forecast-dot" + (selected ? " is-selected" : ""));
  const core = el("span", "forecast-dot-core");
  core.style.background = colour || NEUTRAL_DOT;
  node.append(core);
  return L.divIcon({ html: node, className: "forecast-icon", iconSize: [36, 36], iconAnchor: [18, 18] });
}

function bandTitle(row) {
  const th = row ? BAND_TH[row.colour] : null;
  return th ? th.title : row && row.colour_text ? String(row.colour_text) : "ไม่มีข้อมูล";
}

function drawDots() {
  clearDots();
  const f = state.forecast;
  if (!map.leaflet || f.status !== "done") return;
  for (const m of state.route.matches) {
    const row = f.results.get(m.id);
    if (!row) continue;
    const marker = L.marker([m.lat, m.lon], {
      icon: dotIcon(validHex(row.colour_hex), m.id === state.selectedId),
      pane: "forecastPane", keyboard: false, riseOnHover: true,
    });
    marker.bindTooltip(() => {
      const tip = el("span");
      tip.append(el("strong", null, bandTitle(row)));
      if (row.colour_text) tip.append(el("span", "tip-sub", String(row.colour_text)));
      return tip;
    }, { direction: "top", offset: [0, -14], className: "dot-tip" });
    marker.on("click", () => selectSegment(m.id, false));
    marker.addTo(map.leaflet);
    map.dots.set(m.id, marker);
  }
}

function clearDots() {
  for (const marker of map.dots.values()) marker.remove();
  map.dots.clear();
}

function legendEntries(f) {
  const groups = new Map();
  for (const row of f.results.values()) {
    const key = String(row.colour ?? "unknown");
    if (!groups.has(key)) groups.set(key, { key, hex: validHex(row.colour_hex), text: row.colour_text, count: 0 });
    groups.get(key).count += 1;
  }
  return [...groups.values()].sort((a, b) => {
    const ia = BAND_ORDER.indexOf(a.key); const ib = BAND_ORDER.indexOf(b.key);
    return (ia < 0 ? 99 : ia) - (ib < 0 ? 99 : ib);
  });
}

function progressRow(text, done, total) {
  const wrap = el("div", "progress");
  wrap.append(loadingRow(text));
  if (isNum(done) && isNum(total) && total > 0) {
    const bar = el("div", "progress-track");
    const fill = el("div", "progress-fill");
    fill.style.width = Math.min(100, (100 * done) / total).toFixed(0) + "%";
    bar.append(fill);
    wrap.append(bar);
  }
  return wrap;
}

function renderForecast() {
  const section = $("forecastSection");
  const body = $("forecastBody");
  body.replaceChildren();
  const r = state.route;
  if (!r || r.status !== "ready") { section.hidden = true; return; }
  section.hidden = false;
  const f = state.forecast;
  const keepRoute = "เส้นทางยังแสดงและใช้งานได้ตามปกติ";
  switch (f.status) {
    case "pending":
      body.append(loadingRow("กำลังอัปเดตผลประเมินตามวันและเวลาใหม่…"));
      break;
    case "invalid-time":
      body.append(el("div", "note-box", "เลือกวันที่ (1 ม.ค. 2024 – 31 ธ.ค. 2027) และเวลาออกเดินทางให้ครบ เพื่อดูผลประเมินตามเส้นทาง " + keepRoute));
      break;
    case "waiting":
      body.append(loadingRow("กำลังเชื่อมต่อบริการผลประเมิน… " + keepRoute));
      break;
    case "down": {
      const box = el("div", "error-box");
      box.setAttribute("role", "alert");
      box.append(el("strong", null, "ขณะนี้ยังดูผลประเมินไม่ได้"), el("span", null, "บริการผลประเมินไม่พร้อม " + keepRoute + " ต้นทาง ปลายทาง และเวลายังถูกเก็บไว้"));
      const btn = el("button", "btn btn-ghost btn-touch", "ลองอีกครั้ง");
      btn.type = "button";
      btn.addEventListener("click", retryForecast);
      box.append(btn);
      body.append(box);
      break;
    }
    case "segments":
      body.append(progressRow(
        isNum(f.total) ? "กำลังโหลดช่วงถนนที่มีข้อมูลในพื้นที่เส้นทาง " + fmtInt(f.loaded) + " / " + fmtInt(f.total) : "กำลังโหลดช่วงถนนที่มีข้อมูลในพื้นที่เส้นทาง…",
        f.loaded, f.total));
      break;
    case "matching":
      body.append(progressRow("กำลังจับคู่ช่วงถนนกับเส้นทาง…", f.done, f.total));
      break;
    case "predicting":
      body.append(progressRow("กำลังโหลดผลประเมิน " + fmtInt(f.done) + " / " + fmtInt(f.total) + " ช่วงถนน", f.done, f.total));
      break;
    case "error":
      body.append(apiErrorBox(f.failure, retryForecast));
      body.append(el("p", "help", f.stage === "predictions"
        ? "โหลดผลประเมินได้ไม่ครบ จึงไม่แสดงจุดสีใด ๆ เพื่อไม่ให้เข้าใจผิดว่าครบถ้วน " + keepRoute
        : "โหลดข้อมูลช่วงถนนในพื้นที่เส้นทางไม่ครบ จึงยังไม่แสดงผลประเมิน " + keepRoute));
      break;
    case "none": {
      const empty = el("div", "empty");
      empty.append(el("strong", null, "ยังไม่มีข้อมูลประเมินในเส้นทางนี้"));
      empty.append(el("span", null, "ระบบมีผลประเมินเฉพาะช่วงถนนทางหลวงบางช่วงที่ผ่านเกณฑ์ และไม่พบช่วงที่อยู่แนวเดียวกับเส้นทางนี้ เส้นทางยังใช้ได้ตามปกติ — ไม่มีข้อมูลไม่ได้แปลว่าปลอดภัย"));
      body.append(empty);
      break;
    }
    case "done":
      renderForecastDone(body, f);
      break;
    default:
      break;
  }
  updateSheetSummary();
}

function renderForecastDone(body, f) {
  const n = state.route.matches.length;
  const ctx = f.ctx;
  body.append(el("p", "forecast-lead",
    "พบ " + fmtInt(n) + " ช่วงถนนที่มีผลประเมินและอยู่แนวเดียวกับเส้นทาง (จับคู่โดยประมาณ) · "
    + (ctx.unit === "6h" ? fmtDate(ctx.date) + " ช่วง " + BLOCK_LABEL[ctx.block] : "ภาพรวมทั้งวัน " + fmtDate(ctx.date))));
  const chips = el("div", "chips");
  chips.append(el("span", "chip " + (ctx.date > LAST_OBSERVED_DATE ? "chip-accent" : "chip-teal"),
    ctx.date > LAST_OBSERVED_DATE ? "ฉากทัศน์วิจัย · ไม่มีข้อมูลจริงให้เทียบ" : "ช่วงที่เคยตรวจสอบย้อนหลัง"));
  body.append(chips);

  const legend = el("ul", "legend");
  legend.setAttribute("aria-label", "คำอธิบายสี");
  for (const g of legendEntries(f)) {
    const li = el("li", "legend-item");
    const sw = el("span", "legend-dot");
    sw.style.background = g.hex || NEUTRAL_DOT;
    const text = el("span", "legend-text");
    const th = BAND_TH[g.key];
    text.append(el("strong", null, th ? th.title : String(g.text ?? g.key)));
    if (g.text) text.append(el("span", null, String(g.text)));
    li.append(sw, text, el("span", "legend-count", fmtInt(g.count) + " ช่วง"));
    legend.append(li);
  }
  const routeItem = el("li", "legend-item");
  const line = el("span", "legend-line");
  const routeText = el("span", "legend-text");
  routeText.append(el("strong", null, "เส้นทางส่วนที่ไม่มีจุดสี"), el("span", null, "ไม่มีข้อมูลประเมิน — ไม่ได้แปลว่าปลอดภัย"));
  routeItem.append(line, routeText, el("span", "legend-count", ""));
  legend.append(routeItem);
  body.append(legend);

  body.append(el("p", "help", "แตะจุดสีบนแผนที่หรือเลือกจากรายการเพื่อดูผลประเมินและประวัติของช่วงถนนนั้น จุดเป็นสัญลักษณ์ของช่วงถนนยาวประมาณ 2 กม. ไม่ใช่รัศมีอันตรายหรือตำแหน่งเกิดเหตุจริง"));

  const det = el("details", "segment-list");
  det.append(el("summary", null, "รายการช่วงถนนตามลำดับเส้นทาง (" + fmtInt(n) + ")"));
  const ul = el("ul", "seg-items");
  for (const m of state.route.matches) {
    const row = f.results.get(m.id);
    const li = el("li");
    const btn = el("button", "seg-item" + (m.id === state.selectedId ? " is-selected" : ""));
    btn.type = "button";
    const dot = el("span", "legend-dot");
    dot.style.background = validHex(row && row.colour_hex) || NEUTRAL_DOT;
    const props = m.feature.properties || {};
    const prov = provinceName(props.province_code);
    const text = el("span", "seg-item-text");
    text.append(el("strong", null, "กม. ที่ " + (m.alongM / 1000).toFixed(1) + " · " + routeLabel(props.route_code)));
    text.append(el("span", null, bandTitle(row) + (prov ? " · " + prov : "")));
    btn.append(dot, text);
    btn.addEventListener("click", () => selectSegment(m.id, true));
    li.append(btn);
    ul.append(li);
  }
  det.append(ul);
  body.append(det);

  if (Array.isArray(f.caveats) && f.caveats.length) {
    const cav = el("details");
    cav.append(el("summary", null, "ข้อจำกัดจากระบบผลประเมิน"));
    const list = el("ul", "caveats");
    for (const c of f.caveats) list.append(el("li", null, String(c)));
    cav.append(list);
    body.append(cav);
  }
}

// ---------------------------------------------------------------- selection, prediction & history

function matchById(id) {
  return state.route && state.route.matches ? state.route.matches.find((m) => m.id === id) || null : null;
}

function clearSelection() {
  state.detailGen += 1;
  if (state.detailController) state.detailController.abort();
  state.detailController = null;
  state.selectedId = null;
  if (map.selectedLayer) { map.selectedLayer.remove(); map.selectedLayer = null; }
  $("detailSection").hidden = true;
}

function selectSegment(id, panMap) {
  const f = state.forecast;
  const m = matchById(id);
  if (f.status !== "done" || !m || !f.results.has(id)) return;
  const previous = state.selectedId;
  clearSelection();
  state.selectedId = id;
  for (const [otherId, marker] of map.dots) {
    if (otherId === id || otherId === previous) {
      const row = f.results.get(otherId);
      marker.setIcon(dotIcon(validHex(row.colour_hex), otherId === id));
    }
  }
  if (map.leaflet) {
    try {
      map.selectedLayer = L.geoJSON(m.feature, { style: () => ({ ...SELECTED_SEGMENT_STYLE }), interactive: false }).addTo(map.leaflet);
    } catch (_) { map.selectedLayer = null; }
    if (panMap) map.leaflet.setView([m.lat, m.lon], Math.max(map.leaflet.getZoom(), 12));
  }
  renderForecastSelectionMarks();
  const row = f.results.get(id);
  $("detailSection").hidden = false;
  renderDetailMeta();
  showTab("prediction");
  renderPrediction(f.ctx, row, f.caveats);
  loadHistory();
  if (isMobile()) setSheet(true);
  $("detailSection").scrollIntoView({ block: "start", behavior: "smooth" });
}

function renderForecastSelectionMarks() {
  const items = document.querySelectorAll(".seg-item");
  const matches = state.route && state.route.matches ? state.route.matches : [];
  items.forEach((btn, i) => {
    const on = matches[i] && matches[i].id === state.selectedId;
    btn.classList.toggle("is-selected", on);
    if (on) btn.setAttribute("aria-current", "true"); else btn.removeAttribute("aria-current");
  });
}

function closeDetail() {
  const previous = state.selectedId;
  clearSelection();
  const f = state.forecast;
  if (previous && map.dots.has(previous) && f.status === "done") {
    map.dots.get(previous).setIcon(dotIcon(validHex(f.results.get(previous).colour_hex), false));
  }
  renderForecastSelectionMarks();
}

function renderDetailMeta() {
  const box = $("detailMeta");
  box.replaceChildren();
  const m = matchById(state.selectedId);
  if (!m) return;
  const props = m.feature.properties || {};
  box.append(el("div", "seg-title", routeLabel(props.route_code)));
  const meta = [];
  const prov = provinceName(props.province_code);
  if (prov) meta.push("จังหวัด" + prov);
  if (isNum(props.segment_km)) meta.push("ช่วงยาว " + props.segment_km.toFixed(1) + " กม.");
  meta.push("ประมาณ กม. ที่ " + (m.alongM / 1000).toFixed(1) + " ของเส้นทาง");
  box.append(el("div", "seg-meta", meta.join(" · ")));
  box.append(el("div", "seg-meta seg-note", "จับคู่กับเส้นทางโดยประมาณ (" + Math.round(m.share * 100) + "% ของจุดตัวอย่างอยู่ภายใน 50 ม. จากเส้นทาง)"));
  const det = el("details");
  det.append(el("summary", null, "รหัสอ้างอิงช่วงถนน"), el("div", "mono", m.id));
  box.append(det);
}

function horizonText(ctx) {
  return ctx.unit === "6h" ? fmtDate(ctx.date) + " ช่วง " + (BLOCK_LABEL[ctx.block] || ctx.block) : "ตลอดวัน " + fmtDate(ctx.date);
}

function stat(label, value) {
  const box = el("div", "stat");
  box.append(el("div", "stat-label", label), el("div", "stat-value", value));
  return box;
}

function kvList(pairs) {
  const dl = el("dl", "kv");
  for (const [k, v] of pairs) {
    if (v === undefined || v === null || v === "") continue;
    dl.append(el("dt", null, k), el("dd", null, String(v)));
  }
  return dl;
}

function renderPrediction(ctx, r, caveats) {
  const panel = $("panelPrediction");
  panel.replaceChildren();
  const hero = el("div", "result-hero");
  hero.append(el("div", "result-label", "จำนวนรายการอุบัติเหตุที่คาดว่าจะถูกบันทึกบนช่วงถนนนี้"));
  hero.append(el("div", "result-value", fmtNum(r.expected_recorded_count)));
  hero.append(el("div", "result-unit", "รายการ · " + horizonText(ctx)));
  panel.append(hero);

  const chips = el("div", "chips");
  if (r.research_scenario === true) chips.append(el("span", "chip chip-accent", "ฉากทัศน์วิจัย · ไม่มีข้อมูลจริงให้เทียบ"));
  else if (r.research_scenario === false) chips.append(el("span", "chip chip-teal", "ช่วงที่เคยใช้ตรวจสอบย้อนหลัง"));
  chips.append(el("span", "chip", ctx.unit === "6h" ? "ราย 6 ชั่วโมง" : "รายวัน"));
  panel.append(chips);

  const band = el("div", "band");
  const sw = el("span", "band-swatch");
  const hex = validHex(r.colour_hex);
  if (hex) sw.style.background = hex;
  const th = BAND_TH[r.colour] || null;
  band.append(sw, el("span", "band-title", th ? th.title : "ระดับสี: " + String(r.colour ?? "ไม่ระบุ")));
  if (th) band.append(el("span", "band-text", th.text));
  if (r.colour_text) band.append(el("span", "band-quote", "คำอธิบายจากระบบ: " + r.colour_text));
  panel.append(band);

  const grid = el("div", "stat-grid");
  grid.append(stat("ต่อกิโลเมตร", fmtNum(r.density_per_km) + " รายการ/กม."));
  grid.append(stat("ความยาวช่วงถนน", isNum(r.segment_km) ? r.segment_km.toFixed(1) + " กม." : "ไม่มีข้อมูล"));
  panel.append(grid);

  panel.append(el("p", "explain",
    "ค่านี้คือค่าประเมินเชิงสถิติของจำนวนรายการอุบัติเหตุที่ถูกบันทึกและเชื่อมกับช่วงถนนนี้ในช่วงเวลาที่เลือก "
    + "ไม่ใช่โอกาสที่คุณหรือรถคันใดจะเกิดอุบัติเหตุ และไม่ได้รวมสภาพอากาศ การจราจร หรือเทศกาลแบบปัจจุบัน"));

  const det = el("details");
  det.append(el("summary", null, "ที่มาของผลลัพธ์และข้อจำกัด"));
  const sa = r.source_availability && typeof r.source_availability === "object"
    ? Object.entries(r.source_availability).map(([k, v]) => k + ": " + v).join(" · ") : null;
  det.append(kvList([
    ["ช่วงเวลาที่ประเมิน", r.horizon],
    ["เวลาออกค่าประเมิน", r.issue_time_local],
    ["รุ่นแบบจำลอง", r.model_version],
    ["ส่วนของแบบจำลองที่ใช้", r.component_used],
    ["เหตุผลการเลือก", r.routing_reason],
    ["ช่วงข้อมูล", r.data_period],
    ["แหล่งข้อมูลประกอบ", sa],
  ]));
  if (Array.isArray(caveats) && caveats.length) {
    const ul = el("ul", "caveats");
    for (const c of caveats) ul.append(el("li", null, String(c)));
    det.append(ul);
  }
  panel.append(det);
}

async function loadHistory() {
  const f = state.forecast;
  const id = state.selectedId;
  if (!id || f.status !== "done") return;
  if (state.detailController) state.detailController.abort();
  const gen = ++state.detailGen;
  const controller = new AbortController();
  state.detailController = controller;
  const ctx = f.ctx;
  $("panelHistory").replaceChildren(loadingRow("กำลังโหลดประวัติที่บันทึก…"));
  const body = { segment_id: id, target_date: ctx.date, unit: ctx.unit };
  if (ctx.block) body.time_block = ctx.block;
  try {
    const json = await apiFetch("/api/v1/spatial/history", { method: "POST", body, controller });
    if (gen !== state.detailGen || state.selectedId !== id) return;
    state.detailController = null;
    renderHistory(json);
  } catch (failure) {
    if (gen !== state.detailGen || failure.kind === "aborted") return;
    state.detailController = null;
    if (isServiceDown(failure) && state.ready === "ready") setReady("down");
    $("panelHistory").replaceChildren(apiErrorBox(failure, loadHistory));
  }
}

function barList(title, entries, wide) {
  const wrap = el("div", "bars");
  wrap.append(el("h3", null, title));
  const max = Math.max(1, ...entries.map(([, v]) => (isNum(v) ? v : 0)));
  for (const [label, v] of entries) {
    const row = el("div", "bar-row" + (wide ? " bar-row-wide" : ""));
    const track = el("div", "bar-track");
    const fill = el("div", "bar-fill");
    fill.style.width = isNum(v) ? ((100 * v) / max).toFixed(1) + "%" : "0";
    track.append(fill);
    row.append(el("span", "bar-label", label), track, el("span", "bar-count", isNum(v) ? fmtInt(v) : "—"));
    row.title = label;
    wrap.append(row);
  }
  return wrap;
}

function renderHistory(json) {
  const panel = $("panelHistory");
  panel.replaceChildren();
  const h = json && json.history && typeof json.history === "object" ? json.history : null;
  if (!h) {
    panel.append(apiErrorBox(new RequestFailure("invalid"), loadHistory));
    return;
  }
  const win = h.history_window || {};
  const n = h.n_selected_records;

  const hero = el("div", "stat-grid");
  hero.append(stat("รายการที่บันทึกไว้", isNum(n) ? fmtInt(n) + " รายการ" : "ไม่มีข้อมูล"));
  hero.append(stat("นับถึงวันที่", fmtDate(h.history_cutoff_local)));
  panel.append(hero);

  panel.append(el("p", "explain",
    "นับรายการที่บันทึกและเชื่อมกับช่วงถนนนี้ ตั้งแต่ " + fmtDate(win.window_start_local_exclusive)
    + " ถึง " + fmtDate(h.history_cutoff_local) + " (ก่อนวันที่ประเมินอย่างน้อย " + (isNum(h.latency_days) ? h.latency_days : "—") + " วัน)"));

  if (n === 0) panel.append(el("div", "note-box", "ไม่พบรายการบันทึกในช่วงนี้ — ไม่ได้หมายความว่าถนนช่วงนี้ปลอดภัย"));

  const ps = json.period_status || {};
  const gaps = [];
  if (ps.unsupported_after) gaps.push("ช่วงหลัง ธ.ค. 2025 ยังไม่อยู่ในฐานข้อมูล จึงไม่ได้นับ (ไม่ทราบ ไม่ใช่ศูนย์)");
  if (ps.unsupported_before) gaps.push("ช่วงก่อน ม.ค. 2021 อยู่นอกฐานข้อมูล จึงไม่ได้นับ");
  if (gaps.length) panel.append(el("div", "note-box", gaps.join(" · ")));

  if (h.counts_by_year && typeof h.counts_by_year === "object" && Object.keys(h.counts_by_year).length) {
    const years = Object.entries(h.counts_by_year).sort(([a], [b]) => a.localeCompare(b));
    panel.append(barList("รายปี (ค.ศ.)", years));
  }
  if (h.counts_by_time_block && typeof h.counts_by_time_block === "object" && Object.keys(h.counts_by_time_block).length) {
    const blocks = Object.entries(h.counts_by_time_block).sort(([a], [b]) => a.localeCompare(b));
    panel.append(barList("ตามช่วงเวลาของวัน", blocks.map(([b, v]) => [BLOCK_LABEL[b] || b, v])));
  }

  const cats = h.categories && typeof h.categories === "object" ? h.categories : {};
  for (const key of ["accident_type", "presumed_cause", "weather"]) {
    const c = cats[key];
    if (!c || !Array.isArray(c.top_values) || c.top_values.length === 0) continue;
    const entries = c.top_values.map((t) => [String(t.value), t.records]);
    if (isNum(c.other_known_records) && c.other_known_records > 0) entries.push(["อื่น ๆ", c.other_known_records]);
    if (isNum(c.unknown_records) && c.unknown_records > 0) entries.push(["ไม่ระบุ", c.unknown_records]);
    panel.append(barList(CATEGORY_TH[key], entries, true));
  }

  const det = el("details");
  det.append(el("summary", null, "หมายเหตุเกี่ยวกับประวัติ"));
  det.append(el("p", null, "ข้อมูลเป็นรายการที่ถูกบันทึกและคัดเลือกเพื่อเชื่อมกับช่วงถนนนี้ ไม่ใช่จำนวนอุบัติเหตุทั้งหมด สาเหตุและสภาพอากาศเป็นข้อมูลที่บันทึกไว้ในอดีต ไม่ใช่การพิสูจน์สาเหตุ และไม่ใช่สภาพอากาศปัจจุบัน"));
  if (Array.isArray(h.notes)) {
    const ul = el("ul", "caveats");
    for (const note of h.notes) ul.append(el("li", null, String(note)));
    det.append(ul);
  }
  if (ps.note) det.append(el("p", null, String(ps.note)));
  panel.append(det);
}

// ---------------------------------------------------------------- tabs & sheet

function showTab(which) {
  const pred = which === "prediction";
  $("tabPrediction").setAttribute("aria-selected", String(pred));
  $("tabHistory").setAttribute("aria-selected", String(!pred));
  $("tabPrediction").tabIndex = pred ? 0 : -1;
  $("tabHistory").tabIndex = pred ? -1 : 0;
  $("panelPrediction").hidden = !pred;
  $("panelHistory").hidden = pred;
}

function onTabKey(e) {
  if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;
  const toHistory = e.currentTarget.id === "tabPrediction";
  showTab(toHistory ? "history" : "prediction");
  $(toHistory ? "tabHistory" : "tabPrediction").focus();
  e.preventDefault();
}

function setSheet(open) {
  state.sheetOpen = open;
  $("sheet").classList.toggle("is-collapsed", !open);
  $("sheetToggle").setAttribute("aria-expanded", String(open));
}

function updateSheetSummary() {
  const r = state.route;
  let text = "ค้นหาต้นทางและปลายทาง";
  if (r && r.status === "loading") text = "กำลังคำนวณเส้นทาง…";
  else if (r && r.status === "error") text = "คำนวณเส้นทางไม่สำเร็จ";
  else if (r && r.status === "ready") {
    text = fmtKm(r.distance) + " · " + fmtDuration(r.duration);
    const f = state.forecast;
    if (f.status === "done") text += " · ผลประเมิน " + fmtInt(r.matches.length) + " ช่วง";
    else if (f.status === "none") text += " · ยังไม่มีข้อมูลประเมิน";
  }
  $("sheetSummary").textContent = text;
}

// ---------------------------------------------------------------- controls

function refreshControls() {
  const both = !!state.fields.origin.place && !!state.fields.destination.place;
  const routing = !!state.route && state.route.status === "loading";
  $("btnRoute").disabled = !both || routing;
  $("btnRoute").textContent = routing ? "กำลังคำนวณเส้นทาง…" : "ดูเส้นทาง";
  let hint = "";
  if (!state.fields.origin.place && !state.fields.destination.place) hint = "ค้นหาแล้วเลือกต้นทางและปลายทางจากรายการ หรือเลือกจุดบนแผนที่";
  else if (!state.fields.origin.place) hint = "ยังไม่ได้เลือกต้นทาง";
  else if (!state.fields.destination.place) hint = "ยังไม่ได้เลือกปลายทาง";
  $("routeHint").textContent = hint;
  $("routeHint").hidden = hint === "";
  const canPick = !!map.leaflet && state.boundaryStatus === "ready";
  for (const which of WHICH) {
    const btn = $(which + "Pick");
    btn.disabled = !canPick;
    btn.setAttribute("aria-pressed", String(state.picking === which));
  }
}

// ---------------------------------------------------------------- wiring

for (const which of WHICH) {
  $(which + "Form").addEventListener("submit", (e) => { e.preventDefault(); searchPlaces(which); });
  $(which + "Input").addEventListener("input", () => onFieldInput(which));
  $(which + "Pick").addEventListener("click", () => (state.picking === which ? cancelPicking() : startPicking(which)));
}
$("btnSwap").addEventListener("click", swapEndpoints);
$("btnRoute").addEventListener("click", requestRoute);
$("btnExample").addEventListener("click", fillExample);
$("btnCancelPick").addEventListener("click", cancelPicking);
$("btnRetry").addEventListener("click", retryService);
$("btnResetView").addEventListener("click", fitThailand);
$("btnCloseDetail").addEventListener("click", closeDetail);
$("tripDate").addEventListener("input", onTimeChanged);
$("tripTime").addEventListener("input", onTimeChanged);
for (const input of document.querySelectorAll('input[name="unit"]')) input.addEventListener("change", onTimeChanged);
$("tabPrediction").addEventListener("click", () => showTab("prediction"));
$("tabHistory").addEventListener("click", () => showTab("history"));
$("tabPrediction").addEventListener("keydown", onTabKey);
$("tabHistory").addEventListener("keydown", onTabKey);
$("sheetToggle").addEventListener("click", () => setSheet(!state.sheetOpen));
document.addEventListener("keydown", (e) => { if (e.key === "Escape" && state.picking) cancelPicking(); });

(function initInputs() {
  let date = todayIso();
  if (date < DATE_MIN) date = DATE_MIN;
  if (date > DATE_MAX) date = DATE_MAX;
  $("tripDate").value = date;
  const now = new Date();
  $("tripTime").value = pad2(now.getHours()) + ":" + pad2(now.getMinutes());
})();

initMap();
loadBoundary();
for (const which of WHICH) renderField(which);
updateTimeNote();
updateSheetSummary();
refreshControls();
checkReady();
