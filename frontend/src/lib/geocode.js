// Place search via the Photon public demo (komoot). Explicit searches only, serialised to ≤ 1 request/~1.1 s
// across both fields, cached per query, Thailand-only results. Never auto-picks a result for the user.
import { CONFIG, ENVELOPE } from "../config.js";
import { fetchJson, isNum, sleep, RequestFailure } from "./util.js";

const OSM_TYPE_TH = {
  university: "มหาวิทยาลัย", college: "วิทยาลัย", school: "โรงเรียน", national_park: "อุทยานแห่งชาติ", protected_area: "พื้นที่คุ้มครอง",
  peak: "ยอดเขา", hospital: "โรงพยาบาล", city: "เมือง", town: "เมือง", village: "หมู่บ้าน", station: "สถานี", aerodrome: "สนามบิน",
  mall: "ห้างสรรพสินค้า", hotel: "โรงแรม", attraction: "สถานที่ท่องเที่ยว", viewpoint: "จุดชมวิว", waterfall: "น้ำตก",
};

const cache = new Map();
let chain = Promise.resolve();
let lastAt = 0;

export function geocode(query, signal) {
  const key = query.trim().toLowerCase();
  if (cache.has(key)) return Promise.resolve(cache.get(key));
  const run = async () => {
    if (signal.aborted) throw new RequestFailure("aborted");
    const wait = lastAt + CONFIG.geocodeMinIntervalMs - Date.now();
    if (wait > 0) await sleep(wait);
    if (signal.aborted) throw new RequestFailure("aborted");
    lastAt = Date.now();
    const url = CONFIG.photonUrl + "?q=" + encodeURIComponent(query.trim()) + "&limit=8&bbox=97,5,106,21";
    const places = parsePhoton(await fetchJson(url, { signal }));
    cache.set(key, places);
    return places;
  };
  const p = chain.then(run, run);
  chain = p.catch(() => {});
  return p;
}

export function parsePhoton(json) {
  const out = [];
  const seen = new Set();
  for (const f of Array.isArray(json.features) ? json.features : []) {
    const pr = (f && f.properties) || {};
    const c = f && f.geometry && Array.isArray(f.geometry.coordinates) ? f.geometry.coordinates : null;
    if (!c || !isNum(c[0]) || !isNum(c[1]) || pr.countrycode !== "TH") continue;
    const [lon, lat] = c;
    if (lon < ENVELOPE.west || lon > ENVELOPE.east || lat < ENVELOPE.south || lat > ENVELOPE.north) continue;
    const name = String(pr.name || pr.street || pr.city || "สถานที่ไม่มีชื่อ");
    const sub = [];
    const kind = OSM_TYPE_TH[pr.osm_value];
    if (kind && !name.includes(kind)) sub.push(kind);
    for (const k of ["street", "district", "city", "county", "state"]) {
      const v = pr[k];
      if (typeof v === "string" && v && v !== name && !sub.includes(v)) sub.push(v);
    }
    const id = name + "|" + lat.toFixed(4) + "|" + lon.toFixed(4);
    if (seen.has(id)) continue;
    seen.add(id);
    out.push({ id, name, sub: sub.slice(0, 4).join(" · "), lat, lon, source: "search" });
  }
  return out;
}
