// Convert a detailed Thailand ADM0 boundary (e.g. geoBoundaries-THA-ADM0_simplified.geojson) into the
// light display asset the map uses: public/assets/thailand-boundary.geojson
//
//   node scripts/prepare-boundary.mjs scripts/source/geoBoundaries-THA-ADM0_simplified.geojson
//
// Steps: keep every polygon outer ring (islands included, slivers < MIN_AREA_KM2 dropped),
// Douglas–Peucker simplify at TOL_DEG (~80 m), round to 5 decimals. Display use only — not a legal boundary.
import { readFileSync, writeFileSync } from "node:fs";

const TOL_DEG = 0.0007;
const MIN_AREA_KM2 = 0.3;

const src = process.argv[2];
const out = process.argv[3] || "public/assets/thailand-boundary.geojson";
if (!src) { console.error("usage: node scripts/prepare-boundary.mjs <input.geojson> [output.geojson]"); process.exit(1); }

const gj = JSON.parse(readFileSync(src, "utf8"));
const geoms = gj.type === "FeatureCollection" ? gj.features.map((f) => f.geometry) : [gj.type === "Feature" ? gj.geometry : gj];

function sqSegDist(p, a, b) {
  let x = a[0], y = a[1], dx = b[0] - x, dy = b[1] - y;
  if (dx !== 0 || dy !== 0) {
    const t = ((p[0] - x) * dx + (p[1] - y) * dy) / (dx * dx + dy * dy);
    if (t > 1) { x = b[0]; y = b[1]; } else if (t > 0) { x += dx * t; y += dy * t; }
  }
  dx = p[0] - x; dy = p[1] - y;
  return dx * dx + dy * dy;
}
function simplify(pts, tol) {
  if (pts.length <= 4) return pts;
  const sq = tol * tol, keep = new Uint8Array(pts.length);
  keep[0] = keep[pts.length - 1] = 1;
  const stack = [[0, pts.length - 1]];
  while (stack.length) {
    const [a, b] = stack.pop();
    let max = 0, idx = -1;
    for (let i = a + 1; i < b; i++) { const d = sqSegDist(pts[i], pts[a], pts[b]); if (d > max) { max = d; idx = i; } }
    if (max > sq) { keep[idx] = 1; stack.push([a, idx], [idx, b]); }
  }
  return pts.filter((_, i) => keep[i]);
}
function areaKm2(ring) {
  let s = 0;
  const lat0 = ring[0][1] * Math.PI / 180;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) s += (ring[j][0] + ring[i][0]) * (ring[j][1] - ring[i][1]);
  return Math.abs(s / 2) * 111.32 * 111.32 * Math.cos(lat0);
}

const polys = [];
let inPts = 0, outPts = 0, dropped = 0;
for (const g of geoms) {
  const list = g.type === "Polygon" ? [g.coordinates] : g.type === "MultiPolygon" ? g.coordinates : [];
  for (const poly of list) {
    const ring = poly[0];
    inPts += ring.length;
    if (areaKm2(ring) < MIN_AREA_KM2) { dropped++; continue; }
    let s = simplify(ring, TOL_DEG).map(([x, y]) => [Math.round(x * 1e5) / 1e5, Math.round(y * 1e5) / 1e5]);
    if (s.length < 4) continue;
    const [f, l] = [s[0], s[s.length - 1]];
    if (f[0] !== l[0] || f[1] !== l[1]) s.push([f[0], f[1]]);
    outPts += s.length;
    polys.push([s]);
  }
}
const fc = {
  type: "FeatureCollection",
  features: [{
    type: "Feature",
    properties: {
      name: "Thailand",
      source: "geoBoundaries gbOpen THA ADM0 (simplified), further simplified for display",
      source_url: "https://www.geoboundaries.org/",
      license: "CC BY 4.0 (attribution: geoBoundaries)",
      purpose: "display mask / map click restriction only; not a legal boundary or road coverage data",
    },
    geometry: { type: "MultiPolygon", coordinates: polys },
  }],
};
writeFileSync(out, JSON.stringify(fc));
console.log(`polygons ${polys.length} (dropped ${dropped} slivers) · points ${inPts} → ${outPts} · wrote ${out}`);
