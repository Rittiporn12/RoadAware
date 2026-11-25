// "ย้อนดูผล" (look back): for a route and a PAST period, where would the model have pointed — and where did recorded
// accidents actually happen? Only days the served model never trained on (training cut-off 2023-12-01):
// 2024–2025 (years used to check the model) and Jan–Sep 2026 (the unseen test year).
import { CONFIG, LEVELS } from "../config.js";
import { api, RequestFailure } from "./util.js";

export const REVIEW_MIN = "2024-01-01";
export const REVIEW_MAX = "2026-09-30";
export const REVIEW_MAX_DAYS = 31;
export const TEST_START = "2026-01-01";

export const REVIEW_PERIODS = [
  { id: "songkran69", label: "สงกรานต์ 2569", start: "2026-04-11", end: "2026-04-17" },
  { id: "newyear69", label: "ปีใหม่ 2569", start: "2025-12-29", end: "2026-01-04" },
  { id: "songkran68", label: "สงกรานต์ 2568", start: "2025-04-11", end: "2025-04-17" },
  { id: "newyear68", label: "ปีใหม่ 2568", start: "2024-12-29", end: "2025-01-04" },
];

export function daysBetween(start, end) {
  const out = [];
  const d = new Date(start + "T00:00:00Z"), e = new Date(end + "T00:00:00Z");
  for (; d <= e && out.length <= 400; d.setUTCDate(d.getUTCDate() + 1)) out.push(d.toISOString().slice(0, 10));
  return out;
}

export function periodProblem(p) {
  if (!p || !p.start || !p.end) return "เลือกช่วงเวลา";
  if (p.start < REVIEW_MIN || p.end > REVIEW_MAX) return "เลือกได้ระหว่าง 1 ม.ค. 2567 – 30 ก.ย. 2569";
  if (p.end < p.start) return "วันสิ้นสุดต้องไม่ก่อนวันเริ่ม";
  if (daysBetween(p.start, p.end).length > REVIEW_MAX_DAYS) return "เลือกได้ไม่เกิน " + REVIEW_MAX_DAYS + " วัน";
  return null;
}

// Model side: the daily forecast of every route segment on every day of the period, summed per segment.
// Level of a segment = its highest daily national level in the period. Same hotspot rule as the trip view afterwards.
export async function reviewForecast(matches, { start, end, signal, onProgress }) {
  const days = daysBetween(start, end);
  const rows = [];
  for (const mt of matches) for (const d of days) rows.push({ mt, d });
  const agg = new Map();
  for (let i = 0; i < rows.length; i += CONFIG.predictionBatch) {
    onProgress("โมเดลกำลังประเมินย้อนหลัง " + Math.min(i + CONFIG.predictionBatch, rows.length) + "/" + rows.length + " (ช่วงถนน × วัน)…",
      0.55 + (i / rows.length) * 0.4);
    const batch = rows.slice(i, i + CONFIG.predictionBatch);
    const json = await api("/api/v1/spatial/predictions", { method: "POST", signal,
      body: { unit: "daily", requests: batch.map(({ mt, d }) => ({ segment_id: mt.id, target_date: d })) } });
    const res = Array.isArray(json.results) ? json.results : [];
    if (res.length !== batch.length) throw new RequestFailure("invalid", 200, null);
    res.forEach((p, k) => {
      const mt = batch[k].mt;
      const a = agg.get(mt.id) || { mt, sum: 0, level: null };
      if (p && typeof p.expected_recorded_count === "number") a.sum += p.expected_recorded_count;
      if (p && LEVELS[p.colour] && (!a.level || LEVELS[p.colour].rank > LEVELS[a.level].rank)) a.level = p.colour;
      agg.set(mt.id, a);
    });
  }
  const items = [];
  for (const { mt, sum, level } of agg.values()) {
    if (!level) continue;
    const km = Math.max((mt.endM - mt.startM) / 1000, 0.5);
    items.push({ ...mt, level, eta: { clock: "", block: null }, pred: { expected_recorded_count: sum, density_per_km: sum / km } });
  }
  items.sort((a, b) => a.alongM - b.alongM);
  return { items, days: days.length };
}

// Recorded side: accidents per route segment in the period (no coordinates — shown at the segment on the route).
export async function reviewActuals(matches, { start, end, signal }) {
  const ids = [...new Set(matches.map((m) => m.id))];
  const bySeg = new Map();
  let periodKind = null;
  for (let i = 0; i < ids.length; i += 3000) {
    const json = await api("/api/v1/review/actual", { method: "POST", signal, body: { segment_ids: ids.slice(i, i + 3000), start, end } });
    periodKind = json.period_kind || periodKind;
    for (const r of Array.isArray(json.counts) ? json.counts : []) bySeg.set(r.segment_id, (bySeg.get(r.segment_id) || 0) + r.count);
  }
  return { bySeg, periodKind };
}
