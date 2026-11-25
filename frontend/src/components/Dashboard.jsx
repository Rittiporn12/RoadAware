// แดชบอร์ด (Data Visualization, Level 1 — descriptive: what happened, where, when, how).
// Data: MOT open road-accident records 2564–2569, one row per accident, built by backend/scripts/build_dashboard_data.py
// into public/data/dashboard-v1.json. Everything is computed in the browser, so every filter and every click on a
// chart updates all other charts at once (cross-filtering: a chart ignores its own filter so you can still compare).
import { useEffect, useMemo, useRef, useState } from "react";
import * as L from "leaflet";
import "leaflet/dist/leaflet.css";
import { CONFIG, THAI_BOUNDS } from "../config.js";

const ENV = (import.meta.env) || {};
const DATA_URL = (ENV.BASE_URL || "./") + "data/dashboard-v1.json";
const MONTHS = ["ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.", "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."];
const DOW = ["จ.", "อ.", "พ.", "พฤ.", "ศ.", "ส.", "อา."];
const DOW_FULL = ["วันจันทร์", "วันอังคาร", "วันพุธ", "วันพฤหัสบดี", "วันศุกร์", "วันเสาร์", "วันอาทิตย์"];
const PERIODS = ["วันปกติ", "สงกรานต์ (11–17 เม.ย.)", "ปีใหม่ (29 ธ.ค.–4 ม.ค.)"];
const METRICS = [
  { key: "acc", label: "จำนวนอุบัติเหตุ", unit: "ครั้ง" },
  { key: "dead", label: "ผู้เสียชีวิต", unit: "ราย" },
  { key: "inj", label: "ผู้บาดเจ็บ", unit: "ราย" },
];
const DAY_MS = 86400000;
const BASE_UTC = Date.UTC(2021, 0, 1);
const fmt = (v) => Math.round(v).toLocaleString("en-US");
const fmt1 = (v) => (Math.round(v * 10) / 10).toLocaleString("en-US", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const ymLabel = (ym) => MONTHS[ym % 12] + " " + (2564 + Math.floor(ym / 12));

const EMPTY = { years: [], region: -1, prov: -1, month: -1, cell: -1, period: -1, type: -1, veh: -1, cause: -1, wx: -1 };
// Cross-filter dimensions: a chart is computed with every filter except its own.
const XD = ["month", "prov", "cell", "period", "type", "veh", "cause", "wx"];

// ---------------------------------------------------------------- data
function prepare(raw) {
  const { cols, dims, meta } = raw;
  const n = cols.day.length;
  const yi = new Uint8Array(n), ym = new Uint16Array(n), cell = new Int16Array(n), fest = new Uint8Array(n), reg = new Uint8Array(n);
  for (let i = 0; i < n; i++) {
    const d = new Date(BASE_UTC + cols.day[i] * DAY_MS);
    const y = d.getUTCFullYear(), m = d.getUTCMonth(), dd = d.getUTCDate();
    yi[i] = y - 2021;
    ym[i] = (y - 2021) * 12 + m;
    const h = cols.hour[i];
    cell[i] = h >= 0 ? ((d.getUTCDay() + 6) % 7) * 24 + h : -1;
    fest[i] = m === 3 && dd >= 11 && dd <= 17 ? 1 : (m === 11 && dd >= 29) || (m === 0 && dd <= 4) ? 2 : 0;
    reg[i] = dims.provRegion[cols.prov[i]];
  }
  // calendar of every day in the data (for "per day" averages)
  const nd = meta.last_day + 1;
  const dYear = new Uint8Array(nd), dYm = new Uint16Array(nd), dFest = new Uint8Array(nd), dDow = new Uint8Array(nd);
  for (let k = 0; k < nd; k++) {
    const d = new Date(BASE_UTC + k * DAY_MS);
    const y = d.getUTCFullYear(), m = d.getUTCMonth(), dd = d.getUTCDate();
    dYear[k] = y - 2021; dYm[k] = (y - 2021) * 12 + m; dDow[k] = (d.getUTCDay() + 6) % 7;
    dFest[k] = m === 3 && dd >= 11 && dd <= 17 ? 1 : (m === 11 && dd >= 29) || (m === 0 && dd <= 4) ? 2 : 0;
  }
  const lastYm = dYm[nd - 1];
  return { n, cols, dims, meta, yi, ym, cell, fest, reg, cal: { nd, dYear, dYm, dFest, dDow }, lastYm, years: meta.years_be };
}

function aggregate(D, f, metric) {
  const { n, cols, yi, ym, cell, fest, reg, dims } = D;
  const nm = D.lastYm + 1;
  const out = {
    month: new Float64Array(nm), prov: new Float64Array(dims.prov.length), cell: new Float64Array(7 * 24),
    period: new Float64Array(3), type: new Float64Array(dims.type.length), veh: new Float64Array(dims.veh.length),
    cause: new Float64Array(dims.cause.length), wx: new Float64Array(dims.wx.length),
    map: new Map(), kpi: { acc: 0, dead: 0, serious: 0, minor: 0 },
  };
  const ys = f.years.length ? new Set(f.years.map((y) => y - 2564)) : null;
  const val = { month: ym, prov: cols.prov, cell, period: fest, type: cols.type, veh: cols.veh, cause: cols.cause, wx: cols.wx };
  const active = XD.filter((k) => f[k] >= 0);
  const { dead, serious, minor } = cols;
  const mapCell = cols.cell;
  for (let i = 0; i < n; i++) {
    if (ys && !ys.has(yi[i])) continue;
    if (f.region >= 0 && reg[i] !== f.region) continue;
    let fails = 0, failK = null;
    for (let a = 0; a < active.length; a++) {
      const k = active[a];
      if (val[k][i] !== f[k]) { fails++; failK = k; if (fails > 1) break; }
    }
    if (fails > 1) continue;
    const w = metric === "acc" ? 1 : metric === "dead" ? dead[i] : serious[i] + minor[i];
    if (fails === 1) {
      const v = val[failK][i];
      if (v >= 0) out[failK][v] += w;
      continue;
    }
    out.kpi.acc += 1; out.kpi.dead += dead[i]; out.kpi.serious += serious[i]; out.kpi.minor += minor[i];
    out.month[ym[i]] += w; out.prov[cols.prov[i]] += w; out.period[fest[i]] += w;
    if (cell[i] >= 0) out.cell[cell[i]] += w;
    out.type[cols.type[i]] += w; out.veh[cols.veh[i]] += w; out.cause[cols.cause[i]] += w; out.wx[cols.wx[i]] += w;
    if (w > 0 && mapCell[i] >= 0) out.map.set(mapCell[i], (out.map.get(mapCell[i]) || 0) + w);
  }
  // number of calendar days in each period (respecting year / month / weekday filters) → per-day averages
  const { nd, dYear, dYm, dFest, dDow } = D.cal;
  const days = [0, 0, 0];
  let allDays = 0;
  const dowF = f.cell >= 0 ? Math.floor(f.cell / 24) : -1;
  for (let k = 0; k < nd; k++) {
    if (ys && !ys.has(dYear[k])) continue;
    if (f.month >= 0 && dYm[k] !== f.month) continue;
    if (dowF >= 0 && dDow[k] !== dowF) continue;
    days[dFest[k]]++;
    if (f.period < 0 || dFest[k] === f.period) allDays++;
  }
  out.days = days; out.allDays = allDays;
  return out;
}

// ---------------------------------------------------------------- small pieces
function useWidth(ref) {
  const [w, setW] = useState(600);
  useEffect(() => {
    const el = ref.current;
    if (!el) return undefined;
    const ro = new ResizeObserver(([e]) => setW(Math.max(240, Math.round(e.contentRect.width))));
    ro.observe(el);
    return () => ro.disconnect();
  }, [ref]);
  return w;
}

function Card({ title, sub, children, className = "", action }) {
  return (
    <section className={"db-card " + className}>
      <header className="db-card-h">
        <div><h3>{title}</h3>{sub && <p>{sub}</p>}</div>
        {action}
      </header>
      {children}
    </section>
  );
}

// Horizontal bars; click a bar to filter by it, click again to clear.
function Bars({ items, selected, onPick, unit, limit, valueText }) {
  const shown = limit ? items.slice(0, limit) : items;
  const max = Math.max(1, ...items.map((d) => d.value));
  const total = items.reduce((a, d) => a + d.value, 0) || 1;
  return (
    <ul className={"db-bars" + (selected >= 0 ? " has-sel" : "")}>
      {shown.map((d) => (
        <li key={d.key}>
          <button type="button" className={d.key === selected ? "is-sel" : ""} onClick={() => onPick(d.key === selected ? -1 : d.key)}
            title={`${d.label}: ${fmt(d.value)} ${unit} (${fmt1((d.value / total) * 100)}%) — คลิกเพื่อกรอง`}>
            <span className="db-bar-l">{d.label}</span>
            <span className="db-bar-t"><i style={{ width: (d.value / max) * 100 + "%" }} /></span>
            <span className="db-bar-v">{valueText ? valueText(d) : fmt(d.value)}</span>
          </button>
        </li>
      ))}
    </ul>
  );
}

function rank(arr, names, opts = {}) {
  const items = [];
  arr.forEach((v, i) => { if (!(opts.skip && opts.skip(i))) items.push({ key: i, label: names[i], value: v }); });
  return opts.keepOrder ? items : items.sort((a, b) => b.value - a.value);
}

// Monthly trend (single series). Hover = crosshair + value; click = filter that month.
function Trend({ data, from, to, selected, onPick, unit }) {
  const ref = useRef(null);
  const w = useWidth(ref);
  const [hover, setHover] = useState(null);
  const h = 220, pad = { l: 46, r: 12, t: 12, b: 28 };
  const xs = [];
  for (let m = from; m <= to; m++) xs.push(m);
  const max = Math.max(1, ...xs.map((m) => data[m]));
  const step = Math.pow(10, Math.floor(Math.log10(max)));
  const yMax = Math.ceil(max / step) * step;
  const X = (i) => pad.l + (xs.length < 2 ? 0 : (i / (xs.length - 1)) * (w - pad.l - pad.r));
  const Y = (v) => pad.t + (1 - v / yMax) * (h - pad.t - pad.b);
  const line = xs.map((m, i) => (i ? "L" : "M") + X(i).toFixed(1) + " " + Y(data[m]).toFixed(1)).join(" ");
  const area = line + ` L${X(xs.length - 1).toFixed(1)} ${Y(0)} L${X(0).toFixed(1)} ${Y(0)} Z`;
  const ticks = [0, yMax / 2, yMax];
  const idxAt = (clientX) => {
    const r = ref.current.getBoundingClientRect();
    const t = (clientX - r.left - pad.l) / (w - pad.l - pad.r);
    return Math.max(0, Math.min(xs.length - 1, Math.round(t * (xs.length - 1))));
  };
  const hi = hover != null ? hover : selected >= from && selected <= to ? selected - from : null;
  return (
    <div className="db-trend" ref={ref}>
      <svg width={w} height={h} onMouseMove={(e) => setHover(idxAt(e.clientX))} onMouseLeave={() => setHover(null)}
        onClick={(e) => { const m = xs[idxAt(e.clientX)]; onPick(m === selected ? -1 : m); }} role="img" aria-label="จำนวนรายเดือน">
        {ticks.map((t) => (
          <g key={t}><line x1={pad.l} x2={w - pad.r} y1={Y(t)} y2={Y(t)} className="db-grid" /><text x={pad.l - 8} y={Y(t) + 4} textAnchor="end" className="db-axis">{fmt(t)}</text></g>
        ))}
        {xs.map((m, i) => (m % 12 === 0 || i === 0 ? (
          <g key={m}><line x1={X(i)} x2={X(i)} y1={pad.t} y2={h - pad.b} className="db-grid db-grid-y" /><text x={X(i) + 4} y={h - 8} className="db-axis">{2564 + Math.floor(m / 12)}</text></g>
        ) : null))}
        {xs.map((m, i) => ((m % 12 === 3) ? <rect key={"s" + m} x={X(i) - 3} y={pad.t} width="6" height={h - pad.t - pad.b} className="db-songkran" /> : null))}
        <path d={area} className="db-area" />
        <path d={line} className="db-line" />
        {selected >= from && selected <= to && <circle cx={X(selected - from)} cy={Y(data[selected])} r="5" className="db-dot-sel" />}
        {hi != null && (
          <g>
            <line x1={X(hi)} x2={X(hi)} y1={pad.t} y2={h - pad.b} className="db-cross" />
            <circle cx={X(hi)} cy={Y(data[xs[hi]])} r="4.5" className="db-dot" />
          </g>
        )}
      </svg>
      {hi != null && (
        <div className="db-tip" style={{ left: Math.min(w - 150, Math.max(0, X(hi) - 70)), top: 0 }}>
          <b>{ymLabel(xs[hi])}</b><span>{fmt(data[xs[hi]])} {unit}</span>
        </div>
      )}
    </div>
  );
}

// Weekday × hour heatmap (sequential, one hue). Click a cell to filter.
function Heat({ data, selected, onPick, unit }) {
  const max = Math.max(1, ...data);
  const min = Math.min(...data);
  const [hover, setHover] = useState(null);
  // one hue, light → dark, stretched between this view's min and max so differences stay visible
  const color = (v) => {
    const t = max > min ? (v - min) / (max - min) : 0;
    const a = [240, 246, 245], b = [8, 79, 75];
    return `rgb(${a.map((x, i) => Math.round(x + (b[i] - x) * t)).join(",")})`;
  };
  return (
    <div className="db-heat">
      <div className="db-heat-grid" onMouseLeave={() => setHover(null)}>
        <span />
        {Array.from({ length: 24 }, (_, hh) => <span key={hh} className="db-heat-hx">{hh % 3 === 0 ? hh : ""}</span>)}
        {DOW.map((dn, d) => (
          <FragmentRow key={d} d={d} dn={dn} data={data} color={color} selected={selected} onPick={onPick} setHover={setHover} />
        ))}
      </div>
      <div className="db-heat-foot">
        <span>{hover != null ? `${DOW_FULL[Math.floor(hover / 24)]} ${String(hover % 24).padStart(2, "0")}:00–${String(hover % 24).padStart(2, "0")}:59 · ${fmt(data[hover])} ${unit}` : "ชี้ที่ช่องเพื่อดูตัวเลข · คลิกเพื่อกรอง"}</span>
        <span className="db-ramp"><small>น้อย</small><i /><small>มาก</small></span>
      </div>
    </div>
  );
}
function FragmentRow({ d, dn, data, color, selected, onPick, setHover }) {
  return (
    <>
      <span className="db-heat-dy">{dn}</span>
      {Array.from({ length: 24 }, (_, hh) => {
        const k = d * 24 + hh;
        return (
          <button key={hh} type="button" className={"db-heat-c" + (k === selected ? " is-sel" : "")} style={{ background: color(data[k]) }}
            onMouseEnter={() => setHover(k)} onFocus={() => setHover(k)} onClick={() => onPick(k === selected ? -1 : k)}
            aria-label={`${DOW_FULL[d]} ${hh}:00 ${fmt(data[k])}`} />
        );
      })}
    </>
  );
}

// Density map: one circle per ~5 km cell, area ∝ value.
function DensityMap({ cells, grid, unit }) {
  const el = useRef(null);
  const mapRef = useRef(null);
  const layerRef = useRef(null);
  useEffect(() => {
    const map = L.map(el.current, { zoomControl: true, attributionControl: true, preferCanvas: true, minZoom: 5, maxZoom: 11 });
    L.tileLayer(CONFIG.tileUrl, { attribution: CONFIG.tileAttribution, subdomains: CONFIG.tileSubdomains, maxZoom: 19 }).addTo(map);
    map.fitBounds(THAI_BOUNDS);
    layerRef.current = L.layerGroup().addTo(map);
    mapRef.current = map;
    return () => { map.remove(); mapRef.current = null; };
  }, []);
  useEffect(() => {
    const layer = layerRef.current;
    if (!layer) return;
    layer.clearLayers();
    let max = 1;
    cells.forEach((v) => { if (v > max) max = v; });
    const renderer = L.canvas({ padding: 0.3 });
    const entries = [...cells.entries()].sort((a, b) => a[1] - b[1]);
    for (const [c, v] of entries) {
      const lat = grid.lat0 + Math.floor(c / grid.nlon) * grid.cell_deg;
      const lon = grid.lon0 + (c % grid.nlon) * grid.cell_deg;
      const t = Math.sqrt(v / max);
      L.circleMarker([lat, lon], { renderer, radius: 1 + 7 * t, stroke: false, fillColor: "#C8372D", fillOpacity: 0.18 + 0.55 * t })
        .bindTooltip(`${fmt(v)} ${unit}`, { direction: "top", offset: [0, -4] })
        .addTo(layer);
    }
  }, [cells, grid, unit]);
  return <div className="db-map" ref={el} />;
}

// ---------------------------------------------------------------- page
export default function Dashboard() {
  const [raw, setRaw] = useState(null);
  const [err, setErr] = useState(null);
  const [f, setF] = useState(EMPTY);
  const [metric, setMetric] = useState("acc");
  const [allProv, setAllProv] = useState(false);

  useEffect(() => { document.title = "แดชบอร์ด — RoadAware"; }, []);
  useEffect(() => {
    let alive = true;
    fetch(DATA_URL).then((r) => (r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status))))
      .then((j) => { if (alive) setRaw(prepare(j)); })
      .catch((e) => { if (alive) setErr(String(e.message || e)); });
    return () => { alive = false; };
  }, []);

  const agg = useMemo(() => (raw ? aggregate(raw, f, metric) : null), [raw, f, metric]);
  const set = (k, v) => setF((cur) => ({ ...cur, [k]: v, ...(k === "region" ? { prov: -1 } : {}) }));
  const toggleYear = (y) => setF((cur) => {
    const has = cur.years.includes(y);
    return { ...cur, years: has ? cur.years.filter((x) => x !== y) : [...cur.years, y].sort(), month: -1 };
  });
  const M = METRICS.find((m) => m.key === metric);

  if (err) return <DashShell><div className="db-empty">โหลดข้อมูลไม่สำเร็จ ({err}) — ลองรีเฟรชหน้า</div></DashShell>;
  if (!raw || !agg) return <DashShell><div className="db-empty"><span className="boot-dot" /> กำลังโหลดข้อมูลอุบัติเหตุ…</div></DashShell>;

  const { dims, meta } = raw;
  const years = raw.years;
  const sel = f.years.length ? f.years : years;
  const from = (Math.min(...sel) - 2564) * 12;
  const to = Math.min(raw.lastYm, (Math.max(...sel) - 2564) * 12 + 11);
  const lastDate = new Date(BASE_UTC + meta.last_day * DAY_MS);
  const k = agg.kpi;
  const injured = k.serious + k.minor;
  const perDay = agg.allDays ? k.acc / agg.allDays : 0;

  // chips for active filters
  const chips = [];
  f.years.forEach((y) => chips.push({ label: "ปี " + y, clear: () => toggleYear(y) }));
  if (f.region >= 0) chips.push({ label: "ภาค" + dims.region[f.region], clear: () => set("region", -1) });
  if (f.prov >= 0) chips.push({ label: dims.prov[f.prov], clear: () => set("prov", -1) });
  if (f.month >= 0) chips.push({ label: ymLabel(f.month), clear: () => set("month", -1) });
  if (f.cell >= 0) chips.push({ label: `${DOW_FULL[Math.floor(f.cell / 24)]} ${f.cell % 24}:00 น.`, clear: () => set("cell", -1) });
  if (f.period >= 0) chips.push({ label: PERIODS[f.period].split(" (")[0], clear: () => set("period", -1) });
  ["type", "veh", "cause", "wx"].forEach((key) => { if (f[key] >= 0) chips.push({ label: dims[key][f[key]], clear: () => set(key, -1) }); });

  // quick facts from what is on screen
  const top = (arr, names, skipLast) => { let bi = -1; arr.forEach((v, i) => { if ((!skipLast || i < names.length - 1) && (bi < 0 || v > arr[bi])) bi = i; }); return bi >= 0 && arr[bi] > 0 ? names[bi] : "—"; };
  const hourSum = new Array(24).fill(0);
  agg.cell.forEach((v, i) => { hourSum[i % 24] += v; });
  const peakH = hourSum.indexOf(Math.max(...hourSum));
  const provItems = rank(agg.prov, dims.prov, { skip: (i) => dims.prov[i] === "ไม่ระบุ" });
  const perDayFest = [0, 1, 2].map((p) => ({ key: p, label: PERIODS[p], value: agg.days[p] ? agg.period[p] / agg.days[p] : 0 }));

  return (
    <DashShell>
      <div className="db-head">
        <div>
          <h1>แดชบอร์ดอุบัติเหตุทางถนน</h1>
          <p>ข้อมูลอุบัติเหตุจริงจาก<a href={meta.source} target="_blank" rel="noopener noreferrer">กระทรวงคมนาคม</a> ปี {years[0]}–{years[years.length - 1]} · {fmt(meta.records)} รายการ · ข้อมูลถึง {lastDate.getUTCDate()} {MONTHS[lastDate.getUTCMonth()]} {lastDate.getUTCFullYear() + 543}</p>
        </div>
        <div className="db-metric" role="radiogroup" aria-label="ตัวชี้วัด">
          {METRICS.map((m) => (
            <button key={m.key} type="button" role="radio" aria-checked={metric === m.key} className={metric === m.key ? "is-on" : ""} onClick={() => setMetric(m.key)}>{m.label}</button>
          ))}
        </div>
      </div>

      <div className="db-filters">
        <div className="db-years" role="group" aria-label="ปี">
          <button type="button" className={!f.years.length ? "is-on" : ""} onClick={() => setF((c) => ({ ...c, years: [], month: -1 }))}>ทุกปี</button>
          {years.map((y) => <button key={y} type="button" className={f.years.includes(y) ? "is-on" : ""} onClick={() => toggleYear(y)}>{y}</button>)}
        </div>
        <label className="db-sel"><span>ภาค</span>
          <select value={f.region} onChange={(e) => set("region", +e.target.value)}>
            <option value={-1}>ทุกภาค</option>
            {dims.region.map((r, i) => (r === "ไม่ระบุ" ? null : <option key={r} value={i}>{r}</option>))}
          </select>
        </label>
        <label className="db-sel"><span>จังหวัด</span>
          <select value={f.prov} onChange={(e) => set("prov", +e.target.value)}>
            <option value={-1}>ทุกจังหวัด</option>
            {dims.prov.map((p, i) => ((f.region < 0 || dims.provRegion[i] === f.region) && p !== "ไม่ระบุ" ? <option key={p} value={i}>{p}</option> : null))}
          </select>
        </label>
        <label className="db-sel"><span>ช่วงเทศกาล</span>
          <select value={f.period} onChange={(e) => set("period", +e.target.value)}>
            <option value={-1}>ทุกช่วง</option>
            {PERIODS.map((p, i) => <option key={p} value={i}>{p}</option>)}
          </select>
        </label>
        <label className="db-sel"><span>สภาพอากาศ</span>
          <select value={f.wx} onChange={(e) => set("wx", +e.target.value)}>
            <option value={-1}>ทุกสภาพ</option>
            {dims.wx.map((p, i) => <option key={p} value={i}>{p}</option>)}
          </select>
        </label>
      </div>
      <div className="db-chips" aria-live="polite">
        {chips.length ? (
          <>
            {chips.map((c) => <button key={c.label} type="button" className="db-chip" onClick={c.clear}>{c.label}<span aria-hidden="true">×</span></button>)}
            <button type="button" className="db-clear" onClick={() => setF(EMPTY)}>ล้างตัวกรองทั้งหมด</button>
          </>
        ) : <span className="db-hint">เลือกตัวกรองด้านบน หรือคลิกที่แท่งกราฟ ช่องตาราง หรือจุดบนกราฟเส้น เพื่อกรองทุกกราฟพร้อมกัน</span>}
      </div>

      <div className="db-kpis">
        <div className="db-kpi"><span>อุบัติเหตุ</span><b>{fmt(k.acc)}</b><small>เฉลี่ย {fmt1(perDay)} ครั้ง/วัน</small></div>
        <div className="db-kpi"><span>ผู้เสียชีวิต</span><b>{fmt(k.dead)}</b><small>{fmt1(k.acc ? (k.dead / k.acc) * 100 : 0)} รายต่อ 100 เหตุ</small></div>
        <div className="db-kpi"><span>ผู้บาดเจ็บสาหัส</span><b>{fmt(k.serious)}</b><small>{fmt1(injured ? (k.serious / injured) * 100 : 0)}% ของผู้บาดเจ็บ</small></div>
        <div className="db-kpi"><span>ผู้บาดเจ็บเล็กน้อย</span><b>{fmt(k.minor)}</b><small>รวมบาดเจ็บ {fmt(injured)} ราย</small></div>
      </div>

      <div className="db-facts">
        <span>จังหวัดที่มี{M.label}มากที่สุด <b>{provItems[0] && provItems[0].value > 0 ? provItems[0].label : "—"}</b></span>
        <span>ช่วงเวลาที่พบมากที่สุด <b>{hourSum[peakH] > 0 ? `${String(peakH).padStart(2, "0")}:00–${String(peakH).padStart(2, "0")}:59 น.` : "—"}</b></span>
        <span>ลักษณะที่พบบ่อยที่สุด <b>{top(agg.type, dims.type, true)}</b></span>
        <span>สาเหตุที่พบบ่อยที่สุด <b>{top(agg.cause, dims.cause, true)}</b></span>
      </div>

      <div className="db-grid2 db-grid-wide">
        <Card title={`${M.label}รายเดือน`} sub="แถบจางคือเดือนเมษายน (สงกรานต์) · คลิกที่เส้นเพื่อกรองเดือนนั้น">
          <Trend data={agg.month} from={from} to={to} selected={f.month} onPick={(v) => set("month", v)} unit={M.unit} />
        </Card>
      </div>

      <div className="db-grid2">
        <Card title="แผนที่ความหนาแน่น" sub="วงกลมใหญ่ = เกิดมาก (รวมเป็นช่องละราว 5 กม.)" className="db-card-map">
          <DensityMap cells={agg.map} grid={meta.grid} unit={M.unit} />
        </Card>
        <Card title={`${M.label}รายจังหวัด`} sub="คลิกที่แท่งเพื่อกรองจังหวัด"
          action={<button type="button" className="db-link" onClick={() => setAllProv((v) => !v)}>{allProv ? "แสดง 15 อันดับ" : "ดูทุกจังหวัด"}</button>}>
          <div className={allProv ? "db-scroll" : ""}>
            <Bars items={provItems} selected={f.prov} onPick={(v) => set("prov", v)} unit={M.unit} limit={allProv ? 0 : 15} />
          </div>
        </Card>
      </div>

      <div className="db-grid2">
        <Card title="วันและเวลาที่เกิดเหตุ" sub="แถว = วันในสัปดาห์ · คอลัมน์ = ชั่วโมง (0–23 น.)">
          <Heat data={agg.cell} selected={f.cell} onPick={(v) => set("cell", v)} unit={M.unit} />
        </Card>
        <Card title="ช่วงเทศกาลเทียบวันปกติ" sub={`${M.label}เฉลี่ยต่อวัน · คลิกเพื่อกรอง`}>
          <Bars items={perDayFest} selected={f.period} onPick={(v) => set("period", v)} unit={`${M.unit}/วัน`} valueText={(d) => fmt1(d.value)} />
          <p className="db-note">สงกรานต์และปีใหม่นับ 7 วันอันตรายตามที่ใช้กันทั่วไป ค่าเฉลี่ยต่อวันจึงเทียบกันได้แม้จำนวนวันต่างกัน</p>
        </Card>
      </div>

      <div className="db-grid2">
        <Card title="ลักษณะการเกิดเหตุ" sub="คลิกเพื่อกรอง">
          <Bars items={rank(agg.type, dims.type)} selected={f.type} onPick={(v) => set("type", v)} unit={M.unit} />
        </Card>
        <Card title="มูลเหตุสันนิษฐาน" sub="คลิกเพื่อกรอง">
          <Bars items={rank(agg.cause, dims.cause)} selected={f.cause} onPick={(v) => set("cause", v)} unit={M.unit} />
        </Card>
      </div>

      <div className="db-grid2">
        <Card title="ยานพาหนะคันแรกที่เกิดเหตุ" sub="คลิกเพื่อกรอง">
          <Bars items={rank(agg.veh, dims.veh)} selected={f.veh} onPick={(v) => set("veh", v)} unit={M.unit} />
        </Card>
        <Card title="สภาพอากาศขณะเกิดเหตุ" sub="คลิกเพื่อกรอง">
          <Bars items={rank(agg.wx, dims.wx)} selected={f.wx} onPick={(v) => set("wx", v)} unit={M.unit} />
        </Card>
      </div>

      <p className="db-foot">
        1 รายการ = 1 อุบัติเหตุที่บันทึกบนถนนในความรับผิดชอบของกระทรวงคมนาคม (กรมทางหลวง กรมทางหลวงชนบท และการทางพิเศษฯ) ไม่ใช่ทุกถนนในประเทศ ·
        ตำแหน่งบนแผนที่รวมเป็นช่องละราว 5 กม. · หมวดที่พบน้อยรวมเป็น “อื่นๆ” · ข้อมูลปี {years[years.length - 1]} ยังไม่ครบทั้งปี
      </p>
    </DashShell>
  );
}

function DashShell({ children }) {
  return (
    <div className="dash">
      <header className="db-nav">
        <div className="db-wrap db-nav-in">
          <a className="db-brand" href="#/">
            <svg width="28" height="28" viewBox="0 0 26 26" aria-hidden="true"><circle cx="13" cy="13" r="12" fill="#0F1B2D" /><path d="M7 18 C10 12, 13 15, 19 7" stroke="#E8821E" strokeWidth="2.6" fill="none" strokeLinecap="round" /></svg>
            <span>RoadAware</span>
          </a>
          <nav className="db-links" aria-label="เมนู">
            <a href="#/">หน้าแรก</a>
            <a href="#/dashboard" aria-current="page">แดชบอร์ด</a>
          </nav>
          <a className="db-go" href="#/app">เริ่มใช้งาน</a>
        </div>
      </header>
      <main className="db-wrap db-main">{children}</main>
    </div>
  );
}
