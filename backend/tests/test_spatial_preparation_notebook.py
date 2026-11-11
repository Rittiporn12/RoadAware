"""Tests for V3 notebook 19 (spatial count preparation) and its runner. No network, no kernel.

The notebook's six '# FUNCTIONS' cells are executed (never SETUP/pipeline cells), and the accepted notebook-10 FUNCTIONS helpers are loaded
through the notebook's own hash-verified loader, so the logic under test is the logic the notebook runs. Geometry fixtures are drawn in
EPSG:32647 metres near (700000, 1600000) and converted with the notebook's own transformers. Run from the repository root:
    .venv/bin/python -m pytest backend/tests/test_spatial_preparation_notebook.py -q
"""
import copy
import gzip
import importlib.util
import json
import math
import os
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
NB19 = BACKEND / 'notebooks' / '19_spatial_count_preparation.ipynb'
RUNNER = BACKEND / 'scripts' / 'run_spatial_preparation.py'
CFG = json.loads((BACKEND / 'config' / 'spatial_preparation_v3.json').read_text('utf-8'))
PINS = REPO / 'workflow' / 'spatial' / 'preparation-input-pins-v3.json'
SRC_CFG = json.loads((BACKEND / 'config' / 'external_sources_v2.json').read_text('utf-8'))
FESTIVALS = SRC_CFG['calendar']['recurring_fixed_festivals']
X0, Y0 = 700000.0, 1600000.0


def code_cells(nb):
    d = json.loads(nb.read_text('utf-8'))
    return [''.join(c['source']) if isinstance(c['source'], list) else c['source'] for c in d['cells'] if c['cell_type'] == 'code']


@pytest.fixture(scope='module')
def f():
    ns = {}
    cells = [s for s in code_cells(NB19) if s.lstrip().startswith('# FUNCTIONS')]
    assert len(cells) == 6
    for i, s in enumerate(cells):
        exec(compile(s, f'{NB19.stem}:FUNCTIONS[{i}]', 'exec'), ns)
    return ns


@pytest.fixture(scope='module')
def h10(f):
    nb = CFG['inputs']['notebook10']
    ns, sha = f['load_nb10_helpers'](BACKEND / nb['path'], nb['functions_sha256'], nb['functions_cells'])
    assert sha == nb['functions_sha256']
    return ns


@pytest.fixture(scope='module')
def runner():
    spec = importlib.util.spec_from_file_location('run_spatial_preparation', RUNNER)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture(scope='module')
def tr(f):
    return f['make_transformers'](CFG)


# ---------------------------------------------------------------- pins, config, notebook structure
def test_config_pins_equal_manager_pins():
    pins = json.loads(PINS.read_text('utf-8'))
    I = CFG['inputs']
    for key in ('linkage_manifest', 'linkage_review', 'road_manifest', 'sources_manifest', 'preparation_v2_manifest', 'feature_config_v2',
                'sources_config_v2', 'adm1_metadata', 'adm1_geometry', 'province_mapping', 'traffic_stations', 'calendar_records', 'weather_daily', 'weather_6h'):
        assert I[key]['sha256'] == pins[key]['sha256'] and ('backend/' + I[key]['path']) == pins[key]['path'], key
    assert I['notebook10']['functions_sha256'] == pins['notebook10_functions_sha256']
    assert CFG['protocol']['sha256'] == pins['protocol_v3']['sha256']


def test_validate_config_rejects_protocol_drift(f):
    assert f['validate_config'](CFG)
    for path, val in ((('universe', 'min_length_m'), 400.0), (('labels', 'primary_status_column'), 'status_100m'), (('batch', 'max_rows'), 200000)):
        c = copy.deepcopy(CFG)
        c[path[0]][path[1]] = val
        with pytest.raises(f['PreparationError']):
            f['validate_config'](c)
    c = copy.deepcopy(CFG)
    c['inputs']['weather_daily']['sha256'] = None
    with pytest.raises(f['PreparationError']):
        f['validate_config'](c)


def test_nb10_loader_refuses_wrong_hash(f):
    nb = CFG['inputs']['notebook10']
    with pytest.raises(f['PreparationError']):
        f['load_nb10_helpers'](BACKEND / nb['path'], '0' * 64, nb['functions_cells'])


def test_integral_ids_and_numeric_codes(f):
    assert f['integral_ids'](['8', '8.0', 8.0], 'x').tolist() == [8, 8, 8]
    for bad in (['8.5'], ['nan'], [''], ['abc']):
        with pytest.raises(f['PreparationError']):
            f['integral_ids'](bad, 'x')
    n = lambda v: f['norm_numeric_code'](v, CFG['traffic']['route_regex'], CFG['traffic']['pad'])
    assert (n('1'), n('102'), n(' 36 '), n('0101')) == ('0001', '0102', '0036', '0101')
    assert n('1.0') is None and n('๑') is None and n('12345') is None and n('') is None and n(None) is None


def test_producer_hashes_finds_dict_and_list_records(f):
    m = {'a': {'x.csv': 'h1'}, 'resources': [{'path': 'derived/y.csv.gz', 'sha256': 'h2'}, {'path': None, 'preflight_path': '/abs/z.json', 'sha256': 'h3'}]}
    assert f['producer_hashes'](m, 'x.csv') == ['h1'] and f['producer_hashes'](m, 'y.csv.gz') == ['h2'] and f['producer_hashes'](m, 'z.json') == ['h3']
    assert f['producer_hashes'](m, 'missing.csv') == []


# ---------------------------------------------------------------- universe and static geometry
def ll_line(tr, xy):
    x, y = tr[1].transform(np.asarray(xy)[:, 0], np.asarray(xy)[:, 1])
    return np.column_stack([x, y])


def inv_row(sid, src='doh_highway', status='standard', L=2000.0, res=2000, oid=1, piece=0, idx=0, rk='0001'):
    return {'segment_id': sid, 'resolution_m': float(res), 'snapshot_tag': CFG['snapshot_tag'], 'source_id': src, 'oid': oid, 'part': 0, 'piece': piece,
            'seg_index': idx, 'length_m': L, 'length_geod_m': L, 'short_final': False, 'route_key': rk, 'route_status': status}


def test_universe_is_geometry_only_and_unsupported_explicit(f):
    inv = pd.DataFrame([inv_row('a'), inv_row('b', L=499.9, idx=1), inv_row('c', src='drr_rural', idx=2), inv_row('d', status='route_nonstandard', idx=3),
                        inv_row('e', res=500, idx=4), inv_row('f', L=500.0, idx=5)])
    uni, uns = f['classify_segments'](inv, CFG)
    assert uni['segment_id'].tolist() == ['a', 'f']  # 'a' and 'f' qualify with or without any record
    r = dict(zip(uns['segment_id'], uns['unsupported_reason']))
    assert r == {'b': 'short_lt_min_length', 'c': 'unsupported_source_drr_rural', 'd': 'route_route_nonstandard'}
    dup = pd.DataFrame([inv_row('a'), inv_row('z')])  # same OID/part/piece/index
    with pytest.raises(f['PreparationError']):
        f['classify_segments'](dup, CFG)


def static_for(f, tr, xy):
    ll = ll_line(tr, xy)
    from pyproj import Geod
    xx, yy = tr[0].transform(ll[:, 0], ll[:, 1])
    L = float(np.hypot(np.diff(xx), np.diff(yy)).sum())
    G = float(Geod(ellps='WGS84').line_length(ll[:, 0], ll[:, 1]))
    uni = pd.DataFrame([dict(inv_row('s1', L=L), length_geod_m=G)])
    return f['static_geometry'](uni, {'s1': (ll, {'segment_id': 's1'})}, CFG, tr), uni, ll


def test_static_features_straight_bent_and_zero_chord(f, tr):
    S, _, _ = static_for(f, tr, [[X0, Y0], [X0 + 2000, Y0]])
    r = S.iloc[0]
    assert abs(r['geom_bearing_sin'] - 1) < 1e-9 and abs(r['geom_bearing_cos']) < 1e-9 and abs(r['geom_straightness'] - 1) < 1e-9
    assert r['geom_turning_rad_per_km'] == 0 and abs(r['geom_mid_x_m'] - (X0 + 1000)) < 1e-6 and abs(r['geom_log_length_m'] - math.log(2000)) < 1e-6
    S, _, _ = static_for(f, tr, [[X0, Y0], [X0 + 1000, Y0], [X0 + 1000, Y0 + 1000]])
    r = S.iloc[0]
    assert abs(r['geom_straightness'] - math.sqrt(2) / 2) < 1e-9 and abs(r['geom_turning_rad_per_km'] - (math.pi / 2) / 2) < 1e-9
    S, _, _ = static_for(f, tr, [[X0, Y0], [X0 + 500, Y0], [X0 + 500, Y0 + 500], [X0, Y0 + 500], [X0, Y0]])
    r = S.iloc[0]
    assert bool(r['chord_zero_guard']) and r['geom_bearing_sin'] == 0 and r['geom_bearing_cos'] == 0 and r['geom_straightness'] == 0
    assert np.isfinite(S[[c for c in f['STATIC_FEATURES'] if c != 'route_code']].to_numpy(float)).all()


def test_static_geometry_rejects_tampered_length(f, tr):
    _, uni, ll = static_for(f, tr, [[X0, Y0], [X0 + 2000, Y0]])
    uni = uni.assign(length_m=uni['length_m'] + 0.5)
    with pytest.raises(f['PreparationError']):
        f['static_geometry'](uni, {'s1': (ll, {})}, CFG, tr)


def test_doh_identity_validates_oid_and_route(f, tmp_path):
    p = tmp_path / 'doh.geojson'
    feats = [{'type': 'Feature', 'id': 8.0, 'properties': {'objectid': 8, 'road_code': '0036', 'section_co': '0101'}, 'geometry': None},
             {'type': 'Feature', 'id': 9, 'properties': {'objectid': 9, 'road_code': '0036', 'section_co': 'x1'}, 'geometry': None}]
    p.write_text(json.dumps({'type': 'FeatureCollection', 'features': feats}))
    out = f['doh_identity'](p, [8, 9], ['0036', '0036'], CFG)
    assert out['aadt_section'].tolist()[0] == '0101' and out['aadt_identity_status'].tolist() == ['ok', 'section_code_nonstandard_or_missing']
    with pytest.raises(f['PreparationError']):
        f['doh_identity'](p, [8], ['0001'], CFG)  # route mismatch
    with pytest.raises(f['PreparationError']):
        f['doh_identity'](p, [7], ['0036'], CFG)  # unknown OID


# ---------------------------------------------------------------- ADM1 registry and midpoint join
def square(x0, y0, d=1.0):
    return [[[x0, y0], [x0 + d, y0], [x0 + d, y0 + d], [x0, y0 + d], [x0, y0]]]


def admin_files(tmp_path, polys, isos=('TH-10', 'TH-11')):
    from hashlib import sha256
    feats = [{'type': 'Feature', 'properties': {'shapeISO': iso, 'shapeID': 'ID' + iso, 'shapeName': iso}, 'geometry': {'type': 'Polygon', 'coordinates': p}}
             for iso, p in zip(isos, polys)]
    g = tmp_path / 'adm.geojson'
    g.write_text(json.dumps({'type': 'FeatureCollection', 'features': feats}))
    m = tmp_path / 'meta.json'
    m.write_text(json.dumps(CFG['admin']['expect_metadata']))
    h = sha256(g.read_bytes()).hexdigest()
    pts = pd.DataFrame({'province_code': ['10', '11'], 'shape_iso': ['TH-10', 'TH-11'], 'shape_id': ['IDTH-10', 'IDTH-11'], 'province_key': ['ก', 'ข'],
                        'geometry_sha256': [h, h]})
    pp = tmp_path / 'pts.csv'
    pts.to_csv(pp, index=False)
    c = copy.deepcopy(CFG)
    c['admin']['expected_polygons'] = 2
    return g, m, pp, c, h


def test_admin_registry_join_border_unmapped(f, tmp_path):
    g, m, pp, c, h = admin_files(tmp_path, [square(100.0, 14.0), square(101.0, 14.0)])
    A = f['load_admin'](g, m, pp, c, h)
    J = f['join_points_to_admin']([100.5, 101.0, 105.0, 101.0], [14.5, 14.5, 14.5, 15.0], A)
    assert J['province_join_status'].tolist() == ['mapped', 'ambiguous_border', 'unmapped', 'ambiguous_border']
    assert J['province_code'].iloc[0] == 10.0 and J['province_code'].iloc[1:].isna().all()  # no nearest-centroid fallback


def test_admin_registry_rejects_invalid_and_mismatched(f, tmp_path):
    bow = [[[100.0, 14.0], [101.0, 15.0], [101.0, 14.0], [100.0, 15.0], [100.0, 14.0]]]
    g, m, pp, c, h = admin_files(tmp_path, [bow, square(101.0, 14.0)])
    with pytest.raises(f['PreparationError']):
        f['load_admin'](g, m, pp, c, h)  # never silently repaired
    g, m, pp, c, h = admin_files(tmp_path, [square(100.0, 14.0), square(101.0, 14.0)], isos=('TH-10', 'TH-12'))
    with pytest.raises(f['PreparationError']):
        f['load_admin'](g, m, pp, c, h)
    g, m, pp, c, h = admin_files(tmp_path, [square(100.0, 14.0), square(101.0, 14.0)])
    with pytest.raises(f['PreparationError']):
        f['load_admin'](g, m, pp, c, 'f' * 64)  # points not derived from the pinned polygons


# ---------------------------------------------------------------- events, labels, sparse counts, population
def event(uid, s50='matched', s100='matched', seg_status='assigned', seg='a', date='2022-03-01', block='06-12', scope='pilot', src='doh_highway', oid='1.0'):
    return {'event_uid': uid, 'ce_year': date[:4], 'event_date': date, 'time_block': block, 'province_key': 'ก', 'split': 'train', 'scope': scope,
            'source_id': src, 'status_25m': s50, 'status_50m': s50, 'status_100m': s100, 'segment_status': seg_status,
            'segment_id_2000m': seg if seg_status == 'assigned' else '', 'chosen_source_oid': oid, 'chosen_part': '0', 'chosen_piece': '0'}


def label_fixture(f):
    inv = pd.DataFrame([inv_row('a'), inv_row('z', idx=1), dict(inv_row('c', src='drr_rural', idx=2), oid=1)])
    uni, uns = f['classify_segments'](inv, CFG)
    E = pd.DataFrame([event('e1'), event('e2', block='18-24'), event('e3', date='2022-03-02', block='00-06'),
                      event('e4', s50='too_far', seg_status='not_matched'), event('e5', seg_status='not_matched'),
                      event('e6', seg='c', src='drr_rural'), event('e7', scope='outside_envelope', s50='outside_pilot_envelope', s100='outside_pilot_envelope', seg_status='not_matched'),
                      event('e8', date='2026-01-02')])
    return inv, uni, uns, E


def test_selection_primary_50m_and_assigned_only(f):
    inv, uni, uns, E = label_fixture(f)
    ES = f['select_events'](E, inv, uni['segment_id'], uns, CFG)
    cat = dict(zip(ES['event_uid'], ES['selection']))
    assert [k for k, v in cat.items() if v == 'selected'] == ['e1', 'e2', 'e3']
    assert cat['e4'] == 'unknown_status_50m_too_far'  # 100 m-only match is never selected
    assert cat['e5'] == 'matched_50m_no_segment_assignment' and cat['e6'] == 'unsupported_segment_unsupported_source_drr_rural'
    assert cat['e7'] == 'outside_pilot_envelope' and cat['e8'] == 'date_outside_population_axis' and len(ES) == len(E)
    bad = E.copy()
    bad.loc[0, 'chosen_source_oid'] = '2'
    with pytest.raises(f['PreparationError']):
        f['select_events'](bad, inv, uni['segment_id'], uns, CFG)
    bad = E.copy()
    bad.loc[0, 'time_block'] = ''
    with pytest.raises(f['PreparationError']):
        f['select_events'](bad, inv, uni['segment_id'], uns, CFG)


def test_load_events_fails_closed(f, tmp_path):
    _, _, _, E = label_fixture(f)
    E = pd.concat([E] + [pd.DataFrame([event('y' + str(y), date=str(y) + '-02-01')]) for y in CFG['labels']['years']], ignore_index=True)
    man = {'reconciliation': {'retained': len(E), 'status_by_tolerance': {'50m': {'matched': int((E['status_50m'] == 'matched').sum())}},
                              'matched_with_segment_50m': int(((E['status_50m'] == 'matched') & (E['segment_status'] == 'assigned')).sum())}}
    p = tmp_path / 'e.csv.gz'
    p.write_bytes(gzip.compress(E.to_csv(index=False).encode()))
    assert len(f['load_events'](p, CFG, man)) == len(E)
    p.write_bytes(gzip.compress(pd.concat([E, E.iloc[[0]]]).to_csv(index=False).encode()))
    with pytest.raises(f['PreparationError']):
        f['load_events'](p, CFG, dict(man, reconciliation=dict(man['reconciliation'], retained=len(E) + 1)))  # duplicate UID
    E2 = E[~E['ce_year'].eq('2024')]
    p.write_bytes(gzip.compress(E2.to_csv(index=False).encode()))
    man2 = {'reconciliation': {'retained': len(E2), 'status_by_tolerance': {'50m': {'matched': int((E2['status_50m'] == 'matched').sum())}},
                               'matched_with_segment_50m': int(((E2['status_50m'] == 'matched') & (E2['segment_status'] == 'assigned')).sum())}}
    with pytest.raises(f['PreparationError']):
        f['load_events'](p, CFG, man2)  # a missing year is never zero-filled


def test_sparse_counts_and_virtual_population(f):
    inv, uni, uns, E = label_fixture(f)
    ES = f['select_events'](E, inv, uni['segment_id'], uns, CFG)
    sel = ES[ES['selection'] == 'selected']
    D, B, checks = f['sparse_counts'](sel, CFG)
    assert all(checks.values()) and D['y_count'].tolist() == [2, 1] and B['y_count'].tolist() == [1, 1, 1]
    ax = f['population_axes'](uni['segment_id'], '2022-03-01', '2022-03-03', CFG['time']['time_blocks'])
    assert f['population_size'](ax, 'daily') == 6 and f['population_size'](ax, '6h') == 24
    for unit, C in (('daily', D), ('6h', B)):
        sp = f['sparse_index'](ax, unit, C)
        batches = list(f['iter_population_batches'](ax, unit, 5))
        assert sum(len(k) for _, k in batches) == f['population_size'](ax, unit) and max(len(k) for _, k in batches) <= 5
        allk = pd.concat([k for _, k in batches], ignore_index=True)
        assert not allk.duplicated().any() and set(allk['segment_id']) == set(uni['segment_id'])
        y = f['lookup_counts'](sp, np.arange(f['population_size'](ax, unit)))
        assert y.sum() == len(sel) and (y >= 0).all()
        zseg = allk['segment_id'] == 'z'  # zero-record segment kept with conditional zeros
        assert zseg.any() and y[zseg.to_numpy()].sum() == 0
        audit = f['population_audit'](ax, unit, sp, 5, len(sel), CFG['time']['splits'])
        assert audit['first_key']['target_date'] == '2022-03-01' and audit['last_key']['target_date'] == '2022-03-03'
    with pytest.raises(f['PreparationError']):
        next(f['iter_population_batches'](ax, 'daily', 100001))


BLOCKS = CFG['time']['time_blocks']


def counts_frame(y, seg=('seg-a',), d=('2021-01-01',)):
    return pd.DataFrame({'segment_id': list(seg), 'target_date': list(d), 'y_count': y})


@pytest.fixture
def ax2(f):
    return f['population_axes'](['seg-a'], '2021-01-01', '2021-01-02', BLOCKS)  # 2 daily cells, 8 6-hour cells


def test_population_counterexamples_rejected(f, ax2):
    E = f['PreparationError']
    sp = f['sparse_index'](ax2, 'daily', counts_frame([1]))
    with pytest.raises(E):
        f['keys_from_positions'](ax2, 'daily', [-1])  # was a silent negative-index wrap to 2021-01-02
    for bad in ([-1, 2, 999], [-1], [2], [999]):
        with pytest.raises(E):
            f['lookup_counts'](sp, bad)  # outside the 2-cell population: unknown, never a conditional zero
    with pytest.raises(E):
        f['population_size'](ax2, 'unsupported-unit')  # was 2 (unknown unit treated as daily)


@pytest.mark.parametrize('unit', ['unsupported-unit', 'hourly', 'DAILY', '', None])
def test_population_helpers_reject_unknown_unit(f, ax2, unit):
    E = f['PreparationError']
    keys = pd.DataFrame({'segment_id': ['seg-a'], 'target_date': ['2021-01-01'], 'time_block': [BLOCKS[0]], 'y_count': [1]})
    sp = f['sparse_index'](ax2, 'daily', counts_frame([1]))
    for call in (lambda: f['population_size'](ax2, unit), lambda: f['keys_from_positions'](ax2, unit, [0]),
                 lambda: f['positions_from_keys'](ax2, unit, keys), lambda: f['sparse_index'](ax2, unit, keys),
                 lambda: f['iter_population_batches'](ax2, unit, 10), lambda: f['population_audit'](ax2, unit, sp, 10, 1, CFG['time']['splits'])):
        with pytest.raises(E):
            call()


@pytest.mark.parametrize('bad', [[0.5], [np.nan], [np.inf], [-np.inf], [True], [True, 1], np.array([False]), [2 ** 70],
                                 np.array([2 ** 63], dtype=np.uint64), [1e300], [[0]], ['0'], [None], [-0.5], [2.0]])
def test_position_vectors_validated_before_cast(f, ax2, bad):
    sp = f['sparse_index'](ax2, 'daily', counts_frame([1]))
    with pytest.raises(f['PreparationError']):
        f['keys_from_positions'](ax2, 'daily', bad)
    with pytest.raises(f['PreparationError']):
        f['lookup_counts'](sp, bad)


def test_position_bounds_first_last_zero_and_empty(f, ax2):
    sp = f['sparse_index'](ax2, 'daily', counts_frame([3]))
    assert sp['unit'] == 'daily' and sp['size'] == 2 and sp['axis']['first_date'] == '2021-01-01' and sp['axis']['last_date'] == '2021-01-02'
    assert f['lookup_counts'](sp, [0, 1]).tolist() == [3, 0]  # known no-record cell inside the population == 0
    assert f['lookup_counts'](sp, np.array([1.0, 0.0])).tolist() == [0, 3]  # whole-number floats are exact positions
    K = f['keys_from_positions'](ax2, 'daily', [0, 1])
    assert K['target_date'].tolist() == ['2021-01-01', '2021-01-02'] and K['segment_id'].tolist() == ['seg-a', 'seg-a']
    assert len(f['keys_from_positions'](ax2, 'daily', [])) == 0 and f['lookup_counts'](sp, []).tolist() == []
    with pytest.raises(f['PreparationError']):
        f['lookup_counts']({'pos': sp['pos'], 'y': sp['y']}, [0])  # no bound evidence: refuse rather than default to 0
    with pytest.raises(f['PreparationError']):
        f['keys_from_positions'](ax2, '6h', [8])  # first index past the last 6 h cell
    assert f['keys_from_positions'](ax2, '6h', [7]).iloc[0].to_dict() == {'segment_id': 'seg-a', 'target_date': '2021-01-02', 'time_block': BLOCKS[-1]}


def test_six_hour_roundtrip_order_and_year_boundary(f):
    ax = f['population_axes'](['s-b', 's-a', 's-c'], '2021-12-31', '2022-01-01', BLOCKS)
    for unit, n in (('daily', 6), ('6h', 24)):
        assert f['population_size'](ax, unit) == n
        pos = np.arange(n)
        K = f['keys_from_positions'](ax, unit, pos)
        assert f['positions_from_keys'](ax, unit, K).tolist() == pos.tolist() and not K.duplicated().any()
        with pytest.raises(f['PreparationError']):
            f['keys_from_positions'](ax, unit, [n])
    K = f['keys_from_positions'](ax, '6h', [0, 3, 4, 11, 12, 23])
    assert list(K.itertuples(index=False, name=None)) == [('s-a', '2021-12-31', '00-06'), ('s-a', '2021-12-31', '18-24'), ('s-b', '2021-12-31', '00-06'),
                                                          ('s-c', '2021-12-31', '18-24'), ('s-a', '2022-01-01', '00-06'), ('s-c', '2022-01-01', '18-24')]
    sp = f['sparse_index'](ax, '6h', pd.DataFrame({'segment_id': ['s-b'], 'target_date': ['2022-01-01'], 'time_block': ['12-18'], 'y_count': [3]}))
    y = f['lookup_counts'](sp, np.arange(24))
    assert sp['pos'].tolist() == [18] and y[18] == 3 and y.sum() == 3 and (np.delete(y, 18) == 0).all()
    audit = f['population_audit'](ax, '6h', sp, 5, 3, CFG['time']['splits'])
    assert audit['rows'] == 24 and audit['batches'] == 5 and audit['count_sum'] == 3
    assert audit['first_key'] == {'segment_id': 's-a', 'target_date': '2021-12-31', 'time_block': '00-06'}
    assert audit['last_key'] == {'segment_id': 's-c', 'target_date': '2022-01-01', 'time_block': '18-24'}


@pytest.mark.parametrize('y', [[0], [-1], [1.5], [np.nan], [np.inf], [True], ['1'], [None], [2 ** 70], np.array([2 ** 63], dtype=np.uint64)])
def test_sparse_index_rejects_invalid_counts(f, ax2, y):
    with pytest.raises(f['PreparationError']):
        f['sparse_index'](ax2, 'daily', counts_frame(y))


def test_sparse_index_keys_unique_inside_and_empty_population(f, ax2):
    E = f['PreparationError']
    assert f['sparse_index'](ax2, 'daily', counts_frame([2.0]))['y'].tolist() == [2]
    for C in (counts_frame([1, 1], seg=('seg-a', 'seg-a'), d=('2021-01-01', '2021-01-01')), counts_frame([1], d=('2021-01-03',)),
              counts_frame([1], seg=('seg-b',))):
        with pytest.raises(E):
            f['sparse_index'](ax2, 'daily', C)
    empty = f['sparse_index'](ax2, 'daily', pd.DataFrame({'segment_id': pd.Series([], dtype=object), 'target_date': pd.Series([], dtype=object),
                                                          'y_count': pd.Series([], dtype='int64')}))
    assert len(empty['pos']) == 0 and empty['size'] == 2 and f['lookup_counts'](empty, [0, 1]).tolist() == [0, 0]
    for bad in ([2], [-1]):
        with pytest.raises(E):
            f['lookup_counts'](empty, bad)  # an empty index still has a bound
    a0 = f['population_audit'](ax2, 'daily', empty, 1, 0, CFG['time']['splits'])
    assert a0['rows'] == 2 and a0['batches'] == 2 and a0['count_sum'] == 0 and a0['positive_cells'] == 0
    other = f['population_axes'](['seg-a', 'seg-b'], '2021-01-01', '2021-01-02', BLOCKS)
    with pytest.raises(E):
        f['population_audit'](other, 'daily', empty, 1, 0, CFG['time']['splits'])  # index built for a different population
    with pytest.raises(E):
        f['population_audit'](ax2, '6h', empty, 1, 0, CFG['time']['splits'])


@pytest.mark.parametrize('seg,start,end,blocks', [
    (['seg-a'], '2021-01-02', '2021-01-01', BLOCKS), (['seg-a'], '2021-02-30', '2021-03-01', BLOCKS), (['seg-a'], '2021-1-1', '2021-01-02', BLOCKS),
    (['seg-a'], '', '2021-01-02', BLOCKS), (['seg-a'], None, '2021-01-02', BLOCKS), (['seg-a'], '2021-01-01', 'x', BLOCKS),
    ([], '2021-01-01', '2021-01-02', BLOCKS), (['seg-a', 'seg-a'], '2021-01-01', '2021-01-02', BLOCKS), (['seg-a', ''], '2021-01-01', '2021-01-02', BLOCKS),
    (['seg-a', ' '], '2021-01-01', '2021-01-02', BLOCKS), (['seg-a', None], '2021-01-01', '2021-01-02', BLOCKS),
    (['seg-a'], '2021-01-01', '2021-01-02', []), (['seg-a'], '2021-01-01', '2021-01-02', ['00-06', '00-06']), (['seg-a'], '2021-01-01', '2021-01-02', ['00-06', ''])])
def test_population_axes_reject_invalid(f, seg, start, end, blocks):
    with pytest.raises(f['PreparationError']):
        f['population_axes'](seg, start, end, blocks)


def test_population_axes_single_day_and_batch_subranges(f, ax2):
    one = f['population_axes'](['seg-a'], '2021-01-01', '2021-01-01', BLOCKS)
    assert f['population_size'](one, 'daily') == 1 and one['dates'] == ['2021-01-01']
    sub = list(f['iter_population_batches'](ax2, '6h', 3, '2021-01-02', '2021-01-02'))
    assert [a for a, _ in sub] == [4, 7] and pd.concat([k for _, k in sub])['target_date'].eq('2021-01-02').all()
    assert sum(len(k) for _, k in sub) == 4
    for s0, s1 in (('2020-12-31', None), (None, '2021-01-03'), ('2021-01-02', '2021-01-01'), ('', None), ('2021-1-1', None)):
        with pytest.raises(f['PreparationError']):
            f['iter_population_batches'](ax2, 'daily', 10, s0, s1)  # never an empty success
    for b in (0, 100001, 2.5, True, '10'):
        with pytest.raises(f['PreparationError']):
            f['iter_population_batches'](ax2, 'daily', b)
    assert [a for a, _ in f['iter_population_batches'](ax2, 'daily', 100000)] == [0]


# ---------------------------------------------------------------- calendar, weather, AADT
def test_calendar_new_year_cross_year_and_bank_asof(f, h10):
    dates = ['2021-12-30', '2022-01-02', '2022-04-13']
    fe = h10['festival_features'](dates, FESTIVALS, 14, {k: tuple(v) for k, v in CFG['features']['festival_windows'].items()})
    assert fe['fest_new_year_dist'].tolist()[:2] == [-1, 1] and fe['fest_songkran_in'].tolist()[2] == 1
    rec = pd.DataFrame({'date': ['2024-05-10', '2024-05-01', '2024-05-01'], 'action': ['add', 'add', 'remove'],
                        'known_from': ['2024-05-10', '2023-07-26', '2024-05-02'], 'applied': [True, True, True], 'source_id': ['late', 'base', 'removal']})
    src = [{'id': 'base', 'role': 'annual_base', 'years': [2024]}]
    D = f['date_table'](h10, CFG, FESTIVALS, rec, src).set_index('target_date')
    assert D.loc['2024-05-10', 'bank_holiday_asof'] == 0.0  # announced on the target day: not known at issue
    assert D.loc['2024-05-01', 'bank_holiday_asof'] == 1.0  # removal published after issue is not applied early
    assert np.isnan(D.loc['2025-02-01', 'bank_holiday_asof']) and D.loc['2025-02-01', 'bank_calendar_known_asof'] == 0.0
    assert D.loc['2024-01-01', 'issue_time_local'] == '2023-12-31T18:00:00+07:00' and D.loc['2024-01-01', 'issue_time_utc'] == '2023-12-31T11:00:00+00:00'
    assert bool(D.loc['2026-01-01', 'beyond_evaluated_period']) and not bool(D.loc['2025-12-31', 'beyond_evaluated_period'])
    assert len(D) == (pd.Timestamp('2027-12-31') - pd.Timestamp('2021-01-01')).days + 1


def wx_rows(**over):
    base = {'province_code': '10', 'date': '2024-05-10', 'time_block': 'day', 'rain_sum': '5.0', 'temp_mean': '30.0', 'rain_missing': 'False',
            'temp_missing': 'False', 'n_valid_rain': '24', 'n_valid_temp': '24', 'n_expected': '24', 'n_hours': '24',
            'latest_issue_bound_utc': '2024-05-09T05:00:00+00:00', 'issue_bound_ok': 'True'}
    base.update(over)
    return base


def test_weather_policy_late_partial_invalid(f, h10):
    w = pd.DataFrame([wx_rows(), wx_rows(date='2024-05-11', latest_issue_bound_utc='2024-05-10T05:00:01+00:00', issue_bound_ok='False'),
                      wx_rows(date='2024-05-12', latest_issue_bound_utc='2024-05-11T05:00:00+00:00', rain_missing='True', n_valid_rain='23', rain_sum=''),
                      wx_rows(date='2024-05-13', latest_issue_bound_utc='2024-05-12T05:00:00+00:00', temp_mean='80.0')])
    out, _ = f['weather_table'](w, h10, CFG, [10, 11], 'daily')
    assert out['wx_rain_sum_mm_d2'].iloc[0] == 5.0 and out['wx_rain_reason'].tolist() == ['ok', 'issue_bound_after_issue_time', 'rain_incomplete_hours', 'ok']
    assert np.isnan(out['wx_rain_sum_mm_d2'].iloc[1]) and np.isnan(out['wx_rain_sum_mm_d2'].iloc[2])  # NaN, never 0 or a partial sum
    assert out['wx_temp_reason'].iloc[3] == 'temp_out_of_plausible_range' and np.isnan(out['wx_temp_mean_c_d2'].iloc[3])
    with pytest.raises(f['PreparationError']):
        f['weather_table'](pd.DataFrame([wx_rows(n_valid_rain='20')]), h10, CFG, [10], 'daily')  # cached flag inconsistent
    with pytest.raises(h10['DependencyError']):
        f['weather_table'](pd.DataFrame([wx_rows(latest_issue_bound_utc='2024-05-09T06:00:00+00:00')]), h10, CFG, [10], 'daily')  # tampered 09 guard
    with pytest.raises(f['PreparationError']):
        f['weather_table'](pd.DataFrame([wx_rows(province_code='99')]), h10, CFG, [10], 'daily')


def station(year, route='1', cs='102', sp='25+556', tot='1000.0', tv='True', hv='10.0', hvv='True', avail='2022-03-25T06:10:50+00:00', rc='station'):
    return {'survey_year_ce': str(year), 'route': route, 'control_section': cs, 'survey_point': sp, 'province_text': 'ก', 'row_class': rc, 'total_aadt': tot,
            'total_valid': tv, 'heavy_share_pct': hv, 'heavy_share_valid': hvv, 'available_from_proxy_utc': avail}


def test_aadt_groups_vintages_and_rejections(f, h10):
    st = pd.DataFrame([station(2020, avail='2024-06-01T07:41:10+00:00'), station(2021), station(2021, sp='30+000', tot='3000.0', hv='', hvv='False'),
                       station(2022, avail='2024-06-01T07:48:05+00:00'), station(2021, route='0001', cs='0102', sp='x', rc='duplicate_key'),
                       station(2021, route='1A', sp='y')])
    G, A, audit = f['aadt_tables'](st, CFG, h10)
    g = G.set_index(['aadt_route', 'aadt_section', 'survey_year_ce']).loc[('0001', '0102', 2021)]
    assert g['aadt_mean_total'] == 2000.0 and g['aadt_median_total'] == 2000.0 and g['aadt_mean_heavy_share_pct'] == 10.0 and g['aadt_n_station_rows'] == 2
    assert audit['station_rows_identity_nonstandard'] == 1
    V = f['aadt_vintage_by_date'](A, ['2021-06-01', '2022-03-25', '2022-03-26', '2023-06-01', '2024-06-03'], CFG, h10)['aadt_vintage_survey_year_ce'].tolist()
    assert np.isnan(V[0]) and np.isnan(V[1]) and V[2:] == [2021.0, 2021.0, 2022.0]  # no 2020/2022 backfill before publication
    with pytest.raises(f['PreparationError']):
        f['aadt_tables'](pd.DataFrame([station(2021), station(2021)]), CFG, h10)  # duplicate station rows
    with pytest.raises(f['PreparationError']):
        f['aadt_tables'](pd.DataFrame([station(2021, tot='-5')]), CFG, h10)  # flagged valid but negative


# ---------------------------------------------------------------- builder, context reload, negative controls
@pytest.fixture(scope='module')
def ctx_tables(f, h10):
    settings = f['context_settings'](CFG, FESTIVALS)
    rec = pd.DataFrame({'date': ['2023-01-02'], 'action': ['add'], 'known_from': ['2022-11-01'], 'applied': [True], 'source_id': ['base']})
    src = [{'id': 'base', 'role': 'annual_base', 'years': [2023]}]
    D = f['date_table'](h10, CFG, FESTIVALS, rec, src)
    av = pd.DataFrame({'survey_year_ce': [2021], 'available_from_proxy_utc': ['2022-03-25T06:10:50+00:00']})
    D = D.merge(f['aadt_vintage_by_date'](av, D['target_date'], CFG, h10), on='target_date')
    seg = pd.DataFrame({'segment_id': ['s1', 's2', 's3'], 'route_code': ['0001', '0001', '0036'], 'geom_mid_x_m': [1.0, 2.0, 3.0], 'geom_mid_y_m': [1.0, 2.0, 3.0],
                        'geom_mid_lon': [100.1, 100.2, 100.3], 'geom_mid_lat': [14.1, 14.2, 14.3], 'geom_length_m': [2000.0, 1500.0, 600.0],
                        'geom_log_length_m': np.log([2000.0, 1500.0, 600.0]), 'geom_bearing_sin': [0.0, 1.0, 0.5], 'geom_bearing_cos': [1.0, 0.0, 0.1],
                        'geom_straightness': [1.0, 0.9, 0.3], 'geom_turning_rad_per_km': [0.0, 0.1, 1.0 / 3.0], 'province_code': [10.0, np.nan, 10.0],
                        'province_join_status': ['mapped', 'ambiguous_border', 'mapped'], 'aadt_route': ['0001', '0001', '0036'],
                        'aadt_section': ['0102', '0102', np.nan], 'aadt_identity_status': ['ok', 'ok', 'section_code_nonstandard_or_missing']})
    uns = pd.DataFrame({'segment_id': ['drr1'], 'source_id': ['drr_rural'], 'route_key': ['x'], 'route_status': ['standard'], 'length_m': [2000.0],
                        'unsupported_reason': ['unsupported_source_drr_rural']})
    wd = pd.DataFrame({'province_code': [10, 10], 'target_date': ['2023-01-02', '2023-01-03'], 'wx_rain_sum_mm_d2': [1.0 / 3.0, np.nan],
                       'wx_temp_mean_c_d2': [27.1, np.nan], 'wx_rain_reason': ['ok', 'issue_bound_after_issue_time'], 'wx_temp_reason': ['ok', 'issue_bound_after_issue_time']})
    wb = pd.DataFrame({'province_code': [10], 'target_date': ['2023-01-02'], 'time_block': ['06-12'], 'wx_block_rain_sum_mm_d2': [0.1],
                       'wx_block_temp_mean_c_d2': [25.0], 'wx_block_rain_reason': ['ok'], 'wx_block_temp_reason': ['ok']})
    ag = pd.DataFrame({'aadt_route': ['0001'], 'aadt_section': ['0102'], 'survey_year_ce': [2021], 'aadt_mean_total': [1234.5], 'aadt_median_total': [1200.0],
                       'aadt_mean_heavy_share_pct': [11.1], 'aadt_n_station_rows': [3], 'aadt_n_valid_total': [3]})
    return settings, seg, uns, D, wd, wb, ag


@pytest.fixture(scope='module')
def ctx(f, ctx_tables):
    return f['context_from_tables'](*ctx_tables)


def test_builder_order_columns_and_nan_reasons(f, ctx):
    req = pd.DataFrame({'segment_id': ['s3', 's1', 's2', 's1'], 'target_date': ['2023-01-02', '2023-01-02', '2023-01-02', '2027-06-01']})
    X, M = f['build_feature_rows'](ctx, req, 'daily')
    assert len(X) == 4 and M['segment_id'].tolist() == ['s3', 's1', 's2', 's1']
    assert list(X.columns) == f['feature_columns'](ctx['settings'], 'daily', 'calendar_geometry_context')
    f['validate_columns'](list(X.columns), ctx['settings'])
    assert not set(X.columns) & {'segment_id', 'target_date', 'province_code', 'aadt_n_station_rows', 'y_count'}
    assert X['wx_rain_sum_mm_d2'].iloc[1] == 1.0 / 3.0 and X['aadt_mean_total'].iloc[1] == 1234.5 and M['aadt_n_station_rows'].iloc[1] == 3
    assert np.isnan(X['wx_rain_sum_mm_d2'].iloc[2]) and M['wx_rain_reason'].iloc[2] == 'segment_province_ambiguous_border'
    assert np.isnan(X['aadt_mean_total'].iloc[0]) and M['aadt_reason'].iloc[0].startswith('segment_identity_')
    assert np.isnan(X['wx_rain_sum_mm_d2'].iloc[3]) and M['wx_rain_reason'].iloc[3] == 'not_in_weather_archive' and bool(M['beyond_evaluated_period'].iloc[3])
    assert M['issue_time_local'].iloc[1] == '2023-01-01T18:00:00+07:00' and X['bank_holiday_asof'].iloc[1] == 1.0
    X6, M6 = f['build_feature_rows'](ctx, [{'segment_id': 's1', 'target_date': '2023-01-02', 'time_block': '06-12'},
                                           {'segment_id': 's1', 'target_date': '2023-01-02', 'time_block': '12-18'}], '6h')
    assert X6['time_block'].tolist() == ['06-12', '12-18'] and X6['wx_block_rain_sum_mm_d2'].iloc[0] == 0.1 and np.isnan(X6['wx_block_rain_sum_mm_d2'].iloc[1])
    assert X6['wx_rain_sum_mm_d2'].tolist() == [1.0 / 3.0, 1.0 / 3.0]
    Xb, _ = f['build_feature_rows'](ctx, req, 'daily', 'calendar_geometry')
    assert not any(c.startswith(('wx_', 'aadt_')) for c in Xb.columns)


@pytest.mark.parametrize('req,unit,code', [
    ([{'segment_id': 'nope', 'target_date': '2023-01-02'}], 'daily', 'unknown_segment'),
    ([{'segment_id': 'drr1', 'target_date': '2023-01-02'}], 'daily', 'unsupported_segment'),
    ([{'segment_id': 's1', 'target_date': '2028-01-01'}], 'daily', 'date_out_of_range'),
    ([{'segment_id': 's1', 'target_date': '2020-12-31'}], 'daily', 'date_out_of_range'),
    ([{'segment_id': 's1', 'target_date': '2023-02-30'}], 'daily', 'invalid_date'),
    ([{'segment_id': 's1', 'target_date': '2023-01-02', 'y_count': '0'}], 'daily', 'invalid_fields'),
    ([{'segment_id': 's1', 'target_date': '2023-01-02'}], '6h', 'invalid_fields'),
    ([{'segment_id': 's1', 'target_date': '2023-01-02', 'time_block': '06-18'}], '6h', 'invalid_time_block'),
    ([{'segment_id': 's1', 'target_date': '2023-01-02'}] * 2, 'daily', 'duplicate_keys'),
    ([{'segment_id': 's1', 'target_date': '2023-01-02'}], 'hourly', 'invalid_unit'),
    ([{'segment_id': 1, 'target_date': '2023-01-02'}], 'daily', 'invalid_value')])
def test_builder_rejects_invalid_requests(f, ctx, req, unit, code):
    with pytest.raises(f['RequestError']) as e:
        f['build_feature_rows'](ctx, req, unit)
    assert e.value.code == code


def test_builder_batch_limit(f, ctx):
    small = dict(ctx, settings=dict(ctx['settings'], max_rows=2))
    with pytest.raises(f['RequestError']):
        f['build_feature_rows'](small, [{'segment_id': 's1', 'target_date': d} for d in ('2023-01-02', '2023-01-03', '2023-01-04')], 'daily')


def test_prepared_context_reload_parity_and_tamper(f, ctx, ctx_tables, tmp_path):
    settings, seg, uns, D, wd, wb, ag = ctx_tables
    files = {}
    blobs = {'context_settings.json': json.dumps(settings).encode(), 'universe_segments.csv': f['csv_bytes'](seg), 'unsupported_segments.csv': f['csv_bytes'](uns),
             'date_features.csv': f['csv_bytes'](D), 'weather_context_daily.csv.gz': f['csv_bytes'](wd, gz=True),
             'weather_context_6h.csv.gz': f['csv_bytes'](wb, gz=True), 'aadt_groups.csv': f['csv_bytes'](ag)}
    for n, b in blobs.items():
        (tmp_path / n).write_bytes(b)
        files[n] = f['sha256_file'](tmp_path / n)
    C2 = f['load_prepared_context'](tmp_path, files)
    req = f['reference_requests'](ctx, 'daily', dict(CFG, reference={'seed': 1, 'rows_per_unit': 20, 'beyond_period_share': 0.1}))
    X1, M1 = f['build_feature_rows'](ctx, req, 'daily')
    X2, M2 = f['build_feature_rows'](C2, req, 'daily')
    assert f['frames_identical'](X1, X2) and f['frames_identical'](M1, M2)
    (tmp_path / 'ref.csv').write_bytes(f['csv_bytes'](pd.concat([M1, X1], axis=1)))
    X3 = f['read_numeric_csv'](tmp_path / 'ref.csv', ['segment_id', 'target_date', 'route_code'])[list(X1.columns)]
    assert f['frames_identical'](X1, X3)  # float repr round trip, no rounding hack
    req2 = f['reference_requests'](ctx, 'daily', dict(CFG, reference={'seed': 1, 'rows_per_unit': 20, 'beyond_period_share': 0.1}))
    assert req.equals(req2) and not req.duplicated().any()
    with pytest.raises(f['PreparationError']):
        f['load_prepared_context'](tmp_path, {k: v for k, v in files.items() if k != 'aadt_groups.csv'})
    (tmp_path / 'aadt_groups.csv').write_bytes(blobs['aadt_groups.csv'] + b'0001,0102,2022,1,1,1,1,1\n')
    with pytest.raises(f['PreparationError']):
        f['load_prepared_context'](tmp_path, files)


def test_leakage_negative_controls_all_rejected(f, h10, ctx):
    res = f['leakage_negative_controls'](ctx, h10, CFG)
    assert len(res) >= 20 and all(r['rejected'] for r in res), [r for r in res if not r['rejected']]


# ---------------------------------------------------------------- output guards and runner
def test_check_outputs_and_report_suffix(f, tmp_path):
    p = f['output_paths'](tmp_path / 'rerun-spatial-prep-x', CFG)
    assert f['check_outputs'](p, BACKEND, CFG)
    p['data_dir'].mkdir(parents=True)
    with pytest.raises(f['PreparationError']):
        f['check_outputs'](p, BACKEND, CFG)  # existing output never reused
    bad_cfg = dict(CFG, outputs={'report_dir': 'reports/v3/linkage_audit/x', 'data_dir': 'data/v3/sp'})
    bp = f['output_paths'](BACKEND, bad_cfg)  # paths from the SAME bad config that is checked
    assert bp['report_dir'] == BACKEND / 'reports' / 'v3' / 'linkage_audit' / 'x' and bp['data_dir'] == BACKEND / 'data' / 'v3' / 'sp'
    parent = bp['report_dir'].parent
    listing = sorted(os.listdir(parent)) if parent.is_dir() else None
    assert not os.path.lexists(bp['report_dir']) and not os.path.lexists(bp['data_dir'])
    with pytest.raises(f['PreparationError']) as e:
        f['check_outputs'](bp, BACKEND, bad_cfg)  # report dir inside the protected accepted linkage audit
    assert 'overlaps protected' in str(e.value)
    assert not os.path.lexists(bp['report_dir']) and not os.path.lexists(bp['data_dir'])  # nothing created
    assert listing == (sorted(os.listdir(parent)) if parent.is_dir() else None)  # protected dir unchanged
    for bad in ('rows.csv.gz', 'segments.geojson'):
        with pytest.raises(f['PreparationError']):
            f['check_report_file'](bad, CFG)
    assert f['check_report_file']('count_support.csv', CFG)


def test_runner_refusals(runner, tmp_path):
    assert runner.refusal(BACKEND / 'rerun-spatial-prep-test-never-created') is None
    assert 'already exists' in runner.refusal(BACKEND / 'notebooks')
    assert 'must start with' in runner.refusal(BACKEND / 'rerun-linkage-zzz-never')
    assert 'directly inside' in runner.refusal(tmp_path / 'rerun-spatial-prep-x')
    link = tmp_path / 'rerun-spatial-prep-link'
    os.symlink(tmp_path, link)
    assert 'symlink' in runner.refusal(link)
    cfg = copy.deepcopy(runner.config())
    cfg['outputs']['data_dir'] = '../data/v3/linkage_audit'
    msg = runner.refusal(BACKEND / 'rerun-spatial-prep-y', BACKEND, cfg)
    assert msg is not None
    env = runner.build_env(BACKEND / 'rerun-spatial-prep-z', BACKEND, {'ROADAWARE_STALE': '1', 'PATH': '/bin'})
    assert 'ROADAWARE_STALE' not in env and env['ROADAWARE_V3_OUTPUT_ROOT'].endswith('rerun-spatial-prep-z')
