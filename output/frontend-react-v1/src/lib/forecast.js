// Route → forecast pipeline (no React here, so it can be reasoned about and tested on its own).
//   1. fetch every page of model road segments inside the route's bounding box
//   2. keep only segments that genuinely run along the route (routeMatch.js rule)
//   3. estimate when the traveller passes each segment → that date + 6-hour block
//   4. ask the selected model for those exact rows, ≤128 per batch; any failed batch discards everything
//   5. merge circles that sit on top of each other (e.g. both carriageways)
import { CONFIG, ENVELOPE, DATE_MIN, DATE_MAX, LEVELS } from "../config.js";
import { api, sleep, isNum, isHex, bkkToEpoch, epochToBkk, RequestFailure } from "./util.js";
import { matchFeature } from "./routeMatch.js";

export async function runForecast({ route, date, time, signal, onProgress }) {
  const index = route.index;
  const bb = index.bbox;
  const bbox = [
    Math.max(ENVELOPE.west, bb.west - 0.01), Math.max(ENVELOPE.south, bb.south - 0.01),
    Math.min(ENVELOPE.east, bb.east + 0.01), Math.min(ENVELOPE.north, bb.north + 0.01),
  ].map((v) => Math.round(v * 10000) / 10000);

  // 1) all pages
  const features = [];
  let cursor = null, page = 0, total = null;
  do {
    page += 1;
    onProgress("กำลังโหลดช่วงถนนที่มีข้อมูลรอบเส้นทาง" + (total ? " (" + features.length + "/" + total + ")" : "…"), total ? (features.length / total) * 0.4 : 0.05);
    const qs = "?bbox=" + bbox.join(",") + "&limit=" + CONFIG.segmentPageSize + (cursor !== null ? "&cursor=" + encodeURIComponent(cursor) : "");
    const json = await api("/api/v1/segments" + qs, { signal });
    for (const f of Array.isArray(json.features) ? json.features : []) features.push(f);
    total = json.page && isNum(json.page.total_matched) ? json.page.total_matched : total;
    cursor = json.page && json.page.next_cursor != null ? json.page.next_cursor : null;
  } while (cursor !== null && page < 200);

  // 2) geometric matching, chunked so the UI stays responsive
  const matches = [];
  for (let i = 0; i < features.length; i++) {
    const f = features[i];
    const m = matchFeature(index, f);
    if (m) matches.push({ id: String(f.id ?? (f.properties && f.properties.segment_id)), feature: f, props: f.properties || {}, match: m });
    if (i % 300 === 299) {
      onProgress("กำลังจับคู่ช่วงถนนกับเส้นทาง…", 0.4 + (i / features.length) * 0.15);
      await sleep(0);
      if (signal.aborted) throw new RequestFailure("aborted");
    }
  }
  if (matches.length === 0) return { items: [], spots: [], outOfRange: 0, candidates: features.length };

  // 3) pass time per segment
  const depart = bkkToEpoch(date, time);
  const inRange = [];
  let outOfRange = 0;
  for (const mt of matches) {
    const frac = index.length > 0 ? mt.match.along / index.length : 0;
    mt.eta = epochToBkk(depart + frac * route.duration * 1000);
    mt.alongM = frac * route.distance;
    if (mt.eta.date >= DATE_MIN && mt.eta.date <= DATE_MAX) inRange.push(mt); else outOfRange += 1;
  }

  // 4) predictions
  const preds = new Map();
  for (let i = 0; i < inRange.length; i += CONFIG.predictionBatch) {
    onProgress("กำลังประเมินความเสี่ยง " + Math.min(i + CONFIG.predictionBatch, inRange.length) + "/" + inRange.length + " ช่วงถนน…", 0.55 + (i / inRange.length) * 0.45);
    const batch = inRange.slice(i, i + CONFIG.predictionBatch);
    const body = { unit: "6h", requests: batch.map((mt) => ({ segment_id: mt.id, target_date: mt.eta.date, time_block: mt.eta.block })) };
    const json = await api("/api/v1/spatial/predictions", { method: "POST", body, signal });
    const rows = Array.isArray(json.results) ? json.results : [];
    if (rows.length !== batch.length) throw new RequestFailure("invalid", 200, null);
    rows.forEach((row, k) => preds.set(batch[k].id, row));
  }

  const items = [];
  for (const mt of inRange) {
    const pred = preds.get(mt.id);
    const level = pred && LEVELS[pred.colour] ? pred.colour : null;
    if (!level) continue;
    items.push({ ...mt, pred, level, hex: isHex(pred.colour_hex) ? pred.colour_hex : LEVELS[level].hex });
  }
  return { items, spots: groupSpots(items), outOfRange, candidates: features.length };
}

export function groupSpots(items) {
  const sorted = [...items].sort((a, b) => a.match.along - b.match.along);
  const groups = [];
  for (const it of sorted) {
    const g = groups[groups.length - 1];
    if (g && it.match.along - g.members[g.members.length - 1].match.along < CONFIG.groupWithinM) g.members.push(it);
    else groups.push({ members: [it] });
  }
  for (const g of groups) {
    g.members.sort((a, b) => LEVELS[b.level].rank - LEVELS[a.level].rank || (b.pred.density_per_km || 0) - (a.pred.density_per_km || 0));
    g.primary = g.members[0];
    g.key = g.primary.id;
  }
  return groups;
}

// ---------- history helpers ("what was mostly recorded here") ----------
export function topValues(h, cat, n) {
  const c = h && h.categories && h.categories[cat];
  if (!c || !isNum(c.known_records) || c.known_records <= 0 || !Array.isArray(c.top_values)) return [];
  return c.top_values.slice(0, n).map((t) => ({ value: String(t.value), records: t.records, share: t.records / c.known_records }));
}

export function rainShare(h) {
  const c = h && h.categories && h.categories.weather;
  if (!c || !isNum(c.known_records) || c.known_records <= 0) return null;
  let rain = 0;
  for (const t of c.top_values || []) if (/ฝน/.test(String(t.value))) rain += t.records;
  return rain / c.known_records;
}

export function peakBlock(h) {
  const tb = h && h.counts_by_time_block;
  if (!tb) return null;
  let best = null;
  for (const [k, v] of Object.entries(tb)) if (isNum(v) && (!best || v > best[1])) best = [k, v];
  return best && best[1] > 0 ? best : null;
}

export async function fetchHistory(spot, signal) {
  const p = spot.primary;
  const json = await api("/api/v1/spatial/history", {
    method: "POST",
    signal,
    body: { segment_id: p.id, target_date: p.eta.date, unit: "daily", lookback_days: CONFIG.historyLookbackDays, top_k: 5 },
  });
  return { history: json.history || null, period: json.period_status || null };
}
