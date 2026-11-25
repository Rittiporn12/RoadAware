"""'ย้อนดูผล' (look back): recorded accidents per road segment and day, for days the served model never trained on.

The file and its sha256 come from backend/scripts/build_review_actuals.py (workflow/api/review-pins-v1.json); the file is
hash-checked before it is read and kept in memory afterwards. No coordinates and no record ids are ever returned.
"""
import csv
import hashlib
import json
import re
import threading
from datetime import date
from pathlib import Path

MAX_SEGMENTS = 3000
MAX_DAYS = 92
DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')


class ReviewError(Exception):
    def __init__(self, status, code, message):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


class ReviewData:
    def __init__(self, repo, pins_rel='workflow/api/review-pins-v1.json'):
        self.repo, self.pins_rel = Path(repo), pins_rel
        self._lock = threading.Lock()
        self._by_seg = None
        self._pins = None

    def _load(self):
        with self._lock:
            if self._by_seg is not None:
                return
            try:
                pins = json.loads((self.repo / self.pins_rel).read_text('utf-8'))
                p = self.repo / pins['output']
                h = hashlib.sha256(p.read_bytes()).hexdigest()
            except (OSError, ValueError, KeyError) as e:
                raise ReviewError(503, 'review_unavailable', 'look-back data is not available on this server') from e
            if h != pins.get('output_sha256'):
                raise ReviewError(503, 'review_unavailable', 'look-back data failed verification')
            by = {}
            with open(p, newline='', encoding='utf-8') as f:
                for r in csv.DictReader(f):
                    by.setdefault(r['segment_id'], []).append((r['date'], int(r['count'])))
            self._pins, self._by_seg = pins, by

    def query(self, body):
        if not isinstance(body, dict) or set(body) != {'segment_ids', 'start', 'end'}:
            raise ReviewError(400, 'invalid_fields', 'body must be {segment_ids, start, end}')
        ids, start, end = body['segment_ids'], body['start'], body['end']
        if not isinstance(ids, list) or not ids or len(ids) > MAX_SEGMENTS or not all(isinstance(s, str) and 0 < len(s) < 200 for s in ids):
            raise ReviewError(400, 'invalid_segment_ids', 'segment_ids must be 1..' + str(MAX_SEGMENTS) + ' strings')
        if not all(isinstance(d, str) and DATE_RE.match(d) for d in (start, end)):
            raise ReviewError(400, 'invalid_date', 'start/end must be YYYY-MM-DD')
        try:
            d0, d1 = date.fromisoformat(start), date.fromisoformat(end)
        except ValueError:
            raise ReviewError(400, 'invalid_date', 'start/end must be real dates')
        if d1 < d0 or (d1 - d0).days + 1 > MAX_DAYS:
            raise ReviewError(400, 'invalid_range', 'end must be on/after start and the range at most ' + str(MAX_DAYS) + ' days')
        self._load()
        periods = self._pins['periods']
        lo, hi = min(p['start'] for p in periods), max(p['end'] for p in periods)  # the periods are contiguous (2024-01-01..2026-09-30)
        if not (lo <= start and end <= hi):
            raise ReviewError(400, 'outside_review_periods', 'look-back is available for ' + lo + '..' + hi)
        kinds = [p['kind'] for p in periods if not (end < p['start'] or start > p['end'])]
        kind = kinds[0] if len(kinds) == 1 else 'mixed'
        out = []
        for s in dict.fromkeys(ids):
            for d, n in self._by_seg.get(s, ()):
                if start <= d <= end:
                    out.append({'segment_id': s, 'date': d, 'count': n})
        return {'ok': True, 'start': start, 'end': end, 'period_kind': kind, 'periods': periods,
                'total_records': sum(r['count'] for r in out), 'counts': out,
                'note': 'recorded accidents on DOH highway segments (selected + linked records); not every crash is recorded'}
