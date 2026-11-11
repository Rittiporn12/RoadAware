"""Tests for V3 notebook 18 (conservative accident-to-road linkage audit + candidate segment inventories) and its runner. No network, no kernel.

The notebook's own '# FUNCTIONS' cells are executed (never the SETUP/pipeline cells), so the logic under test is the logic the notebook runs.
Road fixtures are drawn in EPSG:32647 metres near (700000, 1600000) (about 100.86E 14.47N, inside the pilot envelope), converted to lon/lat
with the notebook's own inverse transformer and fed through the notebook's GeoJSON -> metric path, so expected distances/offsets are known by
construction. Run from the repository root:
    .venv/bin/python -m pytest backend/tests/test_spatial_linkage_audit_notebook.py -q
"""
import copy
import gzip
import hashlib
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
NB18 = BACKEND / 'notebooks' / '18_spatial_linkage_audit.ipynb'
RUNNER = BACKEND / 'scripts' / 'run_spatial_linkage_audit.py'
CFG = json.loads((BACKEND / 'config' / 'spatial_linkage_v3.json').read_text('utf-8'))
TRUSTED_PINS = REPO / 'workflow' / 'wip' / '014-spatial-linkage' / 'trusted-input-pins.json'
X0, Y0 = 700000.0, 1600000.0
DOH, DRR, EXAT = 'กรมทางหลวง', 'กรมทางหลวงชนบท', 'การทางพิเศษแห่งประเทศไทย'
TAG = CFG['snapshot']['tag']


def code_cells(nb):
    d = json.loads(nb.read_text('utf-8'))
    return [''.join(c['source']) if isinstance(c['source'], list) else c['source'] for c in d['cells'] if c['cell_type'] == 'code']


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@pytest.fixture(scope='module')
def f():
    ns = {}
    cells = [s for s in code_cells(NB18) if s.lstrip().startswith('# FUNCTIONS')]
    assert len(cells) == 4
    for i, s in enumerate(cells):
        exec(compile(s, f'{NB18.stem}:FUNCTIONS[{i}]', 'exec'), ns)
    return ns


@pytest.fixture(scope='module')
def runner():
    spec = importlib.util.spec_from_file_location('run_spatial_linkage_audit', RUNNER)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture(scope='module')
def tr(f):
    return f['make_transformers'](CFG)


# ---------------------------------------------------------------- config pins and notebook structure
def test_config_pins_equal_trusted_codex_pins():
    if not TRUSTED_PINS.is_file():
        pytest.skip('trusted pin record not present')
    pins = json.loads(TRUSTED_PINS.read_text('utf-8'))
    for key, v in pins.items():
        spec = CFG['inputs'][key]
        assert 'backend/' + spec['path'] == v['path']
        assert spec['sha256'] == v['sha256']


def test_pinned_accepted_files_still_match_their_pins():
    # the three tracked accepted documents; the gitignored lineage only when present locally
    for key in ('road_manifest', 'road_review', 'readiness_manifest', 'lineage'):
        p = BACKEND / CFG['inputs'][key]['path']
        if not p.is_file():
            assert key == 'lineage', key + ' is tracked and must exist'
            continue
        assert sha(p) == CFG['inputs'][key]['sha256'], key


def test_config_derived_pins_equal_accepted_road_manifest():
    man = json.loads((BACKEND / CFG['inputs']['road_manifest']['path']).read_text('utf-8'))
    assert man['derived_files'] == CFG['inputs']['road_derived_sha256']
    assert man['cache_manifest_sha256'] == CFG['inputs']['road_manifest']['expect_cache_manifest_sha256']
    assert TAG == 'rc31' + man['cache_manifest_sha256'][:8]
    ready = json.loads((BACKEND / CFG['inputs']['readiness_manifest']['path']).read_text('utf-8'))
    entry = [e for e in ready['row_level_outputs_gitignored'] if e['path'] == CFG['inputs']['lineage']['manifest_key']]
    assert len(entry) == 1 and entry[0]['sha256'] == CFG['inputs']['lineage']['sha256']


def test_config_rules_are_the_preregistered_ones(f):
    assert f['validate_config'](CFG) == [25.0, 50.0, 100.0]
    m = CFG['matching']
    assert (m['primary_tolerance_m'], m['ambiguity_margin_m']) == (50, 5)
    assert CFG['segmentation']['resolutions_m'] == [500, 1000, 2000]
    assert CFG['alias_map'] == {}
    assert CFG['sources']['exat_expressway']['normalizer'] == 'exat_unresolved'


def test_setup_guards_before_reads_and_no_writes_before_outputs_cell():
    cells = code_cells(NB18)
    setup = next(s for s in cells if s.lstrip().startswith('# SETUP'))
    assert setup.index('check_outputs(') < setup.index('hash_paths(') < setup.index('verify_inputs(') < setup.index('load_lineage(')
    before = cells[:cells.index(next(s for s in cells if s.lstrip().startswith('# OUTPUTS')))]
    pipeline = [s for s in before if not s.lstrip().startswith('# FUNCTIONS')]
    assert not any(w in s for s in pipeline for w in ('atomic_write', 'write_outputs(', 'make_figures(', 'to_csv(', '.mkdir('))


def test_no_model_or_risk_output_in_notebook_source():
    src = '\n'.join(code_cells(NB18))
    for banned in ('.fit(', 'predict_proba', 'sklearn', 'lightgbm', 'xgboost', 'joblib.dump', 'RdYlGn', "'red'", "'green'"):
        assert banned not in src, banned


# ---------------------------------------------------------------- fail-closed input verification (tampered SHA / IDs)
def build_inputs(tmp_path):
    b, cfg = tmp_path / 'backend', copy.deepcopy(CFG)
    inp = cfg['inputs']
    derived = b / inp['road_derived_dir']
    derived.mkdir(parents=True)
    dsha = {}
    for name in sorted(inp['road_derived_sha256']):
        (derived / name).write_bytes(('fixture ' + name).encode())
        dsha[name] = sha(derived / name)
    lin = b / inp['lineage']['path']
    lin.parent.mkdir(parents=True)
    lin.write_bytes(gzip.compress(b'event_uid\n', mtime=0))
    counts = {'doh_highway': 3, 'drr_rural': 2, 'exat_expressway': 1}
    docs = {
        'road_manifest': {'status': 'complete', 'version': inp['road_manifest']['expect_version'],
                          'cache_manifest_sha256': inp['road_manifest']['expect_cache_manifest_sha256'],
                          'preregistration': {'envelope_epsg4326': cfg['envelope_epsg4326']}, 'derived_files': dsha,
                          'sources': {k: {'count': v} for k, v in counts.items()}},
        'road_review': {'status': inp['road_review']['expect_status'], 'counts': {k: {'exact_ids': v, 'not_simple': 0} for k, v in counts.items()}},
        'readiness_manifest': {'status': 'complete', 'linkage': {'retained_events_linked': 5},
                               'row_level_outputs_gitignored': [{'path': inp['lineage']['manifest_key'], 'rows': 5, 'sha256': sha(lin)}]},
    }
    for key, doc in docs.items():
        write_doc(b, cfg, key, doc)
    inp['road_derived_sha256'] = dict(dsha)
    inp['lineage']['sha256'] = sha(lin)
    return b, cfg, docs


def write_doc(b, cfg, key, doc, repin=True):
    p = b / cfg['inputs'][key]['path']
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(doc), 'utf-8')
    if repin:
        cfg['inputs'][key]['sha256'] = sha(p)


def test_verify_inputs_accepts_consistent_pins(f, tmp_path):
    b, cfg, _ = build_inputs(tmp_path)
    rows, docs, expect = f['verify_inputs'](b, cfg)
    assert expect == {'lineage_rows': 5, 'retained_events_linked': 5, 'road_counts': {'doh_highway': 3, 'drr_rural': 2, 'exat_expressway': 1}}
    assert (rows['status'] == 'pass').all() and len(rows) == 3 + 7 + 1


def _tamper_derived(b, cfg, docs):
    p = b / cfg['inputs']['road_derived_dir'] / 'doh_highway_full.geojson'
    p.write_bytes(p.read_bytes() + b' ')


def _tamper_manifest_unpinned(b, cfg, docs):
    d = copy.deepcopy(docs['road_manifest'])
    d['sources']['doh_highway']['count'] = 4
    write_doc(b, cfg, 'road_manifest', d, repin=False)


def _config_pin_differs_from_manifest(b, cfg, docs):
    cfg['inputs']['road_derived_sha256']['drr_rural_full.geojson'] = '0' * 64


def _null_pin(b, cfg, docs):
    cfg['inputs']['road_review']['sha256'] = None


def _review_ids_differ(b, cfg, docs):
    d = copy.deepcopy(docs['road_review'])
    d['counts']['exat_expressway']['exact_ids'] = 2
    write_doc(b, cfg, 'road_review', d)


def _lineage_pin_not_readiness(b, cfg, docs):
    cfg['inputs']['lineage']['sha256'] = 'f' * 64


def _lineage_bytes_tampered(b, cfg, docs):
    p = b / cfg['inputs']['lineage']['path']
    p.write_bytes(gzip.compress(b'event_uid\nx\n', mtime=0))


def _manifest_status_failed(b, cfg, docs):
    d = copy.deepcopy(docs['road_manifest'])
    d['status'] = 'failed'
    write_doc(b, cfg, 'road_manifest', d)


def _envelope_differs(b, cfg, docs):
    d = copy.deepcopy(docs['road_manifest'])
    d['preregistration']['envelope_epsg4326'] = [100.2, 13.5, 102.0, 15.4]
    write_doc(b, cfg, 'road_manifest', d)


@pytest.mark.parametrize('tamper,msg', [
    (_tamper_derived, 'sha256 mismatch'),
    (_tamper_manifest_unpinned, 'road_manifest: sha256 mismatch'),
    (_config_pin_differs_from_manifest, 'differs from the road manifest'),
    (_null_pin, 'not pinned'),
    (_review_ids_differ, 'exact_ids differ'),
    (_lineage_pin_not_readiness, 'lineage pin is not'),
    (_lineage_bytes_tampered, 'lineage: sha256 mismatch'),
    (_manifest_status_failed, 'is not the accepted'),
    (_envelope_differs, 'envelope differs'),
])
def test_verify_inputs_fails_closed(f, tmp_path, tamper, msg):
    b, cfg, docs = build_inputs(tmp_path)
    tamper(b, cfg, docs)
    with pytest.raises(f['LinkageError'], match=msg):
        f['verify_inputs'](b, cfg)


def test_geometry_ids_reconcile_with_manifest_count(f):
    E = f['LinkageError']
    diag = pd.DataFrame({'oid': ['1', '2', '3'], 'geojson_ok': ['True', 'True', 'False']})
    assert f['check_geometry_ids']('doh_highway', [1, 2], diag, 3, [1, 2])
    with pytest.raises(E, match='road manifest count'):
        f['check_geometry_ids']('doh_highway', [1, 2], diag, 4, [1, 2])
    with pytest.raises(E, match='duplicate OID'):
        f['check_geometry_ids']('doh_highway', [1, 2], diag.assign(oid=['1', '1', '3']), 3)
    with pytest.raises(E, match='duplicate geometry id'):
        f['check_geometry_ids']('doh_highway', [1, 1], diag, 3)
    with pytest.raises(E, match='differ from the diagnostics'):
        f['check_geometry_ids']('doh_highway', [1, 3], diag, 3)
    with pytest.raises(E, match='differs from its OID attribute'):
        f['check_geometry_ids']('doh_highway', [1, 2], diag, 3, [1, 5])


# ---------------------------------------------------------------- lineage: unique event UIDs, text columns, coordinate flags without repair
def lineage_frame(f, n):
    d = {c: [''] * n for c in f['LINEAGE_REQUIRED']}
    d.update(event_uid=['u%03d' % i for i in range(n)], ce_year=['2022'] * n, split=['train'] * n, raw_route_code=['0001'] * n, lat_decimals=['06'] * n)
    return pd.DataFrame(d)


def test_load_lineage_keeps_text_and_leading_zeros(f, tmp_path):
    p = tmp_path / 'lin.csv.gz'
    p.write_bytes(gzip.compress(lineage_frame(f, 3).to_csv(index=False).encode('utf-8'), mtime=0))
    df = f['load_lineage'](p, 3, CFG)
    assert df['raw_route_code'].tolist() == ['0001'] * 3 and df['lat_decimals'].tolist() == ['06'] * 3


def test_duplicate_event_uid_count_and_split_fail(f):
    E = f['LinkageError']
    df = lineage_frame(f, 4)
    assert len(f['check_events'](df, 4, CFG)) == 4
    with pytest.raises(E, match='duplicate event_uid'):
        f['check_events'](df.assign(event_uid=['a', 'b', 'a', 'c']), 4, CFG)
    with pytest.raises(E, match='readiness manifest records'):
        f['check_events'](df, 5, CFG)
    with pytest.raises(E, match='split that disagrees'):
        f['check_events'](df.assign(ce_year=['2022', '2024', '2022', '2022']), 4, CFG)
    with pytest.raises(E, match='empty event_uid'):
        f['check_events'](df.assign(event_uid=['a', ' ', 'b', 'c']), 4, CFG)


def test_coordinate_flags_are_never_repaired(f):
    usable = CFG['event_fields']['usable_coord_status']
    df = pd.DataFrame({
        'lat_value': ['14.47', '100.86', '', '14.0', '14.5', '14.5'],
        'lon_value': ['100.86', '14.47', '', '99.5', '100.9', '100.9'],
        'coord_status': [usable, 'latlon_swap_suspect', 'missing', usable, usable, usable],
        'low_precision_flag': ['False', 'False', 'False', 'False', 'True', 'False'],
        'lat_equals_lon_flag': ['False', 'False', 'False', 'False', 'False', 'True'],
        'repeated_coord_flag': ['True', 'False', 'False', 'False', 'False', 'False'],
    })
    c = f['coordinate_audit'](df, CFG)
    assert c['scope'].tolist() == ['pilot', 'coord_not_usable', 'coord_not_usable', 'outside_envelope', 'pilot', 'pilot']
    assert c['precision_class'].tolist() == ['adequate_unverified', 'not_usable', 'not_usable', 'adequate_unverified',
                                             'low_precision_unsuitable', 'low_precision_unsuitable']
    assert c.loc[1, 'lat'] == 100.86 and c.loc[1, 'lon'] == 14.47  # swapped values kept as given
    assert math.isnan(c.loc[2, 'lat']) and math.isnan(c.loc[2, 'lon'])
    assert c['repeated_coord'].tolist() == [True, False, False, False, False, False]
    with pytest.raises(f['LinkageError'], match='non-finite'):
        f['coordinate_audit'](df.assign(coord_status=usable), CFG)


# ---------------------------------------------------------------- CRS
def test_utm47n_projection_against_independent_geodesic(f, tr):
    fwd, _ = tr
    xy = f['project_xy'](fwd, [[99.0, 0.0], [99.0, 14.0]])
    # on the UTM 47N central meridian: x = false easting, y = k0 * meridian arc length (pyproj Geod, independent of the projection)
    arc = f['geod']().inv(99.0, 0.0, 99.0, 14.0)[2]
    assert abs(xy[0, 0] - 500000.0) < 1e-6 and abs(xy[0, 1]) < 1e-6
    assert abs(xy[1, 0] - 500000.0) < 1e-6 and abs(xy[1, 1] - 0.9996 * arc) < 1e-3


def test_crs_rules_enforced(f):
    for bad in ({'always_xy': False}, {'metric_epsg': 3857}, {'geographic_epsg': 4240}):
        cfg = copy.deepcopy(CFG)
        cfg['crs'].update(bad)
        with pytest.raises(f['LinkageError'], match='CRS'):
            f['validate_config'](cfg)


# ---------------------------------------------------------------- route identity: exact agency, strict per-agency normalization
def test_doh_normalization(f):
    n = f['norm_doh']
    assert n('1') == ('standard', '0001') and n('0001') == ('standard', '0001') and n(' 12 ') == ('standard', '0012')
    assert n('１２') == ('standard', '0012')  # full-width digits -> NFKC ASCII
    for raw in ('12345', '1.5', '1A', '๑', 'ทล.1', '-1'):
        assert n(raw) == ('route_nonstandard', None), raw
    assert n('') == ('route_missing', None) and n('  ') == ('route_missing', None)


def test_drr_normalization_keeps_prefix_and_zeros_without_padding(f):
    n = f['norm_drr']
    assert n('นบ.3021') == ('standard', 'นบ.3021')
    assert n('นบ. 3021') == ('standard', 'นบ.3021') and n('นบ..3021') == ('standard', 'นบ.3021') and n('.นบ.3021.') == ('standard', 'นบ.3021')
    assert n('นบ.0021') == ('standard', 'นบ.0021')
    for raw in ('นบ.21', 'นบ3021', 'ab.3021', 'นบ.๓๐๒๑', 'นบ.30210', 'น.3021', '3021'):
        assert n(raw) == ('route_nonstandard', None), raw
    assert n('ส.013') == ('route_special_unverified', 'ส.013') and n('ส.012') == ('route_special_unverified', 'ส.012')
    assert n('') == ('route_missing', None)


def test_exat_never_resolved(f):
    assert f['norm_exat']('E007S013|I') == ('identity_unresolved', None)
    assert f['norm_exat']('RAE') == ('identity_unresolved', None)
    assert f['norm_exat']('') == ('route_missing', None)


def test_exact_agency_crosswalk_no_substring_no_cross_source_merge(f):
    idx = {('doh_highway', '0001'): [0], ('drr_rural', 'นบ.3021'): [1], ('doh_highway', '3021'): [2]}
    df = pd.DataFrame({'raw_agency': [DOH, DRR, DRR, DOH, 'ทางหลวง', DRR + ' ฯ', EXAT, DOH, ' ' + DOH + ' ', DRR],
                       'raw_route_code': ['1', '1', 'นบ.3021', 'นบ.3021', '1', 'นบ.3021', 'E007S013|I', '0002', ' 1 ', '3021']})
    out = f['event_identity'](df, CFG, idx)
    assert out['source_id'].tolist() == ['doh_highway', 'drr_rural', 'drr_rural', 'doh_highway', None, None, 'exat_expressway', 'doh_highway',
                                         'doh_highway', 'drr_rural']
    assert out['identity_status'].tolist() == ['verified', 'route_nonstandard', 'verified', 'route_nonstandard', 'agency_unmapped', 'agency_unmapped',
                                               'identity_unresolved', 'route_not_in_snapshot', 'verified', 'route_nonstandard']
    assert out['route_key_matched'].tolist() == ['0001', None, 'นบ.3021', None, None, None, None, None, '0001', None]


def test_alias_map_requires_evidence_and_exact_key(f):
    cfg = copy.deepcopy(CFG)
    cfg['alias_map'] = {'drr_rural': {'ส.013': {'target': 'นบ.3021'}}}
    with pytest.raises(f['LinkageError'], match='evidence'):
        f['validate_config'](cfg)
    cfg['alias_map'] = {'drr_rural': {'ส.013': {'target': 'นบ.3021', 'evidence': 'fixture citation'}},
                        'exat_expressway': {'E007S013|I': {'target': 'RAE', 'evidence': 'fixture citation'}}}
    f['validate_config'](cfg)
    df = pd.DataFrame({'raw_agency': [DRR, DRR, EXAT], 'raw_route_code': ['ส.013', 'ส.0013', 'E007S013|I']})
    out = f['event_identity'](df, cfg, {('drr_rural', 'นบ.3021'): [0], ('exat_expressway', 'RAE'): [1]})
    assert out['identity_status'].tolist() == ['verified', 'route_special_unverified', 'identity_unresolved']
    assert out['normalization_rule'].iloc[0] == 'drr_prefix_digits+alias'


# ---------------------------------------------------------------- road fixtures (metric construction -> lon/lat GeoJSON -> notebook path)
SCENE = [
    ('doh_highway', 101, '0001', [[(0, 0), (0, 2048)]]),
    ('doh_highway', 102, '0001', [[(0, 2048), (0, 4096)]]),  # same route, shares the junction point (0, 2048)
    ('doh_highway', 201, '0002', [[(1000, 0), (1000, 2000)], [(1020, 0), (1020, 2000)]]),  # multipart parallel carriageways 20 m apart
    ('doh_highway', 301, '0003', [[(3000, 0), (3500, 500), (3500, 0), (3000, 500)]]),  # self-crossing (non-simple)
    ('doh_highway', 401, '3021', [[(5000, 0), (5000, 2000)]]),
    ('drr_rural', 5001, 'นบ.3021', [[(6000, 0), (6000, 2000)]]),
    ('exat_expressway', 1, 'RAE', [[(8000, 0), (8000, 2000)]]),
]


def road(f, inv, sid, oid, route, parts, name=''):
    spec = CFG['sources'][sid]
    lines = [f['project_xy'](inv, [(X0 + x, Y0 + y) for x, y in p]).tolist() for p in parts]
    geom = {'type': 'LineString', 'coordinates': lines[0]} if len(lines) == 1 else {'type': 'MultiLineString', 'coordinates': lines}
    props = {spec['oid_field']: oid, spec['route_field']: route}
    if spec.get('name_field'):
        props[spec['name_field']] = name
    return {'source_id': sid, 'oid': oid, 'geometry': geom, 'route_raw': route, 'props': props}


def diag_for(feats):
    from shapely.geometry import shape
    rows = []
    for ft in feats:
        g = shape(ft['geometry'])
        rows.append({'source_id': ft['source_id'], 'oid': str(ft['oid']), 'geojson_ok': 'True', 'shapely_valid': str(bool(g.is_valid)),
                     'shapely_simple': str(bool(g.is_simple)), 'empty_or_short_part': 'False', 'nonfinite_coord': 'False', 'curve_geometry': 'False',
                     'latlon_swap_suspect': 'False', 'length_full_m': '0', 'length_clipped_m': '0'})
    return pd.DataFrame(rows)


# event uid, agency, route, metric (x, y) offset from (X0, Y0) or explicit (lat_value, lon_value) strings, optional kind
USABLE = CFG['event_fields']['usable_coord_status']
EVENTS = [
    ('e01', DOH, '1', (30, 600)), ('e02', DOH, '0001', (10, 1024)), ('e03', DOH, '1', (30, 2048)), ('e04', DOH, '2', (1009, 1000)),
    ('e05', DOH, '2', (1010, 1000)), ('e06', DOH, '2', (998, 1100)), ('e07', DOH, '3', (3510, 100)), ('e08', DOH, '1', (60, 1100)),
    ('e09', DOH, '1', (5, 700), 'lowp'), ('e10', EXAT, 'E007S013|I', (8005, 500)), ('e11', DRR, 'นบ.3021', (5010, 1200)),
    ('e12', DRR, '3021', (5010, 1200)), ('e13', DOH, '3021', (5010, 1200)), ('e14', DRR, 'ส.013', (6005, 500)),
    ('e15', 'สำนักงานกรมทางหลวง', '1', (5, 300)), ('e16', DOH, '9999', (5, 300)), ('e17', DOH, '', (5, 300)),
    ('e18', DOH, '1', ('100.86', '14.47'), 'swap'), ('e19', DOH, '1', ('', ''), 'missing'), ('e20', DOH, '1', ('14.0', '99.5'), 'outside'),
    ('e21', DRR, 'นบ.3021', (6020, 1300)), ('e22', DOH, '1', (5, 800), 'lateqlon'), ('e23', ' ' + DOH + ' ', ' 1 ', (20, 300)),
]
EXPECTED = {  # (25 m, 50 m, 100 m)
    'e01': ('too_far', 'matched', 'matched'), 'e02': ('matched',) * 3, 'e03': ('too_far', 'ambiguous_multiple', 'ambiguous_multiple'),
    'e04': ('ambiguous_multiple',) * 3, 'e05': ('ambiguous_multiple',) * 3, 'e06': ('matched',) * 3, 'e07': ('ambiguous_unsafe_geometry',) * 3,
    'e08': ('too_far', 'too_far', 'matched'), 'e09': ('low_precision_unsuitable',) * 3, 'e10': ('identity_unresolved',) * 3,
    'e11': ('too_far',) * 3, 'e12': ('route_nonstandard',) * 3, 'e13': ('matched',) * 3, 'e14': ('route_special_unverified',) * 3,
    'e15': ('agency_unmapped',) * 3, 'e16': ('route_not_in_snapshot',) * 3, 'e17': ('route_missing',) * 3, 'e18': ('coord_not_usable',) * 3,
    'e19': ('coord_not_usable',) * 3, 'e20': ('outside_pilot_envelope',) * 3, 'e21': ('matched',) * 3, 'e22': ('low_precision_unsuitable',) * 3,
    'e23': ('matched',) * 3,
}
# matched-any events: chosen OID, part, distance (m, by construction), offset along the piece (m) -> segment index per 500/1000/2000 m
CHOSEN = {'e01': (101, 0, 30.0, 600.0), 'e02': (101, 0, 10.0, 1024.0), 'e06': (201, 0, 2.0, 1100.0), 'e08': (101, 0, 60.0, 1100.0),
          'e13': (401, 0, 10.0, 1200.0), 'e21': (5001, 0, 20.0, 1300.0), 'e23': (101, 0, 20.0, 300.0)}


def event_frame(f, inv):
    rows = []
    for e in EVENTS:
        uid, agency, route, loc = e[:4]
        kind = e[4] if len(e) > 4 else ''
        if isinstance(loc[0], str):
            lat, lon = loc  # explicit (lat_value, lon_value) text exactly as recorded; e18 holds the longitude in lat_value (swap, not repaired)
        else:
            lon_f, lat_f = f['project_xy'](inv, [(X0 + loc[0], Y0 + loc[1])])[0]
            lat, lon = '%.12f' % lat_f, '%.12f' % lon_f
        status = {'swap': 'latlon_swap_suspect', 'missing': 'missing'}.get(kind, USABLE)
        seen = kind in ('swap', 'missing', 'outside')
        rows.append({'event_uid': uid, 'ce_year': '2024' if seen else '2022', 'split': 'seen_diagnostic' if seen else 'train',
                     'event_date': '2024-03-01' if seen else '2022-03-01', 'raw_agency': agency, 'raw_route_code': route, 'raw_route_name': '',
                     'lat_value': lat, 'lon_value': lon, 'coord_status': status, 'low_precision_flag': str(kind == 'lowp'),
                     'lat_equals_lon_flag': str(kind == 'lateqlon'), 'repeated_coord_flag': str(uid in ('e04', 'e05')), 'km_value': '', 'km_status': 'missing'})
    return pd.DataFrame(rows)


@pytest.fixture(scope='module')
def scene(f, tr):
    fwd, inv = tr
    feats = [road(f, inv, *s, name='ทางพิเศษฉลองรัช' if s[0] == 'exat_expressway' else '') for s in SCENE]
    features, parts, pieces = f['build_roads'](feats, diag_for(feats), CFG, fwd)
    idx = f['route_index'](parts)
    lin = event_frame(f, inv)
    ev = pd.concat([lin, f['coordinate_audit'](lin, CFG), f['event_identity'](lin, CFG, idx)], axis=1)
    tols = f['validate_config'](CFG)
    E = pd.concat([ev, f['link_events'](ev, parts, pieces, CFG, fwd, tols)], axis=1)
    E['source_label'] = E['source_id'].fillna('unmapped_agency')
    segs = f['build_segments'](pieces, CFG, inv)
    return {'features': features, 'parts': parts, 'pieces': pieces, 'E': E, 'tols': tols, 'segs': segs, 'feats': feats}


def test_road_parts_and_unsafe_geometry(scene):
    F, P = scene['features'].set_index('oid'), scene['parts']
    assert F.loc[201, 'n_parts'] == 2 and len(P[P['oid'] == 201]) == 2
    assert bool(F.loc[301, 'unsafe']) and 'not_simple' in F.loc[301, 'unsafe_reasons'] and not bool(F.loc[301, 'simple'])
    assert int(F['unsafe'].sum()) == 1
    assert abs(P.loc[P['oid'] == 101, 'len_utm_m'].iloc[0] - 2048.0) < 1e-3
    assert F.loc[1, 'route_status'] == 'identity_unresolved'  # EXAT geometry route 'RAE' is never indexed as a verified identity


UNSAFE_CHECK = 'unsafe flag is feature-level'


def unsafe_check(f, features, parts, pieces):
    # only the unsafe-consistency check is inspected; the length/id checks need real diagnostics
    review = {'counts': {sid: {'not_simple': 0} for sid in CFG['sources']}}
    got = [c for c in f['geometry_checks'](features, parts, pieces, {sid: [] for sid in CFG['sources']}, review, CFG, 0)
           if c['check'].startswith(UNSAFE_CHECK)]
    assert len(got) == 1
    return got[0]


SHARED_OID = [('doh_highway', 8, False), ('drr_rural', 8, True), ('exat_expressway', 8, False)]


def flag_frames(feats, parts, pieces):
    F = pd.DataFrame([{'source_id': s, 'oid': o, 'unsafe': u, 'simple': True, 'n_pieces': 1, 'len_full_geod_m': 0.0, 'diag_length_full_m': 0.0,
                       'len_clipped_geod_m': 0.0, 'diag_length_clipped_m': 0.0} for s, o, u in feats])
    return F, pd.DataFrame(parts, columns=['source_id', 'oid', 'unsafe']), pd.DataFrame(pieces, columns=['source_id', 'oid', 'unsafe'])


def test_unsafe_consistency_passes_built_roads_and_legit_shared_oid(f, scene):
    assert unsafe_check(f, scene['features'], scene['parts'], scene['pieces'])['status'] == 'pass'  # includes unsafe OID 301
    c = unsafe_check(f, *flag_frames(SHARED_OID, SHARED_OID, SHARED_OID + [('drr_rural', 8, True)]))
    assert c['status'] == 'pass' and c['evidence']['pieces']['rows'] == 4 and c['evidence']['duplicate_feature_ids'] == 0


def _set(rows, sid, oid, unsafe):
    return [(s, o, unsafe if (s, o) == (sid, oid) else u) for s, o, u in rows]


@pytest.mark.parametrize('feats, parts, pieces, where, key', [
    # cross-source shared OID 8: corrupted DOH piece flag; the pre-014b OID-only check reported inconsistent_pieces 0 here
    (SHARED_OID, SHARED_OID, _set(SHARED_OID, 'doh_highway', 8, True), 'pieces', 'unsafe_child_of_safe_parent'),
    (SHARED_OID, SHARED_OID, _set(SHARED_OID, 'drr_rural', 8, False), 'pieces', 'safe_child_of_unsafe_parent'),
    (SHARED_OID, _set(SHARED_OID, 'exat_expressway', 8, True), SHARED_OID, 'parts', 'unsafe_child_of_safe_parent'),
    (SHARED_OID, _set(SHARED_OID, 'drr_rural', 8, False), SHARED_OID, 'parts', 'safe_child_of_unsafe_parent'),
    (SHARED_OID, SHARED_OID, SHARED_OID + [('doh_highway', 9, False)], 'pieces', 'missing_parent'),
    (SHARED_OID[:2], SHARED_OID[:2] + [('exat_expressway', 8, False)], SHARED_OID[:2], 'parts', 'missing_parent'),
    (SHARED_OID + [('doh_highway', 8, False)], SHARED_OID, SHARED_OID, None, 'duplicate_feature_ids'),
])
def test_unsafe_consistency_uses_source_and_oid_in_both_directions(f, feats, parts, pieces, where, key):
    F, P, C = flag_frames(feats, parts, pieces)
    c = unsafe_check(f, F, P, C)
    assert c['status'] == 'fail'
    ev = c['evidence'] if where is None else c['evidence'][where]
    assert ev[key] == 1
    if where is not None:
        assert len(ev['examples']) == 1
    if key == 'unsafe_child_of_safe_parent' and where == 'pieces':
        old_bad = int((C['unsafe'] & ~C['oid'].isin(F.loc[F['unsafe'], 'oid'])).sum())
        assert old_bad == 0  # documents the defect: the OID-only rule silently passed this corruption


def test_linkage_statuses_at_every_tolerance(scene):
    E = scene['E'].set_index('event_uid')
    for uid, exp in EXPECTED.items():
        got = tuple(E.loc[uid, 'status_' + lab] for lab in ('25m', '50m', '100m'))
        assert got == exp, (uid, got)


def test_metric_distances_and_chosen_part(scene):
    E = scene['E'].set_index('event_uid')
    for uid, (oid, part, dist, _) in CHOSEN.items():
        assert int(E.loc[uid, 'chosen_source_oid']) == oid and int(E.loc[uid, 'chosen_part']) == part, uid
        assert abs(E.loc[uid, 'chosen_distance_m'] - dist) < 1e-3, uid
    assert abs(E.loc['e06', 'chosen_second_distance_m'] - 22.0) < 1e-3  # other carriageway, outside the 5 m margin
    assert math.isnan(E.loc['e02', 'chosen_second_distance_m'])  # next same-identity part beyond the search radius: unknown, not 0
    assert abs(E.loc['e04', 'best_same_identity_m'] - 9.0) < 1e-3 and abs(E.loc['e04', 'second_same_identity_m'] - 11.0) < 1e-3


def test_tolerance_monotone_eligible_counts_and_nesting(scene):
    E = scene['E'].set_index('event_uid')
    assert [int(E.loc['e01', 'n_eligible_' + t]) for t in ('25m', '50m', '100m')] == [0, 1, 1]
    assert [int(E.loc['e03', 'n_eligible_' + t]) for t in ('25m', '50m', '100m')] == [0, 2, 2]
    assert [int(E.loc['e08', 'n_eligible_' + t]) for t in ('25m', '50m', '100m')] == [0, 0, 1]
    assert [int(E.loc['e04', 'n_eligible_' + t]) for t in ('25m', '50m', '100m')] == [2, 2, 2]
    assert (E['n_eligible_25m'] <= E['n_eligible_50m']).all() and (E['n_eligible_50m'] <= E['n_eligible_100m']).all()
    m25, m50, m100 = (E['status_' + t] == 'matched' for t in ('25m', '50m', '100m'))
    assert (~m25 | m50).all() and (~m50 | m100).all()


def test_cross_source_route_never_merges_and_exat_never_forced(scene):
    E = scene['E'].set_index('event_uid')
    # DRR นบ.3021 recorded 10 m from DOH 3021 geometry: the DOH road is not eligible; DRR geometry is 990 m away -> too_far
    assert E.loc['e11', 'identity_status'] == 'verified' and math.isnan(E.loc['e11', 'best_same_identity_m'])
    assert abs(E.loc['e11', 'nearest_any_road_m'] - 10.0) < 1e-3 and E.loc['e11', 'nearest_any_road_source'] == 'doh_highway'
    assert abs(E.loc['e11', 'nearest_same_agency_any_route_m'] - 990.0) < 1e-3
    # EXAT 5 m from EXAT geometry: diagnostic distance recorded, never accepted
    assert abs(E.loc['e10', 'nearest_any_road_m'] - 5.0) < 1e-3 and E.loc['e10', 'nearest_any_road_source'] == 'exat_expressway'
    assert pd.isna(E.loc['e10', 'chosen_source_oid']) and E.loc['e10', 'segment_id_500m'] is None


def test_unknown_is_never_zero_and_one_assignment_per_event(scene):
    E = scene['E']
    any_m = E[['status_25m', 'status_50m', 'status_100m']].eq('matched').any(axis=1)
    assert set(E.loc[any_m, 'event_uid']) == set(CHOSEN)
    um = E[~any_m]
    for c in ('chosen_distance_m', 'chosen_second_distance_m', 'offset_on_part_m', 'offset_on_piece_m'):
        assert um[c].isna().all(), c
    for c in ('chosen_source_oid', 'chosen_part', 'chosen_piece', 'segment_id_500m', 'segment_id_1000m', 'segment_id_2000m'):
        assert um[c].isna().all(), c
    assert (um['segment_status'] == 'not_matched').all()
    assert E['event_uid'].is_unique
    for R in (500, 1000, 2000):
        assert E.loc[any_m, 'segment_id_%dm' % R].map(lambda s: isinstance(s, str)).all()


def test_event_segment_ids_and_offsets(scene):
    E = scene['E'].set_index('event_uid')
    short = {101: 'doh', 201: 'doh', 401: 'doh', 5001: 'drr'}
    for uid, (oid, part, _, off) in CHOSEN.items():
        assert E.loc[uid, 'segment_status'] == 'assigned' and abs(E.loc[uid, 'offset_on_piece_m'] - off) < 1e-3, uid
        for R in (500, 1000, 2000):
            want = 'rsv1-%s:%s:%d:p%d:c0:r%d:%05d' % (TAG, short[oid], oid, part, R, int(off // R))
            assert E.loc[uid, 'segment_id_%dm' % R] == want, (uid, R)


def test_scene_passes_the_notebook_event_and_segment_checks(f, scene):
    E = scene['E']
    checks = f['event_checks'](E, CFG, scene['tols'], {'lineage_rows': len(E)}) + f['segment_checks'](scene['segs'], scene['pieces'], E, CFG)
    failing = [c['check'] for c in checks if c['status'] != 'pass']
    assert failing == []


def test_event_checks_detect_zero_filled_unknown(f, scene):
    E = scene['E'].copy()
    E.loc[E['event_uid'] == 'e11', 'chosen_distance_m'] = 0.0
    checks = {c['check']: c['status'] for c in f['event_checks'](E, CFG, scene['tols'], {'lineage_rows': len(E)})}
    assert checks['unknown never zero: non-matched rows carry no distance/offset/segment (missing, not 0)'] == 'fail'


def test_review_sample_deterministic(f, scene):
    a_strata, a = f['review_sample'](scene['E'], CFG)
    b_strata, b = f['review_sample'](scene['E'], CFG)
    assert a['event_uid'].tolist() == b['event_uid'].tolist() and a_strata.equals(b_strata)
    assert (a['review_status'] == 'pending_manual_review').all()
    assert set(a['scope']) == {'pilot'}


# ---------------------------------------------------------------- segmentation (geometry universe, lengths, short finals, stable IDs, boundaries)
def manual_pieces(rows):
    from shapely.geometry import LineString
    out = []
    for i, (oid, coords, unsafe) in enumerate(rows):
        out.append({'piece_uid': i, 'part_uid': i, 'source_id': 'doh_highway', 'oid': oid, 'part': 0, 'piece': 0,
                    'geom_utm': LineString([(X0 + x, Y0 + y) for x, y in coords]), 'unsafe': unsafe, 'clipped_at_start': False, 'clipped_at_end': False,
                    'route_raw': '0001', 'route_key': '0001', 'route_status': 'standard', 'overlap_flag': False, 'duplicate_flag': False})
    df = pd.DataFrame(out)
    df['len_utm_m'] = [g.length for g in df['geom_utm']]
    return df


def test_segment_lengths_short_finals_and_conservation(f, tr):
    _, inv = tr
    pieces = manual_pieces([(11, [(0, 0), (0, 2048)], False), (12, [(100, 0), (100, 700), (1700, 700)], False), (13, [(0, 5000), (0, 6000)], True)])
    segs = f['build_segments'](pieces, CFG, inv)
    want = {500: {11: [500, 500, 500, 500, 48], 12: [500, 500, 500, 500, 300]},
            1000: {11: [1000, 1000, 48], 12: [1000, 1000, 300]},
            2000: {11: [2000, 48], 12: [2000, 300]}}
    for R, S in segs.items():
        assert 13 not in set(S['oid'])  # unsafe geometry never segmented
        for oid, lengths in want[R].items():
            g = S[S['oid'] == oid].sort_values('seg_index')
            assert np.allclose(g['length_m'].to_numpy(float), lengths, atol=1e-6), (R, oid)
            assert abs(g['length_m'].sum() - sum(lengths)) < 0.01
            assert g['short_final'].tolist() == [False] * (len(lengths) - 1) + [True]
            assert (g['n_in_piece'] == len(lengths)).all()
            # projected / geodesic: UTM scale factor ~1.00009 at 200 km east of the central meridian (reported, never corrected)
            ratio = g['length_m'].to_numpy(float) / g['length_geod_m'].to_numpy(float)
            assert ((ratio > 1.00005) & (ratio < 1.00013)).all(), (R, oid, ratio)
        assert S['segment_id'].is_unique
    corner = segs[500][(segs[500]['oid'] == 12) & (segs[500]['seg_index'] == 1)].iloc[0]['coords_utm']
    assert len(corner) == 3 and np.allclose(corner[1], [X0 + 100, Y0 + 700])  # vertex kept inside the cut segment
    again = f['build_segments'](pieces, CFG, inv)
    assert all(again[R]['segment_id'].tolist() == segs[R]['segment_id'].tolist() for R in segs)
    assert segs[500]['segment_id'].iloc[4] == 'rsv1-%s:doh:11:p0:c0:r500:00004' % TAG


def test_segment_index_endpoint_convention(f):
    si, ns, eps = f['segment_index'], f['n_segments'], CFG['segmentation']['zero_remainder_eps_m']
    assert [si(t, 2048.0, 500, eps) for t in (0.0, 499.999, 500.0, 1000.0, 1999.999, 2000.0, 2048.0)] == [0, 0, 1, 2, 3, 4, 4]
    assert [si(t, 2000.0, 500, eps) for t in (1500.0, 1999.9, 2000.0)] == [3, 3, 3]  # last segment closed at the piece end
    assert ns(2000.0, 500, eps) == 4 and ns(2000.0005, 500, eps) == 4 and ns(2000.01, 500, eps) == 5 and ns(0.0, 500, eps) == 1
    with pytest.raises(f['LinkageError']):
        si(2049.0, 2048.0, 500, eps)
    with pytest.raises(f['LinkageError']):
        si(-1.0, 2048.0, 500, eps)


INTERVAL_CHECK = 'segment length equals its interval'


def no_events():
    cols = {'segment_id_%dm' % R: pd.Series([], dtype=object) for R in CFG['segmentation']['resolutions_m']}
    return pd.DataFrame(dict(cols, chosen_source_oid=pd.Series([], dtype=float)))


def interval_status(f, segs, pieces):
    got = {}
    for c in f['segment_checks'](segs, pieces, no_events(), CFG):
        if c['check'].startswith(INTERVAL_CHECK):
            got[int(float(c['check'].rsplit(' at ', 1)[1].split()[0]))] = c['status']
    return got


def test_segment_checks_accept_sub_eps_merged_remainder_from_build_segments(f, tr):
    # regression for run 014-001: n_segments absorbs a remainder < eps into the final segment, so that segment is R + remainder > R
    _, inv = tr
    eps = CFG['segmentation']['zero_remainder_eps_m']
    below, above = 500.0 + eps / 2, 500.0 + 10 * eps
    pieces = manual_pieces([(21, [(0, 0), (0, below)], False), (22, [(100, 0), (100, 1000.0 + eps / 2)], False), (23, [(200, 0), (200, above)], False)])
    segs = f['build_segments'](pieces, CFG, inv)
    S = segs[500]
    g21, g22, g23 = (S[S['oid'] == o].sort_values('seg_index') for o in (21, 22, 23))
    assert len(g21) == 1 and abs(g21['length_m'].iloc[0] - below) < 1e-6 and not g21['short_final'].iloc[0]
    assert len(g22) == 2 and abs(g22['length_m'].iloc[1] - (500.0 + eps / 2)) < 1e-6 and g22['end_m'].iloc[0] == 500.0
    assert len(g23) == 2 and abs(g23['length_m'].iloc[1] - 10 * eps) < 1e-6 and g23['short_final'].tolist() == [False, True]
    assert (g21['end_m'] - g21['start_m']).iloc[0] > 500 + 1e-9  # exactly what the pre-014b check rejected
    checks = f['segment_checks'](segs, pieces, no_events(), CFG)
    assert [c['check'] for c in checks if c['status'] != 'pass'] == []
    ev = next(c['evidence'] for c in checks if c['check'].startswith(INTERVAL_CHECK) and c['check'].endswith(' at ' + str(S['resolution_m'].iloc[0]) + ' m'))
    assert ev['finals_absorbing_sub_eps_remainder'] == 2 and ev['max_nonfinal_interval_deviation_m'] == 0.0


def _excess_final(S, eps):
    # final segment stretched past R + eps with length_m kept equal to its interval
    i = S.index[(S['oid'] == 21)][0]
    S.loc[i, 'end_m'] = S.loc[i, 'start_m'] + 500.0 + 1.5 * eps
    S.loc[i, 'length_m'] = 500.0 + 1.5 * eps


def _length_off_interval(S, eps):
    i = S.index[(S['oid'] == 21)][0]
    S.loc[i, 'length_m'] = S.loc[i, 'length_m'] + 0.01


def _nonfinal_interval_shifted(S, eps):
    # non-final interval no longer [0, R) even though length_m agrees with it
    i = S.index[(S['oid'] == 22) & (S['seg_index'] == 0)][0]
    S.loc[i, 'end_m'] = 499.0
    S.loc[i, 'length_m'] = 499.0


@pytest.mark.parametrize('corrupt', [_excess_final, _length_off_interval, _nonfinal_interval_shifted])
def test_segment_checks_still_fail_excess_length_or_corrupted_interval(f, tr, corrupt):
    _, inv = tr
    eps = CFG['segmentation']['zero_remainder_eps_m']
    pieces = manual_pieces([(21, [(0, 0), (0, 500.0 + eps / 2)], False), (22, [(100, 0), (100, 1000.0 + eps / 2)], False)])
    segs = f['build_segments'](pieces, CFG, inv)
    assert interval_status(f, segs, pieces)[500] == 'pass'
    bad = {R: S.copy() for R, S in segs.items()}
    corrupt(bad[500], eps)
    got = interval_status(f, bad, pieces)
    assert got[500] == 'fail' and all(v == 'pass' for R, v in got.items() if R != 500)


def test_exact_boundary_allocation_of_located_events(f):
    from shapely.geometry import LineString
    g = LineString([(0.0, 0.0), (0.0, 2048.0)])  # dyadic length: projections onto it are exact
    parts = pd.DataFrame({'part_uid': [0], 'geom_utm': [g]})
    pieces = pd.DataFrame({'piece_uid': [0], 'part_uid': [0], 'source_id': ['doh_highway'], 'oid': [7], 'part': [0], 'piece': [0], 'geom_utm': [g],
                           'len_utm_m': [2048.0]})
    xy = np.array([[10, 0], [10, 500], [10, 1000], [10, 1500], [10, 2000], [10, 2048], [-10, 499.5]], float)
    loc = f['locate_events'](xy, np.arange(len(xy)), np.zeros(len(xy)), parts, pieces, CFG)
    idx = {R: [int(s.rsplit(':', 1)[1]) for s in loc['segment_id_%dm' % R]] for R in (500, 1000, 2000)}
    assert idx == {500: [0, 1, 2, 3, 4, 4, 0], 1000: [0, 0, 1, 1, 2, 2, 0], 2000: [0, 0, 0, 0, 1, 1, 0]}
    assert loc['segment_id_500m'].iloc[1] == 'rsv1-%s:doh:7:p0:c0:r500:00001' % TAG
    assert (loc['segment_status'] == 'assigned').all()


def test_clipped_multipart_pieces_and_ids(f, tr):
    fwd, inv = tr
    geom = {'type': 'MultiLineString', 'coordinates': [[[100.25, 14.0], [100.26, 14.0]],
                                                       [[100.21, 14.0], [100.19, 14.01], [100.21, 14.02]]]}  # part 1 leaves and re-enters at lon 100.2
    feats = [{'source_id': 'doh_highway', 'oid': 900, 'geometry': geom, 'route_raw': '0001', 'props': {'objectid': 900, 'road_code': '0001'}}]
    features, parts, pieces = f['build_roads'](feats, diag_for(feats), CFG, fwd)
    assert len(parts) == 2 and int(features['n_pieces'].iloc[0]) == 3
    p0, p1 = pieces[pieces['part'] == 0], pieces[pieces['part'] == 1].sort_values('piece')
    assert len(p0) == 1 and not p0['clipped_at_start'].iloc[0] and not p0['clipped_at_end'].iloc[0]
    assert p1['piece'].tolist() == [0, 1]
    assert p1['clipped_at_start'].tolist() == [False, True] and p1['clipped_at_end'].tolist() == [True, False]
    assert p1['start_on_part_m'].iloc[0] < 1e-6 and p1['start_on_part_m'].iloc[1] > p1['end_on_part_m'].iloc[0]
    a, b = f['project_xy'](fwd, [[100.21, 14.0], [100.2, 14.005]])
    assert abs(p1['len_utm_m'].iloc[0] - float(np.hypot(*(a - b)))) < 0.01
    assert abs(p1['len_geod_m'].iloc[0] - f['geod']().inv(100.21, 14.0, 100.2, 14.005)[2]) < 1e-6
    segs = f['build_segments'](pieces, CFG, inv)
    for R, S in segs.items():
        assert S['segment_id'].is_unique
        assert {s.split(':')[3] + ':' + s.split(':')[4] for s in S['segment_id']} == {'p0:c0', 'p1:c0', 'p1:c1'}
        first = S[(S['part'] == 1) & (S['piece'] == 1)].sort_values('seg_index').iloc[0]
        assert bool(first['clipped_at_start'])


def test_piece_overlaps_flagged_not_merged(f):
    from shapely.geometry import LineString
    pieces = pd.DataFrame({'source_id': ['doh_highway', 'drr_rural', 'doh_highway', 'drr_rural'], 'oid': [1, 2, 3, 4],
                           'geom_utm': [LineString([(0, 0), (0, 300)]), LineString([(0, 200), (0, 500)]), LineString([(0, 0), (0, 300)]),
                                        LineString([(50, 0), (50, 100)])]})
    rows, flags, failed = f['piece_overlaps'](pieces, 1.0)
    assert failed == 0 and len(rows) == 3
    assert np.allclose(flags['overlap_m'].to_numpy(), [400, 200, 400, 0])
    assert flags['overlap_flag'].tolist() == [True, True, True, False] and flags['duplicate_flag'].tolist() == [True, False, True, False]


def test_candidate_search_is_radius_bounded(f):
    from shapely.geometry import LineString
    geoms = [LineString([(0, 0), (0, 1000)]), LineString([(500, 0), (500, 1000)])]
    pr = f['candidate_pairs'](np.array([[30.0, 500.0], [260.0, 500.0]]), geoms, 105.0)
    assert pr[['ev', 'part_uid']].values.tolist() == [[0, 0]] and abs(pr['dist_m'].iloc[0] - 30.0) < 1e-9


# ---------------------------------------------------------------- notebook output guard (before any write)
def guard_cfg(**outputs):
    cfg = copy.deepcopy(CFG)
    cfg['protected_paths'] = ['data/v2', 'reports/v2']
    cfg['outputs'] = dict(cfg['outputs'], **outputs)
    return cfg


def guard_backend(tmp_path):
    b = tmp_path / 'backend'
    for d in ('data/v2', 'reports/v2'):
        (b / d).mkdir(parents=True)
        (b / d / 'keep.csv').write_text('x', 'utf-8')
    return b


def test_notebook_output_guard(f, tmp_path):
    E, b, cfg = f['LinkageError'], guard_backend(tmp_path), guard_cfg()
    paths = f['output_paths'](b / 'rerun-linkage-a', cfg)
    assert f['check_outputs'](paths, b, cfg) and not paths['report_dir'].exists()
    with pytest.raises(E, match='overlaps protected'):
        f['check_outputs'](f['output_paths'](b / 'data' / 'v2', cfg), b, cfg)
    root = b / 'rerun-linkage-sym'
    (root / 'reports' / 'v3').mkdir(parents=True)
    os.symlink(b / 'reports' / 'v2', root / 'reports' / 'v3' / 'linkage_audit')
    with pytest.raises(E, match='overlaps protected'):
        f['check_outputs'](f['output_paths'](root, cfg), b, cfg)
    root = b / 'rerun-linkage-symdata'
    (root / 'data' / 'v3').mkdir(parents=True)
    os.symlink(b / 'data' / 'v2', root / 'data' / 'v3' / 'linkage_audit')
    with pytest.raises(E, match='overlaps protected'):
        f['check_outputs'](f['output_paths'](root, cfg), b, cfg)
    root = b / 'rerun-linkage-used'
    used = f['output_paths'](root, cfg)
    used['report_dir'].mkdir(parents=True)
    (used['report_dir'] / 'old.csv').write_text('x', 'utf-8')
    with pytest.raises(E, match='earlier output exists'):
        f['check_outputs'](used, b, cfg)
    with pytest.raises(E, match='contains|overlaps protected'):
        cfg2 = guard_cfg(report_dir='reports')  # ancestor of protected reports/v2
        f['check_outputs'](f['output_paths'](b, cfg2), b, cfg2)
    cfg3 = guard_cfg(data_dir=CFG['outputs']['report_dir'] + '/rows')
    with pytest.raises(E, match='report and data dirs overlap'):
        f['check_outputs'](f['output_paths'](b / 'rerun-linkage-b', cfg3), b, cfg3)


def test_report_dir_accepts_aggregates_only(f):
    assert f['check_report_file']('linkage_status_summary.csv', CFG)
    for bad in ('segments_500m.geojson', 'event_linkage_audit.csv.gz', 'rows.parquet'):
        with pytest.raises(f['LinkageError']):
            f['check_report_file'](bad, CFG)


# ---------------------------------------------------------------- runner guards (pure checks before any mkdir)
def runner_cfg(extra_protected=()):
    cfg = copy.deepcopy(CFG)
    cfg['protected_paths'] = ['data/v2', 'reports/v2'] + list(extra_protected)
    return cfg


def test_runner_accepts_fresh_root_without_creating_it(runner, tmp_path):
    b = guard_backend(tmp_path)
    out = b / 'rerun-linkage-014-001'
    assert runner.refusal(out, b, runner_cfg()) is None
    assert not out.exists()
    w = runner.planned_writes(out, CFG)
    assert not runner._inside(w['run log'], w['notebook report dir']) and not runner._inside(w['notebook report dir'], w['notebook data dir'])


def test_runner_refuses_reused_symlinked_misplaced_or_overlapping_roots(runner, tmp_path):
    b, cfg = guard_backend(tmp_path), runner_cfg()
    used = b / 'rerun-linkage-used'
    used.mkdir()
    assert 'already exists' in runner.refusal(used, b, cfg)
    link = b / 'rerun-linkage-link'
    os.symlink(b / 'data' / 'v2', link)
    assert 'symlink' in runner.refusal(link, b, cfg)
    dangling = b / 'rerun-linkage-dangling'
    os.symlink(tmp_path / 'nowhere', dangling)
    assert 'already exists' in runner.refusal(dangling, b, cfg)
    assert 'must start with' in runner.refusal(b / 'rerun-x', b, cfg)
    assert 'directly inside' in runner.refusal(tmp_path / 'rerun-linkage-outside', b, cfg)
    assert 'directly inside' in runner.refusal(b / 'data' / 'rerun-linkage-nested', b, cfg)
    msg = runner.refusal(b / 'rerun-linkage-p', b, runner_cfg(['rerun-linkage-p/notebooks']))
    assert msg and 'is inside protected' in msg
    msg = runner.refusal(b / 'rerun-linkage-q', b, runner_cfg(['rerun-linkage-q/data/v3/linkage_audit/keep']))
    assert msg and 'contains protected' in msg
    assert not any((b / n).exists() for n in ('rerun-x', 'rerun-linkage-p', 'rerun-linkage-q', 'data/rerun-linkage-nested'))


def test_runner_main_refuses_before_any_write(runner, tmp_path):
    with pytest.raises(SystemExit) as e:
        runner.main(['--output-dir', str(BACKEND / 'notebooks')])
    assert 'already exists' in str(e.value)
    out = tmp_path / 'rerun-linkage-outside'
    with pytest.raises(SystemExit):
        runner.main(['--output-dir', str(out)])
    assert not out.exists()
    with pytest.raises(SystemExit):
        runner.parse_args([])


def test_runner_env_is_explicit(runner, tmp_path):
    env = runner.build_env(tmp_path / 'rerun-linkage-env', BACKEND,
                           base={'ROADAWARE_V3_OUTPUT_ROOT': '/stale', 'ROADAWARE_ROAD_ONLINE': '1', 'PATH': '/bin'})
    assert env['ROADAWARE_V3_OUTPUT_ROOT'] == str((tmp_path / 'rerun-linkage-env').resolve())
    assert env['ROADAWARE_BACKEND_ROOT'] == str(BACKEND.resolve()) and env['PATH'] == '/bin' and env['MPLBACKEND'] == 'Agg'
    assert 'ROADAWARE_ROAD_ONLINE' not in env
