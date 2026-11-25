// Leaflet map.
//  • Thailand is drawn sharp: a second copy of the basemap is clipped to the country outline (public/assets).
//  • Neighbouring countries stay visible underneath, blurred, desaturated and lightly tinted.
//  • Panning is locked to a frame just around Thailand; the minimum zoom keeps the whole country in view.
//  • Route: grey = no forecast coverage. Trip view: one blue = evaluated, red + number = this trip's points to watch.
//    National view: each segment in its national level colour.
import { useEffect, useRef, useState } from "react";
import * as L from "leaflet";
import "leaflet/dist/leaflet.css";
import { CONFIG, THAI_BOUNDS, MAX_BOUNDS, ENVELOPE, LEVELS, UNKNOWN_HEX, ROUTE_HEX, HOT_HEX, tripTierHex } from "../config.js";
import { pointInGeometry } from "../lib/routeMatch.js";
import { pointAt } from "../lib/drive.js";

const isMobile = () => window.matchMedia("(max-width: 900px)").matches;

function pinIcon(letter) {
  return L.divIcon({ className: "pin-icon pin-icon-" + letter.toLowerCase(), html: "<span><b>" + letter + "</b></span>", iconSize: [32, 32], iconAnchor: [16, 36] });
}
function zoneIcon(n, level, selected, mode, clock) {
  const size = selected ? 42 : 34;
  const m = /(\d{1,2}:\d{2})/.exec(String(clock || ""));
  const t = m ? "<em>" + m[1] + " น.</em>" : "";
  return L.divIcon({
    className: "zone-icon zone-" + (level === "red" ? "red" : "orange") + (selected ? " is-selected" : ""), // red = สูงมาก, orange = สูง
    html: "<span>" + Number(n) + "</span>" + t, // number + the time you pass it
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
}

export default function MapView({ route, origin, dest, items, zones, hotIds, rankById, mode, altFocus, onSelectAlt, drivePos, selectedKey, focus, pick, getPadding, onPick, onOutside, onSelectZone, onFailed }) {
  const divRef = useRef(null);
  const mapRef = useRef(null);
  const layers = useRef({});
  const boundaryRef = useRef(null);
  const handlers = useRef({});
  handlers.current = { onPick, onOutside, onSelectZone, onSelectAlt, pick };
  const [tileWarn, setTileWarn] = useState(false);
  const [zoomTick, setZoomTick] = useState(0);

  // ---- create the map once
  useEffect(() => {
    let m;
    try {
      m = L.map(divRef.current, {
        zoomControl: false, maxBoundsViscosity: 1.0, worldCopyJump: false,
        maxZoom: 18, zoomAnimation: false, attributionControl: true,
        // quarter-step zoom: a small trackpad pinch / wheel nudge still zooms instead of rounding back to the same level
        zoomSnap: 0.25, wheelPxPerZoomLevel: 80,
      });
    } catch (_) {
      if (onFailed) onFailed();
      return undefined;
    }
    // Safari on a Mac sends trackpad pinches as gesture events (not wheel events), which Leaflet ignores.
    if (typeof window !== "undefined" && window.GestureEvent && !("ontouchstart" in window)) {
      let z0 = null;
      const el = divRef.current;
      el.addEventListener("gesturestart", (e) => { e.preventDefault(); z0 = m.getZoom(); });
      el.addEventListener("gesturechange", (e) => {
        e.preventDefault();
        if (z0 == null) return;
        const z = z0 + Math.log2(e.scale || 1);
        if (Math.abs(z - m.getZoom()) >= 0.25) m.setZoom(z, { animate: false });
      });
      el.addEventListener("gestureend", (e) => { e.preventDefault(); z0 = null; });
    }
    L.control.zoom({ position: "topright", zoomInTitle: "ซูมเข้า", zoomOutTitle: "ซูมออก" }).addTo(m);

    const pane = (name, z) => { const p = m.createPane(name); p.style.zIndex = String(z); return p; };
    pane("tilesBlur", 200).classList.add("pane-blur");
    const thaiPane = pane("tilesThai", 210);
    pane("outside", 220);
    pane("border", 230).style.pointerEvents = "none";
    pane("altPane", 405);
    pane("routePane", 410).style.pointerEvents = "none";
    pane("segPane", 420).style.pointerEvents = "none";

    let tileErrors = 0;
    const tileOpts = { maxZoom: 18, subdomains: CONFIG.tileSubdomains, detectRetina: false };
    L.tileLayer(CONFIG.tileUrl, { ...tileOpts, pane: "tilesBlur", attribution: CONFIG.tileAttribution })
      .on("tileerror", () => { tileErrors += 1; if (tileErrors >= 6) setTileWarn(true); })
      .on("tileload", () => setTileWarn(false))
      .addTo(m);
    // Same URL → served from the browser cache, so Thailand costs no extra tile requests.
    L.tileLayer(CONFIG.tileUrl, { ...tileOpts, pane: "tilesThai" }).addTo(m);

    layers.current = {
      alts: L.layerGroup().addTo(m),
      route: L.layerGroup().addTo(m),
      seg: L.layerGroup().addTo(m),
      zones: L.layerGroup().addTo(m),
      ends: L.layerGroup().addTo(m),
      car: L.layerGroup().addTo(m),
    };

    // Clip the sharp copy to Thailand. Layer-point coordinates only change on zoom / view reset.
    const updateClip = () => {
      const geom = boundaryRef.current;
      if (!geom) return;
      const polys = geom.type === "Polygon" ? [geom.coordinates] : geom.coordinates;
      let d = "";
      for (const poly of polys) {
        const ring = poly[0];
        ring.forEach(([lon, lat], i) => {
          const p = m.latLngToLayerPoint([lat, lon]);
          d += (i === 0 ? "M" : "L") + p.x.toFixed(1) + " " + p.y.toFixed(1);
        });
        d += "Z";
      }
      thaiPane.style.clipPath = "path('" + d + "')";
      thaiPane.style.webkitClipPath = "path('" + d + "')";
    };
    m.on("zoomend viewreset", updateClip);

    // Minimum zoom = the whole country fits the map (on phones the sheet can be lowered to see it all).
    // Phones: the bottom sheet normally covers ~half the screen; keep the country above it.
    const sheetHeight = () => (isMobile() ? Math.round(window.innerHeight * 0.5) : 0);
    const thaiPadding = () => ({ paddingTopLeft: [16, isMobile() ? 60 : 24], paddingBottomRight: [16, 24] });
    // Lock: the min zoom shows the whole country; the pan limit is the frame around Thailand, grown just
    // enough that a tall phone screen at min zoom can still centre on Thailand.
    const updateLimits = (refit) => {
      m.invalidateSize();
      const p = thaiPadding();
      const total = L.point(p.paddingTopLeft).add(L.point(p.paddingBottomRight));
      const minZ = Math.max(4, Math.floor(m.getBoundsZoom(THAI_BOUNDS, false, total)));
      m.setMinZoom(minZ);
      m.setMaxBounds(null);
      const keep = refit ? null : { c: m.getCenter(), z: m.getZoom() };
      m.setView(L.latLngBounds(THAI_BOUNDS).getCenter(), minZ, { animate: false });
      const size = m.getSize();
      const sheet = sheetHeight();
      m.setMaxBounds(L.latLngBounds(MAX_BOUNDS).extend(m.getBounds())
        .extend(m.containerPointToLatLng([0, size.y + sheet])).extend(m.containerPointToLatLng([size.x, size.y + sheet])));
      if (keep) m.setView(keep.c, Math.max(keep.z, minZ), { animate: false });
    };
    const updateMinZoom = () => updateLimits(false);
    updateLimits(true);
    // On phones, place the country in the part of the map above the bottom sheet.
    m.fitBounds(THAI_BOUNDS, isMobile() ? { paddingTopLeft: [16, 60], paddingBottomRight: [16, sheetHeight() + 8] } : thaiPadding());
    m.on("zoomend", () => setZoomTick((t) => t + 1));
    window.addEventListener("resize", updateMinZoom);
    // The map card changes size when the route strip appears under it (desktop) — keep Leaflet in sync.
    let ro = null;
    if (typeof ResizeObserver !== "undefined") {
      ro = new ResizeObserver(() => m.invalidateSize({ pan: false }));
      ro.observe(divRef.current);
    }

    const inside = (lat, lon) => (boundaryRef.current
      ? pointInGeometry(lon, lat, boundaryRef.current)
      : lon >= ENVELOPE.west && lon <= ENVELOPE.east && lat >= ENVELOPE.south && lat <= ENVELOPE.north);
    m.on("click", (e) => {
      const h = handlers.current;
      if (!h.pick) return;
      if (!inside(e.latlng.lat, e.latlng.lng)) { h.onOutside(); return; }
      h.onPick(e.latlng.lat, e.latlng.lng);
    });

    let cancelled = false;
    fetch(CONFIG.boundaryUrl)
      .then((r) => r.json())
      .then((gj) => {
        if (cancelled) return;
        const geom = gj.type === "FeatureCollection" ? gj.features[0].geometry : gj.geometry;
        if (!geom || (geom.type !== "Polygon" && geom.type !== "MultiPolygon")) return;
        boundaryRef.current = geom;
        updateClip();
        const polys = geom.type === "Polygon" ? [geom.coordinates] : geom.coordinates;
        const world = [[-89, -179.9], [-89, 179.9], [89, 179.9], [89, -179.9]];
        const holes = polys.map((poly) => poly[0].map(([lon, lat]) => [lat, lon]));
        L.polygon([world, ...holes], { pane: "outside", stroke: false, fillColor: "#F3F4F5", fillOpacity: 0.45 })
          .on("click", (e) => { L.DomEvent.stop(e); handlers.current.onOutside(); })
          .addTo(m);
        L.geoJSON(geom, { pane: "border", interactive: false, style: { color: "#0F1B2D", weight: 10, opacity: 0.06, fill: false } }).addTo(m);
        L.geoJSON(geom, { pane: "border", interactive: false, style: { color: "#0B6E69", weight: 1.6, opacity: 0.75, fill: false } }).addTo(m);
      })
      .catch(() => { thaiPane.style.clipPath = "none"; });

    mapRef.current = m;
    return () => {
      cancelled = true;
      window.removeEventListener("resize", updateMinZoom);
      if (ro) ro.disconnect();
      m.remove();
      mapRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (divRef.current) divRef.current.classList.toggle("is-picking", !!pick);
  }, [pick]);

  // ---- endpoints
  useEffect(() => {
    const m = mapRef.current;
    if (!m) return;
    const g = layers.current.ends;
    g.clearLayers();
    const pts = [];
    for (const [p, letter, label] of [[origin, "A", "ต้นทาง: "], [dest, "B", "ปลายทาง: "]]) {
      if (!p) continue;
      const tip = document.createElement("span");
      tip.textContent = label + p.name;
      L.marker([p.lat, p.lon], { icon: pinIcon(letter), keyboard: false, zIndexOffset: 400 }).bindTooltip(tip).addTo(g);
      pts.push([p.lat, p.lon]);
    }
    if (!route) {
      if (pts.length === 2) m.fitBounds(L.latLngBounds(pts), { ...getPadding(), maxZoom: 12 });
      else if (pts.length === 1) m.setView(pts[0], Math.max(m.getZoom(), 10));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [origin, dest]);

  // ---- route line: grey dashed everywhere = unknown; forecast colours are drawn on top
  useEffect(() => {
    const m = mapRef.current;
    if (!m) return;
    const g = layers.current.route;
    g.clearLayers();
    if (!route) return;
    const latlngs = route.coords.map(([lon, lat]) => [lat, lon]);
    L.polyline(latlngs, { pane: "routePane", color: "#FFFFFF", weight: 12, opacity: 0.95, interactive: false, lineCap: "round", lineJoin: "round" }).addTo(g);
    L.polyline(latlngs, { pane: "routePane", color: UNKNOWN_HEX, weight: 5, opacity: 1, interactive: false, lineCap: "round", lineJoin: "round" }).addTo(g);
    m.fitBounds(L.latLngBounds(latlngs), getPadding());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [route]);

  // ---- alternative routes (similar time): quiet dashed lines under the main route; tap to compare in the panel
  useEffect(() => {
    const m = mapRef.current;
    if (!m) return;
    const g = layers.current.alts;
    g.clearLayers();
    // shown only when the person asks to see one (from a suggestion or the routes table): less to decode at first glance
    const list = ((route && !drivePos && route.alternatives) || []).filter((a) => a.id === altFocus);
    list.forEach((a) => {
      const i = route.alternatives.indexOf(a);
      const ll = a.coords.map(([lon, lat]) => [lat, lon]);
      const on = altFocus === a.id;
      L.polyline(ll, { pane: "altPane", color: "#FFFFFF", weight: on ? 11 : 9, opacity: 0.9, lineCap: "round", interactive: false }).addTo(g);
      const line = L.polyline(ll, { pane: "altPane", color: on ? "#6B3FA0" : "#7C8798", weight: on ? 6 : 4, opacity: on ? 0.95 : 0.8, dashArray: on ? "12 6" : "8 8", lineCap: "round" });
      line.bindTooltip("ทางเลือก " + (i + 1) + " · แตะเพื่อเทียบ", { sticky: true });
      line.on("click", () => handlers.current.onSelectAlt && handlers.current.onSelectAlt(a.id));
      line.addTo(g);
    });
    // show the whole comparison: main route + the alternative being looked at
    if (list.length && route) {
      const b = L.latLngBounds(route.coords.map(([lon, lat]) => [lat, lon]));
      list[0].coords.forEach(([lon, lat]) => b.extend([lat, lon]));
      m.fitBounds(b, getPadding());
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [route, altFocus, !!drivePos]);

  // ---- forecast colours on the route
  useEffect(() => {
    const m = mapRef.current;
    if (!m) return;
    const g = layers.current.seg;
    g.clearLayers();
    const national = mode === "national";
    // Hotspots last so they sit on top of the evaluated (blue) route.
    const ordered = national ? items : [...items].sort((a, b) => (hotIds && hotIds.has(a.id) ? 1 : 0) - (hotIds && hotIds.has(b.id) ? 1 : 0));
    for (const it of ordered) {
      const hot = !!(hotIds && hotIds.has(it.id));
      const style = national
        ? { color: LEVELS[it.level].hex, weight: it.level === "red" || it.level === "orange" ? 8 : 6 }
        : { color: hot ? LEVELS[it.level].hex : ROUTE_HEX, weight: hot ? 9 : 6 }; // calm blue; numbered points in their level colour (red สูงมาก / orange สูง)
      L.geoJSON(it.feature, { pane: "segPane", interactive: false, style: () => ({ ...style, opacity: 1, lineCap: "round" }) }).addTo(g);
    }
  }, [items, hotIds, rankById, mode]);

  // ---- numbered zones
  useEffect(() => {
    const m = mapRef.current;
    if (!m) return;
    const g = layers.current.zones;
    g.clearLayers();
    // Declutter: higher-priority zones claim screen space first; a zone whose marker would overlap
    // one already placed is left to the list and the ribbon until the user zooms in.
    const priority = [...zones].sort((a, b) => (b.key === selectedKey) - (a.key === selectedKey) ||
      LEVELS[b.level].rank - LEVELS[a.level].rank || b.maxDensity - a.maxDensity);
    const placed = [];
    for (const z of priority) {
      const pt = m.latLngToContainerPoint(z.anchor);
      if (placed.some((q) => q.distanceTo(pt) < 34)) continue;
      placed.push(pt);
      const selected = z.key === selectedKey;
      const mk = L.marker(z.anchor, { icon: zoneIcon(z.n, z.level, selected, mode, z.eta.clock), zIndexOffset: selected ? 900 : 600, title: "จุดที่ " + z.n + " · ผ่านราว " + z.eta.clock, alt: "จุดที่ " + z.n });
      mk.on("click", () => handlers.current.onSelectZone(z.key));
      mk.addTo(g);
    }
  }, [zones, selectedKey, zoomTick, mode]);

  // ---- drive mode: the car glides every animation frame between position updates and the map follows it.
  //      Simulation: interpolated ALONG the road (pointAt), so it never cuts corners. GPS: straight between fixes.
  //      Dragging the map pauses following; the "กลับไปที่รถ" button resumes it.
  const carRef = useRef(null);
  const animRef = useRef({ from: null, to: null, t0: 0, dur: 250, raf: 0, follow: true });
  const [following, setFollowing] = useState(true);
  const driving = !!drivePos;
  useEffect(() => {
    const m = mapRef.current;
    if (!m) return undefined;
    const onDrag = () => { animRef.current.follow = false; setFollowing(false); };
    m.on("dragstart", onDrag);
    // While two fingers are on the map (pinch zoom) the follow camera stands still, otherwise re-centering the map
    // every frame would cancel the pinch. Zooming keeps following; only dragging unlocks.
    const el = m.getContainer();
    const onTouch = (e) => { animRef.current.pinch = e.touches && e.touches.length >= 2 ? true : animRef.current.pinch && e.touches.length > 0; };
    const onZoomStart = () => { animRef.current.zooming = true; };
    const onZoomEnd = () => { animRef.current.zooming = false; };
    el.addEventListener("touchstart", onTouch, { passive: true });
    el.addEventListener("touchmove", onTouch, { passive: true });
    el.addEventListener("touchend", onTouch, { passive: true });
    el.addEventListener("touchcancel", onTouch, { passive: true });
    m.on("zoomstart", onZoomStart);
    m.on("zoomend", onZoomEnd);
    return () => {
      m.off("dragstart", onDrag); m.off("zoomstart", onZoomStart); m.off("zoomend", onZoomEnd);
      el.removeEventListener("touchstart", onTouch); el.removeEventListener("touchmove", onTouch);
      el.removeEventListener("touchend", onTouch); el.removeEventListener("touchcancel", onTouch);
    };
  }, []);
  useEffect(() => {
    const m = mapRef.current;
    const A = animRef.current;
    if (!m) return;
    if (!drivePos) {
      cancelAnimationFrame(A.raf); A.raf = 0; A.from = A.to = null;
      layers.current.car.clearLayers(); carRef.current = null;
      A.follow = true; setFollowing(true);
      return;
    }
    const now = performance.now();
    const cur = A.to && A.from ? frameAt(A, now) : null;
    A.from = cur || { lat: drivePos.lat, lon: drivePos.lon, along: drivePos.alongM, heading: drivePos.heading || 0 };
    A.to = { lat: drivePos.lat, lon: drivePos.lon, along: drivePos.alongM, heading: drivePos.heading || 0 };
    A.dur = drivePos.source === "sim" ? 260 : Math.min(1500, Math.max(400, now - (A.t0 || now)));
    A.t0 = now;
    A.sim = drivePos.source === "sim";
    if (!carRef.current) {
      const html = '<span><svg width="22" height="22" viewBox="0 0 24 24"><path d="M12 2l7 19-7-4-7 4z" fill="#fff"/></svg></span>';
      const icon = L.divIcon({ className: "car-icon", html, iconSize: [36, 36], iconAnchor: [18, 18] });
      carRef.current = L.marker([A.to.lat, A.to.lon], { icon, interactive: false, keyboard: false, zIndexOffset: 1200 }).addTo(layers.current.car);
      m.setView([A.to.lat, A.to.lon], Math.max(m.getZoom(), 13), { animate: false });
    }
    if (!A.raf) {
      const step = () => {
        const B = animRef.current;
        if (!B.to || !carRef.current) { B.raf = 0; return; }
        const f = frameAt(B, performance.now());
        carRef.current.setLatLng([f.lat, f.lon]);
        const el = carRef.current.getElement();
        const span = el && el.firstChild;
        // smooth the arrow's turn (road vertices would otherwise snap it)
        B.h = B.h == null ? f.heading : B.h + ((((f.heading - B.h) % 360) + 540) % 360 - 180) * 0.15;
        if (span) span.style.transform = "rotate(" + B.h.toFixed(1) + "deg)";
        if (B.follow && !B.pinch && !B.zooming) {
          // phones: keep the car in the upper part of the map, above the bottom sheet
          const offY = isMobile() ? Math.round(m.getSize().y * 0.18) : 0;
          const z = m.getZoom();
          const c = m.unproject(m.project([f.lat, f.lon], z).add([0, offY]), z);
          m.setView(c, z, { animate: false, noMoveStart: true });
        }
        B.raf = requestAnimationFrame(step);
      };
      A.raf = requestAnimationFrame(step);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [drivePos]);
  useEffect(() => () => cancelAnimationFrame(animRef.current.raf), []);
  // While following the car, wheel / pinch zoom around the map centre (the car) instead of the cursor or fingers.
  useEffect(() => {
    const m = mapRef.current;
    if (!m) return;
    const c = driving && following ? "center" : true;
    m.options.scrollWheelZoom = c;
    m.options.touchZoom = c;
  }, [driving, following]);

  function frameAt(A, now) {
    const k = Math.max(0, Math.min(1, (now - A.t0) / A.dur));
    if (A.sim && route && route.index && Number.isFinite(A.from.along) && Number.isFinite(A.to.along)) {
      const p = pointAt(route, A.from.along + (A.to.along - A.from.along) * k);
      return { lat: p.lat, lon: p.lon, along: A.from.along + (A.to.along - A.from.along) * k, heading: p.heading };
    }
    let dh = ((A.to.heading - A.from.heading + 540) % 360) - 180;
    return { lat: A.from.lat + (A.to.lat - A.from.lat) * k, lon: A.from.lon + (A.to.lon - A.from.lon) * k,
             along: A.to.along, heading: A.from.heading + dh * k };
  }
  useEffect(() => {
    const m = mapRef.current;
    if (!m || driving || !route) return;
    m.fitBounds(L.latLngBounds(route.coords.map(([lon, lat]) => [lat, lon])), getPadding());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [driving]);

  // ---- fly to a zone chosen in the list
  useEffect(() => {
    const m = mapRef.current;
    if (!m || !focus) return;
    const z = zones.find((x) => x.key === focus.key);
    if (!z) return;
    const b = L.latLngBounds([]);
    for (const mem of z.members) b.extend(L.geoJSON(mem.feature).getBounds());
    if (b.isValid()) m.fitBounds(b, { ...getPadding(), maxZoom: 13 });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [focus]);

  return (
    <>
      <div ref={divRef} className="map" tabIndex={0} aria-label="แผนที่ประเทศไทย" />
      {driving && (
        <button type="button" className={"btn btn-sm lock-btn" + (following ? " is-on" : "")} aria-pressed={following}
          title={following ? "แผนที่เลื่อนตามรถอยู่ — แตะเพื่อปลดล็อก (หรือลากแผนที่)" : "แตะเพื่อให้แผนที่ตามรถอีกครั้ง"}
          onClick={() => { const next = !animRef.current.follow; animRef.current.follow = next; setFollowing(next); }}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <rect x="5" y="11" width="14" height="10" rx="2" />{following ? <path d="M8 11V7a4 4 0 0 1 8 0v4" /> : <path d="M8 11V7a4 4 0 0 1 7.5-2" />}
          </svg>
          {following ? "ล็อกตามรถ" : "ปลดล็อกอยู่ · แตะเพื่อตามรถ"}
        </button>
      )}
      {tileWarn && <p className="map-chip map-chip-warn" role="status">โหลดภาพแผนที่บางส่วนไม่สำเร็จ — ข้อมูลเส้นทางยังใช้งานได้</p>}
    </>
  );
}
