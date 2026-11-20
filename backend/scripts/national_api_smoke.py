"""Smoke-test a running RoadAware API (national V4) over real HTTP. Usage: .venv/bin/python backend/scripts/national_api_smoke.py [port]"""
import json, sys, urllib.request
BASE = 'http://127.0.0.1:' + (sys.argv[1] if len(sys.argv) > 1 else '8000')


def call(path, body=None):
    req = urllib.request.Request(BASE + path, data=None if body is None else json.dumps(body).encode(), method='GET' if body is None else 'POST',
                                 headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read() or b'{}')
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b'{}')


ok = True
s, ready = call('/ready'); print('/ready', s, json.dumps(ready, ensure_ascii=False)[:600]); ok &= s == 200
places = {'Bangkok-Saraburi (ทล.1)': '100.55,14.00,100.75,14.35', 'Chiang Mai': '98.90,18.70,99.10,18.90', 'Hat Yai': '100.40,6.95,100.55,7.10',
          'Khon Kaen': '102.75,16.35,102.90,16.50', 'Phuket': '98.30,7.85,98.45,8.00'}
for name, bbox in places.items():
    s, g = call('/api/v1/segments?bbox=' + bbox + '&limit=5')
    feats = g.get('features') or []
    print(f'segments {name}: HTTP {s}, {len(feats)} shown')
    ok &= s == 200
    if feats:
        sid = feats[0].get('id') or feats[0]['properties'].get('segment_id')
        s, p = call('/api/v1/spatial/predictions', {'unit': '6h', 'requests': [{'segment_id': sid, 'target_date': '2026-12-31', 'time_block': '18-24'}]})
        r = (p.get('results') or [{}])[0]
        print(f'   predict {sid}: HTTP {s} colour={r.get("colour")} expected={r.get("expected_recorded_count")}')
        s2, hh = call('/api/v1/spatial/history', {'segment_id': sid, 'target_date': '2026-12-31', 'unit': 'daily', 'lookback_days': 1827, 'top_k': 3})
        print(f'   history: HTTP {s2} records={((hh.get("history") or {}).get("total_records"))}')
        ok &= s == 200 and r.get('colour') is not None and s2 == 200
print('SMOKE', 'OK' if ok else 'FAILED')
sys.exit(0 if ok else 1)
