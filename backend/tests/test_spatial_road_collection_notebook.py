"""Tests for V3 notebook 17 (read-only road geometry collection) and its runner. No network, no kernel.

The notebook's own '# FUNCTIONS' cells are executed, so the logic under test is the logic the notebook runs. HTTP is replaced by a
deterministic fake ArcGIS FeatureServer that answers the same GET URLs the notebook builds; its bodies go through the notebook's own
bounded reader. Expected values are worked out by hand from the fixture. Run from the repository root:
    .venv/bin/python -m pytest backend/tests/test_spatial_road_collection_notebook.py -q
"""
import copy
import importlib.util
import io
import json
import re
from pathlib import Path
from urllib.parse import parse_qsl, unquote, urlsplit

import pytest

BACKEND = Path(__file__).resolve().parents[1]
NB17 = BACKEND / 'notebooks' / '17_spatial_road_collection.ipynb'
RUNNER = BACKEND / 'scripts' / 'run_spatial_road_collection.py'
CFG = json.loads((BACKEND / 'config' / 'spatial_road_sources_v3.json').read_text('utf-8'))
SHA = 'c' * 64


def code_cells(nb):
    d = json.loads(nb.read_text('utf-8'))
    return [''.join(c['source']) if isinstance(c['source'], list) else c['source'] for c in d['cells'] if c['cell_type'] == 'code']


@pytest.fixture(scope='module')
def f():
    ns = {}
    for i, s in enumerate(s for s in code_cells(NB17) if s.lstrip().startswith('# FUNCTIONS')):
        exec(compile(s, f'{NB17.stem}:FUNCTIONS[{i}]', 'exec'), ns)
    return ns


@pytest.fixture(scope='module')
def runner():
    spec = importlib.util.spec_from_file_location('run_spatial_road_collection', RUNNER)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# ---------------------------------------------------------------- fake ArcGIS FeatureServer
def make_feature(oid, oid_field='objectid'):
    # vertical 0.009 deg segment at ~14N: ~996 m geodesic; 'length' 1.0 (km) and km_end-km_start 1000 (m) by construction
    x = 100.5 + oid * 0.001
    return {'attributes': {oid_field: oid, 'road_code': '0001', 'km_start': 1000 * oid, 'km_end': 1000 * oid + 1000, 'length': 1.0},
            'geometry': {'paths': [[[x, 14.0], [x, 14.009]]]}}


def layer_meta(oid='objectid', layer_id=0, **over):
    d = {'id': layer_id, 'type': 'Feature Layer', 'name': 'Fake', 'geometryType': 'esriGeometryPolyline', 'objectIdField': oid,
         'maxRecordCount': 2000, 'capabilities': 'Query', 'supportedQueryFormats': 'JSON, geoJSON', 'currentVersion': 11.5,
         'spatialReference': {'wkid': 4326, 'latestWkid': 4326}, 'geometryProperties': {'units': 'esriDecimalDegrees'},
         'fields': [{'name': oid, 'type': 'esriFieldTypeOID'}, {'name': 'road_code', 'type': 'esriFieldTypeString'},
                    {'name': 'km_start', 'type': 'esriFieldTypeInteger'}, {'name': 'km_end', 'type': 'esriFieldTypeInteger'},
                    {'name': 'length', 'type': 'esriFieldTypeDouble'}]}
    d.update(over)
    return d


class FakeArcGIS:
    def __init__(self, f, n=45, oid='objectid', layer_id=0, **layer_over):
        self.f, self.oid = f, oid
        self.features = {i: make_feature(i, oid) for i in range(101, 101 + n)}
        self.layer = layer_meta(oid, layer_id, **layer_over)
        self.calls, self.count_calls, self.page_calls = [], 0, 0
        self.on_page = self.on_ids = self.on_count = None
        self.status_plan = []  # 'transient' or an HTTP status, consumed one per request before normal answers

    def __call__(self, url, timeout, max_bytes):
        self.calls.append(url)
        if self.status_plan:
            s = self.status_plan.pop(0)
            if s == 'transient':
                raise self.f['TransientHTTPError']('simulated timeout')
            return self.f['_bounded_read'](s, {}, io.BytesIO(b'{"error": {"code": 0}}'), max_bytes)
        p = urlsplit(url)
        q, path = dict(parse_qsl(p.query)), unquote(p.path)
        if path.endswith('/FeatureServer'):
            body = {'currentVersion': 11.5, 'layers': [{'id': self.layer['id'], 'name': 'Fake'}]}
        elif not path.endswith('/query'):
            body = self.layer
        elif q.get('returnCountOnly') == 'true':
            self.count_calls += 1
            body = {'count': len(self.features)}
            if self.on_count:
                self.on_count(self.count_calls, body)
        elif q.get('returnIdsOnly') == 'true':
            body = {'objectIdFieldName': self.oid, 'objectIds': sorted(self.features)}
            if self.on_ids:
                self.on_ids(body)
        else:
            self.page_calls += 1
            ids = [int(x) for x in q['objectIds'].split(',')]
            body = {'objectIdFieldName': self.oid, 'geometryType': 'esriGeometryPolyline', 'spatialReference': {'wkid': 4326, 'latestWkid': 4326},
                    'fields': [{'name': fl['name'], 'type': fl['type']} for fl in self.layer['fields']],
                    'features': [copy.deepcopy(self.features[i]) for i in ids if i in self.features]}
            if self.on_page:
                self.on_page(self.page_calls, body, self)
        return self.f['_bounded_read'](200, {'Content-Type': 'application/json'}, io.BytesIO(json.dumps(body).encode()), max_bytes)


def exat_feature(oid):
    # real-shaped EXAT_Road_OpenData record: identity is objectid_1 (esriFieldTypeOID); objectid is an ordinary integer that repeats
    ft = make_feature(oid, 'objectid_1')
    ft['attributes'] = {'objectid_1': oid, 'objectid': 7, 'route': 'R' + str(oid % 3), 'centerline': 'C' + str(oid), 'SHAPE__Length': 0.009}
    return ft


def exat_fake(f, n=45):
    fake = FakeArcGIS(f, n=n, oid='objectid_1', name='EXAT_Road_OpenData')
    fake.features = {i: exat_feature(i) for i in range(101, 101 + n)}
    fake.layer['fields'] = [{'name': 'objectid_1', 'type': 'esriFieldTypeOID'}, {'name': 'objectid', 'type': 'esriFieldTypeInteger'},
                            {'name': 'route', 'type': 'esriFieldTypeString'}, {'name': 'centerline', 'type': 'esriFieldTypeString'},
                            {'name': 'SHAPE__Length', 'type': 'esriFieldTypeDouble', 'virtual': True}]
    return fake


def source_cfg(sid, **budget):
    cfg = copy.deepcopy(CFG)
    cfg['sources'] = [s for s in cfg['sources'] if s['id'] == sid]
    cfg['budget'].update(budget)
    return cfg


def one_source_cfg(**budget):
    return source_cfg('doh_highway', **budget)


def three_fakes(f):
    return {'doh_highway': FakeArcGIS(f), 'drr_rural': FakeArcGIS(f, oid='OBJECTID', layer_id=2), 'exat_expressway': exat_fake(f, n=25)}


def router(cfg, fakes):
    # DOH and EXAT share the MOT host: route by FeatureServer path, never by host alone
    prefixes = [(urlsplit(s['service_url']).path, fakes[s['id']]) for s in cfg['sources']]

    def route(url, timeout, max_bytes):
        p = unquote(urlsplit(url).path)
        for prefix, fake in prefixes:
            if p == prefix or p.startswith(prefix + '/'):
                return fake(url, timeout, max_bytes)
        raise AssertionError('unrouted ' + url)
    return route


def pipeline(f, cfg, out, mode, transport=None, cache=None, expected=None, sleeps=None):
    """The notebook's cell sequence (collect -> derive_tables -> outputs -> acceptance) with injected transport; no logic of its own."""
    paths = f['output_paths'](out, cfg)
    f['check_fresh'](paths, mode == 'online')
    if mode == 'online':
        results, _ = f['run_online'](cfg, paths['raw_dir'], transport, sleep=(sleeps.append if sleeps is not None else lambda s: None))
        man, src = f['build_cache_manifest'](cfg, SHA, results), str(paths['raw_dir'])
    else:
        results, man = f['run_offline'](cfg, cache, expected)
        src = str(Path(cache) / 'raw')
    tables, rows, geo, deps = f['derive_tables'](cfg, results, {})
    f['write_tables_and_derivatives'](paths, tables, rows, geo)
    complete, status = f['write_acceptance'](paths, cfg, SHA, mode, results, man, src, deps)
    return paths, results, tables, rows, complete


def assert_incomplete(paths, results, code):
    v = results['doh_highway']
    assert v['status'] == 'incomplete' and code in {p['code'] for p in v['problems']}, v['problems']
    assert not (paths['report_dir'] / 'road_collection_manifest.json').exists()
    assert not (paths['raw_dir'] / 'cache_manifest.json').exists()
    st = json.loads((paths['report_dir'] / 'road_collection_status.json').read_text('utf-8'))
    assert st['status'] == 'incomplete' and st['sources']['doh_highway']['next_step']


# ---------------------------------------------------------------- complete collection and verified offline rerun
def test_complete_online_then_offline_rerun_reproduces_hashes_ids_and_lengths(f, tmp_path):
    cfg, fake = one_source_cfg(), FakeArcGIS(f, n=45)
    p1, r1, t1, rows1, ok1 = pipeline(f, cfg, tmp_path / 'a', 'online', fake)
    v = r1['doh_highway']
    assert ok1 and v['status'] == 'complete' and v['problems'] == []
    assert v['count_pre'] == 45 == len(v['features']) == v['count_post'] and v['n_pages_planned'] == 3
    assert [r['n_requested'] for r in v['page_rows']] == [20, 20, 5] and [r['status'] for r in v['page_rows']] == ['ok'] * 3
    reqs = v['requests']
    assert [r['kind'] for r in reqs] == ['service', 'layer', 'count_pre', 'ids_pre'] + ['geometry_page'] * 3 + ['count_post', 'ids_post']
    preds = {(r['params']['geometry'], r['params']['geometryType'], r['params']['spatialRel'], r['params']['inSR']) for r in reqs[2:]}
    assert preds == {('100.2,13.5,102.0,15.3', 'esriGeometryEnvelope', 'esriSpatialRelIntersects', '4326')}  # one predicate everywhere
    assert all(r['method'] == 'GET' and f['check_url'](r['url'], cfg['allowed_hosts']) and len(r['sha256']) == 64 for r in reqs)
    assert all(r['params']['outSR'] == '4326' and r['params']['outFields'] == '*' for r in reqs if r['kind'] == 'geometry_page')
    assert reqs[4]['requested_ids'] == list(range(101, 121))
    assert (p1['raw_dir'] / 'cache_manifest.json').is_file()
    exp = p1['report_dir'] / 'road_collection_manifest.json'
    assert exp.is_file()

    p2, r2, t2, rows2, ok2 = pipeline(f, cfg, tmp_path / 'b', 'offline', cache=p1['data_dir'], expected=exp)
    assert ok2 and not p2['raw_dir'].exists()  # offline never writes raw responses
    assert t1['page_reconciliation']['sha256'].tolist() == t2['page_reconciliation']['sha256'].tolist()
    assert rows1['oid'].tolist() == rows2['oid'].tolist() == list(range(101, 146))
    assert rows1['length_full_m'].tolist() == rows2['length_full_m'].tolist()
    m1, m2 = json.loads(exp.read_text('utf-8')), json.loads((p2['report_dir'] / 'road_collection_manifest.json').read_text('utf-8'))
    assert m1['raw_files'] == m2['raw_files'] and m2['mode'] == 'offline'

    fc = json.loads((p1['derived_dir'] / 'doh_highway_full.geojson').read_text('utf-8'))
    assert len(fc['features']) == 45 and fc['features'][0]['properties'] == fake.features[101]['attributes']  # original attributes untouched
    x, y = fc['features'][0]['geometry']['coordinates'][0]
    assert 100 < x < 102 and 13 < y < 16  # GeoJSON lon, lat order
    length = rows1.set_index('oid').loc[101, 'length_full_m']
    assert 990 < length < 1000  # 0.009 deg of latitude at 14N ~ 996 m geodesic (never 0.009 'metres')


def test_unit_hypotheses_are_hypotheses_and_degree_length_is_never_metres(f, tmp_path):
    cfg, fake = one_source_cfg(), FakeArcGIS(f, n=25)
    for ft in fake.features.values():
        ft['attributes']['Shape__Length'] = 0.009
    fake.layer['fields'].append({'name': 'Shape__Length', 'type': 'esriFieldTypeDouble', 'virtual': True})
    _, _, t, _, ok = pipeline(f, cfg, tmp_path, 'online', fake)
    u = t['unit_audit'].set_index('field')
    assert ok
    assert u.loc['length', 'hypothesis'] == 'consistent_with_km' and u.loc['length', 'status'] == 'hypothesis_pending_official_confirmation'
    assert u.loc['km_end - km_start', 'hypothesis'] == 'consistent_with_m'
    assert u.loc['Shape__Length', 'status'] == 'not_metres_never_used_as_length'
    r = t['readiness']
    assert set(r.loc[r['check'].str.startswith('units:'), 'status']) == {'pending'}


def test_unit_hypothesis_unresolved_when_no_scale_fits(f):
    h = f['unit_hypothesis']([0.5, 0.4, 0.6], [1000.0, 1000.0, 1000.0], {'m': 1.0, 'km': 1000.0}, [0.8, 1.25], 0.8)
    assert h['hypothesis'] == 'unresolved' and h['status'] == 'pending_unresolved' and h['n_compared'] == 3


# ---------------------------------------------------------------- paging / ID failures never complete
def test_truncated_page_is_incomplete_and_keeps_raw_evidence(f, tmp_path):
    fake = FakeArcGIS(f)

    def hook(n, body, fk):
        if n == 2:
            body['exceededTransferLimit'] = True
            body['features'] = body['features'][:10]
    fake.on_page = hook
    paths, res, t, _, ok = pipeline(f, one_source_cfg(), tmp_path, 'online', fake)
    assert not ok
    assert_incomplete(paths, res, 'truncated_page')
    assert 'missing_ids' in {p['code'] for p in res['doh_highway']['problems']}
    assert (paths['raw_dir'] / 'doh_highway' / 'pages' / 'page_00002.json').is_file()
    assert json.loads((paths['raw_dir'] / 'collection_log_incomplete.json').read_text('utf-8'))['status'] == 'incomplete'
    assert t['page_reconciliation'].set_index('page').loc[2, 'n_missing'] == 10


@pytest.mark.parametrize('case,code', [('silent_drop', 'missing_ids'), ('duplicate', 'duplicate_oid'), ('unexpected', 'unexpected_ids'),
                                       ('no_oid', 'feature_without_oid'), ('crs', 'unsupported_crs'), ('not_json', 'page_unreadable')])
def test_page_level_defects_fail(f, tmp_path, case, code):
    fake = FakeArcGIS(f)

    def hook(n, body, fk):
        if case == 'silent_drop' and n == 3:
            body['features'].pop()
        elif case == 'duplicate' and n == 2:
            body['features'][0] = copy.deepcopy(fk.features[101])
        elif case == 'unexpected' and n == 1:
            body['features'].append(make_feature(999))
        elif case == 'no_oid' and n == 1:
            del body['features'][0]['attributes']['objectid']
        elif case == 'crs' and n == 1:
            body['spatialReference'] = {'wkid': 32647}
        elif case == 'not_json' and n == 2:
            body.clear()
            body['features'] = 'not a list'
    fake.on_page = hook
    paths, res, _, _, ok = pipeline(f, one_source_cfg(), tmp_path, 'online', fake)
    assert not ok
    assert_incomplete(paths, res, code)


def test_truncated_id_list_or_count_mismatch_stops_before_geometry(f, tmp_path):
    fake = FakeArcGIS(f)
    fake.on_ids = lambda body: body.update(exceededTransferLimit=True)
    paths, res, _, _, ok = pipeline(f, one_source_cfg(), tmp_path / 'a', 'online', fake)
    assert not ok and fake.page_calls == 0
    assert_incomplete(paths, res, 'collection_failed')

    fake = FakeArcGIS(f)
    fake.on_count = lambda n, body: body.update(count=46) if n == 1 else None
    paths, res, _, _, ok = pipeline(f, one_source_cfg(), tmp_path / 'b', 'online', fake)
    assert not ok and fake.page_calls == 0
    assert_incomplete(paths, res, 'count_id_mismatch')


def test_inventory_change_between_pre_and_post_queries_fails(f, tmp_path):
    fake = FakeArcGIS(f)

    def hook(n, body, fk):
        if n == 3:
            fk.features[500] = make_feature(500)  # an edit lands after the last page
    fake.on_page = hook
    paths, res, t, _, ok = pipeline(f, one_source_cfg(), tmp_path, 'online', fake)
    assert not ok and res['doh_highway']['count_post'] == 46
    assert_incomplete(paths, res, 'inventory_changed')
    assert not bool(t['source_summary'].loc[0, 'inventory_stable'])


@pytest.mark.parametrize('over,needle', [({'geometryType': 'esriGeometryPolygon'}, 'expected Feature Layer'),
                                         ({'maxRecordCount': 10}, 'exceeds maxRecordCount'),
                                         ({'capabilities': 'Map'}, 'Query capability'),
                                         ({'supportedQueryFormats': 'AMF'}, 'f=json')])
def test_unusable_layer_metadata_fails_fast_without_queries(f, tmp_path, over, needle):
    fake = FakeArcGIS(f, **over)
    paths, res, _, _, ok = pipeline(f, one_source_cfg(), tmp_path, 'online', fake)
    assert not ok and fake.count_calls == 0 and fake.page_calls == 0
    assert_incomplete(paths, res, 'collection_failed')
    assert needle in res['doh_highway']['problems'][0]['message']


# ---------------------------------------------------------------- budgets, retries, endpoint failure
def _page_sizes(f, tmp_path):
    paths, res, t, _, ok = pipeline(f, one_source_cfg(), tmp_path / 'probe', 'online', FakeArcGIS(f))
    assert ok
    return t['page_reconciliation']['bytes'].tolist()


def test_per_response_cap_rejects_whole_page(f, tmp_path):
    sizes = _page_sizes(f, tmp_path)
    paths, res, _, _, ok = pipeline(f, one_source_cfg(max_response_bytes=sizes[0] - 1), tmp_path / 'x', 'online', FakeArcGIS(f))
    assert not ok
    assert_incomplete(paths, res, 'collection_failed')
    assert 'BudgetExceeded' in res['doh_highway']['problems'][0]['message']
    assert not (paths['raw_dir'] / 'doh_highway' / 'pages').exists()  # nothing truncated and stored
    assert 'budget' in res['doh_highway']['next_step']


def test_total_geometry_budget_stops_collection(f, tmp_path):
    sizes = _page_sizes(f, tmp_path)
    cfg = one_source_cfg(max_total_geometry_bytes=sizes[0] + sizes[1] // 2, max_response_bytes=sizes[0] + sizes[1] // 2)
    paths, res, _, _, ok = pipeline(f, cfg, tmp_path / 'x', 'online', FakeArcGIS(f))
    assert not ok and res['doh_highway']['n_pages_present'] == 1
    assert_incomplete(paths, res, 'collection_failed')


def test_max_features_budget_stops_before_geometry(f, tmp_path):
    fake = FakeArcGIS(f)
    paths, res, _, _, ok = pipeline(f, one_source_cfg(max_features=10), tmp_path, 'online', fake)
    assert not ok and fake.page_calls == 0
    assert_incomplete(paths, res, 'budget_features')


def test_finite_retries_then_success_and_exhaustion(f, tmp_path):
    fake, sleeps = FakeArcGIS(f), []
    fake.status_plan = ['transient', 503]
    _, res, _, _, ok = pipeline(f, one_source_cfg(max_retries=2, retry_backoff_seconds=3), tmp_path / 'a', 'online', fake, sleeps=sleeps)
    assert ok and sleeps == [3.0, 6.0]
    assert [a.get('http_status') for a in res['doh_highway']['requests'][0]['attempts']] == [None, 503, 200]

    fake = FakeArcGIS(f)
    fake.status_plan = ['transient'] * 3
    paths, res, _, _, ok = pipeline(f, one_source_cfg(max_retries=2), tmp_path / 'b', 'online', fake)
    assert not ok and len(fake.calls) == 3
    assert_incomplete(paths, res, 'collection_failed')
    assert 'after 3 attempts' in res['doh_highway']['problems'][0]['message']


def test_http_404_is_not_retried(f, tmp_path):
    fake = FakeArcGIS(f)
    fake.status_plan = [404]
    paths, res, _, _, ok = pipeline(f, one_source_cfg(), tmp_path, 'online', fake)
    assert not ok and len(fake.calls) == 1
    assert_incomplete(paths, res, 'collection_failed')


@pytest.mark.parametrize('down', ['doh_highway', 'drr_rural', 'exat_expressway'])
def test_one_endpoint_down_means_no_completed_manifest_and_no_silent_fallback(f, tmp_path, down):
    cfg, fakes = copy.deepcopy(CFG), three_fakes(f)
    fakes[down].status_plan = ['transient'] * 100
    paths, res, _, _, ok = pipeline(f, cfg, tmp_path, 'online', router(cfg, fakes))
    assert not ok and res[down]['status'] == 'incomplete'
    assert all(res[s]['status'] == 'complete' for s in res if s != down) and len(res) == len(cfg['sources'])
    want = urlsplit(next(s['service_url'] for s in cfg['sources'] if s['id'] == down)).path
    assert fakes[down].calls and all(unquote(urlsplit(u).path).startswith(want) for u in fakes[down].calls)
    st = json.loads((paths['report_dir'] / 'road_collection_status.json').read_text('utf-8'))
    assert st['status'] == 'incomplete' and 'No OSM' in st['sources'][down]['next_step']
    assert not (paths['report_dir'] / 'road_collection_manifest.json').exists()
    assert not (paths['raw_dir'] / 'cache_manifest.json').exists()


# ---------------------------------------------------------------- EXAT (objectid_1 identity) and the three-source snapshot
def test_exat_identity_is_objectid_1_through_paging_and_offline_replay(f, tmp_path):
    cfg, fake = source_cfg('exat_expressway'), exat_fake(f, n=45)
    p1, r1, t1, rows1, ok1 = pipeline(f, cfg, tmp_path / 'a', 'online', fake)
    v = r1['exat_expressway']
    assert ok1 and v['status'] == 'complete' and v['problems'] == [] and v['layer_facts']['object_id_field'] == 'objectid_1'
    assert [r['n_requested'] for r in v['page_rows']] == [20, 20, 5]
    pages = [r for r in v['requests'] if r['kind'] == 'geometry_page']
    assert [r['requested_ids'] for r in pages] == [list(range(101, 121)), list(range(121, 141)), list(range(141, 146))]
    assert rows1['oid'].tolist() == list(range(101, 146))  # objectid (constant 7) would have collapsed to duplicates
    u = t1['unit_audit']
    assert u['field'].tolist() == ['SHAPE__Length'] and u['status'].tolist() == ['not_metres_never_used_as_length']  # no km/length roles
    fc = json.loads((p1['derived_dir'] / 'exat_expressway_full.geojson').read_text('utf-8'))
    assert [ft['properties'] for ft in fc['features']] == [fake.features[i]['attributes'] for i in range(101, 146)]
    exp = p1['report_dir'] / 'road_collection_manifest.json'

    p2, r2, t2, rows2, ok2 = pipeline(f, cfg, tmp_path / 'b', 'offline', cache=p1['data_dir'], expected=exp)
    assert ok2 and r2['exat_expressway']['layer_facts']['object_id_field'] == 'objectid_1'
    assert rows2['oid'].tolist() == rows1['oid'].tolist() and rows2['length_full_m'].tolist() == rows1['length_full_m'].tolist()
    assert t2['page_reconciliation']['sha256'].tolist() == t1['page_reconciliation']['sha256'].tolist()
    m1, m2 = json.loads(exp.read_text('utf-8')), json.loads((p2['report_dir'] / 'road_collection_manifest.json').read_text('utf-8'))
    assert m1['raw_files'] == m2['raw_files']


@pytest.mark.parametrize('case,code,needle', [('ids_field', 'collection_failed', 'objectIdFieldName'),
                                              ('two_oid_fields', 'collection_failed', 'single esriFieldTypeOID'),
                                              ('page_lacks_objectid_1', 'feature_without_oid', 'objectid_1')])
def test_exat_never_falls_back_to_the_ordinary_objectid_field(f, tmp_path, case, code, needle):
    fake = exat_fake(f)
    if case == 'ids_field':
        fake.on_ids = lambda body: body.update(objectIdFieldName='objectid')
    elif case == 'two_oid_fields':
        fake.layer['fields'][1]['type'] = 'esriFieldTypeOID'
    else:
        fake.on_page = lambda n, body, fk: body['features'][0]['attributes'].pop('objectid_1') if n == 1 else None
    paths, res, _, _, ok = pipeline(f, source_cfg('exat_expressway'), tmp_path, 'online', fake)
    v = res['exat_expressway']
    assert not ok and v['status'] == 'incomplete'
    assert any(p['code'] == code and needle in p['message'] for p in v['problems']), v['problems']
    assert not (paths['report_dir'] / 'road_collection_manifest.json').exists()
    if case != 'page_lacks_objectid_1':
        assert fake.page_calls == 0


def test_three_source_snapshot_complete_and_offline_replay_pinned(f, tmp_path):
    cfg, fakes = copy.deepcopy(CFG), three_fakes(f)
    p1, r1, t1, rows1, ok1 = pipeline(f, cfg, tmp_path / 'a', 'online', router(cfg, fakes))
    assert ok1 and set(r1) == {s['id'] for s in cfg['sources']} and all(v['status'] == 'complete' for v in r1.values())
    assert all(fk.page_calls > 0 for fk in fakes.values())
    exp = p1['report_dir'] / 'road_collection_manifest.json'
    m1 = json.loads(exp.read_text('utf-8'))
    assert set(m1['sources']) == set(r1) and m1['version'] == cfg['version']
    assert {sid: s['features'] for sid, s in m1['sources'].items()} == {sid: len(fk.features) for sid, fk in fakes.items()}
    p2, r2, t2, rows2, ok2 = pipeline(f, cfg, tmp_path / 'b', 'offline', cache=p1['data_dir'], expected=exp)
    assert ok2 and json.loads((p2['report_dir'] / 'road_collection_manifest.json').read_text('utf-8'))['raw_files'] == m1['raw_files']
    assert rows2[['source_id', 'oid', 'length_full_m']].values.tolist() == rows1[['source_id', 'oid', 'length_full_m']].values.tolist()


def test_two_source_cache_is_never_replayed_as_a_three_source_snapshot(f, tmp_path):
    two = copy.deepcopy(CFG)
    two['sources'] = [s for s in two['sources'] if s['id'] != 'exat_expressway']
    fakes = three_fakes(f)
    paths, _, _, _, ok = pipeline(f, two, tmp_path / 'two', 'online', router(two, fakes))
    assert ok
    with pytest.raises(f['RoadCollectionError'], match='differs from the config'):
        f['run_offline'](copy.deepcopy(CFG), paths['data_dir'])


# ---------------------------------------------------------------- malformed geometry: retained, flagged, reconciled
def test_malformed_geometry_is_kept_flagged_and_counted_not_dropped(f, tmp_path):
    fake = FakeArcGIS(f)
    fake.features[101]['geometry'] = {'paths': [[[float('nan'), 14.0], [100.6, 14.01]]]}
    fake.features[102]['geometry'] = {'paths': [[[100.6, 14.0]]]}
    fake.features[103]['geometry'] = None
    fake.features[104]['geometry'] = {'paths': [[[14.0, 100.6], [14.01, 100.6]]]}  # lat/lon swapped
    fake.features[105]['geometry'] = {'paths': [[[100.6, 14.0, 5.0], [100.6, 14.01, 5.0]]]}
    fake.features[106]['geometry'] = {'paths': [[[101.9, 14.0], [102.1, 14.0]]]}  # crosses the envelope edge
    paths, res, t, rows, ok = pipeline(f, one_source_cfg(), tmp_path, 'online', fake)
    assert ok  # collection is complete: every requested feature came back; quality is reported, not repaired
    r = rows.set_index('oid')
    assert len(rows) == 45 and bool(r.loc[101, 'nonfinite_coord']) and bool(r.loc[102, 'empty_or_short_part']) and bool(r.loc[103, 'geom_missing'])
    assert bool(r.loc[104, 'latlon_swap_suspect']) and bool(r.loc[104, 'clip_empty']) and bool(r.loc[105, 'extra_dims'])
    assert not any(bool(r.loc[o, 'geojson_ok']) for o in (101, 102, 103))
    half = r.loc[106, 'length_clipped_m'] / r.loc[106, 'length_full_m']
    assert 0.49 < half < 0.51
    q = t['geometry_quality'].iloc[0]
    assert q['features'] == 45 and q['geojson_derivative_ok'] == 42 and q['latlon_swap_suspect'] == 1
    assert b'NaN' in (paths['raw_dir'] / 'doh_highway' / 'pages' / 'page_00001.json').read_bytes()  # raw untouched
    fc = json.loads((paths['derived_dir'] / 'doh_highway_full.geojson').read_text('utf-8'))
    assert len(fc['features']) == 42
    ready = t['readiness'].set_index('check')
    assert ready.loc['geometry_nonempty_finite_lines', 'status'] == 'review' and ready.loc['lonlat_order_and_bounds', 'status'] == 'review'


# ---------------------------------------------------------------- offline cache: tampering/missing/changed never auto-trusted
@pytest.fixture()
def cache(f, tmp_path):
    cfg = one_source_cfg()
    paths, _, _, _, ok = pipeline(f, cfg, tmp_path / 'online', 'online', FakeArcGIS(f))
    assert ok
    return cfg, paths


def _man(paths):
    return json.loads((paths['raw_dir'] / 'cache_manifest.json').read_text('utf-8'))


def _save_man(paths, m):
    (paths['raw_dir'] / 'cache_manifest.json').write_text(json.dumps(m), 'utf-8')


def test_offline_without_cache_fails_clearly(f, tmp_path):
    with pytest.raises(f['RoadCollectionError'], match='--online'):
        f['run_offline'](one_source_cfg(), tmp_path / 'nothing')


@pytest.mark.parametrize('case,needle', [('corrupt_page', 'hash mismatch'), ('missing_page_file', 'cache file missing'),
                                         ('unlisted_file', 'does not list'), ('corrupt_manifest', 'not valid JSON'),
                                         ('status', 'not complete'), ('envelope', 'different envelope'), ('budget', 'different budget'),
                                         ('source', 'different service/layer')])
def test_offline_tampered_or_changed_cache_raises(f, cache, case, needle):
    cfg, paths = cache
    cfg = copy.deepcopy(cfg)
    pages = paths['raw_dir'] / 'doh_highway' / 'pages'
    if case == 'corrupt_page':
        b = (pages / 'page_00002.json').read_bytes()
        (pages / 'page_00002.json').write_bytes(b[:-2] + b' }')
    elif case == 'missing_page_file':
        (pages / 'page_00003.json').unlink()
    elif case == 'unlisted_file':
        (pages / 'page_99999.json').write_bytes(b'{}')
    elif case == 'corrupt_manifest':
        (paths['raw_dir'] / 'cache_manifest.json').write_text('{oops', 'utf-8')
    elif case == 'status':
        m = _man(paths)
        m['status'] = 'incomplete'
        _save_man(paths, m)
    elif case == 'envelope':
        cfg['preregistration']['envelope_epsg4326'] = [100.0, 13.5, 102.0, 15.3]
    elif case == 'budget':
        cfg['budget']['max_total_geometry_bytes'] = 1 << 29
    elif case == 'source':
        cfg['sources'][0]['service_url'] = 'https://giportal.mot.go.th/arcgis/rest/services/Hosted/other/FeatureServer'
    with pytest.raises(f['RoadCollectionError'], match=needle):
        f['run_offline'](cfg, paths['data_dir'])


def test_offline_consistently_removed_page_is_incomplete(f, cache, tmp_path):
    cfg, paths = cache
    m = _man(paths)
    m['sources']['doh_highway']['files'] = [x for x in m['sources']['doh_highway']['files'] if x.get('page') != 3]
    _save_man(paths, m)
    (paths['raw_dir'] / 'doh_highway' / 'pages' / 'page_00003.json').unlink()
    p2, res, _, _, ok = pipeline(f, cfg, tmp_path / 'off', 'offline', cache=paths['data_dir'])
    assert not ok
    assert_incomplete(p2, res, 'missing_or_extra_pages')


def test_offline_rehashed_tampered_content_is_still_revalidated(f, cache, tmp_path):
    cfg, paths = cache
    page = paths['raw_dir'] / 'doh_highway' / 'pages' / 'page_00002.json'
    d = json.loads(page.read_text('utf-8'))
    d['features'].pop()
    page.write_bytes(json.dumps(d).encode())
    m = _man(paths)
    for x in m['sources']['doh_highway']['files']:
        if x.get('page') == 2:
            x['sha256'] = f['sha256_file'](page)
    _save_man(paths, m)
    p2, res, _, _, ok = pipeline(f, cfg, tmp_path / 'off', 'offline', cache=paths['data_dir'])
    assert not ok
    assert_incomplete(p2, res, 'missing_ids')
    exp = paths['report_dir'] / 'road_collection_manifest.json'  # the accepted manifest still pins the original hashes
    with pytest.raises(f['RoadCollectionError'], match='expected accepted manifest'):
        f['run_offline'](cfg, paths['data_dir'], exp)


def test_fresh_output_root_required(f, cache):
    cfg, paths = cache
    with pytest.raises(f['RoadCollectionError'], match='NEW output root'):
        f['check_fresh'](paths, True)


# ---------------------------------------------------------------- read-only URL allow-list, bounded reads, dependencies
def test_configured_endpoints_are_encoded_and_allowed(f):
    assert f['validate_config'](CFG)
    u = f['service_endpoint'](CFG['sources'][0]['service_url'], 0, query=True)
    assert u.startswith('https://giportal.mot.go.th/arcgis/rest/services/Hosted/%E0%B9%80') and u.endswith('/FeatureServer/0/query')  # 'เ' U+0E40
    assert f['check_url'](f['with_query'](u, f['count_params'](CFG['preregistration']['envelope_epsg4326'], 'esriSpatialRelIntersects')),
                          CFG['allowed_hosts'])


@pytest.mark.parametrize('url', [
    'http://gis.drr.go.th/arcgis/rest/services/DRR_Feature/FeatureServer/2/query?f=json',
    'https://example.com/arcgis/rest/services/DRR_Feature/FeatureServer/2/query?f=json',
    'https://gis.drr.go.th/arcgis/rest/services/DRR_Feature/FeatureServer/2/applyEdits?f=json',
    'https://gis.drr.go.th/arcgis/rest/services/DRR_Feature/FeatureServer/2/addFeatures',
    'https://gis.drr.go.th/arcgis/rest/services/DRR_Feature/FeatureServer/2/query?f=json&token=abc',
    'https://gis.drr.go.th:8443/arcgis/rest/services/DRR_Feature/FeatureServer/2/query?f=json',
    'https://user:pw@gis.drr.go.th/arcgis/rest/services/DRR_Feature/FeatureServer/2/query?f=json',
    'https://gis.drr.go.th/arcgis/rest/services/DRR_Feature/MapServer/2/query?f=json',
    'https://gis.drr.go.th/arcgis/rest/services/DRR_Feature/FeatureServer/2/query/extra?f=json',
    'https://gis.drr.go.th/arcgis/admin/services/DRR_Feature/FeatureServer/2/query?f=json',
])
def test_url_guard_refuses_non_read_only_or_foreign_urls(f, url):
    with pytest.raises(f['RoadCollectionError']):
        f['check_url'](url, CFG['allowed_hosts'])


def test_redirects_refused_and_reads_bounded(f):
    with pytest.raises(f['RoadCollectionError'], match='redirect'):
        f['_NoRedirect']().redirect_request(None, None, 302, 'Found', {}, 'https://example.com/')
    with pytest.raises(f['BudgetExceeded'], match='Content-Length'):
        f['_bounded_read'](200, {'Content-Length': '11'}, io.BytesIO(b'x' * 11), 10)
    with pytest.raises(f['BudgetExceeded'], match='not truncated'):
        f['_bounded_read'](200, {}, io.BytesIO(b'x' * 11), 10)
    assert f['_bounded_read'](200, {}, io.BytesIO(b'x' * 10), 10)[2] == b'x' * 10


def test_missing_dependency_fails_with_pin_and_installs_nothing(f):
    with pytest.raises(f['RoadCollectionError'], match=re.escape('shapely>=2.0,<3')):
        f['require_modules'](['pandas', 'shapely'], CFG['dependency_pins'], finder=lambda n: None if n == 'shapely' else object())
    assert f['module_version']('pyproj', finder=lambda n: None) is None


def test_notebook_has_no_hardcoded_counts_no_tls_bypass_no_writes(f):
    code = '\n'.join(code_cells(NB17))
    for n in ('3044', '3700', '599', '547'):
        assert not re.search(r'\b' + n + r'\b', code), n  # live observations are context, never expected counts
    for bad in ('CERT_NONE', '_create_unverified_context', 'check_hostname = False', "method='POST'", 'openstreetmap', 'overpass'):
        assert bad not in code


# ---------------------------------------------------------------- geodesic maths (hand-known WGS84 values)
def test_vincenty_matches_known_wgs84_distances(f):
    v = f['vincenty_m']
    assert abs(v(0, 0, 1, 0) - 111319.491) < 0.01  # equatorial degree = a * pi / 180
    assert abs(v(0, 0, 0, 1) - 110574.389) < 0.05  # first meridian degree
    assert 55790 < v(0, 60, 1, 60) < 55801  # parallel arc at 60N is ~55800 m; the geodesic is marginally shorter
    assert f['line_length_m']([[(0, 0), (1, 0)], [(0, 0), (0, 1)]]) == pytest.approx(111319.491 + 110574.389, abs=0.1)


def test_batches_are_deterministic_and_bounded(f):
    assert f['plan_batches']([5, 3, 9, 1, 7], 2) == [[1, 3], [5, 7], [9]]
    with pytest.raises(f['RoadCollectionError']):
        f['plan_batches']([1], 0)


# ---------------------------------------------------------------- config, discovery context, protected paths
def test_config_preregistration_and_budget(f):
    pr, b = CFG['preregistration'], CFG['budget']
    assert pr['envelope_epsg4326'] == [100.2, 13.5, 102.0, 15.3] and pr['spatial_rel'] == 'esriSpatialRelIntersects'
    assert b['max_total_geometry_bytes'] == 256 * 1024 * 1024 and b['batch_size'] == 20 and b['max_retries'] <= 3
    assert not any('count' in k for s in CFG['sources'] for k in s) and 'expected_count' not in json.dumps(CFG)  # no fixed counts
    bad = copy.deepcopy(CFG)
    bad['sources'][0]['service_url'] = 'https://example.com/arcgis/rest/services/x/FeatureServer'
    with pytest.raises(f['RoadCollectionError']):
        f['validate_config'](bad)


def test_discovery_context_reverifies_manager_hashes_as_context_only(f):
    d = f['discovery_context'](BACKEND, CFG)
    assert d['hash_checks'] and all(h['status'] == 'ok' for h in d['hash_checks'])
    assert d['pilot_envelope_matches'] is True
    assert all(isinstance(d['pilot_counts'][s['id']], int) for s in CFG['sources'])


def test_outputs_never_overlap_protected_inputs(f):
    assert f['check_protected'](f['output_paths'](BACKEND, CFG), BACKEND, CFG['protected_paths'])
    with pytest.raises(f['RoadCollectionError']):
        f['check_protected'](f['output_paths'](BACKEND / 'data' / 'v2', CFG), BACKEND, CFG['protected_paths'])


def test_v3_1_writes_new_dirs_and_protects_accepted_v3_0_outputs(f, runner):
    old = ('reports/v3/road_collection', 'data/v3/road_collection', 'config/archive/spatial_road_sources_v3_0.json',
           'rerun-road-013-online-001', 'rerun-road-013-offline-001')
    assert set(old) <= set(CFG['protected_paths'])
    assert all(CFG['outputs'][k] not in old for k in ('report_dir', 'data_dir'))
    assert runner.default_cache() == BACKEND / CFG['outputs']['data_dir']  # default offline cache follows the config, never the v3.0 cache
    v30 = copy.deepcopy(CFG)
    v30['outputs'] = {'report_dir': 'reports/v3/road_collection', 'data_dir': 'data/v3/road_collection'}
    with pytest.raises(f['RoadCollectionError'], match='protected'):
        f['check_protected'](f['output_paths'](BACKEND, v30), BACKEND, CFG['protected_paths'])
    for root in ('rerun-road-013-online-001', 'rerun-road-013-offline-001'):
        assert runner.write_conflicts(runner.BACKEND / root, True)  # accepted v3.0 rerun roots cannot be reused
    assert len({s['service_url'] + '#' + str(s['layer_id']) for s in CFG['sources']}) == len(CFG['sources'])


# ---------------------------------------------------------------- runner (execution only)
def test_runner_env_is_explicit(runner, tmp_path):
    e = runner.build_env(tmp_path, True, base={'ROADAWARE_ROAD_CACHE_DIR': '/stale', 'PATH': '/bin'})
    assert e['ROADAWARE_ROAD_ONLINE'] == '1' and e['ROADAWARE_ROAD_CACHE_DIR'] == '' and e['PATH'] == '/bin'
    e = runner.build_env(tmp_path, False, cache=tmp_path / 'c', base={})
    assert e['ROADAWARE_ROAD_ONLINE'] == '0' and e['ROADAWARE_ROAD_CACHE_DIR'] == str((tmp_path / 'c').resolve())
    assert e['ROADAWARE_V3_OUTPUT_ROOT'] == str(tmp_path.resolve())


def test_runner_refuses_overlaps_and_reused_roots(runner, tmp_path):
    assert runner.write_conflicts(tmp_path / 'fresh', True) is None
    assert runner.write_conflicts(runner.BACKEND / 'data' / 'v2' / 'x', True)
    assert runner.write_conflicts(runner.BACKEND, False, cache=runner.default_cache())  # offline default root would write into the cache
    assert runner.write_conflicts(tmp_path, True, cache=tmp_path / CFG['outputs']['data_dir'])
    rep = tmp_path / CFG['outputs']['report_dir']
    rep.mkdir(parents=True)
    assert runner.preconditions(tmp_path, False) is None
    (rep / 'x.csv').write_text('a')
    assert 'already exist' in runner.preconditions(tmp_path, False)
    raw = tmp_path / 'r2' / CFG['outputs']['data_dir'] / 'raw'
    raw.mkdir(parents=True)
    (raw / 'x').write_text('a')
    assert runner.preconditions(tmp_path / 'r2', True) and runner.preconditions(tmp_path / 'r2', False) is None


def test_runner_flag_combinations(runner):
    with pytest.raises(SystemExit):
        runner.parse_args(['--online', '--cache-from', 'x'])
    a = runner.parse_args([])
    assert not a.online and a.cache_from is None
