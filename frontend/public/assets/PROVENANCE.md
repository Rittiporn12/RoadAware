# Frontend assets — provenance

## thailand-boundary.geojson

- Source: geoBoundaries gbOpen, Thailand ADM0, simplified release (`scripts/source/geoBoundaries-THA-ADM0_simplified.geojson`, downloaded 18 Nov 2026 from https://github.com/wmgeolab/geoBoundaries/blob/main/releaseData/gbOpen/THA/ADM0/geoBoundaries-THA-ADM0_simplified.geojson).
- License: CC BY 4.0 — attribution "geoBoundaries" (https://www.geoboundaries.org/). Credited in the app's "ข้อมูลนี้มาจากไหน" dialog.
- Processing: `node scripts/prepare-boundary.mjs scripts/source/geoBoundaries-THA-ADM0_simplified.geojson` — outer rings of all 70 polygons (islands included), Douglas–Peucker 0.0007° (~80 m), coordinates rounded to 5 decimals.
- Replaces the Natural Earth 1:50m outline, whose Gulf-of-Thailand coastline cut into Samut Prakan (copy kept in `output/frontend-react-v1/`).
- Use in the app: display only — the sharp Thailand basemap clip, the outline, the dimmed mask over other countries, and rejecting map clicks outside Thailand. Not a legal boundary, not used by the ML model, and not road/forecast coverage.
