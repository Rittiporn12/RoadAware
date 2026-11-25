#!/bin/bash
# RoadAware — voice for drive mode (prepared by Claude). Double-click in Finder; keep this window open while driving/simulating.
# Uses the Mac's own voice set in System Settings → Accessibility → Read & Speak:
#   System speech language = Thai, System voice = Siri Voice 1 (or any Thai voice you like).
# Free, offline, no daily limit. Without this window the website uses the browser's Thai voice instead.
# (Optional: Gemini instead — run with ROADAWARE_TTS_ENGINE=gemini and a key in ~/.roadaware-gemini-key.)
cd "$(dirname "$0")" || exit 1
export ROADAWARE_TTS_ENGINE="${ROADAWARE_TTS_ENGINE:-mac}"
# stop an older RoadAware voice proxy still holding port 8010 (only that program, nothing else)
for p in $(lsof -ti tcp:8010 -sTCP:LISTEN 2>/dev/null); do ps -o command= -p "$p" | grep -q tts_proxy.py && kill "$p"; done
for i in 1 2 3 4 5; do lsof -ti tcp:8010 -sTCP:LISTEN >/dev/null 2>&1 || break; sleep 1; done
if lsof -ti tcp:8010 -sTCP:LISTEN >/dev/null 2>&1; then echo "VOICE_FAILED: port 8010 is used by another program"; read -r; exit 1; fi
.venv/bin/python backend/scripts/tts_proxy.py &
SRV=$!
for i in $(seq 1 10); do curl -fs http://127.0.0.1:8010/health >/dev/null 2>&1 && break; sleep 1; done
kill -0 $SRV 2>/dev/null || { echo "VOICE_FAILED: the voice program stopped — see the lines above"; read -r; exit 1; }
echo "== self-test"
CODE=$(curl -s -o /tmp/roadaware-tts-test.wav -w '%{http_code}' -X POST http://127.0.0.1:8010/tts -H 'Content-Type: application/json' \
  -d '{"text":"ระวัง! อีก 500 เมตร ถึงจุดที่ควรระวัง นี่คือเสียงเตือนของ RoadAware"}')
if [ "$CODE" = "200" ]; then echo "VOICE_OK — playing the test sentence (should be the voice you picked in Read & Speak)"; afplay /tmp/roadaware-tts-test.wav 2>/dev/null
else echo "VOICE_FAILED (HTTP $CODE) — see the line above; the website will use the browser voice instead"; fi
echo "== voice running on http://127.0.0.1:8010 — refresh the website. Close this window to stop."
wait $SRV
