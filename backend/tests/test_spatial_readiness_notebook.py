"""Tests for V3 notebook 16 (spatial data readiness audit) and its runner. No network, no kernel.

The notebook's own '# FUNCTIONS' cells are executed, so the logic under test is the logic the audit runs. Fixture expectations are worked
out by hand. Integration tests at the bottom use the real accepted V2/raw files under backend/ and are skipped (with the reason) when those
gitignored files are absent. Run from the repository root:
    .venv/bin/python -m pytest backend/tests/test_spatial_readiness_notebook.py -q
"""
import importlib.util
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
NB16 = BACKEND / 'notebooks' / '16_spatial_data_readiness.ipynb'
RUNNER = BACKEND / 'scripts' / 'run_spatial_readiness.py'
CFG = json.loads((BACKEND / 'config' / 'spatial_readiness_v3.json').read_text('utf-8'))
ALIASES = json.loads((BACKEND / 'config' / 'data_pipeline.json').read_text('utf-8'))['schema_aliases']
BBOX = CFG['thailand_broad_bbox']
REAL = all((BACKEND / CFG['inputs'][k]['path']).is_file() for k in ('events_v2', 'row_lineage_v2')) and \
    (BACKEND / CFG['inputs']['raw_manifest']).is_file()


def code_cells(nb):
    d = json.loads(nb.read_text('utf-8'))
    return [''.join(c['source']) if isinstance(c['source'], list) else c['source'] for c in d['cells'] if c['cell_type'] == 'code']


@pytest.fixture(scope='module')
def f():
    ns = {}
    for i, s in enumerate(s for s in code_cells(NB16) if s.lstrip().startswith('# FUNCTIONS')):
        exec(compile(s, f'{NB16.stem}:FUNCTIONS[{i}]', 'exec'), ns)
    return ns


@pytest.fixture(scope='module')
def runner():
    spec = importlib.util.spec_from_file_location('run_spatial_readiness', RUNNER)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# ---------------------------------------------------------------- raw linkage fixture
FA, FB = 'accidents_2564_original.csv', 'accidents_2565_original.csv'


def raw_frame(codes, lats, lons):
    n = len(codes)
    return pd.DataFrame({'ACC_CODE': codes, 'LATITUDE': lats, 'LONGITUDE': lons, 'รหัสสายทาง': ['4164'] * n, 'KM': ['17.2'] * n,
                         'จังหวัด': ['พัทลุง'] * n})


def linkage_case():
    raw = {FA: raw_frame(['101', '102', '103'], [' 13.70 ', '14.0', '100.5'], ['100.50', '101.0', '13.7']),
           FB: raw_frame([' 201 ', '202'], ['15.1', '16.2'], ['101.1', '102.2'])}
    meta = {FA: {'be_year': 2564, 'ce_year': 2021, 'sha256': 'a' * 64}, FB: {'be_year': 2565, 'ce_year': 2022, 'sha256': 'b' * 64}}
    events = pd.DataFrame({'event_uid': ['2564:101', '2564:103', '2565:201', '2565:202'],
                           'event_date': ['2021-01-05', '2021-03-01', '2022-02-02', '2022-12-31'],
                           'time_block': ['00-06', '06-12', '', '18-24'], 'province_key': ['พัทลุง'] * 4})
    lineage = pd.DataFrame({'event_uid': ['2564:101', '2564:102', '2564:103', '2565:201', '2565:202'],
                            'v2_disposition': ['retained', 'quarantined', 'retained', 'retained', 'retained'],
                            'source_file': [FA, FA, FA, FB, FB], 'source_row': ['2', '3', '4', '2', '3']})
    return events, lineage, raw, meta


def test_linkage_maps_every_retained_uid_once_and_keeps_raw_strings(f):
    events, lineage, raw, meta = linkage_case()
    linked, headers = f['link_retained_events'](events, lineage, raw, meta, ALIASES)
    assert len(linked) == 4 and linked['event_uid'].is_unique
    r = linked.set_index('event_uid')
    assert r.loc['2564:103', 'source_row'] == 4 and r.loc['2564:103', 'raw_index'] == 2
    assert r.loc['2564:101', 'raw_latitude'] == ' 13.70 '  # untouched raw string, not stripped or parsed
    assert r.loc['2565:201', 'source_sha256'] == 'b' * 64 and r.loc['2565:201', 'ce_year'] == 2022
    assert headers['km'][FA] == 'KM' and headers['latitude'][FB] == 'LATITUDE'
    assert '2564:102' not in r.index  # quarantined rows are not linked as retained


def _acc_mismatch(e, l, r, m):
    r[FA].loc[0, 'ACC_CODE'] = '999'


def _off_by_one(e, l, r, m):
    l.loc[l.event_uid == '2564:101', 'source_row'] = '3'  # header-counted vs zero-based confusion lands on another record


def _row_out_of_bounds(e, l, r, m):
    l.loc[l.event_uid == '2564:103', 'source_row'] = '5'


def _row_header(e, l, r, m):
    l.loc[l.event_uid == '2564:101', 'source_row'] = '1'


def _row_non_integer(e, l, r, m):
    l.loc[l.event_uid == '2564:101', 'source_row'] = '2.5'


def _missing_lineage(e, l, r, m):
    l.drop(l.index[l.event_uid == '2565:202'], inplace=True)


def _missing_raw_row(e, l, r, m):
    r[FB] = r[FB].iloc[:1]  # raw file lost a record the lineage still points at


def _duplicate_lineage_uid(e, l, r, m):
    l.loc[len(l)] = ['2564:101', 'retained', FA, '2']


def _two_uids_one_record(e, l, r, m):
    l.loc[l.event_uid == '2564:103', 'source_row'] = '2'


def _duplicate_event(e, l, r, m):
    e.loc[len(e)] = e.iloc[0].tolist()


def _unverified_file(e, l, r, m):
    l.loc[l.source_file == FB, 'source_file'] = 'accidents_2566_original.csv'


def _missing_column(e, l, r, m):
    e.drop(columns='province_key', inplace=True)


@pytest.mark.parametrize('corrupt,match', [
    (_acc_mismatch, 'BE-year:ACC_CODE'), (_off_by_one, 'BE-year:ACC_CODE'), (_row_out_of_bounds, 'outside'), (_row_header, 'outside'),
    (_row_non_integer, 'non-integer'), (_missing_lineage, 'lack lineage'), (_missing_raw_row, 'outside'),
    (_duplicate_lineage_uid, 'duplicate retained'), (_two_uids_one_record, 'already-used raw record'), (_duplicate_event, 'duplicate event_uid'),
    (_unverified_file, 'not loaded and hash-verified'), (_missing_column, 'missing columns')])
def test_linkage_corruption_fails(f, corrupt, match):
    events, lineage, raw, meta = linkage_case()
    corrupt(events, lineage, raw, meta)
    with pytest.raises(f['SpatialReadinessError'], match=match):
        f['link_retained_events'](events, lineage, raw, meta, ALIASES)


def test_ambiguous_header_fails(f):
    with pytest.raises(f['SpatialReadinessError'], match='ambiguous'):
        f['resolve_alias'](['KM', 'ก.ม.'], ALIASES, 'km')
    assert f['resolve_alias'](['ก.ม.'], ALIASES, 'km') == 'ก.ม.'
    assert f['resolve_alias'](['X'], ALIASES, 'km') is None


def test_raw_disposition_frame_keeps_v2_dispositions(f):
    events, lineage, raw, meta = linkage_case()
    allraw, info = f['raw_disposition_frame'](raw, meta, lineage, ALIASES)
    assert len(allraw) == 5
    d = allraw.set_index(['source_file', 'source_row'])['v2_disposition']
    assert d[(FA, 3)] == 'quarantined' and d[(FA, 2)] == 'retained'
    assert info == {'lineage_rows_unparsed_source_row': 0, 'lineage_keys_without_raw_record': 0}
    lineage = lineage[lineage.event_uid != '2565:202']
    allraw, _ = f['raw_disposition_frame'](raw, meta, lineage, ALIASES)
    assert allraw.set_index(['source_file', 'source_row']).loc[(FB, 3), 'v2_disposition'] == 'absent_from_lineage'


# ---------------------------------------------------------------- coordinates / route / KM
def test_coordinates_flagged_without_silent_repair(f):
    df = pd.DataFrame({'raw_latitude': ['13.756331', '100.5', '', 'abc', '0', 'inf', '40.0', '13.7', '13.756331'],
                       'raw_longitude': ['100.501765', '13.7', '100.0', '100.0', '0', '100.0', '100.0', '100.5', '100.501765']})
    before = df.copy()
    out = f['audit_coordinates'](df, BBOX, round_dp=6, low_precision_max_decimals=3, repeated_min_events=2)
    assert out['coord_status'].tolist() == ['inside_broad_bbox_unverified', 'swap_candidate_unrepaired', 'missing', 'non_numeric',
                                            'zero_coordinate', 'non_finite', 'outside_broad_bbox', 'inside_broad_bbox_unverified',
                                            'inside_broad_bbox_unverified']
    pd.testing.assert_frame_equal(df, before)  # raw strings untouched
    assert out.loc[1, 'lat_value'] == 100.5 and out.loc[1, 'lon_value'] == 13.7  # swap candidate is NOT swapped
    assert len(out) == len(df)  # nothing dropped
    assert out['low_precision_flag'].tolist() == [False] * 7 + [True, False]
    assert out.loc[0, 'repeated_coord_flag'] and out.loc[8, 'repeated_coord_flag'] and out.loc[0, 'n_events_same_coord'] == 2
    assert not out.loc[2, 'repeated_coord_flag'] and out.loc[2, 'coord_key'] == ''


def test_route_km_formats_and_failures(f):
    df = pd.DataFrame({'raw_route_code': ['4164', 'นม.3052', '', '0012', '-'],
                       'raw_km': ['17.2', '17+200', '1,5', 'กม.5', '']})
    out = f['audit_route_km'](df, km_plausible_max=1500)
    assert out['route_format'].tolist() == ['digits_only', 'letters_and_digits', 'missing', 'digits_only', 'other_symbols']
    assert out['route_leading_zero_flag'].tolist() == [False, False, False, True, False]
    assert out['km_format'].tolist() == ['decimal_number', 'km_plus_m', 'comma_ambiguous', 'unparsed_text', 'missing']
    assert out['km_status'].tolist() == ['parsed_unvalidated', 'parsed_unvalidated', 'parse_failed', 'parse_failed', 'missing']
    assert out.loc[0, 'km_value'] == pytest.approx(17.2) and out.loc[1, 'km_value'] == pytest.approx(17.2)
    assert 'assumed metres' in out.loc[1, 'km_parse_rule'] and math.isnan(out.loc[2, 'km_value'])
    big = f['audit_route_km'](pd.DataFrame({'raw_route_code': ['1', '1'], 'raw_km': ['2000', '-3']}), km_plausible_max=1500)
    assert big['km_status'].tolist() == ['implausible_value', 'implausible_value']


def test_repeated_points_are_described_not_deduplicated(f):
    df = pd.DataFrame({'raw_latitude': ['14.1'] * 3 + ['15.2'], 'raw_longitude': ['101.1'] * 3 + ['102.2']})
    co = f['audit_coordinates'](df, BBOX, repeated_min_events=3)
    d = pd.concat([df, co], axis=1).assign(event_date=['2021-01-01', '2021-01-01', '2021-02-01', '2021-03-01'],
                                           route_key=['1', '2', '1', '1'], province_key='P', ce_year=2021)
    top, summary = f['repeated_coordinate_summary'](d, 10)
    assert len(d) == 4 and summary['events_at_repeated_keys'] == 3 and summary['keys_spanning_multiple_route_keys'] == 1
    assert 'NOT presumed duplicate' in top.loc[0, 'interpretation']


def test_distances_are_geodesic_not_degree_metres(f):
    one_deg_lat = f['haversine_m'](np.array([13.0]), np.array([100.0]), 14.0, 100.0)[0]
    assert one_deg_lat == pytest.approx(111195, rel=1e-3)
    one_deg_lon_at_60 = f['haversine_m'](np.array([60.0]), np.array([0.0]), 60.0, 1.0)[0]
    assert one_deg_lon_at_60 == pytest.approx(55597, rel=2e-3)  # about half: degree-to-metre scaling is not constant
    nn, sub = f['nearest_neighbour_m']([13.0, 13.0, 14.0], [100.0, 100.0, 100.0], max_points=10)
    assert nn.tolist()[:2] == [0.0, 0.0] and nn[2] == pytest.approx(111195, rel=1e-3) and not sub
    _, sub = f['nearest_neighbour_m'](np.linspace(13, 14, 50), np.full(50, 100.0), max_points=20)
    assert sub  # bounded memory: subsampled and flagged


# ---------------------------------------------------------------- geometry / readiness
def test_missing_geometry_is_pending_not_success(f, tmp_path):
    reg = f['registered_geometry_status'](tmp_path, CFG['geometry_sources'])
    assert set(reg['status']) == {'not_collected'}
    caps = f['capability_status'](reg, shapely_available=True)
    assert set(caps['status']) == {'PENDING_NOT_VERIFIED'} and len(caps) == len(f['CAPABILITIES'])
    scan = f['scan_geometry_files'](tmp_path, ['data/external_v3'], CFG['geometry_extensions'])
    assert scan['note'].tolist() == ['search root absent']


def test_geometry_without_pin_or_with_wrong_hash_is_not_usable(f, tmp_path):
    p = tmp_path / 'geo' / 'roads.geojson'
    p.parent.mkdir()
    p.write_text('{"type": "FeatureCollection", "features": []}', 'utf-8')
    src = {'id': 'x', 'role': 'road_network', 'path': 'geo/roads.geojson'}
    st = lambda s: f['registered_geometry_status'](tmp_path, [s])['status'].iloc[0]
    assert st(dict(src, sha256=None)) == 'present_unpinned_not_usable'
    assert st(dict(src, sha256='0' * 64)) == 'hash_mismatch_not_usable'
    good = dict(src, sha256=f['sha256_file'](p))
    assert st(good) == 'hash_verified_content_not_audited'
    caps = f['capability_status'](f['registered_geometry_status'](tmp_path, [good]), shapely_available=True)
    road = caps[caps.requires_role == 'road_network']['status']
    assert set(road) == {'PENDING_CONTENT_AUDIT'}  # even hash-verified geometry is never VERIFIED by this audit
    assert caps.set_index('capability').loc['point_in_province', 'status'] == 'PENDING_NOT_VERIFIED'
    scan = f['scan_geometry_files'](tmp_path, ['geo'], CFG['geometry_extensions'])
    assert scan['path'].tolist() == ['geo/roads.geojson'] and 'unregistered' in scan['note'].iloc[0]


def test_catalog_formats_separate_vector_from_wms(f):
    assert f['classify_format']('WMS') == 'image_or_map_service_not_vector'
    assert f['classify_format'](' shp ') == 'vector_geometry_candidate'
    assert f['classify_format']('XLSX') == 'tabular_no_verified_geometry'
    rows = f['catalog_resources']({'result': {'name': 'p', 'license_title': 'L', 'resources': [{'name': 'r', 'format': 'WMS', 'url': 'u'}]}}, 's', 'h')
    assert rows[0]['format_class'] == 'image_or_map_service_not_vector' and rows[0]['acceptance'] == 'candidate_metadata_only'
    assert f['catalog_resources']({'unexpected': 1}, 's', 'h') == []


def test_feature_readiness_rules(f):
    caps = pd.DataFrame({'capability': list(f['CAPABILITIES']), 'status': 'PENDING_NOT_VERIFIED'})
    m = f['feature_readiness'](CFG['feature_readiness'], caps)
    st = m.set_index('feature_group')['status']
    assert st['target_day_outcomes'] == 'blocked' and st['historical_location_lags'] == 'blocked'
    assert not m[m['requires_capability'].notna()]['status'].isin(['allow', 'allow_context_only']).any()
    sneaky = [{'feature_group': 'g', 'status': 'allow', 'requires_capability': 'road_snapping', 'reason': 'r'}]
    assert f['feature_readiness'](sneaky, caps)['status'].iloc[0] == 'pending'  # cannot be allowed without verified geometry
    with pytest.raises(f['SpatialReadinessError'], match='explanatory'):
        f['feature_readiness']([{'feature_group': 'g', 'status': 'allow', 'target_day_outcome': True}], caps)
    with pytest.raises(f['SpatialReadinessError'], match='latency'):
        f['feature_readiness']([{'feature_group': 'g', 'status': 'allow_context_only', 'historical_lag': True}], caps)
    with pytest.raises(f['SpatialReadinessError'], match='status'):
        f['feature_readiness']([{'feature_group': 'g', 'status': 'maybe'}], caps)


# ---------------------------------------------------------------- zero labels / budgets
def test_unknown_reporting_never_becomes_observed_zero(f):
    universe = pd.DataFrame({'space_key': ['s1', 's1', 's2', 's2', 's3'], 'time_key': ['d1', 'd2', 'd1', 'd2', 'd1'],
                             'observation_status': ['observed', 'observed', 'unknown_reporting', 'unknown_reporting', 'outside_network']})
    ev = pd.DataFrame({'space_key': ['s1', 's2', 's9'], 'time_key': ['d1', 'd2', 'd1']})
    u, info = f['labels_on_universe'](ev, universe, max_cells=100)
    y = u.set_index(['space_key', 'time_key'])
    assert y.loc[('s1', 'd1'), 'y_recorded_count'] == 1 and y.loc[('s1', 'd2'), 'y_recorded_count'] == 0
    assert math.isnan(y.loc[('s2', 'd1'), 'y_recorded_count']) and y.loc[('s2', 'd1'), 'label_status'] == 'unknown_reporting_not_zero'
    assert math.isnan(y.loc[('s2', 'd2'), 'y_recorded_count']) and y.loc[('s2', 'd2'), 'label_status'] == 'unknown_reporting_events_lower_bound'
    assert math.isnan(y.loc[('s3', 'd1'), 'y_recorded_count'])
    assert info == {'cells': 5, 'observed_zero_cells': 1, 'unknown_cells': 2, 'events_in_unknown_cells': 1, 'events_outside_universe': 1}
    with pytest.raises(f['SpatialReadinessError'], match='duplicate'):
        f['labels_on_universe'](ev, pd.concat([universe, universe.iloc[:1]]), max_cells=100)
    with pytest.raises(f['SpatialReadinessError'], match='observation_status'):
        f['labels_on_universe'](ev, universe.assign(observation_status='assumed_zero'), max_cells=100)
    with pytest.raises(f['SpatialReadinessError'], match='budget'):
        f['labels_on_universe'](ev, universe, max_cells=4)


def test_event_only_support_reports_no_zero_share(f):
    d = pd.DataFrame({'event_date': ['2021-01-04', '2021-01-04', '2021-01-10', '2021-01-11'], 'time_block': ['00-06', '00-06', '', '06-12'],
                      'province_key': ['A', 'A', 'A', 'B'], 'province_route_key': ['A|1', 'A|2', '', 'B|1']})
    r = f['occupied_support'](d, 'province_key', 'day', 'p x d')
    assert r['n_occupied_groups'] == 3 and r['zero_share'] is None and r['zero_label_status'].startswith('NOT_ESTABLISHED')
    assert f['occupied_support'](d, 'province_key', '7d', 'p x w')['n_occupied_groups'] == 2  # Mon 4th and Sun 10th share a week
    six = f['occupied_support'](d, 'province_key', '6h', 'p x 6h')
    assert six['n_events_without_space_or_time_key'] == 1 and six['n_occupied_groups'] == 2
    assert f['occupied_support'](d, 'province_route_key', 'day', 'r x d')['n_events_without_space_or_time_key'] == 1
    with pytest.raises(f['SpatialReadinessError'], match='ISO'):
        f['occupied_support'](d.assign(event_date='04/01/2021'), 'province_key', 'day', 'x')


def test_national_crossproduct_is_refused(f):
    assert f['guard_crossproduct'](77, 1095, CFG['max_universe_cells'], 'province x day') == 77 * 1095
    with pytest.raises(f['SpatialReadinessError'], match='budget'):
        f['guard_crossproduct'](5000, 1095 * 4, CFG['max_universe_cells'], 'route x 6h')


# ---------------------------------------------------------------- integrity helpers / notebook hygiene
def test_hash_helpers_detect_tampering(f, tmp_path):
    (tmp_path / 'd').mkdir()
    (tmp_path / 'd' / 'a.csv').write_text('x', 'utf-8')
    before = f['hash_tree'](tmp_path, ['d', 'missing.json'])
    assert before['missing.json'] is None and 'd/a.csv' in before
    (tmp_path / 'd' / 'a.csv').write_text('y', 'utf-8')
    assert f['changed_keys'](before, f['hash_tree'](tmp_path, ['d', 'missing.json'])) == ['d/a.csv']
    with pytest.raises(f['SpatialReadinessError'], match='does not match'):
        f['verify_file'](tmp_path / 'd' / 'a.csv', f['sha256_file'](tmp_path / 'd' / 'a.csv')[::-1], 'x')
    with pytest.raises(f['SpatialReadinessError'], match='not found'):
        f['verify_file'](tmp_path / 'nope.csv', '0' * 64, 'x')


def test_reports_refuse_row_level_columns_and_protected_overlap(f, tmp_path):
    with pytest.raises(f['SpatialReadinessError'], match='row-level'):
        f['assert_aggregate'](pd.DataFrame({'event_uid': ['1'], 'n': [1]}), 'x.csv')
    f['assert_aggregate'](pd.DataFrame({'province_key': ['A'], 'n': [1]}), 'x.csv')
    with pytest.raises(f['SpatialReadinessError'], match='overlaps'):
        f['check_output_roots']([tmp_path / 'data' / 'v2' / 'x'], [tmp_path / 'data' / 'v2'])
    f['check_output_roots']([tmp_path / 'data' / 'v3' / 'spatial_readiness'], [tmp_path / 'data' / 'v2'])


def test_notebook_has_no_network_fit_or_personal_paths():
    src = '\n'.join(code_cells(NB16))
    for banned in ('/Users/', 'urlopen', 'urllib', 'requests.', '.fit(', 'http.client'):
        assert banned not in src, banned
    assert any(c.lstrip().startswith('# PARAMETERS') for c in code_cells(NB16))
    assert sum(c.lstrip().startswith('# FUNCTIONS') for c in code_cells(NB16)) == 2


def test_config_pins_match_accepted_v2_evidence():
    prep = json.loads((BACKEND / CFG['inputs']['preparation_manifest']).read_text('utf-8'))
    outs = {d['path']: d['sha256'] for d in prep['data_outputs']}
    for k in ('events_v2', 'row_lineage_v2', 'panel_daily_v2'):
        assert outs[Path(CFG['inputs'][k]['path']).name] == CFG['inputs'][k]['sha256']
    for p in CFG['protected_paths']:
        assert not p.startswith(('reports/v3', 'data/v3'))


def test_existing_v2_files_unchanged_against_pre_task_snapshot():
    snap = REPO / '.ai-team' / 'references' / 'spatial012-before.json'
    if not snap.is_file():
        pytest.skip(f'{snap} (manager pre-task hash snapshot, local only) absent')
    before = json.loads(snap.read_text('utf-8'))
    keys = [k for k in before if k.startswith(('backend/notebooks/09', 'backend/notebooks/1', 'backend/config/', 'backend/reports/v2/',
                                                'backend/scripts/run_v2', 'backend/requirements-data.txt'))]
    assert keys
    import hashlib
    changed = [k for k in keys if (REPO / k).is_file() and hashlib.sha256((REPO / k).read_bytes()).hexdigest() != before[k]]
    missing = [k for k in keys if not (REPO / k).is_file()]
    assert not changed and not missing, (changed, missing)


# ---------------------------------------------------------------- runner
def test_runner_never_overwrites_and_forces_offline(runner, tmp_path):
    assert runner.preconditions(tmp_path) is None
    rep = tmp_path / 'reports' / 'v3' / 'spatial_readiness'
    rep.mkdir(parents=True)
    (rep / 'spatial_readiness_manifest.json').write_text('{}', 'utf-8')
    assert 'fresh root' in runner.preconditions(tmp_path)
    env = runner.build_env(tmp_path, base={'ROADAWARE_V3_OFFLINE': '0', 'ROADAWARE_V3_OUTPUT_ROOT': '/stale', 'PATH': '/bin'})
    assert env['ROADAWARE_V3_OFFLINE'] == '1' and env['ROADAWARE_V3_OUTPUT_ROOT'] == str(tmp_path.resolve()) and env['PATH'] == '/bin'


# ---------------------------------------------------------------- integration on the real accepted files (skipped when absent)
@pytest.mark.skipif(not REAL, reason='gitignored V2/raw data not present')
def test_real_linkage_reproduces_all_retained_events(f):
    inp = CFG['inputs']
    for k in ('events_v2', 'row_lineage_v2'):
        f['verify_file'](BACKEND / inp[k]['path'], inp[k]['sha256'], k)
    man = json.loads((BACKEND / inp['raw_manifest']).read_text('utf-8'))
    years = set(CFG['years']['train']) | set(CFG['years']['seen_diagnostic'])
    raw, meta = {}, {}
    for e in man['files']:
        if e['ce_year'] in years:
            f['verify_file'](BACKEND / e['path'], inp['raw_files'][e['file']], e['file'])
            raw[e['file']] = pd.read_csv(BACKEND / e['path'], dtype=str, keep_default_na=False, encoding=e['encoding'])
            meta[e['file']] = {'be_year': e['be_year'], 'ce_year': e['ce_year'], 'sha256': e['sha256']}
    ev = pd.read_csv(BACKEND / inp['events_v2']['path'], dtype=str, keep_default_na=False)
    lin = pd.read_csv(BACKEND / inp['row_lineage_v2']['path'], dtype=str, keep_default_na=False)
    linked, _ = f['link_retained_events'](ev, lin, raw, meta, ALIASES)
    assert len(linked) == CFG['expected_retained_events'] and linked['event_uid'].is_unique
    co = f['audit_coordinates'](linked, BBOX)
    assert len(co) == len(linked) and co['coord_status'].isin(f['COORD_STATUSES']).all()
