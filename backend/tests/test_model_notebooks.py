"""Fixture tests for RoadAware model notebook 06 (tiny synthetic data; no Jupyter kernel needed).

Each test executes the notebook's own '# FUNCTIONS' code cell, so the logic under test is exactly what notebook 06
(and later 07/08) run. Expected values are computed by hand or by an independent oracle (scikit-learn metrics), not
by re-implementing the notebook code. Tiny model parameters below are deliberately small; the real protocol
configuration is checked separately and is never changed by these tests. Run from the repository root:
    .venv/bin/python -m pytest backend/tests -q
"""
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
