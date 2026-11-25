"""Build the 'ย้อนดูผล' (look back) data: recorded accidents per road segment per day, only for days the model never
trained on (prepared by Claude).

    python3 backend/scripts/build_review_actuals.py [--ledger backend/rerun-2026-eval-national-<id>/data/v4/evaluation_2026/row_ledger.csv]

* 2024-01-01 .. 2025-12-31: notebook-19 national daily counts (selected + linked DOH records; model trained to 2023-12-01)
* 2026-01-01 .. 2026-09-30: notebook-23 national row ledger, eligible records only (the unseen 2026 test set)
Writes backend/data/v4/review/actual_daily.csv (segment_id,date,count) and workflow/api/review-pins-v1.json with the
sha256 of the output and of every input, which the API checks before serving it. No coordinates, no row-level ids.
"""
import argparse
import glob
import hashlib
import json
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[2]
COUNTS = 'backend/data/v4/spatial_preparation/counts_daily.csv.gz'
OUT = 'backend/data/v4/review/actual_daily.csv'
PINS = 'workflow/api/review-pins-v1.json'
START_SEEN, END_SEEN = '2024-01-01', '2025-12-31'
START_TEST, END_TEST = '2026-01-01', '2026-09-30'


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ledger', default=None)
    a = ap.parse_args()
    ledger = a.ledger or sorted(glob.glob(str(REPO / 'backend/rerun-2026-eval-national-*/data/v4/evaluation_2026/row_ledger.csv')))[-1]
    ledger = str(Path(ledger).resolve().relative_to(REPO))
    c = pd.read_csv(REPO / COUNTS, dtype={'segment_id': str, 'target_date': str})
    c = c[(c.target_date >= START_SEEN) & (c.target_date <= END_SEEN) & (c.y_count > 0)]
    c = c.rename(columns={'target_date': 'date', 'y_count': 'count'})[['segment_id', 'date', 'count']]
    l = pd.read_csv(REPO / ledger, dtype=str, usecols=['event_date', 'segment_id_2000m', 'exclusive_reason'])
    l = l[(l.exclusive_reason == 'eligible') & (l.event_date >= START_TEST) & (l.event_date <= END_TEST)]
    l = l.groupby(['segment_id_2000m', 'event_date']).size().reset_index(name='count')
    l = l.rename(columns={'segment_id_2000m': 'segment_id', 'event_date': 'date'})
    out = pd.concat([c, l]).sort_values(['date', 'segment_id']).reset_index(drop=True)
    out['count'] = out['count'].astype(int)
    p = REPO / OUT
    p.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(p, index=False, lineterminator='\n')
    pins = {
        'kind': 'roadaware_review_actuals_v1',
        'note': 'Recorded accidents per segment per day on days the served model never trained on (training cut-off 2023-12-01). '
                '2024-2025 are previously-seen diagnostic years; 2026 Jan-Sep is the unseen national test set. For the look-back view only.',
        'output': OUT, 'output_sha256': sha(p), 'rows': int(len(out)), 'records': int(out['count'].sum()),
        'periods': [{'start': START_SEEN, 'end': END_SEEN, 'kind': 'seen_diagnostic', 'records': int(c['count'].sum())},
                    {'start': START_TEST, 'end': END_TEST, 'kind': 'unseen_test_2026', 'records': int(l['count'].sum())}],
        'inputs': {COUNTS: sha(REPO / COUNTS), ledger: sha(REPO / ledger)},
    }
    (REPO / PINS).write_text(json.dumps(pins, indent=2, ensure_ascii=False) + '\n', 'utf-8')
    print(json.dumps({k: pins[k] for k in ('rows', 'records', 'periods')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
