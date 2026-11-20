// Turning per-segment forecasts into things a traveller can read:
//   zones   — the trip's HOTSPOTS: segments whose national level is สูง/สูงมาก AND that are in the top 20% of this
//             route's evaluated segments (by predicted recorded density), merged into numbered zones (max 5 shown)
//   ribbon  — the whole route A→B as a strip (trip view: hotspot / evaluated / no data; national view: level colours)
//   summary — share of the evaluated route length in each national level (lengths only — never a route probability)
//   history — recorded categories summed over a zone's segments ("ส่วนใหญ่เกิดจาก…") and plain-language tips
// Forecast values are never summed into a route probability; only lengths and historical record counts are added up.
import { CONFIG, LEVELS, ZONE_LEVELS, BLOCKS } from "../config.js";
import { isNum, routeLabel } from "./util.js";

export function density(it) {
  const p = it.pred || {};
  if (isNum(p.density_per_km)) return p.density_per_km;
  const km = Math.max((it.endM - it.startM) / 1000, 0.5);
  return isNum(p.expected_recorded_count) ? p.expected_recorded_count / km : 0;
}

function quantile(sorted, q) {
  if (!sorted.length) return Infinity;
  const pos = (sorted.length - 1) * q, lo = Math.floor(pos), hi = Math.ceil(pos);
  return sorted[lo] + (sorted[hi] - sorted[lo]) * (pos - lo);
}

const lengthKm = (it) => Math.max(0, it.endM - it.startM) / 1000;

export function buildZones(items, provinceName) {
  const empty = { zones: [], hidden: 0, counts: levelKm(items), hotIds: new Set(), threshold: null };
  if (!items.length) return empty;
  const ds = items.map(density).sort((a, b) => a - b);
  const threshold = quantile(ds, CONFIG.hotspotQuantile);
  const hot = items.filter((it) => ZONE_LEVELS.includes(it.level) && density(it) >= threshold).sort((a, b) => a.startM - b.startM);
  const groups = [];
  for (const it of hot) {
    const g = groups[groups.length - 1];
    if (g && it.startM - g.endM <= CONFIG.zoneGapM) {
      g.members.push(it);
      g.endM = Math.max(g.endM, it.endM);
    } else {
      groups.push({ members: [it], startM: it.startM, endM: it.endM });
    }
  }
  const rankOf = (d) => { let lo = 0, hi = ds.length; while (lo < hi) { const mid = (lo + hi) >> 1; if (ds[mid] < d) lo = mid + 1; else hi = mid; } return lo / ds.length; };
  const zones = groups.map((g) => {
    const level = g.members.reduce((best, m) => (LEVELS[m.level].rank > LEVELS[best].rank ? m.level : best), "orange");
    const first = g.members.reduce((a, b) => (a.alongM <= b.alongM ? a : b));
    const mid = (g.startM + g.endM) / 2;
    const anchorItem = g.members.reduce((a, b) => (Math.abs(a.alongM - mid) <= Math.abs(b.alongM - mid) ? a : b));
    const codes = {};
    const provs = [];
    for (const m of g.members) {
      const c = m.props.route_code;
      if (typeof c === "string" && c) codes[c] = (codes[c] || 0) + 1;
      const p = provinceName(m.props.province_code);
      if (p && !provs.includes(p)) provs.push(p);
    }
    const code = Object.keys(codes).sort((a, b) => codes[b] - codes[a])[0];
    const maxDensity = Math.max(...g.members.map(density));
    return {
      key: g.members.map((m) => m.id).sort().join("+"),
      level,
      members: g.members,
      startM: g.startM,
      endM: g.endM,
      lengthM: g.endM - g.startM,
      eta: first.eta,
      anchor: anchorItem.match.anchor,
      road: code ? routeLabel(code) : "ทางหลวง",
      provinces: provs,
      maxDensity,
      routeRank: rankOf(maxDensity), // share of this route's evaluated segments with a lower predicted density
    };
  });
  // Keep the strongest hotspots (highest predicted density), then number them in the order they are passed.
  const ranked = [...zones].sort((a, b) => b.maxDensity - a.maxDensity || LEVELS[b.level].rank - LEVELS[a.level].rank || b.lengthM - a.lengthM);
  const shown = ranked.slice(0, CONFIG.maxZones).sort((a, b) => a.startM - b.startM);
  shown.forEach((z, i) => { z.n = i + 1; });
  const hotIds = new Set(shown.flatMap((z) => z.members.map((m) => m.id)));
  return { zones: shown, hidden: Math.max(0, zones.length - shown.length), counts: levelKm(items), hotIds, threshold };
}

// Evaluated route length per national level (km). Used for the overview bar and the departure comparison.
export function levelKm(items) {
  const km = { red: 0, orange: 0, yellow: 0, base: 0 };
  for (const it of items) if (km[it.level] !== undefined) km[it.level] += lengthKm(it);
  return km;
}

export function buildRibbon(items, distance, hotIds) {
  const n = CONFIG.ribbonBins;
  const w = distance / n;
  const bins = new Array(n).fill(null);
  for (const it of items) {
    const b0 = Math.max(0, Math.floor(it.startM / w)), b1 = Math.min(n - 1, Math.floor(it.endM / w));
    const hot = !!(hotIds && hotIds.has(it.id));
    for (let b = b0; b <= b1; b++) {
      const cur = bins[b];
      if (!cur) bins[b] = { level: it.level, hot };
      else bins[b] = { level: LEVELS[it.level].rank > LEVELS[cur.level].rank ? it.level : cur.level, hot: cur.hot || hot };
    }
  }
  const pieces = [];
  let covered = 0;
  for (const bin of bins) {
    if (bin) covered += 1;
    const last = pieces[pieces.length - 1];
    const level = bin ? bin.level : null, hot = bin ? bin.hot : false;
    if (last && last.level === level && last.hot === hot) last.n += 1; else pieces.push({ level, hot, n: 1 });
  }
  return { pieces, coverage: covered / n };
}

// ---------- history over a zone ----------
const CATS = ["weather", "accident_type", "presumed_cause"];

export function aggregateHistory(histories) {
  const agg = { n: 0, blocks: {}, cats: {} };
  for (const c of CATS) agg.cats[c] = { known: 0, unknown: 0, values: new Map() };
  for (const h of histories) {
    if (!h) continue;
    agg.n += isNum(h.n_selected_records) ? h.n_selected_records : 0;
    for (const c of CATS) {
      const src = h.categories && h.categories[c];
      if (!src) continue;
      agg.cats[c].known += isNum(src.known_records) ? src.known_records : 0;
      agg.cats[c].unknown += isNum(src.unknown_records) ? src.unknown_records : 0;
      for (const t of Array.isArray(src.top_values) ? src.top_values : []) {
        const v = String(t.value);
        agg.cats[c].values.set(v, (agg.cats[c].values.get(v) || 0) + (isNum(t.records) ? t.records : 0));
      }
    }
    for (const b of BLOCKS) {
      const v = h.counts_by_time_block && h.counts_by_time_block[b];
      if (isNum(v)) agg.blocks[b] = (agg.blocks[b] || 0) + v;
    }
  }
  return agg;
}

export function topValues(agg, cat, k) {
  const c = agg.cats[cat];
  if (!c || c.known <= 0) return [];
  return [...c.values.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, k)
    .map(([value, records]) => ({ value, records, share: records / c.known }));
}

export function rainShare(agg) {
  const c = agg.cats.weather;
  if (!c || c.known <= 0) return null;
  let rain = 0;
  for (const [v, r] of c.values) if (/ฝน/.test(v)) rain += r;
  return rain / c.known;
}

export function peakBlock(agg) {
  let best = null;
  for (const b of BLOCKS) {
    const v = agg.blocks[b];
    if (isNum(v) && v > 0 && (!best || v > best.records)) best = { block: b, records: v };
  }
  return best;
}

// General, plain-language advice derived only from what was recorded most often (never a causal claim).
export function tipsFor(agg) {
  const tips = [];
  const add = (t) => { if (!tips.includes(t) && tips.length < 3) tips.push(t); };
  const types = topValues(agg, "accident_type", 3).filter((t) => t.share >= 0.15);
  for (const t of types) {
    const v = t.value;
    if (/ชนท้าย/.test(v)) add("เว้นระยะจากคันหน้าอย่างน้อย 3 วินาที และระวังรถชะลอกะทันหัน");
    else if (/โค้ง/.test(v)) add("ลดความเร็วก่อนเข้าโค้ง ไม่ใช่ระหว่างโค้ง");
    else if (/พลิกคว่ำ|ตกถนน/.test(v)) add("ระวังการหลับใน พักรถทุก 2 ชั่วโมง และหลีกเลี่ยงการหักหลบกะทันหัน");
    else if (/สิ่งกีดขวาง/.test(v)) add("ระวังสิ่งกีดขวางและงานบนผิวทาง โดยเฉพาะตอนกลางคืน");
    else if (/ตรงกันข้าม|แซง/.test(v)) add("ระวังรถสวนทางและการแซงบนช่วงที่ไม่มีเกาะกลาง");
    else if (/ด้านข้าง|ตัดหน้า|ทางแยก/.test(v)) add("ระวังรถเปลี่ยนเลน ทางแยก และจุดกลับรถ");
  }
  const rain = rainShare(agg);
  if (rain !== null && rain >= 0.2) add("ถ้าฝนตก เปิดไฟหน้า ลดความเร็ว และเว้นระยะมากกว่าปกติ");
  const cause = topValues(agg, "presumed_cause", 1)[0];
  if (cause && cause.share >= 0.3) {
    if (/เร็ว/.test(cause.value)) add("ขับตามความเร็วที่กำหนด — เหตุส่วนใหญ่ที่นี่ถูกบันทึกว่าขับเร็วเกินกำหนด");
    else if (/หลับ/.test(cause.value)) add("ถ้าง่วง ให้แวะพักก่อนถึงช่วงนี้");
  }
  const peak = peakBlock(agg);
  if (peak && (peak.block === "18-24" || peak.block === "00-06")) add("เหตุมักเกิดช่วงกลางคืน ระวังทัศนวิสัยและเปิดไฟให้เห็นชัด");
  return tips;
}
