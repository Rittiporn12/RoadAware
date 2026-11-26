// Runtime configuration. External services are public demos for this local prototype only (no SLA).

// Server address. Order: ?api= in the link (remembered in this browser) → remembered value → build-time default → local.
// Demo hosting: the site on GitHub Pages talks to the API on the presenter's Mac through a temporary https tunnel,
// e.g. https://rittiporn12.github.io/RoadAware/?api=https://xxxx.trycloudflare.com  ("Start Demo Server.command" prints this link).
function cleanUrl(v) {
  try {
    const url = new URL(v);
    if (url.protocol === "https:" || url.protocol === "http:") return url.origin + url.pathname.replace(/\/+$/, "");
  } catch (_) { /* invalid */ }
  return null;
}
function resolveUrl(param, storeKey, fallback) {
  let fromLink = null, stored = null;
  try { fromLink = cleanUrl(new URLSearchParams(window.location.search).get(param) || ""); } catch (_) { /* ignore */ }
  try {
    if (fromLink) window.localStorage.setItem(storeKey, fromLink);
    else stored = cleanUrl(window.localStorage.getItem(storeKey) || "");
  } catch (_) { /* storage blocked: link value still used */ }
  return fromLink || stored || fallback;
}
const ENV = (import.meta.env) || {};
const onLocalhost = typeof window !== "undefined" && /^(127\.0\.0\.1|localhost|192\.168\.|10\.)/.test(window.location.hostname);
function resolveApiBase() {
  // on the developer's own machine the local API always wins (a remembered tunnel would be stale)
  if (onLocalhost && !new URLSearchParams(window.location.search).get("api")) return ENV.VITE_API_BASE || "http://127.0.0.1:8000";
  return resolveUrl("api", "roadaware.api", ENV.VITE_API_BASE || "http://127.0.0.1:8000");
}
function resolveTtsUrl() {
  if (onLocalhost && !new URLSearchParams(window.location.search).get("tts")) return ENV.VITE_TTS_URL || "http://127.0.0.1:8010";
  return resolveUrl("tts", "roadaware.tts", ENV.VITE_TTS_URL || "http://127.0.0.1:8010");
}

export const CONFIG = {
  apiBase: resolveApiBase(),
  photonUrl: "https://photon.komoot.io/api/",
  ttsUrl: resolveTtsUrl(), // local Gemini voice proxy (backend/scripts/tts_proxy.py); optional
  osrmUrl: "https://router.project-osrm.org/route/v1/driving/",
  // Real basemap: OpenStreetMap standard tiles (Thai place and road names, no API key).
  // Follow https://operations.osmfoundation.org/policies/tiles/ — fine for this local prototype; use your own
  // tile server or a keyed provider for production.
  tileUrl: "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
  tileSubdomains: "abc",
  tileAttribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  boundaryUrl: (ENV.BASE_URL || "/") + "assets/thailand-boundary.geojson", // works under /RoadAware/ on GitHub Pages
  apiTimeoutMs: 30000,
  externalTimeoutMs: 15000,
  geocodeMinIntervalMs: 1100,
  segmentPageSize: 500,
  predictionBatch: 128,
  historyLookbackDays: 1827,
  snapWarnM: 300,
  // ช่วงเสี่ยงที่ห่างกันไม่เกิน 1,500 ม. รวมเป็นจุดเดียว
  zoneGapM: 1500,       // hotspot segments closer than this along the route form one zone
  // จุดเสี่ยงต้องอยู่ใน 20% บนสุดของเส้นทาง
  hotspotQuantile: 0.8, // trip hotspot = national level สูง/สูงมาก AND in the top 20% of this route's evaluated segments
  // แสดงไม่เกิน 5 จุดต่อ 500 กม.
  maxZones: 5,          // per ~500 km of route, capped by maxZonesCap
  // และไม่เกิน 10 จุดต่อเส้นทาง
  maxZonesCap: 10,
  altMaxTimeRatio: 1.35,   // alternative routes kept when their driving time is ≤ 35% longer
  altMinCoverage: 0.7,     // below this an alternative is mostly unevaluated → never called better
  ribbonBins: 240,
};

// ---- Demo server discovery (GitHub Pages only) -------------------------------------------------------------
// "Start Demo Server.command" publishes the Mac's current tunnel address to endpoint.json on the repo's
// demo-endpoint branch every time it starts (and {"online": false} when it stops). The site reads it on load,
// so the plain address https://<user>.github.io/<repo>/ always talks to the server that is running right now —
// no ?api= link to copy. The published address wins over an old ?api= link or a remembered value.
function endpointSources() {
  if (ENV.VITE_ENDPOINT_URL) return [ENV.VITE_ENDPOINT_URL];
  if (typeof window === "undefined") return [];
  const m = window.location.hostname.match(/^([a-z0-9-]+)\.github\.io$/i);
  const repo = window.location.pathname.split("/").filter(Boolean)[0];
  if (!m || !repo) return [];
  return [
    `https://api.github.com/repos/${m[1]}/${repo}/contents/endpoint.json?ref=demo-endpoint`,
    `https://raw.githubusercontent.com/${m[1]}/${repo}/demo-endpoint/endpoint.json`,
  ];
}
function remember(key, v) { try { window.localStorage.setItem(key, v); } catch (_) { /* storage blocked */ } }
let discovery = null;
// Resolves to { source: "local" | "published" | "link", offline?: true, updated?: string }. Runs once per page load.
// หาที่อยู่ของเซิร์ฟเวอร์ API อัตโนมัติ
export function discoverServer() {
  // ถ้าหาไปแล้ว ใช้ผลเดิม
  if (discovery) return discovery;
  // เริ่มค้นหา (ทำครั้งเดียว)
  discovery = (async () => {
    // แหล่งที่อยู่ (ไฟล์ endpoint.json บน branch demo-endpoint) ถ้ารันบนเครื่องตัวเองไม่ต้องหา
    const sources = onLocalhost ? [] : endpointSources();
    // ไม่มีแหล่ง → ใช้เซิร์ฟเวอร์บนเครื่อง
    if (!sources.length) return { source: "local" };
    // ลองทีละแหล่ง
    for (const url of sources) {
      try {
        // ยกเลิกถ้ารอเกิน 5 วินาที
        const ctrl = new AbortController();
        const timer = setTimeout(() => ctrl.abort(), 5000);
        // อ่านไฟล์ (ใส่เวลาต่อท้ายกันการ cache)
        const r = await fetch(url + (url.includes("?") ? "&" : "?") + "t=" + Date.now(), {
          cache: "no-store", signal: ctrl.signal,
          // ถ้าอ่านผ่าน GitHub API ขอเนื้อไฟล์ดิบ
          headers: url.includes("api.github.com") ? { Accept: "application/vnd.github.raw+json" } : {},
        });
        // ยกเลิกตัวจับเวลา
        clearTimeout(timer);
        // อ่านไม่ได้ → ลองแหล่งถัดไป
        if (!r.ok) continue;
        // แปลงเป็น JSON
        const j = await r.json();
        // ไฟล์บอกว่าเซิร์ฟเวอร์ปิดอยู่ → แสดงสถานะออฟไลน์
        if (j && j.online === false) return { source: "published", offline: true, updated: j.updated };
        // ที่อยู่ API (ลิงก์ Cloudflare tunnel)
        const api = cleanUrl((j && j.api) || "");
        // ต้องเป็น https เท่านั้น
        if (!api || !api.startsWith("https://")) continue;
        // ตั้งค่าที่อยู่ API และจำไว้ในเบราว์เซอร์
        CONFIG.apiBase = api; remember("roadaware.api", api);
        // ที่อยู่บริการเสียงพูด
        const tts = cleanUrl((j && j.tts) || "");
        // ตั้งค่าบริการเสียง
        if (tts && tts.startsWith("https://")) { CONFIG.ttsUrl = tts; remember("roadaware.tts", tts); }
        // สำเร็จ
        return { source: "published", updated: j.updated };
      // ผิดพลาด → ลองแหล่งถัดไป
      } catch (_) { /* try the next source */ }
    }
    // หาไม่ได้ → ใช้ที่อยู่จากลิงก์ (?api=) หรือที่จำไว้
    return { source: "link" }; // nothing published: keep ?api= / remembered value
  })();
  // คืนผลการค้นหา
  return discovery;
}

export const ENVELOPE = { west: 97.0, south: 5.0, east: 106.0, north: 21.0 };
export const THAI_BOUNDS = [[5.6, 97.3], [20.5, 105.65]];
// Neighbouring countries stay visible (dimmed + blurred) but the view cannot travel further than this.
export const MAX_BOUNDS = [[4.4, 95.6], [21.6, 107.2]];
export const DATE_MIN = "2024-01-01";
export const DATE_MAX = "2027-12-31";
export const LAST_OBSERVED_DATE = "2025-12-31";

// API colour key = the NATIONAL level: where this segment's predicted recorded density sits among all
// segment x time cells in Thailand (2022-23 reference). Order matters (rank).
export const LEVELS = {
  red:    { rank: 4, label: "สูงมาก", nat: "5% บนสุดของประเทศ", hex: "#C8372D", ink: "#FFFFFF", soft: "#F8E1DE" },
  orange: { rank: 3, label: "สูง", nat: "5–20% บนสุด", hex: "#E8821E", ink: "#3D1F00", soft: "#FBE6CF" },
  yellow: { rank: 2, label: "ปานกลาง", nat: "20–50% บนสุด", hex: "#E9B92F", ink: "#3A2C00", soft: "#FBF0CF" },
  base:   { rank: 1, label: "ต่ำกว่าครึ่งประเทศ", nat: "ครึ่งล่างของประเทศ", hex: "#7FA3C4", ink: "#0F1B2D", soft: "#E5EDF4" },
};
export const UNKNOWN_HEX = "#B9C1CC"; // local / city roads the model does not cover yet (solid, quiet — not a risk colour)
export const ROUTE_HEX = "#3E5C86";   // evaluated route (trip view) — neutral, not a risk colour
// Trip view shading: lower half / middle / upper fifth of THIS trip (one blue hue, light → dark). Red is kept for numbered points.
export const TRIP_TIERS = [{ upTo: 0.5, hex: "#8DB0E3", label: "ต่ำ" }, { upTo: 0.8, hex: "#4C76B8", label: "กลาง" }, { upTo: 1.01, hex: "#1E3460", label: "สูง" }];
export const tripTierHex = (rank) => (TRIP_TIERS.find((t) => rank < t.upTo) || TRIP_TIERS[TRIP_TIERS.length - 1]).hex;
export const HOT_HEX = "#C8372D";     // numbered trip hotspots
export const LEVEL_ORDER = ["red", "orange", "yellow", "base"];
export const ZONE_LEVELS = ["red", "orange"];

export const BLOCKS = ["00-06", "06-12", "12-18", "18-24"];
export const BLOCK_LABEL = { "00-06": "00:00–06:00 น.", "06-12": "06:00–12:00 น.", "12-18": "12:00–18:00 น.", "18-24": "18:00–24:00 น." };
export const DEPART_OPTIONS = [
  { time: "06:00", part: "เช้า" },
  { time: "11:00", part: "สาย" },
  { time: "16:00", part: "บ่าย" },
  { time: "21:00", part: "ค่ำ" },
];
