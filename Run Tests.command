#!/bin/bash
# RoadAware — full check (prepared by Claude). Double-click in Finder. ~10–20 min.
# 1) every backend test (pilot + shared code)   2) production build of the website
cd "$(dirname "$0")" || exit 1
mkdir -p .ai-team/national
LOG=".ai-team/national/tests-$(date +%Y%m%d-%H%M%S).log"
{
  echo "== $(date) start (branch: $(git branch --show-current), $(git log --oneline -1))"
  echo "== [1/2] backend tests"
  .venv/bin/python -m pytest backend/tests -q -p no:cacheprovider 2>&1 | tail -40; echo "TESTS_EXIT=${PIPESTATUS[0]}"
  echo "== [2/2] website build"
  ( cd frontend && npm run build 2>&1 | tail -15; echo "BUILD_EXIT=${PIPESTATUS[0]}" )
  echo "== $(date) done"
} 2>&1 | tee "$LOG"
echo; echo "Finished. Log: $LOG — you can close this window and tell Claude."
