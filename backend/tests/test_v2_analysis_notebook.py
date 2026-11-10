"""Offline fixture tests for V2 notebook 12 (evaluation / error analysis) and the runner's evaluate stage. No network, no kernel, no real data.

Tests execute the notebook's own '# FUNCTIONS' cells, so the logic under test is what the notebook runs. Expected values are
worked out by hand from tiny fixtures. Run from the repository root:
    .venv/bin/python -m pytest backend/tests/test_v2_analysis_notebook.py -q
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
NB12 = BACKEND / 'notebooks' / '12_v2_evaluation_error_analysis.ipynb'
NB11 = BACKEND / 'notebooks' / '11_v2_model_experiments.ipynb'
RUNNER = BACKEND / 'scripts' / 'run_v2_notebooks.py'


def code_cells(nb=NB12):
    d = json.loads(nb.read_text('utf-8'))
    return [''.join(c['source']) if isinstance(c['source'], list) else c['source'] for c in d['cells'] if c['cell_type'] == 'code']


def exec_functions(nb):
    ns = {}
    for i, s in enumerate(s for s in code_cells(nb) if s.lstrip().startswith('# FUNCTIONS')):
        exec(compile(s, f'{nb.stem}:FUNCTIONS[{i}]', 'exec'), ns)
    return ns


@pytest.fixture(scope='module')
def f():
    return exec_functions(NB12)


@pytest.fixture(scope='module')
def runner():
    spec = importlib.util.spec_from_file_location('run_v2_notebooks', RUNNER)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# ---------- structure ----------
def test_notebook_structure_self_contained():
    cells = code_cells()
    assert cells[0].startswith('# SETUP') and cells[1].startswith('# FUNCTIONS') and cells[2].startswith('# FUNCTIONS')
    assert sum(c.startswith('# FUNCTIONS') for c in cells) == 2
    for c in cells:
        compile(c, 'cell', 'exec')
        assert '.ai-team' not in c and 'handoffs' not in c
        assert '.fit(' not in c and 'joblib.load' not in c and 'requests' not in c and 'urllib' not in c  # no fitting, no bundles, no network
    body = '\n'.join(cells)
    # every lock / hash verification precedes the first prediction read
    first_read = body.index('load_predictions(MODEL_DATA')
    for call in ('verify_model_manifest(MAN', 'verify_report_outputs(MAN', 'verify_model_data_outputs(MAN', 'verify_selection_lock(SEL_LOCK_PATH',
                 'compare_selection(', 'verify_experiment_lock(LOCK_PATH', 'SNAP_BEFORE = snapshot('):
        assert body.index(call) < first_read, call
    assert 'production_ready' in cells[-1] and 'snapshot_diff(SNAP_BEFORE, SNAP_AFTER)' in cells[-1]


# ---------- metrics (hand-calculated) ----------
def test_metrics_hand_values(f):
    y, mu = [0, 1, 2], [0.5, 1.0, 4.0]
    m = f['metrics'](y, mu, 1e-9)
    dev = (2 * 0.5 + 0.0 + 2 * (2 * math.log(0.5) + 2)) / 3   # y=0 -> 2*mu; y=mu -> 0; y=2,mu=4 -> 2*(2 ln .5 + 2)
    assert m['mean_poisson_deviance'] == pytest.approx(dev, rel=1e-12)
    assert m['mae'] == pytest.approx(2.5 / 3) and m['bias'] == pytest.approx(2.5 / 3) and m['wape'] == pytest.approx(2.5 / 3)
    assert m['rmse'] == pytest.approx(math.sqrt(4.25 / 3)) and m['sum_y'] == 3 and m['sum_pred'] == 5.5 and m['n_deviance_floored'] == 0
    z = f['metrics']([0, 0], [0.0, 0.0], 1e-9)
    assert z['n_deviance_floored'] == 2 and z['mean_poisson_deviance'] == pytest.approx(2e-9) and z['wape'] is None
    e = f['metrics']([], [], 1e-9)
    assert e['n'] == 0 and e['mae'] is None and e['mean_poisson_deviance'] is None
    with pytest.raises(ValueError):
        f['metrics']([1], [-0.1], 1e-9)


def test_deviance_and_bootstrap_match_notebook11(f):
    if not NB11.is_file():
        pytest.skip('notebook 11 not present')
    g = exec_functions(NB11)
    rng = np.random.default_rng(0)
    y = rng.poisson(1.3, 500).astype(float)
    mu = rng.uniform(0, 3, 500)
    mu[:5] = 0.0
    a, na = f['deviance_rows'](y, mu, 1e-9)
    b, nb = g['poisson_deviance_rows'](y, mu, 1e-9)
    assert na == nb and np.allclose(a, b, rtol=1e-12, atol=1e-12)
    blocks = np.repeat(np.arange(50), 10)
    b12 = f['block_bootstrap'](a, blocks, 200, 42)
    b11 = g['block_bootstrap'](a, blocks, 200, 42)
    assert all(b12[k] == b11[k] for k in ('point', 'lower', 'upper', 'n_blocks'))


def test_bootstrap_constant_difference(f):
    r = f['block_bootstrap']([0.25] * 12, [0, 0, 0, 1, 1, 1, 2, 2, 2, 3, 3, 3], 50, 1)
    assert r['point'] == r['lower'] == r['upper'] == pytest.approx(0.25) and r['n_blocks'] == 4
    assert list(f['calendar_blocks'](['2022-01-01', '2022-01-07', '2022-01-08', '2022-01-15'], '2022-01-01', 7)) == [0, 0, 1, 2]


# ---------- reconciliation ----------
def test_reconcile_tolerance_nulls_and_missing_rows(f):
    a = pd.DataFrame({'method_id': ['m1', 'm2'], 'mae': [1.0, 2.0], 'wape': [None, 0.5]})
    b = pd.DataFrame({'method_id': ['m1', 'm2'], 'mae': [1.0 + 1e-12, 2.0], 'wape': [None, 0.5]})
    t = f['reconcile'](a, b, ['method_id'], cols=['mae', 'wape'])
    assert t['passed'].all() and f['assert_reconciled'](t, 'x')
    b2 = b.assign(mae=[1.0 + 1e-6, 2.0])
    with pytest.raises(f['ReconciliationError']):
        f['assert_reconciled'](f['reconcile'](a, b2, ['method_id'], cols=['mae', 'wape']), 'x')
    b3 = b.assign(wape=[0.1, 0.5])   # one side null
    assert not f['reconcile'](a, b3, ['method_id'], cols=['mae', 'wape'])['passed'].all()
    t4 = f['reconcile'](a, b.iloc[:1], ['method_id'], cols=['mae'])   # row missing in 11
    assert (t4['metric'] == '(row)').sum() == 1 and not t4['passed'].all()


def test_recompute_tables_marks_incomplete_methods(f):
    oof = pd.DataFrame({'fold': ['A', 'A', 'B'], 'y': [1.0, 0.0, 2.0], 'baseline_global_mean': [1.0, 1.0, 1.0], 'c1__core': [1.0, np.nan, 2.0]})
    p, bf = f['recompute_tables'](oof, ['baseline_global_mean', 'c1__core'], {'c1': 'poisson'}, 1e-9)
    assert dict(zip(p['method_id'], p['status'])) == {'baseline_global_mean': 'ok', 'c1__core': 'failed'}
    assert list(bf['fold']) == ['A', 'B'] and bf['sum_y'].tolist() == [1.0, 2.0]


# ---------- slices ----------
def test_slice_totals_empty_levels_and_support(f):
    df = pd.DataFrame({'target_date': ['2022-01-01', '2022-01-01', '2022-01-02', '2022-01-03', '2022-01-03'],
                       'lvl': ['a', 'a', 'b', 'b', 'b'], 'y': [0.0, 2.0, 1.0, 3.0, 0.0], 'm': [1.0, 1.0, 1.0, 2.0, 0.5]})
    t = f['slice_metrics'](df, 'lvl', ['m'], 1e-9, min_cells=3, min_events=4, levels=['a', 'b', 'c'])
    t = t.set_index('level')
    assert t.loc['a', 'n'] == 2 and t.loc['a', 'sum_y'] == 2 and t.loc['a', 'sum_pred'] == 2 and t.loc['a', 'residual_total'] == 0
    assert t.loc['b', 'n'] == 3 and t.loc['b', 'sum_y'] == 4 and t.loc['b', 'sum_pred'] == 3.5 and t.loc['b', 'bias'] == pytest.approx(-0.5 / 3)
    assert t.loc['b', 'mae'] == pytest.approx((0 + 1 + 0.5) / 3) and t.loc['b', 'n_days'] == 2 and t.loc['a', 'share_zero'] == 0.5
    assert t.loc['c', 'n'] == 0 and t.loc['c', 'support'] == 'empty' and pd.isna(t.loc['c', 'mae'])
    assert t.loc['a', 'support'] == 'small_support_descriptive_only' and t.loc['b', 'support'] == 'adequate_support'
    assert t['n'].sum() == len(df) and t['sum_y'].sum() == df['y'].sum() and t['sum_pred'].sum() == df['m'].sum()


def test_slice_labels(f):
    fr = pd.DataFrame({'target_date': ['2022-04-13', '2022-04-10', '2022-05-01', '2022-05-02'], 'y': [0.0, 1.0, 12.0, 3.0],
                       'fest_songkran_in': [1, 0, 0, np.nan], 'fest_songkran_pre_1_3': [1, 1, 0, 0],
                       'bank_calendar_known_asof': [1, 0, np.nan, 1], 'wx_a': [1.0, np.nan, np.nan, 2.0], 'wx_b': [1.0, 1.0, np.nan, 2.0],
                       'trf': [np.nan, 1.0, 1.0, 1.0]})
    for _, c in f['FESTIVAL_WINDOWS']:
        if c not in fr.columns:
            fr[c] = 0
    j, n_overlap = f['add_slice_columns'](fr, ['wx_a', 'wx_b'], ['trf'], 10.0)
    assert list(j['sl_festival']) == ['songkran_in', 'songkran_pre_1_3', 'none', 'unknown'] and n_overlap == 1
    assert list(j['sl_weather']) == ['available', 'partial', 'missing', 'available']
    assert list(j['sl_traffic']) == ['missing', 'available', 'available', 'available']
    assert list(j['sl_bank_calendar']) == ['known_asof', 'not_known_asof', 'missing', 'known_asof']
    assert list(j['sl_outcome_bin']) == ['0', '1', '10+', '2-3'] and list(j['sl_high_count']) == ['below_10', 'below_10', 'high_ge_10', 'below_10']
    assert list(j['sl_weekday']) == ['Wed', 'Sun', 'Sun', 'Mon']
    assert f['high_count_threshold']([0] * 99 + [7]) == 1.0 and f['high_count_threshold']([5] * 10) == 5.0


# ---------- calibration ----------
def test_calibration_ties_and_empty_bins(f):
    edges = f['calibration_edges']([1.0, 1.0, 1.0, 1.0, 2.0], 4)    # duplicate quantiles collapse, no crash
    assert list(edges) == [1.0, 2.0]
    one = f['calibration_edges']([0.7] * 20, 10)
    assert list(one) == [0.7]
    t1 = f['calibration_table']([1, 0, 2], [0.7, 0.7, 0.7], one, 1, 1)
    assert len(t1) == 1 and t1.loc[0, 'n'] == 3 and t1.loc[0, 'mean_y'] == pytest.approx(1.0)
    t = f['calibration_table']([0, 1, 4], [0.5, 1.0, 3.0], [1.0, 2.0, 3.0], 2, 1)   # 0.5 below range -> first bin; 3.0 -> last bin
    assert t['n'].tolist() == [2, 1] and t.loc[0, 'sum_y'] == 1 and t.loc[1, 'obs_over_pred'] == pytest.approx(4 / 3)
    assert t.loc[1, 'support'] == 'small_support_descriptive_only'
    e = f['calibration_table']([0, 1], [0.5, 1.5], [1.0, 2.0, 3.0], 1, 1)            # nothing reaches the last bin: kept with n = 0
    assert e['n'].tolist() == [2, 0] and e.loc[1, 'support'] == 'empty' and pd.isna(e.loc[1, 'mean_pred'])


# ---------- paired keys / ablation ----------
def test_paired_keys(f):
    df = pd.DataFrame({'k': ['a', 'b'], 'p': [1.0, 2.0], 'q': [1.0, np.nan]})
    with pytest.raises(ValueError):
        f['paired_columns'](df, 'p', 'q', ['k'])
    with pytest.raises(ValueError):
        f['paired_columns'](pd.concat([df, df]), 'p', 'p', ['k'])
    left, right = pd.DataFrame({'k': ['a', 'b'], 'p': [1.0, 2.0]}), pd.DataFrame({'k': ['a', 'c'], 'p': [1.0, 2.0]})
    with pytest.raises(ValueError):
        f['paired_on_keys'](left, right, ['k'], 'p')
    assert len(f['paired_on_keys'](left, left.iloc[::-1], ['k'], 'p')) == 2


def test_ablation_rows_hand_values(f):
    oof = pd.DataFrame({'fold': ['A', 'A', 'B', 'B'], 'k': ['1', '2', '3', '4'], 'target_date': ['2022-01-01', '2022-01-02', '2022-07-01', '2022-07-02'],
                        'y': [1.0] * 4, 'c__core': [1.0, 1.0, 2.0, 2.0], 'c__calendar': [1.0] * 4})
    boot = {'n_resamples': 50, 'seed': 42, 'ci': 0.95, 'block_days': 7}
    r = f['ablation_rows'](oof, [('calendar', 'core'), ('full', 'core')], ['c'], {'c': 'rf'}, 1e-9, np.array([0, 0, 1, 1]), boot, ['k'])
    ok = r[r['status'].eq('ok')].iloc[0]
    d2 = 2 * (math.log(0.5) + 1)   # y=1, mu=2
    assert ok['delta_deviance'] == pytest.approx(-d2 / 2) and ok['relative_change'] == pytest.approx(-1.0)
    assert ok['folds_improved'] == 1 and ok['n_folds'] == 2 and ok['effect'] == 'benefit' and ok['delta_mae'] == pytest.approx(-0.5)
    assert r[r['variant'].eq('full')]['status'].tolist() == ['incomplete']   # missing method is reported, not dropped


# ---------- tamper rejection ----------
def _fake_11(tmp, f):
    out = tmp / 'out11'
    rep, md = out / 'reports' / 'v2' / 'models', out / 'data' / 'v2' / 'models'
    rep.mkdir(parents=True)
    md.mkdir(parents=True)
    (md / 'oof_predictions_daily.csv.gz').write_bytes(b'oof')
    (rep / 'oof_metrics_pooled.csv').write_text('a\n1\n')
    hashes = {'experiment_lock_sha256': 'e', 'notebook11_functions_sha256': 'n'}
    lock = {'schema': f['SELECTION_LOCK_SCHEMA'], 'hashes': hashes,
            'files': [{'path': 'data/v2/models/oof_predictions_daily.csv.gz', 'sha256': f['sha256_file'](md / 'oof_predictions_daily.csv.gz')},
                      {'path': 'reports/v2/models/oof_metrics_pooled.csv', 'sha256': f['sha256_file'](rep / 'oof_metrics_pooled.csv')}]}
    f['write_json'](rep / 'selection_lock.json', lock)
    return out, rep, md, hashes


def test_selection_lock_tamper_rejected(f, tmp_path):
    out, rep, md, hashes = _fake_11(tmp_path, f)
    sha = f['sha256_file'](rep / 'selection_lock.json')
    assert f['verify_selection_lock'](rep / 'selection_lock.json', sha, hashes, out)['schema'] == f['SELECTION_LOCK_SCHEMA']
    with pytest.raises(f['LockError']):
        f['verify_selection_lock'](rep / 'selection_lock.json', sha, dict(hashes, notebook11_functions_sha256='other'), out)
    (md / 'oof_predictions_daily.csv.gz').write_bytes(b'tampered')
    with pytest.raises(f['LockError']):
        f['verify_selection_lock'](rep / 'selection_lock.json', sha, hashes, out)
    with pytest.raises(f['LockError']):
        f['verify_selection_lock'](rep / 'selection_lock.json', '0' * 64, hashes, out)


def test_report_outputs_and_completion_tamper_rejected(f, tmp_path):
    out, rep, md, _ = _fake_11(tmp_path, f)
    man = {'report_outputs': [{'path': 'oof_metrics_pooled.csv', 'sha256': f['sha256_file'](rep / 'oof_metrics_pooled.csv')},
                              {'path': 'run_manifest_model.json', 'sha256': 'stale-runner-log-hash'}]}
    got = f['verify_report_outputs'](man, rep, required=('oof_metrics_pooled.csv',))
    assert list(got) == ['oof_metrics_pooled.csv']   # legacy manifest: mutable runner log excluded explicitly, not silently "verified"
    new = {'report_outputs': man['report_outputs'][:1], 'report_outputs_excluded': {'run_manifest_model.json': 'runner-owned'}}
    assert list(f['verify_report_outputs'](new, rep, required=('oof_metrics_pooled.csv',))) == ['oof_metrics_pooled.csv']
    with pytest.raises(f['DependencyError']):   # 11 may not exclude real evidence from its hashes
        f['verify_report_outputs'](dict(new, report_outputs_excluded={'selection_lock.json': 'x'}), rep, required=('oof_metrics_pooled.csv',))
    with pytest.raises(f['DependencyError']):
        f['verify_report_outputs'](man, rep, required=('oof_metrics_pooled.csv', 'selection_lock.json'))
    (rep / 'oof_metrics_pooled.csv').write_text('a\n2\n')
    with pytest.raises(f['DependencyError']):
        f['verify_report_outputs'](man, rep, required=('oof_metrics_pooled.csv',))
    with pytest.raises(f['DependencyError']):
        f['verify_model_manifest']({'schema': f['MODEL_MANIFEST_SCHEMA'], 'producer': f['MODEL_PRODUCER'], 'status': 'running'}, ['daily'])
    with pytest.raises(f['DependencyError']):
        f['verify_model_manifest']({'schema': f['MODEL_MANIFEST_SCHEMA'], 'producer': f['MODEL_PRODUCER'], 'status': 'completed',
                                    'production_ready': True, 'operational_status': 'BLOCKED'}, ['daily'])
    with pytest.raises(f['DependencyError']):
        f['verify_file'](rep / 'missing.csv', 'x', 'missing input')


def _runner_log(path, rep, status='ok', nb_status='ok', stage='model'):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({'stage': stage, 'status': status, 'roots': {'model_reports': str(rep)},
                                'notebooks': [{'notebook': '11_v2_model_experiments', 'status': nb_status, 'cells_completed': 11}]}))
    return path


@pytest.mark.parametrize('layout', ['canonical', 'legacy_report_local'])
def test_model_runner_log_layouts_and_status(f, tmp_path, layout):
    out, rep, md, _ = _fake_11(tmp_path, f)
    paths = f['model_runner_log_paths'](rep)
    assert paths['canonical'] == rep.parent / 'run_manifest_model.json' and paths['legacy_report_local'] == rep / 'run_manifest_model.json'
    with pytest.raises(f['DependencyError']):   # no log at all: completion of the final checks cell is unproven
        f['verify_model_runner_logs'](rep)
    p = _runner_log(paths[layout], rep)
    got = f['verify_model_runner_logs'](rep)
    assert list(got) == [layout] and got[layout]['status'] == 'ok' and got[layout]['path'] == str(p)
    for kw in ({'status': 'failed', 'nb_status': 'failed'}, {'status': 'running', 'nb_status': 'running'}, {'nb_status': 'failed'},
               {'status': None}, {'stage': 'evaluate'}):
        _runner_log(p, rep, **kw)
        with pytest.raises(f['DependencyError']):
            f['verify_model_runner_logs'](rep)
    _runner_log(p, tmp_path / 'other' / 'reports' / 'v2' / 'models')   # log of a different 11 run
    with pytest.raises(f['DependencyError']):
        f['verify_model_runner_logs'](rep)
    _runner_log(p, rep)
    assert f['verify_model_runner_logs'](rep)[layout]['status'] == 'ok'


def test_model_runner_logs_every_available_log_must_be_ok(f, tmp_path):
    out, rep, md, _ = _fake_11(tmp_path, f)
    paths = f['model_runner_log_paths'](rep)
    _runner_log(paths['canonical'], rep)
    _runner_log(paths['legacy_report_local'], rep, status='failed', nb_status='failed')
    with pytest.raises(f['DependencyError']):
        f['verify_model_runner_logs'](rep)
    _runner_log(paths['legacy_report_local'], rep)
    assert sorted(f['verify_model_runner_logs'](rep)) == ['canonical', 'legacy_report_local']


def test_compare_selection_and_snapshot(f, tmp_path):
    s = {'recommended_method': 'baseline_b', 'recommendation_kind': 'k', 'best_candidate': 'c__core', 'strongest_baseline': 'baseline_b',
         'family_best': {'poisson': 'c__core'}, 'gate': {'passed': False}}
    sel = {'daily': s}
    pick = {'daily': {k: s[k] for k in ('recommended_method', 'recommendation_kind', 'best_candidate', 'strongest_baseline', 'family_best')}}
    assert f['compare_selection'](sel, sel, pick)
    with pytest.raises(f['LockError']):
        f['compare_selection'](sel, {'daily': dict(s, recommended_method='c__core')}, pick)
    with pytest.raises(f['LockError']):   # gate failed but the candidate is recommended
        bad = dict(s, recommended_method='c__core')
        f['compare_selection']({'daily': bad}, {'daily': bad}, {'daily': dict(pick['daily'], recommended_method='c__core')})
    p = tmp_path / 'x.txt'
    p.write_text('a')
    b = f['snapshot']([p])
    p.write_text('b')
    assert f['snapshot_diff'](b, f['snapshot']([p])) == [str(p)]


def test_join_context_rejects_missing_ineligible_and_relabelled(f):
    ctx = pd.DataFrame({'k': ['a', 'b', 'c'], 'ctx_eligible': [True, True, False], 'ctx_split': ['train'] * 3, 'ctx_y': [1.0, 0.0, 2.0]})
    ok = f['join_context'](pd.DataFrame({'k': ['a', 'b'], 'y': [1.0, 0.0]}), ctx, ['k'])
    assert len(ok) == 2
    for pred in (pd.DataFrame({'k': ['a', 'z'], 'y': [1.0, 0.0]}), pd.DataFrame({'k': ['c'], 'y': [2.0]}), pd.DataFrame({'k': ['a'], 'y': [5.0]})):
        with pytest.raises(f['DependencyError']):
            f['join_context'](pred, ctx, ['k'])


def test_check_write_roots(f, tmp_path):
    ro = tmp_path / 'models'
    assert f['check_write_roots']([('a', tmp_path / 'analysis')], [('11', ro)], [tmp_path / 'v2' / 'panel.csv.gz'])
    with pytest.raises(ValueError):
        f['check_write_roots']([('a', ro / 'analysis')], [('11', ro)], [])
    with pytest.raises(ValueError):
        f['check_write_roots']([('a', tmp_path / 'v2')], [], [tmp_path / 'v2' / 'panel.csv.gz'])


# ---------- runner evaluate stage ----------
def test_runner_evaluate_stage(runner, tmp_path):
    assert runner.notebooks_for_stage('evaluate') == ['12_v2_evaluation_error_analysis']
    assert runner.notebooks_for_stage('all') == ['09_external_collection_date_evidence', '10_v2_preparation_features_leakage']
    assert runner.notebooks_for_stage('model') == ['11_v2_model_experiments']
    r = runner.resolve_roots(tmp_path / 'out', tmp_path / 'ext', tmp_path / 'v1', stage='evaluate', model_dir=tmp_path / 'm' / 'reports',
                             model_data_dir=tmp_path / 'm' / 'data', preparation_dir=tmp_path / 'prep', prep_data_dir=tmp_path / 'p10')
    assert r['analysis_reports'] == (tmp_path / 'out').resolve() / 'reports' / 'v2' / 'analysis'
    env = runner.build_env(r, base={'ROADAWARE_V2_MODEL_REPORT_DIR': '/stale', 'PATH': '/bin'})
    assert env['ROADAWARE_V2_MODEL_REPORT_DIR'] == str(r['model_reports']) and env['ROADAWARE_V2_MODEL_DATA_ROOT'] == str(r['model_data'])
    assert env['ROADAWARE_V2_ANALYSIS_DATA_ROOT'] == str(r['analysis_data']) and env['ROADAWARE_V2_DATA_ROOT'] == str(r['prep_data'])
    assert env['ROADAWARE_V2_MODEL_NOTEBOOK'].endswith('11_v2_model_experiments.ipynb')
    with pytest.raises(ValueError):   # analysis output inside the read-only 11 report dir
        runner.resolve_roots(tmp_path / 'out', tmp_path / 'ext', tmp_path / 'v1', stage='evaluate', model_dir=tmp_path / 'out' / 'reports' / 'v2')
    with pytest.raises(ValueError):   # analysis data root would contain the read-only 10 data root
        runner.resolve_roots(tmp_path / 'out', tmp_path / 'ext', tmp_path / 'v1', stage='evaluate', prep_data_dir=tmp_path / 'out' / 'data' / 'v2' / 'analysis' / 'x',
                             model_dir=tmp_path / 'm1', model_data_dir=tmp_path / 'm2')
    assert 'not found' in runner.evaluate_preconditions(r)
    r['model_reports'].mkdir(parents=True)
    (r['model_reports'] / 'model_manifest.json').write_text('{}')
    assert 'runner log' in runner.evaluate_preconditions(r)
    (r['model_reports'].parent / 'run_manifest_model.json').write_text('{}')   # canonical location (12 itself checks its status)
    assert runner.evaluate_preconditions(r) is None
    assert runner.model_run_logs(r['model_reports']) == [r['model_reports'].parent / 'run_manifest_model.json', r['model_reports'] / 'run_manifest_model.json']
    r['analysis_reports'].mkdir(parents=True)
    (r['analysis_reports'] / 'analysis_manifest.json').write_text('{}')
    assert 'already exists' in runner.evaluate_preconditions(r)
    assert 'model_reports' not in runner.resolve_roots(tmp_path / 'out', tmp_path / 'ext', tmp_path / 'v1', stage='prepare')
