# Frontend integration contract (local research API V3, task 019) — no frontend is implemented

Base URL `http://127.0.0.1:8000`. Allowed browser origins (exact): `http://localhost:5173`, `http://127.0.0.1:5173`, `http://localhost:3000`, `http://127.0.0.1:3000`; no credentials/cookies. All bodies are `application/json`, at most 64 KiB, strict JSON (no NaN/Infinity, no duplicate keys, exact fields, no type coercion). Every response carries `production_ready: false`. The authoritative schema is the `openapi.json` saved by the live smoke.

Accepted 12 November 2026: live HTTP004 **73/73 checks**, final backend **831 passed / 1 conditional skip**. Ready for Frontend/Dashboard integration within the research scope. [Accepted record](accepted-runtime-v3.json), [verified OpenAPI](../../output/spatial-model-results/v3-api-019-004/openapi.json), [actual public response examples](../../output/spatial-model-results/v3-api-019-004/sample_responses.json). No frontend or deployment is included.

## Startup
Poll `GET /ready`: render data only when 200 and `research_backend_ready` is true. On 503 show "backend unavailable" with `components.*.code`; never show cached or zero values instead.

## Map (segments)
- `GET /api/v1/segments?bbox=west,south,east,north&limit=1..500&cursor=<next_cursor>` → GeoJSON FeatureCollection (EPSG:4326 lon/lat). Order is `segment_id` ascending; follow `page.next_cursor` until null. bbox span ≤ 20° per axis.
- `feature.id` == `properties.segment_id` is the stable key linking geometry, history and predictions.
- Roads not returned here are **unsupported**: draw them grey / "no data". Never draw them as low risk or zero.

## Predictions (segment)
`POST /api/v1/spatial/predictions` `{"unit": "daily"|"6h", "requests": [{"segment_id", "target_date", "time_block" (6h only: 00-06|06-12|12-18|18-24)}]}` (1..128 unique rows; target dates 2024-01-01..2027-12-31).
Results keep request order. Per row use: `expected_recorded_count`, `density_per_km`, `colour` + `colour_hex` + `colour_text` (always show the text, not colour alone), `horizon`, `issue_time_local`, `model_version`, `component_used`/`routing_reason`, `source_availability`, `research_scenario`/`data_period`.
Labels to display: "expected recorded-count rate (research)"; `base` colour is NOT "safe"; dates after 2025-12-31 are research scenarios without ground truth. Never sum rows into a route probability; no safest-route wording.
`POST /api/v1/spatial/baseline-predictions` (same body) is a comparison only.

## History
- Segment: `POST /api/v1/spatial/history` `{"segment_id", "target_date", "unit"[, "time_block"][, "lookback_days" ≤ 1827][, "categories"][, "top_k" ≤ 10]}` → `history` (counts before the target's issue/30-day cutoff) + `period_status`. If `period_status.unsupported_after` is set (e.g. 2026), show that period as "not in catalog", not zero. Categories are recorded attributes, not causes.
- Province: `GET /api/v1/history?province_key=&start_month=YYYY-MM&end_month=YYYY-MM[&categories=a,b][&top_k=]` (2021-01..2025-12, ≤ 60 months). Province list: `GET /api/v1/provinces` (label points only).
- Province predictions (V2 compatibility): `POST /api/v1/predictions` `{"requests": [{"province_key", "target_date", "unit"[, "time_block"]}]}` — province scope only.

## Errors
Envelope `{"ok": false, "error": {"code", "family", "message", "rows"?, "errors"?}}`. 400 invalid (show `rows`), 404 coverage (unknown/unsupported id: grey, never zero), 413/415 client bug, 503 unavailable (generic message; retry later), 500 internal (no partial result).

## Evaluation panel

`spatial_evaluation_21.metrics` contains32 verified selected/baseline rows for both units: `scope=oof` is the2022–23 selection period; `scope=diag` is previously seen2024–25. `dimension=pooled|period`, `group`, `n`, `total_actual`, `total_pred`, deviance/MAE/RMSE/bias/WAPE and floor counts retain their CSV meanings. Do not mix units or compare full-population OOF score levels with the2026 positive-cell diagnostic. Display counts and scope with each metric.
`GET /api/v1/evaluation`: show `diagnostics_2026.limits` verbatim next to any 2026 metric; strong-baseline deviance may be `null` with `deviance_status: infinite_due_zero_prediction` — show the floor audit separately; note where the baseline has the lower MAE (`lower_mae_on_this_conditional_cohort`).
