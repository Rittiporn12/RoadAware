import { CONFIG } from "../config.js";

export const isNum = (v) => typeof v === "number" && Number.isFinite(v);
export const isHex = (v) => typeof v === "string" && /^#[0-9a-fA-F]{6}$/.test(v);
export const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
export const pad2 = (n) => String(n).padStart(2, "0");

// ---------- HTTP ----------
export class RequestFailure extends Error {
  constructor(kind, status, body) { super(kind); this.kind = kind; this.status = status; this.body = body; }
}

// JSON fetch with timeout and optional cancellation. Throws RequestFailure (kind: aborted|timeout|network|http|invalid).
export async function fetchJson(url, { method = "GET", body, signal, timeoutMs = CONFIG.externalTimeoutMs } = {}) {
  const ctrl = new AbortController();
  let timedOut = false;
  const timer = setTimeout(() => { timedOut = true; ctrl.abort(); }, timeoutMs);
  const onAbort = () => ctrl.abort();
  if (signal) { if (signal.aborted) ctrl.abort(); else signal.addEventListener("abort", onAbort, { once: true }); }
  const init = { method, signal: ctrl.signal, cache: "no-store" };
  if (body !== undefined) { init.headers = { "Content-Type": "application/json" }; init.body = JSON.stringify(body); }
  let res, text;
  try {
    res = await fetch(url, init);
    text = await res.text();
  } catch (err) {
    if (err && err.name === "AbortError") throw new RequestFailure(timedOut ? "timeout" : "aborted");
    throw new RequestFailure("network");
  } finally {
    clearTimeout(timer);
    if (signal) signal.removeEventListener("abort", onAbort);
  }
  let json = null;
  try { json = JSON.parse(text); } catch (_) { json = null; }
  if (res.ok) {
    if (json === null || typeof json !== "object") throw new RequestFailure("invalid", res.status, null);
    return json;
  }
  throw new RequestFailure("http", res.status, json);
}

export const api = (path, opts = {}) => fetchJson(CONFIG.apiBase + path, { timeoutMs: CONFIG.apiTimeoutMs, ...opts });

export function techText(f) {
  if (!f) return null;
  const parts = [f.kind || "error"];
  if (f.status) parts.push("HTTP " + f.status);
  const e = f.body && f.body.error;
  if (e && e.code) parts.push(String(e.code));
  return parts.join(" · ");
}

export const isServiceDown = (f) => f && (f.kind === "network" || f.kind === "timeout" || f.status === 503);

// ---------- Bangkok time (independent of the browser's zone) ----------
const BKK_OFFSET_MS = 7 * 3600 * 1000;

export function bkkToEpoch(dateIso, timeHm) {
  const [y, mo, d] = dateIso.split("-").map(Number);
  const [h, mi] = timeHm.split(":").map(Number);
  return Date.UTC(y, mo - 1, d, h, mi) - BKK_OFFSET_MS;
}

export function epochToBkk(ms) {
  const t = new Date(ms + BKK_OFFSET_MS);
  const date = t.getUTCFullYear() + "-" + pad2(t.getUTCMonth() + 1) + "-" + pad2(t.getUTCDate());
  const hour = t.getUTCHours();
  const block = hour < 6 ? "00-06" : hour < 12 ? "06-12" : hour < 18 ? "12-18" : "18-24";
  return { date, hour, minute: t.getUTCMinutes(), block, clock: pad2(hour) + ":" + pad2(t.getUTCMinutes()) + " น." };
}

// ---------- formatting ----------
export const fmtKm = (m) => (m / 1000).toLocaleString("th-TH", { maximumFractionDigits: m < 10000 ? 1 : 0 }) + " กม.";
export function fmtDuration(s) {
  const mins = Math.round(s / 60);
  const h = Math.floor(mins / 60), mm = mins % 60;
  return h > 0 ? h + " ชม. " + mm + " นาที" : mm + " นาที";
}
export const fmtThaiDate = (iso) => new Date(iso + "T00:00:00").toLocaleDateString("th-TH", { day: "numeric", month: "short", year: "numeric" });
export const fmtPct = (x) => Math.round(x * 100) + "%";
export function fmtSmall(v) {
  if (!isNum(v)) return "ไม่มีข้อมูล";
  return v === 0 ? "0" : v.toLocaleString("th-TH", { maximumSignificantDigits: 2 });
}
export function routeLabel(code) {
  if (typeof code !== "string" || code === "") return "ทางหลวง";
  return "ทางหลวงหมายเลข " + (/^\d+$/.test(code) ? String(Number(code)) : code);
}
