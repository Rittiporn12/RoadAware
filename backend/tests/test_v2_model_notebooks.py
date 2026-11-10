"""Offline fixture tests for V2 notebook 11 (model experiments) and the runner's model stage. No network, no kernel, no real data.

Tests execute the notebook's own '# FUNCTIONS' cells, so the logic under test is what the notebook runs. Expected values are
worked out by hand from tiny fixtures. Run from the repository root:
    .venv/bin/python -m pytest backend/tests/test_v2_model_notebooks.py -q
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
NB11 = BACKEND / 'notebooks' / '11_v2_model_experiments.ipynb'
RUNNER = BACKEND / 'scripts' / 'run_v2_notebooks.py'
CFG = json.loads((BACKEND / 'config' / 'model_experiment_v2.json').read_text('utf-8'))
OFF = '+07:00'


def code_cells():
    nb = json.loads(NB11.read_text('utf-8'))
    return [''.join(c['source']) if isinstance(c['source'], list) else c['source'] for c in nb['cells'] if c['cell_type'] == 'code']


@pytest.fixture(scope='module')
def f():
    ns = {}
    for i, s in enumerate(s for s in code_cells() if s.lstrip().startswith('# FUNCTIONS')):
        exec(compile(s, f'11:FUNCTIONS[{i}]', 'exec'), ns)
    return ns


def ts(s):
    return pd.to_datetime(pd.Series(s), format='%Y-%m-%dT%H:%M:%S%z')


def daily_frame(rows):
    """rows: (province, date, y[, eligible[, split[, extra]]])."""
    recs = []
    for r in rows:
        p, d, y = r[:3]
        rec = {'province_key': p, 'target_date': d, 'y': float(y), 'eligible': r[3] if len(r) > 3 else True, 'split': r[4] if len(r) > 4 else 'train'}
        rec.update(r[5] if len(r) > 5 else {})
        recs.append(rec)
    df = pd.DataFrame(recs)
    start = ts(df['target_date'] + 'T00:00:00' + OFF)
    df['start_ts'], df['end_ts'], df['issue_ts'] = start, start + pd.Timedelta(days=1), start - pd.Timedelta(hours=6)
    d = pd.to_datetime(df['target_date'])
    df['bl_weekday'], df['bl_month'] = d.dt.dayofweek.astype(str), d.dt.month.astype(str)
    df['province'] = df['province_key']
    return df


def block_frame(province, dates):
    recs = []
    for d in dates:
        for b, lab in enumerate(['00-06', '06-12', '12-18', '18-24']):
            recs.append({'province_key': province, 'target_date': d, 'time_block': lab, 'b': b, 'y': 1.0, 'eligible': True, 'split': 'train'})
    df = pd.DataFrame(recs)
    day = ts(df['target_date'] + 'T00:00:00' + OFF)
    df['start_ts'] = day + pd.to_timedelta(df['b'] * 6, unit='h')
    df['end_ts'] = df['start_ts'] + pd.Timedelta(hours=6)
    df['issue_ts'] = day - pd.Timedelta(hours=6)
    return df


# ---------- notebook structure / config ----------
def test_notebook_structure_self_contained():
    cells = code_cells()
    assert cells[0].startswith('# SETUP') and cells[1].startswith('# FUNCTIONS') and cells[2].startswith('# FUNCTIONS')
    assert sum(c.startswith('# FUNCTIONS') for c in cells) == 2
    for c in cells:
        compile(c, 'cell', 'exec')
        assert '.ai-team' not in c and 'handoffs' not in c
    # the selection lock is written before the final-fit cell reads any diagnostic label
    i_lock = next(i for i, c in enumerate(cells) if 'write_selection_lock(SEL_LOCK_PATH' in c)
    i_final = next(i for i, c in enumerate(cells) if c.startswith('# F. Final fit'))
    assert i_lock < i_final and cells[i_final].index('verify_selection_lock') < cells[i_final].index("F_['diag_masks']")


def test_config_matches_protocol_draft():
    m = {c['id']: c for c in CFG['model_configs']}
    assert [m['poisson_a0.001']['params']['alpha'], m['poisson_a0.01']['params']['alpha']] == [0.001, 0.01]
    assert m['poisson_a0.01']['params'] == {'alpha': 0.01, 'max_iter': 1000, 'tol': 1e-06}
    assert m['rf_poisson']['params'] == {'criterion': 'poisson', 'n_estimators': 80, 'max_depth': 18, 'max_leaf_nodes': 128, 'min_samples_leaf': 50,
                                         'max_features': 0.8, 'random_state': 42, 'n_jobs': 2}
    assert m['hgb_poisson']['params'] == {'loss': 'poisson', 'max_iter': 160, 'max_leaf_nodes': 15, 'min_samples_leaf': 100, 'l2_regularization': 5.0,
                                          'learning_rate': 0.05, 'early_stopping': False, 'random_state': 42}
    assert list(CFG['feature_variants']) == ['core', 'calendar', 'calendar_weather', 'calendar_traffic', 'full']
    assert [x['name'] for x in CFG['folds']] == ['2022H1', '2022H2', '2023H1', '2023H2']
    assert CFG['gate']['min_relative_deviance_reduction'] == 0.01 and CFG['gate']['max_mae_ratio'] == 1.02 and CFG['gate']['min_fold_wins'] == 3
    assert CFG['gate']['bootstrap'] == {**CFG['gate']['bootstrap'], 'block_days': 7, 'n_resamples': 500, 'seed': 42}
    assert CFG['final_fit']['cutoff_local'] == '2023-12-31T18:00:00+07:00' and CFG['metrics']['deviance_floor'] == 1e-09
    assert CFG['family_order'] == ['poisson', 'rf', 'hgb']


# ---------- baselines ----------
def test_smoothing_and_fallbacks_hand_calculated(f):
    tr = daily_frame([('A', '2021-01-04', 2), ('A', '2021-01-11', 4), ('A', '2021-01-05', 0), ('B', '2021-01-04', 1)])  # Mon, Mon, Tue, Mon
    ev = daily_frame([('A', '2021-01-18', 0), ('A', '2021-01-19', 0), ('A', '2021-01-20', 0), ('C', '2021-01-18', 0)])  # Mon, Tue, Wed, Mon
    spec = {s['id']: s for s in CFG['baselines']['daily']}
    assert f['predict_baseline'](f['fit_baseline'](spec['global_mean'], tr), ev).tolist() == [1.75] * 4
    assert f['predict_baseline'](f['fit_baseline'](spec['province_mean'], tr), ev).tolist() == [2.0, 2.0, 2.0, 1.75]
    p = f['predict_baseline'](f['fit_baseline'](spec['province_weekday_k10'], tr), ev)
    assert p == pytest.approx([(6 + 10 * 2) / 12, (0 + 10 * 2) / 11, 2.0, 1.75])
    assert f['predict_baseline'](f['fit_baseline'](spec['zero'], tr), ev).tolist() == [0.0] * 4
    # 6 h: province-block falls back to the Train block mean, then global
    b = pd.DataFrame({'province_key': ['A', 'A', 'B'], 'time_block': ['00-06', '06-12', '00-06'], 'y': [3.0, 1.0, 1.0]})
    e = pd.DataFrame({'province_key': ['A', 'B', 'C', 'C'], 'time_block': ['00-06', '06-12', '00-06', '18-24']})
    st = f['fit_baseline']({'id': 'pb', 'levels': [['time_block'], ['province_key', 'time_block']]}, b)
    assert f['predict_baseline'](st, e).tolist() == pytest.approx([3.0, 1.0, 2.0, 5 / 3])


def test_recent_baseline_frozen_at_cutoff_and_falls_back(f):
    cutoff = pd.Timestamp('2021-01-31T18:00:00+07:00')
    tr = daily_frame([('A', '2021-01-01', 10), ('A', '2021-01-30', 2), ('B', '2021-01-01', 4)])
    spec = {'id': 'r', 'levels': [['province_key']], 'recent': {'cols': ['province_key'], 'days': 29}}
    st = f['fit_baseline'](spec, tr, cutoff=cutoff)
    ev = daily_frame([('A', '2021-02-01', 99), ('B', '2021-02-01', 99), ('C', '2021-02-01', 99)])
    assert f['predict_baseline'](st, ev).tolist() == pytest.approx([2.0, 4.0, 16 / 3])
    assert st['frozen_at'] == cutoff.isoformat() and st['recent']['n_window_cells'] == 1
    ev2 = ev.assign(y=[0.0, 1000.0, 5.0])  # evaluation labels never update a fitted state
    assert np.array_equal(f['predict_baseline'](st, ev2), f['predict_baseline'](st, ev))
    with pytest.raises(ValueError):
        f['fit_baseline'](spec, tr)  # no cutoff: refused
    with pytest.raises(ValueError):
        f['fit_baseline'](spec, daily_frame([('A', '2021-02-05', 1)]), cutoff=cutoff)  # Train cell after the frozen cutoff


# ---------- temporal cutoff ----------
def test_issue_time_cutoff_daily_and_6h(f):
    issue = f['issue_time_for']('2022-01-01', 18, 1, OFF)
    assert issue == pd.Timestamp('2021-12-31T18:00:00+07:00')
    assert f['issue_time_for'](CFG['final_fit']['first_diagnostic_date'], 18, 1, OFF) == pd.Timestamp(CFG['final_fit']['cutoff_local'])
    d = daily_frame([('A', x, 1) for x in ('2021-12-29', '2021-12-30', '2021-12-31')] + [('A', '2022-01-01', 1, True, 'train'), ('A', '2022-01-02', 1, False)])
    tm = f['fit_mask'](d, issue, 'train')
    assert d.loc[tm, 'target_date'].tolist() == ['2021-12-29', '2021-12-30']  # the 31st ends at 01-01 00:00 > issue
    em = f['eval_mask'](d, '2022-01-01', '2022-06-30', 'train')
    assert d.loc[em, 'target_date'].tolist() == ['2022-01-01']  # ineligible 01-02 excluded
    chk = f['check_fold'](d, tm, em, issue, ['province_key', 'target_date'], 'x')
    assert chk['n_train'] == 2 and chk['disjoint_keys']
    with pytest.raises(ValueError):
        f['check_fold'](d, tm | em, em, issue, ['province_key', 'target_date'], 'leak')
    b = block_frame('A', ['2021-12-31', '2022-01-01'])
    bm = f['fit_mask'](b, issue, 'train')
    assert b.loc[bm, 'time_block'].tolist() == ['00-06', '06-12', '12-18']  # 18-24 of the 31st ends after the issue
    assert f['check_issue_times'](d, 18, 1, OFF)
    with pytest.raises(f['DependencyError']):
        f['check_issue_times'](d.assign(issue_ts=d['issue_ts'] + pd.Timedelta(hours=1)), 18, 1, OFF)


# ---------- preprocessing leakage ----------
def test_preprocessing_fitted_on_train_only_and_keeps_all_missing(f):
    Xtr = pd.DataFrame({'province': ['A', 'A', 'B', 'B'], 'a': [1.0, 2.0, 3.0, np.nan], 'allnan': [np.nan] * 4})
    Xev = pd.DataFrame({'province': ['C', 'A'], 'a': [100.0, np.nan], 'allnan': [5.0, np.nan]})
    p = f['make_preprocessor']('onehot_impute', ['province'], ['a', 'allnan']).fit(Xtr)
    names = list(p.get_feature_names_out())
    assert 'num__allnan' in names and 'num__a' in names
    assert not any('missingindicator' in n for n in names) and len(names) == 4  # no extra missingness predictors
    out = pd.DataFrame(p.transform(Xev), columns=names)
    assert out.loc[0, ['cat__province_A', 'cat__province_B']].tolist() == [0.0, 0.0]  # unknown level -> all-zero one-hot
    assert out.loc[1, 'num__a'] == 2.0  # Train median, not influenced by the evaluation value 100
    assert out.loc[1, 'num__allnan'] == 0.0
    p2 = f['make_preprocessor']('onehot_impute_scale', ['province'], ['a', 'allnan']).fit(Xtr)
    before = p2.transform(Xev)
    p2.transform(Xev.assign(a=[1e6, 1e6]))
    assert np.array_equal(before, p2.transform(Xev))  # transforming new evaluation values never refits
    o = f['make_preprocessor']('ordinal_native', ['province'], ['a', 'allnan']).fit(Xtr)
    t = o.transform(Xev)
    assert np.isnan(t[0, 0]) and t[1, 0] == 0.0 and t.shape[1] == 3


def synth():
    rng = np.random.default_rng(0)
    rows = []
    for d in pd.date_range('2021-01-01', '2021-03-31').strftime('%Y-%m-%d'):
        for p in ('A', 'B'):
            wx = np.nan if rng.random() < 0.3 else float(rng.normal())
            rows.append((p, d, int(rng.poisson(2 if p == 'A' else 1)), True, 'train', {'month': int(d[5:7]), 'wx': wx}))
    return daily_frame(rows)


def test_run_unit_oof_identical_keys_no_label_leak(f):
    fr = synth()
    folds = []
    for name, s, e in (('F1', '2021-02-01', '2021-02-28'), ('F2', '2021-03-01', '2021-03-31')):
        iss = f['issue_time_for'](s, 18, 1, OFF)
        folds.append({'fold': name, 'issue': iss, 'train_mask': f['fit_mask'](fr, iss, 'train'), 'eval_mask': f['eval_mask'](fr, s, e, 'train')})
    cfgs = copy.deepcopy(CFG['model_configs'])
    for c in cfgs:
        if c['family'] == 'rf':
            c['params']['n_estimators'] = 5  # speed only; the notebook uses the locked 80
    variants = {'core': ['province', 'month'], 'wx': ['province', 'month', 'wx']}
    args = (variants, ['province'], cfgs, CFG['baselines']['daily'])
    oof, preds, log, _ = f['run_unit_oof'](fr, folds, *args, threads=1, log=lambda *a: None)
    n_eval = sum(int(x['eval_mask'].sum()) for x in folds)
    assert len(oof) == n_eval == 28 * 2 + 31 * 2
    methods = [c for c in oof if c.startswith('baseline_') or '__' in c]
    assert len(methods) == 6 + 4 * 2 and not oof[methods].isna().any().any()  # every method predicts every evaluation row (NaN wx kept)
    assert all(r['status'] == 'ok' for r in log)
    assert oof.columns.is_unique and not oof.duplicated(['province_key', 'target_date']).any()  # no duplicate target_date column/keys
    assert sum(r['method_id'] == 'baseline_global_mean' for r in log) == 2  # baselines fitted once per fold, not per variant
    # end to end: metrics, per-unit selection and calendar-block bootstrap on the same OOF keys
    pooled, byfold = f['oof_metric_tables'](oof, methods, cfgs, 1e-9, set())
    assert (pooled['status'] == 'ok').all() and (pooled['n'] == n_eval).all() and len(byfold) == 2 * len(methods)
    assert pooled.loc[pooled['method_id'].eq('baseline_zero'), 'mean_poisson_deviance'].isna().all()
    gm = pooled.set_index('method_id').loc['baseline_global_mean']
    y = oof['y'].to_numpy(float)
    assert gm['mae'] == pytest.approx(np.abs(oof['baseline_global_mean'] - y).mean())
    s = f['select_unit'](pooled, CFG['family_order'])
    assert s['best_candidate'] in methods and s['strongest_baseline'] not in (None, 'baseline_zero')
    best = pooled.loc[pooled['family'].ne('baseline'), 'mean_poisson_deviance'].min()
    assert pooled.set_index('method_id').loc[s['best_candidate'], 'mean_poisson_deviance'] == best
    blocks = f['calendar_blocks'](oof['target_date'], '2021-02-01', 7)
    assert blocks.min() == 0 and len(np.unique(blocks)) == 9  # 59 days -> 9 seven-day blocks
    dc, _ = f['poisson_deviance_rows'](y, oof[s['best_candidate']], 1e-9)
    db, _ = f['poisson_deviance_rows'](y, oof[s['strongest_baseline']], 1e-9)
    b = f['block_bootstrap'](dc - db, blocks, 50, 42)
    assert b['lower'] <= b['upper'] and b['n_blocks'] == 9 and b['point'] == pytest.approx((dc - db).mean())
    # perturbing evaluation labels changes nothing that was fitted
    fr2 = fr.copy()
    fr2.loc[folds[0]['eval_mask'], 'y'] += 50  # every F1 evaluation label (none is in F1 Train)
    oof2, *_ = f['run_unit_oof'](fr2, folds[:1], *args, threads=1, log=lambda *a: None)
    first = oof[oof['fold'].eq('F1')].reset_index(drop=True)
    assert not np.array_equal(first['y'], oof2['y'])
    for m in methods:
        assert np.allclose(first[m], oof2[m], rtol=0, atol=1e-12)  # RF n_jobs summation order only


# ---------- metrics ----------
def test_metric_floor_and_zero_baseline(f):
    d, nf = f['poisson_deviance_rows']([0, 1, 2], [0, 1, 2], 1e-9)
    assert nf == 1 and d.tolist() == pytest.approx([2e-9, 0.0, 0.0], abs=1e-15)
    d2, _ = f['poisson_deviance_rows']([1], [2], 1e-9)
    assert d2[0] == pytest.approx(2 * (math.log(0.5) + 1))
    m = f['metric_summary']([0, 0], [0.0, 0.5], 1e-9)
    assert m['wape'] is None and m['mae'] == 0.25 and m['n_deviance_floored'] == 1 and m['sum_pred'] == 0.5
    z = f['metric_summary']([1, 0], [0.0, 0.0], 1e-9, deviance=False)
    assert z['mean_poisson_deviance'] is None and z['n_deviance_floored'] is None and z['mae'] == 0.5
    with pytest.raises(ValueError):
        f['metric_summary']([1], [-0.1], 1e-9)
    with pytest.raises(ValueError):
        f['poisson_deviance_rows']([1], [np.nan], 1e-9)


def test_family_selection_and_ties(f):
    rows = pd.DataFrame([
        {'method_id': 'hgb_poisson__core', 'family': 'hgb', 'status': 'ok', 'mean_poisson_deviance': 0.5, 'mae': 1},
        {'method_id': 'poisson_a0.01__full', 'family': 'poisson', 'status': 'ok', 'mean_poisson_deviance': 0.5, 'mae': 1},
        {'method_id': 'poisson_a0.001__full', 'family': 'poisson', 'status': 'ok', 'mean_poisson_deviance': 0.5, 'mae': 1},
        {'method_id': 'rf_poisson__core', 'family': 'rf', 'status': 'failed', 'mean_poisson_deviance': np.nan, 'mae': np.nan},
        {'method_id': 'rf_poisson__full', 'family': 'rf', 'status': 'ok', 'mean_poisson_deviance': 0.6, 'mae': 1},
        {'method_id': 'baseline_zero', 'family': 'baseline', 'status': 'ok', 'mean_poisson_deviance': np.nan, 'mae': 0.1},
        {'method_id': 'baseline_province_mean', 'family': 'baseline', 'status': 'ok', 'mean_poisson_deviance': 0.7, 'mae': 1},
        {'method_id': 'baseline_global_mean', 'family': 'baseline', 'status': 'ok', 'mean_poisson_deviance': 0.7, 'mae': 1}])
    s = f['select_unit'](rows, CFG['family_order'])
    assert s['family_best'] == {'poisson': 'poisson_a0.001__full', 'rf': 'rf_poisson__full', 'hgb': 'hgb_poisson__core'}
    assert s['best_candidate'] == 'poisson_a0.001__full'  # tie with hgb -> Poisson first, then method id
    assert s['strongest_baseline'] == 'baseline_global_mean'  # zero excluded; tie -> id
    assert s['failed_methods'] == ['rf_poisson__core']
    assert f['pick_best']([]) is None


def test_stability_gate_hand_calculated(f):
    g = CFG['gate']
    cand, base = {'mean_poisson_deviance': 0.9, 'mae': 1.02}, {'mean_poisson_deviance': 1.0, 'mae': 1.0}
    folds_b = {'a': 1.0, 'b': 1.0, 'c': 1.0, 'd': 1.0}
    ok = f['stability_gate'](cand, base, {'a': 0.9, 'b': 0.9, 'c': 0.9, 'd': 1.1}, folds_b, {'upper': -0.01, 'lower': -0.2, 'point': -0.1}, g)
    assert ok['passed'] and ok['checks']['fold_wins']['value'] == 3
    bad = f['stability_gate'](cand, base, {'a': 0.9, 'b': 0.9, 'c': 1.0, 'd': 1.1}, folds_b, {'upper': -0.01, 'lower': -0.2, 'point': -0.1}, g)
    assert not bad['passed'] and not bad['checks']['fold_wins']['pass']  # a fold tie is not a win
    assert not f['stability_gate'](cand, base, {k: 0.9 for k in folds_b}, folds_b, {'upper': 0.0, 'lower': -1, 'point': -0.1}, g)['passed']
    assert not f['stability_gate']({'mean_poisson_deviance': 0.995, 'mae': 1.0}, base, {k: 0.9 for k in folds_b}, folds_b,
                                   {'upper': -1, 'lower': -2, 'point': -1}, g)['passed']


def test_bootstrap_calendar_block_grouping(f):
    dates = pd.date_range('2022-01-01', '2022-01-14').strftime('%Y-%m-%d').tolist()
    blocks = f['calendar_blocks'](dates, '2022-01-01', 7)
    assert blocks.tolist() == [0] * 7 + [1] * 7
    # block 0: 7 rows of +1; block 1: 14 rows (two provinces per day) of -1
    d = dates[:7] + dates[7:] * 2
    diff = np.array([1.0] * 7 + [-1.0] * 14)
    r = f['block_bootstrap'](diff, f['calendar_blocks'](d, '2022-01-01', 7), 500, 42)
    allowed = {1.0, -1.0, round((7 - 14) / 21, 12)}
    assert set(np.round(r['stats'], 12)) <= allowed and r['n_blocks'] == 2
    assert r['point'] == pytest.approx(-7 / 21)
    r2 = f['block_bootstrap'](diff, f['calendar_blocks'](d, '2022-01-01', 7), 500, 42)
    assert np.array_equal(r['stats'], r2['stats']) and r['upper'] == r2['upper']


# ---------- locks ----------
def test_selection_lock_tampering(f, tmp_path):
    oof = tmp_path / 'oof.csv.gz'
    oof.write_bytes(b'abc')
    lock = tmp_path / 'selection_lock.json'
    hashes = {'model_config_sha256': 'h1'}
    sha = f['write_selection_lock'](lock, {'hashes': hashes, 'files': [{'path': 'oof.csv.gz', 'sha256': f['sha256_file'](oof)}], 'units': {}})
    assert f['verify_selection_lock'](lock, sha, hashes, tmp_path)['schema'] == 'roadaware-v2-selection-lock/1'
    with pytest.raises(f['LockError']):
        f['write_selection_lock'](lock, {'hashes': {}, 'files': []})  # never overwritten within a run
    with pytest.raises(f['LockError']):
        f['verify_selection_lock'](lock, sha, {'model_config_sha256': 'other'}, tmp_path)
    oof.write_bytes(b'abd')
    with pytest.raises(f['LockError']):
        f['verify_selection_lock'](lock, sha, hashes, tmp_path)
    oof.write_bytes(b'abc')
    lock.write_text(lock.read_text('utf-8').replace('"units": {}', '"units": {"daily": 1}'), 'utf-8')
    with pytest.raises(f['LockError']):
        f['verify_selection_lock'](lock, sha, hashes, tmp_path)


def test_experiment_lock_verification(f, tmp_path):
    proto, cfg, man = tmp_path / 'p.md', tmp_path / 'c.json', tmp_path / 'm.json'
    proto.write_text('protocol', 'utf-8')
    cfg.write_text('{}', 'utf-8')
    pm = {'started_utc': '2026-11-10T00:00:00+00:00', 'data_outputs': [{'path': 'panel_daily_v2.csv.gz', 'sha256': 'aa', 'bytes': 1}]}
    man.write_text(json.dumps(pm), 'utf-8')
    ic = CFG['inputs']
    good = {'schema': ic['experiment_lock_schema'], 'protocol_sha256': f['sha256_file'](proto), 'model_config_sha256': f['sha256_file'](cfg),
            'preparation_manifest_sha256': f['sha256_file'](man), 'preparation_data_outputs': [{'path': 'panel_daily_v2.csv.gz', 'sha256': 'aa'}],
            'source_run_id': '2026-11-10T10:59:15+00:00', 'preparation_run_id': pm['started_utc']}
    lp = tmp_path / 'lock.json'
    run = lambda: f['verify_experiment_lock'](lp, proto, cfg, man, pm, ic['experiment_lock_schema'], ic['experiment_lock_fields'])
    with pytest.raises(f['LockError']):
        run()  # absent
    lp.write_text(json.dumps(good), 'utf-8')
    assert run()['preparation_run_id'] == pm['started_utc']
    for k, v in (('protocol_sha256', '0' * 64), ('schema', 'x/1'), ('preparation_run_id', 'other'), ('source_run_id', ''),
                 ('preparation_data_outputs', [{'path': 'panel_daily_v2.csv.gz', 'sha256': 'ab'}])):
        lp.write_text(json.dumps(dict(good, **{k: v})), 'utf-8')
        with pytest.raises(f['LockError']):
            run()
    lp.write_text(json.dumps({k: v for k, v in good.items() if k != 'model_config_sha256'}), 'utf-8')
    with pytest.raises(f['LockError']):
        run()
    lp.write_text(json.dumps(good), 'utf-8')
    proto.write_text('protocol edited', 'utf-8')
    with pytest.raises(f['LockError']):
        run()


def test_reload_consistency_and_bundle_tamper(f, tmp_path):
    fr = synth()
    c = next(x for x in CFG['model_configs'] if x['id'] == 'poisson_a0.01')
    pipe = f['make_pipeline'](c, ['province'], ['month', 'wx']).fit(fr[['province', 'month', 'wx']], fr['y'])
    p = tmp_path / 'b.joblib'
    sha = f['save_model_bundle'](p, pipe, {'m': 1})
    again = f['load_model_bundle'](p, sha)['pipeline'].predict(fr[['province', 'month', 'wx']])
    assert f['reload_consistency'](pipe.predict(fr[['province', 'month', 'wx']]), again, 1e-12)['pass']
    assert not f['reload_consistency']([1.0, 2.0], [1.0, 2.1], 1e-12)['pass']
    with pytest.raises(f['DependencyError']):
        f['load_model_bundle'](p, '0' * 64)
    st = f['fit_baseline'](next(s for s in CFG['baselines']['daily'] if s['id'] == 'province_weekday_k10'), fr)
    js = f['write_json'](tmp_path / 'st.json', st)
    assert np.array_equal(f['predict_baseline'](f['read_json_strict'](js), fr), f['predict_baseline'](st, fr))


# ---------- feature guard / frames ----------
def test_feature_guard_and_variants(f):
    fcfg = json.loads((BACKEND / 'config' / 'feature_pipeline_v2.json').read_text('utf-8'))
    approved = [x['name'] for x in fcfg['features'] if 'daily' in x['panels']]
    assert f['validate_feature_columns'](approved, approved, fcfg['forbidden_feature_names'], fcfg['forbidden_feature_substrings'])
    for bad, allowed in ((['province', 'y_recorded_count'], approved + ['y_recorded_count']), (['province', 'target_date'], approved + ['target_date']),
                         (['province', 'wx_rain_missing_x'], approved + ['wx_rain_missing_x']), (['province', 'label_status'], approved + ['label_status']),
                         (['province', 'not_allowed'], approved), (['province', 'province'], approved)):
        with pytest.raises(ValueError):
            f['validate_feature_columns'](bad, allowed, fcfg['forbidden_feature_names'], fcfg['forbidden_feature_substrings'], never=['label_status'])
    groups = {}
    for x in fcfg['features']:
        groups.setdefault(x['group'], []).append(x['name'])
    v = f['variant_columns'](approved, groups, CFG['feature_variants'], [])
    assert sorted(v['full']) == sorted(approved) and 'wx_rain_sum_mm_d2' not in v['calendar_traffic'] and 'trf_mean_aadt' not in v['calendar_weather']
    assert set(v['core']) == {'province', 'day_of_week', 'month', 'day_of_month', 'is_weekend', 'doy_sin', 'doy_cos'}
    b6 = [x['name'] for x in fcfg['features'] if '6h' in x['panels']]
    assert 'time_block' in f['variant_columns'](b6, groups, CFG['feature_variants'], ['timeblock'])['core']
    with pytest.raises(ValueError):
        f['variant_columns'](approved + ['orphan'], groups, CFG['feature_variants'], [])


def test_load_unit_frame_keys_and_schema(f, tmp_path):
    it = {'keys': ['province_key', 'target_date'], 'target': 'y_recorded_count', 'mask': 'training_eligible', 'split': 'split',
          'feature_columns': ['province', 'month', 'wx']}
    pan = pd.DataFrame({'province_key': ['A', 'B'], 'target_date': ['2021-01-01', '2021-01-01'], 'y_recorded_count': ['0', '3'],
                        'training_eligible': ['True', 'False'], 'split': ['train', 'train'],
                        'issue_time_local': ['2020-12-31T18:00:00+07:00'] * 2, 'target_start_local': ['2021-01-01T00:00:00+07:00'] * 2,
                        'target_end_local': ['2021-01-02T00:00:00+07:00'] * 2})
    fe = pd.DataFrame({'province_key': ['A', 'B'], 'target_date': ['2021-01-01'] * 2, 'province': ['A', 'B'], 'month': [1, 1], 'wx': [np.nan, 2.5]})
    pan.to_csv(tmp_path / 'p.csv', index=False)
    fe.to_csv(tmp_path / 'f.csv', index=False)
    fr = f['load_unit_frame'](tmp_path / 'p.csv', tmp_path / 'f.csv', it, ['province'], OFF)
    assert fr['eligible'].tolist() == [True, False] and fr['y'].tolist() == [0.0, 3.0] and np.isnan(fr.loc[0, 'wx']) and len(fr) == 2
    assert fr.loc[0, 'end_ts'] == pd.Timestamp('2021-01-02T00:00:00+07:00')
    fe.iloc[::-1].to_csv(tmp_path / 'f2.csv', index=False)
    with pytest.raises(f['DependencyError']):
        f['load_unit_frame'](tmp_path / 'p.csv', tmp_path / 'f2.csv', it, ['province'], OFF)
    pan.assign(training_eligible=['yes', 'False']).to_csv(tmp_path / 'p2.csv', index=False)
    with pytest.raises(f['DependencyError']):
        f['load_unit_frame'](tmp_path / 'p2.csv', tmp_path / 'f.csv', it, ['province'], OFF)
    pan.assign(target_end_local=['2021-01-02T00:00:00Z'] * 2).to_csv(tmp_path / 'p3.csv', index=False)
    with pytest.raises(f['DependencyError']):
        f['load_unit_frame'](tmp_path / 'p3.csv', tmp_path / 'f.csv', it, ['province'], OFF)


def test_completed_output_root_detected_before_fit(f, tmp_path):
    rep, md = tmp_path / 'reports', tmp_path / 'models'
    rep.mkdir()
    md.mkdir()
    (rep / 'run_manifest_model.json').write_text('{}', 'utf-8')  # the runner log alone is not a completed run
    assert f['existing_results'](rep, md) == []
    (md / 'oof_predictions_daily.csv.gz').write_bytes(b'x')
    (rep / 'selection_lock.json').write_text('{}', 'utf-8')
    hits = f['existing_results'](rep, md)
    assert len(hits) == 2 and (rep / 'selection_lock.json').read_text('utf-8') == '{}'  # detected, never deleted


def test_write_roots_guard(f, tmp_path):
    prep, data = tmp_path / 'reports' / 'v2' / 'preparation', tmp_path / 'data' / 'v2'
    ok = f['check_write_roots'](tmp_path / 'reports' / 'v2' / 'models', data / 'models', prep, data, [], [data / 'panel_daily_v2.csv.gz'])
    assert ok
    with pytest.raises(ValueError):
        f['check_write_roots'](tmp_path / 'reports' / 'v2' / 'models', data, prep, data, [], [])
    with pytest.raises(ValueError):
        f['check_write_roots'](prep / 'x', data / 'models', prep, data, [], [])
    with pytest.raises(ValueError):
        f['check_write_roots'](tmp_path / 'r', data / 'models', prep, data, [], [data / 'models' / 'panel.csv.gz'])


# ---------- runner ----------
def load_runner():
    spec = importlib.util.spec_from_file_location('run_v2_notebooks', RUNNER)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_runner_model_stage_roots_and_env(tmp_path):
    r = load_runner()
    assert r.notebooks_for_stage('model') == ['11_v2_model_experiments']
    assert r.notebooks_for_stage('all') == ['09_external_collection_date_evidence', '10_v2_preparation_features_leakage']
    roots = r.resolve_roots(tmp_path / 'out', tmp_path / 'ext', tmp_path / 'v1', stage='model', preparation_dir=tmp_path / 'prep',
                            prep_data_dir=tmp_path / 'pdata', experiment_lock=tmp_path / 'lock.json')
    env = r.build_env(roots, base={'ROADAWARE_V2_MODEL_DATA_ROOT': '/stale', 'PATH': '/bin'})
    assert env['ROADAWARE_V2_DATA_ROOT'] == str((tmp_path / 'pdata').resolve())
    assert env['ROADAWARE_V2_MODEL_DATA_ROOT'] == str((tmp_path / 'out').resolve() / 'data' / 'v2' / 'models')
    assert env['ROADAWARE_V2_PREPARATION_DIR'] == str((tmp_path / 'prep').resolve()) and env['ROADAWARE_V2_EXPERIMENT_LOCK'] == str((tmp_path / 'lock.json').resolve())
    d = r.resolve_roots(stage='model')
    assert d['prep_data'] == r.BACKEND / 'data' / 'v2' and d['model_data'] == r.BACKEND / 'data' / 'v2' / 'models'
    assert d['lock'] == r.REPO / 'workflow' / 'model-protocol-v2-lock.json'
    with pytest.raises(ValueError):  # model data root may not equal / contain the read-only 10 data root
        r.resolve_roots(tmp_path / 'out', tmp_path / 'ext', tmp_path / 'v1', stage='model', prep_data_dir=tmp_path / 'out' / 'data' / 'v2' / 'models')
    with pytest.raises(ValueError):  # model reports may not sit inside the read-only preparation dir
        r.resolve_roots(tmp_path / 'out', tmp_path / 'ext', tmp_path / 'v1', stage='model', preparation_dir=tmp_path / 'out' / 'reports' / 'v2')
    assert 'model_data' not in r.resolve_roots(tmp_path / 'out', tmp_path / 'ext', tmp_path / 'v1', stage='prepare')
    assert r.completed_model_outputs(roots) == []
    (roots['model_reports']).mkdir(parents=True)
    (roots['model_reports'] / 'selection_lock.json').write_text('{}', 'utf-8')
    assert r.completed_model_outputs(roots) == [str(roots['model_reports'] / 'selection_lock.json')]
