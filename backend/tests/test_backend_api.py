"""Tests for the task-019 local API: notebook-24 FUNCTIONS (exec'd from the canonical tracked notebook with an explicit FIXTURE pin computed here,
never a trusted pin), fail-closed startup before any exec, the thin FastAPI transport with an injected tiny FAKE runtime, and an opt-in actual
accepted-bundle check. Run from the repository root:
    .venv/bin/python -m pytest backend/tests/test_backend_api.py -q
    ROADAWARE_API_ACTUAL=1 .venv/bin/python -m pytest backend/tests/test_backend_api.py -q -k actual     # after the manager filled the pins
"""
import copy
import hashlib
import json
import math
import os
import sys
import types
from pathlib import Path

import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[2]
BACKEND = REPO / 'backend'
NB24 = BACKEND / 'notebooks' / '24_backend_api_contract.ipynb'
CFG = json.loads((BACKEND / 'config' / 'backend_api_v3.json').read_text('utf-8'))
sys.path.insert(0, str(BACKEND))
from api import runtime as RT  # noqa: E402
from api.app import create_app  # noqa: E402

needs24 = pytest.mark.skipif(not NB24.is_file(), reason='canonical notebook 24 not assembled yet (Codex assembles .ai-team/handoffs/019 first)')


def funcs_of(nb_path):
    nb = json.loads(Path(nb_path).read_text('utf-8'))
    return [''.join(c['source']) for c in nb['cells'] if c['cell_type'] == 'code' and ''.join(c['source']).lstrip().startswith('# FUNCTIONS')]


@pytest.fixture(scope='module')
def H():
    if not NB24.is_file():
        pytest.skip('canonical notebook 24 not assembled yet')
    fixture_pin = hashlib.sha256('\n\n'.join(funcs_of(NB24)).encode('utf-8')).hexdigest()  # FIXTURE pin (test only, not the manager pin)
    return RT.exec_functions(NB24, 3, '\n\n', fixture_pin, 'notebook24')


SEGS = ['s:doh:1:p0:c0:r2000:00000', 's:doh:1:p0:c0:r2000:00001', 's:doh:2:p0:c0:r2000:00000']


def tiny_fc():
    return {'type': 'FeatureCollection', 'features': [
        {'type': 'Feature', 'id': SEGS[0], 'properties': {'route_code': '0001'}, 'geometry': {'type': 'LineString', 'coordinates': [[100.0, 13.0], [100.01, 13.01]]}},
        {'type': 'Feature', 'id': SEGS[1], 'properties': {'route_code': '0001'}, 'geometry': {'type': 'LineString', 'coordinates': [[100.01, 13.01], [100.02, 13.02]]}},
        {'type': 'Feature', 'id': SEGS[2], 'properties': {'route_code': '0002'}, 'geometry': {'type': 'LineString', 'coordinates': [[101.0, 15.0], [101.02, 15.0]]}}]}


def tiny_csv():
    return pd.DataFrame({'segment_id': SEGS, 'route_code': ['0001', '0001', '0002'], 'geom_length_m': ['2000.0', '2000.0', '1500.5'],
                         'province_code': ['13.0', '13.0', '30.0']}, dtype=str)


GL = CFG['limits']['geometry']


# ---------- notebook-24 pure FUNCTIONS ----------
@needs24
def test_notebook24_has_exactly_three_functions_cells_and_no_ai_team_reference():
    f = funcs_of(NB24)
    assert len(f) == 3 and not any('.ai-team' in s for s in f)


@needs24
@pytest.mark.parametrize('raw,code', [(b'{"a":1,"a":2}', 'invalid_json'), (b'{"a":NaN}', 'invalid_json'), (b'{"a":Infinity}', 'invalid_json'),
                                      (b'{"a":1e999}', 'invalid_json'), (b'\xff\xfe', 'invalid_json'), (b'', 'invalid_json'), (b'{"a":', 'invalid_json'),
                                      (b'x' * 65537, 'body_too_large')])
def test_strict_json_body(H, raw, code):
    with pytest.raises(H['ApiError']) as e:
        H['parse_json_body'](raw, 65536)
    assert e.value.code == code and e.value.status in (400, 413)


@needs24
def test_sanitize_and_error_body_never_leak_paths_or_details(H):
    e = H['ApiError']('artifact_hash_mismatch', 'unavailable', 'bundle /Users/x/RoadAware/backend/models/a.joblib differs')
    b = H['error_body'](e)
    assert '/Users' not in json.dumps(b) and b['error']['message'] == H['GENERIC_MESSAGE']['unavailable'] and b['production_ready'] is False
    assert '<redacted>' in H['sanitize_message']('bad /home/u/a/b.csv here', 'invalid')
    with pytest.raises(ValueError):
        H['check_finite']({'x': [1.0, float('nan')]})


@needs24
def test_body_contracts_exact_fields(H):
    assert H['spatial_prediction_body']({'unit': 'daily', 'requests': []}) == ('daily', [])
    for bad in ({'unit': 'daily'}, {'unit': 'daily', 'requests': [], 'x': 1}, [], {'unit': 'daily', 'requests': {}}):
        with pytest.raises(H['ApiError']):
            H['spatial_prediction_body'](bad)
    with pytest.raises(H['ApiError']):
        H['province_prediction_body']({'requests': [], 'model': 'x'})


@needs24
def test_spatial_answer_maps_families(H):
    assert H['spatial_answer']({'ok': True, 'results': []})['ok'] is True
    for fam, status in (('invalid', 400), ('coverage', 404), ('unavailable', 503)):
        with pytest.raises(H['ApiError']) as e:
            H['spatial_answer']({'ok': False, 'error': {'code': 'c', 'family': fam, 'message': 'm', 'rows': [0, 2]}})
        assert e.value.status == status and (e.value.rows == [0, 2] if fam != 'unavailable' else e.value.rows is None)
    assert H['catalog_query_error']([{'code': 'unknown_segment'}]).status == 404
    assert H['catalog_query_error']([{'code': 'unknown_segment'}, {'code': 'invalid_date'}]).status == 400
    assert all(x['message'] is None for x in H['province_request_error']([{'index': 0, 'field': 'province_key', 'code': 'unknown_province', 'message': 'echo'}]).errors)


@needs24
def test_geometry_index_and_pages(H):
    idx = H['build_geometry_index'](tiny_fc(), tiny_csv(), SEGS, GL)
    assert idx['ids'] == tuple(sorted(SEGS)) and idx['km'][idx['pos'][SEGS[2]]] == pytest.approx(1.5005) and idx['province_code'][0] == 13
    pages, cur = [], 0
    while cur is not None:
        r = H['query_segments'](idx, (97.0, 5.0, 106.0, 21.0), 2, cur, 'snap')
        pages.append([f['id'] for f in r['features']])
        cur = None if r['page']['next_cursor'] is None else int(r['page']['next_cursor'])
    assert pages == [sorted(SEGS)[:2], sorted(SEGS)[2:]]
    r = H['query_segments'](idx, (100.5, 14.0, 101.5, 16.0), 10, 0, 'snap')
    assert [f['id'] for f in r['features']] == [SEGS[2]] and r['features'][0]['geometry']['type'] == 'LineString'
    with pytest.raises(H['ApiError']):
        H['query_segments'](idx, (97.0, 5.0, 106.0, 21.0), 2, 99, 'snap')
    assert H['get_segment'](idx, SEGS[0], set(), 'snap')['feature']['id'] == SEGS[0]
    for sid, code in (('other-road', 'unsupported_segment'), ('nope', 'unknown_segment')):
        with pytest.raises(H['ApiError']) as e:
            H['get_segment'](idx, sid, {'other-road'}, 'snap')
        assert e.value.code == code and e.value.status == 404


@needs24
@pytest.mark.parametrize('mutate', ['dup', 'nan', 'envelope', 'mismatch', 'props', 'route', 'length', 'expected'])
def test_geometry_index_fails_closed(H, mutate):
    fc, df, exp = tiny_fc(), tiny_csv(), list(SEGS)
    if mutate == 'dup':
        fc['features'][1]['id'] = SEGS[0]
    elif mutate == 'nan':
        fc['features'][0]['geometry']['coordinates'][0][0] = float('nan')
    elif mutate == 'envelope':
        fc['features'][0]['geometry']['coordinates'] = [[13.0, 100.0], [13.01, 100.01]]  # lat/lon swapped
    elif mutate == 'mismatch':
        df.loc[0, 'segment_id'] = 'zzz'
    elif mutate == 'props':
        fc['features'][0]['properties']['lambda'] = 0
    elif mutate == 'route':
        df.loc[0, 'route_code'] = '9999'
    elif mutate == 'length':
        df.loc[0, 'geom_length_m'] = 'inf'
    else:
        exp = exp[:2]
    with pytest.raises(H['ApiError']) as e:
        H['build_geometry_index'](fc, df, exp, GL)
    assert e.value.family == 'unavailable'


@needs24
@pytest.mark.parametrize('bbox', ['106,5,97,21', '97,21,106,5', 'nan,5,106,21', 'inf,5,106,21', '1e1,5,106,21', '97,5,106', '97,5,106,21,1', '0,0,90,80',
                                  '-181,5,106,21', '97, 5,106,21', ''])
def test_bbox_refused(H, bbox):
    with pytest.raises(H['ApiError']):
        H['parse_bbox'](bbox, GL)


@needs24
def test_page_and_query_limits(H):
    assert H['parse_page']({}, GL) == (100, 0)
    for q in ({'limit': '0'}, {'limit': '501'}, {'limit': '-1'}, {'limit': 'true'}, {'cursor': '1.5'}):
        with pytest.raises(H['ApiError']):
            H['parse_page'](q, GL)
    with pytest.raises(H['ApiError']):
        H['strict_query']([('bbox', 'a'), ('bbox', 'b')], ('bbox',), 'segments')
    with pytest.raises(H['ApiError']):
        H['strict_query']([('path', '/etc')], ('bbox',), 'segments')


def metric_row(unit, method, mae, status='finite', dev='7.1'):
    r = {k: '1' for k in ('n_segments', 'n_positive_cells', 'n_raw_records', 'actual_total', 'pred_total', 'n_zero_pred_on_positive', 'rmse',
                          'bias_pred_minus_actual', 'wape', 'pred_to_actual_ratio', 'deviance_floor_audit', 'deviance_floor_audit_floor',
                          'deviance_floor_audit_n_floored', 'deviance_floor_audit_floored_contribution', 'deviance_floor_audit_floored_share')}
    r.update(unit=unit, dim='overall', group='all', method=method, mae=str(mae), deviance_status=status, mean_poisson_deviance=dev if status == 'finite' else '')
    return r


@needs24
def test_diagnostics_summary_keeps_infinite_deviance_null_and_limits(H):
    rec = json.loads((REPO / 'workflow/evaluation-2026/accepted-diagnostics-v3.json').read_text('utf-8'))
    A = rec['acceptance']
    man = {'status': 'complete', 'research_only': True, 'production_ready': False, 'checks_failed': 0, 'evaluation_available': True,
           'counts': {'raw_records': A['raw_rows'], 'eligible_records': A['eligible_raw_records'], 'positive_cells': {'daily': A['daily_positive_cells'], '6h': A['six_hour_positive_cells']}}}
    rows = [metric_row('daily', 'selected', 1.01), metric_row('daily', 'strong_baseline', 1.02, 'infinite_due_zero_prediction'),
            metric_row('6h', 'selected', 1.05), metric_row('6h', 'strong_baseline', 1.04, 'infinite_due_zero_prediction'),
            dict(metric_row('daily', 'selected', 9.0), dim='month')]
    s = H['diagnostics_2026_summary'](rec, man, rows)
    by = {(r['unit'], r['method']): r for r in s['overall_metrics']}
    assert by[('daily', 'strong_baseline')]['mean_poisson_deviance'] is None and by[('daily', 'strong_baseline')]['deviance_status'] != 'finite'
    assert by[('daily', 'strong_baseline')]['deviance_floor_audit'] is not None and s['lower_mae_on_this_conditional_cohort'] == {'daily': 'selected', '6h': 'strong_baseline'}
    assert s['counts']['eligible_raw_records'] == 4336 and s['counts']['requested_window_rows'] == 17272 and s['production_ready'] is False
    assert any('Provider checksum NOT verified' in x for x in s['limits'])
    H['check_finite'](s)
    bad = copy.deepcopy(man)
    bad['counts']['eligible_records'] = 1
    with pytest.raises(H['ApiError']):
        H['diagnostics_2026_summary'](rec, bad, rows)


EVAL_COLS = ('n', 'zero_cells', 'nonzero_cells', 'total_actual', 'total_pred', 'pred_over_actual', 'mean_poisson_deviance', 'mae', 'rmse', 'bias', 'wape',
             'exposure_segment_km_periods', 'observed_records_per_km_period', 'predicted_records_per_km_period', 'metric_floor_cells',
             'metric_floor_actual_positive_cells', 'metric_floor_actual_records', 'metric_floor_deviance_sum')
SEL21 = {u: {'selected': 'hgb::ctx', 'baseline': 'seg_k365'} for u in ('daily', '6h')}


def eval_row(unit, scope, role, dimension='pooled', group='all', **kw):
    r = {k: '1.5' for k in EVAL_COLS}
    r.update(n='100', total_actual='12.0', wape_status='ok', mean_deviance_zero_cells='9.9')
    r.update(unit=unit, scope=scope, role=role, method=SEL21[unit][role], dimension=dimension, group=group)
    r.update(kw)
    return r


def eval_fixture_rows():
    rows = [eval_row(u, s, ro) for u in ('daily', '6h') for s in ('oof', 'diag') for ro in ('selected', 'baseline')]
    rows += [eval_row('daily', 'diag', 'selected', 'period', 'seen_2024', mae='0.25', metric_floor_cells='7'),
             eval_row('daily', 'diag', 'baseline', 'period', 'seen_2024', wape='', wape_status='undefined_zero_actual'),
             eval_row('daily', 'oof', 'selected', 'route', 'r0001'),  # other dimensions stay in the report, not in the API
             dict(eval_row('6h', 'oof', 'selected'), role='candidate', method='other')]
    return rows


@needs24
def test_evaluation_21_metrics_expose_numeric_selected_and_baseline_rows(H):
    rec = {'status': 'accepted_spatial_evaluation_research_only', 'functions_sha256': 'f' * 64}
    man = {'status': 'complete', 'functions_sha256': 'f' * 64, 'selected': SEL21, 'checks': [1, 2], 'report_files': {'metrics_by_group.csv': 'a' * 64}}
    s = H['evaluation_21_summary'](rec, man, eval_fixture_rows())
    m = s['metrics']
    assert len(m) == 10 and {(r['dimension'], r['group']) for r in m} == {('pooled', 'all'), ('period', 'seen_2024')}
    by = {(r['unit'], r['scope'], r['role'], r['dimension']): r for r in m}
    p = by[('daily', 'diag', 'selected', 'period')]
    assert p['mae'] == 0.25 and p['metric_floor_cells'] == 7 and p['n'] == 100 and p['total_actual'] == 12.0 and p['wape_status'] == 'ok'
    assert by[('daily', 'diag', 'baseline', 'period')]['wape'] is None and by[('daily', 'diag', 'baseline', 'period')]['wape_status'] == 'undefined_zero_actual'
    assert by[('6h', 'oof', 'baseline', 'pooled')]['method'] == 'seg_k365' and 'mean_deviance_zero_cells' not in p
    assert s['production_ready'] is False and 'diagnostics_2026' in s['metrics_note']
    H['check_finite'](s)
    for bad in ([dict(r, method='swapped') if r['role'] == 'baseline' and r['dimension'] == 'pooled' else r for r in eval_fixture_rows()],  # selection differs
                [r for r in eval_fixture_rows() if not (r['unit'] == '6h' and r['scope'] == 'diag' and r['role'] == 'baseline')],  # pooled row missing
                eval_fixture_rows() + [eval_row('daily', 'oof', 'selected')],  # duplicate key
                [dict(r, dim=r.pop('dimension')) for r in eval_fixture_rows()]):  # 'dim' is not the CSV column name
        with pytest.raises(H['ApiError']):
            H['evaluation_21_summary'](rec, man, bad)


def test_load_evaluation_verifies_metrics_hash_before_reading(tmp_path):
    root = 'backend/rerun-x'
    d = tmp_path / root / 'reports/v3/spatial_evaluation'
    d.mkdir(parents=True)
    (d / 'metrics_by_group.csv').write_text('unit,scope\ndaily,oof\n', 'utf-8')
    man = {'status': 'complete', 'report_files': {'metrics_by_group.csv': '0' * 64}}
    (d / 'spatial_evaluation_manifest.json').write_text(json.dumps(man), 'utf-8')
    (tmp_path / 'workflow/evaluation').mkdir(parents=True)
    (tmp_path / 'workflow/evaluation/rec.json').write_text(json.dumps({'root': root, 'manifest_sha256': RT.sha256_file(d / 'spatial_evaluation_manifest.json')}), 'utf-8')
    lock = {'files': {'workflow/evaluation/rec.json': '1' * 64}, 'components': {'evaluation': 'workflow/evaluation/rec.json'}}
    called = []
    with pytest.raises(RT.StartupError) as ei:
        RT._load_evaluation(tmp_path, lock, CFG, {'evaluation_21_summary': lambda *a: called.append(a)}, {})
    assert ei.value.code == 'artifact_hash_mismatch' and not called


@needs24
def test_history_period_marks_2026_unsupported_not_zero(H):
    res = {'history_cutoff_local': '2026-05-01T18:00:00+07:00', 'n_selected_records': 0,
           'history_window': {'window_start_local_exclusive': '2021-05-01T18:00:00+07:00', 'catalog_data_start_local': '2021-01-01T00:00:00+07:00',
                              'catalog_data_end_local_exclusive': '2026-01-01T00:00:00+07:00', 'window_fully_inside_catalog_data': False}}
    out = H['spatial_history_period'](res, '2021-01', '2025-12')
    assert out['period_status']['status'] == 'partially_unsupported_period' and out['period_status']['unsupported_after']['from_local'].startswith('2026-01-01')
    res['history_cutoff_local'], res['history_window']['window_fully_inside_catalog_data'] = '2024-01-30T18:00:00+07:00', True
    assert H['spatial_history_period'](res, '2021-01', '2025-12')['period_status']['unsupported_after'] is None


# ---------- fail-closed startup (before any exec/deserialization) ----------
def test_default_startup_fails_closed_until_manager_pins_24():
    lock = json.loads((REPO / RT.LOCK_REL).read_text('utf-8'))
    if lock.get('notebook24_functions') is not None:
        pytest.skip('manager pins already filled; the actual test covers readiness')
    rt = RT.load_runtime()
    assert not rt.ready and rt.components['notebook24'] == {'status': 'unavailable', 'code': 'api_pins_pending'} and rt.h24 is None


def fake_repo(tmp_path, pin_ok=True, extra=None):
    (tmp_path / 'workflow/api').mkdir(parents=True)
    (tmp_path / 'backend/config').mkdir(parents=True)
    (tmp_path / 'backend/notebooks').mkdir(parents=True)
    sentinel = tmp_path / 'EXECUTED'
    cells = [{'cell_type': 'code', 'id': 'f' + str(i), 'metadata': {}, 'outputs': [], 'execution_count': None,
              'source': '# FUNCTIONS ' + str(i) + '\nimport pathlib\npathlib.Path(' + repr(str(sentinel)) + ').write_text("x")\n'} for i in range(3)]
    nbp = tmp_path / 'backend/notebooks/24_backend_api_contract.ipynb'
    nbp.write_text(json.dumps({'cells': cells, 'metadata': {}, 'nbformat': 4, 'nbformat_minor': 5}), 'utf-8')
    cfgp = tmp_path / 'backend/config/backend_api_v3.json'
    cfgp.write_text(json.dumps(CFG), 'utf-8')
    fsha = hashlib.sha256('\n\n'.join(c['source'] for c in cells).encode('utf-8')).hexdigest()
    files = {'backend/config/backend_api_v3.json': RT.sha256_file(cfgp), 'backend/notebooks/24_backend_api_contract.ipynb': RT.sha256_file(nbp)}
    files.update(extra or {})
    lock = {'kind': RT.LOCK_KIND, 'files': files, 'components': {}, 'required_api_files_pending_manager_review': sorted(files)[:2],
            'notebook24_functions': {'cells': 3, 'join': '\n\n', 'sha256': fsha if pin_ok else '0' * 64}}
    (tmp_path / RT.LOCK_REL).write_text(json.dumps(lock), 'utf-8')
    return sentinel


@pytest.mark.parametrize('case,code', [('tampered_file', 'artifact_hash_mismatch'), ('missing_file', 'artifact_missing'),
                                       ('functions_pin', 'artifact_hash_mismatch'), ('wrong_kind', 'artifact_unavailable')])
def test_tampered_or_missing_inputs_refuse_before_exec(tmp_path, case, code):
    (tmp_path / 'x').mkdir()
    (tmp_path / 'x/a.json').write_text('{}', 'utf-8')
    extra = {'x/a.json': '1' * 64} if case == 'tampered_file' else ({'x/missing.json': '1' * 64} if case == 'missing_file' else {})
    sentinel = fake_repo(tmp_path, pin_ok=case != 'functions_pin', extra=extra)
    if case == 'wrong_kind':
        lp = tmp_path / RT.LOCK_REL
        lock = json.loads(lp.read_text('utf-8'))
        lock['kind'] = 'other'
        lp.write_text(json.dumps(lock), 'utf-8')
    rt = RT.load_runtime(repo=tmp_path)
    assert rt.components['notebook24'] == {'status': 'unavailable', 'code': code} and not rt.ready and not sentinel.exists()


def test_valid_fake_pins_exec_only_after_verification(tmp_path):
    sentinel = fake_repo(tmp_path)
    rt = RT.load_runtime(repo=tmp_path)
    assert sentinel.exists() and rt.components['notebook24']['status'] == 'available'
    assert not rt.ready and all(rt.components[c]['status'] == 'unavailable' for c in ('spatial_runtime', 'catalog', 'geometry'))  # no records -> fail closed


# ---------- transport with an injected tiny FAKE runtime (not evidence about real models) ----------
def fake_predict(svc, unit, reqs):
    if not isinstance(unit, str) or unit not in ('daily', '6h'):
        return {'ok': False, 'unit': None, 'production_ready': False, 'error': {'code': 'invalid_unit', 'family': 'invalid', 'message': 'unit', 'rows': []}}
    if not 1 <= len(reqs) <= 128:
        return {'ok': False, 'error': {'code': 'batch_size', 'family': 'invalid', 'message': 'rows', 'rows': []}}
    bad = [i for i, r in enumerate(reqs) if r.get('segment_id') not in SEGS]
    if bad:
        return {'ok': False, 'error': {'code': 'unknown_segment', 'family': 'coverage', 'message': 'outside', 'rows': bad}}
    lam = float('nan') if any(r.get('target_date') == '2099-01-01' for r in reqs) else 0.25
    return {'ok': True, 'unit': unit, 'rows': len(reqs), 'production_ready': False,
            'results': [{'segment_id': r['segment_id'], 'target_date': r['target_date'], 'expected_recorded_count': lam + i} for i, r in enumerate(reqs)]}


def fake_runtime(H, ready=True):
    comps = {c: {'status': 'available', 'code': None} for c in RT.COMPONENTS}
    comps['province_runtime'] = {'status': 'unavailable', 'code': 'artifact_unavailable'}  # optional V2 service absent in this fake
    if not ready:
        comps['spatial_runtime'] = {'status': 'unavailable', 'code': 'artifact_hash_mismatch'}
    svc = types.MappingProxyType({'status': 'available', 'ctx': {'unsupported': frozenset({'other-road'})}})
    return RT.Runtime(comps, H, CFG, spatial=svc, ns22={'predict_batch': fake_predict, 'predict_baseline_batch': fake_predict},
                      geometry=H['build_geometry_index'](tiny_fc(), tiny_csv(), SEGS, GL))


@pytest.fixture()
def client(H):
    from fastapi.testclient import TestClient
    with TestClient(create_app(runtime_factory=lambda: fake_runtime(H))) as c:
        yield c


def post(c, path, obj=None, raw=None, ctype='application/json'):
    return c.post(path, content=raw if raw is not None else json.dumps(obj).encode('utf-8'), headers={'Content-Type': ctype})


def assert_strict_finite_json(text):
    """Parses as JSON refusing NaN/Infinity constants, then walks every numeric value (bool excluded) and requires it finite."""
    def refuse(c):
        raise AssertionError('non-finite JSON constant ' + c)

    def walk(o):
        if isinstance(o, dict):
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
        elif isinstance(o, float):
            assert math.isfinite(o)
    walk(json.loads(text, parse_constant=refuse))


def test_strict_finite_json_fixture_parses_instead_of_string_scanning():
    assert_strict_finite_json('{"error":{"message":"non-finite JSON constant refused (NaN/Infinity)"},"x":[1,2.5,true]}')
    for bad in ('{"x":NaN}', '{"x":[1,Infinity]}', '{"x":-Infinity}', '{"x":1e999}'):
        with pytest.raises(AssertionError):
            assert_strict_finite_json(bad)


@needs24
def test_health_ready_and_unavailable_runtime(H, client):
    from fastapi.testclient import TestClient
    assert client.get('/health').json()['status'] == 'alive'
    r = client.get('/ready')
    assert r.status_code == 200 and r.json()['research_backend_ready'] is True and r.json()['production_ready'] is False
    with TestClient(create_app(runtime_factory=lambda: fake_runtime(H, ready=False))) as c:
        r = c.get('/ready')
        assert r.status_code == 503 and r.json()['components']['spatial_runtime']['code'] == 'artifact_hash_mismatch'
        r = post(c, '/api/v1/spatial/predictions', {'unit': 'daily', 'requests': [{'segment_id': SEGS[0], 'target_date': '2024-03-01'}]})
        assert r.status_code == 503 and r.json()['error']['code'] == 'backend_not_ready' and '/Users' not in r.text
        assert c.get('/health').status_code == 200


@needs24
def test_predictions_order_errors_and_limits(client):
    rows = [{'segment_id': s, 'target_date': '2024-03-0' + str(i + 1)} for i, s in enumerate(SEGS)]
    r = post(client, '/api/v1/spatial/predictions', {'unit': 'daily', 'requests': rows})
    assert r.status_code == 200 and [x['segment_id'] for x in r.json()['results']] == SEGS and r.json()['production_ready'] is False
    cases = [(post(client, '/api/v1/spatial/predictions', raw=b'{"unit":'), 400, 'invalid_json'),
             (post(client, '/api/v1/spatial/predictions', raw=b'{"unit":"daily","requests":[{"segment_id":"a","target_date":NaN}]}'), 400, 'invalid_json'),
             (post(client, '/api/v1/spatial/predictions', {'unit': 'daily', 'requests': rows, 'x': 1}), 400, 'invalid_fields'),
             (post(client, '/api/v1/spatial/predictions', {'unit': True, 'requests': rows}), 400, 'invalid_unit'),
             (post(client, '/api/v1/spatial/predictions', {'unit': 'daily', 'requests': [dict(rows[0], segment_id='nope')]}), 404, 'unknown_segment'),
             (post(client, '/api/v1/spatial/predictions', raw=b'{"unit":"daily","requests":[' + b' ' * 65600 + b']}'), 413, 'body_too_large'),
             (post(client, '/api/v1/spatial/predictions', raw=b'{}', ctype='text/plain'), 415, 'unsupported_media_type'),
             (post(client, '/api/v1/spatial/predictions', {'unit': 'daily', 'requests': [dict(rows[0], target_date='2099-01-01')]}), 500, 'response_invalid'),
             (client.get('/api/v1/nope'), 404, 'not_found'), (client.get('/api/v1/spatial/predictions'), 405, 'method_not_allowed'),
             (post(client, '/api/v1/predictions', {'requests': []}), 503, 'component_unavailable')]
    for r, st, code in cases:
        assert r.status_code == st and r.json()['error']['code'] == code, (st, code, r.text[:200])
        assert 'Traceback' not in r.text and '/Users' not in r.text and '"target_date":NaN' not in r.text  # no traceback, path or input-body echo
        assert_strict_finite_json(r.text)  # the wording "(NaN/Infinity)" inside a message string is legal finite JSON
    assert post(client, '/api/v1/spatial/predictions', {'unit': 'daily', 'requests': [dict(rows[0], segment_id='nope'), rows[1], dict(rows[2], segment_id='x')]}).json()['error']['rows'] == [0, 2]


@needs24
def test_segments_routes(client):
    r = client.get('/api/v1/segments', params={'bbox': '97,5,106,21', 'limit': '2'})
    assert r.status_code == 200 and r.json()['page']['next_cursor'] == '2' and r.json()['type'] == 'FeatureCollection'
    assert client.get('/api/v1/segments/' + SEGS[0]).json()['feature']['id'] == SEGS[0]
    assert client.get('/api/v1/segments/other-road').json()['error']['code'] == 'unsupported_segment'
    assert client.get('/api/v1/segments', params={'bbox': '106,5,97,21'}).status_code == 400
    assert client.get('/api/v1/segments', params={'bbox': '97,5,106,21', 'x': '1'}).status_code == 400
    assert client.get('/api/v1/segments/' + SEGS[0], params={'a': '1'}).status_code == 400


@needs24
def test_cors_allowlist_no_wildcard_no_credentials(client):
    ok = client.options('/api/v1/spatial/predictions', headers={'Origin': 'http://localhost:5173', 'Access-Control-Request-Method': 'POST',
                                                               'Access-Control-Request-Headers': 'content-type'})
    assert ok.status_code == 200 and ok.headers['access-control-allow-origin'] == 'http://localhost:5173' and 'access-control-allow-credentials' not in ok.headers
    bad = client.options('/api/v1/spatial/predictions', headers={'Origin': 'http://evil.example', 'Access-Control-Request-Method': 'POST'})
    assert 'access-control-allow-origin' not in bad.headers
    assert 'access-control-allow-origin' not in client.get('/health', headers={'Origin': 'http://evil.example'}).headers


@needs24
def test_openapi_lists_routes(client):
    paths = client.get('/openapi.json').json()['paths']
    for p in ('/health', '/ready', '/api/v1/metadata', '/api/v1/evaluation', '/api/v1/provinces', '/api/v1/history', '/api/v1/segments',
              '/api/v1/segments/{segment_id}', '/api/v1/spatial/history', '/api/v1/spatial/predictions', '/api/v1/spatial/baseline-predictions', '/api/v1/predictions'):
        assert p in paths


from api import openapi_docs as D  # noqa: E402

POST_ROUTES = ('/api/v1/spatial/predictions', '/api/v1/spatial/baseline-predictions', '/api/v1/spatial/history', '/api/v1/predictions')


def _examples(op, status):
    return op['responses'][str(status)]['content']['application/json']['examples']


@needs24
def test_openapi_request_schemas_are_strict_and_bounded(client):
    paths = client.get('/openapi.json').json()['paths']
    for p in POST_ROUTES:
        rb = paths[p]['post']['requestBody']
        sch = rb['content']['application/json']['schema']
        assert rb['required'] is True and sch['additionalProperties'] is False and sch['required']
        if 'requests' in sch['properties']:
            it = sch['properties']['requests']
            assert it['maxItems'] == CFG['limits']['max_batch'] == 128 and it['minItems'] == 1 and it['items']['additionalProperties'] is False
            assert set(it['items']['required']) <= set(it['items']['properties'])
        assert 'validates only through the pinned notebook FUNCTIONS' in sch['description']  # documentation, not a second validator
    assert paths['/api/v1/spatial/predictions']['post']['requestBody']['content']['application/json']['schema']['required'] == ['unit', 'requests']
    assert {q['name'] for q in paths['/api/v1/history']['get']['parameters']} >= {'province_key', 'start_month', 'end_month'}
    assert {q['name'] for q in paths['/api/v1/segments']['get']['parameters']} >= {'bbox', 'limit', 'cursor'}


@needs24
def test_openapi_success_error_unavailable_examples(client):
    paths = client.get('/openapi.json').json()['paths']
    sp = paths['/api/v1/spatial/predictions']['post']
    units = {ex['value']['unit'] for ex in sp['requestBody']['content']['application/json']['examples'].values()}
    assert units == {'daily', '6h'} and {e['value']['unit'] for e in _examples(sp, 200).values()} == {'daily', '6h'}
    for path, method in (('/api/v1/spatial/predictions', 'post'), ('/api/v1/spatial/baseline-predictions', 'post'), ('/api/v1/spatial/history', 'post'),
                         ('/api/v1/predictions', 'post'), ('/api/v1/history', 'get'), ('/api/v1/segments', 'get'), ('/api/v1/segments/{segment_id}', 'get'),
                         ('/api/v1/evaluation', 'get')):
        op = paths[path][method]
        assert all(e['value']['ok'] is True and e['value']['production_ready'] is False for e in _examples(op, 200).values()), path
        assert {e['value']['error']['code'] for e in _examples(op, 503).values()} == {'backend_not_ready', 'component_unavailable'}, path
        assert all(e['value']['error']['message'] == D.GENERIC_UNAVAILABLE for e in _examples(op, 503).values())
    assert _examples(paths['/api/v1/predictions']['post'], 200)['province_v2_ok']['value']['province_prediction_v2']['results'][0]['unit'] == 'daily'
    assert 'ready_unavailable' in _examples(paths['/ready']['get'], 503)
    m = _examples(paths['/api/v1/evaluation']['get'], 200)['evaluation_ok']['value']['spatial_evaluation_21']['metrics']
    assert {(r['scope'], r['role']) for r in m} == {('oof', 'selected'), ('oof', 'baseline'), ('diag', 'selected')} and all(isinstance(r['mae'], float) for r in m)
    text = json.dumps(paths, ensure_ascii=False)
    assert '/Users/' not in text and 'event_uid' not in text and 'source_row' not in text and '.joblib' not in text


@needs24
def test_example_requests_pass_the_notebook24_body_contract_and_schemas(H):
    checked = 0
    for name, ex in D.EXAMPLES.items():
        rq = ex.get('request') or {}
        if 'body' not in rq or ex['status'] != 200:  # error examples are deliberately invalid
            continue
        checked += 1
        obj = H['parse_json_body'](json.dumps(rq['body'], ensure_ascii=False).encode('utf-8'), CFG['limits']['max_body_bytes'])
        sch = D.SCHEMAS[D.REQUEST_EXAMPLES[rq['path']][0]]
        assert set(sch['required']) <= set(obj) <= set(sch['properties']), name
        if rq['path'] == '/api/v1/predictions':
            H['province_prediction_body'](obj)
        elif rq['path'] != '/api/v1/spatial/history':
            H['spatial_prediction_body'](obj)
        if 'requests' in obj:
            it = sch['properties']['requests']['items']
            assert 1 <= len(obj['requests']) <= 128 and all(set(it['required']) <= set(r) <= set(it['properties']) for r in obj['requests']), name
    assert checked == 5 and D.MAX_BATCH == CFG['limits']['max_batch'] and D.EXAMPLES['body_too_large']['response']['error']['message'].endswith(str(CFG['limits']['max_body_bytes']) + ' bytes')


def test_matches_is_a_subset_comparison_with_tolerance():
    live = {'a': 1.0, 'b': [{'x': 1, 'y': 2}, {'x': 3}], 'c': True, 'seconds': 0.2}
    assert D.matches({'a': 1.0 + 1e-15, 'b': [{'x': 3}]}, live) and D.matches({'seconds': 9.0}, live)
    assert not D.matches({'a': 1.001}, live) and not D.matches({'c': 1}, live) and not D.matches({'z': None}, live)
    assert not D.matches({'b': [{'x': 4}]}, live) and not D.matches([1], {'a': 1})


@pytest.mark.skipif(not (BACKEND / 'rerun-api-019-001/sample_responses.json').is_file(), reason='actual 001 live sample_responses.json not present (ignored run root)')
def test_examples_are_subsets_of_the_actual_001_live_samples():
    s = json.loads((BACKEND / 'rerun-api-019-001/sample_responses.json').read_text('utf-8'))
    assert D.matches(D.EXAMPLES['ready_ok']['response'], s['ready'])
    assert D.matches(D.EXAMPLES['spatial_history_ok']['response'], s['spatial_history'])
    assert D.matches(D.EXAMPLES['segments_page']['response']['features'], s['segments_page']['features'])
    assert D.matches(D.EXAMPLES['spatial_date_before_asof']['response'], s['error_example'])
    assert D.matches(D.EXAMPLES['spatial_daily']['response']['results'], s['spatial_prediction']['results'])
    ev = {k: v for k, v in D.EXAMPLES['evaluation_ok']['response'].items() if k != 'spatial_evaluation_21'}
    assert D.matches(ev, s['evaluation'])


def test_smoke_fixture_lock_path_is_bounded():
    sys.path.insert(0, str(BACKEND / 'scripts'))
    import smoke_api_live as S
    ok = 'backend/rerun-api-019-002/' + S.FIXTURE_DIR + '/' + S.FIXTURE_LOCK
    assert S._fixture_lock_rel(ok) == ok
    for bad in ('workflow/api/input-pins-v3.json', '/tmp/x.json', 'backend/rerun-api-1/../../workflow/api/input-pins-v3.json',
                'backend/other/' + S.FIXTURE_DIR + '/' + S.FIXTURE_LOCK):
        with pytest.raises(SystemExit):
            S._fixture_lock_rel(bad)


def _smoke():
    sys.path.insert(0, str(BACKEND / 'scripts'))
    import smoke_api_live as S
    return S


def test_smoke_fixture_child_argv_generated_by_the_phase_dispatches_to_child_mode(tmp_path, monkeypatch):
    S = _smoke()
    (tmp_path / 'workflow/api').mkdir(parents=True)
    (tmp_path / S.LOCK_REL).write_text(json.dumps({'files': {'backend/notebooks/24_backend_api_contract.ipynb': 'a' * 64}}), 'utf-8')
    root = tmp_path / 'backend' / 'rerun-api-019-test'
    root.mkdir(parents=True)
    seen = {}

    def fake_start(cmd, log_path, port, timeout):
        seen['cmd'] = cmd
        return types.SimpleNamespace(), None, None  # child "never answered": the phase records a failed check, nothing is contacted

    monkeypatch.setattr(S, 'REPO', tmp_path)
    monkeypatch.setattr(S, 'RESULTS', [])
    monkeypatch.setattr(S, 'port_free', lambda port: True)
    monkeypatch.setattr(S, 'start_server', fake_start)
    monkeypatch.setattr(S, 'stop_server', lambda proc, log: 0)
    assert S.run_fixture_phase(root, 8766, 5.0) == 0
    cmd = seen['cmd']
    assert cmd[0] == sys.executable and Path(cmd[1]) == BACKEND / 'scripts' / 'smoke_api_live.py' and '--run-root' not in cmd
    copied = json.loads((root / S.FIXTURE_DIR / S.FIXTURE_LOCK).read_text('utf-8'))
    assert copied['files']['backend/notebooks/24_backend_api_contract.ipynb'] != 'a' * 64 and 'TEST_FIXTURE' in copied
    calls = []
    monkeypatch.setattr(S, 'serve_fixture', lambda lock_rel, port: calls.append((lock_rel, port)) or 0)
    assert S.main(cmd[2:]) == 0  # the exact generated argv parses and reaches the child mode (was: argparse exit 2, --run-root required)
    assert calls == [('backend/rerun-api-019-test/' + S.FIXTURE_DIR + '/' + S.FIXTURE_LOCK, 8766)]
    assert S._fixture_lock_rel(calls[0][0]) == calls[0][0]
    for bad in ([], ['--port', '8765'], cmd[2:] + ['--run-root', 'backend/rerun-api-x'], cmd[2:] + ['--fixture-port', '9000']):
        with pytest.raises(SystemExit):
            S.main(bad)
    assert len(calls) == 1


def _tiny_consumed_repo(root, S, overlap=None):
    """Tiny stand-in for the accepted chains: lock -> records/config -> 22 pins -> 20 model_bundles -> models/<unit>/<file>; 13 config/manifest -> 11 bundles.
    overlap='same' also pins the 21 manifest in the 22 serving pins (like the real chains); overlap='conflict' pins it there with a different hash."""
    def put(rel, obj):
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(obj if isinstance(obj, bytes) else json.dumps(obj).encode('utf-8'))
        return hashlib.sha256(p.read_bytes()).hexdigest()

    e21 = 'backend/e21/reports/v3/spatial_evaluation/'
    ev = {'root': 'backend/e21', 'manifest_sha256': put(e21 + 'spatial_evaluation_manifest.json',
                                                        {'report_files': {'metrics_by_group.csv': put(e21 + 'metrics_by_group.csv', b'm')}})}
    mb_dir = 'backend/m20/data'
    bundles = []
    for u in ('daily', '6h'):
        for f in ('c__core.joblib', 'c__context.joblib'):  # same file names in both units, like the real 20 bundles
            bundles.append({'unit': u, 'config_id': 'c', 'file': f, 'sha256': put(mb_dir + '/models/' + u + '/' + f, (u + f).encode())})
        bundles.append({'unit': u, 'config_id': 'other', 'file': 'o.joblib', 'sha256': '0' * 64})  # not chosen: never required
    sp_rel = 'workflow/serving/input-pins-v3.json'
    sp = {'files': {mb_dir + '/model_bundles.json': put(mb_dir + '/model_bundles.json', {'bundles': bundles})},
          'selection': {'daily': 'c::routed_context', '6h': 'c::routed_context', 'baseline': 'b'}}
    if overlap:
        sp['files'][e21 + 'spatial_evaluation_manifest.json'] = ev['manifest_sha256'] if overlap == 'same' else '0' * 64
    srec = {sp_rel: put(sp_rel, sp)}
    for u in ('daily', '6h'):
        srec['backend/s22/baseline_stats_' + u + '.npz'] = put('backend/s22/baseline_stats_' + u + '.npz', b'npz' + u.encode())
    sel13 = {'daily': {'recommended_method': 'h', 'strongest_baseline': 'bm'}, '6h': {'recommended_method': 'h6', 'strongest_baseline': 'bb'}}
    mm_bundles, vih = [], {}
    for u, s in sel13.items():
        for m in s.values():
            path = 'bundles/' + u + '/' + m + '.bin'
            vih['bundle:' + u + ':' + m] = h = put('backend/data/v2/models/' + path, m.encode())
            mm_bundles.append({'unit': u, 'method_id': m, 'path': path, 'sha256': h})
    vih['model_manifest'] = put('backend/reports/v2/models/model_manifest.json', {'bundles': mm_bundles})
    pcfg_rel, smf_rel = 'backend/config/inference_v2.json', 'backend/reports/v2/serving/serving_manifest.json'
    pcfg = put(pcfg_rel, {'trust_anchors': {'model_manifest_sha256': vih['model_manifest']}, 'expected_selection': sel13,
                          'paths': {'model_report_dir': 'reports/v2/models', 'model_data_dir': 'data/v2/models'}})
    prec = {pcfg_rel: pcfg, smf_rel: put(smf_rel, {'config_sha256': pcfg, 'verified_input_hashes': vih})}
    cat = {'source_notebook': 'backend/notebooks/14.ipynb', 'source_notebook_sha256': put('backend/notebooks/14.ipynb', b'nb14'),
           'config': 'backend/config/catalog_v3.json', 'config_sha256': put('backend/config/catalog_v3.json', b'{}'),
           'report_dir': 'backend/c14/r', 'data_dir': 'backend/c14/d',
           'manifest_sha256': put('backend/c14/r/catalog_manifest.json', {'outputs': {'report_files': {'p.csv': put('backend/c14/r/p.csv', b'p')}}})}
    drec = {'report_dir': 'backend/d23', 'files': {'backend/d23/evaluation_2026_manifest.json': put(
        'backend/d23/evaluation_2026_manifest.json', {'report_files': {'metrics.csv': put('backend/d23/metrics.csv', b'd')}})}}
    cfg = {'components': {'spatial_runtime': {'pins': sp_rel}, 'province_runtime': {'config': pcfg_rel},
                          'evaluation': {'manifest': 'reports/v3/spatial_evaluation/spatial_evaluation_manifest.json',
                                         'metrics': 'reports/v3/spatial_evaluation/metrics_by_group.csv'},
                          'diagnostics_2026': {'manifest': 'evaluation_2026_manifest.json', 'metrics': 'metrics.csv'}}}
    recs = {'catalog': ('workflow/c.json', cat), 'evaluation': ('workflow/e.json', ev), 'spatial_runtime': ('workflow/s.json', {'files': srec}),
            'province_runtime': ('workflow/p.json', {'files': prec}), 'diagnostics_2026': ('workflow/d.json', drec)}
    files = {rel: put(rel, obj) for rel, obj in recs.values()}
    files[S.CONFIG_REL] = put(S.CONFIG_REL, cfg)
    put(S.LOCK_REL, {'files': files, 'components': {n: rel for n, (rel, _) in recs.items()}})
    return mb_dir


def test_smoke_consumed_set_resolves_unit_dirs_chosen_bundles_and_root_anchor(tmp_path):
    S = _smoke()
    mb_dir = _tiny_consumed_repo(tmp_path, S)
    pins = S.consumed_pins(tmp_path)
    assert S.coverage_problems(pins) == []
    spatial = sorted(r for r, (_, o) in pins.items() if 'spatial_chosen_bundle' in o)
    assert spatial == sorted(mb_dir + '/models/' + u + '/' + f for u in ('daily', '6h') for f in ('c__core.joblib', 'c__context.joblib'))
    assert all(pins[r][0] == hashlib.sha256((tmp_path / r).read_bytes()).hexdigest() for r in spatial)
    assert not any(r.endswith('o.joblib') for r in pins)
    assert sorted(r for r, (_, o) in pins.items() if 'province_chosen_bundle' in o) == sorted(
        'backend/data/v2/models/bundles/' + p for p in ('daily/h.bin', 'daily/bm.bin', '6h/h6.bin', '6h/bb.bin'))
    assert pins[S.LOCK_REL] == (hashlib.sha256((tmp_path / S.LOCK_REL).read_bytes()).hexdigest(), (S.ROOT_ANCHOR,))
    no_bundles = {r: v for r, v in pins.items() if not {'spatial_chosen_bundle', 'province_chosen_bundle'} & set(v[1])}
    assert any(p.startswith('spatial_chosen_bundle') for p in S.coverage_problems(no_bundles))
    assert any(p.startswith('province_chosen_bundle') for p in S.coverage_problems(no_bundles))
    assert len(S.coverage_problems({})) == len(S.REQUIRED_EXACT) + len(S.REQUIRED_AT_LEAST)


def test_smoke_consumed_set_counts_every_membership_of_a_file_in_two_chains(tmp_path):
    """final019b regression: the 21 manifest is pinned first via the 22 serving pins and again as the evaluation record; it is one physical file
    that must satisfy both categories (first-origin-only accounting reported 'evaluation_record: 0 < 1')."""
    S = _smoke()
    _tiny_consumed_repo(tmp_path, S, overlap='same')
    m21 = 'backend/e21/reports/v3/spatial_evaluation/spatial_evaluation_manifest.json'
    pins = S.consumed_pins(tmp_path)
    assert pins[m21] == (hashlib.sha256((tmp_path / m21).read_bytes()).hexdigest(), ('spatial_serving_pins', 'evaluation_record'))
    assert list(pins).count(m21) == 1 and S.coverage_problems(pins) == []
    first_only = {r: (s, o[:1]) for r, (s, o) in pins.items()}  # the old setdefault accounting
    assert 'evaluation_record: 0 < 1' in S.coverage_problems(first_only)
    without_eval = {r: (s, tuple(x for x in o if x != 'evaluation_record')) for r, (s, o) in pins.items()}
    assert S.coverage_problems(without_eval) == ['evaluation_record: 0 < 1']
    no_metrics = {r: v for r, v in pins.items() if 'evaluation_manifest' not in v[1]}
    assert S.coverage_problems(no_metrics) == ['evaluation_manifest: 0 != 1']
    (tmp_path / m21).unlink()
    with pytest.raises(S.ConsumedSetError):
        S.consumed_pins(tmp_path)


def test_smoke_consumed_set_refuses_one_file_pinned_with_two_hashes(tmp_path):
    S = _smoke()
    _tiny_consumed_repo(tmp_path, S, overlap='conflict')
    with pytest.raises(S.ConsumedSetError, match='conflicting trusted hashes'):
        S.consumed_pins(tmp_path)


@pytest.mark.parametrize('case', ['missing_22_bundle', 'missing_13_bundle', 'tampered_model_bundles', 'tampered_record'])
def test_smoke_consumed_set_refuses_missing_bundles_and_broken_chains(tmp_path, case):
    S = _smoke()
    mb_dir = _tiny_consumed_repo(tmp_path, S)
    if case == 'missing_22_bundle':
        (tmp_path / mb_dir / 'models/6h/c__context.joblib').unlink()
    elif case == 'missing_13_bundle':
        (tmp_path / 'backend/data/v2/models/bundles/daily/bm.bin').unlink()
    elif case == 'tampered_model_bundles':
        (tmp_path / mb_dir / 'model_bundles.json').write_text('{"bundles": []}', 'utf-8')
    else:
        (tmp_path / 'workflow/s.json').write_text('{"files": {}}', 'utf-8')
    with pytest.raises(S.ConsumedSetError):
        S.consumed_pins(tmp_path)


def test_api_sources_do_not_import_ai_team():
    for p in list((BACKEND / 'api').glob('*.py')) + [BACKEND / 'scripts/run_api_server.py', BACKEND / 'scripts/smoke_api_live.py']:
        assert '.ai-team' not in p.read_text('utf-8'), p


# ---------- actual accepted bundles (opt-in; requires the manager-filled pins and the ignored accepted data) ----------
@pytest.mark.skipif(os.environ.get('ROADAWARE_API_ACTUAL') != '1', reason='set ROADAWARE_API_ACTUAL=1 after the manager filled the notebook-24/config pins')
def test_actual_runtime_ready_parity_and_thresholds():
    rt = RT.load_runtime()
    assert rt.ready, rt.public_components()
    srec = json.loads((REPO / 'workflow/serving/accepted-runtime-v3.json').read_text('utf-8'))
    fx = json.loads((REPO / srec['data_dir'] / 'prediction_fixtures.json').read_text('utf-8'))
    for u in ('daily', '6h'):
        saved = next(x for x in fx[u]['responses'] if x['which'] == 'selected')
        assert rt.spatial_predict({'unit': u, 'requests': saved['requests']}, 'selected')['results'] == saved['response']['results']
    erec = json.loads((REPO / 'workflow/evaluation/accepted-runtime-v3.json').read_text('utf-8'))
    man21 = json.loads((REPO / erec['root'] / 'reports/v3/spatial_evaluation/spatial_evaluation_manifest.json').read_text('utf-8'))
    md = rt.metadata()
    for u in ('daily', '6h'):
        p = REPO / erec['root'] / 'reports/v3/spatial_evaluation' / ('colour_contract_' + u + '.json')
        assert RT.sha256_file(p) == man21['report_files'][p.name]
        assert md['spatial_runtime']['units'][u]['colour_cutoffs'] == json.loads(p.read_text('utf-8'))['raw_cutoffs']
    assert md['geometry']['segments'] == 3105 and md['production_ready'] is False
    assert rt.diag23['counts']['eligible_raw_records'] == 4336 and math.isfinite(rt.diag23['overall_metrics'][0]['mae'])
