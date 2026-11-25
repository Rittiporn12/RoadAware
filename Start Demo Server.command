#!/bin/bash
# RoadAware — present from the website on GitHub Pages, using THIS Mac as the server (prepared by Claude).
# Double-click in Finder. Keep this window open during the presentation; close it (or Ctrl+C) to stop everything.
#   • starts the API (national model) and the Mac voice on this Mac
#   • opens a free temporary https tunnel (Cloudflare Quick Tunnel, no account) so the website can reach them
#   • publishes the tunnel address to GitHub (branch demo-endpoint, file endpoint.json), so the plain site
#     https://rittiporn12.github.io/RoadAware/ always finds THIS run's server by itself — on any device
#   • when this window closes it publishes "offline", so the home page shows the server is off
# The tunnel address changes every run; nobody needs to copy it any more. (Backup link with ?api= is printed too.)
cd "$(dirname "$0")" || exit 1
SITE="https://rittiporn12.github.io/RoadAware/"
export ROADAWARE_CORS_EXTRA="https://rittiporn12.github.io"
LOGDIR="$HOME/.roadaware/demo-logs"; mkdir -p "$LOGDIR" "$HOME/.roadaware/bin"
PIDS=()
PUBLISHED=0
# Write endpoint.json on the demo-endpoint branch without touching the working tree or the current branch.
publish_endpoint() { # $1 = JSON text
  (
    export GIT_AUTHOR_NAME="Rittiporn12" GIT_AUTHOR_EMAIL="earthcraftchallenge@gmail.com"
    export GIT_COMMITTER_NAME="$GIT_AUTHOR_NAME" GIT_COMMITTER_EMAIL="$GIT_AUTHOR_EMAIL"
    B=$(printf '%s\n' "$1" | git hash-object -w --stdin) &&
    T=$(printf '100644 blob %s\tendpoint.json\n' "$B" | git mktree) &&
    C=$(git commit-tree "$T" -m "demo server address $(date '+%Y-%m-%d %H:%M')") &&
    git push -q -f origin "$C:refs/heads/demo-endpoint"
  ) >>"$LOGDIR/publish.log" 2>&1
}
CLEANED=0
cleanup() {
  [ "$CLEANED" = 1 ] && return; CLEANED=1
  echo; echo "Stopping…"
  if [ "$PUBLISHED" = 1 ]; then
    echo "   telling the website the server is offline…"
    publish_endpoint "{\"online\":false,\"updated\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}" & PP=$!
    for i in $(seq 1 12); do kill -0 $PP 2>/dev/null || break; sleep 1; done
  fi
  for p in "${PIDS[@]}"; do kill "$p" 2>/dev/null; done
  exit 0
}
trap cleanup INT TERM HUP EXIT

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

# one gateway on 8020 serves the API and /voice/, so a single tunnel is enough
for p in $(lsof -ti tcp:8020 -sTCP:LISTEN 2>/dev/null); do ps -o command= -p "$p" | grep -q demo_gateway.py && kill "$p"; done; sleep 1
.venv/bin/python backend/scripts/demo_gateway.py >"$LOGDIR/gateway.log" 2>&1 &
PIDS+=($!); sleep 1

echo "== Opening the tunnel…"
API_URL=""
for attempt in 1 2 3 4 5 6; do
  : >"$LOGDIR/tunnel.log"
  "$CF" tunnel --no-autoupdate --url "http://127.0.0.1:8020" >"$LOGDIR/tunnel.log" 2>&1 &
  TPID=$!
  for i in $(seq 1 30); do
    API_URL="$(grep -Eo 'https://[a-z0-9-]+\.trycloudflare\.com' "$LOGDIR/tunnel.log" | head -1)"
    [ -n "$API_URL" ] && break
    kill -0 $TPID 2>/dev/null || break
    sleep 1
  done
  if [ -n "$API_URL" ]; then PIDS+=($TPID); break; fi
  kill $TPID 2>/dev/null
  WAIT=$((attempt * 15))
  echo "   Cloudflare is busy ($(grep -Eo 'status [0-9]+' "$LOGDIR/tunnel.log" | head -1)); trying again in ${WAIT}s (attempt $attempt/6)…"
  sleep $WAIT
done
[ -n "$API_URL" ] || { echo "DEMO_FAILED: Cloudflare did not give a tunnel — wait a few minutes and start again"; tail -5 "$LOGDIR/tunnel.log"; read -r; exit 1; }
TTS_URL=""; curl -fs http://127.0.0.1:8010/health >/dev/null 2>&1 && TTS_URL="$API_URL/voice"
LINK="$SITE?api=$API_URL"; [ -n "$TTS_URL" ] && LINK="$LINK&tts=$TTS_URL"

# wait until the public address answers (DNS of a new tunnel can take a few seconds)
for i in $(seq 1 30); do curl -fs "$API_URL/ready" >/dev/null 2>&1 && break; sleep 2; done

echo "== Publishing the server address for the website…"
if publish_endpoint "{\"online\":true,\"api\":\"$API_URL\",\"tts\":\"$TTS_URL\",\"updated\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}"; then
  PUBLISHED=1; OPEN="$SITE"; echo "   done"
else
  echo "   PUBLISH_FAILED (see $LOGDIR/publish.log) — use the long link below instead"; OPEN="$LINK"
fi

printf '%s' "$OPEN" | pbcopy
echo ""
echo "=================================================================="
echo " DEMO_READY"
echo ""
if [ "$PUBLISHED" = 1 ]; then
  echo "   Website:  $SITE"
  echo "   (finds this server by itself on every device — just open it)"
else
  echo "   Open:     $LINK"
fi
echo ""
echo "   Backup link (only if the plain address does not connect):"
echo "   $LINK"
echo ""
echo " • Keep this window open and the Mac awake during the presentation."
echo " • Close this window (or press Ctrl+C) to stop the server."
echo "=================================================================="
open "$OPEN"
caffeinate -dimsu -w $$ &
wait
