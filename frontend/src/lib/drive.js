// Drive mode helpers (no React): where am I along the route, what is the next numbered point, what to say.
// Positions are in route metres (route.distance scale, the same scale as zone.startM / zone.endM).
import { nearestOnRoute } from "./routeMatch.js";
import { topValues, tipsFor } from "./zones.js";
import { CONFIG } from "../config.js";

// Lat/lon at a distance along the route (simulation).
export function pointAt(route, alongM) {
  const ix = route.index;
  const target = Math.max(0, Math.min(ix.length, (alongM / route.distance) * ix.length));
  let lo = 0, hi = ix.cum.length - 1;
  while (lo < hi - 1) { const mid = (lo + hi) >> 1; if (ix.cum[mid] <= target) lo = mid; else hi = mid; }
  const seg = ix.cum[hi] - ix.cum[lo];
  const t = seg > 0 ? (target - ix.cum[lo]) / seg : 0;
  const x = ix.pts[lo][0] + t * (ix.pts[hi][0] - ix.pts[lo][0]);
  const y = ix.pts[lo][1] + t * (ix.pts[hi][1] - ix.pts[lo][1]);
  const [lon, lat] = ix.proj.inv(x, y);
  const heading = (Math.atan2(ix.pts[hi][0] - ix.pts[lo][0], ix.pts[hi][1] - ix.pts[lo][1]) * 180) / Math.PI;
  return { lat, lon, heading };
}

// GPS fix → distance along the route, or null when the fix is not on (near) the route.
export function locate(route, lat, lon) {
  const ix = route.index;
  const [x, y] = ix.proj.fwd(lon, lat);
  const hit = nearestOnRoute(ix, x, y);
  if (!hit) return null;
  return { alongM: (hit.along / ix.length) * route.distance, offM: hit.d };
}

// The point you are in, or the next one ahead.
export function nextZone(zones, alongM) {
  for (const z of zones) {
    if (alongM >= z.startM && alongM <= z.endM) return { zone: z, inside: true, distM: 0 };
    if (z.startM > alongM) return { zone: z, inside: false, distM: z.startM - alongM };
  }
  return null;
}

const km = (m) => (m >= 1000 ? (Math.round(m / 100) / 10).toString().replace(/\.0$/, "") + " กิโลเมตร" : Math.round(m / 50) * 50 + " เมตร");

// Thai sentence for a spoken warning. agg = aggregated recorded history of the zone (may be null).
export function warningText(z, stage, agg) {
  const where = z.road + (z.provinces && z.provinces.length ? " ช่วง" + z.provinces[0] : "");
  let s;
  if (stage === "inside") s = "เข้าสู่จุดที่ควรระวังแล้ว! จุดที่ " + z.n + " ยาวประมาณ " + km(z.lengthM) + " ตั้งใจขับนะ";
  else if (stage <= 500) s = "ระวัง! อีก " + km(stage) + " ถึงจุดที่ " + z.n + " " + where;
  else s = "ข้างหน้าอีก " + km(stage) + " มีจุดที่ควรระวัง จุดที่ " + z.n + " " + where;
  if (agg && agg.n > 0 && stage !== "inside") {
    const t = topValues(agg, "accident_type", 1)[0];
    if (t && t.share >= 0.25) s += " ที่ผ่านมาส่วนใหญ่เป็น " + t.value;
    const tip = tipsFor(agg)[0];
    if (tip) s += " " + tip.split("—")[0].trim();
  }
  return s;
}

export function fmtDist(m) {
  if (m >= 10000) return Math.round(m / 1000) + " กม.";
  if (m >= 1000) return (Math.round(m / 100) / 10).toFixed(1) + " กม.";
  return Math.max(0, Math.round(m / 50) * 50) + " ม.";
}

// Speech. First choice: the local voice proxy (Mac Siri voice by default, or Gemini TTS) (backend/scripts/tts_proxy.py — the API key
// stays on the computer, never in the browser). Fallback: the device's own Thai voice. One fixed, lively style.
// Messages are QUEUED, never cut off mid-sentence; if several wait (fast simulation) only the newest per group
// (one numbered point) is kept so the voice never falls behind the car. A short chime precedes each warning.
const RATE = 1.12, PITCH = 1.2;
const audioCache = new Map(); // text -> Promise<object URL | null>
let proxyState = "unknown";   // unknown | ok | off
let proxyEngine = "mac";      // mac (Siri / system voice rendered by the proxy) | gemini

export async function checkVoiceProxy() {
  try {
    const r = await fetch(CONFIG.ttsUrl + "/health", { signal: AbortSignal.timeout ? AbortSignal.timeout(2500) : undefined });
    const j = await r.json();
    proxyState = r.ok && j.ok ? "ok" : "off";
    proxyEngine = j.engine === "gemini" ? "gemini" : "mac";
  } catch (_) { proxyState = "off"; }
  return proxyState;
}
export const voiceSource = () => proxyState;
export const voiceLabel = (state) => (state === "ok" ? (proxyEngine === "gemini" ? "เสียง Gemini" : "เสียง Siri (Mac)") : "เสียงเบราว์เซอร์");

function fetchAudio(text) {
  if (proxyState === "off") return Promise.resolve(null);
  if (!audioCache.has(text)) {
    const p = fetch(CONFIG.ttsUrl + "/tts", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text }) })
      .then((r) => (r.ok ? r.blob() : null))
      .then((b) => (b && b.size > 100 ? URL.createObjectURL(b) : null))
      .catch(() => null);
    audioCache.set(text, p);
    p.then((u) => { if (!u) audioCache.delete(text); });
  }
  return audioCache.get(text);
}
// One request at a time, in route order (nearest points first): the free Gemini tier allows only a few clips per
// minute, so the proxy paces them; firing them all at once would only tie up the browser's connections.
const prefetchQueue = [];
let prefetching = false;
async function drainPrefetch() {
  if (prefetching) return;
  prefetching = true;
  while (prefetchQueue.length && proxyState !== "off") {
    const t = prefetchQueue.shift();
    await fetchAudio(t);
  }
  prefetching = false;
}
export function prefetchSpeech(texts) {
  prefetchQueue.length = 0;
  for (const t of texts) if (t && !prefetchQueue.includes(t)) prefetchQueue.push(t);
  drainPrefetch();
}

let audioCtx = null;
function chime() {
  try {
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return 0;
    audioCtx = audioCtx || new AC();
    const t = audioCtx.currentTime;
    [[880, 0], [1320, 0.13]].forEach(([f, dt]) => {
      const o = audioCtx.createOscillator(), g = audioCtx.createGain();
      o.type = "sine"; o.frequency.value = f;
      g.gain.setValueAtTime(0.0001, t + dt); g.gain.exponentialRampToValueAtTime(0.25, t + dt + 0.02); g.gain.exponentialRampToValueAtTime(0.0001, t + dt + 0.12);
      o.connect(g).connect(audioCtx.destination); o.start(t + dt); o.stop(t + dt + 0.13);
    });
    return 300;
  } catch (_) { return 0; }
}

const queue = [];
let speaking = false, gen = 0, current = null;

// Best Thai voice on this device: downloaded Premium / Enhanced (or Google / Siri) voices sound far more natural
// than the compact default, so they win when installed.
function bestThaiVoice() {
  const th = window.speechSynthesis.getVoices().filter((x) => /^th/i.test(x.lang));
  const score = (x) => (/premium/i.test(x.name) ? 4 : /enhanced|ปรับปรุง/i.test(x.name) ? 3 : /google|siri/i.test(x.name) ? 2 : 0) + (x.localService ? 0.5 : 0);
  return th.sort((a, b) => score(b) - score(a))[0] || null;
}

function deviceVoice(text, done) {
  if (!window.speechSynthesis) { done(); return; }
  const u = new SpeechSynthesisUtterance(text);
  u.lang = "th-TH";
  const v = bestThaiVoice();
  if (v) u.voice = v;
  u.rate = RATE; u.pitch = PITCH;
  u.onend = done; u.onerror = done;
  window.speechSynthesis.speak(u);
}

async function playNext() {
  if (speaking || !queue.length) return;
  const { text, group } = queue.shift();
  speaking = true;
  const my = gen;
  const done = () => { if (my !== gen) return; speaking = false; current = null; playNext(); };
  const wait = group ? chime() : 0;
  // Gemini audio if it arrives quickly (prefetched ones are instant); otherwise the device voice.
  const url = await Promise.race([fetchAudio(text), new Promise((r) => setTimeout(() => r(null), 3500))]);
  if (my !== gen) return;
  await new Promise((r) => setTimeout(r, wait));
  if (my !== gen) return;
  if (url) {
    const a = new Audio(url);
    current = a;
    a.onended = done; a.onerror = () => deviceVoice(text, done);
    a.play().catch(() => deviceVoice(text, done));
  } else {
    deviceVoice(text, done);
  }
}

export function speak(text, muted, group) {
  try {
    if (muted || typeof window === "undefined") return false;
    if (!window.speechSynthesis && proxyState === "off") return false;
    if (group) for (let i = queue.length - 1; i >= 0; i--) if (queue[i].group === group) queue.splice(i, 1);
    queue.push({ text, group: group || null });
    playNext();
    return true;
  } catch (_) {
    return false;
  }
}

export function stopSpeech() {
  queue.length = 0;
  gen += 1;
  speaking = false;
  try { if (current) current.pause(); } catch (_) { /* ignore */ }
  current = null;
  try { if (window.speechSynthesis) window.speechSynthesis.cancel(); } catch (_) { /* ignore */ }
}
