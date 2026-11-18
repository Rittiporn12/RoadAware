// Leaflet map, Thailand only: bounded pan/zoom + an opaque mask over every other country.
// Leaflet is driven imperatively from effects; the selected spot's popup body is a React portal.
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { CONFIG, THAI_BOUNDS, MAX_BOUNDS, LEVELS, ENVELOPE } from "../config.js";
import { pointInGeometry } from "../lib/routeMatch.js";

const isMobile = () => window.matchMedia("(max-width: 860px)").matches;

function endpointIcon(letter) {
  return L.divIcon({
    className: "endpoint-icon endpoint-" + letter.toLowerCase(),
    html: "<span><b>" + letter + "</b></span>", // constant markup only
    iconSize: [30, 30],
    iconAnchor: [15, 34],
  });
}

export default function MapView({
  route, origin, dest, spots, hiddenLevels, selectedKey, focus, pick,
  getPadding, onPick, onOutside, onSelectSpot, onFailed, children,
}) {
  const divRef = useRef(null);
  const mapRef = useRef(null);
  const layers = useRef({});
  const boundaryRef = useRef(null);
  const circles = useRef(new Map());
  const popupRef = useRef(null);
  const handlers = useRef({});
  handlers.current = { onPick, onOutside, onSelectSpot, pick };
  const popupEl = useMemo(() => document.createElement("div"), []);
  const [tileWarn, setTileWarn] = useState(false);

  // ---- create the map once
  useEffect(() => {
    let m;
    try {
      m = L.map(divRef.current, { zoomControl: false, maxBounds: MAX_BOUNDS, maxBoundsViscosity: 1.0, worldCopyJump: false, maxZoom: 18 });
    } catch (_) {
      onFailed && onFailed();
      return undefined;
    }
    L.control.zoom({ position: isMobile() ? "bottomright" : "topright" }).addTo(m);
    m.createPane("mask").style.zIndex = 350;
    m.createPane("routePane").style.zIndex = 410;
    m.createPane("segPane").style.zIndex = 420;
    m.createPane("spotPane").style.zIndex = 630;
    let tileErrors = 0;
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    })
      .on("tileload", () => setTileWarn(false))
      .on("tileerror", () => { tileErrors += 1; if (tileErrors >= 4) setTileWarn(true); })
      .addTo(m);
    layers.current = {
      route: L.layerGroup().addTo(m),
      seg: L.layerGroup().addTo(m),
      spot: L.layerGroup().addTo(m),
      ends: L.layerGroup().addTo(m),
    };
    popupRef.current = L.popup({ maxWidth: 300, minWidth: 230, autoPanPaddingTopLeft: [20, 70], autoPanPaddingBottomRight: [20, 20] });

    const updateMinZoom = () => {
      m.invalidateSize();
      m.setMinZoom(Math.max(4, Math.floor(m.getBoundsZoom(THAI_BOUNDS, false))));
    };
    updateMinZoom();
    m.fitBounds(THAI_BOUNDS);
    window.addEventListener("resize", updateMinZoom);

    const inside = (lat, lon) => (boundaryRef.current
      ? pointInGeometry(lon, lat, boundaryRef.current)
      : lon >= ENVELOPE.west && lon <= ENVELOPE.east && lat >= ENVELOPE.south && lat <= ENVELOPE.north);
    m.on("click", (e) => {
      const h = handlers.current;
      if (!h.pick) return;
      if (!inside(e.latlng.lat, e.latlng.lng)) { h.onOutside(); return; }
      h.onPick(e.latlng.lat, e.latlng.lng);
    });

    // Thailand display boundary (Natural Earth, public domain) → mask with Thai rings as holes.
    let cancelled = false;
    fetch(CONFIG.boundaryUrl)
      .then((r) => r.json())
      .then((gj) => {
        if (cancelled) return;
        const geom = gj.type === "FeatureCollection" ? gj.features[0].geometry : gj.geometry;
        if (!geom || (geom.type !== "Polygon" && geom.type !== "MultiPolygon")) return;
        boundaryRef.current = geom;
        const polys = geom.type === "Polygon" ? [geom.coordinates] : geom.coordinates;
        const world = [[-89, -179.9], [-89, 179.9], [89, 179.9], [89, -179.9]];
        const holes = polys.map((poly) => poly[0].map(([lon, lat]) => [lat, lon]));
        L.polygon([world, ...holes], { pane: "mask", stroke: false, fillColor: "#e9e4da", fillOpacity: 1 })
          .on("click", (e) => { L.DomEvent.stop(e); handlers.current.onOutside(); })
          .addTo(m);
        L.geoJSON(geom, { pane: "mask", interactive: false, style: { color: "#0e6b70", weight: 1.5, opacity: 0.7, fill: false } }).addTo(m);
      })
      .catch(() => { /* bounds still restrict the view; picking falls back to the envelope */ });

    mapRef.current = m;
    return () => {
      cancelled = true;
      window.removeEventListener("resize", updateMinZoom);
      m.remove();
      mapRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ---- pick cursor
  useEffect(() => {
    if (divRef.current) divRef.current.classList.toggle("is-picking", !!pick);
  }, [pick]);

  // ---- endpoint markers
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
      L.marker([p.lat, p.lon], { icon: endpointIcon(letter), keyboard: false, zIndexOffset: 500 }).bindTooltip(tip).addTo(g);
      pts.push([p.lat, p.lon]);
    }
    if (!route) {
      if (pts.length === 2) m.fitBounds(L.latLngBounds(pts), { ...getPadding(), maxZoom: 13 });
      else if (pts.length === 1) m.setView(pts[0], Math.max(m.getZoom(), 11));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [origin, dest]);

  // ---- route line (grey = no forecast coverage; coloured segment overlays are drawn on top)
  useEffect(() => {
    const m = mapRef.current;
    if (!m) return;
    const g = layers.current.route;
    g.clearLayers();
    if (!route) return;
    const latlngs = route.coords.map(([lon, lat]) => [lat, lon]);
    L.polyline(latlngs, { pane: "routePane", color: "#ffffff", weight: 10, opacity: 0.95, interactive: false }).addTo(g);
    L.polyline(latlngs, { pane: "routePane", color: "#8d99a3", weight: 6, opacity: 1, interactive: false }).addTo(g);
    m.fitBounds(L.latLngBounds(latlngs), getPadding());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [route]);

  // ---- risk circles + matched segment overlays
  useEffect(() => {
    const m = mapRef.current;
    if (!m) return;
    const { seg, spot } = layers.current;
    seg.clearLayers();
    spot.clearLayers();
    circles.current = new Map();
    for (const g of spots) {
      for (const mem of g.members) {
        if (hiddenLevels.has(mem.level)) continue;
        L.geoJSON(mem.feature, { pane: "segPane", interactive: false, style: () => ({ color: mem.hex, weight: 6, opacity: 0.85 }) }).addTo(seg);
      }
      const p = g.primary;
      if (hiddenLevels.has(p.level)) continue;
      const lv = LEVELS[p.level];
      if (lv.rank >= 3) {
        L.circleMarker(p.match.anchor, { pane: "spotPane", radius: lv.radius + 9, stroke: false, fillColor: p.hex, fillOpacity: 0.22, interactive: false }).addTo(spot);
      }
      const tip = document.createElement("span");
      tip.textContent = lv.title + " · ผ่านราว " + p.eta.clock;
      const c = L.circleMarker(p.match.anchor, { pane: "spotPane", radius: lv.radius, color: "#ffffff", weight: 2.5, fillColor: p.hex, fillOpacity: 0.95 })
        .bindTooltip(tip, { direction: "top", offset: [0, -lv.radius] })
        .on("click", (e) => { L.DomEvent.stop(e); handlers.current.onSelectSpot(g.key, false); })
        .addTo(spot);
      circles.current.set(g.key, c);
    }
    if (!spots.length) m.closePopup();
  }, [spots, hiddenLevels]);

  // ---- popup for the selected spot (content = React portal)
  useEffect(() => {
    const m = mapRef.current;
    if (!m) return;
    const g = spots.find((s) => s.key === selectedKey);
    if (!g || hiddenLevels.has(g.primary.level)) { m.closePopup(popupRef.current); return; }
    popupRef.current.setLatLng(g.primary.match.anchor).setContent(popupEl);
    if (!m.hasLayer(popupRef.current)) popupRef.current.openOn(m);
  }, [selectedKey, spots, hiddenLevels, popupEl]);

  // list click → move the map to that spot
  useEffect(() => {
    const m = mapRef.current;
    if (!m || !focus) return;
    const g = spots.find((s) => s.key === focus.key);
    if (g) m.setView(g.primary.match.anchor, Math.max(m.getZoom(), 12), { animate: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [focus]);

  // re-measure the popup after React changes its content (e.g. history arrives)
  useLayoutEffect(() => {
    if (popupRef.current && mapRef.current && mapRef.current.hasLayer(popupRef.current)) popupRef.current.update();
  });

  return (
    <>
      <div ref={divRef} className="map" tabIndex={0} aria-label="แผนที่ประเทศไทย" />
      {tileWarn && <p className="tile-warning" role="status">โหลดภาพแผนที่พื้นหลังบางส่วนไม่สำเร็จ — ข้อมูลเส้นทางยังใช้งานได้</p>}
      {selectedKey && createPortal(children, popupEl)}
    </>
  );
}
