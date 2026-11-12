"""Tests for notebook 22 (verified spatial inference + robustness contract). The five '# FUNCTIONS' cells of the assembled source notebook are
executed (never pipeline cells). Pure-logic tests use tiny fixtures; integration tests use the ACCEPTED pinned artifacts when present (skipped
otherwise) and never write outside pytest tmp dirs. Run from the repository root (after assembling notebook 22):
    .venv/bin/python -m pytest backend/tests/test_spatial_inference_notebook.py -q
"""
import copy
import importlib.util
import json
import math
import os
import types
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
NB22 = BACKEND / 'notebooks' / '22_spatial_inference_contract.ipynb'
CFG = json.loads((BACKEND / 'config' / 'spatial_inference_v3.json').read_text('utf-8'))
PINS_PATH = BACKEND / CFG['pins']['path']


def code_cells(p):
    return [''.join(c['source']) for c in json.loads(Path(p).read_text('utf-8'))['cells'] if c['cell_type'] == 'code']


def exec_functions(p, n):
    cells = [s for s in code_cells(p) if s.lstrip().startswith('# FUNCTIONS')]
    assert len(cells) == n
    ns = {}
    for i, s in enumerate(cells):
        exec(compile(s, f'{Path(p).stem}:FUNCTIONS[{i}]', 'exec'), ns)
    return ns


@pytest.fixture(scope='module')
def F():
    return exec_functions(NB22, 5)


@pytest.fixture(scope='module')
def N19():
    return exec_functions(BACKEND / 'notebooks' / '19_spatial_count_preparation.ipynb', 6)


@pytest.fixture(scope='module')
def N20():
    return exec_functions(BACKEND / 'notebooks' / '20_spatial_count_experiments.ipynb', 6)


def load_module(name, rel):
    spec = importlib.util.spec_from_file_location(name, BACKEND / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_source_notebook_unexecuted_five_functions_no_handoff_reference():
    nb = json.loads(NB22.read_text('utf-8'))
    assert all(not c.get('outputs') and c.get('execution_count') is None for c in nb['cells'] if c['cell_type'] == 'code')
    assert not any('.ai-team' in s for s in code_cells(NB22))
    assert sum(s.lstrip().startswith('# FUNCTIONS') for s in code_cells(NB22)) == 5


def test_strict_json(F):
    assert F['jsonable']({'a': np.float64('nan'), 'b': np.int64(3), 'c': [np.inf]}) == {'a': None, 'b': 3, 'c': [None]}
    with pytest.raises(ValueError):
        F['strict_dumps']({'x': float('nan')})


def test_verify_file_codes(F, tmp_path):
    p = tmp_path / 'a.bin'
    p.write_bytes(b'abc')
    good = F['sha256_file'](p)
    assert F['verify_file'](p, good, 'x') == good
    for exp, path, code in ((None, p, 'artifact_unavailable'), ('0' * 64, p, 'artifact_hash_mismatch'), (good, tmp_path / 'missing', 'artifact_missing')):
        with pytest.raises(F['ServingError']) as e:
            F['verify_file'](path, exp, 'x')
        assert e.value.code == code and F['error_family'](code) == 'unavailable'
    assert F['error_family']('unknown_segment') == 'coverage' and F['error_family']('batch_size') == 'invalid'


def test_load_functions_hash_and_subset(F, tmp_path):
    nb = {'cells': [{'cell_type': 'code', 'id': 'a', 'source': '# FUNCTIONS (1/2)\nA = 1\n'}, {'cell_type': 'code', 'id': 'b', 'source': '# FUNCTIONS (2/2)\nimport no_such_module_xyz\n'},
                    {'cell_type': 'code', 'id': 'c', 'source': 'PIPELINE = 1\n'}], 'metadata': {}, 'nbformat': 4, 'nbformat_minor': 5}
    p = tmp_path / 'n.ipynb'
    p.write_text(json.dumps(nb), 'utf-8')
    sha = F['sha256_bytes'](('# FUNCTIONS (1/2)\nA = 1\n' + '# FUNCTIONS (2/2)\nimport no_such_module_xyz\n').encode('utf-8'))
    ns, got = F['load_functions'](p, 2, '', sha, None, 'fixture', [0])  # hash covers both; only cell 0 executed
    assert got == sha and ns['A'] == 1 and 'PIPELINE' not in ns
    with pytest.raises(F['ServingError']) as e:
        F['load_functions'](p, 2, '\n\n', sha, None, 'fixture', [0])
    assert e.value.code == 'artifact_hash_mismatch'
    with pytest.raises(F['ServingError']):
        F['load_functions'](p, 2, '', sha, {'0:a': '0' * 64}, 'fixture', [0])


def test_output_guards_new_root_overlap_and_symlink(F, tmp_path):
    b = tmp_path / 'backend'
    (b / 'reports' / 'v3' / 'spatial_preparation').mkdir(parents=True)
    out = b / 'rerun-spatial-serving-x'
    assert F['check_outputs'](F['output_paths'](out, CFG), b, CFG)
    with pytest.raises(F['ServingError']):  # output root == a protected tree
        F['check_outputs'](F['output_paths'](b, dict(CFG, outputs={'report_dir': 'reports/v3/spatial_preparation/x', 'data_dir': 'data/v3/spatial_serving'})), b, CFG)
    (b / 'alias').symlink_to(b / 'reports' / 'v3' / 'spatial_preparation')
    with pytest.raises(F['ServingError']):  # symlink alias into a protected dir
        F['check_outputs'](F['output_paths'](b, dict(CFG, outputs={'report_dir': 'alias/r', 'data_dir': 'data/v3/spatial_serving'})), b, CFG)
    (out / CFG['outputs']['report_dir']).mkdir(parents=True)
    with pytest.raises(F['ServingError']):  # reused root
        F['check_outputs'](F['output_paths'](out, CFG), b, CFG)


def fake_service(F, N19, N20):
    """Minimal available service for the request contract (validation happens before any feature work)."""
    blocks = ['00-06', '06-12', '12-18', '18-24']
    ctx = {'settings': {'max_rows': 100000, 'research_start': '2021-01-01', 'research_end': '2027-12-31', 'time_blocks': blocks},
           'seg': pd.DataFrame({'x': [1.0, 2.0, 3.0, 4.0]}, index=pd.Index(['s1', 's2', 's3', 's4'], name='segment_id')), 'unsupported': {'u1'}}
    c20 = json.loads((BACKEND / 'config' / 'spatial_experiment_v3.json').read_text('utf-8'))
    meta = dict(max_batch=128, supported_target_start='2024-01-01', supported_target_end='2027-12-31', observed_diagnostic_end='2025-12-31',
                artifact_kind='benchmark', fit_issue_local='2023-12-31 18:00:00', training_label_cutoff_local='2023-12-01 18:00:00')
    return types.MappingProxyType({'status': 'available', 'error': None, 'ctx': ctx, 'H': {'19': N19, '20': N20}, 'cfg20': c20, 'meta': meta,
                                   'issue': pd.Timestamp('2023-12-31 18:00'), 'cutoff': pd.Timestamp('2023-12-01 18:00'), 'units': {}, 'cfg': CFG})


@pytest.mark.parametrize('unit,reqs,code', [
    ('hourly', [{'segment_id': 's1', 'target_date': '2024-01-01'}], 'invalid_unit'),
    (True, [{'segment_id': 's1', 'target_date': '2024-01-01'}], 'invalid_unit'),
    ('daily', {'segment_id': 's1', 'target_date': '2024-01-01'}, 'invalid_request'),
    ('daily', [], 'batch_size'),
    ('daily', [{'segment_id': 's1', 'target_date': '2024-01-01'}] * 129, 'batch_size'),
    ('daily', [{'segment_id': 's1', 'target_date': '2024-01-01', 'time_block': '00-06'}], 'invalid_fields'),
    ('6h', [{'segment_id': 's1', 'target_date': '2024-01-01'}], 'invalid_fields'),
    ('daily', [{'segment_id': 's1', 'target_date': '2024-01-01', 'path': '/tmp/x'}], 'invalid_fields'),
    ('daily', [{'segment_id': True, 'target_date': '2024-01-01'}], 'invalid_value'),
    ('daily', [{'segment_id': 's1', 'target_date': 20240101}], 'invalid_value'),
    ('daily', [{'segment_id': 's1 ', 'target_date': '2024-01-01'}], 'invalid_value'),
    ('daily', [{'segment_id': 's1', 'target_date': '2024-02-30'}], 'invalid_date'),
    ('6h', [{'segment_id': 's1', 'target_date': '2024-01-01', 'time_block': '06-13'}], 'invalid_time_block'),
    ('daily', [{'segment_id': 's1', 'target_date': '2024-01-01'}, {'segment_id': 's1', 'target_date': '2024-01-01'}], 'duplicate_keys'),
    ('daily', [{'segment_id': 's1', 'target_date': '2023-12-31'}], 'date_before_artifact_asof'),
    ('daily', [{'segment_id': 's1', 'target_date': '2021-03-01'}], 'date_before_artifact_asof'),
    ('daily', [{'segment_id': 's1', 'target_date': '2028-01-01'}], 'date_out_of_range'),
    ('daily', [{'segment_id': 'nope', 'target_date': '2024-01-01'}], 'unknown_segment'),
    ('daily', [{'segment_id': 'u1', 'target_date': '2024-01-01'}], 'unsupported_segment'),
])
def test_request_contract_codes(F, N19, N20, unit, reqs, code):
    svc = fake_service(F, N19, N20)
    with pytest.raises(F['ServingError']) as e:
        F['validate_public'](svc, unit, reqs)
    assert e.value.code == code
    r = F['predict_batch'](svc, unit, reqs)
    assert r['ok'] is False and r['error']['code'] == code and r['production_ready'] is False
    json.dumps(r, allow_nan=False)


def test_serving_error_rows_never_truth_test_arrays(F):
    E = F['ServingError']
    assert E('x', 'm', np.flatnonzero(np.array([True, False, True]))).rows == [0, 2]  # 2+ ndarray positions (was ambiguous-truth ValueError)
    assert E('x', 'm', np.array([0])).rows == [0]  # lone row 0 (was dropped as falsy)
    assert E('x', 'm', np.array([True, False, False])).rows == [0]  # boolean mask
    assert E('x', 'm', pd.Index([3, 1])).rows == [3, 1] and E('x', 'm', [5]).rows == [5] and E('x', 'm').rows == [] and E('x', 'm', np.array([], np.int64)).rows == []
    assert E('x', 'm', np.arange(50)).rows == list(range(10))
    assert all(type(r) is int for r in E('x', 'm', np.array([4, 7], np.int64)).rows)


def _q(unit, seg='s1', d='2024-01-01', **kw):
    return dict({'segment_id': seg, 'target_date': d, **({'time_block': '00-06'} if unit == '6h' else {})}, **kw)


MULTI = [  # (requests builder, expected code, expected family, expected rows): good and bad rows mixed, incl. row 0 and 2+ bad rows
    (lambda u: [_q(u, 's1', '2023-12-31'), _q(u, 's2'), _q(u, 's3', '2023-06-01'), _q(u, 's4')], 'date_before_artifact_asof', 'invalid', [0, 2]),
    (lambda u: [_q(u, 's1', '2022-05-05'), _q(u, 's2')], 'date_before_artifact_asof', 'invalid', [0]),
    (lambda u: [_q(u, 's1'), _q(u, 's2', '2023-12-31')], 'date_before_artifact_asof', 'invalid', [1]),
    (lambda u: [_q(u, 's1'), _q(u, 's2', '2028-01-01'), _q(u, 's3'), _q(u, 's4', '2030-06-01')], 'date_out_of_range', 'invalid', [1, 3]),
    (lambda u: [_q(u, 's1', '2020-01-01'), _q(u, 's2', '2029-01-01')], 'date_out_of_range', 'invalid', [0, 1]),
    (lambda u: [_q(u, 'nope-a'), _q(u, 'nope-b'), _q(u, 's3')], 'unknown_segment', 'coverage', [0, 1]),
    (lambda u: [_q(u, 'nope'), _q(u, 'u1'), _q(u, 's3')], 'unsupported_segment', 'coverage', [0, 1]),
    (lambda u: [_q(u, 's1', '2024-02-30'), _q(u, 's2'), _q(u, 's3', '2024-3-01')], 'invalid_date', 'invalid', [0, 2]),
    (lambda u: [_q(u, 'nope'), _q(u, 's2', '2024-13-01')], 'invalid_date', 'invalid', [1]),  # family order: invalid_date before coverage
    (lambda u: [_q(u, ' s1'), _q(u, 's2', target_date=20240101), _q(u, 's3')], 'invalid_value', 'invalid', [0, 1]),
    (lambda u: [_q(u, 's1'), _q(u, 's2'), _q(u, 's1'), _q(u, 's2')], 'duplicate_keys', 'invalid', [2, 3]),
    (lambda u: [_q(u, 's1', path='x'), _q(u, 's2'), _q(u, 's3', extra=1)], 'invalid_fields', 'invalid', [0, 2]),
    (lambda u: [_q(u, 's1'), 'not-an-object', 7], 'invalid_request', 'invalid', [1, 2]),
]


@pytest.mark.parametrize('unit', ['daily', '6h'])
@pytest.mark.parametrize('case', range(len(MULTI)))
def test_multi_row_invalid_batches_atomic_with_exact_rows(F, N19, N20, unit, case):
    build, code, fam, rows = MULTI[case]
    svc = fake_service(F, N19, N20)
    with pytest.raises(F['ServingError']) as e:
        F['validate_public'](svc, unit, build(unit))
    assert e.value.code == code and e.value.rows == rows
    for fn in ('predict_batch', 'predict_baseline_batch'):
        r = F[fn](svc, unit, build(unit))
        assert r['ok'] is False and 'results' not in r, r  # whole batch refused, no partial predictions
        assert (r['error']['code'], r['error']['family'], r['error']['rows']) == (code, fam, rows), r['error']
        json.dumps(r, allow_nan=False)


def test_multi_row_6h_block_families(F, N19, N20):
    svc = fake_service(F, N19, N20)
    for reqs, code, rows in (([_q('6h', 's1', time_block='24-30'), _q('6h', 's2'), _q('6h', 's3', time_block='06-13')], 'invalid_time_block', [0, 2]),
                             ([_q('6h', 's1', time_block='24-30'), _q('6h', 's2', time_block='')], 'invalid_value', [1])):
        for fn in ('predict_batch', 'predict_baseline_batch'):
            r = F[fn](svc, '6h', reqs)
            assert r['ok'] is False and 'results' not in r and r['error']['code'] == code and r['error']['rows'] == rows


def test_valid_request_passes_and_first_supported_date_obeys_latency(F, N19, N20):
    svc = fake_service(F, N19, N20)
    R = F['validate_public'](svc, '6h', [{'segment_id': 's2', 'target_date': '2024-01-01', 'time_block': '18-24'}, {'segment_id': 's1', 'target_date': '2027-12-31', 'time_block': '00-06'}])
    assert R['segment_id'].tolist() == ['s2', 's1']  # order preserved


def test_unavailable_service_never_answers(F):
    svc = F['unavailable_service']('artifact_hash_mismatch', 'fixture', 0.0)
    for fn in ('predict_batch', 'predict_baseline_batch'):
        r = F[fn](svc, 'daily', [{'segment_id': 's1', 'target_date': '2024-01-01'}])
        assert r['ok'] is False and r['error']['code'] == 'artifact_unavailable' and 'results' not in r
    h = F['health'](svc)
    assert h['startup_status'] == 'unavailable' and h['production_ready'] is False and h['research_ready'] is False
    assert F['coverage'](svc, ['s1'])['error']['code'] == 'artifact_unavailable'


def test_tampered_bundle_refused_before_joblib_load(N20, tmp_path, monkeypatch):
    import joblib
    from sklearn.dummy import DummyRegressor
    est = DummyRegressor().fit([[0.0], [1.0]], [0.0, 1.0])
    meta = N20['save_bundle'](est, tmp_path / 'm.joblib', {'unit': 'daily'})
    b = bytearray((tmp_path / 'm.joblib').read_bytes())
    b[len(b) // 2] ^= 0xFF
    (tmp_path / 'm.joblib').write_bytes(bytes(b))
    called = []
    monkeypatch.setattr(joblib, 'load', lambda *a, **k: called.append(1))
    with pytest.raises(Exception):
        N20['load_bundle'](tmp_path / 'm.joblib', meta['sha256'])
    assert not called


def test_runner_refusals(tmp_path):
    R = load_module('run_spatial_inference', 'scripts/run_spatial_inference.py')
    assert R.refusal(BACKEND / 'rerun-spatial-serving-pytest-never-created') is None
    assert 'must start with' in R.refusal(BACKEND / 'rerun-spatial-eval-x')
    assert 'directly inside' in R.refusal(tmp_path / 'rerun-spatial-serving-x')
    assert 'already exists' in R.refusal(BACKEND / 'notebooks')
    env = R.build_env(tmp_path / 'o', base={'ROADAWARE_EVIL': '1', 'PATH': '/bin'})
    assert 'ROADAWARE_EVIL' not in env and env['OMP_NUM_THREADS'] == '2'


# ---------- integration with the ACCEPTED pinned artifacts (skipped when absent) ----------
def _have_accepted():
    if not PINS_PATH.is_file():
        return False
    pins = json.loads(PINS_PATH.read_text('utf-8'))
    return all((REPO / k).is_file() for k in pins['files']) and (BACKEND / CFG['inputs']['prepared_data_dir'] / 'counts_6h.csv.gz').is_file()


accepted = pytest.mark.skipif(not _have_accepted(), reason='accepted 19/20/21 artifacts not present')


@pytest.fixture(scope='module')
def LIVE(F, tmp_path_factory):
    pins = json.loads(PINS_PATH.read_text('utf-8'))
    docs, _ = F['verify_chain'](BACKEND, CFG, pins)
    H = F['load_helpers'](BACKEND, CFG, pins, docs)
    H['cfg20'] = docs['cfg20']
    n19, prep = H['19'], docs['paths']['prepared']
    ctx = n19['load_prepared_context'](prep, docs['man19']['data_files_gitignored'])
    axj = json.loads((prep / 'population_axes.json').read_text('utf-8'))
    ax = n19['population_axes'](axj['segments'], axj['dates'][0], axj['dates'][-1], axj['blocks'])
    d = tmp_path_factory.mktemp('serving')
    bf = {}
    for u, cols in (('daily', ['segment_id', 'target_date']), ('6h', ['segment_id', 'target_date', 'time_block'])):
        sp = n19['sparse_index'](ax, u, n19['read_numeric_csv'](prep / ('counts_' + u + '.csv.gz'), cols))
        st, _ = F['build_baseline_stats'](H, CFG, ctx, ax, sp, u, pins['selection']['baseline'])
        bf[u] = (d / (u + '.npz'), F['save_baseline_stats'](d / (u + '.npz'), st))
    svc = F['load_service'](BACKEND, CFG, pins, bf)
    return {'svc': svc, 'pins': pins, 'docs': docs, 'ax': ax, 'bf': bf, 'dir': d}


@accepted
def test_live_service_health_and_metadata(F, LIVE):
    svc = LIVE['svc']
    assert svc['status'] == 'available', svc['error']
    h = F['health'](svc)
    assert h['startup_status'] == 'available' and h['production_ready'] is False
    m = F['metadata'](svc)
    assert m['units']['daily']['method'] == 'hgb_poisson_fixed::routed_context' and m['units']['6h']['baseline'] == 'segment_mean_k365'
    assert m['supported_target_start'] == '2024-01-01' and m['production_ready'] is False
    json.dumps(m, allow_nan=False)
    assert all(t['pass'] and t['max_abs_error'] <= 1e-12 for s in svc['units'].values() for t in s['selftest'].values())
    with pytest.raises(TypeError):
        svc['units']['daily']['est']['core'] = None  # immutable mappings
    with pytest.raises(ValueError):
        svc['units']['daily']['baseline_table'][0, 0] = 1.0


@accepted
@pytest.mark.parametrize('unit', ['daily', '6h'])
def test_live_parity_saved_mask_scope_and_future(F, LIVE, unit, record_property):
    """REAL saved 20 diag rows at known offsets + 2026-27 research rows through the PUBLIC API. Component expectations come from the SAVED 20
    context mask at each offset (the actual 2024/25 scope is reported, e.g. core-only when no observed weather/AADT context exists); context
    routing itself is covered by the separate, clearly synthetic test below."""
    svc, docs, ax = LIVE['svc'], LIVE['docs'], LIVE['ax']
    S = svc['units'][unit]
    sel = F['open_saved'](docs, unit, S['method'])
    base = F['open_saved'](docs, unit, S['baseline'])
    mask = F['open_saved'](docs, unit, 'context_mask')
    nb = 4 if unit == '6h' else 1
    n_ctx = int(sum(int((np.asarray(mask[i:i + (1 << 22)]) == 1).sum()) for i in range(0, len(mask), 1 << 22)))
    scope = F['routing_scope'](n_ctx, len(mask))
    record_property('observed_routing_scope_' + unit, scope)
    record_property('saved_mask_context_rows_' + unit, n_ctx)
    print(unit, 'actual saved 2024/25 routing scope:', scope, '| context rows', n_ctx, 'of', len(mask))
    head = np.asarray(mask[:200000])
    offs = sorted(set(np.flatnonzero(head == 1)[:40].tolist()) | set(np.flatnonzero(head == 0)[:40].tolist())
                  | set(np.linspace(0, len(mask) - 1, 40).astype(np.int64).tolist()))  # unique, spread over the full window
    assert len(offs) <= 128
    d0 = ax['date_pos']['2024-01-01']
    keys = svc['H']['19']['keys_from_positions'](ax, unit, np.asarray(offs) + d0 * len(ax['segments']) * nb)
    reqs = keys.to_dict('records')
    rs, rb = F['predict_batch'](svc, unit, reqs), F['predict_baseline_batch'](svc, unit, reqs)
    assert rs['ok'] and rb['ok']
    err_s = max(abs(r['expected_recorded_count'] - float(sel[o])) for r, o in zip(rs['results'], offs))
    err_b = max(abs(r['expected_recorded_count'] - float(base[o])) for r, o in zip(rb['results'], offs))
    record_property('sampled_max_abs_error_' + unit, max(err_s, err_b))
    assert err_s <= 1e-12 and err_b <= 1e-12
    want = ['context' if int(mask[o]) == 1 else 'core' for o in offs]
    assert [r['component_used'] for r in rs['results']] == want
    for r, w in zip(rs['results'], want):
        assert (r['routing_reason'] == 'context_complete') if w == 'context' else r['routing_reason'].startswith('core_fallback_missing_context:')
    if n_ctx == 0:  # actual observed scope: core fallback only; nothing in the real data exercised the context component
        assert set(want) == {'core'}
    assert all(r['component_used'] == 'baseline' and r['routing_reason'] == 'baseline_has_no_routing' for r in rb['results'])
    assert [(r['segment_id'], r['target_date']) for r in rs['results']] == [(q['segment_id'], q['target_date']) for q in reqs]
    assert set(rs['results'][0]) == set(rb['results'][0])  # same keys for selected and baseline
    fut = [dict(reqs[0], target_date='2027-06-15'), dict(reqs[1], target_date='2026-02-01')]
    rf = F['predict_batch'](svc, unit, fut)
    assert rf['ok'] and all(r['research_scenario'] and r['data_period'].startswith('research_scenario') for r in rf['results'])
    assert all(r['colour'] in ('base', 'yellow', 'orange', 'red') for r in rf['results'])
    json.dumps([rs, rb, rf], allow_nan=False)


@accepted
@pytest.mark.parametrize('unit', ['daily', '6h'])
def test_live_SYNTHETIC_routing_fixture_not_observed_evidence(F, LIVE, unit):
    """CLEARLY SYNTHETIC: routed trigger columns overwritten in a service COPY (real 2024/25 has no observed context). Exercises context-complete,
    core-fallback and mixed routing through the runtime path with the pinned schema/bundles. Never evidence about observed 2024/25 data."""
    svc = LIVE['svc']
    real_build = svc['H']['19']['build_feature_rows']
    rows, s = F['synthetic_routing_probe'](svc, unit)
    assert svc['H']['19']['build_feature_rows'] is real_build  # the trusted service is untouched
    assert s['evidence'].startswith('SYNTHETIC_FIXTURE') and 'NOT_observed' in s['evidence'] and all(r['evidence'] == s['evidence'] for r in rows)
    trig = list(LIVE['docs']['cfg20']['candidates']['routed_trigger_columns'][unit])  # from the pinned 20 config, not the service copy
    assert list(svc['units'][unit]['trigger']) == trig
    kinds = [r['kind'] for r in rows]
    assert {'context_complete', 'all_missing'} <= set(kinds) and any(k.startswith('missing_') for k in kinds)  # mixed batch
    want_reason = {'context_complete': 'context_complete', 'missing_first_trigger': 'core_fallback_missing_context:' + trig[0],
                   'missing_last_trigger': 'core_fallback_missing_context:' + trig[-1], 'all_missing': 'core_fallback_missing_context:' + ','.join(trig)}
    for r in rows:
        ctx = r['kind'] == 'context_complete'
        assert r['component_used'] == ('context' if ctx else 'core') and r['routing_reason'] == want_reason[r['kind']]
        assert abs(r['expected_recorded_count'] - (r['context_prediction'] if ctx else r['core_prediction'])) <= 1e-12
        assert math.isfinite(r['core_prediction']) and math.isfinite(r['context_prediction']) and r['core_prediction'] >= 0 and r['context_prediction'] >= 0
        assert r['baseline_component'] == 'baseline' and r['baseline_reason'] == 'baseline_has_no_routing' and r['baseline_unchanged_by_context']
        assert r['passed']
    assert s['schema_and_order_equal_pinned_bundle_columns'] and s['context_differs_from_core_on_context_rows']
    assert s['context_rows'] > 0 and s['core_rows'] > 0 and s['all_passed']


@accepted
def test_live_robustness_cases_all_pass(F, LIVE):
    for u in ('daily', '6h'):
        rows = F['run_cases'](F['robustness_cases'](LIVE['svc'], u))
        assert all(r['passed'] for r in rows), [r for r in rows if not r['passed']]
        multi = [r for r in rows if r['case'].startswith('multi_')]
        assert any('_selected_' in r['case'] for r in multi) and any('_baseline_' in r['case'] for r in multi)
        assert any(r['expected_rows'] == '[0, 2]' and r['got_rows'] == '[0, 2]' for r in multi)  # 2+ rows incl. row 0
        assert all(r['family'] in ('invalid', 'coverage') for r in multi)


@accepted
def test_live_tampered_pins_and_baseline_unavailable(F, LIVE):
    pins = copy.deepcopy(LIVE['pins'])
    k = next(x for x in pins['files'] if x.endswith('model_bundles.json'))
    pins['files'][k] = '0' * 64
    s = F['load_service'](BACKEND, CFG, pins, LIVE['bf'], selftest=False)
    assert s['status'] == 'unavailable' and s['error']['code'] == 'artifact_hash_mismatch'
    s = F['load_service'](BACKEND, CFG, LIVE['pins'], {u: (p, '0' * 64) for u, (p, _) in LIVE['bf'].items()}, selftest=False)
    assert s['status'] == 'unavailable' and s['error']['code'] == 'artifact_hash_mismatch'
    r = F['predict_batch'](s, 'daily', [{'segment_id': LIVE['ax']['segments'][0], 'target_date': '2024-01-01'}])
    assert r['ok'] is False and r['error']['code'] == 'artifact_unavailable'


@accepted
def test_live_csv_reload_parity(F, LIVE, tmp_path):
    svc = LIVE['svc']
    seg = LIVE['ax']['segments'][:5]
    r = F['predict_batch'](svc, 'daily', [{'segment_id': s, 'target_date': '2025-07-01'} for s in seg])
    df = pd.DataFrame([{k: v for k, v in x.items() if k != 'source_availability'} for x in r['results']]).assign(which='selected', bank_calendar='x')
    ok, _ = F['csv_reload_parity'](df, tmp_path / 'r.csv', svc['H'])
    assert ok
