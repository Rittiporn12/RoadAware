#!/bin/bash
# RoadAware — national coverage, step 7 (prepared by Claude). Double-click in Finder.
# Starts the NATIONAL API on http://127.0.0.1:8000, runs a smoke test, then keeps serving (close the window or Ctrl+C to stop).
cd "$(dirname "$0")" || exit 1
mkdir -p .ai-team/national
LOG=".ai-team/national/step7-$(date +%Y%m%d-%H%M%S).log"
{
  echo "== $(date) start national API (branch: $(git branch --show-current))"
  .venv/bin/python backend/scripts/run_api_server.py --national --log-level warning &
  SRV=$!
  for i in $(seq 1 180); do curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/ready 2>/dev/null | grep -q 200 && break; kill -0 $SRV 2>/dev/null || break; sleep 2; done
  .venv/bin/python backend/scripts/national_api_smoke.py 8000; echo "SMOKE_EXIT=$?"
  echo "== API is running at http://127.0.0.1:8000 — now start the website (cd frontend && npm run dev). Close this window to stop the API."
  wait $SRV
} 2>&1 | tee "$LOG"
