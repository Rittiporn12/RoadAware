"""Tests for notebook 14 (historical catalog V3). They exec ONLY the five '# FUNCTIONS' cells of the assembled source notebook on tiny
synthetic fixtures in temp dirs (no kernel, no real data, no writes into the repository). Run from the repository root after assembling:
    .venv/bin/python -m pytest backend/tests/test_historical_catalog_notebook.py -q
"""
import copy
import gzip
import hashlib
import importlib.util
import json
import os
import re
from pathlib import Path, PurePosixPath

import numpy as np
import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[2]
BACKEND = REPO / 'backend'
NB = BACKEND / 'notebooks' / '14_backend_catalog.ipynb'
CFG = json.loads((BACKEND / 'config' / 'catalog_v3.json').read_text('utf-8'))
BK, P2 = 'กรุงเทพมหานคร', 'นนทบุรี'
H64 = ['ปีที่เกิดเหตุ', 'ACC_CODE', 'ลักษณะการเกิดเหตุ', 'มูลเหตุสันนิษฐาน', 'สภาพอากาศ']
H65 = ['ปีที่เกิดเหตุ', 'ACC_CODE', 'ลักษณะการเกิดอุบัติเหตุ', 'มูลเหตุสันนิษฐาน']  # other alias, no weather header


@pytest.fixture(scope='module')
def F():
    cells = json.loads(NB.read_text('utf-8'))['cells']
    funcs = [''.join(c['source']) for c in cells if c['cell_type'] == 'code' and ''.join(c['source']).lstrip().startswith('# FUNCTIONS')]
    assert len(funcs) == 5
    ns = {'__name__': 'nb14_functions'}
    for i, s in enumerate(funcs):
        exec(compile(s, 'nb14:FUNCTIONS[' + str(i) + ']', 'exec'), ns)
    return ns


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def fixture_cfg():
    c = copy.deepcopy(CFG)
    c['catalog'].update(expected_provinces=2, last_month='2022-12', coverage_years=[2021, 2022, 2023])
    c['controls']['n_bruteforce_queries'] = 40
    return c


RAW64 = [['2564', ' A1 ', 'ชน  ท้าย ', 'ขับเร็ว', 'แจ่มใส'], ['2564', 'A2', 'พลิกคว่ำ', '', 'ฝนตก'], ['2564', 'A3', 'ชนท้าย', 'หลับใน', ''],
         ['2564', 'AX', 'x', 'x', 'x']]
RAW65 = [['2565', 'B1', 'ชนท้าย', 'ขับเร็ว'], ['2565', 'B2', '', 'ตัดหน้า']]
EVENTS = [('2564:A1', '2021', '2021-03-10', '50000', '12-18', BK), ('2564:A2', '2021', '2021-05-01', '', '', P2),
          ('2564:A3', '2021', '2021-12-31', '80000', '18-24', BK), ('2565:B1', '2022', '2022-01-15', '3600', '00-06', P2),
          ('2565:B2', '2022', '2022-07-04', '30000', '06-12', BK)]
ROWS = {'2564:A1': ('accidents_2564_original.csv', '2'), '2564:A2': ('accidents_2564_original.csv', '3'), '2564:A3': ('accidents_2564_original.csv', '4'),
        '2565:B1': ('accidents_2565_original.csv', '2'), '2565:B2': ('accidents_2565_original.csv', '3')}
SEL = [('2564:A1', 'S1'), ('2564:A3', 'S1'), ('2565:B1', 'S2'), ('2565:B2', 'S1')]


def build_world(tmp, mutate=None):
    """Synthetic backend + repo with every pinned input, producer manifests consistent with the hashes, and manager pins."""
    b, repo, cfg = tmp / 'backend', tmp, fixture_cfg()
    W = {'backend': b, 'repo': repo, 'cfg': cfg, 'events': pd.DataFrame(EVENTS, columns=['event_uid', 'source_year_ce', 'event_date', 'time_sec', 'time_block', 'province_key']),
         'raw64': pd.DataFrame(RAW64, columns=H64), 'raw65': pd.DataFrame(RAW65, columns=H65)}
    W['events']['date_decision'], W['events']['date_confidence'] = 'x', 'x'
    lin = [{'event_uid': u, 'source_file': ROWS[u][0], 'source_year': u[:4], 'source_year_ce': y, 'source_row': ROWS[u][1], 'acc_code': u[5:],
            'v2_disposition': 'retained', 'event_date_v2': d, 'time_sec': t, 'province_key': p} for u, y, d, t, _, p in EVENTS]
    lin.append({'event_uid': '2564:AX', 'source_file': 'accidents_2564_original.csv', 'source_year': '2564', 'source_year_ce': '2021', 'source_row': '5',
                'acc_code': 'AX', 'v2_disposition': 'quarantined', 'event_date_v2': '', 'time_sec': '', 'province_key': ''})
    W['lineage'] = pd.DataFrame(lin)
    W['legacy'] = pd.DataFrame([('2564:A1', 'ชน ท้าย', 'ขับเร็ว', 'แจ่มใส'), ('2564:A3', 'ชนท้าย', 'หลับใน', ''), ('2564:Z9', 'q', 'q', 'q')],
                               columns=['event_uid', 'accident_type', 'presumed_cause', 'weather'])
    ev = {e[0]: e for e in EVENTS}
    W['selected'] = pd.DataFrame([{'event_uid': u, 'ce_year': ev[u][1], 'split': 'train', 'event_date': ev[u][2], 'time_block': ev[u][4],
                                   'province_key': ev[u][5], 'segment_id_2000m': s, 'chosen_source_oid': '1', 'chosen_part': '0', 'chosen_piece': '0'}
                                  for u, s in SEL])
    if mutate:
        mutate(W)
    for d in ('data/raw/accidents', 'data/v2', 'data/interim', 'data/v3/spatial_preparation', 'reports/v2/preparation', 'reports/v2/sources',
              'reports/v3/spatial_preparation', 'config', 'notebooks'):
        (b / d).mkdir(parents=True, exist_ok=True)
    raws = []
    for be, df in ((2564, W['raw64']), (2565, W['raw65'])):
        rel = 'data/raw/accidents/accidents_%d_original.csv' % be
        df.to_csv(b / rel, index=False, encoding='utf-8-sig')
        raws.append({'be_year': be, 'ce_year': be - 543, 'file': Path(rel).name, 'original_path': '/elsewhere/' + rel, 'path': rel, 'sha256': sha(b / rel),
                     'bytes': (b / rel).stat().st_size, 'encoding': 'utf-8-sig', 'rows': len(df), 'n_columns': len(df.columns), 'columns': list(df.columns)})
    W['raw_entries'] = raws
    if 'raw_manifest_hook' in W:
        W['raw_manifest_hook'](raws)
    I = {k: v['path'] for k, v in cfg['inputs'].items()}
    (b / I['raw_manifest']).write_text(json.dumps({'files': raws}), 'utf-8')
    W['events'].to_csv(b / I['events_v2'], index=False)
    W['lineage'].to_csv(b / I['row_lineage_v2'], index=False)
    W['legacy'].to_csv(b / I['legacy_descriptive'], index=False)
    (b / I['data_pipeline']).write_text(json.dumps({'schema_aliases': {'acc_code': ['ACC_CODE'], 'presumed_cause': ['มูลเหตุสันนิษฐาน'],
                                                                       'accident_type': ['ลักษณะการเกิดเหตุ', 'ลักษณะการเกิดอุบัติเหตุ'], 'weather': ['สภาพอากาศ']}}), 'utf-8')
    (b / I['sources_manifest']).write_text('{}', 'utf-8')
    pd.DataFrame([{'province_code': '10', 'name_th': BK, 'name_en': 'Bangkok', 'lat': 13.7, 'lon': 100.6, 'point_meaning': 'representative', 'province_key': BK},
                  {'province_code': '12', 'name_th': P2, 'name_en': 'Nonthaburi', 'lat': 13.9, 'lon': 100.5, 'point_meaning': 'representative', 'province_key': P2}]
                 ).to_csv(b / I['province_points'], index=False)
    W['selected'].to_csv(b / I['selected_events'], index=False)
    pd.DataFrame({'segment_id': ['S1', 'S2', 'S3'], 'route_code': '1'}).to_csv(b / I['universe_segments'], index=False)
    S = W['selected']
    S.groupby(['segment_id_2000m', 'event_date']).size().rename('y_count').reset_index().rename(columns={'segment_id_2000m': 'segment_id', 'event_date': 'target_date'}
                                                                                               ).to_csv(b / I['counts_daily'], index=False)
    S.groupby(['segment_id_2000m', 'event_date', 'time_block']).size().rename('y_count').reset_index().rename(
        columns={'segment_id_2000m': 'segment_id', 'event_date': 'target_date'}).to_csv(b / I['counts_6h'], index=False)
    root = '/orig/backend/'
    m10 = {'producer': '10_v2_preparation_features_leakage', 'schema': 'roadaware-v2-preparation-manifest/1', 'status': 'completed',
           'inputs': [{'role': '09_sources_manifest', 'path': root + I['sources_manifest'], 'sha256': sha(b / I['sources_manifest'])},
                      {'role': 'config', 'path': root + I['data_pipeline'], 'sha256': sha(b / I['data_pipeline'])},
                      {'role': 'v1_raw_manifest', 'path': root + I['raw_manifest'], 'sha256': sha(b / I['raw_manifest'])},
                      {'role': 'v1_interim', 'path': root + I['legacy_descriptive'], 'sha256': sha(b / I['legacy_descriptive'])},
                      {'role': '09_output', 'path': root + I['province_points'], 'sha256': sha(b / I['province_points'])}] +
                     [{'role': 'v1_raw_csv', 'path': root + r['path'], 'sha256': r['sha256']} for r in raws],
           'data_outputs': [{'path': Path(I[k]).name, 'sha256': sha(b / I[k]), 'bytes': (b / I[k]).stat().st_size} for k in ('events_v2', 'row_lineage_v2')]}
    if 'm10_hook' in W:
        W['m10_hook'](m10)
    (b / I['preparation_manifest']).write_text(json.dumps(m10), 'utf-8')
    (b / I['spatial_preparation_manifest']).write_text(json.dumps({'status': 'complete', 'data_files_gitignored': {
        Path(I[k]).name: sha(b / I[k]) for k in ('selected_events', 'universe_segments', 'counts_daily', 'counts_6h')}}), 'utf-8')
    (b / I['spatial_review']).write_text(json.dumps({'status': 'accepted_spatial_count_preparation_only', 'selected_events': len(S), 'universe_segments': 3}), 'utf-8')
    (b / 'config' / 'catalog_v3.json').write_text(json.dumps(cfg), 'utf-8')
    pins = {'schema': 'roadaware-catalog-input-pins/1', 'registered_before_catalog_implementation': True, 'files': {p: sha(b / p) for p in I.values()}}
    (repo / 'workflow' / 'catalog').mkdir(parents=True, exist_ok=True)
    (repo / cfg['pins']['path']).write_text(json.dumps(pins), 'utf-8')
    return W


def pipeline(F, W):
    """The notebook's flow, function by function, on the fixture world."""
    b, cfg, I = W['backend'], W['cfg'], {k: v['path'] for k, v in W['cfg']['inputs'].items()}
    pins, pins_sha = F['load_pins'](W['repo'], cfg)
    rows, docs = F['verify_inputs'](b, cfg, pins)
    rd = F['read_str_csv']
    ev, lin, leg = rd(b / I['events_v2']), rd(b / I['row_lineage_v2']), rd(b / I['legacy_descriptive'])
    J = F['join_retained_lineage'](ev, lin, cfg)
    raw = F['verify_raw_sources'](b, cfg, docs['raw_manifest'], docs['preparation_manifest'], set(J['source_file']))
    rec0, prov = F['recover_descriptions'](J, raw, docs['data_pipeline']['schema_aliases'], lambda f: F['read_raw_csv'](raw[f]['path'], raw[f]['entry']))
    rec, cov, summ = F['compare_legacy'](rec0, leg)
    P = F['load_provinces'](rd(b / I['province_points']), cfg['catalog']['expected_provinces'])
    months = F['month_range'](cfg['catalog']['first_month'], cfg['catalog']['last_month'])
    F['check_event_domain'](rec, P, months)
    PM, PC = F['province_tables'](rec, P, months)
    uni = rd(b / I['universe_segments'])['segment_id'].tolist()
    R = F['spatial_rows'](rd(b / I['selected_events']), rec, uni)
    mon, tot, seg, scov = F['spatial_tables'](R, uni, months, cfg['catalog']['coverage_years'])
    return {'pins_sha': pins_sha, 'inputs': rows, 'docs': docs, 'events': ev, 'rec': rec, 'cov': cov, 'summary': summ, 'P': P, 'months': months, 'PM': PM, 'PC': PC,
            'uni': uni, 'R': R, 'mon': mon, 'seg': seg, 'prec': F['reconcile_province'](PM, PC, rec, P, months),
            'srec': F['reconcile_spatial'](R, rd(b / I['selected_events']), uni, rd(b / I['counts_daily']), rd(b / I['counts_6h']), docs['spatial_review'], mon, seg)}


def export(F, W, X, tmp):
    rep, data = tmp / 'out' / 'rep', tmp / 'out' / 'data'
    rf, df = {}, {}
    for name, d in (('province_monthly.csv', X['PM']), ('province_category_monthly.csv', X['PC'])):
        F['atomic_write_bytes'](rep / name, F['csv_bytes'](d))
        rf[name] = sha(rep / name)
    F['atomic_write_bytes'](data / 'selected_history_rows.csv.gz', gzip.compress(F['csv_bytes'](X['R']), mtime=0))
    F['atomic_write_bytes'](data / 'universe_segment_ids.csv', F['csv_bytes'](pd.DataFrame({'segment_id': sorted(X['uni'])})))
    F['atomic_write_json'](data / 'provinces.json', {'provinces': X['P'].to_dict('records')})
    for n in ('selected_history_rows.csv.gz', 'universe_segment_ids.csv', 'provinces.json'):
        df[n] = sha(data / n)
    cells = F['notebook_code_cells'](NB)
    fsha = F['functions_sha'](cells)
    cfgp = W['backend'] / 'config' / 'catalog_v3.json'
    man = F['build_manifest']('complete', W['cfg'], sha(cfgp), X['pins_sha'], 'notebooks/14_backend_catalog.ipynb', sha(NB), fsha, F['code_cells_sha'](cells),
                              [], [], rf, df, F['environment'](), {}, [{'check': 'fixture', 'status': 'pass'}], {}, {}, F['utcnow']())
    F['atomic_write_json'](rep / 'catalog_manifest.json', man)
    return rep, data, cfgp, sha(rep / 'catalog_manifest.json'), fsha


def view_of(F, W, X):
    return F['build_catalog_view'](W['cfg'], X['P'].to_dict('records'), X['PM'], X['PC'], X['uni'], X['R'], 'test')


# ---------- happy path ----------
def test_fixture_recovery_province_spatial_and_controls(F, tmp_path):
    W = build_world(tmp_path)
    X = pipeline(F, W)
    rec = X['rec'].set_index('event_uid')
    assert len(rec) == 5 and '2564:AX' not in rec.index and '2564:Z9' not in rec.index  # no raw-only or legacy-only records
    assert rec.loc['2564:A1', 'accident_type'] == 'ชน ท้าย'  # V1 whitespace normalisation
    assert rec.loc['2565:B1', 'accident_type'] == 'ชนท้าย'  # alias differs by year
    assert rec.loc['2565:B1', 'weather'] == '' and rec.loc['2564:A3', 'weather'] == ''  # missing header and real blank stay unknown
    assert rec.loc['2564:A2', 'time_block'] == '' and rec.loc['2564:A2', 'event_date'] == '2021-05-01'  # accepted values, never re-parsed
    cov = X['cov'].set_index('field')
    assert cov.loc['accident_type', 'unknown_before_recovery'] == 3 and cov.loc['accident_type', 'unknown_after_recovery'] == 1
    assert cov.loc['weather', 'unknown_after_recovery'] == 3 and X['summary']['legacy_matched'] == 2 and X['summary']['legacy_uids_not_accepted_events'] == 1
    assert (X['rec']['legacy_status'] == 'repaired_recovered').sum() == 3
    PM = X['PM']
    assert len(PM) == 2 * 24 and PM['n_records'].sum() == 5 and (PM['n_records'] == 0).sum() == 2 * 24 - 5
    assert PM['unknown_time_block'].sum() == 1 and (PM['known_time_block'] + PM['unknown_time_block'] == PM['n_records']).all()
    assert X['prec']['ok'].all() and X['srec']['ok'].all()
    assert set(X['R'].columns) == set(F['SPATIAL_ROW_COLS']) and len(X['R']) == 4
    seg = X['seg'].set_index('segment_id')
    assert seg.loc['S3', 'n_selected_total'] == 0 and seg.loc['S3', 'history_status'] == 'empty_selected_history_not_safety'
    ctrl = F['run_query_controls'](view_of(F, W, X), X['R'], W['cfg'], X['rec']['event_uid'])
    assert ctrl['ok'].all(), ctrl[~ctrl['ok']].to_dict('records')
    names = ' | '.join(ctrl['control'])
    assert 'detector flags planted real retained UID' in names and 'exact match against 5 retained UIDs' in names


def test_spatial_cutoff_rule_exact(F, tmp_path):
    W = build_world(tmp_path)
    X = pipeline(F, W)
    v = view_of(F, W, X)
    q = lambda td, unit, **k: F['query_spatial_history'](v, {'segment_id': 'S1', 'target_date': td, 'unit': unit, **k})['n_selected_records']
    # A1: 2021-03-10 block 12-18 ends 18:00 == cutoff of target 2021-04-10 (issue 04-09 18:00 - 30 d)
    assert q('2021-04-10', '6h', time_block='00-06') == 1 and q('2021-04-09', '6h', time_block='00-06') == 0
    # daily: day end 2021-03-11 00:00 <= cutoff needs target >= 2021-04-11
    assert q('2021-04-11', 'daily') == 1 and q('2021-04-10', 'daily') == 0
    e = int(F['event_end_seconds'](['2021-03-10'], ['12-18'], '6h')[0])
    assert F['history_eligible']([e], e, e - 10)[0] and not F['history_eligible']([e], e - 1, e - 10)[0]
    r = F['query_spatial_history'](v, {'segment_id': 'S1', 'target_date': '2021-04-10', 'unit': '6h', 'time_block': '12-18'})
    assert r['issue_time_local'] == '2021-04-09T18:00:00+07:00' and r['history_cutoff_local'] == '2021-03-10T18:00:00+07:00'
    assert r['n_same_time_block'] == 1 and r['categories']['weather']['known_records'] == 1
    assert sum(m['records'] for m in r['counts_by_month']) == r['n_selected_records']
    # lookback window: 1 day before cutoff still contains A1's block end
    assert q('2021-04-10', '6h', time_block='00-06', lookback_days=1) == 1
    # no future history: a target before any record ends has N=0 and is flagged not-safety
    r0 = F['query_spatial_history'](v, {'segment_id': 'S3', 'target_date': '2027-12-31', 'unit': 'daily'})
    assert r0['n_selected_records'] == 0 and r0['empty_history_is_not_safety'] is True
    assert not F['leaked_keys'](r0) and not F['leaked_keys'](r)
    assert not F['public_result_violations'](r, 'spatial') and not F['public_result_violations'](r0, 'spatial')


# ---------- privacy controls: explicit public schema + exact retained-UID detection (correction 020a) ----------
# Real universe ids look like this; DOH route numbers 25xx made the old '25dd:' shape regex flag 4 public ids in run 020-002.
REAL_SHAPE = 'rsv1-rc31f3d87fc7:doh:%s:p0:c0:r2000:%05d'
OLD_SHAPE_RE = r'(?<![0-9])25[0-9]{2}:[^\s"]+'


def test_uid_detector_counterexamples(F):
    U = F['uid_index'](['2564:A1', '2565:B1', '2566:12345'])
    hits = lambda o: len(F['retained_uid_hits'](o, U))
    # real retained UIDs are found as whole strings, embedded tokens, object keys and at any depth
    assert hits('2566:12345') == 1 and hits({'a': [{'b': 'record 2566:12345, km 3'}]}) == 1 and hits({'2564:A1': 1}) == 1
    assert hits({'x': {'y': ['2565:B1']}, 'z': 'ids 2564:A1/2566:12345'}) == 3
    # legitimate public strings are tolerated: segment ids with 25xx route tokens (even equal to a BE year), ISO dates/times,
    # a longer code that only shares a UID prefix, and a UID-shaped string that is NOT a retained UID
    public = [REAL_SHAPE % ('2564', 0), REAL_SHAPE % ('2566', 1), REAL_SHAPE % ('2577', 2), '2021-03-10T18:00:00+07:00', '2024-06',
              '2566:123456', '2566:1234', '12566:12345', '2599:A1']
    assert all(re.search(OLD_SHAPE_RE, s) for s in public[:3])  # the old regex flagged these public ids
    assert hits(public) == 0
    with pytest.raises(F['CatalogError'], match='vacuous'):
        F['uid_index']([])
    with pytest.raises(F['CatalogError'], match='BE year'):
        F['uid_index'](['nocolon'])


def test_forbidden_keys_recursive_and_public_schema(F, tmp_path):
    W = build_world(tmp_path)
    X = pipeline(F, W)
    v = view_of(F, W, X)
    s = F['query_spatial_history'](v, {'segment_id': 'S1', 'target_date': '2022-12-31', 'unit': '6h', 'time_block': '00-06'})
    p = F['query_province_history'](v, {'province_key': BK, 'start_month': '2021-01', 'end_month': '2022-12'})
    assert not F['public_result_violations'](s, 'spatial') and not F['public_result_violations'](p, 'province')
    for key in ('event_uid', 'source_row', 'lat', 'lon', 'coordinates', 'narrative', 'acc_code', 'time_sec'):
        d = json.loads(json.dumps(s))
        d['categories']['weather']['top_values'].append({'value': 'v', 'records': 1, 'nested': [{key: 1}]})
        assert key in F['leaked_keys'](d)
        assert F['public_result_violations'](d, 'spatial')
        with pytest.raises(F['CatalogError'], match='public schema'):
            F['require_public_result'](d, 'spatial')
    for mutate in (lambda d: d.update(extra=1), lambda d: d.pop('history_cutoff_local'), lambda d: d['history_window'].update(rows=[]),
                   lambda d: d['counts_by_time_block'].pop('00-06'), lambda d: d.pop('n_same_time_block'),
                   lambda d: d['counts_by_month'].append({'year_month': '2021-01', 'records': 1, 'segment': 'S1'})):
        d = json.loads(json.dumps(s))
        mutate(d)
        assert F['public_result_violations'](d, 'spatial')
    d = json.loads(json.dumps(p))
    d['province']['lat'] = 13.7
    assert F['public_result_violations'](d, 'province')
    U = F['uid_index'](X['rec']['event_uid'])
    assert F['audit_public_result'](s, 'spatial', U) == {'schema_violations': 0, 'forbidden_keys': 0, 'retained_uid_hits': 0}


def test_controls_tolerate_real_segment_ids_and_fail_real_leaks(F, tmp_path):
    """Regression for run 020-002: real-format segment ids whose DOH route equals a BE year must pass; a REAL retained UID that reaches a
    public answer (here smuggled in as a category value) must be detected."""
    W = build_world(tmp_path)
    X = pipeline(F, W)
    ren = {'S1': REAL_SHAPE % ('2564', 0), 'S2': REAL_SHAPE % ('2565', 1), 'S3': REAL_SHAPE % ('2577', 2)}
    R = X['R'].assign(segment_id=X['R']['segment_id'].map(ren))
    v = F['build_catalog_view'](W['cfg'], X['P'].to_dict('records'), X['PM'], X['PC'], [ren[u] for u in X['uni']], R, 'test')
    ctrl = F['run_query_controls'](v, R, W['cfg'], X['rec']['event_uid'])
    assert ctrl['ok'].all(), ctrl[~ctrl['ok']].to_dict('records')
    tol = ctrl[ctrl['control'].str.startswith('detector tolerates')].iloc[0]
    assert tol['observed'] == '0' and '(3 carry a 25xx: route token)' in tol['control']
    U = F['uid_index'](X['rec']['event_uid'])
    R2 = R.copy()
    R2.loc[R2['segment_id'] == ren['S1'], 'accident_type'] = '2564:A3'  # a real retained UID leaking through a category value
    v2 = F['build_catalog_view'](W['cfg'], X['P'].to_dict('records'), X['PM'], X['PC'], [ren[u] for u in X['uni']], R2, 'leak')
    res = F['query_spatial_history'](v2, {'segment_id': ren['S1'], 'target_date': '2023-06-01', 'unit': 'daily'})
    assert F['audit_public_result'](res, 'spatial', U)['retained_uid_hits'] >= 1
    ctrl2 = F['run_query_controls'](v2, R2, W['cfg'], X['rec']['event_uid'])
    bad = ctrl2[~ctrl2['ok']]
    assert len(bad) and bad['control'].str.contains('no retained event UID').any()
    assert '2564:A3' not in ' '.join(ctrl2['observed']) + ' '.join(ctrl2['control'])  # evidence carries counts, never the UID


def test_province_query_retrospective_and_strict(F, tmp_path):
    W = build_world(tmp_path)
    X = pipeline(F, W)
    v = view_of(F, W, X)
    r = F['query_province_history'](v, {'province_key': BK, 'start_month': '2021-01', 'end_month': '2022-12', 'top_k': 1})
    assert r['total_records'] == 3 and r['as_of_cutoff'] is None and r['zero_months'] == 21
    at = r['categories']['accident_type']
    assert at['known_records'] + at['unknown_records'] == 3 and at['unknown_records'] == 1 and len(at['top_values']) == 1
    assert at['other_known_records'] == at['known_records'] - at['top_values'][0]['records']
    for bad in ({'province_key': BK, 'start_month': '2021-01', 'end_month': '2023-01'}, {'province_key': BK, 'start_month': '2021-01'},
                {'province_key': 1, 'start_month': '2021-01', 'end_month': '2021-02'}, {'province_key': BK, 'start_month': '2021-01', 'end_month': '2021-02', 'top_k': False}):
        with pytest.raises(F['CatalogQueryError']):
            F['query_province_history'](v, bad)


@pytest.mark.parametrize('req,code', [
    ({'segment_id': 'S9', 'target_date': '2024-01-01', 'unit': 'daily'}, 'unknown_segment'),
    ({'segment_id': 'S1', 'target_date': '2024-01-01', 'unit': 'daily', 'top_k': True}, 'invalid_type'),
    ({'segment_id': 'S1', 'target_date': '2024-01-01', 'unit': 'daily', 'extra': 1}, 'unknown_field'),
    ({'segment_id': 'S1', 'target_date': '2028-01-01', 'unit': 'daily'}, 'out_of_range'),
    ({'segment_id': 'S1', 'target_date': '2024-02-30', 'unit': 'daily'}, 'invalid_date'),
    ({'segment_id': 'S1', 'target_date': '2024-01-01', 'unit': 'weekly'}, 'invalid_unit'),
    ({'segment_id': 'S1', 'target_date': '2024-01-01', 'unit': '6h'}, 'missing_field'),
    ({'segment_id': 'S1', 'target_date': '2024-01-01', 'unit': 'daily', 'lookback_days': 5000}, 'out_of_range'),
    ({'segment_id': 'S1', 'target_date': '2024-01-01', 'unit': 'daily', 'lookback_days': float('nan')}, 'invalid_type'),
])
def test_strict_spatial_requests(F, tmp_path, req, code):
    W = build_world(tmp_path)
    v = view_of(F, W, pipeline(F, W))
    with pytest.raises(F['CatalogQueryError']) as e:
        F['query_spatial_history'](v, req)
    assert code in [x['code'] for x in e.value.errors]


def test_batch_and_json_limits(F, tmp_path):
    W = build_world(tmp_path)
    v = view_of(F, W, pipeline(F, W))
    good = {'segment_id': 'S1', 'target_date': '2024-01-01', 'unit': 'daily'}
    assert len(F['query_spatial_history_batch'](v, [good])['results']) == 1
    for reqs in ([dict(good, lookback_days=i + 1) for i in range(129)], [good, dict(good)], [], 'x'):
        with pytest.raises(F['CatalogQueryError']):
            F['query_spatial_history_batch'](v, reqs)
    for txt in ('{"a": NaN}', '{"a": 1, "a": 2}', '{"a": "' + 'x' * 70000 + '"}', b'\xff\xfe'):
        with pytest.raises(F['CatalogQueryError']):
            F['parse_request_json'](txt, 65536)


# ---------- negative fixtures: inputs / recovery ----------
def _expect(F, tmp_path, mutate, match):
    W = build_world(tmp_path, mutate)
    with pytest.raises(F['CatalogError'], match=match):
        pipeline(F, W)


def test_raw_tamper_rejected(F, tmp_path):
    W = build_world(tmp_path)
    p = W['backend'] / 'data/raw/accidents/accidents_2565_original.csv'
    p.write_bytes(p.read_bytes() + b'\n')
    with pytest.raises(F['CatalogError'], match='sha256'):
        pipeline(F, W)


def test_raw_manifest_year_and_rows_checked(F, tmp_path):
    _expect(F, tmp_path, lambda W: W.__setitem__('raw_manifest_hook', lambda raws: raws[1].update(ce_year=2023)), 'be_year/ce_year|ce_year')
    _expect(F, tmp_path / 'b', lambda W: W.__setitem__('raw_manifest_hook', lambda raws: raws[1].update(rows=3)), 'records != manifest rows')


@pytest.mark.parametrize('row,match', [('9', 'outside'), ('1', 'outside'), ('2.0', 'plain non-negative integer'), ('-2', 'plain non-negative integer')])
def test_row_bounds_and_fraction(F, tmp_path, row, match):
    def m(W):
        W['lineage'].loc[W['lineage']['event_uid'] == '2565:B2', 'source_row'] = row
    _expect(F, tmp_path, m, match)


def test_duplicate_coordinates_and_uid_sets(F, tmp_path):
    def dup(W):
        W['lineage'].loc[W['lineage']['event_uid'] == '2565:B2', 'source_row'] = '2'
    _expect(F, tmp_path, dup, 'duplicate retained source coordinates')

    def missing(W):
        W['events'] = W['events'][W['events']['event_uid'] != '2565:B2']
    _expect(F, tmp_path / 'b', missing, 'UID set')

    def dup_uid(W):
        W['lineage'] = pd.concat([W['lineage'], W['lineage'].iloc[[0]].assign(source_row='5')], ignore_index=True)
    _expect(F, tmp_path / 'c', dup_uid, 'not unique')


def test_row_uid_mismatch_and_source_year(F, tmp_path):
    def swap(W):
        W['lineage'].loc[W['lineage']['event_uid'] == '2565:B1', 'source_row'] = '3'
        W['lineage'].loc[W['lineage']['event_uid'] == '2565:B2', 'source_row'] = '2'
    _expect(F, tmp_path, swap, 'BE-year:ACC_CODE')

    def year(W):
        for k in ('events', 'lineage'):
            W[k].loc[W[k]['event_uid'] == '2565:B1', 'source_year_ce'] = '2021'
    _expect(F, tmp_path / 'b', year, 'ce_year')


def test_repaired_date_disagreement_and_ambiguous_headers(F, tmp_path):
    def date(W):
        W['lineage'].loc[W['lineage']['event_uid'] == '2564:A1', 'event_date_v2'] = '2021-10-03'
    _expect(F, tmp_path, date, 'disagree with their lineage')

    def amb(W):
        W['raw65'].insert(4, 'ลักษณะการเกิดเหตุ', 'x')
    _expect(F, tmp_path / 'b', amb, 'ambiguous headers')


def test_legacy_conflict_rejected(F, tmp_path):
    def m(W):
        W['legacy'].loc[W['legacy']['event_uid'] == '2564:A3', 'weather'] = 'ฝนตก'
    _expect(F, tmp_path, m, 'legacy descriptor conflicts')


def test_producer_membership_and_pins(F, tmp_path):
    _expect(F, tmp_path, lambda W: W.__setitem__('m10_hook', lambda m: m['inputs'][3].update(sha256='0' * 64)), 'notebook-10')
    _expect(F, tmp_path / 'b', lambda W: W.__setitem__('m10_hook', lambda m: m.update(status='failed')), 'accepted completed producer')
    W = build_world(tmp_path / 'c')
    p = W['repo'] / W['cfg']['pins']['path']
    pins = json.loads(p.read_text('utf-8'))
    pins['files'].pop('data/v2/events_v2.csv.gz')
    p.write_text(json.dumps(pins), 'utf-8')
    with pytest.raises(F['CatalogError'], match='pin file set'):
        pipeline(F, W)


def test_selected_inconsistent_with_accepted_events(F, tmp_path):
    def m(W):
        W['selected'].loc[W['selected']['event_uid'] == '2564:A3', 'time_block'] = '12-18'
    _expect(F, tmp_path, m, 'selected events disagree')

    def extra(W):
        W['selected'] = pd.concat([W['selected'], W['selected'].iloc[[0]].assign(event_uid='2564:ZZ')], ignore_index=True)
    _expect(F, tmp_path / 'b', extra, 'not accepted recovered events')


# ---------- runtime load / tamper ----------
def test_load_catalog_verifies_hashes_before_use(F, tmp_path):
    W = build_world(tmp_path)
    X = pipeline(F, W)
    rep, data, cfgp, msha, fsha = export(F, W, X, tmp_path)
    cat = F['load_catalog'](rep, data, cfgp, msha, fsha, None, NB)
    assert F['query_spatial_history'](cat, {'segment_id': 'S1', 'target_date': '2022-12-31', 'unit': 'daily'})['n_selected_records'] == 3
    assert F['catalog_summary'](cat)['research_status']['production_ready'] is False
    with pytest.raises(F['CatalogError']):
        F['load_catalog'](rep, data, cfgp, '0' * 64, fsha)
    with pytest.raises(F['CatalogError'], match='FUNCTIONS'):
        F['load_catalog'](rep, data, cfgp, msha, '0' * 64)
    nb2 = tmp_path / 'nb.ipynb'
    nb = json.loads(NB.read_text('utf-8'))
    nb['cells'][[i for i, c in enumerate(nb['cells']) if c['cell_type'] == 'code'][2]]['source'] = ['# FUNCTIONS (tampered)\n']
    nb2.write_text(json.dumps(nb), 'utf-8')
    with pytest.raises(F['CatalogError']):
        F['load_catalog'](rep, data, cfgp, msha, fsha, None, nb2)
    raw = (data / 'universe_segment_ids.csv').read_bytes()
    (data / 'universe_segment_ids.csv').write_bytes(raw + b'S4\n')
    with pytest.raises(F['CatalogError'], match='sha256'):
        F['load_catalog'](rep, data, cfgp, msha, fsha)
    (data / 'universe_segment_ids.csv').write_bytes(raw)
    cfgp.write_text(cfgp.read_text('utf-8') + ' ', 'utf-8')
    with pytest.raises(F['CatalogError'], match='config'):
        F['load_catalog'](rep, data, cfgp, msha, fsha)


# ---------- output guards ----------
def test_output_guards(F, tmp_path):
    W = build_world(tmp_path)
    b, repo, cfg = W['backend'], W['repo'], W['cfg']
    ok = F['output_paths'](b / 'rerun-historical-catalog-t1', cfg)
    assert F['check_outputs'](ok, b, repo, cfg)
    with pytest.raises(F['CatalogError'], match='overlaps guarded'):
        F['check_outputs'](F['output_paths'](b / 'data' / 'v2', cfg), b, repo, cfg)
    bad = dict(cfg, outputs=dict(cfg['outputs'], report_dir='reports/v3/spatial_preparation/x'))
    bad_paths = F['output_paths'](b, bad)
    assert not os.path.lexists(bad_paths['report_dir'])
    with pytest.raises(F['CatalogError'], match='protected snapshot overlaps runtime outputs'):
        F['check_outputs'](bad_paths, b, repo, bad)
    assert not os.path.lexists(bad_paths['report_dir']) and not os.path.lexists(bad_paths['data_dir'])
    (b / 'real').mkdir()
    os.symlink(b / 'real', b / 'rerun-historical-catalog-link')
    with pytest.raises(F['CatalogError'], match='symlink'):
        F['check_outputs'](F['output_paths'](b / 'rerun-historical-catalog-link', cfg), b, repo, cfg)
    (b / 'reports' / 'v3' / 'historical_catalog').mkdir(parents=True)
    with pytest.raises(F['CatalogError'], match='already exists'):
        F['check_outputs'](F['output_paths'](b, cfg), b, repo, cfg)
    with pytest.raises(F['CatalogError']):
        F['check_report_file']('rows.csv.gz', cfg)


@pytest.fixture(scope='module')
def RUN():
    spec = importlib.util.spec_from_file_location('run_historical_catalog', BACKEND / 'scripts' / 'run_historical_catalog.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_runner_refusals(RUN, tmp_path):
    b = tmp_path / 'backend'
    b.mkdir()
    cfg = fixture_cfg()
    assert RUN.refusal(b / 'rerun-historical-catalog-x', b, cfg) is None
    (b / 'config').mkdir()
    assert 'already exists' in RUN.refusal(b / 'config', b, cfg)
    assert 'must start with' in RUN.refusal(b / 'rerun-spatial-model-016-003', b, cfg)
    assert 'directly inside' in RUN.refusal(b / 'sub' / 'rerun-historical-catalog-x', b, cfg)
    (b / 'real').mkdir()
    os.symlink(b / 'real', b / 'rerun-historical-catalog-l')
    assert 'already exists' in RUN.refusal(b / 'rerun-historical-catalog-l', b, cfg)
    bad = dict(cfg, outputs=dict(cfg['outputs'], data_dir='../data/v2/x'))
    assert 'overlap' in RUN.refusal(b / 'rerun-historical-catalog-y', b, bad)
    env = RUN.build_env(b / 'rerun-historical-catalog-x', b, {'ROADAWARE_OTHER': '1', 'PATH': '/bin'})
    assert 'ROADAWARE_OTHER' not in env and env['MPLBACKEND'] == 'Agg'


def test_real_config_and_notebook_contract(F):
    F['validate_config'](CFG)
    assert CFG['production_ready'] is False and CFG['outputs']['report_dir'] == 'reports/v3/historical_catalog'
    assert 'config/catalog_v2.json' not in json.dumps(CFG['write_guard_paths']) and CFG['pins']['path'] == 'workflow/catalog/input-pins-v3.json'
    pins = json.loads((REPO / CFG['pins']['path']).read_text('utf-8'))
    assert set(pins['files']) == {v['path'] for v in CFG['inputs'].values()}
    for code in [''.join(c['source']) for c in json.loads(NB.read_text('utf-8'))['cells'] if c['cell_type'] == 'code']:
        assert '.ai-team' not in code and 'import tests' not in code


def _overlap(a, b):
    pa, pb = PurePosixPath(a).parts, PurePosixPath(b).parts
    return pa[:min(len(pa), len(pb))] == pb[:min(len(pa), len(pb))]


def test_real_snapshot_membership_and_runtime_output_exclusion(F):
    """The ACTUAL configured snapshot protects accepted inputs/outputs and notebook-20 SOURCE files (runner/tests/notebook/config) but never a
    runtime output (concurrent run roots, notebook-20 reports/data, this catalog's outputs, the executing notebook-14 source)."""
    snap, runtime = F['snapshot_rels'](CFG), F['runtime_output_rels'](CFG)
    assert F['snapshot_conflicts'](CFG) == []
    assert {'scripts/run_spatial_experiments.py', 'tests/test_spatial_experiments_notebook.py', 'notebooks/20_spatial_count_experiments.ipynb', 'config',
            'notebooks/19_spatial_count_preparation.ipynb', 'data/v3/spatial_preparation', 'reports/v3/spatial_preparation', 'data/raw',
            'data/v2/events_v2.csv.gz', 'data/v3/spatial_preparation/selected_events.csv.gz'} <= set(snap)
    assert {'rerun-spatial-model-016-001', 'rerun-spatial-model-016-002', 'reports/v3/spatial_experiments', 'data/v3/spatial_experiments',
            'reports/v3/historical_catalog', 'data/v3/historical_catalog', 'notebooks/14_backend_catalog.ipynb'} <= set(runtime)
    assert not [(s, r) for s in snap for r in runtime if _overlap(s, r)]
    assert not any(PurePosixPath(s).parts[0].startswith('rerun-') for s in snap)
    assert 'notebooks' not in snap and 'reports/v3' not in snap and 'data/v3' not in snap
    # fail closed when the config would snapshot a runtime output
    for key, bad in (('protected_paths', 'notebooks'), ('protected_paths', 'reports/v3'), ('readonly_hashed_paths', 'rerun-spatial-model-016-003/x'),
                     ('readonly_hashed_paths', 'data/v3/spatial_experiments/oof.csv.gz'), ('protected_paths', 'data/v3/historical_catalog')):
        c = copy.deepcopy(CFG)
        c[key] = c[key] + [bad]
        assert F['snapshot_conflicts'](c)
        with pytest.raises(F['CatalogError'], match='runtime outputs'):
            F['snapshot_rels'](c)
    c = copy.deepcopy(CFG)
    del c['runtime_output_paths']
    with pytest.raises(F['CatalogError'], match='runtime_output_paths'):
        F['validate_config'](c)


def test_snapshot_ignores_runtime_output_changes_but_catches_source_changes(F, tmp_path):
    b = tmp_path / 'backend'
    for rel in ('scripts/run_spatial_experiments.py', 'tests/test_spatial_experiments_notebook.py', 'notebooks/20_spatial_count_experiments.ipynb',
                'config/spatial_experiment_v3.json', 'reports/v3/spatial_experiments/metrics.csv', 'data/v3/spatial_experiments/oof.csv.gz',
                'rerun-spatial-model-016-002/reports/v3/log.json', 'notebooks/14_backend_catalog.ipynb', 'reports/v3/historical_catalog/x.csv'):
        (b / rel).parent.mkdir(parents=True, exist_ok=True)
        (b / rel).write_text('v1', 'utf-8')
    rels = F['snapshot_rels'](CFG)
    before = F['hash_paths'](b, rels)
    assert 'scripts/run_spatial_experiments.py' in before and 'config/spatial_experiment_v3.json' in before
    assert not any('spatial_experiments/' in k or k.startswith('rerun-') or 'historical_catalog' in k or k.startswith('notebooks/14') for k in before)
    for rel in ('reports/v3/spatial_experiments/metrics.csv', 'data/v3/spatial_experiments/oof.csv.gz', 'rerun-spatial-model-016-002/reports/v3/log.json',
                'notebooks/14_backend_catalog.ipynb', 'reports/v3/historical_catalog/x.csv'):
        (b / rel).write_text('v2 concurrent change', 'utf-8')
    assert F['snapshot_diff'](before, F['hash_paths'](b, rels)) == []
    (b / 'scripts/run_spatial_experiments.py').write_text('tampered', 'utf-8')
    (b / 'tests/test_spatial_experiments_notebook.py').unlink()
    assert F['snapshot_diff'](before, F['hash_paths'](b, rels)) == ['scripts/run_spatial_experiments.py', 'tests/test_spatial_experiments_notebook.py']
