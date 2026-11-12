"""Independent verifier for a notebook-23 run (2026 raw observed-record audit + positive-cell diagnostic). Imports NOTHING from the notebook,
runner or producer FUNCTIONS: it re-reads the pinned raw CSV with the csv module and re-derives counts, the exclusive ledger order, the monthly
ledger, the observed positive cells and every overall/monthly metric from the saved numeric predictions.

Usage (from the repository root):
    .venv/bin/python backend/scripts/verify_spatial_2026_evaluation.py --run-root backend/rerun-2026-eval-023-001
    .venv/bin/python backend/scripts/verify_spatial_2026_evaluation.py --run-root ... --json-out /tmp/verify_2026.json

Exit 0 when every check passes, 1 otherwise. Read-only: writes only the optional --json-out file (refused inside the run root).
"""
import argparse
import csv
import datetime as dt
import hashlib
import io
import json
import math
import sys
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

BACKEND = Path(__file__).resolve().parents[1]
ORDER = ['outside_window', 'exact_duplicate_after_first', 'invalid_date_time', 'agency_outside_doh_scope', 'invalid_or_unknown_route',
         'invalid_coordinates_or_province', 'outside_pilot_envelope', 'linkage_outside_50m', 'linkage_ambiguous', 'linkage_unknown',
         'no_accepted_segment', 'eligible']
ROW_LEVEL_COLUMNS = {'record_uid_internal', 'source_row', 'fingerprint', 'lat', 'lon', 'lat_value', 'lon_value', 'LATITUDE', 'LONGITUDE', 'segment_id',
                     'segment_id_2000m', 'chosen_distance_m', 'report_date', 'event_date'}
DOH = 'กรมทางหลวง'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def strict_load(p):
    def bad(c):
        raise ValueError('non-finite JSON constant ' + c + ' in ' + str(p))
    return json.loads(Path(p).read_text('utf-8'), parse_constant=bad)


def dmy(s):
    t = s.strip()
    parts = t.split('/')
    if len(parts) != 3 or not all(p.isdigit() and p.isascii() for p in parts) or not (1 <= len(parts[0]) <= 2 and 1 <= len(parts[1]) <= 2 and len(parts[2]) == 4):
        return None
    try:
        return dt.date(int(parts[2]), int(parts[1]), int(parts[0])).isoformat()
    except ValueError:
        return None


def hm(s):
    t = s.strip()
    parts = t.split(':')
    if len(parts) not in (2, 3) or not all(p.isdigit() and p.isascii() for p in parts) or not 1 <= len(parts[0]) <= 2 or any(len(p) != 2 for p in parts[1:]):
        return None
    h, m, x = int(parts[0]), int(parts[1]), int(parts[2]) if len(parts) == 3 else 0
    return h * 3600 + m * 60 + x if h < 24 and m < 60 and x < 60 else None


def unit_deviance(y, m):
    """2*(y*log y - y*log m - (y - m)) with the y == 0 log term := 0 (written differently from the producer on purpose)."""
    t = np.zeros(len(y))
    pos = y > 0
    t[pos] = y[pos] * (np.log(y[pos]) - np.log(m[pos]))
    return 2.0 * (t - (y - m))


def metrics(y, p, floor=None):
    """Raw metrics on unmodified lambdas; raw deviance null + status when a positive cell has lambda 0 (limit +inf); optional original-floor audit."""
    y, p = np.asarray(y, float), np.asarray(p, float)
    n, sy, e = len(y), float(y.sum()), p - y
    zero = int(((p <= 0) & (y > 0)).sum())
    status = 'unavailable_empty' if n == 0 else ('infinite_due_zero_prediction' if zero else 'finite')
    out = {'n_positive_cells': n, 'n_raw_records': int(sy), 'actual_total': sy, 'pred_total': float(p.sum()),
           'mean_poisson_deviance': float(unit_deviance(y, p).mean()) if status == 'finite' else None, 'deviance_status': status,
           'n_zero_pred_on_positive': zero, 'mae': float(np.abs(e).mean()) if n else None, 'rmse': float(math.sqrt((e ** 2).mean())) if n else None,
           'bias_pred_minus_actual': float(e.mean()) if n else None, 'wape': float(np.abs(e).sum() / sy) if sy > 0 else None,
           'pred_to_actual_ratio': float(p.sum() / sy) if sy > 0 else None}
    if floor is not None and n:
        low = p < floor
        d = unit_deviance(y, np.maximum(p, floor))
        out.update({'deviance_floor_audit': float(d.mean()), 'deviance_floor_audit_n_floored': int(low.sum()),
                    'deviance_floor_audit_floored_contribution': float(d[low].sum() / n)})
    return out


def lag_stats(ed, rd, snapshot, label_days, ref_months):
    """Per event month (UNKNOWN when the event date is unknown): lag counts, unknown/negative counts, quantiles, share > label days, min age and the
    late-arrival risk indicator (mean over records with a known event date of the share of Jan-Mar reference lags exceeding the record's age)."""
    import bisect
    snap = dt.date.fromisoformat(snapshot)
    month = [d[:7] if d else 'UNKNOWN' for d in ed]
    lag, st = [], []
    for e, r in zip(ed, rd):
        if r is None:
            lag.append(None), st.append('report_date_unknown')
        elif e is None:
            lag.append(None), st.append('event_date_unknown')
        else:
            x = (dt.date.fromisoformat(r) - dt.date.fromisoformat(e)).days
            lag.append(x), st.append('negative_lag_report_before_event' if x < 0 else 'ok')
    ref = sorted(x for x, s, e in zip(lag, st, ed) if s == 'ok' and int(e[5:7]) in ref_months)
    out = {}
    for m in sorted(set(month)):
        ii = [i for i in range(len(ed)) if month[i] == m]
        a = np.array([lag[i] for i in ii if st[i] == 'ok'], float)
        ages = [(snap - dt.date.fromisoformat(ed[i])).days for i in ii if ed[i] is not None]
        q = lambda v: float(np.quantile(a, v)) if len(a) else None
        out[m] = {'n_raw_records': len(ii), 'n_lag_known': int(len(a)), 'n_report_date_unknown': sum(st[i] == 'report_date_unknown' for i in ii),
                  'n_negative_lag': sum(st[i] == 'negative_lag_report_before_event' for i in ii), 'lag_median_days': q(0.5), 'lag_p90_days': q(0.9),
                  'lag_p95_days': q(0.95), 'lag_p99_days': q(0.99), 'lag_max_days': float(a.max()) if len(a) else None,
                  'share_lag_gt_label_days': float((a > label_days).mean()) if len(a) else None, 'min_age_at_snapshot_days': float(min(ages)) if ages else None,
                  'late_arrival_risk_indicator': (sum((len(ref) - bisect.bisect_right(ref, g)) / len(ref) for g in ages) / len(ages)) if ref and ages else None}
    return out, st


def expected_ranking(rows, min_support, top_n):
    """rows: dicts unit/method/dim/group/n_positive_cells/ratio (recomputed here). TRUE direction: under < 1, over > 1, total_match == 1."""
    out = {}
    for u, meth in sorted({(r['unit'], r['method']) for r in rows}):
        g = [r for r in rows if r['unit'] == u and r['method'] == meth and r['dim'] != 'overall' and r['n_positive_cells'] >= min_support and r['ratio'] is not None]
        under = sorted((r for r in g if r['ratio'] < 1), key=lambda r: (r['ratio'], r['dim'], r['group']))
        over = sorted((r for r in g if r['ratio'] > 1), key=lambda r: (-r['ratio'], r['dim'], r['group']))
        match = sorted((r for r in g if r['ratio'] == 1), key=lambda r: (r['dim'], r['group']))
        out[(u, meth)] = {'counts': (len(g), len(under), len(over), len(match)), 'under_predicted': [(r['dim'], r['group']) for r in under[:top_n]],
                          'over_predicted': [(r['dim'], r['group']) for r in over[:top_n]], 'total_match': [(r['dim'], r['group']) for r in match]}
    return out


def ranking_problems(RK, expected):
    """Compare the saved ranking with the independently expected one: membership/order, true direction of every ratio, explicit NONE rows, counts."""
    bad = []
    if set(zip(RK['unit'], RK['method'])) != set(expected):
        bad.append('unit/method combinations differ')
    for (u, meth), e in expected.items():
        sub = RK[(RK['unit'] == u) & (RK['method'] == meth)]
        cnt = sub[['n_supported_groups', 'n_groups_under', 'n_groups_over', 'n_groups_total_match']].drop_duplicates()
        if len(cnt) != 1 or tuple(int(float(x)) for x in cnt.iloc[0]) != e['counts']:
            bad.append((u, meth, 'counts'))
        for kind in ('under_predicted', 'over_predicted', 'total_match'):
            k = sub[sub['kind'] == kind]
            r = pd.to_numeric(k['pred_to_actual_ratio'], errors='coerce')
            if not e[kind] and kind != 'total_match':
                if not (len(k) == 1 and k.iloc[0]['group'] == 'NONE' and r.isna().all()):
                    bad.append((u, meth, kind, 'missing explicit NONE row'))
                continue
            if list(zip(k['dim'], k['group'])) != e[kind] or [int(float(x)) for x in k['rank']] != list(range(1, len(k) + 1)):
                bad.append((u, meth, kind, 'membership/order'))
            if (kind == 'under_predicted' and not (r < 1).all()) or (kind == 'over_predicted' and not (r > 1).all()) or (kind == 'total_match' and not (r == 1).all()):
                bad.append((u, meth, kind, 'wrong direction'))
    return bad


def close(a, b, tol=1e-9):
    if a is None or (isinstance(a, float) and math.isnan(a)):
        return b is None or (isinstance(b, float) and math.isnan(b))
    if b is None or (isinstance(b, float) and math.isnan(b)):
        return False
    return abs(float(a) - float(b)) <= tol * max(1.0, abs(float(a)))


def verify(run_root, backend=BACKEND):
    run_root, backend = Path(run_root), Path(backend)
    cfg = strict_load(backend / 'config' / 'spatial_2026_evaluation_v3.json')
    rep, dat = run_root / cfg['outputs']['report_dir'], run_root / cfg['outputs']['data_dir']
    checks = []

    def ck(name, ok, ev=None):
        checks.append({'check': name, 'status': 'pass' if ok else 'fail', 'evidence': ev})
        return ok

    man = strict_load(rep / 'evaluation_2026_manifest.json')
    ck('manifest strict JSON, status complete*, research only, production_ready false, every producer check passed',
       man.get('status') in ('complete', 'complete_diagnostic_unavailable') and man.get('production_ready') is False and man.get('research_only') is True
       and man.get('checks_failed') == 0 and all(c['status'] == 'pass' for c in man['checks']), {'status': man.get('status'), 'checks': len(man['checks'])})
    ck('protected paths unchanged during the run (manifest before == after)', man.get('protected_unchanged') is True and man['protected_before'] == man['protected_after'])
    files = sorted(p.name for p in rep.iterdir())
    ck('report dir = manifest report files + manifest (no extra/symlinked files)', files == sorted(list(man['report_files']) + ['evaluation_2026_manifest.json'])
       and not any((rep / f).is_symlink() for f in files), files)
    bad = [n for n, h in man['report_files'].items() if sha(rep / n) != h] + [n for n, h in man['data_files_gitignored'].items() if sha(dat / n) != h]
    ck('every report/data file hash equals the manifest', not bad, bad)
    for n in man['report_files']:
        if n.endswith('.json'):
            strict_load(rep / n)
    leak = []
    for n in man['report_files']:
        if n.endswith('.csv'):
            cols = set(pd.read_csv(rep / n, nrows=0).columns)
            if cols & ROW_LEVEL_COLUMNS:
                leak.append(n + ':' + ','.join(sorted(cols & ROW_LEVEL_COLUMNS)))
        if n.endswith(('.csv', '.md', '.json')) and 'r2026:' in (rep / n).read_text('utf-8'):
            leak.append(n + ':internal uid')
    ck('reports are aggregate only (no row-level columns, record ids or coordinates)', not leak, leak)

    # ---- raw source, independently ----
    sp = strict_load(backend / cfg['pins']['source'])
    src = backend / cfg['source']['new_csv']
    ck('raw snapshot hash equals the manager source pin', sha(src) == sp['files']['backend/' + cfg['source']['new_csv']])
    rows = list(csv.reader(io.StringIO(src.read_bytes().decode('utf-8-sig'), newline='')))
    header, body = rows[0], rows[1:]
    C = cfg['source']['columns']
    ix = {k: header.index(v) for k, v in C.items()}
    n = len(body)
    ck('raw row count equals the pin and the manifest', n == int(sp['new_snapshot']['rows']) == int(man['counts']['raw_records']), n)
    L = pd.read_csv(dat / 'row_ledger.csv', dtype=str, keep_default_na=False)
    ck('row ledger has one row per raw record in file order', len(L) == n and L['source_row'].tolist() == [str(i) for i in range(1, n + 1)])
    fp = [hashlib.sha256('\x1f'.join(r).encode('utf-8')).hexdigest() for r in body]
    ck('full-row fingerprints re-derived independently', fp == L['fingerprint'].tolist())
    seen, dup = set(), []
    for f in fp:
        dup.append(f in seen)
        seen.add(f)
    ed = [dmy(r[ix['event_date']]) for r in body]
    ck('explicit D/M/Y event dates re-derived', [d or '' for d in ed] == L['event_date'].tolist())
    tm = [hm(r[ix['event_time']]) for r in body]
    yr_ok = [d is not None and r[ix['year']].strip() == d[:4] for d, r in zip(ed, body)]
    w0, w1 = cfg['window']['start'], cfg['window']['end']
    doh = [unicodedata.normalize('NFKC', r[ix['agency']]).strip() == DOH for r in body]
    ck('DOH agency (exact NFKC string) agrees with the ledger source id', doh == (L['source_id'] == 'doh_highway').tolist())
    reason = []
    for i in range(n):
        g = L.iloc[i]
        flags = [ed[i] is not None and not (w0 <= ed[i] <= w1), dup[i], ed[i] is None or tm[i] is None or not yr_ok[i], not doh[i],
                 g['identity_status'] != 'verified',
                 g['coord_status'] != 'inside_broad_bbox_unverified' or g['precision_class'] == 'low_precision_unsuitable' or g['province'] == 'UNKNOWN',
                 g['scope'] == 'outside_envelope']
        # linkage flags apply to DOH + verified route + pilot-envelope + usable-precision coordinates (province validity is not a linkage input)
        scope_ok =doh[i] and g['identity_status'] == 'verified' and g['scope'] == 'pilot' and g['coord_status'] == 'inside_broad_bbox_unverified' \
            and g['precision_class'] != 'low_precision_unsuitable'
        st = g['status_50m']
        flags += [scope_ok and st == 'too_far', scope_ok and st in ('ambiguous_multiple', 'ambiguous_unsafe_geometry'),
                  scope_ok and st not in ('too_far', 'ambiguous_multiple', 'ambiguous_unsafe_geometry', 'matched'),
                  scope_ok and st == 'matched' and not (g['segment_status'] == 'assigned' and g['in_universe'] == 'True')]
        reason.append(next((ORDER[k] for k, f in enumerate(flags) if f), 'eligible'))
    mism = int(sum(a != b for a, b in zip(reason, L['exclusive_reason'])))
    ck('exclusive ordered reason re-derived for every raw record', mism == 0, {'mismatches': mism})
    R = pd.Series(reason)
    ck('reason totals equal the manifest counts', R.value_counts().to_dict() == {k: int(v) for k, v in man['counts']['reasons'].items()})
    month = pd.Series([d[:7] if d else 'UNKNOWN' for d in ed])
    lm = pd.crosstab(month, R).reindex(columns=ORDER, fill_value=0)
    rm = pd.read_csv(rep / 'ledger_by_month.csv', dtype={'event_month': str}).set_index('event_month')
    ck('monthly ledger reconciles (every reason x month, totals = raw rows)', (rm[ORDER].astype(int).sort_index() == lm.sort_index()).all().all()
       and int(rm['raw_records'].sum()) == n)
    ck('October and later excluded by the date rule', not any(d and d > w1 and r == 'eligible' for d, r in zip(ed, reason)))

    # ---- CKAN facts, date bounds, report lag/maturity, province/agency totals, old/new (independent) ----
    facts = strict_load(rep / 'source_facts.json')
    raw_bytes = src.read_bytes()
    pkg = strict_load(backend / cfg['source']['ckan'])
    res = [r for r in (pkg.get('result') or {}).get('resources', []) if r.get('id') == cfg['source']['resource_id']]
    fc = facts['ckan']
    ck('CKAN facts re-derived: resource id, last_modified (= saved package = source pin), size = file bytes, sha256 = pin, md5 flag; last_modified not a completeness proof',
       len(res) == 1 and fc['resource_id'] == cfg['source']['resource_id'] == sp['new_snapshot']['resource_id']
       and fc['last_modified'] == res[0].get('last_modified') == sp['new_snapshot']['last_modified']
       and int(res[0].get('size')) == len(raw_bytes) == int(fc['file_bytes']) == int(sp['new_snapshot']['bytes'])
       and facts['source_sha256'] == hashlib.sha256(raw_bytes).hexdigest() == sp['files']['backend/' + cfg['source']['new_csv']]
       and fc['ckan_hash_equals_file_md5'] == (res[0].get('hash') == hashlib.md5(raw_bytes).hexdigest())
       and facts.get('snapshot_last_modified_proves_completeness') is False, {'last_modified': fc.get('last_modified'), 'bytes': len(raw_bytes)})
    rd = [dmy(r[ix['report_date']]) for r in body]
    evd, rpd, nd = [d for d in ed if d], [d for d in rd if d], facts['new_snapshot_dates']
    ck('event/report date bounds, unknown report dates and exact duplicates re-derived',
       nd['raw_rows'] == n and nd['event_date_min'] == min(evd) and nd['event_date_max'] == max(evd) and nd['report_date_min'] == min(rpd)
       and nd['report_date_max'] == max(rpd) == sp['new_snapshot']['report_last_date'] and max(evd) == sp['new_snapshot']['event_last_date']
       and int(nd['report_date_status'].get('ok', 0)) == len(rpd) and sum(int(v) for k, v in nd['report_date_status'].items() if k != 'ok') == n - len(rpd)
       and int(nd['exact_full_row_duplicates_after_first']) == sum(dup),
       {'event': [min(evd), max(evd)], 'report': [min(rpd), max(rpd)], 'report_date_unknown': n - len(rpd)})
    M_ = cfg['metrics']
    want_lag, lag_st = lag_stats(ed, rd, cfg['source']['snapshot_report_last_date'], M_['label_assumption_days'], M_['lag_reference_months'])
    LG = pd.read_csv(rep / 'lag_by_month.csv', dtype={'event_month': str}, keep_default_na=False)
    bad = []
    for m, w in want_lag.items():
        row = LG[LG['event_month'] == m]
        if len(row) != 1 or row.iloc[0]['maturity'] != 'unverified':
            bad.append((m, 'row/maturity'))
            continue
        for k, v in w.items():
            got_v = pd.to_numeric(pd.Series([row.iloc[0][k]]), errors='coerce').iloc[0]
            if not close(v, None if pd.isna(got_v) else float(got_v)):
                bad.append((m, k))
    ck('lag by month re-derived (counts, unknown report date, negative lag, quantiles, share > 30 d, min age, late-arrival risk arithmetic); maturity unverified',
       not bad and len(LG) == len(want_lag), bad[:8])
    ck('row ledger lag status agrees with the independent lag status', lag_st == L['lag_status'].tolist())
    LP = pd.read_csv(rep / 'lag_by_province.csv', dtype={'province': str}, keep_default_na=False)
    lbp = pd.read_csv(rep / 'ledger_by_province.csv', dtype={'province': str}, keep_default_na=False).set_index('province')['raw_records'].astype(int)
    lba = pd.read_csv(rep / 'ledger_by_agency.csv', dtype={'agency': str}, keep_default_na=False).set_index('agency')['raw_records'].astype(int)
    ck('province/agency totals reconcile (lag_by_province = ledger_by_province = row ledger; agency ledger = row ledger; unknown/negative totals); maturity unverified',
       LP.set_index('province')['n_raw_records'].astype(int).sort_index().to_dict() == lbp.sort_index().to_dict() == L['province'].value_counts().sort_index().to_dict()
       and lba.sort_index().to_dict() == L['agency'].value_counts().sort_index().to_dict() and int(LP['n_raw_records'].astype(int).sum()) == n
       and int(LP['n_report_date_unknown'].astype(int).sum()) == lag_st.count('report_date_unknown')
       and int(LP['n_negative_lag'].astype(int).sum()) == lag_st.count('negative_lag_report_before_event') and (LP['maturity'] == 'unverified').all(),
       {'provinces': len(LP), 'agencies': len(lba)})
    op = backend / cfg['source']['original_csv']
    ck('original CSV hash equals the manager source pin', sha(op) == sp['files']['backend/' + cfg['source']['original_csv']])
    orows = list(csv.reader(io.StringIO(op.read_bytes().decode(cfg['source']['encoding']), newline='')))
    obody, oix = orows[1:], orows[0].index(C['event_date'])
    omon = [(dmy(r[oix]) or 'UNKNOWN')[:7] for r in obody]
    nmon = [d[:7] if d else 'UNKNOWN' for d in ed]
    ofp = [hashlib.sha256('\x1f'.join(r).encode('utf-8')).hexdigest() for r in obody]
    from collections import Counter
    oc, nc = Counter(zip(omon, ofp)), Counter(zip(nmon, fp))
    ON = pd.read_csv(rep / 'old_new_monthly.csv', dtype={'event_month': str}, keep_default_na=False).set_index('event_month')
    bad = []
    for m in sorted(set(omon) | set(nmon)):
        a, b = omon.count(m), nmon.count(m)
        both = sum(min(v, nc.get(k, 0)) for k, v in oc.items() if k[0] == m)
        if m not in ON.index or [int(ON.at[m, c]) for c in ('old_raw_records', 'new_raw_records', 'net_record_count_change', 'identical_full_rows_in_both')] != [a, b, b - a, both] \
                or 'not proven unique' not in ON.at[m, 'interpretation']:
            bad.append(m)
    ck('old/new monthly raw record counts, net change and identical full-row overlap re-derived (net change/revision, not unique late events)',
       not bad and len(ON) == len(set(omon) | set(nmon)) and int(ON['old_raw_records'].astype(int).sum()) == len(obody), bad[:5])

    # ---- cells, geography, all group metrics, deviance status/floor audit and ranking from saved numbers ----
    def read_str(p):
        return pd.read_csv(p, dtype=str, keep_default_na=False)

    el = L[R.to_numpy() == 'eligible']
    rtp = strict_load(backend / cfg['pins']['runtime'])
    c22 = backend / cfg['runtime']['config22']
    cfg22 = strict_load(c22)
    p22 = backend / cfg22['pins']['path']
    pins22 = strict_load(p22)
    c20_rel = cfg22['inputs']['config20']
    c20_ok = (sha(c22) == rtp['files'].get('backend/' + cfg['runtime']['config22']) and sha(p22) == rtp['files'].get('workflow/serving/' + p22.name)
              and sha(backend / c20_rel) == pins22['files'].get(cfg22['pins']['repo_prefix'] + c20_rel))
    floor = float(strict_load(backend / c20_rel)['metrics']['deviance_floor'])
    fa = facts.get('deviance_floor_audit') or {}
    ck('original notebook-20 deviance floor: config20 hash equals the pinned 22 input pins, floor unchanged = registered value = report facts',
       c20_ok and floor == float(cfg['metrics']['original_deviance_floor_audit']['expected_floor']) and fa.get('floor') == floor
       and fa.get('config20_sha256') == sha(backend / c20_rel), {'floor': floor, 'config20': c20_rel})
    MP = read_str(rep / 'multi_province.csv').set_index('unit') if (rep / 'multi_province.csv').exists() else None
    rank_rows, metric_rows = [], []
    for unit, keys in (('daily', ['segment_id_2000m', 'event_date']), ('6h', ['segment_id_2000m', 'event_date', 'time_block'])):
        k2 = ['segment_id', 'target_date'] + (['time_block'] if unit == '6h' else [])
        grp = el.groupby(keys, sort=True)
        exp = grp.size().rename('y').reset_index().rename(columns={'segment_id_2000m': 'segment_id', 'event_date': 'target_date'})
        prov = grp['province'].agg(lambda s: sorted(s.value_counts().items(), key=lambda kv: (-kv[1], str(kv[0])))[0][0]).to_numpy()
        nprov = grp['province'].nunique().to_numpy()
        got = read_str(dat / ('cells_' + unit + '.csv'))
        got['y'] = got['y'].astype(int)
        m = exp.merge(got[k2 + ['y']], on=k2, how='outer', suffixes=('_exp', '_got'), indicator=True)
        ck(unit + ': observed positive cells re-derived from eligible records (keys and y)', (m['_merge'] == 'both').all() and (m['y_exp'] == m['y_got']).all()
           and (got['y'] >= 1).all(), {'cells': len(exp)})
        gs = got.sort_values(k2).reset_index(drop=True)
        ck(unit + ': cell province = mode of recorded event province (ties lexical); multi-province counts reconcile',
           list(prov) == gs['province'].tolist() and [int(x) for x in nprov] == gs['n_provinces'].astype(int).tolist()
           and (MP is None or (int(MP.at[unit, 'multi_province_cells']) == int((nprov > 1).sum())
                               and int(MP.at[unit, 'raw_records_in_multi_province_cells']) == int(exp['y'].to_numpy()[nprov > 1].sum()))),
           {'multi_province_cells': int((nprov > 1).sum())})
        pp = dat / ('predictions_' + unit + '.csv')
        if not man['evaluation_available']:
            ck(unit + ': diagnostic unavailable -> no predictions or metrics fabricated', not pp.exists() and not (rep / 'metrics.csv').exists())
            continue
        P = read_str(pp)
        y, ps, pb = P['y'].astype(float).to_numpy(), P['pred_selected'].astype(float).to_numpy(), P['pred_baseline'].astype(float).to_numpy()
        ck(unit + ': predictions cover exactly the cells, same order, finite non-negative', P[k2].equals(got[k2]) and (y == got['y'].to_numpy()).all()
           and np.isfinite(np.r_[ps, pb]).all() and (np.r_[ps, pb] >= 0).all())
        d = pd.to_datetime(P['target_date'], format='%Y-%m-%d')
        m2s = {mm: s for s, ms in cfg['calendar']['seasons'].items() for mm in ms}
        fest = ['none'] * len(P)
        for name, (a, b) in cfg['calendar']['festivals'].items():
            fest = [name if a <= t <= b else f for t, f in zip(P['target_date'], fest)]
        G = {'month': P['target_date'].str[:7].tolist(), 'iso_week_start': [(t - dt.timedelta(days=t.weekday())).strftime('%Y-%m-%d') for t in d],
             'weekday': [('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')[t.weekday()] for t in d], 'season': [m2s.get(t.month, 'UNKNOWN') for t in d],
             'festival': fest, 'time_block_group': [b if b else 'day' for b in P['time_block']],
             'missing_context': ['context_complete' if r == 'context_complete' else 'core_fallback_missing_context' for r in P['routing_reason']]}
        ck(unit + ': calendar/time/context group labels re-derived from target date, block and routing reason', all(G[k] == P[k].tolist() for k in G)
           and P['province'].tolist() == got['province'].tolist() and P['route'].tolist() == got['route'].tolist())
        for dim in ('overall', 'month', 'iso_week_start', 'weekday', 'time_block_group', 'season', 'festival', 'province', 'route', 'missing_context', 'component_used'):
            labels = np.array(['all'] * len(P) if dim == 'overall' else P[dim].tolist(), dtype=object)
            for g in sorted(set(labels)):
                ii = labels == g
                for meth, p in (('selected', ps), ('strong_baseline', pb)):
                    w = metrics(y[ii], p[ii], floor)
                    w['n_segments'] = int(P.loc[ii, 'segment_id'].nunique())
                    metric_rows.append(dict(unit=unit, dim=dim, group=g, method=meth, **w))
                    rank_rows.append({'unit': unit, 'method': meth, 'dim': dim, 'group': g, 'n_positive_cells': w['n_positive_cells'], 'ratio': w['pred_to_actual_ratio']})
    if man['evaluation_available']:
        MS = read_str(rep / 'metrics.csv')
        bad = []
        for w in metric_rows:
            row = MS[(MS['unit'] == w['unit']) & (MS['dim'] == w['dim']) & (MS['group'] == w['group']) & (MS['method'] == w['method'])]
            if len(row) != 1:
                bad.append((w['unit'], w['dim'], w['group'], w['method'], 'row'))
                continue
            for k, v in w.items():
                if k in ('unit', 'dim', 'group', 'method'):
                    continue
                gv = row.iloc[0][k]
                if k == 'deviance_status':
                    ok = gv == v
                else:
                    num = pd.to_numeric(pd.Series([gv]), errors='coerce').iloc[0]
                    ok = close(v, None if pd.isna(num) else float(num))
                if not ok:
                    bad.append((w['unit'], w['dim'], w['group'], w['method'], k))
        ck('every group metric (all dims, both methods) recomputed from saved lambdas: totals, supports, raw deviance + status + zero-on-positive count, '
           'original-floor audit (value, floored count, contribution), MAE/RMSE/bias/WAPE/ratio', not bad and len(MS) == len(metric_rows), bad[:8])
        ov = [w for w in metric_rows if w['dim'] == 'overall']
        ck('overall raw deviance status and zero-on-positive counts (null only when limit is +inf)',
           all((w['mean_poisson_deviance'] is None) == (w['deviance_status'] != 'finite') for w in metric_rows),
           {w['unit'] + '/' + w['method']: {'status': w['deviance_status'], 'n_zero_pred_on_positive': w['n_zero_pred_on_positive'],
                                            'raw': w['mean_poisson_deviance'], 'floor_audit': w.get('deviance_floor_audit'),
                                            'n_floored': w.get('deviance_floor_audit_n_floored')} for w in ov})
        exp_rank = expected_ranking(rank_rows, int(cfg['metrics']['min_group_support_cells']), int(cfg['metrics']['rank_top_n']))
        RK = read_str(rep / 'under_over_ranking.csv')
        probs = ranking_problems(RK, exp_rank)
        ck('under/over ranking: true direction only (under < 1, over > 1), supports/order re-derived, explicit NONE row for an empty side', not probs,
           {'problems': probs[:8], 'counts': {u + '/' + mt: e['counts'] for (u, mt), e in exp_rank.items()}})
        md = (rep / 'report_2026_th.md').read_text('utf-8')
        no_over = [k for k, e in exp_rank.items() if e['counts'][2] == 0]
        ck('Thai report: deviance status/zero-on-positive/floor-audit columns in the main table; honest "no over-predicted group" statement; no legacy over label',
           all(c in md for c in ('deviance_status', 'n_zero_pred_on_positive', 'deviance_floor_audit')) and 'most_over_predicted' not in md
           and md.count('ไม่มีกลุ่มใดที่ทำนายสูงกว่าจริง') >= len(no_over), {'unit_methods_without_over_groups': [u + '/' + mt for u, mt in no_over]})
    cov = pd.read_csv(rep / 'coverage_flags.csv')
    ck('coverage flags: unobserved cells reported unknown (never zero) and no full-population metric', (cov['zero_label_status'] == 'unverified_unknown_not_zero').all()
       and (cov['full_population_metric'] == 'not_available').all() and (cov['unknown_cells'] + cov['observed_positive_cells'] == cov['requested_cells']).all())
    return checks


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--run-root', required=True)
    ap.add_argument('--json-out')
    a = ap.parse_args(argv)
    try:
        checks = verify(a.run_root)
    except Exception as e:
        checks = [{'check': 'verifier completed', 'status': 'fail', 'evidence': type(e).__name__ + ': ' + str(e)[:500]}]
    ok = all(c['status'] == 'pass' for c in checks)
    for c in checks:
        print(('PASS ' if c['status'] == 'pass' else 'FAIL ') + c['check'])
    print(('ALL PASS' if ok else 'FAILED') + ' (' + str(sum(c['status'] == 'pass' for c in checks)) + '/' + str(len(checks)) + ')')
    if a.json_out:
        out = Path(a.json_out).resolve()
        if Path(a.run_root).resolve() in out.parents:
            print('refusing --json-out inside the run root', file=sys.stderr)
            return 1
        out.write_text(json.dumps({'run_root': str(Path(a.run_root).resolve()), 'ok': ok, 'checks': checks}, indent=2, ensure_ascii=False, default=str), 'utf-8')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
