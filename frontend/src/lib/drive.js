// Drive mode helpers (no React): where am I along the route, what is the next numbered point, what to say.
// Positions are in route metres (route.distance scale, the same scale as zone.startM / zone.endM).
import { nearestOnRoute } from "./routeMatch.js";
import { topValues, tipsFor } from "./zones.js";

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
  if (stage === "inside") s = "เข้าสู่จุดที่ควรระวัง ที่ " + z.n + " " + where + " ยาวประมาณ " + km(z.lengthM) + " ขับด้วยความระมัดระวัง";
  else s = "อีก " + km(stage) + " ถึงจุดที่ควรระวัง ที่ " + z.n + " " + where;
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

// Speech: Thai voice when the browser has one; silently does nothing otherwise.
// Messages are QUEUED, never cut off mid-sentence. If several are waiting (fast simulation), only the newest
// message per group (e.g. one numbered point) is kept, so the voice does not fall behind the car.
const queue = [];
let speaking = false;

function playNext() {
  if (speaking || !queue.length) return;
  const { text } = queue.shift();
  const u = new SpeechSynthesisUtterance(text);
  u.lang = "th-TH";
  const v = window.speechSynthesis.getVoices().find((x) => /^th/i.test(x.lang));
  if (v) u.voice = v;
  u.rate = 1.0;
  speaking = true;
  const done = () => { speaking = false; playNext(); };
  u.onend = done;
  u.onerror = done;
  window.speechSynthesis.speak(u);
}

export function speak(text, muted, group) {
  try {
    if (muted || typeof window === "undefined" || !window.speechSynthesis) return false;
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
  speaking = false;
  try { if (window.speechSynthesis) window.speechSynthesis.cancel(); } catch (_) { /* ignore */ }
}
