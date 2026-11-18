// Runtime configuration. External services are public demos for this local prototype only (no SLA).

function resolveApiBase() {
  const param = new URLSearchParams(window.location.search).get("api");
  if (param) {
    try {
      const url = new URL(param);
      if (url.protocol === "http:" || url.protocol === "https:") return url.origin + url.pathname.replace(/\/+$/, "");
    } catch (_) { /* default */ }
  }
  return import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";
}

export const CONFIG = {
  apiBase: resolveApiBase(),
  photonUrl: "https://photon.komoot.io/api/",
  osrmUrl: "https://router.project-osrm.org/route/v1/driving/",
  boundaryUrl: "/assets/thailand-boundary.geojson",
  apiTimeoutMs: 30000,
  externalTimeoutMs: 15000,
  geocodeMinIntervalMs: 1100,
  segmentPageSize: 500,
  predictionBatch: 128,
  historyLookbackDays: 1827,
  groupWithinM: 600,
  snapWarnM: 300,
};

export const ENVELOPE = { west: 97.0, south: 5.0, east: 106.0, north: 21.0 };
export const THAI_BOUNDS = [[5.6, 97.3], [20.5, 105.65]];
export const MAX_BOUNDS = [[4.6, 96.2], [21.4, 106.7]];
export const DATE_MIN = "2024-01-01";
export const DATE_MAX = "2027-12-31";
export const LAST_OBSERVED_DATE = "2025-12-31";

export const LEVELS = {
  red:    { rank: 4, title: "เฝ้าระวังสูงสุด", desc: "อยู่ใน 5% บนของค่าอ้างอิง (จัดอันดับเชิงเปรียบเทียบ ไม่ใช่ความเสี่ยงสัมบูรณ์)", radius: 13, hex: "#c62828" },
  orange: { rank: 3, title: "เฝ้าระวังสูง", desc: "อยู่ช่วงเปอร์เซ็นไทล์ที่ 80–95 ของค่าอ้างอิง", radius: 11, hex: "#f07c1b" },
  yellow: { rank: 2, title: "ปานกลาง", desc: "สูงกว่าค่ากลาง (เปอร์เซ็นไทล์ที่ 50–80 ของค่าอ้างอิง)", radius: 9, hex: "#f2c418" },
  base:   { rank: 1, title: "ต่ำกว่าค่ากลาง", desc: "ต่ำกว่าค่ามัธยฐานของค่าอ้างอิง — ไม่ได้แปลว่าปลอดภัย", radius: 7, hex: "#2c7fb8" },
};
export const LEVEL_ORDER = ["red", "orange", "yellow", "base"];
export const BLOCKS = ["00-06", "06-12", "12-18", "18-24"];
export const BLOCK_LABEL = { "00-06": "00:00–06:00 น.", "06-12": "06:00–12:00 น.", "12-18": "12:00–18:00 น.", "18-24": "18:00–24:00 น." };
export const CATEGORY_TH = { weather: "สภาพอากาศขณะเกิดเหตุ", accident_type: "ลักษณะการชน/เหตุ", presumed_cause: "สาเหตุที่สันนิษฐานในบันทึก" };
