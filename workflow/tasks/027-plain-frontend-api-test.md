# Goal
Implement the user's explicitly authorized minimal frontend API test page, with NO CSS, connected directly to the existing RoadAware local API. Codex independently verifies in a browser. Thai UI and instructions preferred.

## Current context
- frontend currently contains only a reserved README. User now authorizes this limited test page, not a full product/dashboard.
- Read workflow/api/frontend-integration-contract-v3.md and backend API runbook. Backend is already accepted; do not change it or rerun training/notebooks/pipelines.
- API http://127.0.0.1:8000; browser origin http://127.0.0.1:5173 is already allowed by CORS.
- Keep simple static HTML + vanilla JS, no dependencies/build/package installation. Serve frontend with python3 -m http.server 5173 --bind 127.0.0.1 --directory frontend.
- Codex has opened Monitor AI Team.command to expose worker progress.

## Allowed changes
Only frontend/index.html, frontend/app.js, frontend/README.md. Do not touch unrelated files. No CSS files/style attributes/style blocks/frameworks.

## Requirements and acceptance criteria
1. Real fetch calls, no mocks, fabricated responses, cached fallback or fake zero values. Configurable API base URL defaults to http://127.0.0.1:8000.
2. Clearly display local research-only / production_ready=false and that predicted counts are research recorded-count rates, not individual accident probabilities. Future dates after 2025 are research scenarios without ground truth; unsupported history is not zero.
3. Start by calling GET /ready; show HTTP status and raw formatted JSON and research_backend_ready. Gate data actions on readiness, provide retry. Network/CORS/timeout errors must show understandable Thai messages; failed readiness must invalidate prior ready state. Config changes invalidate readiness. Use bounded fetch timeout and prevent overlapping operations/confusing stale outputs. Render all API output safely with textContent, never innerHTML from API.
4. Let user get actual segments using bbox default 100.4,13.6,100.8,14.0 and limit e.g. 10, choose a returned segment ID (populate select), target date default 2026-11-12 and unit daily/6h plus valid time block. Support fetching next page using returned page.next_cursor, if available; cursor resets for changed query/base.
5. Buttons to POST spatial predictions, baseline predictions and spatial history for chosen segment using contract bodies. Display actual request URL/method/body, HTTP status, loading/success/error, raw pretty JSON for every request; do not retain stale successful data as current after failure. Include returned error.code/message and rows/details through raw JSON. Baseline marked comparison only.
6. Simple buttons for metadata, provinces and evaluation are useful; if evaluation shown raw, keep its limits visible in JSON and warn that scopes/units must not be combined. No graphs/maps/dashboard design needed.
7. Provide deliberate API error test button sending invalid request to predictions endpoint so Codex/user can see real HTTP 400 envelope. Also permit unavailable API via base URL for network error test. Errors should not leave buttons disabled forever.
8. README includes exact two-terminal startup commands from repo root (existing .venv backend and static frontend), URL to open, stop commands, simple happy path/error test and limits. No claim of tests you did not run.

## Verification requested
Codex runs syntax checks, starts existing backend and static frontend without changing backend, and performs real browser interactions for readiness, segments, daily/6h prediction, history, HTTP error and unavailable API. Worker file tools only; report static inspection separately from checks actually executed.

## Constraints and final report
No backend/config/pins/data/model changes; no training, dependency install, deployment or CSS. Do not add tests that mirror implementation. Keep user-facing page compact. Report changed files, checks actually run, checks not run and remaining issues. Short progress updates visible in monitor.
