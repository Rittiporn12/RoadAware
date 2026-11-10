"""Fixture tests for RoadAware model notebooks 06 and 07 (tiny synthetic data; no Jupyter kernel needed).

Each test executes the notebooks' own '# FUNCTIONS' code cells (07 on top of 06, exactly as notebook 07 does), so the
logic under test is what the notebooks run. Expected values are computed by hand or by an independent oracle
(scikit-learn metrics), not by re-implementing the notebook code. Tiny model parameters below are deliberately small;
the real protocol configuration is checked separately and is never changed by these tests. Run from the repository root:
    .venv/bin/python -m pytest backend/tests -q
"""
import copy
import hashlib
import importlib.util
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

BACKEND = Path(__file__).resolve().parents[1]
NB06 = BACKEND / 'notebooks' / '06_baseline_candidate_models.ipynb'
NB07 = BACKEND / 'notebooks' / '07_evaluation_experiment_results.ipynb'
RUNNER = BACKEND / 'scripts' / 'run_model_notebooks.py'
XCFG = json.loads((BACKEND / 'config' / 'model_experiment_v1.json').read_text('utf-8'))
DCFG = json.loads((BACKEND / 'config' / 'data_pipeline.json').read_text('utf-8'))
TZ = DCFG['timezone_assumption']
FEATURES = XCFG['features']
TARGET = 'y_recorded_count'
OOF = 'oof_train_backtest'
FAMILIES = ['poisson', 'random_forest', 'hist_gradient_boosting']

# Tiny fixture parameters (fast and convergent on ~100 rows); the real grid lives in model_experiment_v1.json.
TINY = [
    {'id': 'poisson_tiny', 'family': 'poisson', 'deviance_domain': 'floor', 'params': {'alpha': 1.0, 'max_iter': 1000, 'tol': 1e-6}},
    {'id': 'rf_tiny', 'family': 'random_forest', 'deviance_domain': 'floor',
     'params': {'n_estimators': 8, 'max_depth': 4, 'min_samples_leaf': 2, 'max_features': 0.7, 'criterion': 'poisson',
                'random_state': 0, 'n_jobs': 2}},
    {'id': 'hgb_tiny', 'family': 'hist_gradient_boosting', 'deviance_domain': 'floor',
     'params': {'max_iter': 15, 'max_leaf_nodes': 4, 'min_samples_leaf': 2, 'learning_rate': 0.2, 'l2_regularization': 0.0,
                'loss': 'poisson', 'early_stopping': False, 'random_state': 0}},
]


def load_functions():
    nb = json.loads(NB06.read_text('utf-8'))
    srcs = [''.join(c['source']) if isinstance(c['source'], list) else c['source'] for c in nb['cells'] if c['cell_type'] == 'code']
    hits = [s for s in srcs if s.lstrip().startswith('# FUNCTIONS')]
    assert len(hits) == 1, 'notebook 06: expected exactly one FUNCTIONS cell'
    ns = {}
    exec(compile(hits[0], '06:FUNCTIONS', 'exec'), ns)
    return ns


@pytest.fixture(scope='module')
def f():
    return load_functions()


def y_rule(p, d):
    """Province A is busy, B is quiet: a model that learns from its own Train rows must rank A above B."""
    return 3 + d.day % 2 if p == 'A' else int(d.day % 3 == 0)


def make_panel(start, end, provinces=('A', 'B'), y_of=y_rule, split='train', eligible=True):
    rows = [{'province': p, 'target_date': d, TARGET: int(y_of(p, d))}
            for d in pd.date_range(start, end, freq='D') for p in provinces]
    df = pd.DataFrame(rows)
    d = df['target_date']
    df['target_start'] = d.dt.tz_localize(TZ)
    df['target_end'] = df['target_start'] + pd.Timedelta(days=1)
    df['issue_time'] = df['target_start'] - pd.Timedelta(hours=6)  # 18:00 the previous day
    df['split'] = split
    df['training_eligible'] = eligible
    df['possibly_undercounted'] = False
    df['boundary_excluded'] = False
    df['day_of_week'] = d.dt.dayofweek
    df['month'] = d.dt.month
    df['day_of_month'] = d.dt.day
    df['day_of_year'] = d.dt.dayofyear
    df['is_weekend'] = (d.dt.dayofweek >= 5).astype(int)
    return df


def fit_ok(f, spec, df):
    b = f['fit_bundle'](spec, df, df[TARGET], XCFG['encoding'], 2, FEATURES)
    assert b['fit_info']['status'] == 'ok', b['fit_info']
    return b


# ---------------------------------------------------------------- protocol / config

def test_real_config_matches_locked_protocol_and_has_three_distinct_families(f):
    assert f['validate_experiment_config'](XCFG) == []
    fams = [c['family'] for c in XCFG['candidates']]
    assert sorted(set(fams)) == sorted(FAMILIES)
    assert {fam: fams.count(fam) for fam in FAMILIES} == {'poisson': 3, 'random_forest': 2, 'hist_gradient_boosting': 2}
    assert XCFG['production_enabled'] is False and XCFG['features'] == DCFG['feature_allowlist']


def test_config_drift_is_reported(f):
    bad = json.loads(json.dumps(XCFG))
    bad['candidates'][3]['params']['n_estimators'] = 81
    assert any(p.startswith('candidates') for p in f['validate_experiment_config'](bad))
    del bad['bootstrap']
    assert 'bootstrap: missing from config' in f['validate_experiment_config'](bad)


def test_strict_boolean_parsing_never_treats_false_string_as_true(f):
    s = pd.Series(['True', 'False', ' false ', '1', '0'], name='training_eligible')
    assert f['as_bool'](s).tolist() == [True, False, False, True, False]
    with pytest.raises(ValueError):
        f['as_bool'](pd.Series(['yes'], name='x'))
    panel = make_panel('2021-01-01', '2021-01-02')
    panel['training_eligible'] = ['False', 'True', 'False', 'True']
    assert len(f['cohort'](panel)) == 2


# ---------------------------------------------------------------- metrics

def test_metrics_hand_computed(f):
    m = f['regression_metrics']([0, 1, 3], [1, 1, 1])
    assert m['mae'] == pytest.approx(1.0)
    assert m['rmse'] == pytest.approx(math.sqrt(5 / 3))
    assert m['bias'] == pytest.approx(-1 / 3)
    assert m['wape'] == pytest.approx(3 / 4)
    assert m['observed_total'] == 4 and m['predicted_total'] == 3
    # unit deviances: y=0,mu=1 -> 2 ; y=1,mu=1 -> 0 ; y=3,mu=1 -> 2*(3 ln 3 - 2)
    assert m['mean_poisson_deviance'] == pytest.approx((2 + 0 + 2 * (3 * math.log(3) - 2)) / 3)
    assert m['n_floored_for_deviance'] == 0


def test_metrics_agree_with_sklearn_oracle_with_weights(f):
    from sklearn.metrics import mean_absolute_error, mean_poisson_deviance, mean_squared_error
    rng = np.random.default_rng(3)
    y, p, w = rng.poisson(1.5, 200), rng.uniform(0.1, 3, 200), rng.uniform(0.5, 2, 200)
    m = f['regression_metrics'](y, p, w)
    assert m['mae'] == pytest.approx(mean_absolute_error(y, p, sample_weight=w))
    assert m['rmse'] == pytest.approx(math.sqrt(mean_squared_error(y, p, sample_weight=w)))
    assert m['mean_poisson_deviance'] == pytest.approx(mean_poisson_deviance(y, p, sample_weight=w))


def test_deviance_domain_zero_predictor_floor_and_wape_null(f):
    zero = f['regression_metrics']([0, 2], [0, 0], deviance_domain='undefined')
    assert zero['mean_poisson_deviance'] is None and zero['mae'] == pytest.approx(1.0)
    floored = f['regression_metrics']([0, 2], [0, 1], deviance_domain='floor', floor=1e-9)
    assert floored['n_floored_for_deviance'] == 1 and math.isfinite(floored['mean_poisson_deviance'])
    assert f['regression_metrics']([0, 0], [0.5, 0.5])['wape'] is None
    with pytest.raises(ValueError):
        f['regression_metrics']([1], [1], deviance_domain='clip')
    with pytest.raises(ValueError):
        f['unit_poisson_deviance']([1.0], [0.0])


@pytest.mark.parametrize('y,p', [([1, 2], [1, -0.1]), ([1, 2], [1, np.nan]), ([1, 2], [1, np.inf]),
                                 ([-1, 2], [1, 1]), ([np.nan, 2], [1, 1]), ([1, 2, 3], [1, 1])])
def test_invalid_labels_or_predictions_are_rejected(f, y, p):
    with pytest.raises(ValueError):
        f['regression_metrics'](y, p)


def test_strict_json_rejects_infinity_and_maps_nan_to_null(f, tmp_path):
    assert f['to_jsonable']({'a': np.float64('nan'), 'b': np.int64(2)}) == {'a': None, 'b': 2}
    with pytest.raises(ValueError):
        f['write_json'](tmp_path / 'x.json', {'a': float('inf')})


# ---------------------------------------------------------------- numerical agreement (RF reload regression)

def test_reload_tolerance_accepts_roundoff_and_rejects_material_change(f):
    a = np.array([0.25, 1.0, 3.7, 0.0])
    tol = f['RELOAD_TOLERANCE']
    assert tol == {'rtol': 1e-12, 'atol': 1e-12}
    r = f['compare_predictions'](a, a + 1.7763568394002505e-15)  # magnitude measured on the real forest
    assert r['within_tolerance'] and not r['exact_equal'] and 0 < r['max_abs_diff'] < 1e-14
    assert f['compare_predictions'](a, a.copy())['exact_equal']
    moved = a.copy()
    moved[2] += 1e-6
    r = f['compare_predictions'](a, moved)
    assert not r['within_tolerance'] and r['n_outside_tolerance'] == 1 and r['max_abs_diff'] == pytest.approx(1e-6)
    with pytest.raises(AssertionError, match='max_abs_diff'):
        f['assert_predictions_agree'](a, moved, 'rf reload')
    near = a.copy()
    near[1] += 5e-12  # bound at |a|=1 is 2e-12
    assert not f['compare_predictions'](a, near)['within_tolerance']
    with pytest.raises(ValueError):
        f['compare_predictions'](a, a[:3])
    with pytest.raises(ValueError):
        f['compare_predictions'](a, -a - 1)


def test_parallel_forest_repeat_predictions_agree_within_tolerance(f):
    df = make_panel('2021-01-01', '2021-03-31')
    b = fit_ok(f, TINY[1], df)
    p1, p2 = f['predict_bundle'](b, df), f['predict_bundle'](b, df)
    assert f['compare_predictions'](p1, p2)['within_tolerance']


# ---------------------------------------------------------------- temporal folds

FOLD_CFG = [{'fold': 1, 'eval_start': '2022-01-01', 'eval_end': '2022-01-05'},
            {'fold': 2, 'eval_start': '2022-01-06', 'eval_end': '2022-01-10'}]


def test_fold_cutoff_excludes_label_ending_after_first_issue_and_keys_are_disjoint(f):
    coh = make_panel('2021-12-01', '2022-01-10')
    folds = f['build_temporal_folds'](coh, FOLD_CFG, 18, 1, TZ)
    f1, f2 = folds
    # first issue for 2022-01-01 is 2021-12-31 18:00; the label of 2021-12-31 ends 2022-01-01 00:00 > cutoff
    assert f1['first_issue_time'] == pd.Timestamp('2021-12-31 18:00', tz=TZ).isoformat()
    assert f1['fit_last_date'] == '2021-12-30' and f1['n_fit_rows'] == 30 * 2
    assert f1['eval_first_date'] == '2022-01-01' and f1['eval_last_date'] == '2022-01-05' and f1['n_eval_rows'] == 10
    assert f2['fit_last_date'] == '2022-01-04'  # expanding window, again one day short of the evaluation start
    for fd in folds:
        fit, ev = coh.loc[fd['fit_index']], coh.loc[fd['eval_index']]
        assert (fit['target_end'] <= pd.Timestamp(fd['first_issue_time'])).all()
        assert not set(zip(fit['province'], fit['target_date'])) & set(zip(ev['province'], ev['target_date']))
        assert fd['eval_label_sum'] == int(ev[TARGET].sum())


def test_fold_violations_negative_controls(f):
    coh = make_panel('2021-12-25', '2022-01-03')
    cutoff = f['first_issue_time']('2022-01-01', 18, 1, TZ)
    ev = coh[coh['target_date'] >= '2022-01-01']
    leaky = coh[coh['target_date'] <= '2021-12-31']  # includes the 2021-12-31 label that ends after the cutoff
    assert any('end after the first evaluation issue' in v for v in f['fold_violations'](leaky, ev, cutoff))
    overlap = pd.concat([coh[coh['target_date'] <= '2021-12-30'], ev.iloc[:1]])
    msgs = f['fold_violations'](overlap, ev, cutoff)
    assert any('keys in both fit and evaluation' in v for v in msgs)
    dup = pd.concat([ev, ev.iloc[:1]])
    assert any('duplicate' in v for v in f['fold_violations'](coh[coh['target_date'] <= '2021-12-30'], dup, cutoff))


def test_province_support_requires_positive_past_labels(f):
    # B appears in the fit window only with zero labels; C has no fit rows at all
    coh = make_panel('2021-12-20', '2022-01-03', provinces=('A', 'B', 'C'),
                     y_of=lambda p, d: (2 if p == 'A' else 0) if d < pd.Timestamp('2022-01-01') else 1)
    coh = coh[~((coh['province'] == 'C') & (coh['target_date'] < '2022-01-01'))]
    fd = f['build_temporal_folds'](coh, [{'fold': 1, 'eval_start': '2022-01-01', 'eval_end': '2022-01-03'}], 18, 1, TZ)[0]
    assert fd['n_fit_provinces_any_row'] == 2 and fd['n_fit_provinces_positive_label'] == 1
    assert fd['n_eval_provinces'] == 3 and fd['n_eval_provinces_without_positive_past_label'] == 2
    assert fd['eval_provinces_without_positive_past_label'] == 'B;C' and fd['n_eval_provinces_without_any_past_row'] == 1


# ---------------------------------------------------------------- baselines

def test_baseline_means_fallbacks_and_smoothing_hand_computed(f):
    X = pd.DataFrame({'province': ['A', 'A', 'A', 'A', 'B'], 'day_of_week': [0, 0, 1, 2, 0]})
    y = np.array([2.0, 4.0, 0.0, 2.0, 1.0])
    st = f['fit_baseline']('province_weekday_smoothed', {'pseudo_obs': 10}, X, y)
    assert st['global_mean'] == pytest.approx(9 / 5)
    assert st['province_mean'] == pytest.approx({'A': 2.0, 'B': 1.0})
    assert st['province_weekday_mean']['A']['0'] == pytest.approx((6 + 10 * 2.0) / (2 + 10))
    Xt = pd.DataFrame({'province': ['A', 'A', 'Z'], 'day_of_week': [0, 6, 0]})
    p = f['predict_baseline']('province_weekday_smoothed', st, Xt)
    assert p == pytest.approx([26 / 12, 2.0, 9 / 5])  # smoothed cell; unseen weekday -> province; unknown province -> global
    pm = f['fit_baseline']('province_mean', {}, X, y)
    assert f['predict_baseline']('province_mean', pm, Xt) == pytest.approx([2.0, 2.0, 9 / 5])
    assert f['predict_baseline']('zero', {}, Xt).tolist() == [0, 0, 0]


def test_baseline_bundle_rejects_negative_output(f):
    df = make_panel('2021-01-01', '2021-01-10')
    b = f['fit_bundle'](XCFG['baselines'][1], df, df[TARGET], XCFG['encoding'], 2, FEATURES)
    b['baseline_state']['global_mean'] = -1.0
    with pytest.raises(ValueError, match='negative'):
        f['predict_bundle'](b, df)


# ---------------------------------------------------------------- three real families on tiny fixtures

@pytest.mark.parametrize('spec', TINY, ids=[s['family'] for s in TINY])
def test_family_learns_from_train_only_and_handles_unknown_categories(f, spec):
    train = make_panel('2021-01-01', '2021-02-28')
    b = fit_ok(f, spec, train)
    ct = b['pipeline'].named_steps['features']
    enc = ct.named_transformers_['ordinal' if spec['family'] == 'hist_gradient_boosting' else 'onehot']
    assert list(enc.categories_[0]) == ['A', 'B']  # province categories come from the fit rows only
    if spec['family'] == 'hist_gradient_boosting':
        assert list(b['pipeline'].named_steps['model'].is_categorical_) == [True] * 4 + [False] * 2
        assert b['pipeline'].named_steps['model'].n_iter_ == spec['params']['max_iter']  # no early stopping
    p = f['predict_bundle'](b, train)
    assert p[train['province'].to_numpy() == 'A'].mean() > p[train['province'].to_numpy() == 'B'].mean()
    unseen = make_panel('2021-12-15', '2021-12-16', provinces=('ZZ', 'A'))  # unseen province, month and day_of_year
    q = f['predict_bundle'](b, unseen)
    assert np.isfinite(q).all() and (q >= 0).all() and len(q) == 4


def test_nonconverged_and_failed_fits_are_ineligible_not_scored(f):
    df = make_panel('2021-01-01', '2021-02-28')
    nc = f['fit_bundle']({'id': 'p1', 'family': 'poisson', 'deviance_domain': 'floor', 'params': {'alpha': 1e-4, 'max_iter': 1, 'tol': 1e-12}},
                         df, df[TARGET], XCFG['encoding'], 2, FEATURES)
    assert nc['fit_info']['status'] == 'nonconverged' and nc['fit_info']['converged'] is False
    with pytest.raises(RuntimeError, match='not eligible'):
        f['predict_bundle'](nc, df)
    bad = f['fit_bundle']({'id': 'x', 'family': 'svm', 'deviance_domain': 'floor', 'params': {}}, df, df[TARGET], XCFG['encoding'], 2, FEATURES)
    assert bad['fit_info']['status'] == 'failed' and 'svm' in bad['fit_info']['error'] and bad['pipeline'] is None
    with pytest.raises(RuntimeError, match='not eligible'):
        f['predict_bundle'](bad, df)


def test_backtest_scores_every_method_on_identical_cells_and_marks_ineligible(f):
    coh = make_panel('2021-12-01', '2022-01-10')
    folds = f['build_temporal_folds'](coh, FOLD_CFG, 18, 1, TZ)
    nc = {'id': 'poisson_nc', 'family': 'poisson', 'deviance_domain': 'floor', 'params': {'alpha': 1e-4, 'max_iter': 1, 'tol': 1e-12}}
    specs = list(XCFG['baselines']) + TINY + [nc]
    oof, log = f['run_backtest'](coh, folds, specs, XCFG['encoding'], FEATURES, 2)
    assert len(oof) == sum(fd['n_eval_rows'] for fd in folds) and not oof.duplicated(['province', 'target_date']).any()
    om = f['oof_metrics_table'](oof, specs, log, FOLD_CFG, 1e-9)
    ok = om[om['eligible']]
    assert set(ok['spec_id']) == {s['id'] for s in specs} - {'poisson_nc'}
    assert ok['n_rows'].nunique() == 1 and int(ok['n_rows'].iloc[0]) == len(oof)
    bad = om.set_index('spec_id').loc['poisson_nc']
    assert not bad['eligible'] and pd.isna(bad['mean_poisson_deviance'])
    zero = om.set_index('spec_id').loc['baseline_zero']
    assert zero['eligible'] and pd.isna(zero['mean_poisson_deviance']) and zero['mae'] > 0  # raw MAE kept, deviance undefined
    sel = f['select_models'](om, FAMILIES)
    assert sel['selected_family'] in FAMILIES and sel['best_baseline'] != 'baseline_zero'


def test_oof_scope_rejects_later_year_rows_and_out_of_window_dates(f):
    oof = pd.DataFrame({'fold': [1, 1], 'province': ['A', 'B'], 'target_date': pd.to_datetime(['2022-01-01', '2022-01-02']),
                        'split': ['train', 'train']})
    assert f['validate_oof_scope'](oof, FOLD_CFG[:1])
    with pytest.raises(ValueError, match='outside the train split'):
        f['validate_oof_scope'](oof.assign(split=['train', 'validation']), FOLD_CFG[:1])
    with pytest.raises(ValueError, match='outside its evaluation window'):
        f['validate_oof_scope'](oof.assign(target_date=pd.to_datetime(['2022-01-01', '2024-01-02'])), FOLD_CFG[:1])


# ---------------------------------------------------------------- fresh-interpreter bundle reload

RELOAD_SCRIPT = r'''
import json, sys
import joblib, numpy as np, pandas as pd
bundle_path, x_path, nb_path, out_path = sys.argv[1:5]
bundle = joblib.load(bundle_path)  # unpickled BEFORE any notebook code exists in this interpreter
nb = json.load(open(nb_path, encoding='utf-8'))
src = [''.join(c['source']) for c in nb['cells'] if c['cell_type'] == 'code' and ''.join(c['source']).lstrip().startswith('# FUNCTIONS')][0]
ns = {}
exec(compile(src, 'FUNCTIONS', 'exec'), ns)
np.save(out_path, ns['predict_bundle'](bundle, pd.read_csv(x_path, dtype={'province': str})))
'''


@pytest.mark.parametrize('spec', [XCFG['baselines'][3]] + TINY, ids=['baseline'] + [s['family'] for s in TINY])
def test_bundle_reloads_in_fresh_interpreter_with_matching_predictions(f, spec, tmp_path):
    train = make_panel('2021-01-01', '2021-02-28')
    b = fit_ok(f, spec, train)
    sha = f['save_bundle'](b, tmp_path / 'b.joblib')
    X = make_panel('2021-03-01', '2021-03-05', provinces=('A', 'B', 'ZZ'))[FEATURES]
    X.to_csv(tmp_path / 'x.csv', index=False)
    subprocess.run([sys.executable, '-c', RELOAD_SCRIPT, str(tmp_path / 'b.joblib'), str(tmp_path / 'x.csv'), str(NB06),
                    str(tmp_path / 'p.npy')], check=True, capture_output=True, timeout=300, cwd=str(tmp_path))
    r = f['compare_predictions'](f['predict_bundle'](b, X), np.load(tmp_path / 'p.npy'))
    assert r['within_tolerance'], r
    assert f['load_bundle'](tmp_path / 'b.joblib', sha)['spec_id'] == spec['id']
    with pytest.raises(RuntimeError, match='sha256 mismatch'):
        f['load_bundle'](tmp_path / 'b.joblib', '0' * 64)


def test_bundle_with_notebook_defined_objects_is_refused(f, tmp_path):
    df = make_panel('2021-01-01', '2021-01-10')
    b = f['fit_bundle'](XCFG['baselines'][1], df, df[TARGET], XCFG['encoding'], 2, FEATURES)
    b['fit_info']['hook'] = lambda x: x
    with pytest.raises(TypeError, match='non-plain'):
        f['save_bundle'](b, tmp_path / 'b.joblib')


# ---------------------------------------------------------------- selection, ties, gate, lock

def metrics_frame(f, rows, scope=OOF):
    df = pd.DataFrame(rows, columns=['spec_id', 'family', 'eligible', 'mean_poisson_deviance', 'mae'])
    for k in f['METRIC_KEYS']:
        if k not in df:
            df[k] = 1.0
    df['evaluation_scope'] = scope
    return df


SEL_ROWS = [('baseline_zero', 'baseline', True, None, 0.9), ('baseline_b', 'baseline', True, 1.2, 0.6),
            ('baseline_a', 'baseline', True, 1.1, 0.6), ('poisson_x', 'poisson', True, 1.0, 0.7),
            ('poisson_a', 'poisson', True, 1.0, 0.7), ('rf_1', 'random_forest', True, 1.0, 0.1),
            ('hgb_bad', 'hist_gradient_boosting', False, 0.5, 0.1), ('hgb_2', 'hist_gradient_boosting', True, 1.0, 0.1)]


def test_selection_exact_ties_and_exclusions(f):
    sel = f['select_models'](metrics_frame(f, SEL_ROWS), FAMILIES)
    assert sel['best_per_family'] == {'poisson': 'poisson_a', 'random_forest': 'rf_1', 'hist_gradient_boosting': 'hgb_2'}
    assert sel['selected_candidate'] == 'poisson_a'  # three-way exact tie -> family order; lower MAE elsewhere is irrelevant
    assert sel['best_baseline'] == 'baseline_a'  # zero baseline (undefined deviance) excluded
    sel2 = f['select_models'](metrics_frame(f, SEL_ROWS), ['random_forest', 'poisson', 'hist_gradient_boosting'])
    assert sel2['selected_candidate'] == 'rf_1'
    again = f['select_models'](metrics_frame(f, list(reversed(SEL_ROWS))), FAMILIES)
    assert again == sel  # row order does not matter


def test_selection_refuses_later_year_metrics_and_missing_family(f):
    with pytest.raises(ValueError, match='later-year'):
        f['select_models'](metrics_frame(f, SEL_ROWS, scope='validation_2024'), FAMILIES)
    mixed = metrics_frame(f, SEL_ROWS)
    mixed.loc[0, 'evaluation_scope'] = 'reused_test_2025'
    with pytest.raises(ValueError):
        f['select_models'](mixed, FAMILIES)
    no_hgb = [r for r in SEL_ROWS if r[0] != 'hgb_2']
    with pytest.raises(RuntimeError, match='no eligible configuration for family hist_gradient_boosting'):
        f['select_models'](metrics_frame(f, no_hgb), FAMILIES)


def gate(f, cand_dev=0.9, cand_mae=0.5, fold_c=(0.8, 0.8, 0.8, 1.2), ci_high=-0.01):
    om = metrics_frame(f, [('c', 'poisson', True, cand_dev, cand_mae), ('b', 'baseline', True, 1.0, 0.5)])
    fm = pd.DataFrame([{'fold': i, 'spec_id': s, 'mean_poisson_deviance': v, 'evaluation_scope': OOF}
                       for i, c in enumerate(fold_c, 1) for s, v in (('c', c), ('b', 1.0))])
    return f['decision_gate']('c', 'b', om, fm, {'evaluation_scope': OOF, 'ci_high': ci_high}, XCFG['decision_gate'])


def test_decision_gate_each_criterion_can_keep_the_baseline(f):
    g = gate(f)
    assert g['stable_gain'] and g['recommended_reference'] == 'c' and g['recommended_reference_type'] == 'candidate'
    for kw, crit in [({'cand_mae': 0.52}, 'mae_ratio_candidate_over_baseline'),
                     ({'fold_c': (0.8, 0.8, 1.2, 1.2)}, 'folds_with_lower_deviance'),
                     ({'ci_high': 0.0}, 'bootstrap_ci_upper_deviance_difference'),
                     ({'cand_dev': 0.995}, 'relative_deviance_improvement')]:
        g = gate(f, **kw)
        assert not g['stable_gain'] and g['recommended_reference'] == 'b', kw
        assert not g['criteria'][crit]['passed'] and crit in g['reasoning']
    with pytest.raises(ValueError):
        f['decision_gate']('c', 'b', metrics_frame(f, [('c', 'poisson', True, 0.9, 0.5), ('b', 'baseline', True, 1, 0.5)]),
                           pd.DataFrame({'fold': [1], 'spec_id': ['c'], 'mean_poisson_deviance': [1.0], 'evaluation_scope': [OOF]}),
                           {'evaluation_scope': 'validation_2024', 'ci_high': -1}, XCFG['decision_gate'])


def test_selection_lock_detects_edits_and_choice_hash_ignores_float_roundoff(f, tmp_path):
    om = metrics_frame(f, SEL_ROWS)
    sel = f['select_models'](om, FAMILIES)
    g = gate(f)
    lock = f['build_selection_lock'](sel, g, om, {'c': 1}, 'oofsha', 'fsha', FAMILIES)
    path = tmp_path / 'selection_lock.json'
    f['write_json'](path, lock)
    assert f['verify_selection_lock'](path, lock['decision_sha256'], lock['choice_sha256'])['choice']['selected_candidate'] == 'poisson_a'
    # last-bit change of a metric: decision hash moves, the strict choice hash does not
    om2 = om.copy()
    om2.loc[om2['spec_id'] == 'baseline_a', 'mae'] += 1e-15
    lock2 = f['build_selection_lock'](sel, g, om2, {'c': 1}, 'oofsha', 'fsha', FAMILIES)
    assert lock2['decision_sha256'] != lock['decision_sha256'] and lock2['choice_sha256'] == lock['choice_sha256']
    edited = json.loads(path.read_text('utf-8'))
    edited['decision']['selected_candidate']['spec_id'] = 'rf_1'
    f['write_json'](path, edited)
    with pytest.raises(RuntimeError, match='corrupt or was edited'):
        f['verify_selection_lock'](path)
    forged = dict(lock, choice=dict(lock['choice'], selected_candidate='rf_1'))
    forged['choice_sha256'] = f['sha256_json'](forged['choice'])
    f['write_json'](path, forged)
    with pytest.raises(RuntimeError, match='does not match'):
        f['verify_selection_lock'](path)
    f['write_json'](path, lock)
    with pytest.raises(RuntimeError, match='choice changed'):
        f['verify_selection_lock'](path, None, '0' * 64)


# ---------------------------------------------------------------- paired calendar-day block bootstrap

def test_block_indices_are_consecutive_calendar_runs(f):
    idx = f['block_indices'](20, 7, np.random.default_rng(0))
    assert len(idx) == 20 and idx.min() >= 0 and idx.max() < 20
    for blk in (idx[0:7], idx[7:14], idx[14:20]):
        assert (np.diff(blk) == 1).all()


def test_bootstrap_is_paired_seeded_and_reproducible(f):
    rng = np.random.default_rng(1)
    dates = np.repeat(pd.date_range('2022-01-01', periods=60), 3)
    b = rng.uniform(0, 3, len(dates))
    const = f['paired_block_bootstrap'](dates, b + 0.25, b, replicates=200, seed=7)
    assert const['point_estimate'] == pytest.approx(0.25)
    assert const['ci_low'] == pytest.approx(0.25) and const['ci_high'] == pytest.approx(0.25)  # pairing cancels shared noise
    a = b + rng.normal(0, 1, len(b))
    r1 = f['paired_block_bootstrap'](dates, a, b, replicates=200, seed=42)
    r2 = f['paired_block_bootstrap'](dates, a, b, replicates=200, seed=42)
    r3 = f['paired_block_bootstrap'](dates, a, b, replicates=200, seed=43)
    assert r1 == r2 and (r1['ci_low'], r1['ci_high']) != (r3['ci_low'], r3['ci_high'])
    assert r1['valid_replicates'] == 200 and r1['n_days_zero_weight'] == 0


def test_bootstrap_calendar_gaps_have_zero_weight_and_row_weights_apply(f):
    dates = list(pd.date_range('2022-01-01', '2022-01-10')) + list(pd.date_range('2022-01-20', '2022-01-29'))
    diff = np.arange(20, dtype=float)
    r = f['paired_block_bootstrap'](dates, diff, np.zeros(20), replicates=50, seed=0)
    assert r['n_calendar_days'] == 29 and r['n_days_with_rows'] == 20 and r['n_days_zero_weight'] == 9
    assert r['point_estimate'] == pytest.approx(diff.mean())  # missing days are not zero outcomes
    w = f['paired_block_bootstrap'](['2022-01-01', '2022-01-02'], [1.0, 5.0], [0.0, 0.0], weights=[3, 1], replicates=10, seed=0)
    assert w['point_estimate'] == pytest.approx((3 * 1 + 1 * 5) / 4) and w['weight_sum'] == 4
    sparse = f['paired_block_bootstrap'](['2022-01-01', '2022-01-31'], [1.0, 2.0], [0.0, 0.0], replicates=100, seed=0)
    assert sparse['valid_replicates'] <= 100 and sparse['n_days_zero_weight'] == 29
    with pytest.raises(ValueError):
        f['paired_block_bootstrap'](['2022-01-01'], [np.inf], [0.0])
    with pytest.raises(ValueError):
        f['paired_block_bootstrap'](['2022-01-01'], [1.0], [0.0], weights=[-1])
    with pytest.raises(ValueError):
        f['paired_block_bootstrap'](['2022-01-01', '2022-01-02'], [1.0], [0.0])


def test_bootstrap_comparison_of_a_method_with_itself_is_exactly_zero(f):
    oof = pd.DataFrame({'target_date': np.repeat(pd.date_range('2022-01-01', periods=10), 2), TARGET: [0, 1] * 10,
                        'pred__m': np.linspace(0.1, 2, 20)})
    r = f['bootstrap_comparisons'](oof, [('m', 'm')], 1e-9, XCFG['bootstrap'])[0]
    assert r['point_estimate'] == 0 and r['ci_low'] == 0 and r['ci_high'] == 0 and r['evaluation_scope'] == OOF


# ---------------------------------------------------------------- support / rerun contract / source hashes

def test_support_lists_every_month_including_zero_support(f):
    panel = pd.concat([make_panel('2021-01-01', '2021-01-03'), make_panel('2024-02-01', '2024-02-02', split='validation', eligible=False)])
    splits = [{'name': 'train', 'start': '2021-01-01', 'end': '2021-03-31'}, {'name': 'validation', 'start': '2024-01-01', 'end': '2024-03-31'}]
    s = f['support_by_split_month'](panel, splits, FOLD_CFG).set_index(['split', 'month'])
    assert len(s) == 6
    assert s.loc[('train', '2021-01'), 'eligible_rows'] == 6 and s.loc[('train', '2021-02'), 'eligible_rows'] == 0
    assert s.loc[('validation', '2024-02'), 'panel_rows'] == 4 and s.loc[('validation', '2024-02'), 'eligible_rows'] == 0
    assert s.loc[('validation', '2024-02'), 'role_in_06'] == 'later_year_not_scored_in_06'


def test_rerun_contract_allows_same_and_refuses_different(f, tmp_path):
    c = {'data_inputs_sha256': {'p': 'a'}, 'protocol_sha256': 'x', 'experiment_config_sha256': 'y', 'data_pipeline_config_sha256': 'z'}
    m = tmp_path / 'experiment_manifest.json'
    assert f['check_rerun_contract'](m, c) == 'new_output_root'
    f['write_json'](m, {'status': 'running_or_failed', 'contract': c})
    assert f['check_rerun_contract'](m, dict(c)) == 'same_contract_rerun'
    with pytest.raises(RuntimeError, match='data_inputs_sha256'):
        f['check_rerun_contract'](m, dict(c, data_inputs_sha256={'p': 'b'}))
    f['write_json'](m, {'status': 'ok'})
    with pytest.raises(RuntimeError, match='no recorded contract'):
        f['check_rerun_contract'](m, c)


def test_semantic_notebook_hash_ignores_outputs_but_not_source(f, tmp_path):
    nb = {'cells': [{'cell_type': 'code', 'source': ['# FUNCTIONS\n', 'x = 1'], 'outputs': [], 'execution_count': None}]}
    p = tmp_path / 'n.ipynb'
    p.write_text(json.dumps(nb), 'utf-8')
    h = f['notebook_semantic_sha256'](p)
    nb['cells'][0].update(outputs=[{'output_type': 'stream', 'text': 'hi'}], execution_count=3)
    p.write_text(json.dumps(nb), 'utf-8')
    assert f['notebook_semantic_sha256'](p) == h
    nb['cells'][0]['source'] = ['# FUNCTIONS\n', 'x = 2']
    p.write_text(json.dumps(nb), 'utf-8')
    assert f['notebook_semantic_sha256'](p) != h
    assert f['functions_cell_source'](p).endswith('x = 2')


# ---------------------------------------------------------------- optional: actual verified panel (read-only)

PANEL = BACKEND / 'data' / 'processed' / 'province_day_panel.csv'


@pytest.mark.skipif(not PANEL.is_file(), reason='verified panel not present (data/ is not in git)')
def test_actual_fold_support_matches_independent_counts(f):
    """Counts Codex derived independently from the unchanged panel (workflow/model-review-feedback.md)."""
    coh = f['cohort'](f['load_panel'](PANEL))
    fc = DCFG['forecast']
    folds = f['fold_summary'](f['build_temporal_folds'](coh, XCFG['folds'], fc['issue_hour_local'], fc['issue_days_before_target'], TZ))
    assert len(coh) == 63757
    assert folds['n_fit_rows'].tolist() == [21622, 32297, 43354, 53211]
    assert folds['n_eval_rows'].tolist() == [10675, 11057, 9855, 10471]
    assert folds['eval_label_sum'].tolist() == [6623, 6425, 5825, 5575]
    assert int(folds['n_eval_rows'].sum()) == 42058 and int(folds['eval_label_sum'].sum()) == 24448
    assert (folds['n_eval_provinces_without_positive_past_label'] == 0).all()
    assert (folds['n_fit_provinces_positive_label'] >= folds['n_eval_provinces']).all()


# ================================================================ notebook 07: later-year diagnostics of frozen models

def _code_cells(path):
    nb = json.loads(path.read_text('utf-8'))
    return [''.join(c['source']) if isinstance(c['source'], list) else c['source'] for c in nb['cells'] if c['cell_type'] == 'code']


def load_functions_07():
    """06 FUNCTIONS then 07 FUNCTIONS in one namespace (the order notebook 07 relies on). Returns (ns, 06-only snapshot)."""
    ns = load_functions()
    before = dict(ns)
    hits = [s for s in _code_cells(NB07) if s.lstrip().startswith('# FUNCTIONS')]
    assert len(hits) == 1, 'notebook 07: expected exactly one FUNCTIONS cell'
    exec(compile(hits[0], '07:FUNCTIONS', 'exec'), ns)
    return ns, before


@pytest.fixture(scope='module')
def g():
    return load_functions_07()[0]


def test_07_functions_do_not_rebind_any_06_name():
    ns, before = load_functions_07()
    rebound = sorted(k for k, v in before.items() if k != '__builtins__' and ns[k] is not v)
    assert rebound == []


def test_07_never_fits_selects_or_writes_the_lock():
    src = '\n'.join(_code_cells(NB07))
    for forbidden in ('fit_bundle(', 'run_backtest(', 'select_models(', 'decision_gate(', 'build_selection_lock(', 'save_bundle(',
                      '.fit(', 'write_json(LOCK_PATH', 'bootstrap_comparisons('):
        assert forbidden not in src, forbidden


def test_verified_functions_extraction_rejects_tampered_or_ambiguous_source(g, tmp_path):
    src = '# FUNCTIONS\nx = 1\n'
    nb = {'cells': [{'cell_type': 'markdown', 'source': 'doc'}, {'cell_type': 'code', 'source': src}]}
    p = tmp_path / 'n.ipynb'
    p.write_text(json.dumps(nb), 'utf-8')
    sha = hashlib.sha256(src.encode('utf-8')).hexdigest()
    ns = {}
    assert g['load_verified_06_functions'](p, sha, ns) == sha and ns['x'] == 1
    with pytest.raises(RuntimeError, match='refusing'):
        g['load_verified_06_functions'](p, None, {})
    nb['cells'][1]['source'] = src.replace('1', '2')
    p.write_text(json.dumps(nb), 'utf-8')
    ns = {}
    with pytest.raises(RuntimeError, match='refusing'):
        g['load_verified_06_functions'](p, sha, ns)
    assert 'x' not in ns  # tampered code is never executed
    nb['cells'].append({'cell_type': 'code', 'source': src})
    p.write_text(json.dumps(nb), 'utf-8')
    with pytest.raises(ValueError, match='exactly one'):
        g['extract_verified_functions_source'](p, sha)


def test_expected_06_functions_sha_cross_checks_both_manifests_before_exec(g):
    art = {'producer': '06_baseline_candidate_models', 'status': 'ok', 'source': {'functions_cell_sha256': 'abc'}}
    b = json.dumps(art).encode('utf-8')
    exp = {'producer': '06_baseline_candidate_models', 'status': 'ok', 'source': {'functions_cell_sha256': 'abc'},
           'model_artifact_manifest_sha256': hashlib.sha256(b).hexdigest()}
    assert g['expected_06_functions_sha'](exp, art, b) == 'abc'
    with pytest.raises(RuntimeError, match='bytes differ'):
        g['expected_06_functions_sha'](exp, art, b + b' ')
    with pytest.raises(RuntimeError, match='status'):
        g['expected_06_functions_sha'](dict(exp, status='running_or_failed'), art, b)
    with pytest.raises(RuntimeError, match='disagree'):
        g['expected_06_functions_sha'](dict(exp, source={'functions_cell_sha256': 'other'}), art, b)


# ---------------------------------------------------------------- 07: upstream verification fixtures

def make_upstream(f, g, root):
    """A small but internally consistent notebook-06 output root (two real baseline bundles, a real lock)."""
    rep = root / 'reports' / 'models'
    rep.mkdir(parents=True)
    df = make_panel('2021-01-01', '2021-01-20')
    specs = [XCFG['baselines'][0], XCFG['baselines'][2]]
    bundles = []
    for s in specs:
        rel = 'data/model/bundles/' + s['id'] + '.joblib'
        sha = f['save_bundle'](fit_ok(f, s, df), root / rel)
        bundles.append({'spec_id': s['id'], 'family': 'baseline', 'status': 'ok', 'bundle_path': rel, 'bundle_sha256': sha,
                        'reload_within_tolerance': True})
    om = metrics_frame(f, SEL_ROWS)
    contract = {'data_inputs_sha256': {'p': 'a'}, 'protocol_sha256': 'x', 'experiment_config_sha256': 'y', 'data_pipeline_config_sha256': 'z'}
    source = {k: k + '_value' for k in g['STRICT_SOURCE_KEYS']}
    lock = f['build_selection_lock'](f['select_models'](om, FAMILIES), gate(f), om, contract, 'oofsha', source['functions_cell_sha256'], FAMILIES)
    f['write_json'](rep / 'selection_lock.json', lock)
    lock_sha = f['sha256_file'](rep / 'selection_lock.json')
    (rep / 'oof_metrics.csv').write_text('a,b\n1,2\n', 'utf-8')
    files = [{'path': 'reports/models/selection_lock.json', 'sha256': lock_sha},
             {'path': 'reports/models/oof_metrics.csv', 'sha256': f['sha256_file'](rep / 'oof_metrics.csv')}]
    art = {'producer': '06_baseline_candidate_models', 'status': 'ok', 'contract': contract, 'source': dict(source, runner_sha256='runner_at_06'),
           'selection_lock_decision_sha256': lock['decision_sha256'], 'selection_lock_choice_sha256': lock['choice_sha256'],
           'oof_predictions_sha256': 'oofsha', 'files': files, 'bundles': bundles}
    f['write_json'](rep / 'model_artifact_manifest.json', art)
    ch = lock['choice']
    exp = {'producer': '06_baseline_candidate_models', 'status': 'ok', 'production_enabled': False, 'contract': contract,
           'source': dict(source, runner_sha256='runner_at_06'), 'later_years_scored_in_06': False,
           'model_artifact_manifest_sha256': f['sha256_file'](rep / 'model_artifact_manifest.json'), 'selection_lock_file_sha256': lock_sha,
           'oof_predictions_sha256': 'oofsha',
           'selection': dict({k: ch[k] for k in ('selected_candidate', 'best_per_family', 'best_baseline', 'recommended_reference',
                                                 'recommended_reference_type', 'stable_gain')},
                             decision_sha256=lock['decision_sha256'], choice_sha256=lock['choice_sha256'])}
    return {'root': root, 'rep': rep, 'exp': exp, 'art': art, 'art_sha': exp['model_artifact_manifest_sha256'], 'lock': lock,
            'lock_sha': lock_sha, 'source': source, 'contract': contract, 'spec_ids': [s['id'] for s in specs]}


def _upv(g, u, **kw):
    a = dict(exp=u['exp'], art=u['art'], art_sha=u['art_sha'], lock_sha=u['lock_sha'], source=u['source'], contract=u['contract'], ids=u['spec_ids'])
    a.update(kw)
    return g['upstream_violations'](a['exp'], a['art'], a['art_sha'], a['lock_sha'], a['source'], a['contract'], a['ids'])


def test_upstream_violations_accept_consistent_06_outputs_and_treat_runner_bytes_as_provenance(f, g, tmp_path):
    u = make_upstream(f, g, tmp_path)
    assert _upv(g, u) == []
    assert _upv(g, u, source=dict(u['source'], runner_sha256='runner_changed_for_07')) == []  # not a strict key


@pytest.mark.parametrize('mutate,expect', [
    (lambda u: u['exp'].update(status='running_or_failed'), 'experiment_manifest: status'),
    (lambda u: u['art'].update(status='incomplete'), 'model_artifact_manifest: status'),
    (lambda u: u['source'].update(notebook_semantic_sha256='edited'), 'source.notebook_semantic_sha256'),
    (lambda u: u['source'].update(functions_cell_sha256='edited'), 'source.functions_cell_sha256'),
    (lambda u: u['source'].update(experiment_config_sha256='edited'), 'source.experiment_config_sha256'),
    (lambda u: u['contract']['data_inputs_sha256'].update(p='b'), 'contract differs'),
    (lambda u: u.update(art_sha='0' * 64), 'model_artifact_manifest.json bytes'),
    (lambda u: u.update(lock_sha='0' * 64), 'selection_lock.json bytes'),
    (lambda u: u['art']['bundles'].pop(), 'bundle spec ids'),
    (lambda u: u['art']['bundles'][0].update(status='nonconverged'), 'no status-ok bundle'),
    (lambda u: u['exp'].update(later_years_scored_in_06=True), 'later_years_scored_in_06'),
    (lambda u: u['exp']['selection'].update(choice_sha256='forged'), 'selection lock hashes differ'),
])
def test_upstream_violations_detect_each_tampering(f, g, tmp_path, mutate, expect):
    u = make_upstream(f, g, tmp_path)
    u = dict(u, exp=copy.deepcopy(u['exp']), art=copy.deepcopy(u['art']), source=dict(u['source']), contract=copy.deepcopy(u['contract']))
    mutate(u)
    v = _upv(g, u)
    assert any(expect in x for x in v), v


def test_artifact_hashes_are_checked_before_any_bundle_is_unpickled(f, g, tmp_path):
    u = make_upstream(f, g, tmp_path)
    assert g['artifact_hash_violations'](u['root'], u['art']) == []
    before = g['upstream_file_hashes'](u['root'], u['art'])
    rec = u['art']['bundles'][1]
    bp = u['root'] / rec['bundle_path']
    bp.write_bytes(bp.read_bytes() + b'tampered')
    assert any('sha256 mismatch ' + rec['bundle_path'] in x for x in g['artifact_hash_violations'](u['root'], u['art']))
    with pytest.raises(RuntimeError, match='bundle sha256 mismatch'):
        f['load_bundle'](bp, rec['bundle_sha256'])
    assert g['upstream_file_hashes'](u['root'], u['art'])[rec['bundle_path']] != before[rec['bundle_path']]
    bp.unlink()
    assert any(x.startswith('missing ') for x in g['artifact_hash_violations'](u['root'], u['art']))
    art = copy.deepcopy(u['art'])
    art['files'][1]['path'] = '../outside.csv'
    assert any('escapes' in x for x in g['artifact_hash_violations'](u['root'], art))
    (u['rep'] / 'oof_metrics.csv').write_text('a,b\n1,3\n', 'utf-8')
    assert any('sha256 mismatch reports/models/oof_metrics.csv' in x for x in g['artifact_hash_violations'](u['root'], u['art']))


def test_lock_mutation_is_rejected_before_and_after_scoring(f, g, tmp_path):
    u = make_upstream(f, g, tmp_path)
    path, d, c = u['rep'] / 'selection_lock.json', u['lock']['decision_sha256'], u['lock']['choice_sha256']
    lock = f['verify_selection_lock'](path, d, c)
    assert g['lock_consistency_violations'](lock, u['exp'], u['source'], u['contract']) == []
    assert g['assert_lock_unchanged'](path, d, c, u['lock_sha']) == u['lock_sha']
    edited = json.loads(path.read_text('utf-8'))
    edited['decision']['best_baseline']['spec_id'] = 'baseline_b'
    f['write_json'](path, edited)
    with pytest.raises(RuntimeError, match='corrupt or was edited'):
        g['assert_lock_unchanged'](path, d, c, u['lock_sha'])
    path.write_text(json.dumps(u['lock']), 'utf-8')  # same content, different bytes: hashes verify, bytes do not
    with pytest.raises(RuntimeError, match='bytes changed'):
        g['assert_lock_unchanged'](path, d, c, u['lock_sha'])
    exp = copy.deepcopy(u['exp'])
    exp['selection']['selected_candidate'] = 'rf_1'
    assert any('selected_candidate' in x for x in g['lock_consistency_violations'](lock, exp, u['source'], u['contract']))
    assert any('FUNCTIONS' in x for x in g['lock_consistency_violations'](lock, u['exp'], dict(u['source'], functions_cell_sha256='x'), u['contract']))
    assert any('contract' in x for x in g['lock_consistency_violations'](lock, u['exp'], u['source'], dict(u['contract'], protocol_sha256='q')))


def test_bundle_metadata_must_match_the_frozen_spec(f, g):
    s = XCFG['baselines'][2]
    b = fit_ok(f, s, make_panel('2021-01-01', '2021-01-10'))
    assert g['bundle_metadata_violations'](b, s, FEATURES) == []
    assert any('params' in x for x in g['bundle_metadata_violations'](b, dict(s, params={'pseudo_obs': 3}), FEATURES))
    assert any('features' in x for x in g['bundle_metadata_violations'](b, s, FEATURES[::-1]))
    assert any('spec_id' in x for x in g['bundle_metadata_violations'](b, XCFG['baselines'][1], FEATURES))
    assert any('fit status' in x for x in g['bundle_metadata_violations'](dict(b, fit_info=dict(b['fit_info'], status='nonconverged')), s, FEATURES))


# ---------------------------------------------------------------- 07: cells, identical keys, metrics, support

def later_panel():
    tr = make_panel('2021-01-01', '2021-02-28')
    va = make_panel('2024-01-01', '2024-01-03', split='validation')
    va['training_eligible'] = ['False', 'false', 'True', 'TRUE', 'true', '1']  # strict string parsing
    te = make_panel('2025-01-01', '2025-01-02', split='reused_test_2025')
    d26 = make_panel('2026-01-01', '2026-01-02', split='diagnostic_2026')
    return tr, pd.concat([tr, va, te, d26], ignore_index=True)


def test_diagnostic_cells_are_eligible_later_split_rows_only(g):
    tr, panel = later_panel()
    cells = g['diagnostic_cells'](panel)
    assert cells['split'].tolist() == ['validation'] * 4 + ['reused_test_2025'] * 4  # 'False'/'false' rows excluded
    assert cells['target_date'].dt.year.max() == 2025 and 'diagnostic_2026' not in set(cells['split'])
    with pytest.raises(ValueError, match='diagnostic year'):
        g['diagnostic_cells'](pd.concat([panel, make_panel('2026-02-01', '2026-02-01', split='validation')], ignore_index=True))
    with pytest.raises(ValueError, match='duplicate'):
        g['diagnostic_cells'](pd.concat([panel, panel[panel['split'] == 'reused_test_2025'].iloc[[0]]], ignore_index=True))
    flagged = panel.copy()
    flagged.loc[flagged['split'] == 'reused_test_2025', 'possibly_undercounted'] = True
    with pytest.raises(ValueError, match='possibly_undercounted'):
        g['diagnostic_cells'](flagged)


def test_every_frozen_method_is_scored_on_identical_keys(f, g, tmp_path):
    tr, panel = later_panel()
    specs = list(XCFG['baselines']) + [TINY[0]]
    ids = [s['id'] for s in specs]
    bundles = {s['id']: fit_ok(f, s, tr) for s in specs}
    cells = g['diagnostic_cells'](panel)
    pred, secs = g['predict_all'](bundles, specs, cells, FEATURES)
    assert g['same_cell_violations'](pred, cells, ids) == [] and set(secs) == set(ids)
    assert set(pred['evaluation_scope']) == {'diagnostic_validation_2024', 'diagnostic_reused_test_2025'}
    assert (pred['pred__baseline_zero'] == 0).all()
    pm = tr.groupby('province')[TARGET].mean()
    assert np.allclose(pred['pred__baseline_province_mean'], pred['province'].map(pm))  # learned from Train only
    assert any('keys differ' in x for x in g['same_cell_violations'](pred.sample(frac=1, random_state=0), cells, ids))
    holed = pred.copy()
    holed.loc[0, 'pred__poisson_tiny'] = np.nan
    assert any('missing predictions' in x for x in g['same_cell_violations'](holed, cells, ids))
    assert any('column missing' in x for x in g['same_cell_violations'](pred.drop(columns='pred__baseline_zero'), cells, ids))
    relabeled = pred.copy()
    relabeled[TARGET] = relabeled[TARGET] + 1
    assert any('labels differ' in x for x in g['same_cell_violations'](relabeled, cells, ids))
    p = tmp_path / 'diagnostic_predictions.csv'
    pred.assign(target_date=pred['target_date'].dt.strftime('%Y-%m-%d')).to_csv(p, index=False)
    saved = g['read_diagnostic_predictions'](p)
    assert g['same_cell_violations'](saved, cells, ids) == []
    for sid in ids:
        assert f['compare_predictions'](pred['pred__' + sid], saved['pred__' + sid])['within_tolerance']


def hand_pred():
    d = pd.to_datetime(['2024-01-01', '2024-01-01', '2025-01-01', '2025-01-02'])
    df = pd.DataFrame({'split': ['validation', 'validation', 'reused_test_2025', 'reused_test_2025'], 'province': ['A', 'B', 'A', 'B'],
                       'target_date': d, TARGET: [0, 2, 1, 3], 'pred__m': [1.0, 1.0, 1.0, 2.0], 'pred__baseline_zero': [0.0] * 4})
    df['year_month'] = d.strftime('%Y-%m')
    return df, [{'id': 'm', 'family': 'poisson', 'deviance_domain': 'floor'}, XCFG['baselines'][0]]


def test_diagnostic_metrics_hand_computed_per_scope_and_pooled(g):
    pred, specs = hand_pred()
    dm = g['diagnostic_metrics'](pred, specs, 1e-9).set_index(['evaluation_scope', 'spec_id'])
    v = dm.loc[('diagnostic_validation_2024', 'm')]  # errors +1, -1
    assert (v['mae'], v['rmse'], v['bias'], v['wape']) == (1.0, 1.0, 0.0, 1.0)
    assert v['mean_poisson_deviance'] == pytest.approx((2.0 + 2 * (2 * math.log(2) - 1)) / 2)
    assert v['n_rows'] == 2 and v['n_distinct_dates'] == 1 and v['support_status'] == 'scored'
    t = dm.loc[('diagnostic_reused_test_2025', 'm')]  # errors 0, -1
    assert t['mae'] == 0.5 and t['rmse'] == pytest.approx(math.sqrt(0.5)) and t['bias'] == -0.5 and t['wape'] == 0.25
    assert t['mean_poisson_deviance'] == pytest.approx((0.0 + 2 * (3 * math.log(1.5) - 1)) / 2)
    p = dm.loc[('diagnostic_pooled_2024_2025', 'm')]
    assert p['mae'] == 0.75 and p['bias'] == -0.25 and p['observed_total'] == 6 and p['predicted_total'] == 5 and p['n_distinct_dates'] == 3
    z = dm.loc[('diagnostic_pooled_2024_2025', 'baseline_zero')]
    assert pd.isna(z['mean_poisson_deviance']) and z['mae'] == 1.5 and z['bias'] == -1.5


def test_metric_recomputation_check_catches_wrong_or_fake_scores(g):
    pred, specs = hand_pred()
    dm = g['diagnostic_metrics'](pred, specs, 1e-9)
    chk = g['metric_recomputation_check'](pred, specs, dm, 1e-9)
    assert chk['max_scaled_abs_diff'].max() <= 1e-12
    bad = dm.copy()
    bad.loc[(bad['spec_id'] == 'm') & (bad['evaluation_scope'] == 'diagnostic_pooled_2024_2025'), 'mae'] += 1e-6
    with pytest.raises(AssertionError, match='mae'):
        g['metric_recomputation_check'](pred, specs, bad, 1e-9)
    fake = dm.copy()
    fake['mean_poisson_deviance'] = fake['mean_poisson_deviance'].astype(object)
    fake.loc[fake['spec_id'] == 'baseline_zero', 'mean_poisson_deviance'] = 0.0  # a zero predictor has no defined deviance
    with pytest.raises(AssertionError, match='null mismatch'):
        g['metric_recomputation_check'](pred, specs, fake, 1e-9)
    assert g['metric_tables_max_abs_diff'](dm, dm) == 0.0
    with pytest.raises(ValueError, match='null pattern'):
        g['metric_tables_max_abs_diff'](dm, fake)


def test_months_without_eligible_support_get_null_scores_not_zero(f, g):
    tr = make_panel('2021-01-01', '2021-01-31')
    va = pd.concat([make_panel('2024-01-01', '2024-01-05', split='validation'),
                    make_panel('2024-02-01', '2024-02-03', split='validation', eligible=False)], ignore_index=True)
    panel = pd.concat([tr, va], ignore_index=True)
    splits = [{'name': 'train', 'start': '2021-01-01', 'end': '2021-02-28'}, {'name': 'validation', 'start': '2024-01-01', 'end': '2024-03-31'},
              {'name': 'reused_test_2025', 'start': '2025-01-01', 'end': '2025-01-31'}]
    specs = [XCFG['baselines'][2], XCFG['baselines'][0]]
    bundles = {s['id']: fit_ok(f, s, tr) for s in specs}
    cells = g['diagnostic_cells'](panel)
    pred, _ = g['predict_all'](bundles, specs, cells, FEATURES)
    focus = {'selected_candidate': 'baseline_province_mean', 'strongest_baseline': 'baseline_province_mean'}
    cov = g['coverage_table'](panel, splits, FOLD_CFG, pred, focus, 1e-9, {s['id']: s for s in specs})
    c = cov.set_index(['split', 'month'])
    assert len(c) == 2 + 3 + 1  # every month of every split
    feb = c.loc[('validation', '2024-02')]  # panel rows exist but none eligible
    assert feb['panel_rows'] == 6 and feb['eligible_rows'] == 0 and feb['eligible_share_of_panel'] == 0
    assert feb['score_status'] == 'no_eligible_support_null_scores'
    for col in ('selected_candidate__mae', 'selected_candidate__mean_poisson_deviance', 'strongest_baseline__rmse', 'selected_candidate__observed_total'):
        assert pd.isna(feb[col]), col
    mar = c.loc[('validation', '2024-03')]  # not even panel rows
    assert mar['panel_rows'] == 0 and pd.isna(mar['eligible_share_of_panel']) and pd.isna(mar['selected_candidate__mae'])
    assert c.loc[('reused_test_2025', '2025-01'), 'score_status'] == 'no_eligible_support_null_scores'
    jan = c.loc[('validation', '2024-01')]
    assert jan['eligible_rows'] == 10 and jan['score_status'] == 'scored_later_year_diagnostic' and pd.notna(jan['selected_candidate__mae'])
    assert jan['eligible_first_date'] == '2024-01-01' and jan['eligible_last_date'] == '2024-01-05'
    assert c.loc[('train', '2021-01'), 'score_status'] == 'train_not_scored_in_07' and pd.isna(c.loc[('train', '2021-01'), 'selected_candidate__mae'])
    mm = g['monthly_metrics'](pred, specs, 1e-9, splits)
    empty = mm[mm['year_month'].isin(['2024-02', '2024-03', '2025-01'])]
    assert len(empty) == 3 * len(specs) and (empty['n_rows'] == 0).all() and (empty['support_status'] == 'no_eligible_support').all()
    assert empty[['mae', 'rmse', 'bias', 'observed_total', 'predicted_total']].isna().all().all()
    dm = g['diagnostic_metrics'](pred, specs, 1e-9)
    t25 = dm[dm['evaluation_scope'] == 'diagnostic_reused_test_2025']
    assert (t25['n_rows'] == 0).all() and t25[['mae', 'observed_total']].isna().all().all()
    g['metric_recomputation_check'](pred, specs, dm, 1e-9)  # empty scope: nulls are expected, no exception
    sup = f['support_by_split_month'](panel, splits, FOLD_CFG)
    assert g['coverage_support_violations'](cov, sup) == []
    tampered = sup.copy()
    tampered.loc[2, 'eligible_rows'] += 1
    assert g['coverage_support_violations'](cov, tampered) != []
    summary = g['split_support_summary'](panel, cells)
    warn = g['support_warnings'](summary, cov)
    assert '2024-02' in warn['diagnostic_validation_2024'] and 'selection-biased' in warn['diagnostic_validation_2024']
    assert summary.set_index('split').loc['reused_test_2025', 'eligible_cells'] == 0


# ---------------------------------------------------------------- 07: frozen choice is never replaced by later-year ranks

CHOICE = {'selected_candidate': 'p1', 'best_per_family': {'poisson': 'p1', 'random_forest': 'r1', 'hist_gradient_boosting': 'h1'},
          'best_baseline': 'b1', 'recommended_reference': 'p1', 'recommended_reference_type': 'candidate', 'stable_gain': True,
          'gate_criteria_passed': {}}
FROZEN_SPECS = [('p1', 'poisson'), ('p2', 'poisson'), ('r1', 'random_forest'), ('h1', 'hist_gradient_boosting'),
                ('b1', 'baseline'), ('b2', 'baseline'), ('baseline_zero', 'baseline')]


def diag_frame(f, g, devs):
    rows = []
    for scope in g['DIAG_SCOPES']:
        for sid, fam in FROZEN_SPECS:
            r = dict.fromkeys(f['METRIC_KEYS'], 1.0)
            r.update(evaluation_scope=scope, spec_id=sid, family=fam, n_rows=10, mean_poisson_deviance=devs[sid], support_status='scored',
                     n_distinct_dates=5, n_months_with_support=1, n_provinces=2, first_date='2024-01-01', last_date='2024-01-05')
            rows.append(r)
    return pd.DataFrame(rows)


def frozen_oof(f):
    dev = {'p1': 0.90, 'p2': 0.95, 'r1': 1.00, 'h1': 0.97, 'b1': 1.10, 'b2': 1.20, 'baseline_zero': None}
    return metrics_frame(f, [(sid, fam, True, dev[sid], 0.5) for sid, fam in FROZEN_SPECS])


def test_main_table_keeps_frozen_picks_when_later_year_ranks_differ(f, g):
    oof = frozen_oof(f)
    later = {'p1': 0.9, 'p2': 0.4, 'r1': 0.5, 'h1': 0.6, 'b1': 0.7, 'b2': 0.65, 'baseline_zero': None}
    dm = diag_frame(f, g, later)
    main = g['main_results_table'](CHOICE, oof, dm, FAMILIES)
    for scope in g['DIAG_SCOPES']:
        sub = main[main['evaluation_scope'] == scope].set_index('spec_id')
        assert sub.index.tolist() == ['p1', 'r1', 'h1', 'b1', 'baseline_zero']
        assert sub['is_selected_candidate'].tolist() == [True, False, False, False, False]
        assert sub.loc['p1', 'oof_rank_among_main_rows'] == 1 and sub.loc['p1', 'later_rank_among_main_rows'] == 4
        assert sub.loc['p1', 'later_rank_differs_from_oof'] and not sub['frozen_choice_changed'].any()
        assert sub.loc['p1', 'deviance_minus_strongest_baseline'] == pytest.approx(0.2)
        assert pd.isna(sub.loc['baseline_zero', 'mean_poisson_deviance']) and pd.isna(sub.loc['baseline_zero', 'later_rank_among_main_rows'])
    rk = g['rank_comparison'](CHOICE, oof, dm, FAMILIES)
    assert (rk['frozen_selected_candidate'] == 'p1').all() and (rk['later_lowest_deviance_family_best'] == 'r1').all()
    assert rk['family_best_rank_differs'].all() and (rk['later_lowest_deviance_any_spec'] == 'p2').all()  # reported only
    assert (rk['later_lowest_deviance_baseline'] == 'b2').all() and rk['baseline_rank_differs'].all()
    assert (rk['selected_candidate_beats_strongest_baseline'] == False).all()  # noqa: E712
    assert (rk['n_family_bests_beating_strongest_baseline'] == 2).all() and not rk['frozen_choice_changed'].any()
    allc = g['all_config_table']([{'id': s, 'family': fam} for s, fam in FROZEN_SPECS], oof, dm, CHOICE)
    roles = allc.drop_duplicates('spec_id').set_index('spec_id')['roles']
    assert roles['p1'] == 'selected_candidate;best_of_family;recommended_reference' and roles['b1'] == 'strongest_baseline' and roles['p2'] == ''
    assert allc.set_index(['evaluation_scope', 'spec_id']).loc[('diagnostic_pooled_2024_2025', 'p2'), 'later_rank_all_specs'] == 1
    rng = np.random.default_rng(0)
    for _ in range(5):  # any later-year ordering leaves the frozen rows untouched
        shuffled = {k: (None if v is None else float(rng.uniform(0.1, 2))) for k, v in later.items()}
        m2 = g['main_results_table'](CHOICE, oof, diag_frame(f, g, shuffled), FAMILIES)
        assert m2[['evaluation_scope', 'role', 'spec_id', 'is_selected_candidate', 'is_recommended_reference']].equals(
            main[['evaluation_scope', 'role', 'spec_id', 'is_selected_candidate', 'is_recommended_reference']])


def test_later_year_metrics_cannot_reach_selection_or_oof_slots(f, g):
    oof = frozen_oof(f)
    dm = diag_frame(f, g, {'p1': 0.9, 'p2': 0.4, 'r1': 0.5, 'h1': 0.6, 'b1': 0.7, 'b2': 0.65, 'baseline_zero': None})
    with pytest.raises(ValueError, match='later-year'):
        f['select_models'](dm.assign(eligible=True), FAMILIES)
    for fn in ('main_results_table', 'rank_comparison'):
        with pytest.raises(ValueError):
            g[fn](CHOICE, dm.assign(eligible=True), dm, FAMILIES)
    with pytest.raises(ValueError):
        g['all_config_table']([{'id': s, 'family': fam} for s, fam in FROZEN_SPECS], dm.assign(eligible=True), dm, CHOICE)
    assert f['select_models'](oof, FAMILIES)['selected_candidate'] == 'p1'  # the OOF lock itself is what 07 reads


# ---------------------------------------------------------------- runner stages

def load_runner():
    spec = importlib.util.spec_from_file_location('run_model_notebooks_under_test', RUNNER)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_runner_stage_mapping_and_separate_analysis_run_manifest():
    r = load_runner()
    assert r.notebooks_for_stage('train') == ['06_baseline_candidate_models']
    assert r.notebooks_for_stage('analysis') == ['07_evaluation_experiment_results']
    assert r.notebooks_for_stage('all') == ['06_baseline_candidate_models', '07_evaluation_experiment_results']
    with pytest.raises(ValueError):
        r.notebooks_for_stage('deploy')
    assert r.run_manifest_name('analysis') == 'run_manifest_analysis.json'
    assert r.run_manifest_name('train') == r.run_manifest_name('all') == 'run_manifest.json'
    assert all((BACKEND / 'notebooks' / (n + '.ipynb')).is_file() for n in r.notebooks_for_stage('all'))


def test_runner_analysis_requires_status_ok_06_outputs_and_hashes_them(tmp_path):
    r = load_runner()
    rep = tmp_path / 'reports' / 'models'
    rep.mkdir(parents=True)
    assert 'not found' in r.train_outputs_problem(rep)
    (rep / 'selection_lock.json').write_text('{}', 'utf-8')
    (rep / 'experiment_manifest.json').write_text(json.dumps({'status': 'running_or_failed'}), 'utf-8')
    (rep / 'model_artifact_manifest.json').write_text(json.dumps({'status': 'ok', 'files': [{'path': 'data/model/x.csv'}],
                                                                  'bundles': [{'bundle_path': 'data/model/bundles/a.joblib'}]}), 'utf-8')
    assert 'running_or_failed' in r.train_outputs_problem(rep)
    (rep / 'experiment_manifest.json').write_text(json.dumps({'status': 'ok'}), 'utf-8')
    assert r.train_outputs_problem(rep) is None
    (tmp_path / 'data' / 'model' / 'bundles').mkdir(parents=True)
    (tmp_path / 'data' / 'model' / 'x.csv').write_text('1', 'utf-8')
    (tmp_path / 'data' / 'model' / 'bundles' / 'a.joblib').write_bytes(b'a')
    h = r.upstream_hashes(tmp_path)
    assert {'data/model/x.csv', 'data/model/bundles/a.joblib', 'reports/models/selection_lock.json'} <= set(h) and all(h.values())
    (tmp_path / 'data' / 'model' / 'bundles' / 'a.joblib').write_bytes(b'b')
    assert r.upstream_hashes(tmp_path)['data/model/bundles/a.joblib'] != h['data/model/bundles/a.joblib']


# ---------------------------------------------------------------- optional: actual 06 artifacts / panel (read-only)

ART_MANIFEST = BACKEND / 'reports' / 'models' / 'model_artifact_manifest.json'


@pytest.mark.skipif(not ART_MANIFEST.is_file(), reason='notebook 06 outputs not present')
def test_actual_06_functions_and_semantic_hash_match_the_recorded_manifest(f, g):
    art = json.loads(ART_MANIFEST.read_text('utf-8'))
    assert art['status'] == 'ok'
    src = g['extract_verified_functions_source'](NB06, art['source']['functions_cell_sha256'])
    assert f['sha256_bytes'](src.encode('utf-8')) == art['source']['functions_cell_sha256']
    assert f['notebook_semantic_sha256'](NB06) == art['source']['notebook_semantic_sha256']


@pytest.mark.skipif(not PANEL.is_file(), reason='verified panel not present (data/ is not in git)')
def test_actual_diagnostic_cells_match_06_support_and_2024_q4_has_no_support(f, g):
    panel = f['load_panel'](PANEL)
    cells = g['diagnostic_cells'](panel, g['DIAGNOSTIC_SPLITS'], DCFG['diagnostic_split']['year'])
    sup = pd.read_csv(BACKEND / 'reports' / 'models' / 'support_by_split_month.csv')
    later = sup[sup['split'].isin(g['DIAGNOSTIC_SPLITS'])]
    assert len(cells) == int(later['eligible_rows'].sum())
    assert int(cells[TARGET].sum()) == int(later['eligible_target_sum'].sum())
    ym = cells['target_date'].dt.strftime('%Y-%m')
    assert not ym.isin(['2024-10', '2024-11', '2024-12']).any()
    assert (later.set_index('month').loc[['2024-10', '2024-11', '2024-12'], 'eligible_rows'] == 0).all()
    assert cells['target_date'].dt.year.max() <= 2025
