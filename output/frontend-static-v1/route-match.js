"use strict";

// RoadAware — conservative matching of model road segments (≈2 km DOH segments) to a driving route.
//
// Rule (documented in README):
//   1. Sample each segment along its own geometry every SAMPLE_STEP_M metres (plus both ends).
//   2. A sample is "on the route" when it lies within BUFFER_M metres of the route polyline.
//   3. The segment is matched only when at least MIN_FRACTION of its samples are on the route.
// A crossing road or a parallel road far from the route therefore does not inherit a forecast.
// The match is an approximate spatial linkage for display, never navigation-grade coverage.
//
// Pure functions, no DOM: loaded by the browser (window.RouteMatch) and by Node for tests.

(function (root) {
  const SAMPLE_STEP_M = 100;
  const BUFFER_M = 50;
  const MIN_FRACTION = 0.5;
  const CELL_M = 250;

  function makeProjection(lat0) {
    const kx = 111320 * Math.cos((lat0 * Math.PI) / 180);
    const ky = 110540;
    return {
      fwd: (lon, lat) => [lon * kx, lat * ky],
      inv: (x, y) => [x / kx, y / ky],
    };
  }

  // routeCoords: [[lon, lat], ...] from OSRM GeoJSON.
  function buildRouteIndex(routeCoords) {
    if (!Array.isArray(routeCoords) || routeCoords.length < 2) throw new Error("route needs >= 2 points");
    let minLon = Infinity, minLat = Infinity, maxLon = -Infinity, maxLat = -Infinity;
    for (const [lon, lat] of routeCoords) {
      if (lon < minLon) minLon = lon; if (lon > maxLon) maxLon = lon;
      if (lat < minLat) minLat = lat; if (lat > maxLat) maxLat = lat;
    }
    const proj = makeProjection((minLat + maxLat) / 2);
    const pts = routeCoords.map(([lon, lat]) => proj.fwd(lon, lat));
    const cum = new Float64Array(pts.length);
    for (let i = 1; i < pts.length; i++) {
      cum[i] = cum[i - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]);
    }
    const grid = new Map();
    for (let i = 0; i < pts.length - 1; i++) {
      const [x1, y1] = pts[i], [x2, y2] = pts[i + 1];
      const cx0 = Math.floor((Math.min(x1, x2) - BUFFER_M) / CELL_M), cx1 = Math.floor((Math.max(x1, x2) + BUFFER_M) / CELL_M);
      const cy0 = Math.floor((Math.min(y1, y2) - BUFFER_M) / CELL_M), cy1 = Math.floor((Math.max(y1, y2) + BUFFER_M) / CELL_M);
      for (let cx = cx0; cx <= cx1; cx++) {
        for (let cy = cy0; cy <= cy1; cy++) {
          const key = cx + "," + cy;
          let list = grid.get(key);
          if (!list) { list = []; grid.set(key, list); }
          list.push(i);
        }
      }
    }
    const padLat = BUFFER_M / 110540, padLon = BUFFER_M / (111320 * Math.cos(((minLat + maxLat) / 2) * Math.PI / 180));
    return {
      proj, pts, cum, grid,
      length: cum[cum.length - 1],
      bbox: { west: minLon - padLon, south: minLat - padLat, east: maxLon + padLon, north: maxLat + padLat },
    };
  }

  // Distance (m) from projected point to the route, and distance along the route of the closest point.
  function nearestOnRoute(index, x, y) {
    const list = index.grid.get(Math.floor(x / CELL_M) + "," + Math.floor(y / CELL_M));
    if (!list) return null;
    let best = null;
    for (const i of list) {
      const [x1, y1] = index.pts[i], [x2, y2] = index.pts[i + 1];
      const dx = x2 - x1, dy = y2 - y1;
      const len2 = dx * dx + dy * dy;
      let t = len2 > 0 ? ((x - x1) * dx + (y - y1) * dy) / len2 : 0;
      t = Math.max(0, Math.min(1, t));
      const px = x1 + t * dx, py = y1 + t * dy;
      const d = Math.hypot(x - px, y - py);
      if (!best || d < best.d) best = { d, along: index.cum[i] + t * Math.sqrt(len2) };
    }
    return best;
  }

  function lineParts(geometry) {
    if (!geometry) return [];
    if (geometry.type === "LineString") return [geometry.coordinates];
    if (geometry.type === "MultiLineString") return geometry.coordinates;
    return [];
  }

  function featureBbox(parts) {
    let w = Infinity, s = Infinity, e = -Infinity, n = -Infinity;
    for (const line of parts) for (const [lon, lat] of line) {
      if (lon < w) w = lon; if (lon > e) e = lon;
      if (lat < s) s = lat; if (lat > n) n = lat;
    }
    return { west: w, south: s, east: e, north: n };
  }

  function bboxOverlap(a, b) {
    return a.west <= b.east && a.east >= b.west && a.south <= b.north && a.north >= b.south;
  }

  // Samples every SAMPLE_STEP_M along each part, including both ends. Returns projected [x, y].
  function samplePoints(index, parts) {
    const out = [];
    for (const line of parts) {
      if (!Array.isArray(line) || line.length === 0) continue;
      const p = line.map(([lon, lat]) => index.proj.fwd(lon, lat));
      out.push(p[0]);
      let carry = 0;
      for (let i = 1; i < p.length; i++) {
        const [x1, y1] = p[i - 1], [x2, y2] = p[i];
        const segLen = Math.hypot(x2 - x1, y2 - y1);
        let pos = SAMPLE_STEP_M - carry;
        while (pos <= segLen) {
          const t = pos / segLen;
          out.push([x1 + t * (x2 - x1), y1 + t * (y2 - y1)]);
          pos += SAMPLE_STEP_M;
        }
        carry = segLen - (pos - SAMPLE_STEP_M);
      }
      const last = p[p.length - 1];
      const prev = out[out.length - 1];
      if (!prev || Math.hypot(prev[0] - last[0], prev[1] - last[1]) > 1) out.push(last);
    }
    return out;
  }

  // Returns null (not matched) or { fraction, along, anchor: [lat, lon], samples }.
  function matchFeature(index, feature) {
    const parts = lineParts(feature && feature.geometry);
    if (parts.length === 0) return null;
    if (!bboxOverlap(featureBbox(parts), index.bbox)) return null;
    const samples = samplePoints(index, parts);
    if (samples.length === 0) return null;
    const onRoute = [];
    for (const [x, y] of samples) {
      const r = nearestOnRoute(index, x, y);
      if (r && r.d <= BUFFER_M) onRoute.push({ x, y, along: r.along });
    }
    const fraction = onRoute.length / samples.length;
    if (fraction < MIN_FRACTION) return null;
    onRoute.sort((a, b) => a.along - b.along);
    const mid = onRoute[Math.floor(onRoute.length / 2)];
    const [lon, lat] = index.proj.inv(mid.x, mid.y);
    return { fraction, along: mid.along, anchor: [lat, lon], samples: samples.length };
  }

  // Ray-casting point-in-polygon for a GeoJSON (Multi)Polygon; used for the Thailand display boundary.
  function pointInRings(lon, lat, rings) {
    let inside = false;
    for (const ring of rings) {
      for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
        const [xi, yi] = ring[i], [xj, yj] = ring[j];
        if ((yi > lat) !== (yj > lat) && lon < ((xj - xi) * (lat - yi)) / (yj - yi) + xi) inside = !inside;
      }
    }
    return inside;
  }

  function pointInGeometry(lon, lat, geometry) {
    if (!geometry) return false;
    if (geometry.type === "Polygon") return pointInRings(lon, lat, geometry.coordinates);
    if (geometry.type === "MultiPolygon") return geometry.coordinates.some((poly) => pointInRings(lon, lat, poly));
    return false;
  }

  const api = {
    SAMPLE_STEP_M, BUFFER_M, MIN_FRACTION,
    buildRouteIndex, matchFeature, nearestOnRoute, pointInGeometry,
  };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.RouteMatch = api;
})(typeof window !== "undefined" ? window : globalThis);
