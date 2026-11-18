// Turning per-segment forecasts into things a traveller can read:
//   zones   — consecutive "ระวัง/ระวังมาก" segments along the route merged into numbered zones (max 5 shown)
//   ribbon  — the whole route A→B as a strip of coloured pieces (grey = no forecast coverage)
//   history — recorded categories summed over a zone's segments ("ส่วนใหญ่เกิดจาก…") and plain-language tips
// Forecast values are never summed into a route probability; only historical record counts are added up.
import { CONFIG, LEVELS, ZONE_LEVELS, BLOCKS } from "../config.js";
import { isNum, routeLabel } from "./util.js";

export function buildZones(items, provinceName) {
  const high = items.filter((it) => ZONE_LEVELS.includes(it.level)).sort((a, b) => a.startM - b.startM);
  const groups = [];
  for (const it of high) {
    const g = groups[groups.length - 1];
    if (g && it.startM - g.endM <= CONFIG.zoneGapM) {
      g.members.push(it);
      g.endM = Math.max(g.endM, it.endM);
    } else {
      groups.push({ members: [it], startM: it.startM, endM: it.endM });
    }
  }
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
    const maxDensity = Math.max(...g.members.map((m) => (isNum(m.pred.density_per_km) ? m.pred.density_per_km : 0)));
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
    };
  });
  const ranked = [...zones].sort((a, b) => LEVELS[b.level].rank - LEVELS[a.level].rank || b.lengthM - a.lengthM || b.maxDensity - a.maxDensity);
  const shown = ranked.slice(0, CONFIG.maxZones).sort((a, b) => a.startM - b.startM);
  shown.forEach((z, i) => { z.n = i + 1; });
  return { zones: shown, hidden: Math.max(0, zones.length - shown.length), counts: zoneCounts(zones) };
}

export function zoneCounts(zones) {
  let red = 0, orange = 0;
  for (const z of zones) { if (z.level === "red") red += 1; else orange += 1; }
  return { red, orange };
}

export function buildRibbon(items, distance) {
  const n = CONFIG.ribbonBins;
  const w = distance / n;
  const bins = new Array(n).fill(null);
  for (const it of items) {
    const b0 = Math.max(0, Math.floor(it.startM / w)), b1 = Math.min(n - 1, Math.floor(it.endM / w));
    for (let b = b0; b <= b1; b++) {
      if (!bins[b] || LEVELS[it.level].rank > LEVELS[bins[b]].rank) bins[b] = it.level;
    }
  }
  const pieces = [];
  let covered = 0;
  for (const lv of bins) {
    if (lv) covered += 1;
    const last = pieces[pieces.length - 1];
    if (last && last.level === lv) last.n += 1; else pieces.push({ level: lv, n: 1 });
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
