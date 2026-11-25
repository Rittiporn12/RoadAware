"""Build frontend/public/data/hero-map.json for the home page's hero map.

Thailand's boundary (frontend/public/assets/thailand-boundary.geojson) projected to SVG units, the 900 ~5 km cells
with the most model-dataset accidents (from frontend/public/data/dashboard-v1.json, so run build_dashboard_data.py
first), and an illustrative Bangkok -> Chiang Mai route along highways 1/32/11.
Run from the repository root: python3 backend/scripts/build_hero_map.py
"""
import json
import math
from collections import Counter
from pathlib import Path

PUB = Path(__file__).resolve().parents[2] / "frontend" / "public"
K, C, LON0, LAT0 = 60, math.cos(math.radians(13)), 97.2, 20.6


def P(lon, lat):
    return (round((lon - LON0) * K * C, 1), round((LAT0 - lat) * K, 1))


def area(r):
    return abs(sum(r[i][0] * r[i - 1][1] - r[i - 1][0] * r[i][1] for i in range(len(r)))) / 2


def main():
    g = json.loads((PUB / "assets" / "thailand-boundary.geojson").read_text())
    parts = []
    for poly in sorted(g["features"][0]["geometry"]["coordinates"], key=lambda p: -area(p[0])):
        ring = poly[0]
        if area(ring) < 0.002:
            continue
        pts, last = [], None
        for lon, lat in ring:
            x, y = P(lon, lat)
            if last and math.hypot(x - last[0], y - last[1]) < 1.6:
                continue
            pts.append((x, y))
            last = (x, y)
        if len(pts) >= 4:
            parts.append("M" + " L".join(f"{x} {y}" for x, y in pts) + "Z")
    d = json.loads((PUB / "data" / "dashboard-v1.json").read_text())
    gr = d["meta"]["grid"]
    cnt = Counter(c for c in d["cols"]["cell"] if c is not None and c >= 0)
    top = cnt.most_common(900)
    mx = top[0][1]
    hot = []
    for c, v in top:
        lat = gr["lat0"] + (c // gr["nlon"]) * gr["cell_deg"] + gr["cell_deg"] / 2
        lon = gr["lon0"] + (c % gr["nlon"]) * gr["cell_deg"] + gr["cell_deg"] / 2
        x, y = P(lon, lat)
        hot.append([x, y, round(math.sqrt(v / mx), 3)])
    route = [(100.52, 13.75), (100.62, 14.02), (100.57, 14.35), (100.45, 14.59), (100.40, 14.89), (100.12, 15.18), (100.12, 15.70),
             (99.80, 16.10), (99.52, 16.48), (99.13, 16.88), (99.23, 17.61), (99.49, 18.29), (99.01, 18.58), (98.99, 18.79)]
    out = {"w": round((105.75 - LON0) * K * C), "h": round((LAT0 - 5.5) * K), "path": "".join(parts), "hot": hot,
           "route": [P(*p) for p in route], "records": sum(cnt.values())}
    (PUB / "data" / "hero-map.json").write_text(json.dumps(out, separators=(",", ":")))
    print("hero-map.json:", len(hot), "cells,", out["records"], "records")


if __name__ == "__main__":
    main()
