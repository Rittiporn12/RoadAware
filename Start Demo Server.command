#!/bin/bash
# RoadAware — present from the website on GitHub Pages, using THIS Mac as the server (prepared by Claude).
# Double-click in Finder. Keep this window open during the presentation; close it (or Ctrl+C) to stop everything.
#   • starts the API (national model) and the Mac voice on this Mac
#   • opens a free temporary https tunnel (Cloudflare Quick Tunnel, no account) so the website can reach them
#   • prints / copies / opens the link:  https://rittiporn12.github.io/RoadAware/?api=...&tts=...
# The tunnel address changes every time this is started — always use the link printed by THIS run.
cd "$(dirname "$0")" || exit 1
SITE="https://rittiporn12.github.io/RoadAware/"
export ROADAWARE_CORS_EXTRA="https://rittiporn12.github.io"
LOGDIR="$HOME/.roadaware/demo-logs"; mkdir -p "$LOGDIR" "$HOME/.roadaware/bin"
PIDS=()
cleanup() { echo; echo "Stopping…"; for p in "${PIDS[@]}"; do kill "$p" 2>/dev/null; done; exit 0; }
trap cleanup INT TERM EXIT

# --- cloudflared (download once if missing) ---
CF="$(command -v cloudflared || true)"
[ -z "$CF" ] && [ -x "$HOME/.roadaware/bin/cloudflared" ] && CF="$HOME/.roadaware/bin/cloudflared"
if [ -z "$CF" ]; then
  echo "== Downloading cloudflared (one time)…"
  ARCH="$(uname -m)"; [ "$ARCH" = "arm64" ] && A=arm64 || A=amd64
  if curl -fsSL -o /tmp/cloudflared.tgz "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-darwin-$A.tgz" \
     || curl -fsSL -o /tmp/cloudflared.tgz "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-darwin-amd64.tgz"; then
    tar -xzf /tmp/cloudflared.tgz -C "$HOME/.roadaware/bin" && chmod +x "$HOME/.roadaware/bin/cloudflared"
    CF="$HOME/.roadaware/bin/cloudflared"
  fi
  if [ ! -x "$CF" ] && command -v brew >/dev/null; then brew install cloudflared && CF="$(command -v cloudflared)"; fi
  [ -x "$CF" ] || { echo "DEMO_FAILED: could not install cloudflared"; read -r; exit 1; }
fi

# --- API (reuse one that is already running) ---
if curl -fs http://127.0.0.1:8000/ready >/dev/null 2>&1; then
  echo "== API already running on this Mac (note: it must have been started by this file to accept the website)"
else
  echo "== Starting the API (takes a few seconds)…"
  .venv/bin/python backend/scripts/run_api_server.py --national --log-level warning >"$LOGDIR/api.log" 2>&1 &
  PIDS+=($!)
  for i in $(seq 1 90); do curl -fs http://127.0.0.1:8000/ready >/dev/null 2>&1 && break; sleep 1; done
  curl -fs http://127.0.0.1:8000/ready >/dev/null 2>&1 || { echo "DEMO_FAILED: API did not start — see $LOGDIR/api.log"; tail -20 "$LOGDIR/api.log"; read -r; exit 1; }
fi
echo "   API ready"

# --- voice (optional) ---
# stop an older RoadAware voice proxy still holding port 8010 (only that program, nothing else)
for p in $(lsof -ti tcp:8010 -sTCP:LISTEN 2>/dev/null); do ps -o command= -p "$p" | grep -q tts_proxy.py && kill "$p"; done
for i in 1 2 3 4 5; do lsof -ti tcp:8010 -sTCP:LISTEN >/dev/null 2>&1 || break; sleep 1; done
if lsof -ti tcp:8010 -sTCP:LISTEN >/dev/null 2>&1; then echo "VOICE_FAILED: port 8010 is used by another program"; echo "   (continuing without the Mac voice)"; fi
if ! lsof -ti tcp:8010 -sTCP:LISTEN >/dev/null 2>&1; then
  ROADAWARE_TTS_ENGINE=mac .venv/bin/python backend/scripts/tts_proxy.py >"$LOGDIR/voice.log" 2>&1 &
  PIDS+=($!)
  for i in $(seq 1 10); do curl -fs http://127.0.0.1:8010/health >/dev/null 2>&1 && break; sleep 1; done
fi

start_tunnel() { "$CF" tunnel --no-autoupdate --url "http://127.0.0.1:$1" >"$2" 2>&1 & PIDS+=($!); }
url_from() { # $1 log → waits for the https address in the tunnel log
  for i in $(seq 1 40); do
    U="$(grep -Eo 'https://[a-z0-9-]+\.trycloudflare\.com' "$1" | head -1)"
    [ -n "$U" ] && { echo "$U"; return 0; }
    sleep 1
  done
  return 1
}
echo "== Opening the tunnels…"
: >"$LOGDIR/tunnel-api.log"; : >"$LOGDIR/tunnel-voice.log"
start_tunnel 8000 "$LOGDIR/tunnel-api.log"
VOICE=0; curl -fs http://127.0.0.1:8010/health >/dev/null 2>&1 && { VOICE=1; start_tunnel 8010 "$LOGDIR/tunnel-voice.log"; }
API_URL="$(url_from "$LOGDIR/tunnel-api.log")" || { echo "DEMO_FAILED: tunnel did not start — see $LOGDIR/tunnel-api.log"; tail -20 "$LOGDIR/tunnel-api.log"; read -r; exit 1; }
TTS_URL=""; [ $VOICE = 1 ] && TTS_URL="$(url_from "$LOGDIR/tunnel-voice.log")"
LINK="$SITE?api=$API_URL"; [ -n "$TTS_URL" ] && LINK="$LINK&tts=$TTS_URL"

# wait until the public address answers (DNS of a new tunnel can take a few seconds)
for i in $(seq 1 30); do curl -fs "$API_URL/ready" >/dev/null 2>&1 && break; sleep 2; done

printf '%s' "$LINK" | pbcopy
echo ""
echo "=================================================================="
echo " DEMO_READY — open this link (already copied, also opening now):"
echo ""
echo "   $LINK"
echo ""
echo " • Phone: send yourself the link above, or open it once on the phone."
echo "   The site remembers the server, so the plain site address works"
echo "   afterwards in the same browser — until this window is closed."
echo " • Keep this window open and the Mac awake during the presentation."
echo " • Close this window (or press Ctrl+C) to stop the server."
echo "=================================================================="
open "$LINK"
caffeinate -dimsu -w $$ &
wait
