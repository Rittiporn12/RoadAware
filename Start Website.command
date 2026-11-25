#!/bin/bash
# RoadAware website (prepared by Claude). Double-click in Finder. Uses port 3000 (allowed by the API) so it does not clash with other apps on 5173.
cd "$(dirname "$0")/frontend" || exit 1
[ -d node_modules ] || npm install
( sleep 4; open "http://127.0.0.1:3000/" ) &
npm run dev -- --host 127.0.0.1 --port 3000 --strictPort
