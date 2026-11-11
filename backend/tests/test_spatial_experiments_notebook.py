"""Tests for V3 notebook 20 (spatial recorded-count experiments) and its runner. No network, no kernel.

The notebook's six '# FUNCTIONS' cells are executed (never pipeline cells); the accepted notebook-19 FUNCTIONS are bound through notebook 20's
own hash-verified loader against the manager pins, so the logic under test is the logic the notebook runs. Tiny hand-computed fixtures check
the exact formulas; tests that need the ignored prepared data skip when it is absent. Run from the repository root:
    .venv/bin/python -m pytest backend/tests/test_spatial_experiments_notebook.py -q
"""
import copy
import importlib.util
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
NB20 = BACKEND / 'notebooks' / '20_spatial_count_experiments.ipynb'
NB19 = BACKEND / 'notebooks' / '19_spatial_count_preparation.ipynb'
RUNNER = BACKEND / 'scripts' / 'run_spatial_experiments.py'
CFG = json.loads((BACKEND / 'config' / 'spatial_experiment_v3.json').read_text('utf-8'))
PINS = json.loads((REPO / 'workflow' / 'spatial' / 'experiment-input-pins-v3.json').read_text('utf-8'))
DD19 = BACKEND / CFG['inputs']['prepared_data_dir']
BLOCKS = ['00-06', '06-12', '12-18', '18-24']


def code_cells(nb):
    d = json.loads(nb.read_text('utf-8'))
    return [''.join(c['source']) if isinstance(c['source'], list) else c['source'] for c in d['cells'] if c['cell_type'] == 'code']


@pytest.fixture(scope='module')
def f():
    ns = {}
    cells = [s for s in code_cells(NB20) if s.lstrip().startswith('# FUNCTIONS')]
    assert len(cells) == 6
    for i, s in enumerate(cells):
        exec(compile(s, f'{NB20.stem}:FUNCTIONS[{i}]', 'exec'), ns)
    _, sha, _ = ns['load_nb19_functions'](NB19, PINS)
    assert sha == PINS['notebook19_functions_sha256']
    return ns


@pytest.fixture(scope='module')
def runner():
    spec = importlib.util.spec_from_file_location('run_spatial_experiments', RUNNER)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def axis(f, segs, start, end):
    return f['H19']['population_axes'](segs, start, end, BLOCKS)


def sparse(f, ax, unit, rows):
    cols = ['segment_id', 'target_date'] + (['time_block'] if unit == '6h' else [])
    df = pd.DataFrame(rows, columns=cols + ['y_count']) if rows else pd.DataFrame({c: pd.Series([], dtype=object) for c in cols}).assign(y_count=pd.Series([], dtype=np.int64))
    return f['H19']['sparse_index'](ax, unit, df)


def fake_ctx(lengths_m, routes):
    seg = pd.DataFrame({'segment_id': list(lengths_m), 'geom_length_m': [float(v) for v in lengths_m.values()], 'route_code': [routes[s] for s in lengths_m]})
    return {'seg': seg.set_index('segment_id')}


# ---------- config / lock ----------
def test_config_grid_matches_protocol_and_pins(f):
    c = {x['config_id']: x for x in CFG['candidates']['configs']}
    assert c['poisson_a1e-05']['params'] == {'alpha': 1e-05, 'max_iter': 1000, 'tol': 1e-06} and c['poisson_a1e-04']['params']['alpha'] == 1e-4
    assert c['rf_poisson_fixed']['params'] == {'criterion': 'poisson', 'n_estimators': 80, 'max_depth': 16, 'max_leaf_nodes': 128, 'min_samples_leaf': 100,
                                               'max_features': 0.8, 'n_jobs': 2, 'random_state': 42}
    assert c['hgb_poisson_fixed']['params'] == {'loss': 'poisson', 'max_iter': 160, 'max_leaf_nodes': 15, 'min_samples_leaf': 100, 'l2_regularization': 5.0,
                                                'learning_rate': 0.05, 'early_stopping': False, 'max_bins': 255, 'random_state': 42}
    assert CFG['transfer']['configs'] == ['poisson_a1e-05', 'rf_poisson_fixed', 'hgb_poisson_fixed']
    e = CFG['pins']['expect']
    assert e['notebook19_functions_sha256'] == PINS['notebook19_functions_sha256']
    assert e['preparation_manifest_sha256'] == PINS['files']['backend/reports/v3/spatial_preparation/spatial_preparation_manifest.json']
    assert 'bank_holiday_asof' not in CFG['candidates']['routed_trigger_columns']['6h']


def test_nb19_loader_refuses_tampered_pins(f, tmp_path):
    bad = copy.deepcopy(PINS)
    bad['notebook19_functions_sha256'] = '0' * 64
    with pytest.raises(f['ExperimentError']):
        f['load_nb19_functions'](NB19, bad)
    bad = copy.deepcopy(PINS)
    k = sorted(bad['notebook19_code_cells_sha256'])[0]
    bad['notebook19_code_cells_sha256'][k] = '1' * 64
    with pytest.raises(f['ExperimentError']):
        f['load_nb19_functions'](NB19, bad)
    f['load_nb19_functions'](NB19, PINS)  # rebind the verified helpers


def test_lock_immutable_and_tamper_detected(f, tmp_path):
    paths = {'data_dir': tmp_path / 'd', 'report_dir': tmp_path / 'r'}
    sha = f['write_lock']({'a': 1, 'x': float('nan')}, paths)
    assert json.loads((tmp_path / 'd' / 'experiment_lock.json').read_text())['x'] is None
    assert f['verify_lock'](paths, sha)
    with pytest.raises(f['ExperimentError']):
        f['write_lock']({'a': 2}, paths)
    (tmp_path / 'r' / 'experiment_lock.json').write_text('{"a": 3}')
    with pytest.raises(f['ExperimentError']):
        f['verify_lock'](paths, sha)


def test_strict_json(f, tmp_path):
    f['atomic_write_json'](tmp_path / 'a.json', {'v': np.float64('inf'), 'w': np.int64(3)})
    assert f['read_strict_json'](tmp_path / 'a.json') == {'v': None, 'w': 3}
    (tmp_path / 'b.json').write_text('{"v": NaN}')
    with pytest.raises(f['ExperimentError']):
        f['read_strict_json'](tmp_path / 'b.json')


# ---------- time / embargo ----------
def test_target_end_embargo_boundaries(f):
    ax = axis(f, ['s1'], '2021-01-01', '2024-01-31')
    cut = f['training_cutoff']('2022-01-01', CFG)
    assert str(cut) == '2021-12-01 18:00:00'
    Td = f['train_dates_per_block'](ax, 'daily', cut)
    T6 = f['train_dates_per_block'](ax, '6h', cut)
    assert ax['dates'][Td[0] - 1] == '2021-11-30'  # day ends 2021-12-01 00:00 <= cutoff; 2021-12-01 ends 12-02 00:00 > cutoff
    assert [ax['dates'][t - 1] for t in T6] == ['2021-12-01', '2021-12-01', '2021-12-01', '2021-11-30']  # 12-18 ends exactly at the cutoff (allowed)
    cut2 = cut - pd.Timedelta(seconds=1)
    assert ax['dates'][f['train_dates_per_block'](ax, '6h', cut2)[2] - 1] == '2021-11-30'
    rows = f['fold_rows'](CFG, {'daily': ax, '6h': ax})
    assert len(rows) == 10 and all(pd.Timestamp(r['last_train_target_end_local']) <= pd.Timestamp(r['train_cutoff_local']) for r in rows)
    assert [r['fold_id'] for r in rows[:5]] == ['2022H1', '2022H2', '2023H1', '2023H2', 'benchmark_2024']


def test_positions_compose_decompose_match_19_keys(f):
    ax = axis(f, ['a', 'b', 'c'], '2021-01-01', '2021-01-05')
    pos = np.arange(f['H19']['population_size'](ax, '6h'))
    d, s, b = f['decompose'](ax, '6h', pos)
    assert np.array_equal(f['compose'](ax, '6h', d, s, b), pos)
    k = f['H19']['keys_from_positions'](ax, '6h', pos)
    assert (k['target_date'].to_numpy() == np.asarray(ax['dates'])[d]).all() and (k['segment_id'].to_numpy() == np.asarray(ax['segments'])[s]).all()
    assert (k['time_block'].to_numpy() == np.asarray(BLOCKS)[b]).all()
    sp = sparse(f, ax, 'daily', [])
    bad = dict(sp, size=sp['size'] + 1)
    with pytest.raises(f['ExperimentError']):
        f['check_sparse'](bad, ax, 'daily')


# ---------- sampling ----------
def test_sampling_weights_strata_reproducible(f):
    segs = ['s%02d' % i for i in range(5)]
    ax = axis(f, segs, '2021-01-01', '2021-04-30')
    rows = [('s00', '2021-01-03', '06-12', 2), ('s00', '2021-02-03', '06-12', 1), ('s01', '2021-01-10', '18-24', 1), ('s04', '2021-04-20', '00-06', 5)]
    sp = sparse(f, ax, '6h', rows)
    T = np.array([60, 60, 60, 59])
    pos, y, w, s = f['sample_training'](ax, '6h', sp, T, 'F1', CFG)
    assert s['exposure_reconciles'] and s['records_reconcile'] and s['unique_positions'] and s['no_future_cells']
    assert s['training_records'] == 4 and s['positive_cells'] == 3  # the 2021-04-20 record is beyond T (never sampled)
    assert np.all(np.diff(pos) > 0)  # date -> segment -> block order
    d, si, b = f['decompose'](ax, '6h', pos)
    assert (d < T[b]).all()
    for k in range(len(segs) * 4):
        m = (si * 4 + b) == k
        npos = int((y[m] > 0).sum())
        nz = T[k % 4] - npos
        assert int((y[m] == 0).sum()) == min(32, nz)
        assert np.allclose(w[m][y[m] == 0], nz / min(32, nz)) and (w[m][y[m] > 0] == 1).all()
    assert math.isclose(w.sum(), len(segs) * T.sum()) and (w * y).sum() == 4
    p2, *_ = f['sample_training'](ax, '6h', sp, T, 'F1', CFG)
    p3, *_ = f['sample_training'](ax, '6h', sp, T, 'F2', CFG)
    assert np.array_equal(pos, p2) and not np.array_equal(pos, p3)
    assert f['stratum_seed'](42, '6h', 'F1', 's00', '00-06') != f['stratum_seed'](42, '6h', 'F1', 's00', '06-12')


def test_sampling_uniform_without_replacement(f):
    ax = axis(f, ['a'], '2021-01-01', '2021-03-31')
    sp = sparse(f, ax, 'daily', [('a', '2021-01-05', 1)])
    hits = np.zeros(64)
    for r in range(300):
        pos, y, w, _ = f['sample_training'](ax, 'daily', sp, np.array([64]), 'R' + str(r), CFG)
        d = f['decompose'](ax, 'daily', pos[y == 0])[0]
        assert len(d) == 32 and len(set(d.tolist())) == 32 and 4 not in set(d.tolist())
        hits[d] += 1
    p = np.delete(hits, 4) / 300
    assert abs(p.mean() - 32 / 63) < 1e-12 and p.min() > 0.38 and p.max() < 0.64


# ---------- baselines ----------
def baseline_setup(f):
    ax = axis(f, ['a', 'b', 'c'], '2021-01-01', '2021-01-20')
    sp = sparse(f, ax, 'daily', [('a', '2021-01-02', 1), ('a', '2021-01-09', 2), ('c', '2021-01-05', 1), ('a', '2021-01-15', 7)])
    ctx = fake_ctx({'a': 1000, 'b': 2000, 'c': 3000, 'd': 4000, 'e': 5000}, {'a': 'R1', 'b': 'R1', 'c': 'R2', 'd': 'R1', 'e': 'R3'})
    B = f['fit_baselines'](ax, 'daily', sp, np.array([10]), ctx, CFG)
    tabs, ev = f['baseline_tables'](B, ctx, ['a', 'b', 'c', 'd', 'e'], CFG)
    return B, tabs, ev


def test_baselines_exact_manual(f):
    B, t, ev = baseline_setup(f)
    assert B['training_records'] == 4 and B['denominator_cells'] == 30  # record on day 15 > T excluded; denominators = full calendar
    assert np.allclose(t['global_mean'][:3, 0], 4 / 30)
    assert np.allclose(t['global_length_rate'][:, 0], [1 / 15, 2 / 15, 3 / 15, 4 / 15, 5 / 15])
    assert np.allclose(t['route_length_rate'][:, 0], [0.1, 0.2, 0.1, 0.4, 5 / 15])  # R1 = 3/(3 km*10), R2 = 1/(3*10); R3 unseen -> global
    assert np.allclose(t['segment_mean_k30'][:, 0], [0.15, 0.15, 0.1, 0.4, 1 / 3])
    assert np.allclose(t['segment_mean_k180'][0, 0], (3 + 180 * 0.1) / 190) and np.allclose(t['segment_mean_k365'][1, 0], 365 * 0.2 / 375)
    # 2021-01-01 is a Friday: Jan 2/9 Saturdays (N=2), Monday Jan 4 (N=1)
    assert np.isclose(t['segment_weekday_k10'][0, 5, 0], (3 + 10 * 0.15) / 12) and np.isclose(t['segment_weekday_k10'][0, 0, 0], 1.5 / 11)
    assert np.isclose(t['segment_month_k30'][0, 0, 0], (3 + 30 * 0.15) / 40)
    assert np.allclose(t['recent90_segment'][:, 0], [0.3, 0.0, 0.1, 0.4, 1 / 3])  # window clipped to the 10 available days; unseen -> segment_mean_k30
    assert np.isclose(t['segment_weekday_k10'][3, 2, 0], 0.4) and np.isclose(t['segment_month_k30'][4, 6, 0], 1 / 3)
    assert ev == {'eval_segments': 5, 'unseen_segments': 2, 'unseen_routes_segments': 1, 'zero_route_rate_segments': 0, 'recent_fallback_cells': 2}
    p = f['baseline_predict'](t, np.array([0, 0]), np.array([0, 0]), np.array([5, 0]), np.array([0, 0]), ['segment_weekday_k10', 'zero'])
    assert np.allclose(p['segment_weekday_k10'], [4.5 / 12, 1.5 / 11]) and (p['zero'] == 0).all()


def test_baseline_zero_route_rate_allowed_and_6h_by_block(f):
    ax = axis(f, ['a', 'b'], '2021-01-01', '2021-01-10')
    sp = sparse(f, ax, '6h', [('a', '2021-01-02', '18-24', 3)])
    ctx = fake_ctx({'a': 1000, 'b': 1000}, {'a': 'R1', 'b': 'R2'})
    B = f['fit_baselines'](ax, '6h', sp, np.array([5, 5, 5, 4]), ctx, CFG)
    t, ev = f['baseline_tables'](B, ctx, ['a', 'b'], CFG)
    assert np.allclose(t['global_mean'][0], [0, 0, 0, 3 / 8]) and t['route_length_rate'][1].max() == 0.0 and ev['zero_route_rate_segments'] == 1
    assert np.isclose(t['segment_mean_k30'][0, 3], (3 + 30 * 3 / 4) / 34) and (t['segment_mean_k30'][1] == 0).all()


# ---------- metrics / selection / bootstrap ----------
def test_poisson_deviance_manual_zero_and_floor(f):
    d = f['poisson_deviance_terms'](np.array([0.0, 1.0, 2.0, 1.0]), np.array([0.5, 1.0, 0.0, 2.0]), 1e-12)
    assert np.allclose(d, [1.0, 0.0, 2 * (2 * math.log(2 / 1e-12) - 2 + 1e-12), 2 * (math.log(0.5) + 1)])
    assert f['poisson_deviance_terms'](np.array([0.0]), np.array([0.0]), 1e-12)[0] == pytest.approx(2e-12)
    with pytest.raises(f['ExperimentError']):
        f['poisson_deviance_terms'](np.array([-1.0]), np.array([1.0]), 1e-12)
    with pytest.raises(f['ExperimentError']):
        f['poisson_deviance_terms'](np.array([1.0]), np.array([-0.1]), 1e-12)


def test_pooled_equals_partition_accumulators(f):
    rng = np.random.default_rng(0)
    y = rng.poisson(0.3, 5000).astype(float)
    mu = rng.gamma(1.0, 0.3, 5000)
    whole = f['acc_add'](f['acc_new'](), y, mu, 1e-12)
    parts = [f['acc_add'](f['acc_new'](), y[a:a + 700], mu[a:a + 700], 1e-12) for a in range(0, 5000, 700)]
    m1, m2 = f['acc_metrics'](whole), f['acc_metrics'](f['acc_merge'](*parts))
    for k in ('mean_poisson_deviance', 'mae', 'rmse', 'bias', 'wape', 'total_pred'):
        assert m1[k] == pytest.approx(m2[k], rel=1e-12)
    assert m1['zero_cells'] + m1['nonzero_cells'] == 5000 and m1['total_actual'] == y.sum()
    assert m1['mae'] == pytest.approx(np.abs(mu - y).mean()) and m1['mean_poisson_deviance'] == pytest.approx(f['poisson_deviance_terms'](y, mu, 1e-12).mean())
    g = f['acc_add'](f['acc_new'](3), y, mu, 1e-12, np.arange(5000) % 3, 3)
    assert g['dev'].sum() == pytest.approx(whole['dev'][0]) and f['acc_metrics'](f['acc_new']())['n'] == 0
    assert f['acc_metrics'](f['acc_add'](f['acc_new'](), np.zeros(3), np.ones(3), 1e-12))['wape'] is None


def sel_inputs(dc, db, mc, mb, fold_c, fold_b, status=None):
    folds = [x['fold_id'] for x in CFG['time']['folds']]
    names = ['poisson_a1e-05::core', 'poisson_a1e-05::routed_context', 'segment_mean_k30', 'global_mean', 'zero']
    pooled = {n: {'mean_poisson_deviance': db + 1, 'mae': mb} for n in names}
    pooled['zero'] = {'mean_poisson_deviance': 0.0, 'mae': 0.0}
    pooled['segment_mean_k30'] = {'mean_poisson_deviance': db, 'mae': mb}
    pooled['poisson_a1e-05::core'] = {'mean_poisson_deviance': dc, 'mae': mc}
    pooled['poisson_a1e-05::routed_context'] = {'mean_poisson_deviance': dc, 'mae': mc}
    pf = {fo: {'poisson_a1e-05::core': {'mean_poisson_deviance': fold_c[i]}, 'segment_mean_k30': {'mean_poisson_deviance': fold_b[i]}} for i, fo in enumerate(folds)}
    st = status or {'poisson_a1e-05::core': True, 'poisson_a1e-05::routed_context': True}
    return pooled, pf, st


def test_selection_gate(f):
    s = f['select_unit'](*sel_inputs(0.98, 1.0, 1.0, 1.0, [1, 1, 1, 2], [2, 2, 2, 1]), CFG)
    assert s['strongest_baseline'] == 'segment_mean_k30'  # zero is never eligible even with deviance 0
    assert s['best_candidate'] == 'poisson_a1e-05::core' and s['recommended'] == 'candidate'  # exact tie -> core before routed_context
    assert f['select_unit'](*sel_inputs(0.995, 1.0, 1.0, 1.0, [1, 1, 1, 2], [2, 2, 2, 1]), CFG)['recommended'] == 'baseline'  # < 1 %
    assert f['select_unit'](*sel_inputs(0.9, 1.0, 1.03, 1.0, [1, 1, 1, 2], [2, 2, 2, 1]), CFG)['gates']['mae_ratio'] is False
    s = f['select_unit'](*sel_inputs(0.9, 1.0, 1.0, 1.0, [1, 1, 2, 2], [2, 2, 1, 1]), CFG)
    assert s['n_fold_wins'] == 2 and s['selected_method'] == 'segment_mean_k30'
    s = f['select_unit'](*sel_inputs(0.9, 1.0, 1.0, 1.0, [1] * 4, [2] * 4, {'poisson_a1e-05::core': False, 'poisson_a1e-05::routed_context': False}), CFG)
    assert s['best_candidate'] is None and s['selected_method'] == 'segment_mean_k30'


def test_block_bootstrap_day_blocks_and_reproducible(f):
    assert f['day_blocks'](730, 7)[-1] == (728, 730) and len(f['day_blocks'](730, 7)) == 105
    rng = np.random.default_rng(1)
    b = rng.gamma(2.0, 1.0, 730)
    c = b * 0.9
    r1, r2 = f['block_bootstrap'](c, b, CFG), f['block_bootstrap'](c, b, CFG)
    assert r1 == r2 and r1['partial_last_block_days'] == 2 and r1['blocks'] == 105
    assert r1['point_relative_deviance_reduction'] == pytest.approx(0.1) and r1['ci_low'] == pytest.approx(0.1) and r1['ci_high'] == pytest.approx(0.1)
    c2 = b.copy()
    c2[:7] *= 3  # one bad week: resamples move the 7 days together, so the CI must widen around a lower point estimate
    r3 = f['block_bootstrap'](c2, b, CFG)
    assert r3['point_relative_deviance_reduction'] < 0.1 and r3['ci_low'] < r3['ci_high']
    r4 = f['block_bootstrap'](c, np.zeros(730), CFG)
    assert r4['ci_low'] is None and r4['ci_status'].startswith('undefined')


# ---------- estimators / routing ----------
def tiny_frame(n=600, seed=0, unit='6h'):
    rng = np.random.default_rng(seed)
    X = pd.DataFrame({'route_code': rng.choice(['0001', '0002', '0035'], n), 'num1': rng.normal(size=n), 'num2': rng.normal(size=n), 'allnan': np.nan})
    if unit == '6h':
        X['time_block'] = rng.choice(BLOCKS, n)
    y = rng.poisson(np.exp(0.3 * X['num1'].to_numpy()) * 0.5).astype(float)
    return X, y


@pytest.mark.parametrize('cid', ['poisson_a1e-05', 'rf_poisson_fixed', 'hgb_poisson_fixed'])
def test_train_only_transforms_unseen_categories_and_all_missing(f, cid):
    X, y = tiny_frame()
    cols = ['route_code', 'num1', 'num2', 'allnan', 'time_block']
    conf = next(c for c in CFG['candidates']['configs'] if c['config_id'] == cid)
    w = np.ones(len(y))
    w[:50] = 3.0
    est, rec = f['fit_component'](conf, 'calendar_geometry', X, y, w, cols, CFG)
    assert est is not None and rec['status'].startswith('ok'), rec
    Xu = X.head(20).copy()
    Xu['route_code'] = 'NEVER_SEEN'
    Xu['time_block'] = '99-99'
    Xu[['num1', 'num2']] = np.nan
    p = f['predict_component'](est, Xu, cols, CFG)
    assert np.isfinite(p).all() and (p >= 0).all()
    if cid != 'hgb_poisson_fixed':
        imp = est.named_steps['pre'].named_transformers_['num'].named_steps['impute']
        assert np.allclose(imp.statistics_, [np.median(X['num1']), np.median(X['num2']), 0.0])  # train medians; all-missing kept (0)
    else:
        assert list(est.named_steps['model'].is_categorical_) == [True, True, False, False, False]


def test_failed_fit_is_recorded_not_hidden(f):
    X, y = tiny_frame(300)
    X['route_code'] = ['r' + str(i) for i in range(300)]  # > 255 categories
    est, rec = f['fit_component'](CFG['candidates']['configs'][3], 'calendar_geometry', X, y, np.ones(300), ['route_code', 'num1'], CFG)
    assert est is None and rec['status'] == 'failed' and 'exceeds' in rec['error']


def test_routed_context_uses_feature_missingness_only(f):
    cols = CFG['candidates']['routed_trigger_columns']['6h']
    X = pd.DataFrame({c: [1.0, 1.0, np.nan] for c in cols})
    X['bank_holiday_asof'] = [np.nan, 0.0, 0.0]
    m = f['context_complete'](X, '6h', CFG)
    assert m.tolist() == [True, True, False]  # unknown bank calendar never forces the core fallback
    X2 = X.copy()
    X2['wx_block_rain_sum_mm_d2'] = [1.0, np.nan, 1.0]
    X2['wx_rain_sum_mm_d2'] = [1.0, 1.0, 1.0]
    assert f['context_complete'](X2, '6h', CFG).tolist() == [True, False, False]
    assert f['context_complete'](X2, 'daily', CFG).tolist() == [True, True, False]
    assert f['routed_prediction'](np.array([1.0, 2.0, 3.0]), np.array([9.0, 9.0, 9.0]), m).tolist() == [9.0, 9.0, 3.0]
    with pytest.raises(f['ExperimentError']):
        f['routed_prediction'](None, np.ones(3), m)
    import inspect
    assert list(inspect.signature(f['context_complete']).parameters) == ['X', 'unit', 'cfg']


# ---------- bundles / hashes / guards ----------
def test_model_bundle_and_data_hash_tamper(f, tmp_path):
    X, y = tiny_frame(400)
    cols = ['route_code', 'num1', 'time_block']
    est, rec = f['fit_component'](CFG['candidates']['configs'][0], 'calendar_geometry', X, y, np.ones(400), cols, CFG)
    meta = f['save_bundle'](est, tmp_path / 'm.joblib', {'config_id': 'x'})
    e2, m2 = f['load_bundle'](tmp_path / 'm.joblib', meta['sha256'])
    assert np.array_equal(f['predict_component'](e2, X, cols, CFG), f['predict_component'](est, X, cols, CFG))
    with pytest.raises(f['ExperimentError']):
        f['load_bundle'](tmp_path / 'm.joblib', '0' * 64)
    with open(tmp_path / 'm.joblib', 'ab') as fh:
        fh.write(b'tamper')
    with pytest.raises(f['ExperimentError']):
        f['load_bundle'](tmp_path / 'm.joblib', meta['sha256'])
    (tmp_path / 'd.csv').write_text('a\n1\n')
    h = f['sha256_file'](tmp_path / 'd.csv')
    (tmp_path / 'd.csv').write_text('a\n2\n')
    with pytest.raises(f['ExperimentError']):
        f['verify_pinned'](tmp_path / 'd.csv', h, 'data')


def test_array_finalize_rejects_sentinel_and_negative(f, tmp_path):
    mm = f['new_array'](tmp_path / 'p.npy', 5)
    mm[:4] = 1.0
    mm.flush()
    with pytest.raises(f['ExperimentError']):
        f['finalize_array'](tmp_path / 'p.npy', 5, 'pred')
    mm[4] = -1.0
    mm.flush()
    with pytest.raises(f['ExperimentError']):
        f['finalize_array'](tmp_path / 'p.npy', 5, 'pred')
    mm[4] = 0.0
    mm.flush()
    meta = f['finalize_array'](tmp_path / 'p.npy', 5, 'pred')
    assert meta['dtype'] == 'float64' and meta['shape'] == [5]
    assert np.load(tmp_path / 'p.npy', allow_pickle=False).sum() == 4.0


def test_artifact_budget(f):
    ok = f['estimate_artifact_bytes'](CFG, {'oof': CFG['time']['expected_oof_rows'], 'diag': {'daily': 2269755, '6h': 9079020}, 'transfer': {'daily': 149650, '6h': 598600}})
    assert ok['within_budget'] and ok['total_bytes'] < 4 * 1024 ** 3
    with pytest.raises(f['ExperimentError']):
        f['estimate_artifact_bytes'](CFG, {'oof': {'6h': 10 ** 9}, 'diag': {}, 'transfer': {}})


def test_output_guards(f, tmp_path):
    cfg = copy.deepcopy(CFG)
    cfg['protected_paths'] = ['prot']
    (tmp_path / 'prot').mkdir()
    paths = f['output_paths'](tmp_path / 'prot', cfg)
    with pytest.raises(f['ExperimentError']):
        f['check_outputs'](paths, tmp_path, cfg)
    paths = f['output_paths'](tmp_path / 'new', cfg)
    assert f['check_outputs'](paths, tmp_path, cfg)
    paths['report_dir'].mkdir(parents=True)
    with pytest.raises(f['ExperimentError']):
        f['check_outputs'](paths, tmp_path, cfg)
    (tmp_path / 'link').symlink_to(tmp_path / 'prot')
    with pytest.raises(f['ExperimentError']):
        f['check_outputs'](f['output_paths'](tmp_path / 'link', cfg), tmp_path, cfg)
    with pytest.raises(f['ExperimentError']):
        f['check_report_file']('rows.csv.gz', cfg)


def test_runner_refusals(runner, tmp_path):
    cfg = runner.config()
    assert 'rerun-spatial-model-' in runner.refusal(BACKEND / 'rerun-spatial-prep-x', BACKEND, cfg)
    assert runner.refusal(BACKEND / 'rerun-other-x', BACKEND, cfg) is not None
    assert runner.refusal(tmp_path / 'rerun-spatial-model-x', BACKEND, cfg) is not None  # not directly inside backend/
    assert runner.refusal(BACKEND / 'reports', BACKEND, cfg) is not None  # existing path
    assert runner.refusal(BACKEND / 'rerun-spatial-model-test-never-created', BACKEND, cfg) is None
    env = runner.build_env(BACKEND / 'rerun-spatial-model-x', BACKEND, {'ROADAWARE_STALE': '1', 'PATH': '/bin'})
    assert 'ROADAWARE_STALE' not in env and env['OMP_NUM_THREADS'] == '2'


# ---------- geometry split ----------
def test_transfer_split_oid_and_buffer(f, tmp_path):
    from pyproj import Transformer
    inv = Transformer.from_crs(32647, 4326, always_xy=True)
    lines = {'E1': ((700000, 1600000), (701000, 1600000)), 'E2': ((702000, 1600000), (703000, 1600000)), 'T1': ((704000, 1600000), (705000, 1600000)),
             'T2': ((700000, 1600500), (701000, 1600500)), 'T3': ((700000, 1605000), (701000, 1605000)), 'T4': ((710000, 1610000), (711000, 1610000))}
    oid = {'E1': 10, 'E2': 11, 'T1': 11, 'T2': 20, 'T3': 21, 'T4': 22}
    feats = []
    for sid, ((x0, y0), (x1, y1)) in lines.items():
        lon, lat = inv.transform([x0, x1], [y0, y1])
        feats.append({'type': 'Feature', 'id': sid, 'properties': {}, 'geometry': {'type': 'LineString', 'coordinates': [[lon[0], lat[0]], [lon[1], lat[1]]]}})
    (tmp_path / 'g.geojson').write_text(json.dumps({'type': 'FeatureCollection', 'features': feats}))
    seg = pd.DataFrame({'segment_id': list(lines), 'geom_mid_lon': [102, 102, 100, 100, 100, 100], 'geom_mid_lat': [15, 15, 14, 14, 14, 14],
                        'oid': [float(oid[s]) for s in lines]}).set_index('segment_id')
    pre = {'eval_midpoint_predicate': {'lon_gte': 101.25, 'lat_gte': 14.5}, 'buffer_m_epsg32647': 1000, 'eval_segments': 2, 'eval_source_oids': 2,
           'train_segments': 2, 'train_source_oids': 2, 'removed_buffer_additional': 1,
           'eval_segment_ids_sha256': f['ids_sha'](['E2', 'E1'], 'json_list'), 'train_segment_ids_sha256': f['ids_sha'](['T4', 'T3'], 'json_list')}
    ev, tr, res = f['transfer_split'](seg, tmp_path / 'g.geojson', pre, ['lines', 'json_list'])
    assert ev == ['E1', 'E2'] and tr == ['T3', 'T4'] and res['matched_encoding'] == 'json_list'
    assert res['removed_same_source_oid_non_eval'] == 1 and res['source_oids_disjoint'] and res['min_train_eval_distance_m'] >= 1000
    bad = dict(pre, train_segments=3)
    with pytest.raises(f['ExperimentError']):
        f['transfer_split'](seg, tmp_path / 'g.geojson', bad, ['lines', 'json_list'])
    with pytest.raises(f['ExperimentError']):
        f['transfer_split'](seg, tmp_path / 'g.geojson', pre, ['lines'])


# ---------- tests on the accepted (ignored) prepared data ----------
@pytest.fixture(scope='module')
def ctx(f):
    if not (DD19 / 'context_settings.json').is_file():
        pytest.skip('accepted notebook-19 prepared data not present (gitignored)')
    return f['H19']['load_prepared_context'](DD19, PINS['prepared_data_hashes'])


def test_19_feature_parity_and_columns(f, ctx):
    feats = f['check_feature_columns'](ctx['settings'], PINS)
    for u in ('daily', '6h'):
        req = pd.read_csv(DD19 / ('reference_requests_' + u + '.csv'), dtype=str, keep_default_na=False)
        Xc, _ = f['H19']['build_feature_rows'](ctx, req, u, 'calendar_geometry_context')
        Xb, _ = f['H19']['build_feature_rows'](ctx, req, u, 'calendar_geometry')
        RL = f['H19']['read_numeric_csv'](DD19 / ('reference_features_' + u + '.csv'), ['segment_id', 'target_date', 'time_block', 'route_code'])
        assert f['H19']['frames_identical'](Xb, Xc[feats[u]['calendar_geometry']])
        assert f['H19']['frames_identical'](Xc, RL[feats[u]['calendar_geometry_context']])
        assert not set(Xc.columns) & {'segment_id', 'target_date', 'y_count'}


class ConstModel:
    def __init__(self, v):
        self.v = v

    def predict(self, X):
        return np.full(len(X), self.v)


def test_full_population_eval_no_downsampling(f, ctx, tmp_path):
    segs = sorted(ctx['seg'].index)[:3]
    ax = f['H19']['population_axes'](segs, '2022-01-01', '2022-01-04', BLOCKS)
    rows = [(segs[0], '2022-01-02', '06-12', 2)]
    sp = sparse(f, ax, '6h', rows)
    tabs = {p: f['baseline_tables'](f['fit_baselines'](ax, '6h', sp, np.array([1, 1, 1, 1]), ctx, CFG), ctx, segs, CFG)[0] for p in ('P1', 'P2')}
    models = {p: {'core': {'poisson_a1e-05': ConstModel(0.1)}, 'context': {'poisson_a1e-05': ConstModel(0.2)}} for p in ('P1', 'P2')}
    cfg = copy.deepcopy(CFG)
    cfg['resources']['batch_rows'] = 7  # forces many batches across the period boundary
    R = f['evaluate_population'](ctx, ax, '6h', sp, [('P1', '2022-01-02', '2022-01-02'), ('P2', '2022-01-03', '2022-01-04')], models, tabs, cfg, tmp_path, 'oof',
                                 ['poisson_a1e-05::core', 'segment_mean_k30'])
    n = 3 * 3 * 4
    assert R['rows'] == n and sum(p['rows'] for p in R['periods']) == n and R['periods'][1]['row_offset'] == 12
    assert sum(R['period_acc'][p]['zero']['n'][0] for p in ('P1', 'P2')) == n
    y = np.load(tmp_path / 'oof_6h_y.npy', allow_pickle=False)
    assert y.sum() == 2 and y[1] == 2  # 2022-01-02 is the first evaluated day: local row = segment 0 * 4 + block 06-12
    core = np.load(tmp_path / 'oof_6h_poisson_a1e-05__core.npy', allow_pickle=False)
    mask = np.load(tmp_path / 'oof_6h_context_mask.npy', allow_pickle=False)
    assert (core == 0.1).all() and set(np.unique(mask)) <= {0, 1}
    routed = R['period_acc']['P1']['poisson_a1e-05::routed_context']['pred'][0] + R['period_acc']['P2']['poisson_a1e-05::routed_context']['pred'][0]
    assert routed == pytest.approx(np.where(mask == 1, 0.2, 0.1).sum())
    acc = f['acc_add'](f['acc_new'](), y, core, 1e-12)
    pooled = f['acc_metrics'](f['acc_merge'](R['period_acc']['P1']['poisson_a1e-05::core'], R['period_acc']['P2']['poisson_a1e-05::core']))
    assert pooled['mean_poisson_deviance'] == pytest.approx(f['acc_metrics'](acc)['mean_poisson_deviance'], rel=1e-12)
    assert R['day_dev']['poisson_a1e-05::core'].sum() == pytest.approx(acc['dev'][0])
