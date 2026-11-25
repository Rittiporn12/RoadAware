"""Build frontend/public/data/hero-map.json for the home page's hero map.

Thailand's boundary (frontend/public/assets/thailand-boundary.geojson) projected to SVG units and drawn as smooth
curves, the DOH highway network (backend/data/v4/linkage_audit/segments_2000m.geojson) in three classes by route
number (1-digit, 2-digit, 3-digit routes), and an illustrative Bangkok -> Chiang Mai trip snapped onto highways 1/32/11.
Run from the repository root: python3 backend/scripts/build_hero_map.py
"""
import json
import math
from pathlib import Path

PUB = Path(__file__).resolve().parents[2] / "frontend" / "public"
K, C, LON0, LAT0 = 60, math.cos(math.radians(13)), 97.2, 20.6


def P(lon, lat):
    return (round((lon - LON0) * K * C, 1), round((LAT0 - lat) * K, 1))


def area(r):
    return abs(sum(r[i][0] * r[i - 1][1] - r[i - 1][0] * r[i][1] for i in range(len(r)))) / 2


def smooth(pts):
    """Closed Catmull-Rom spline through pts as SVG cubic curves (no corners)."""
    n = len(pts)
    out = [f"M{pts[0][0]} {pts[0][1]}"]
    for i in range(n):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[(i + 1) % n], pts[(i + 2) % n]
        c1 = (round(p1[0] + (p2[0] - p0[0]) / 6, 1), round(p1[1] + (p2[1] - p0[1]) / 6, 1))
        c2 = (round(p2[0] - (p3[0] - p1[0]) / 6, 1), round(p2[1] - (p3[1] - p1[1]) / 6, 1))
        out.append(f"C{c1[0]} {c1[1]} {c2[0]} {c2[1]} {p2[0]} {p2[1]}")
    return "".join(out) + "Z"


def main():
    g = json.loads((PUB / "assets" / "thailand-boundary.geojson").read_text())
    parts = []
    for poly in sorted(g["features"][0]["geometry"]["coordinates"], key=lambda p: -area(p[0])):
        ring = poly[0]
        if area(ring) < 0.004:
            continue
        pts, last = [], None
        for lon, lat in ring:
            x, y = P(lon, lat)
            if last and math.hypot(x - last[0], y - last[1]) < 2.2:
                continue
            pts.append((x, y))
            last = (x, y)
        if len(pts) >= 6:
            parts.append(smooth(pts))
    seg = json.loads((Path(__file__).resolve().parents[1] / "data" / "v4" / "linkage_audit" / "segments_2000m.geojson").read_text())
    roads = {1: [], 2: [], 3: []}
    trip_nodes = []
    for f in seg["features"]:
        k = f["properties"].get("route_key")
        if not k or not k.isdigit() or k.startswith("1") and len(k.lstrip("0")) == 4:
            continue
        digits = len(k.lstrip("0"))
        if digits > 3:
            continue
        line, last = [], None
        for lon, lat in f["geometry"]["coordinates"]:
            x, y = P(lon, lat)
            if last is None or math.hypot(x - last[0], y - last[1]) >= 0.8:
                line.append((x, y))
                last = (x, y)
        end = P(*f["geometry"]["coordinates"][-1])
        if line[-1] != end:
            line.append(end)
        if len(line) >= 2:
            roads[digits].append("M" + " L".join(f"{x} {y}" for x, y in line))
        if k in ("0001", "0032", "0011"):
            trip_nodes.extend(line)
    route = [(100.52, 13.75), (100.62, 14.02), (100.57, 14.35), (100.45, 14.59), (100.40, 14.89), (100.12, 15.18), (100.12, 15.70),
             (99.80, 16.10), (99.52, 16.48), (99.13, 16.88), (99.23, 17.61), (99.49, 18.29), (99.01, 18.58), (98.99, 18.79)]
    # densify the rough trip, then snap every point to the nearest vertex of highways 1/32/11 so it sits on the road
    dense = []
    for (a1, b1), (a2, b2) in zip(route, route[1:]):
        for t in range(8):
            dense.append(P(a1 + (a2 - a1) * t / 8, b1 + (b2 - b1) * t / 8))
    dense.append(P(*route[-1]))
    snapped = []
    for x, y in dense:
        q = min(trip_nodes, key=lambda n: (n[0] - x) ** 2 + (n[1] - y) ** 2)
        if not snapped or q != snapped[-1]:
            snapped.append(q)
    out = {"w": round((105.75 - LON0) * K * C), "h": round((LAT0 - 5.5) * K), "path": "".join(parts),
           "roads": {"major": "".join(roads[1]), "mid": "".join(roads[2]), "minor": "".join(roads[3])},
           "route": snapped}
    (PUB / "data" / "hero-map.json").write_text(json.dumps(out, separators=(",", ":")))
    print("hero-map.json:", {k: len(v) for k, v in roads.items()}, "road pieces,", len(snapped), "trip points")


if __name__ == "__main__":
    main()
