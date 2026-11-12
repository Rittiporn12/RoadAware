"""Tests for notebook 21 (spatial evaluation + relative colour contract). The four '# FUNCTIONS' cells of the assembled source notebook are
executed (never pipeline cells), so the logic under test is the logic the notebook runs. Tiny hand-computed fixtures only; no accepted data
is required. Run from the repository root (after assembling notebook 21):
    .venv/bin/python -m pytest backend/tests/test_spatial_evaluation_notebook.py -q
"""
import importlib.util
import json
import math
import os
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

BACKEND = Path(__file__).resolve().parents[1]
NB21 = BACKEND / 'notebooks' / '21_spatial_evaluation_colours.ipynb'
CFG = json.loads((BACKEND / 'config' / 'spatial_evaluation_v3.json').read_text('utf-8'))


def code_cells(p):
    return [''.join(c['source']) for c in json.loads(p.read_text('utf-8'))['cells'] if c['cell_type'] == 'code']


@pytest.fixture(scope='module')
def F():
    cells = [s for s in code_cells(NB21) if s.lstrip().startswith('# FUNCTIONS')]
    assert len(cells) == 4
    ns = {}
    for i, s in enumerate(cells):
        exec(compile(s, f'{NB21.stem}:FUNCTIONS[{i}]', 'exec'), ns)
    return ns


def load_module(name, rel):
    spec = importlib.util.spec_from_file_location(name, BACKEND / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def contract(F, d, unit='daily'):
    return F['build_colour_contract'](np.asarray(d, float), unit, CFG['colour'], {'method': 'fixture'})


def test_source_notebook_unexecuted_and_no_handoff_reference():
    nb = json.loads(NB21.read_text('utf-8'))
    assert all(not c.get('outputs') and c.get('execution_count') is None for c in nb['cells'] if c['cell_type'] == 'code')
    assert not any('.ai-team' in s for s in code_cells(NB21))


def test_cutoff_ties_duplicates_and_equality(F):
    c = contract(F, [0.0] * 60 + [1.0] * 40)
    assert c['raw_cutoffs'] == [0.0, 1.0, 1.0] and c['unique_cutoffs'] == [0.0, 1.0]
    codes = F['assign_colour_codes'](np.array([0.0, 1.0, 1.0 + 1e-12, 2.0]), np.array([1000.0] * 4), c, 'daily')
    assert codes.tolist() == [0, 1, 3, 3]  # equal to a cutoff stays in the lower band; duplicate cutoffs skip orange
    assert c['labels_in_use'] == ['base', 'yellow'] and c['reference_cell_counts'] == {'base': 60, 'yellow': 40, 'orange': 0, 'red': 0}


@pytest.mark.parametrize('value', [0.0, 0.37])
def test_constant_and_zero_predictions_never_force_bands(F, value):
    c = contract(F, [value] * 50)
    assert c['raw_cutoffs'] == [value] * 3 and c['labels_in_use'] == ['base']
    assert F['assign_colour_codes'](np.array([value]), np.array([1000.0]), c, 'daily').tolist() == [0]


def test_cutoffs_are_type7_quantiles_and_fixed_strict_json(F):
    rng = np.random.default_rng(3)
    d = rng.gamma(0.3, 0.01, 1001)
    c = contract(F, d)
    assert c['raw_cutoffs'] == [float(v) for v in np.quantile(d, [0.5, 0.8, 0.95], method='linear')]
    back = json.loads(F['json_bytes'](c).decode('utf-8'))
    assert back['raw_cutoffs'] == c['raw_cutoffs'] and all(type(v) is float for v in back['raw_cutoffs'])
    ref = back['reference']
    assert ref['density_float64_le_sha256'] == F['density_digest'](d) == c['reference']['density_float64_le_sha256']
    assert ref['n_cells'] == d.size and ref['min'] == float(d.min()) and ref['max'] == float(d.max()) and ref['method'] == 'fixture'
    assert sum(back['reference_cell_counts'].values()) == d.size
    # the strict-JSON round trip is itself a valid contract that reproduces the same bands
    F['validate_colour_contract'](back, 'daily')
    assert (F['assign_colour_codes'](d, np.full(d.size, 1000.0), back, 'daily') == F['assign_colour_codes'](d, np.full(d.size, 1000.0), c, 'daily')).all()


def test_invalid_unknown_unsupported_are_grey_never_green(F):
    c = contract(F, np.linspace(0, 1, 101))
    pred = np.array([np.nan, -1.0, np.inf, 0.5, 0.5, 0.5, 0.5])
    length = np.array([1000.0, 1000.0, 1000.0, 0.0, -5.0, np.nan, 1000.0])
    sup = np.array([True] * 6 + [False])
    codes = F['assign_colour_codes'](pred, length, c, 'daily', supported=sup)
    assert (codes == F['GREY_CODE']).all()
    assert list(F['colour_labels'](codes)) == ['grey'] * 7
    assert 'green' not in json.dumps(c).lower() and 'safe' not in c['accessible_text']['base'].replace('NOT safe', '')
    legend = F['colour_legend'](c)
    assert [x['label'] for x in legend] == ['base', 'yellow', 'orange', 'red', 'grey']


def test_reference_inputs_must_be_finite_nonnegative(F):
    for bad in ([1.0, np.nan], [1.0, -0.1], [np.inf], []):
        with pytest.raises(F['EvaluationError']):
            contract(F, bad)


def test_horizons_separate_and_tampered_contract_refused(F):
    c = contract(F, np.linspace(0, 1, 11), 'daily')
    with pytest.raises(F['EvaluationError'], match='never converted'):
        F['assign_colour_codes'](np.array([0.1]), np.array([1000.0]), c, '6h')
    for key, val in (('raw_cutoffs', [0.3, 0.2, 0.9]), ('raw_cutoffs', [0.1, 0.2]), ('labels', ['green', 'yellow', 'orange', 'red']), ('kind', 'x')):
        t = dict(c, **{key: val})
        with pytest.raises(F['EvaluationError']):
            F['assign_colour_codes'](np.array([0.1]), np.array([1000.0]), t, 'daily')


def test_density_uses_km_and_same_horizon(F):
    d, ok = F['segment_density'](np.array([0.2, 0.2]), np.array([2000.0, 500.0]))
    assert ok.all() and d.tolist() == [0.1, 0.4]


def test_deviance_matches_notebook20_formula(F):
    y, mu = np.array([0.0, 1.0, 2.0, 1.0]), np.array([0.5, 0.5, 2.0, 0.0])
    got = F['poisson_deviance_terms'](y, mu, 1e-12)
    exp = [2 * 0.5, 2 * (math.log(1 / 0.5) - 0.5), 0.0, 2 * (math.log(1 / 1e-12) - (1 - 1e-12))]
    assert np.allclose(got, exp, rtol=1e-14)
    with pytest.raises(F['EvaluationError']):
        F['poisson_deviance_terms'](np.array([1.0]), np.array([-0.1]), 1e-12)


def test_streamed_grouped_metrics_equal_exact_tiny_array(F):
    rng = np.random.default_rng(7)
    y = rng.poisson(0.3, 37).astype(float)
    mu = rng.gamma(1.0, 0.3, 37)
    mu[:3] = 0.0
    km = rng.uniform(0.5, 2.0, 37)
    codes = rng.integers(0, 3, 37)
    one, many = F['new_acc'](3), F['new_acc'](3)
    F['acc_add'](one, y, mu, km, 1e-12, codes)
    for lo in range(0, 37, 5):
        F['acc_add'](many, y[lo:lo + 5], mu[lo:lo + 5], km[lo:lo + 5], 1e-12, codes[lo:lo + 5])
    assert np.allclose(one, many, rtol=1e-13, atol=1e-15)
    for g in range(3):
        m, sel = F['acc_metrics'](one[g]), codes == g
        dv = F['poisson_deviance_terms'](y[sel], mu[sel], 1e-12)
        assert m['n'] == sel.sum() and math.isclose(m['mean_poisson_deviance'], dv.mean(), rel_tol=1e-12)
        assert math.isclose(m['mae'], np.abs(mu[sel] - y[sel]).mean(), rel_tol=1e-12)
        assert math.isclose(m['rmse'], math.sqrt(np.square(mu[sel] - y[sel]).mean()), rel_tol=1e-12)
        assert m['metric_floor_cells'] == int((mu[sel] < 1e-12).sum())
        # exposure-weighted density = total records / total segment-km-periods, not the mean of per-cell ratios
        if y[sel].sum() > 0:
            assert math.isclose(m['observed_records_per_km_period'], y[sel].sum() / km[sel].sum(), rel_tol=1e-12)
        assert math.isclose(m['predicted_records_per_km_period'], mu[sel].sum() / km[sel].sum(), rel_tol=1e-12)
    with pytest.raises(F['EvaluationError']):
        F['acc_add'](F['new_acc'](2), y, mu, km, 1e-12, np.full(37, 2))


def test_zero_actual_group_has_undefined_wape(F):
    a = F['new_acc'](1)
    F['acc_add'](a, np.zeros(4), np.full(4, 0.1), np.ones(4), 1e-12, np.zeros(4, np.int64))
    m = F['acc_metrics'](a[0])
    assert m['wape'] is None and m['wape_status'] == 'undefined_zero_actual' and m['pred_over_actual'] is None


def test_unknown_province_and_dimensions(F):
    S = pd.DataFrame({'segment_id': ['a', 'b'], 'geom_length_m': [1000.0, 2000.0], 'province_code': [13.0, np.nan], 'route_code': ['0001', '0346']}).set_index('segment_id')
    D = pd.DataFrame({'day_of_week': [0, 6], 'month': [1, 4], 'season_hot': [0.0, 1.0], 'season_wet': [0.0, 0.0], 'season_cool': [1.0, 0.0],
                      **{f'fest_{f}_{s}': [0.0, 0.0] for f in ('new_year', 'songkran') for s in ('in', 'pre_1_3', 'pre_4_7', 'post_1_3', 'post_4_7')}})
    D.loc[1, 'fest_songkran_in'] = 1.0
    dims = F['build_dimensions'](S, D, '6h', CFG, ['p1'])
    assert dims['province'][2] == ['13', 'unknown'] and dims['province'][1].tolist() == [0, 1]
    assert dims['route_code'][2] == ['0001', '0346'] and dims['time_block'][2] == CFG['time']['blocks_6h']
    assert list(dims['festival'][2]) == ['none', 'songkran_in'] and list(dims['season'][2]) == ['cool', 'hot']
    d, s, b = F['cell_index'](0, 16, 2, 4)
    assert d.tolist() == [0] * 8 + [1] * 8 and s.tolist() == ([0] * 4 + [1] * 4) * 2 and b.tolist() == [0, 1, 2, 3] * 4


def test_period_coverage_tamper_refused(F):
    P = [{'id': 'a', 'row_offset': 0, 'rows': 4}]
    assert F['period_codes_for'](P, 0, 4).tolist() == [0] * 4
    with pytest.raises(F['EvaluationError']):
        F['period_codes_for'](P, 2, 6)


def test_fractional_km_capture_is_deterministic(F):
    km = np.array([1.0, 2.0, 1.0])
    dens = np.array([[3.0, 2.0, 1.0], [1.0, 1.0, 1.0]])
    y = np.array([[1.0, 4.0, 0.0], [2.0, 2.0, 2.0]])
    res, ty, tp = F['capture_by_period'](dens, y, y, km, [0.5, 1.0])
    # row 0: budget 2 km -> seg0 whole (1 km) + half of seg1 (1 of 2 km) -> 1 + 0.5 * 4; row 1: ties keep index order -> seg0 + half seg1
    assert res[0.5]['actual'].tolist() == [3.0, 3.0] and res[1.0]['actual'].tolist() == [5.0, 6.0] and ty.tolist() == [5.0, 6.0]
    again, _, _ = F['capture_by_period'](dens, y, y, km, [0.5])
    assert again[0.5]['actual'].tolist() == res[0.5]['actual'].tolist()
    with pytest.raises(F['EvaluationError']):
        F['capture_by_period'](dens, y, y, np.array([1.0, 0.0, 1.0]), [0.5])
    m = F['to_period_matrix'](np.arange(16), 2, 4)
    assert m[:, 0].tolist() == [0, 1, 2, 3, 8, 9, 10, 11] and m.shape == (8, 2)


def test_calibration_bins_partition_and_collapse(F):
    p = np.array([0.0] * 6 + [0.1, 0.2, 0.3, 0.4])
    e = F['calibration_edges'](p, [0.0, 0.5, 0.8, 1.0])
    c = F['calibration_codes'](p, e)
    assert e[0] == 0.0 and e[-1] == 0.4 and (np.diff(e) > 0).all() and c.min() == 0 and c.max() == e.size - 2
    assert F['calibration_codes'](np.zeros(3), F['calibration_edges'](np.zeros(3), [0.0, 0.5, 1.0])).tolist() == [0, 0, 0]


def test_floor_audit_and_reconcile(F):
    y = np.array([0.0, 1.0, 0.0, 1.0])
    pb, pc = np.array([0.0, 0.0, 0.2, 0.5]), np.array([0.1, 0.3, 0.2, 0.5])
    codes = F['floor_codes'](pb, pc, 1e-12)
    ab, ac = F['new_acc'](4), F['new_acc'](4)
    F['acc_add'](ab, y, pb, np.ones(4), 1e-12, codes)
    F['acc_add'](ac, y, pc, np.ones(4), 1e-12, codes)
    rows, s = F['floor_audit_rows'](ab, ac, 'daily', 'oof')
    assert [r['cells'] for r in rows] == [2, 2, 0, 0] and rows[1]['actual_positive_cells'] == 1
    assert math.isclose(s['baseline_floor_gain_share'], 1.0) and math.isclose(s['complement_relative_deviance_reduction'], 0.0, abs_tol=1e-15)
    assert F['reconcile']({'n': 3, 'wape': None}, {'n': 3, 'wape': float('nan')}, ['n', 'wape'], 1e-9, 0) == []
    assert F['reconcile']({'n': 3}, {'n': 4}, ['n'], 1e-9, 0)


def write_fake_accepted(tmp, tamper=None):
    arrays = tmp / 'arrays'
    arrays.mkdir(parents=True)
    a = np.arange(4, dtype=np.float64)
    np.save(arrays / 'oof_daily_m.npy', a)
    h = F_sha(arrays / 'oof_daily_m.npy')
    meta = {'file': 'oof_daily_m.npy', 'dtype': 'float64', 'shape': [4], 'sha256': h}
    if tamper == 'shape':
        meta['shape'] = [5]
    if tamper == 'bytes':
        np.save(arrays / 'oof_daily_m.npy', a + 1)
    return {'index': {'units': {'daily': {'oof': {'m::routed_context': meta}}}}, 'manifest20': {'data_files_gitignored': {'arrays/oof_daily_m.npy': h}},
            'data_dir20': tmp}


def F_sha(p):
    import hashlib
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def test_array_hash_shape_tamper_and_stored_method_first(F, tmp_path):
    docs = write_fake_accepted(tmp_path / 'ok')
    fn, metas = F['load_method'](docs, 'daily', 'oof', 'm::routed_context')  # stored routed array used; no components needed
    assert fn(0, 4).tolist() == [0.0, 1.0, 2.0, 3.0] and len(metas) == 1
    for t in ('shape', 'bytes'):
        with pytest.raises(F['EvaluationError']):
            F['load_method'](write_fake_accepted(tmp_path / t, t), 'daily', 'oof', 'm::routed_context')
    with pytest.raises(F['EvaluationError'], match='neither stored nor derivable'):
        F['load_method'](docs, 'daily', 'oof', 'x::routed_context')


def test_output_guard(F, tmp_path):
    backend = tmp_path / 'backend'
    (backend / 'config').mkdir(parents=True)
    ok = F['output_paths'](backend / 'rerun-spatial-eval-t1', CFG)
    assert F['output_problems'](ok, backend, CFG) == []
    assert F['output_problems'](F['output_paths'](backend / 'rerun-x', CFG), backend, CFG)
    assert F['output_problems'](F['output_paths'](tmp_path / 'rerun-spatial-eval-t2', CFG), backend, CFG)
    assert F['output_problems'](F['output_paths'](backend / CFG['inputs']['accepted_root'], CFG), backend, CFG)
    (backend / 'real').mkdir()
    os.symlink(backend / 'real', backend / 'rerun-spatial-eval-link')
    assert any('symlink' in p for p in F['output_problems'](F['output_paths'](backend / 'rerun-spatial-eval-link', CFG), backend, CFG))
    ok['report_dir'].mkdir(parents=True)
    assert any('already exists' in p for p in F['output_problems'](ok, backend, CFG))
    p = tmp_path / 'x.bin'
    F['atomic_write_bytes'](p, b'1')
    with pytest.raises(F['EvaluationError']):
        F['atomic_write_bytes'](p, b'2')


def test_runner_refuses_bad_roots(tmp_path):
    R = load_module('run_spatial_evaluation', 'scripts/run_spatial_evaluation.py')
    cfg = R.config()
    assert R.refusal(R.BACKEND / 'rerun-spatial-eval-never-created-0', R.BACKEND, cfg) is None
    assert 'must start with' in R.refusal(R.BACKEND / 'rerun-other-1', R.BACKEND, cfg)
    assert 'directly inside' in R.refusal(tmp_path / 'rerun-spatial-eval-1', R.BACKEND, cfg)
    assert 'already exists' in R.refusal(R.BACKEND / 'notebooks', R.BACKEND, cfg)


def eval_fixture(F, province=(72.0, 72.0, np.nan)):
    S = pd.DataFrame({'segment_id': ['a', 'b', 'c'], 'geom_length_m': [1000.0, 2000.0, 500.0], 'province_code': list(province),
                      'route_code': ['0001', '0001', '0346']}).set_index('segment_id')
    D = pd.DataFrame({'day_of_week': [0, 1, 2, 3], 'month': [4, 4, 4, 4], 'season_hot': [1.0] * 4, 'season_wet': [0.0] * 4, 'season_cool': [0.0] * 4,
                      **{f'fest_{f}_{s}': [0.0] * 4 for f in ('new_year', 'songkran') for s in ('in', 'pre_1_3', 'pre_4_7', 'post_1_3', 'post_4_7')}})
    D.loc[1, 'fest_songkran_in'] = 1.0
    km = S['geom_length_m'].to_numpy() / 1000.0
    y = np.array([0, 1, 0, 0, 0, 2, 1, 0, 0, 0, 0, 0], float)
    rng = np.random.default_rng(5)
    sel = rng.gamma(1.0, 0.3, 12)
    base = np.where(np.arange(12) % 4 == 0, 0.0, sel * 0.8)
    preds = {'selected': sel, 'baseline': base}
    s = np.arange(12) % 3
    contract = F['build_colour_contract'](sel / km[s], 'daily', CFG['colour'], {'method': 'fixture'})
    edges = {r: F['calibration_edges'](p, CFG['calibration']['predicted_count_quantile_edges']) for r, p in preds.items()}
    out, accs = [], {}
    for scope, ids in (('oof', ('f1', 'f2')), ('diag', ('seen_2024', 'seen_2025'))):
        ctx = {'S': S, 'D': D, 'cfg': CFG, 'periods': [{'id': ids[0], 'row_offset': 0, 'rows': 6}, {'id': ids[1], 'row_offset': 6, 'rows': 6}],
               'methods': {'selected': 'hgb::routed_context', 'baseline': 'base'}, 'pred': {r: (lambda lo, hi, p=p: p[lo:hi]) for r, p in preds.items()},
               'y': y, 'mask': np.zeros(12, np.int8), 'n_rows': 12, 'n_seg': 3, 'n_blk': 1, 'date0': 0, 'km': km, 'contract': contract,
               'cal_edges': edges, 'floor': 1e-12, 'batch_rows': 5}
        df, accs[scope] = F['evaluate_scope']('daily', scope, ctx)
        out.append(df)
    return S, pd.concat(out, ignore_index=True), accs, y, preds, contract


def test_evaluate_scope_streams_full_population_and_province_reconciles(F):
    S, met, accs, y, preds, _ = eval_fixture(F)
    for r, p in preds.items():
        pooled = met[(met.scope == 'oof') & (met.role == r) & (met.dimension == 'pooled')].iloc[0]
        assert pooled['n'] == 12 and pooled['total_actual'] == 4.0
        assert math.isclose(pooled['deviance_sum'], F['poisson_deviance_terms'](y, p, 1e-12).sum(), rel_tol=1e-12)
        prov = met[(met.scope == 'oof') & (met.role == r) & (met.dimension == 'province')].set_index('group')
        assert prov['n'].to_dict() == {'72': 8, 'unknown': 4} and prov['total_actual'].sum() == 4.0
        assert met[(met.scope == 'oof') & (met.role == r) & (met.dimension == 'colour')]['n'].sum() == 12
    rec = F['province_reconciliation'](S, met, 'daily', 'oof', 12)
    assert rec['problems'] == [] and rec['expected_unknown_cells'] == 4 and rec['unknown_group_present'] and rec['roles'] == ['baseline', 'selected']
    dropped = met[~((met.dimension == 'province') & (met.group == 'unknown') & (met.role == 'selected'))]
    assert any('selected' in p for p in F['province_reconciliation'](S, dropped, 'daily', 'oof', 12)['problems'])
    lost = met.copy()
    lost.loc[(lost.dimension == 'province') & (lost.group == '72'), 'n'] = 7
    assert len(F['province_reconciliation'](S, lost, 'daily', 'oof', 12)['problems']) == 2
    with pytest.raises(F['EvaluationError']):
        F['province_reconciliation'](S, met, 'daily', 'oof', 13)
    # all codes known: zero expected unknown is verified explicitly (no unknown group), not forced
    S2, met2, _, _, _, _ = eval_fixture(F, (72.0, 20.0, 20.0))
    rec2 = F['province_reconciliation'](S2, met2, 'daily', 'diag', 12)
    assert rec2['problems'] == [] and rec2['expected_unknown_cells'] == 0 and not rec2['unknown_group_present'] and rec2['known_province_groups'] == 2


def test_group_table_figures_and_five_heading_presentation(F, tmp_path):
    S, met, accs, y, preds, contract = eval_fixture(F)
    gg = F['group_gain_table'](met, 'oof', ['weekday', 'province'])
    assert list(gg[gg.dimension == 'weekday'].group) == ['Mon', 'Tue', 'Wed', 'Thu'] and (gg.cells > 0).all()
    names = {'72': {'name_en': 'Suphan Buri', 'name_th': 'สุพรรณบุรี'}}
    fig = F['fig_group_panels'](gg, ['daily'], ['weekday', 'province'], 'title', note='note', names=names)
    labels = [t.get_text() for t in fig.axes[1].get_yticklabels()]
    assert labels[0].startswith('72 Suphan Buri') and fig._suptitle.get_text() == 'title'
    assert len(F['save_figure'](fig, tmp_path, 'groups')) == 2 and (tmp_path / 'groups.png').stat().st_size > 0
    lb = pd.DataFrame([{'unit': 'daily', 'method': m, 'kind': k, 'deployment_eligible': True, 'n': 12, 'mean_poisson_deviance': dv, 'mae': 0.1, 'rmse': 0.2,
                        'relative_deviance_reduction_vs_strongest_baseline': g} for m, k, dv, g in (('hgb::routed_context', 'routed_context', 0.9, 0.1), ('base', 'baseline', 1.0, 0.0))])
    fig = F['fig_bars'](lb, ['daily'], 'method', 'relative_deviance_reduction_vs_strongest_baseline', 't', 'x', pct=True, hline=0.01, horizontal=True, colour_by='kind', note='n')
    assert len(F['save_figure'](fig, tmp_path, 'methods')) == 2
    rows, summ = F['floor_audit_rows'](accs['oof'][('baseline', 'floor')], accs['oof'][('selected', 'floor')], 'daily', 'oof')
    cap = pd.DataFrame([{'unit': 'daily', 'scope': 'oof_2022_2023', 'time_block': 'all', 'role': r, 'road_km_fraction': f, 'capture_share': v}
                        for r, vs in (('selected', (0.2, 0.5)), ('baseline', (0.25, 0.4))) for f, v in zip((0.01, 0.05), vs)])
    col = pd.DataFrame([{'unit': 'daily', 'scope': 'oof_2022_2023', 'colour': 'base', 'cells': 12, 'cell_share': 1.0, 'exposure_share': 1.0, 'record_share': 1.0,
                         'observed_records_per_km_period': 0.1}])
    tr = pd.DataFrame([{'unit': 'daily', 'method': 'hgb::core', 'n': 5, 'total_actual': 1.0, 'mean_poisson_deviance': 0.5, 'relative_to_best_baseline': -0.1}])
    sel = [{'unit': 'daily', 'selected_method': 'hgb::routed_context', 'baseline': 'base', 'relative_deviance_reduction': 0.1, 'mae_ratio': 1.0,
            'n_fold_wins': 2, 'all_pass': False, 'baseline_retained': False}]
    c20 = json.loads((BACKEND / 'config' / 'spatial_experiment_v3.json').read_text('utf-8'))
    text = F['presentation_th']({
        'label_meaning': 'y = recorded count', 'sel_rows': sel, 'config20': c20, 'leaderboard': lb, 'leaderboard_all': lb, 'met': met,
        'feature_columns': {'daily': {'calendar_geometry': ['month'], 'calendar_geometry_context': ['month', 'wx_rain_sum_mm_d2']}},
        'floor_rows': pd.DataFrame(rows), 'floor_sum': [summ], 'cap': cap, 'colour_rows': col, 'transfer': tr,
        'boot': {'daily': {'resamples': 500, 'ci_low': 0.01, 'ci_high': 0.03, 'ci_status': 'ok'}}, 'contracts': {'daily': contract},
        'figs': ['figures/method_comparison.png'], 'province_names': names, 'network': {'segments': 3, 'network_km': 3.5},
        'capture_cfg': CFG['capture'], 'diag_context_cells': {'daily': 0}})
    heads = [l[3:] for l in text.splitlines() if l.startswith('## ')]
    assert heads == list(F['GATE_HEADINGS']) == ['Baseline และ Candidate Models', 'Evaluation Metrics', 'Experiment Results', 'Error Analysis', 'เหตุผลเลือกโมเดล']
    assert 'สุพรรณบุรี' in text and 'hist_gradient_boosting' in text and 'previously seen' in text and '2026' in text
    assert 'seen_2024' in text and 'f1' in text  # OOF folds and seen years are both tabulated, under separate labels


def test_independent_verifier_math_matches_but_is_separate(F):
    Vf = load_module('verify_spatial_evaluation', 'scripts/verify_spatial_evaluation.py')
    rng = np.random.default_rng(11)
    x = np.sort(rng.gamma(0.5, 1.0, 999))
    assert all(math.isclose(Vf.q7(x, q), float(np.quantile(x, q, method='linear')), rel_tol=1e-14) for q in (0.5, 0.8, 0.95))
    y, mu = rng.poisson(0.4, 50).astype(float), rng.gamma(1.0, 0.4, 50)
    mu[0] = 0.0
    assert np.allclose(Vf.unit_dev(y, mu, 1e-12), F['poisson_deviance_terms'](y, mu, 1e-12), rtol=1e-12)
    src = (BACKEND / 'scripts' / 'verify_spatial_evaluation.py').read_text('utf-8')
    assert 'exec(' not in src and 'build_colour_contract' not in src and 'capture_by_period' not in src and 'acc_add' not in src
