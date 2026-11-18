"use strict";

// RoadAware map workspace. Every value shown comes from the local research API; untrusted text
// is always rendered with textContent / DOM nodes (never innerHTML).

const DEFAULT_API_BASE = "http://127.0.0.1:8000";
const FETCH_TIMEOUT_MS = 30000;
const PAGE_SIZE = 100;
const LAST_OBSERVED_DATE = "2025-12-31";
// Backend geometry limits (backend_api_v3.json limits.geometry).
const ENVELOPE = { west: 97.0, south: 5.0, east: 106.0, north: 21.0 };
const MAX_SPAN_DEG = 20.0;
const THAILAND_BOUNDS = [[5.5, 97.3], [20.5, 105.7]];
const BANGKOK_BBOX = { west: 100.4, south: 13.6, east: 100.8, north: 14.0 };
const PROVINCE_HALF_SPAN = 0.3;

const BLOCK_LABEL = { "00-06": "00:00–06:00 น.", "06-12": "06:00–12:00 น.", "12-18": "12:00–18:00 น.", "18-24": "18:00–24:00 น." };
const BAND_TH = {
  base: { title: "ต่ำกว่าค่ากลาง (เชิงเปรียบเทียบ)", text: "ต่ำกว่าค่ามัธยฐานของค่าอ้างอิง — ไม่ได้หมายความว่าปลอดภัย" },
  yellow: { title: "สูงกว่าค่ากลาง (เชิงเปรียบเทียบ)", text: "อยู่ช่วงเปอร์เซ็นไทล์ที่ 50–80 ของค่าอ้างอิง" },
  orange: { title: "สูง (เชิงเปรียบเทียบ)", text: "อยู่ช่วงเปอร์เซ็นไทล์ที่ 80–95 ของค่าอ้างอิง" },
  red: { title: "สูงที่สุด (เชิงเปรียบเทียบ)", text: "อยู่ใน 5% บนของค่าอ้างอิง — เป็นการจัดอันดับ ไม่ใช่ความเสี่ยงสัมบูรณ์" },
  grey: { title: "ไม่มีข้อมูล", text: "ไม่สามารถให้ค่าคาดการณ์สำหรับช่วงถนนหรือช่วงเวลานี้" },
};
const CATEGORY_TH = { accident_type: "ลักษณะเหตุที่บันทึก", presumed_cause: "สาเหตุที่สันนิษฐานในบันทึก", weather: "สภาพอากาศที่บันทึก" };

const NEUTRAL_STYLE = { color: "#3f5566", weight: 3, opacity: 0.75 };
const SELECTED_STYLE = { color: "#0a4f53", weight: 7, opacity: 1 };

const $ = (id) => document.getElementById(id);

const API_BASE = resolveApiBase();

const state = {
  ready: "checking",          // "checking" | "ready" | "down"
  readyController: null,
  provinces: new Map(),       // normalised province_code -> province
  // area / segments
  areaGen: 0,
  area: null,                 // { bbox, title, sub }
  segController: null,
  segBusy: false,
  areaFailure: null,          // RequestFailure of the last page request for the current area
  features: new Map(),        // segment_id -> feature
  order: [],
  nextCursor: null,
  totalMatched: null,
  // selection / results
  selectedId: null,
  resultGen: 0,
  predController: null,
  predBusy: false,
  prediction: null,           // { ctx, row } — current only
};

const map = { leaflet: null, roads: null, area: null, marker: null, layers: new Map(), tilesLoaded: 0, tileErrors: 0 };

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
  return DEFAULT_API_BASE;
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

function fmtCoord(v) {
  return v.toFixed(4);
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

function clampBbox(b) {
  let west = Math.max(ENVELOPE.west, b.west);
  let east = Math.min(ENVELOPE.east, b.east);
  let south = Math.max(ENVELOPE.south, b.south);
  let north = Math.min(ENVELOPE.north, b.north);
  if (east - west > MAX_SPAN_DEG) { const c = (west + east) / 2; west = c - MAX_SPAN_DEG / 2; east = c + MAX_SPAN_DEG / 2; }
  if (north - south > MAX_SPAN_DEG) { const c = (south + north) / 2; south = c - MAX_SPAN_DEG / 2; north = c + MAX_SPAN_DEG / 2; }
  if (!(east > west) || !(north > south)) return null;
  const r = (x) => Math.round(x * 10000) / 10000;
  return { west: r(west), south: r(south), east: r(east), north: r(north) };
}

function bboxParam(b) {
  return [b.west, b.south, b.east, b.north].join(",");
}

function insideEnvelope(lat, lon) {
  return lon >= ENVELOPE.west && lon <= ENVELOPE.east && lat >= ENVELOPE.south && lat <= ENVELOPE.north;
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

// One real HTTP request. Resolves with parsed JSON for 2xx; otherwise throws RequestFailure.
async function apiFetch(path, { method = "GET", body, controller } = {}) {
  const ctrl = controller || new AbortController();
  let timedOut = false;
  const timer = setTimeout(() => { timedOut = true; ctrl.abort(); }, FETCH_TIMEOUT_MS);
  const init = { method, signal: ctrl.signal, cache: "no-store" };
  if (body !== undefined) {
    init.headers = { "Content-Type": "application/json" };
    init.body = JSON.stringify(body);
  }
  let response;
  let text;
  try {
    response = await fetch(API_BASE + path, init);
    text = await response.text();
  } catch (err) {
    if (err && err.name === "AbortError") throw new RequestFailure(timedOut ? "timeout" : "aborted");
    throw new RequestFailure("network");
  } finally {
    clearTimeout(timer);
  }
  let json = null;
  try { json = JSON.parse(text); } catch (_) { json = null; }
  if (response.status >= 200 && response.status < 300) {
    if (json === null || typeof json !== "object") throw new RequestFailure("invalid", response.status, null);
    return json;
  }
  throw new RequestFailure("http", response.status, json);
}

// True when the failure means the backend itself is unavailable (not a problem with this request).
function isServiceDown(failure) {
  return failure.kind === "network" || failure.kind === "timeout" || (failure.kind === "http" && failure.status === 503);
}

// Friendly Thai description of a failure; technical code/message only goes into a collapsed details.
function describeFailure(failure) {
  const err = failure.body && failure.body.error ? failure.body.error : null;
  if (failure.kind === "timeout") return { title: "บริการตอบช้าเกินไป", text: "ไม่ได้รับคำตอบภายใน " + FETCH_TIMEOUT_MS / 1000 + " วินาที โปรดลองอีกครั้ง", err };
  if (failure.kind === "network") return { title: "เชื่อมต่อบริการข้อมูลไม่ได้", text: "บริการอาจยังไม่เปิดหรือกำลังเริ่มทำงาน โปรดลองอีกครั้งในอีกสักครู่", err };
  if (failure.kind === "invalid") return { title: "ได้รับข้อมูลที่อ่านไม่ได้", text: "บริการตอบกลับในรูปแบบที่ไม่คาดไว้ จึงไม่แสดงผล", err };
  const s = failure.status;
  if (s === 503) return { title: "บริการข้อมูลไม่พร้อมชั่วคราว", text: "โปรดลองอีกครั้งในภายหลัง", err };
  if (s === 404) return { title: "ไม่มีข้อมูลสำหรับรายการนี้", text: "ช่วงถนนนี้อยู่นอกขอบเขตข้อมูลที่รองรับ (ไม่มีข้อมูล ไม่ใช่ศูนย์)", err };
  if (s === 400) return { title: "คำขอไม่ถูกต้อง", text: "โปรดตรวจสอบวันที่และตัวเลือกอีกครั้ง (รองรับ 1 ม.ค. 2024 – 31 ธ.ค. 2027)", err };
  return { title: "เกิดข้อผิดพลาดจากบริการ", text: "ไม่มีผลลัพธ์บางส่วนแสดง โปรดลองอีกครั้ง", err };
}

function errorBox(failure, onRetry) {
  const info = describeFailure(failure);
  const box = el("div", "error-box");
  box.setAttribute("role", "alert");
  box.append(el("strong", null, info.title), el("span", null, info.text));
  if (info.err && (info.err.code || info.err.message)) {
    const det = el("details");
    det.append(el("summary", null, "รายละเอียดทางเทคนิค"));
    if (failure.status) det.append(el("div", null, "HTTP " + failure.status));
    if (info.err.code) det.append(el("div", "mono", info.err.code));
    if (info.err.message) det.append(el("div", null, info.err.message));
    box.append(det);
  }
  if (onRetry) {
    const btn = el("button", "btn btn-ghost btn-small", "ลองอีกครั้ง");
    btn.type = "button";
    btn.addEventListener("click", onRetry);
    box.append(btn);
  }
  return box;
}

function loadingRow(text) {
  const row = el("div", "loading");
  row.append(el("span", "spinner"), el("span", null, text));
  return row;
}

// ---------------------------------------------------------------- readiness

async function checkReady() {
  if (state.readyController) state.readyController.abort();
  const controller = new AbortController();
  state.readyController = controller;
  setReady("checking");
  let ok = false;
  try {
    const json = await apiFetch("/ready", { controller });
    ok = json.research_backend_ready === true;
  } catch (failure) {
    // 503 bodies carry research_backend_ready false; any failure (incl. timeout) means not ready.
    ok = false;
  }
  if (state.readyController !== controller) return; // superseded by a newer check
  state.readyController = null;
  setReady(ok ? "ready" : "down");
  if (ok) loadProvinces();
}

function setReady(next) {
  const wasReady = state.ready === "ready";
  state.ready = next;
  const dot = $("statusDot");
  dot.className = "status-dot " + (next === "ready" ? "is-ready" : next === "down" ? "is-down" : "is-checking");
  $("statusText").textContent = next === "ready" ? "บริการข้อมูลพร้อม" : next === "down" ? "บริการข้อมูลไม่พร้อม" : "กำลังเชื่อมต่อ…";
  $("btnRetry").hidden = next !== "down";
  const banner = $("serviceBanner");
  if (next === "down") {
    banner.textContent = "ขณะนี้เชื่อมต่อบริการข้อมูลไม่ได้ ยังเลื่อนดูแผนที่ได้ แต่การค้นหาถนนและการคาดการณ์จะใช้ได้เมื่อบริการกลับมา กด “ลองอีกครั้ง” ที่มุมขวาบน";
    banner.hidden = false;
  } else {
    banner.hidden = true;
  }
  if (wasReady && next !== "ready") {
    // Readiness lost: nothing previously shown may be presented as current.
    clearArea();
  }
  refreshControls();
}

function serviceLost() {
  if (state.ready === "ready") setReady("down");
}

async function loadProvinces() {
  if (state.provinces.size > 0) return;
  try {
    const json = await apiFetch("/api/v1/provinces");
    const list = Array.isArray(json.provinces) ? json.provinces : [];
    const sorted = list.filter((p) => p && typeof p.name_th === "string").sort((a, b) => a.name_th.localeCompare(b.name_th, "th"));
    const select = $("provinceSelect");
    select.replaceChildren(new Option("— เลือกจังหวัด —", ""));
    for (const p of sorted) {
      const key = provinceKey(p.province_code);
      if (key) state.provinces.set(key, p);
      const pt = p.representative_point || {};
      if (isNum(pt.lat) && isNum(pt.lon) && key) select.append(new Option(p.name_th, key));
    }
    // Labels may now be resolvable for already-listed roads.
    rebuildSegmentOptions();
    renderSegmentCard();
  } catch (_) {
    // Province names are optional context; the map and presets keep working without them.
  }
  refreshControls();
}

// ---------------------------------------------------------------- controls

function currentInputs() {
  const unit = document.querySelector('input[name="unit"]:checked').value;
  const block = unit === "6h" ? document.querySelector('input[name="block"]:checked').value : null;
  return { segmentId: state.selectedId, date: $("targetDate").value, unit, block };
}

function validDate(d) {
  return /^\d{4}-\d{2}-\d{2}$/.test(d) && d >= "2024-01-01" && d <= "2027-12-31";
}

function refreshControls() {
  const ready = state.ready === "ready";
  const locked = state.predBusy; // inputs that affect a running prediction are frozen
  const areaEnabled = ready && !locked;
  $("btnBangkok").disabled = !areaEnabled;
  $("btnViewRoads").disabled = !areaEnabled || !map.leaflet;
  $("provinceSelect").disabled = !areaEnabled || state.provinces.size === 0;
  $("radiusSelect").disabled = locked;
  $("segmentSelect").disabled = !ready || locked || state.segBusy || state.order.length === 0;
  $("btnMore").hidden = !state.nextCursor || !ready;
  $("btnMore").disabled = locked || state.segBusy;
  $("targetDate").disabled = locked;
  for (const input of document.querySelectorAll('input[name="unit"], input[name="block"]')) input.disabled = locked;
  const unit = document.querySelector('input[name="unit"]:checked').value;
  $("blockGroup").hidden = unit !== "6h";

  const inputs = currentInputs();
  const canPredict = ready && !locked && !state.segBusy && !!inputs.segmentId && validDate(inputs.date);
  $("btnPredict").disabled = !canPredict;
  $("btnPredict").textContent = state.predBusy ? "กำลังคาดการณ์…" : "ดูการคาดการณ์";
  let hint = "";
  if (!ready) hint = state.ready === "checking" ? "กำลังเชื่อมต่อบริการข้อมูล…" : "ใช้งานได้เมื่อบริการข้อมูลพร้อม";
  else if (!inputs.segmentId) hint = "เลือกช่วงถนนก่อน แล้วกดดูการคาดการณ์";
  else if (!validDate(inputs.date)) hint = "เลือกวันที่ระหว่าง 1 ม.ค. 2024 ถึง 31 ธ.ค. 2027";
  $("predictHint").textContent = hint;
  $("predictHint").hidden = hint === "";

  $("mapHint").textContent = !ready
    ? "เลื่อนดูแผนที่ได้ — การค้นหาถนนจะใช้ได้เมื่อบริการข้อมูลพร้อม"
    : locked ? "กำลังคาดการณ์… รอสักครู่ก่อนเลือกพื้นที่ใหม่"
      : "คลิกบนแผนที่เพื่อค้นหาช่วงถนนที่มีข้อมูลรอบจุดนั้น";
}

function updateDateNote() {
  const d = $("targetDate").value;
  const note = $("dateNote");
  if (!validDate(d)) note.textContent = "รองรับวันที่ 1 ม.ค. 2024 ถึง 31 ธ.ค. 2027";
  else if (d > LAST_OBSERVED_DATE) note.textContent = fmtDate(d) + " · ฉากทัศน์วิจัย ยังไม่มีข้อมูลจริงให้เทียบ";
  else note.textContent = fmtDate(d) + " · ช่วงที่เคยใช้ตรวจสอบแบบจำลองย้อนหลัง";
}

// ---------------------------------------------------------------- invalidation

// Any change to segment / date / unit / block: drop results and cancel the running prediction.
function invalidateResult() {
  state.resultGen += 1;
  if (state.predController) state.predController.abort();
  state.predController = null;
  state.predBusy = false;
  state.prediction = null;
  renderPredictionEmpty();
  renderHistoryEmpty();
  restyleRoads();
  refreshControls();
}

// Any change of area: cancel segment loading, drop roads, selection and results.
function clearArea() {
  state.areaGen += 1;
  if (state.segController) state.segController.abort();
  state.segController = null;
  state.segBusy = false;
  state.area = null;
  state.areaFailure = null;
  state.features.clear();
  state.order = [];
  state.nextCursor = null;
  state.totalMatched = null;
  state.selectedId = null;
  if (map.roads) map.roads.clearLayers();
  map.layers.clear();
  if (map.area) { map.area.remove(); map.area = null; }
  if (map.marker) { map.marker.remove(); map.marker = null; }
  rebuildSegmentOptions();
  renderSegmentCard();
  renderAreaStatus();
  invalidateResult();
}

// ---------------------------------------------------------------- area & segments

function selectArea(bbox, title, sub, options = {}) {
  if (state.ready !== "ready" || state.predBusy) return;
  const clamped = clampBbox(bbox);
  clearArea();
  if (!clamped) {
    state.area = { bbox: null, title, sub: "พื้นที่นี้อยู่นอกขอบเขตที่ระบบรองรับ" };
    renderAreaStatus();
    return;
  }
  state.area = { bbox: clamped, title, sub };
  if (map.leaflet) {
    map.area = L.rectangle([[clamped.south, clamped.west], [clamped.north, clamped.east]], {
      color: "#d9702a", weight: 2, dashArray: "6 6", fill: true, fillOpacity: 0.04, interactive: false,
    }).addTo(map.leaflet);
    if (options.point) {
      map.marker = L.circleMarker(options.point, { radius: 6, color: "#fff", weight: 2, fillColor: "#d9702a", fillOpacity: 1, interactive: false }).addTo(map.leaflet);
    }
    if (options.fit) map.leaflet.fitBounds(map.area.getBounds(), { padding: [24, 24] });
  }
  loadSegmentsPage(false);
}

async function loadSegmentsPage(more) {
  if (state.ready !== "ready" || !state.area || !state.area.bbox) return;
  if (more && !state.nextCursor) return;
  if (state.segController) state.segController.abort();
  const gen = state.areaGen;
  const controller = new AbortController();
  state.segController = controller;
  state.segBusy = true;
  const params = new URLSearchParams({ bbox: bboxParam(state.area.bbox), limit: String(PAGE_SIZE) });
  if (more) params.set("cursor", state.nextCursor);
  renderAreaStatus();
  refreshControls();
  let json = null;
  let failure = null;
  try {
    json = await apiFetch("/api/v1/segments?" + params.toString(), { controller });
  } catch (f) {
    failure = f;
  }
  // Ignore anything that belongs to an area the user already left or a superseded page request.
  if (gen !== state.areaGen || state.segController !== controller) return;
  state.segController = null;
  state.segBusy = false;
  if (failure) {
    if (isServiceDown(failure)) { serviceLost(); if (state.ready !== "ready") return; }
    state.areaFailure = failure;
    renderAreaStatus();
    refreshControls();
    return;
  }
  state.areaFailure = null;
  const features = Array.isArray(json.features) ? json.features : null;
  const page = json.page && typeof json.page === "object" ? json.page : null;
  if (!features || !page) {
    state.areaFailure = new RequestFailure("invalid");
    renderAreaStatus();
    refreshControls();
    return;
  }
  for (const f of features) {
    const id = f && f.properties ? String(f.properties.segment_id ?? f.id) : null;
    if (!id || state.features.has(id)) continue;
    state.features.set(id, f);
    state.order.push(id);
    addRoadLayer(id, f);
  }
  state.nextCursor = page.next_cursor ?? null;
  state.totalMatched = isNum(page.total_matched) ? page.total_matched : null;
  rebuildSegmentOptions();
  renderAreaStatus();
  refreshControls();
}

function renderAreaStatus() {
  const box = $("areaStatus");
  box.replaceChildren();
  if (!state.area) {
    box.append(el("p", "empty-note", "ยังไม่ได้เลือกพื้นที่"));
    renderPager();
    return;
  }
  box.append(el("p", "area-title", state.area.title));
  if (state.area.sub) box.append(el("p", "area-sub", state.area.sub));
  if (state.segBusy) {
    box.append(loadingRow("กำลังค้นหาช่วงถนนที่มีข้อมูล…"));
  } else if (state.areaFailure) {
    box.append(errorBox(state.areaFailure, () => loadSegmentsPage(state.order.length > 0)));
  } else if (state.area.bbox && state.order.length === 0 && state.totalMatched !== null) {
    const empty = el("div", "empty");
    empty.append(el("strong", null, "ไม่มีช่วงถนนที่รองรับในพื้นที่นี้"));
    empty.append(el("span", null, "ระบบมีข้อมูลเฉพาะช่วงถนนทางหลวงที่ผ่านเกณฑ์ ลองคลิกจุดอื่น ขยายระยะค้นหา หรือเลือกจังหวัด (ไม่มีข้อมูล ไม่ได้แปลว่าศูนย์)"));
    box.append(empty);
  }
  renderPager();
}

function renderPager() {
  const info = $("pageInfo");
  if (!state.area || state.order.length === 0 || state.totalMatched === null) {
    info.textContent = "";
    return;
  }
  info.textContent = "แสดง " + fmtInt(state.order.length) + " จาก " + fmtInt(state.totalMatched) + " ช่วงถนนในพื้นที่นี้";
}

function segmentLabel(id) {
  const props = state.features.get(id).properties || {};
  const parts = [routeLabel(props.route_code)];
  const prov = provinceName(props.province_code);
  if (prov) parts.push(prov);
  // Ordinal among loaded segments of the same route (list is ordered by segment_id).
  let n = 0;
  for (const other of state.order) {
    if ((state.features.get(other).properties || {}).route_code === props.route_code) n += 1;
    if (other === id) break;
  }
  parts.push("ช่วงที่ " + n);
  return parts.join(" · ");
}

function rebuildSegmentOptions() {
  const select = $("segmentSelect");
  select.replaceChildren();
  if (state.order.length === 0) {
    select.append(new Option(state.area ? "— ไม่มีช่วงถนนให้เลือก —" : "— เลือกพื้นที่ก่อน —", ""));
  } else {
    select.append(new Option("— เลือกช่วงถนน (" + fmtInt(state.order.length) + " รายการ) —", ""));
    for (const id of state.order) select.append(new Option(segmentLabel(id), id));
  }
  select.value = state.selectedId && state.features.has(state.selectedId) ? state.selectedId : "";
  for (const [id, layer] of map.layers) {
    if (layer.getTooltip()) layer.setTooltipContent(tooltipNode(id));
  }
}

function selectSegment(id) {
  if (state.predBusy || state.ready !== "ready") return;
  const next = id && state.features.has(id) ? id : null;
  if (next === state.selectedId) return;
  state.selectedId = next;
  $("segmentSelect").value = next || "";
  invalidateResult();
  renderSegmentCard();
  if (next && map.layers.has(next)) map.layers.get(next).bringToFront();
}

function renderSegmentCard() {
  const card = $("segmentCard");
  card.replaceChildren();
  if (!state.selectedId || !state.features.has(state.selectedId)) {
    card.hidden = true;
    return;
  }
  const props = state.features.get(state.selectedId).properties || {};
  card.append(el("div", "seg-title", routeLabel(props.route_code)));
  const meta = [];
  const prov = provinceName(props.province_code);
  meta.push(prov ? "จังหวัด" + prov : "จังหวัด: ไม่ระบุ");
  if (isNum(props.segment_km)) meta.push("ยาว " + props.segment_km.toFixed(1) + " กม.");
  card.append(el("div", "seg-meta", meta.join(" · ")));
  const det = el("details");
  det.append(el("summary", null, "รหัสอ้างอิงช่วงถนน"), el("div", "mono", state.selectedId));
  card.append(det);
  card.hidden = false;
}

// ---------------------------------------------------------------- map

function initMap() {
  if (typeof window.L === "undefined" || !L.map) {
    $("mapFallbackText").textContent = "โหลดชุดแผนที่ไม่สำเร็จ (แผนที่ต้องใช้อินเทอร์เน็ต) คุณยังเลือกพื้นที่จากรายชื่อจังหวัดหรือปุ่มกรุงเทพฯ ได้ตามปกติ";
    $("mapFallback").hidden = false;
    $("mapHint").hidden = true;
    $("btnResetView").disabled = true;
    return;
  }
  try {
    const m = L.map("map", { zoomControl: true, minZoom: 5, maxZoom: 18, worldCopyJump: false });
    m.fitBounds(THAILAND_BOUNDS);
    const tiles = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).addTo(m);
    tiles.on("tileload", () => { map.tilesLoaded += 1; $("tileWarning").hidden = true; });
    tiles.on("tileerror", () => {
      map.tileErrors += 1;
      if (map.tileErrors >= 4) $("tileWarning").hidden = false;
    });
    map.roads = L.featureGroup().addTo(m);
    m.on("click", onMapClick);
    map.leaflet = m;
  } catch (_) {
    map.leaflet = null;
    $("mapFallback").hidden = false;
    $("mapHint").hidden = true;
  }
}

function tooltipNode(id) {
  return el("span", null, segmentLabel(id));
}

function addRoadLayer(id, feature) {
  if (!map.leaflet || !feature.geometry) return;
  let layer;
  try {
    layer = L.geoJSON(feature, { style: () => ({ ...NEUTRAL_STYLE }) });
  } catch (_) {
    return;
  }
  layer.bindTooltip(tooltipNode(id), { sticky: true, className: "road-tip" });
  layer.on("click", (e) => {
    L.DomEvent.stopPropagation(e);
    selectSegment(id);
  });
  layer.addTo(map.roads);
  map.layers.set(id, layer);
  styleRoad(id);
}

function styleRoad(id) {
  const layer = map.layers.get(id);
  if (!layer) return;
  if (id !== state.selectedId) {
    layer.setStyle({ ...NEUTRAL_STYLE });
    return;
  }
  const pred = state.prediction && state.prediction.ctx.segmentId === id ? state.prediction.row : null;
  const colour = pred && typeof pred.colour_hex === "string" && /^#[0-9a-fA-F]{6}$/.test(pred.colour_hex) ? pred.colour_hex : null;
  layer.setStyle(colour ? { color: colour, weight: 8, opacity: 1 } : { ...SELECTED_STYLE });
  layer.bringToFront();
}

function restyleRoads() {
  for (const id of map.layers.keys()) styleRoad(id);
}

function onMapClick(e) {
  if (state.ready !== "ready" || state.predBusy) return;
  const { lat, lng } = e.latlng;
  if (!insideEnvelope(lat, lng)) {
    clearArea();
    state.area = { bbox: null, title: "ตำแหน่ง " + fmtCoord(lat) + ", " + fmtCoord(lng), sub: "จุดนี้อยู่นอกพื้นที่ที่ระบบรองรับ (ประเทศไทย) — ไม่มีข้อมูล" };
    renderAreaStatus();
    return;
  }
  const half = Number($("radiusSelect").value) || 0.2;
  selectArea(
    { west: lng - half, south: lat - half, east: lng + half, north: lat + half },
    "รอบตำแหน่ง " + fmtCoord(lat) + ", " + fmtCoord(lng),
    "กรอบค้นหา ±" + half + "° (ประมาณ ±" + Math.round(half * 111) + " กม.)",
    { point: [lat, lng] },
  );
}

// ---------------------------------------------------------------- prediction & history

async function runPrediction() {
  if (state.ready !== "ready" || state.predBusy || state.segBusy) return;
  const ctx = currentInputs();
  if (!ctx.segmentId || !validDate(ctx.date)) return;
  invalidateResult();
  const gen = state.resultGen;
  const controller = new AbortController();
  state.predController = controller;
  state.predBusy = true;
  refreshControls();
  showTab("prediction");
  $("panelPrediction").replaceChildren(loadingRow("กำลังคำนวณค่าคาดการณ์…"));
  $("panelHistory").replaceChildren(loadingRow("รอผลการคาดการณ์ก่อนโหลดประวัติ…"));

  const row = { segment_id: ctx.segmentId, target_date: ctx.date };
  if (ctx.block) row.time_block = ctx.block;
  const stale = () => gen !== state.resultGen;

  let predJson = null;
  try {
    predJson = await apiFetch("/api/v1/spatial/predictions", { method: "POST", body: { unit: ctx.unit, requests: [row] }, controller });
  } catch (failure) {
    if (stale() || failure.kind === "aborted") return;
    finishPrediction(controller);
    if (isServiceDown(failure)) { serviceLost(); if (state.ready !== "ready") return; }
    $("panelPrediction").replaceChildren(errorBox(failure, runPrediction));
    renderHistoryEmpty();
    return;
  }
  if (stale()) return;
  const result = Array.isArray(predJson.results) ? predJson.results[0] : null;
  if (!result || result.segment_id !== ctx.segmentId || result.target_date !== ctx.date) {
    finishPrediction(controller);
    $("panelPrediction").replaceChildren(errorBox(new RequestFailure("invalid"), runPrediction));
    renderHistoryEmpty();
    return;
  }
  state.prediction = { ctx, row: result, response: predJson };
  renderPrediction(ctx, result, predJson);
  styleRoad(ctx.segmentId);

  // History for the same captured inputs.
  $("panelHistory").replaceChildren(loadingRow("กำลังโหลดประวัติที่บันทึก…"));
  const histBody = { segment_id: ctx.segmentId, target_date: ctx.date, unit: ctx.unit };
  if (ctx.block) histBody.time_block = ctx.block;
  let histJson = null;
  try {
    histJson = await apiFetch("/api/v1/spatial/history", { method: "POST", body: histBody, controller });
  } catch (failure) {
    if (stale() || failure.kind === "aborted") return;
    finishPrediction(controller);
    if (isServiceDown(failure)) { serviceLost(); if (state.ready !== "ready") return; }
    $("panelHistory").replaceChildren(errorBox(failure, reloadHistory));
    return;
  }
  if (stale()) return;
  finishPrediction(controller);
  renderHistory(ctx, histJson);
}

// Retry only the history card for the inputs of the prediction currently shown.
async function reloadHistory() {
  if (!state.prediction || state.predBusy || state.ready !== "ready") return;
  const ctx = state.prediction.ctx;
  const gen = state.resultGen;
  const controller = new AbortController();
  state.predController = controller;
  state.predBusy = true;
  refreshControls();
  $("panelHistory").replaceChildren(loadingRow("กำลังโหลดประวัติที่บันทึก…"));
  const body = { segment_id: ctx.segmentId, target_date: ctx.date, unit: ctx.unit };
  if (ctx.block) body.time_block = ctx.block;
  try {
    const json = await apiFetch("/api/v1/spatial/history", { method: "POST", body, controller });
    if (gen !== state.resultGen) return;
    finishPrediction(controller);
    renderHistory(ctx, json);
  } catch (failure) {
    if (gen !== state.resultGen || failure.kind === "aborted") return;
    finishPrediction(controller);
    if (isServiceDown(failure)) { serviceLost(); if (state.ready !== "ready") return; }
    $("panelHistory").replaceChildren(errorBox(failure, reloadHistory));
  }
}

function finishPrediction(controller) {
  if (state.predController === controller) state.predController = null;
  state.predBusy = false;
  refreshControls();
}

function horizonText(ctx) {
  return ctx.unit === "6h" ? fmtDate(ctx.date) + " ช่วง " + (BLOCK_LABEL[ctx.block] || ctx.block) : "ตลอดวัน " + fmtDate(ctx.date);
}

function renderPredictionEmpty() {
  const panel = $("panelPrediction");
  const empty = el("div", "empty");
  empty.append(el("strong", null, "ยังไม่มีผลการคาดการณ์"));
  empty.append(el("span", null, state.selectedId
    ? "กด “ดูการคาดการณ์” เพื่อดูค่าคาดการณ์ของช่วงถนนที่เลือกตามวันและเวลาที่กำหนด"
    : "เริ่มจากคลิกบนแผนที่หรือเลือกจังหวัด จากนั้นเลือกช่วงถนนที่มีข้อมูล"));
  panel.replaceChildren(empty);
}

function renderHistoryEmpty() {
  const empty = el("div", "empty");
  empty.append(el("strong", null, "ยังไม่มีประวัติที่แสดง"));
  empty.append(el("span", null, "ประวัติจะโหลดพร้อมการคาดการณ์ของช่วงถนนที่เลือก"));
  $("panelHistory").replaceChildren(empty);
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
    dl.append(el("dt", null, k), el("dd", null, v));
  }
  return dl;
}

function renderPrediction(ctx, r, response) {
  const panel = $("panelPrediction");
  panel.replaceChildren();
  const props = (state.features.get(ctx.segmentId) || {}).properties || {};
  const prov = provinceName(props.province_code);

  const hero = el("div", "result-hero");
  hero.append(el("div", "result-eyebrow", routeLabel(props.route_code) + (prov ? " · " + prov : "")));
  hero.append(el("div", "result-label", "จำนวนรายการอุบัติเหตุที่คาดว่าจะถูกบันทึก"));
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
  if (typeof r.colour_hex === "string" && /^#[0-9a-fA-F]{6}$/.test(r.colour_hex)) sw.style.background = r.colour_hex;
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
    "ค่านี้คือค่าคาดการณ์เชิงสถิติของจำนวนรายการอุบัติเหตุที่ถูกบันทึกและเชื่อมกับช่วงถนนนี้ในช่วงเวลาที่เลือก "
    + "ไม่ใช่โอกาสที่คุณหรือรถคันใดจะเกิดอุบัติเหตุ สีบนแผนที่ใช้เฉพาะช่วงถนนที่คาดการณ์อยู่ และเป็นการเปรียบเทียบเชิงสัมพัทธ์"));

  const det = el("details");
  det.append(el("summary", null, "ที่มาของผลลัพธ์และข้อจำกัด"));
  const sa = r.source_availability && typeof r.source_availability === "object"
    ? Object.entries(r.source_availability).map(([k, v]) => k + ": " + v).join(" · ") : null;
  det.append(kvList([
    ["ช่วงเวลาที่คาดการณ์", r.horizon],
    ["เวลาออกค่าคาดการณ์", r.issue_time_local],
    ["รุ่นแบบจำลอง", r.model_version],
    ["ส่วนของแบบจำลองที่ใช้", r.component_used],
    ["เหตุผลการเลือก", r.routing_reason],
    ["ช่วงข้อมูล", r.data_period],
    ["แหล่งข้อมูลประกอบ", sa],
  ]));
  if (Array.isArray(response.caveats) && response.caveats.length) {
    const ul = el("ul", "caveats");
    for (const c of response.caveats) ul.append(el("li", null, c));
    det.append(ul);
  }
  panel.append(det);
}

function barList(title, entries, wide) {
  const wrap = el("div", "bars");
  wrap.append(el("h3", null, title));
  const max = Math.max(1, ...entries.map(([, v]) => (isNum(v) ? v : 0)));
  for (const [label, v] of entries) {
    const row = el("div", "bar-row" + (wide ? " bar-row-wide" : ""));
    const track = el("div", "bar-track");
    const fill = el("div", "bar-fill");
    fill.style.width = isNum(v) ? (100 * v / max).toFixed(1) + "%" : "0";
    track.append(fill);
    row.append(el("span", "bar-label", label), track, el("span", "bar-count", isNum(v) ? fmtInt(v) : "—"));
    row.title = label;
    wrap.append(row);
  }
  return wrap;
}

function renderHistory(ctx, json) {
  const panel = $("panelHistory");
  panel.replaceChildren();
  const h = json && json.history && typeof json.history === "object" ? json.history : null;
  if (!h) {
    panel.append(errorBox(new RequestFailure("invalid"), reloadHistory));
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
    + " ถึง " + fmtDate(h.history_cutoff_local) + " (ก่อนวันที่คาดการณ์อย่างน้อย " + (isNum(h.latency_days) ? h.latency_days : "—") + " วัน)"));

  if (n === 0) {
    panel.append(el("div", "note-box", "ไม่พบรายการบันทึกในช่วงนี้ — ไม่ได้หมายความว่าถนนช่วงนี้ปลอดภัย"));
  }

  const ps = json.period_status || {};
  const gaps = [];
  if (ps.unsupported_after) gaps.push("ช่วงหลัง ธ.ค. 2025 ยังไม่อยู่ในฐานข้อมูล จึงไม่ได้นับ (ไม่ทราบ ไม่ใช่ศูนย์)");
  if (ps.unsupported_before) gaps.push("ช่วงก่อน ม.ค. 2021 อยู่นอกฐานข้อมูล จึงไม่ได้นับ");
  if (gaps.length) panel.append(el("div", "note-box", gaps.join(" · ")));

  if (h.counts_by_year && typeof h.counts_by_year === "object" && Object.keys(h.counts_by_year).length) {
    const years = Object.entries(h.counts_by_year).sort(([a], [b]) => a.localeCompare(b));
    panel.append(barList("รายปี (ค.ศ.)", years.map(([y, v]) => [y, v])));
  }
  if (h.counts_by_time_block && typeof h.counts_by_time_block === "object" && Object.keys(h.counts_by_time_block).length) {
    const blocks = Object.entries(h.counts_by_time_block).sort(([a], [b]) => a.localeCompare(b));
    panel.append(barList("ตามช่วงเวลาของวัน", blocks.map(([b, v]) => [(BLOCK_LABEL[b] || b), v])));
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
  det.append(el("p", null, "ข้อมูลเป็นรายการที่ถูกบันทึกและคัดเลือกเพื่อเชื่อมกับช่วงถนนนี้ ไม่ใช่จำนวนอุบัติเหตุทั้งหมด สาเหตุและสภาพอากาศเป็นข้อมูลที่บันทึกไว้ ไม่ใช่การพิสูจน์สาเหตุ และไม่ใช่สภาพอากาศปัจจุบัน"));
  if (Array.isArray(h.notes)) {
    const ul = el("ul", "caveats");
    for (const note of h.notes) ul.append(el("li", null, note));
    det.append(ul);
  }
  if (ps.note) det.append(el("p", null, ps.note));
  panel.append(det);
}

// ---------------------------------------------------------------- tabs

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

// ---------------------------------------------------------------- wiring

$("btnRetry").addEventListener("click", checkReady);
$("btnBangkok").addEventListener("click", () =>
  selectArea(BANGKOK_BBOX, "กรุงเทพฯ และปริมณฑล", "กรอบพื้นที่ที่กำหนดไว้ล่วงหน้า", { fit: true }));
$("btnViewRoads").addEventListener("click", () => {
  if (!map.leaflet) return;
  const b = map.leaflet.getBounds();
  selectArea({ west: b.getWest(), south: b.getSouth(), east: b.getEast(), north: b.getNorth() },
    "พื้นที่ในมุมมองแผนที่ปัจจุบัน", "จำกัดอยู่ในขอบเขตที่ระบบรองรับ");
});
$("btnResetView").addEventListener("click", () => {
  if (map.leaflet) map.leaflet.fitBounds(THAILAND_BOUNDS);
});
$("provinceSelect").addEventListener("change", (e) => {
  const p = state.provinces.get(e.target.value);
  if (!p) return;
  const pt = p.representative_point;
  selectArea(
    { west: pt.lon - PROVINCE_HALF_SPAN, south: pt.lat - PROVINCE_HALF_SPAN, east: pt.lon + PROVINCE_HALF_SPAN, north: pt.lat + PROVINCE_HALF_SPAN },
    "จังหวัด" + p.name_th,
    "กรอบรอบจุดอ้างอิงของจังหวัด (±" + PROVINCE_HALF_SPAN + "°) อาจไม่ครอบคลุมทั้งจังหวัด",
    { fit: true, point: [pt.lat, pt.lon] },
  );
  e.target.value = "";
});
$("segmentSelect").addEventListener("change", (e) => selectSegment(e.target.value || null));
$("btnMore").addEventListener("click", () => loadSegmentsPage(true));
$("targetDate").addEventListener("input", () => { updateDateNote(); invalidateResult(); });
for (const input of document.querySelectorAll('input[name="unit"], input[name="block"]')) {
  input.addEventListener("change", invalidateResult);
}
$("btnPredict").addEventListener("click", runPrediction);
$("tabPrediction").addEventListener("click", () => showTab("prediction"));
$("tabHistory").addEventListener("click", () => showTab("history"));
$("tabPrediction").addEventListener("keydown", onTabKey);
$("tabHistory").addEventListener("keydown", onTabKey);

initMap();
updateDateNote();
renderAreaStatus();
renderPredictionEmpty();
renderHistoryEmpty();
refreshControls();
checkReady();
