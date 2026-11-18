// Route → forecast pipeline (no React).
//   loadRouteMatches: every page of model road segments in the route's bbox, kept only when they really run
//                     along the route (routeMatch.js rule). Done once per route.
//   predictMatches:   estimated pass time per segment → its date + 6-hour block → selected-model rows,
//                     ≤128 per batch; any failed batch throws (no partial picture).
import { CONFIG, ENVELOPE, DATE_MIN, DATE_MAX, LEVELS } from "../config.js";
import { api, sleep, isNum, bkkToEpoch, epochToBkk, RequestFailure } from "./util.js";
import { matchFeature } from "./routeMatch.js";

export async function loadRouteMatches(route, { signal, onProgress }) {
  const bb = route.index.bbox;
  const bbox = [
    Math.max(ENVELOPE.west, bb.west - 0.01), Math.max(ENVELOPE.south, bb.south - 0.01),
    Math.min(ENVELOPE.east, bb.east + 0.01), Math.min(ENVELOPE.north, bb.north + 0.01),
  ].map((v) => Math.round(v * 10000) / 10000);

  const features = [];
  let cursor = null, page = 0, total = null;
  do {
    page += 1;
    onProgress("กำลังหาช่วงถนนที่มีข้อมูลบนเส้นทาง…", total ? (features.length / total) * 0.4 : 0.05);
    const qs = "?bbox=" + bbox.join(",") + "&limit=" + CONFIG.segmentPageSize + (cursor !== null ? "&cursor=" + encodeURIComponent(cursor) : "");
    const json = await api("/api/v1/segments" + qs, { signal });
    for (const f of Array.isArray(json.features) ? json.features : []) features.push(f);
    total = json.page && isNum(json.page.total_matched) ? json.page.total_matched : total;
    cursor = json.page && json.page.next_cursor != null ? json.page.next_cursor : null;
  } while (cursor !== null && page < 200);

  const matches = [];
  for (let i = 0; i < features.length; i++) {
    const f = features[i];
    const m = matchFeature(route.index, f);
    if (m) {
      const props = f.properties || {};
      const segM = isNum(props.segment_km) ? props.segment_km * 1000 : 2000;
      const frac = route.index.length > 0 ? m.along / route.index.length : 0;
      const alongM = frac * route.distance;
      matches.push({
        id: String(f.id ?? props.segment_id), feature: f, props, match: m, frac, alongM,
        startM: Math.max(0, alongM - segM / 2), endM: Math.min(route.distance, alongM + segM / 2),
      });
    }
    if (i % 300 === 299) {
      onProgress("กำลังจับคู่ช่วงถนนกับเส้นทาง…", 0.4 + (i / features.length) * 0.15);
      await sleep(0);
      if (signal.aborted) throw new RequestFailure("aborted");
    }
  }
  matches.sort((a, b) => a.alongM - b.alongM);
  return matches;
}

export async function predictMatches(matches, route, { date, time, signal, onProgress }) {
  const depart = bkkToEpoch(date, time);
  const rows = [];
  let outOfRange = 0;
  for (const mt of matches) {
    const eta = epochToBkk(depart + mt.frac * route.duration * 1000);
    if (eta.date >= DATE_MIN && eta.date <= DATE_MAX) rows.push({ mt, eta }); else outOfRange += 1;
  }
  const items = [];
  for (let i = 0; i < rows.length; i += CONFIG.predictionBatch) {
    if (onProgress) onProgress("กำลังประเมินความเสี่ยง " + Math.min(i + CONFIG.predictionBatch, rows.length) + "/" + rows.length + " ช่วงถนน…", 0.55 + (i / rows.length) * 0.45);
    const batch = rows.slice(i, i + CONFIG.predictionBatch);
    const body = { unit: "6h", requests: batch.map(({ mt, eta }) => ({ segment_id: mt.id, target_date: eta.date, time_block: eta.block })) };
    const json = await api("/api/v1/spatial/predictions", { method: "POST", body, signal });
    const res = Array.isArray(json.results) ? json.results : [];
    if (res.length !== batch.length) throw new RequestFailure("invalid", 200, null);
    res.forEach((pred, k) => {
      const level = pred && LEVELS[pred.colour] ? pred.colour : null;
      if (level) items.push({ ...batch[k].mt, eta: batch[k].eta, pred, level });
    });
  }
  return { items, outOfRange };
}

export async function fetchSegmentHistory(segmentId, targetDate, signal) {
  const json = await api("/api/v1/spatial/history", {
    method: "POST",
    signal,
    body: { segment_id: segmentId, target_date: targetDate, unit: "daily", lookback_days: CONFIG.historyLookbackDays, top_k: 10 },
  });
  return json.history || null;
}
