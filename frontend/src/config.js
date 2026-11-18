// Runtime configuration. External services are public demos for this local prototype only (no SLA).

function resolveApiBase() {
  const param = new URLSearchParams(window.location.search).get("api");
  if (param) {
    try {
      const url = new URL(param);
      if (url.protocol === "http:" || url.protocol === "https:") return url.origin + url.pathname.replace(/\/+$/, "");
    } catch (_) { /* default */ }
  }
  return (import.meta.env && import.meta.env.VITE_API_BASE) || "http://127.0.0.1:8000";
}

export const CONFIG = {
  apiBase: resolveApiBase(),
  photonUrl: "https://photon.komoot.io/api/",
  osrmUrl: "https://router.project-osrm.org/route/v1/driving/",
  // Real basemap: OpenStreetMap standard tiles (Thai place and road names, no API key).
  // Follow https://operations.osmfoundation.org/policies/tiles/ — fine for this local prototype; use your own
  // tile server or a keyed provider for production.
  tileUrl: "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
  tileSubdomains: "abc",
  tileAttribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  boundaryUrl: "/assets/thailand-boundary.geojson",
  apiTimeoutMs: 30000,
  externalTimeoutMs: 15000,
  geocodeMinIntervalMs: 1100,
  segmentPageSize: 500,
  predictionBatch: 128,
  historyLookbackDays: 1827,
  snapWarnM: 300,
  zoneGapM: 1500,       // high-level segments closer than this along the route form one zone
  maxZones: 5,
  ribbonBins: 240,
};

export const ENVELOPE = { west: 97.0, south: 5.0, east: 106.0, north: 21.0 };
export const THAI_BOUNDS = [[5.6, 97.3], [20.5, 105.65]];
// Neighbouring countries stay visible (dimmed + blurred) but the view cannot travel further than this.
export const MAX_BOUNDS = [[4.4, 95.6], [21.6, 107.2]];
export const DATE_MIN = "2024-01-01";
export const DATE_MAX = "2027-12-31";
export const LAST_OBSERVED_DATE = "2025-12-31";

// API colour key → what travellers see. Order matters (rank).
export const LEVELS = {
  red:    { rank: 4, label: "ระวังมาก", hex: "#C8372D", ink: "#FFFFFF", soft: "#F8E1DE" },
  orange: { rank: 3, label: "ระวัง", hex: "#E8821E", ink: "#3D1F00", soft: "#FBE6CF" },
  yellow: { rank: 2, label: "ปานกลาง", hex: "#E9B92F", ink: "#3A2C00", soft: "#FBF0CF" },
  base:   { rank: 1, label: "ปกติ", hex: "#7FA3C4", ink: "#0F1B2D", soft: "#E5EDF4" },
};
export const UNKNOWN_HEX = "#9AA3AF";
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
