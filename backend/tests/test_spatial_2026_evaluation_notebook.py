"""Tests for notebook 23 (2026 raw observed-record audit + bounded positive-cell diagnostic). The four '# FUNCTIONS' cells of the assembled source
notebook are executed (never pipeline cells); the accepted notebook-18 FUNCTIONS are exec'd for the tiny-geometry linkage fixtures. Pure fixtures
only; nothing is written outside pytest tmp dirs. Run from the repository root (after assembling notebook 23):
    .venv/bin/python -m pytest backend/tests/test_spatial_2026_evaluation_notebook.py -q
"""
import importlib.util
import io
import json
import math
import types
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
NB23 = BACKEND / 'notebooks' / '23_2026_record_diagnostics.ipynb'
NB18 = BACKEND / 'notebooks' / '18_spatial_linkage_audit.ipynb'
CFG = json.loads((BACKEND / 'config' / 'spatial_2026_evaluation_v3.json').read_text('utf-8'))


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
    return exec_functions(NB23, 4)


@pytest.fixture(scope='module')
def N18():
    return exec_functions(NB18, 4)


def load_module(name, rel):
    spec = importlib.util.spec_from_file_location(name, BACKEND / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


HEADER = list(CFG['source']['columns'].values())


def raw_frame(rows):
    df = pd.DataFrame([[r.get(k, '') for k in CFG['source']['columns']] for r in rows], columns=HEADER, dtype=object)
    df.insert(0, '_source_row', np.arange(1, len(df) + 1))
    return df


def base_row(**kw):
    r = dict(year='2026', event_date='5/3/2026', event_time='8:15', report_date='10/3/2026', report_time='9:00', agency='กรมทางหลวง', route_code='2',
             route_name='x', km='1', province='นครราชสีมา', latitude='14.123456', longitude='101.123456', weather_at_event='แจ่มใส')
    r.update(kw)
    return r


# ---------- notebook structure ----------
def test_source_notebook_unexecuted_four_functions_no_handoff_reference():
    nb = json.loads(NB23.read_text('utf-8'))
    code = [c for c in nb['cells'] if c['cell_type'] == 'code']
    assert all(not c['outputs'] and c['execution_count'] is None for c in code)
    assert sum(''.join(c['source']).lstrip().startswith('# FUNCTIONS') for c in code) == 4
    assert not any('.ai-team' in ''.join(c['source']) for c in code)


def test_config_window_order_and_research_only():
    assert CFG['window'] == {'start': '2026-01-01', 'end': '2026-09-30', 'note': CFG['window']['note']}
    assert CFG['ledger_order'][-1] == 'eligible' and CFG['ledger_order'][0] == 'outside_window'
    assert any('production_ready is false' in c for c in CFG['caveats'])


def test_ledger_order_matches_config(F):
    assert list(F['EXCLUSIVE_REASONS']) == CFG['ledger_order']


# ---------- dates / times ----------
def test_explicit_dmy_no_ambiguity_leap_and_month_boundaries(F):
    iso, st = F['parse_dmy'](pd.Series(['1/2/2026', '2/1/2026', '29/2/2024', '29/2/2026', '31/4/2026', '30/9/2026', '1/10/2026', '2026-01-01', '', '01/02/26', ' 7/9/2026 ']))
    assert iso.tolist() == ['2026-02-01', '2026-01-02', '2024-02-29', None, None, '2026-09-30', '2026-10-01', None, None, None, '2026-09-07']
    assert st.tolist() == ['ok', 'ok', 'ok', 'invalid_calendar', 'invalid_calendar', 'ok', 'ok', 'bad_format', 'missing', 'bad_format', 'ok']


def test_time_precision_and_blocks(F):
    sec, st = F['parse_hm'](pd.Series(['0:01', '06:00', '5:59:59', '23:59', '24:00', '7:5', '', 'abc', '12:30:15']))
    assert st.tolist() == ['ok', 'ok', 'ok', 'ok', 'out_of_range', 'bad_format', 'missing', 'bad_format', 'ok']
    assert sec.iloc[2] == 5 * 3600 + 59 * 60 + 59 and sec.iloc[8] == 12 * 3600 + 30 * 60 + 15
    assert F['block_of'](sec.to_numpy()) == ['00-06', '06-12', '00-06', '18-24', None, None, None, None, '12-18']


# ---------- fingerprints / duplicates ----------
def test_exact_duplicate_only_full_row_not_location_time(F):
    rows = [base_row(), base_row(), base_row(km='2'), base_row(latitude='14.123457')]
    df = raw_frame(rows)
    R = F['parse_records'](df, HEADER, CFG, {'นครราชสีมา'})
    assert R['exact_duplicate_after_first'].tolist() == [False, True, False, False]
    assert R['fingerprint'].nunique() == 3


def test_missing_report_date_time_coords_province_stay_unknown(F):
    rows = [base_row(report_date=''), base_row(event_time=''), base_row(latitude=''), base_row(province='ไม่รู้จัก'), base_row(year='2025')]
    R = F['parse_records'](raw_frame(rows), HEADER, CFG, {'นครราชสีมา'})
    lag, st = F['lag_days'](R)
    assert st.tolist()[0] == 'report_date_unknown' and math.isnan(lag.iloc[0])
    assert R['invalid_date_time'].tolist() == [False, True, False, False, True]
    assert R['time_block'].iloc[1] is None
    assert R['province'].tolist()[3] == 'UNKNOWN' and not R['province_valid'].iloc[3]
    C = F['audit_coordinates'](raw_frame(rows), 'LATITUDE', 'LONGITUDE', CFG['coordinates'])
    assert C['coord_status'].tolist()[2] == 'missing'


def test_coordinate_replica_flags(F):
    rows = [base_row(latitude='101.1', longitude='14.1'), base_row(latitude='0', longitude='0'), base_row(latitude='14.1', longitude='101.1'), base_row(latitude='x')]
    C = F['audit_coordinates'](raw_frame(rows), 'LATITUDE', 'LONGITUDE', CFG['coordinates'])
    assert C['coord_status'].tolist() == ['swap_candidate_unrepaired', 'zero_coordinate', 'inside_broad_bbox_unverified', 'non_numeric']
    assert C['low_precision_flag'].tolist() == [False, False, True, False]


def test_negative_lag_and_maturity_unverified(F):
    rows = [base_row(report_date='1/3/2026'), base_row(), base_row(event_date='20/9/2026', report_date='')]
    R = F['parse_records'](raw_frame(rows), HEADER, CFG, {'นครราชสีมา'})
    lag, st = F['lag_days'](R)
    assert st.tolist() == ['negative_lag_report_before_event', 'ok', 'report_date_unknown']
    T = F['lag_table'](R, lag, st, 'event_month', '2026-11-02', 30, [3])
    assert set(T['maturity']) == {'unverified'}
    sep = T[T['event_month'] == '2026-09'].iloc[0]
    # pandas stores the missing median as NaN in a float column: assert missing semantics, never an invented number
    assert sep['n_lag_known'] == 0 and pd.isna(sep['lag_median_days']) and pd.isna(sep['lag_p99_days']) and sep['n_report_date_unknown'] == 1
    assert pd.isna(sep['share_lag_gt_label_days'])
    mar = T[T['event_month'] == '2026-03'].iloc[0]
    assert mar['n_negative_lag'] == 1 and mar['n_lag_known'] == 1 and mar['lag_median_days'] == 5.0
    # serialization: strict JSON null and an empty CSV field (never 0, never NaN text)
    rec = json.loads(F['strict_json_bytes'](T.to_dict('records')))
    js = next(r for r in rec if r['event_month'] == '2026-09')
    assert js['lag_median_days'] is None and js['share_lag_gt_label_days'] is None and js['late_arrival_risk_indicator'] is not None
    back = pd.read_csv(io.BytesIO(F['csv_bytes'](T)), dtype={'event_month': str})
    assert pd.isna(back.loc[back['event_month'] == '2026-09', 'lag_median_days']).all()


def test_late_arrival_risk_indicator_arithmetic(F):
    # reference lags (Jan-Mar, ok only): 5 (Mar) and 40 (Feb); a Sep event aged 43 d at snapshot -> share of reference lags > 43 = 0
    rows = [base_row(), base_row(event_date='1/2/2026', report_date='13/3/2026'), base_row(event_date='20/9/2026', report_date='22/9/2026'),
            base_row(event_date='30/10/2026', report_date='')]
    R = F['parse_records'](raw_frame(rows), HEADER, CFG, {'นครราชสีมา'})
    lag, st = F['lag_days'](R)
    T = F['lag_table'](R, lag, st, 'event_month', '2026-11-02', 30, [1, 2, 3]).set_index('event_month')
    assert T.at['2026-09', 'late_arrival_risk_indicator'] == 0.0
    # Oct 30 event aged 3 d: both reference lags (5, 40) exceed 3 -> 1.0; Feb share_lag_gt_label_days = 1 (40 > 30)
    assert T.at['2026-10', 'late_arrival_risk_indicator'] == 1.0 and T.at['2026-02', 'share_lag_gt_label_days'] == 1.0
    v = load_module('ver23_lag', 'scripts/verify_spatial_2026_evaluation.py')
    want, vst = v.lag_stats(R['event_date'].tolist(), R['report_date'].tolist(), '2026-11-02', 30, [1, 2, 3])
    assert vst == st.tolist()
    for m, w in want.items():
        for k, x in w.items():
            got = T.at[m, k]
            assert (x is None and pd.isna(got)) or got == pytest.approx(x), (m, k)


def test_old_new_comparison_is_net_change_not_unique_events(F):
    old = F['parse_records'](raw_frame([base_row(), base_row(km='5')]), HEADER, CFG, set())
    new = F['parse_records'](raw_frame([base_row(), base_row(km='6'), base_row(event_date='9/3/2026')]), HEADER, CFG, set())
    T = F['old_new_comparison'](old, new)
    r = T[T['event_month'] == '2026-03'].iloc[0]
    assert (r['old_raw_records'], r['new_raw_records'], r['net_record_count_change'], r['identical_full_rows_in_both']) == (2, 3, 1, 1)
    assert 'not proven unique' in r['interpretation']


# ---------- linkage (accepted notebook-18 rules on tiny metric geometry) ----------
def test_tiny_geometry_matched_ambiguous_too_far(N18):
    from shapely.geometry import LineString
    parts = pd.DataFrame({'part_uid': [0, 1, 2], 'source_id': ['doh_highway'] * 3, 'route_key': ['0002', '0002', '0024'], 'oid': [1, 2, 3], 'part': [0, 0, 0],
                          'unsafe': [False, False, False], 'geom_utm': [LineString([(0, 0), (1000, 0)]), LineString([(0, 3), (1000, 3)]), LineString([(0, 500), (1000, 500)])]})
    pts = np.array([[500.0, 40.0], [500.0, 1.4], [500.0, 300.0], [500.0, 520.0]])
    ev = pd.DataFrame({'scope': ['pilot'] * 4, 'precision_class': ['adequate_unverified'] * 4, 'source_id': ['doh_highway'] * 4,
                       'identity_status': ['verified'] * 4, 'route_key_matched': ['0002', '0002', '0002', '0024']})
    pairs = N18['candidate_pairs'](pts, parts['geom_utm'].tolist(), 105.0)
    out, _ = N18['assign_status'](ev, pairs, parts, [25.0, 50.0, 100.0], 5.0)
    # 40 m from line 0 but line 1 at 37 m is within best+5 m -> ambiguous; 1.4 m vs 1.6 m -> ambiguous; 300 m -> too_far; 20 m to the only 0024 -> matched
    assert out['status_50m'].tolist() == ['ambiguous_multiple', 'ambiguous_multiple', 'too_far', 'matched']


def synthetic_E(rows):
    base = dict(source_id='doh_highway', identity_status='verified', coord_status='inside_broad_bbox_unverified', precision_class='adequate_unverified',
                scope='pilot', status_50m='matched', segment_status='assigned', segment_id_2000m='S1', route_key_matched='0002')
    return pd.DataFrame([dict(base, **r) for r in rows])


def test_exclusive_order_and_multi_issue(F):
    rows = [base_row(), base_row(), base_row(event_date='3/10/2026', event_time=''), base_row(event_time=''), base_row(agency='กรมทางหลวงชนบท'), base_row(),
            base_row(), base_row(), base_row(), base_row(), base_row(), base_row(province='?')]
    for i, r in enumerate(rows):
        r['km'] = str(i)  # distinct raw rows: only the forced row 1 is a duplicate
    R = F['parse_records'](raw_frame(rows), HEADER, CFG, {'นครราชสีมา'})
    assert not R['exact_duplicate_after_first'].any()
    R.loc[1, 'exact_duplicate_after_first'] = True  # duplicate flag tested separately; here force the ordered precedence
    E = synthetic_E([{}, {}, {}, {}, {'source_id': 'drr_rural'}, {'identity_status': 'route_not_in_snapshot'}, {'coord_status': 'outside_broad_bbox'},
                     {'scope': 'outside_envelope'}, {'status_50m': 'too_far'}, {'status_50m': 'ambiguous_unsafe_geometry'}, {'segment_id_2000m': 'NOT_IN_UNIVERSE'}, {}])
    Fl = F['issue_flags'](R, E, CFG['window'], CFG, frozenset({'S1'}))
    reason = F['exclusive_reason'](Fl)
    assert reason.tolist() == ['eligible', 'exact_duplicate_after_first', 'outside_window', 'invalid_date_time', 'agency_outside_doh_scope',
                               'invalid_or_unknown_route', 'invalid_coordinates_or_province', 'outside_pilot_envelope', 'linkage_outside_50m',
                               'linkage_ambiguous', 'no_accepted_segment', 'invalid_coordinates_or_province']
    assert Fl.loc[2, ['outside_window', 'invalid_date_time']].all()  # multi-issue kept even though one exclusive reason
    tabs, order, multi, cross = F['ledger_tables'](R, Fl, reason)
    assert int(tabs['event_month']['raw_records'].sum()) == len(R) and int(order['records'].sum()) == len(R)
    assert int(multi['records'].sum()) == len(R)


def test_observed_cells_positive_only_and_coverage_unknown(F):
    rows = [base_row(), base_row(event_time='13:00'), base_row(event_date='6/3/2026')]
    R = F['parse_records'](raw_frame(rows), HEADER, CFG, {'นครราชสีมา'})
    E = synthetic_E([{}, {}, {}])
    el = np.array([True, True, True])
    D = F['observed_cells'](R, E, el, CFG, 'daily')
    H = F['observed_cells'](R, E, el, CFG, '6h')
    assert D['y'].tolist() == [2, 1] and len(H) == 3 and (H['y'] >= 1).all()
    cov = F['coverage_flags'](CFG['window'], 10, {'daily': D, '6h': H}, 4)
    mar = cov[(cov['unit'] == 'daily') & (cov['month'] == '2026-03')].iloc[0]
    assert mar['requested_cells'] == 31 * 10 and mar['observed_positive_cells'] == 2 and mar['unknown_cells'] == 308
    assert set(cov['zero_label_status']) == {'unverified_unknown_not_zero'} and set(cov['full_population_metric']) == {'not_available'}


# ---------- runtime use: identical keys, fallback, fail closed ----------
def fake_runtime(fail=False, ctx_missing=False):
    calls = {'selected': [], 'baseline': []}

    def resp(which, unit, rq):
        calls[which].append([dict(r) for r in rq])
        if fail:
            return {'ok': False, 'error': {'code': 'unknown_segment', 'rows': [0]}}
        res = [{'segment_id': r['segment_id'], 'target_date': r['target_date'], 'time_block': r.get('time_block'), 'expected_recorded_count': 0.25 if which == 'selected' else 0.5,
                'component_used': 'core' if ctx_missing else 'context', 'routing_reason': 'core_fallback_missing_context:wx' if ctx_missing else 'context_complete',
                'method': 'hgb::routed_context' if which == 'selected' else 'segment_mean_k365', 'model_version': 'v', 'issue_time_local': 'x',
                'source_availability': {'aadt': 'ok', 'weather_daily_rain': None, 'bank_calendar': 'unknown_preserved_missing'}} for r in rq]
        return {'ok': True, 'results': res}
    N22 = {'predict_batch': lambda s, u, rq: resp('selected', u, rq), 'predict_baseline_batch': lambda s, u, rq: resp('baseline', u, rq)}
    service = {'meta': {'max_batch': 128}}
    return N22, service, calls


def cells(n):
    return pd.DataFrame({'segment_id': ['S' + str(i) for i in range(n)], 'target_date': ['2026-03-05'] * n, 'time_block': [None] * n, 'y': [1] * n,
                         'province': ['p'] * n, 'route': ['0002'] * n, 'n_provinces': [1] * n})


def test_identical_ordered_keys_both_methods_chunked(F):
    N22, svc, calls = fake_runtime()
    P = F['predict_cells'](N22, svc, 'daily', cells(300), 128)
    assert [len(c) for c in calls['selected']] == [128, 128, 44]
    assert calls['selected'] == calls['baseline']
    assert len(P) == 300 and (P['pred_selected'] == 0.25).all() and (P['pred_baseline'] == 0.5).all()
    with pytest.raises(F['EvalError']):
        F['predict_cells'](N22, svc, 'daily', cells(3), 129)


def test_runtime_refusal_fails_closed_never_zero(F):
    N22, svc, _ = fake_runtime(fail=True)
    with pytest.raises(F['EvalError'], match='refused'):
        F['predict_cells'](N22, svc, 'daily', cells(3), 128)


def test_missing_context_fallback_group_and_metrics(F):
    N22, svc, _ = fake_runtime(ctx_missing=True)
    P = F['add_groups'](F['predict_cells'](N22, svc, 'daily', cells(30), 128), CFG)
    assert set(P['missing_context']) == {'core_fallback_missing_context'} and set(P['component_used']) == {'core'}
    assert set(P['festival']) == {'none'} and set(P['season']) == {'hot'} and set(P['weekday']) == {'Thu'}
    M = F['group_metrics'](P, 'daily')
    o = M[(M['dim'] == 'overall') & (M['method'] == 'selected')].iloc[0]
    assert o['mae'] == pytest.approx(0.75) and o['bias_pred_minus_actual'] == pytest.approx(-0.75) and o['wape'] == pytest.approx(0.75)
    assert o['mean_poisson_deviance'] == pytest.approx(2 * (math.log(1 / 0.25) - 0.75))
    cmp = F['compare_methods'](M, 20)
    assert (cmp[cmp['dim'] == 'overall']['better_mae'] == 'strong_baseline').all()  # baseline-better groups reported honestly
    rk = F['under_over_ranking'](M, 20, 3)
    # every prediction is below the actual (0.25 and 0.5 vs y = 1): no group is over-predicted -> explicit NONE row, never relabelled under rows
    over = rk[rk['kind'] == 'over_predicted']
    assert len(over) == 2 and set(over['group']) == {'NONE'} and over['pred_to_actual_ratio'].isna().all() and (over['n_groups_over'] == 0).all()
    under = rk[rk['kind'] == 'under_predicted']
    assert (under['pred_to_actual_ratio'] < 1).all() and set(under['method']) == {'selected', 'strong_baseline'}
    assert 'most_over_predicted' not in set(rk['kind'])
    lines = F['ranking_summary_th'](rk)
    assert len(lines) == 2 and all('ไม่มีกลุ่มใดที่ทำนายสูงกว่าจริง' in s for s in lines)


def ratio_metrics(ratios, support=25):
    """Synthetic metric rows (unit daily, two methods) with the given pred/actual ratio per group."""
    rows = []
    for meth in ('selected', 'strong_baseline'):
        for i, r in enumerate(ratios):
            rows.append({'unit': 'daily', 'dim': 'month', 'group': '2026-0' + str(i + 1), 'method': meth, 'n_positive_cells': support,
                         'n_raw_records': 100, 'pred_to_actual_ratio': r})
        rows.append({'unit': 'daily', 'dim': 'overall', 'group': 'all', 'method': meth, 'n_positive_cells': 999, 'n_raw_records': 999, 'pred_to_actual_ratio': 0.5})
    return pd.DataFrame(rows)


def rank_expected_rows(M):
    return [{'unit': r.unit, 'method': r.method, 'dim': r.dim, 'group': r.group, 'n_positive_cells': r.n_positive_cells, 'ratio': r.pred_to_actual_ratio}
            for r in M.itertuples(index=False)]


@pytest.mark.parametrize('ratios,n_under,n_over', [([0.04, 0.09, 0.06], 3, 0), ([1.5, 2.0, 1.1], 0, 3), ([0.5, 1.0, 1.7, 0.8], 2, 1)])
def test_under_over_true_direction_all_under_all_over_mixed(F, ratios, n_under, n_over):
    M = ratio_metrics(ratios)
    rk = F['under_over_ranking'](M, 20, 2)
    for meth in ('selected', 'strong_baseline'):
        g = rk[rk['method'] == meth]
        u, o, t = (g[g['kind'] == k] for k in ('under_predicted', 'over_predicted', 'total_match'))
        assert (g['n_groups_under'] == n_under).all() and (g['n_groups_over'] == n_over).all()
        if n_under:
            assert (u['pred_to_actual_ratio'] < 1).all() and u['pred_to_actual_ratio'].is_monotonic_increasing and len(u) == min(2, n_under)
        else:
            assert len(u) == 1 and u.iloc[0]['group'] == 'NONE'
        if n_over:
            assert (o['pred_to_actual_ratio'] > 1).all() and o['pred_to_actual_ratio'].is_monotonic_decreasing and len(o) == min(2, n_over)
        else:
            assert len(o) == 1 and o.iloc[0]['group'] == 'NONE'
        assert (t['pred_to_actual_ratio'] == 1).all() and len(t) == sum(r == 1 for r in ratios)
        assert 'overall' not in set(g['dim'])
    # independent verifier logic agrees, and detects a relabelled (wrong-direction) ranking
    v = load_module('ver23_rank', 'scripts/verify_spatial_2026_evaluation.py')
    exp = v.expected_ranking(rank_expected_rows(M), 20, 2)
    RK = rk.astype(object).where(rk.notna(), '').astype(str)
    assert v.ranking_problems(RK, exp) == []
    bad = rk.copy()
    sel = bad['kind'] == ('under_predicted' if n_under else 'over_predicted')
    bad.loc[sel, 'kind'] = 'over_predicted' if n_under else 'under_predicted'
    assert v.ranking_problems(bad.astype(object).where(bad.notna(), '').astype(str), exp)


def test_under_over_support_threshold_excludes_small_groups(F):
    M = ratio_metrics([1.5, 0.5])
    M.loc[(M['group'] == '2026-01'), 'n_positive_cells'] = 5  # the only over group is unsupported
    rk = F['under_over_ranking'](M, 20, 3)
    o = rk[(rk['kind'] == 'over_predicted') & (rk['method'] == 'selected')]
    assert len(o) == 1 and o.iloc[0]['group'] == 'NONE' and o.iloc[0]['n_supported_groups'] == 1


def test_metric_zero_prediction_deviance_status_and_wape_zero_actual(F):
    m = F['metric_row']([1, 2], [0.0, 1.0])
    assert m['mean_poisson_deviance'] is None and m['n_zero_pred_on_positive'] == 1 and m['deviance_status'] == 'infinite_due_zero_prediction'
    assert F['metric_row']([0, 0], [1.0, 1.0])['wape'] is None
    assert F['metric_row']([], [])['deviance_status'] == 'unavailable_empty'
    ok = F['metric_row']([1, 2], [0.5, 1.0])
    assert ok['deviance_status'] == 'finite' and ok['mean_poisson_deviance'] == pytest.approx(np.mean([2 * (math.log(2) - 0.5), 2 * (2 * math.log(2) - 1)]))
    # strict JSON: the non-finite raw deviance is null, the status is explicit
    js = json.loads(F['strict_json_bytes'](m))
    assert js['mean_poisson_deviance'] is None and js['deviance_status'] == 'infinite_due_zero_prediction'


def test_original_floor_audit_from_saved_lambdas(F):
    fl = 1e-12
    m = F['metric_row']([1, 2, 1], [0.0, 1.0, 0.5], fl)
    # raw stays null with status; the audit uses m = max(lambda, 1e-12) inside the deviance only
    t = [2 * (1 * math.log(1 / fl) - (1 - fl)), 2 * (2 * math.log(2) - 1), 2 * (math.log(2) - 0.5)]
    assert m['mean_poisson_deviance'] is None and m['deviance_status'] == 'infinite_due_zero_prediction'
    assert m['deviance_floor_audit'] == pytest.approx(np.mean(t)) and m['deviance_floor_audit_n_floored'] == 1
    assert m['deviance_floor_audit_floored_contribution'] == pytest.approx(t[0] / 3) and m['deviance_floor_audit_floor'] == fl
    # no prediction below the floor -> the two definitions coincide
    c = F['metric_row']([1, 2], [0.5, 1.0], fl)
    assert c['deviance_floor_audit_n_floored'] == 0 and c['deviance_floor_audit'] == pytest.approx(c['mean_poisson_deviance'])
    v = load_module('ver23_floor', 'scripts/verify_spatial_2026_evaluation.py')
    w = v.metrics(np.array([1.0, 2.0, 1.0]), np.array([0.0, 1.0, 0.5]), fl)
    for k in ('deviance_floor_audit', 'deviance_floor_audit_n_floored', 'deviance_floor_audit_floored_contribution', 'n_zero_pred_on_positive', 'mae', 'wape'):
        assert w[k] == pytest.approx(m[k]), k
    assert w['mean_poisson_deviance'] is None and w['deviance_status'] == m['deviance_status']
    assert CFG['metrics']['original_deviance_floor_audit']['expected_floor'] == fl


def test_group_metrics_status_columns_and_comparison(F):
    P = cells(30).assign(pred_selected=0.5, pred_baseline=0.0)
    P = F['add_groups'](P.assign(routing_reason='context_complete', component_used='context'), CFG)
    M = F['group_metrics'](P, 'daily', 1e-12)
    o = M[M['dim'] == 'overall'].set_index('method')
    assert o.at['selected', 'deviance_status'] == 'finite' and o.at['strong_baseline', 'deviance_status'] == 'infinite_due_zero_prediction'
    assert o.at['strong_baseline', 'n_zero_pred_on_positive'] == 30 and pd.isna(o.at['strong_baseline', 'mean_poisson_deviance'])
    assert o.at['strong_baseline', 'deviance_floor_audit_n_floored'] == 30 and np.isfinite(o.at['strong_baseline', 'deviance_floor_audit'])
    cmp = F['compare_methods'](M, 20)
    r = cmp[cmp['dim'] == 'overall'].iloc[0]
    assert r['better_deviance'] == 'undefined' and r['deviance_status_baseline'] == 'infinite_due_zero_prediction' and r['n_zero_pred_on_positive_baseline'] == 30


def test_multi_province_counts_and_mode_rule(F):
    rows = [base_row(), base_row(province='ขอนแก่น', km='2'), base_row(event_date='6/3/2026')]
    R = F['parse_records'](raw_frame(rows), HEADER, CFG, {'นครราชสีมา', 'ขอนแก่น'})
    C = F['observed_cells'](R, synthetic_E([{}, {}, {}]), np.array([True, True, True]), CFG, 'daily')
    assert C['province'].tolist()[0] == sorted(['นครราชสีมา', 'ขอนแก่น'])[0] and C['n_provinces'].tolist() == [2, 1]  # tie -> lexically first
    mp = F['multi_province_counts']({'daily': C}).iloc[0]
    assert (mp['positive_cells'], mp['multi_province_cells'], mp['raw_records_in_multi_province_cells']) == (2, 1, 2)
    assert 'not the segment-midpoint province' in mp['province_rule']


def test_report_th_discloses_status_floor_geography_and_calendar(F):
    P = F['add_groups'](cells(30).assign(pred_selected=0.5, pred_baseline=0.0, routing_reason='context_complete', component_used='context'), CFG)
    M = F['group_metrics'](P, 'daily', 1e-12)
    T = {'metrics': M, 'under_over_ranking': F['under_over_ranking'](M, 20, 3), 'multi_province': pd.DataFrame([{'unit': 'daily', 'multi_province_cells': 0}]),
         'ledger_order': pd.DataFrame([{'step': 1, 'reason': 'eligible', 'records': 30}]),
         'lag_by_month': pd.DataFrame([{'event_month': '2026-03', 'n_raw_records': 30, 'n_lag_known': 0, 'n_report_date_unknown': 30, 'n_negative_lag': 0,
                                        'lag_median_days': np.nan, 'lag_p90_days': np.nan, 'lag_p99_days': np.nan, 'share_lag_gt_label_days': np.nan,
                                        'late_arrival_risk_indicator': np.nan, 'maturity': 'unverified'}]),
         'old_new_monthly': pd.DataFrame([{'event_month': '2026-03', 'old_raw_records': 1, 'interpretation': 'x'}])}
    facts = {'ckan': {'last_modified': 't', 'file_bytes': 1, 'ckan_hash_equals_file_md5': False}, 'source_sha256': 'a' * 64,
             'new_dates': {'raw_rows': 30, 'event_date_min': 'a', 'event_date_max': 'b', 'report_date_min': 'c', 'report_date_max': 'd',
                           'exact_full_row_duplicates_after_first': 0}, 'deviance_floor': {'floor': 1e-12, 'config20_sha256': 'f' * 64}}
    md = F['report_th']('complete', T, facts, CFG)
    for s in ('deviance_status', 'infinite_due_zero_prediction', 'n_zero_pred_on_positive', 'deviance_floor_audit', 'numerical-floor audit', '1e-12',
              'ไม่มีกลุ่มใดที่ทำนายสูงกว่าจริง', '**ไม่ใช่** จังหวัดจากจุดกึ่งกลาง segment', 'analytical windows', '07:19', '08:13', 'right-truncated', 'ไม่ใช่** สัดส่วนเหตุการณ์จริง'):
        assert s in md, s
    assert 'most_over_predicted' not in md


# ---------- trust / tamper / strict JSON ----------
def test_verify_file_and_functions_tamper(F, tmp_path):
    p = tmp_path / 'a.txt'
    p.write_text('x')
    ok = F['sha256_file'](p)
    assert F['verify_file'](p, ok, 'a') == ok
    for bad in (None, '0' * 64, 'zz'):
        with pytest.raises(F['EvalError']):
            F['verify_file'](p, bad, 'a')
    nb = tmp_path / 'n.ipynb'
    nb.write_text(json.dumps({'cells': [{'cell_type': 'code', 'source': '# FUNCTIONS 1\nX = 1'}, {'cell_type': 'code', 'source': 'Y = 2'}]}))
    good = F['sha256_bytes']('# FUNCTIONS 1\nX = 1'.encode())
    ns, _ = F['load_functions'](nb, 1, '\n\n', good, 'n')
    assert ns['X'] == 1 and 'Y' not in ns
    with pytest.raises(F['EvalError']):
        F['load_functions'](nb, 1, '\n\n', '0' * 64, 'n')


def test_strict_json_refuses_nan(F, tmp_path):
    p = tmp_path / 'x.json'
    p.write_text('{"a": NaN}')
    with pytest.raises(F['EvalError']):
        F['read_strict_json'](p)
    assert b'null' in F['strict_json_bytes']({'a': float('nan')})


def test_pins_wrong_kind_refused(F, tmp_path):
    b = tmp_path / 'backend'
    (b / 'p').mkdir(parents=True)
    (b / 'p' / 'pins.json').write_text(json.dumps({'kind': 'other', 'files': {'x': 'y'}}))
    cfg = {'pins': {'runtime': 'p/pins.json', 'runtime_kind': CFG['pins']['runtime_kind']}}
    with pytest.raises(F['EvalError'], match='wrong kind'):
        F['load_pins'](b, cfg, 'runtime')


def test_output_guard_refuses_reuse_and_protected_overlap(F, tmp_path):
    b = tmp_path / 'backend'
    (b / 'data' / 'raw' / 'accidents').mkdir(parents=True)
    cfg = dict(CFG)
    P = F['output_paths'](b, cfg)
    with pytest.raises(F['EvalError']):
        F['check_outputs']({'out_root': b, 'report_dir': b / 'data' / 'raw' / 'accidents' / 'r', 'data_dir': b / 'x'}, b, cfg)
    root = b / 'rerun-2026-eval-t'
    P = F['output_paths'](root, cfg)
    assert F['check_outputs'](P, b, cfg)
    P['report_dir'].mkdir(parents=True)
    with pytest.raises(F['EvalError'], match='NEW root'):
        F['check_outputs'](P, b, cfg)
    with pytest.raises(F['EvalError']):
        F['check_report_file']('rows.csv.gz', cfg)


def test_ckan_provenance_mismatch_refused(F, tmp_path):
    f = tmp_path / 'a.csv'
    f.write_bytes(b'abc')
    pkg = {'success': True, 'result': {'resources': [{'id': 'rid', 'format': 'CSV', 'size': 3, 'last_modified': 't', 'url': 'u/rid/a.csv', 'hash': ''}]}}
    assert F['ckan_provenance'](pkg, 'rid', f, {'bytes': 3, 'last_modified': 't'})['file_bytes'] == 3
    with pytest.raises(F['EvalError']):
        F['ckan_provenance'](pkg, 'rid', f, {'bytes': 4, 'last_modified': 't'})


# ---------- runner / verifier ----------
def test_runner_refuses_bad_roots(tmp_path):
    m = load_module('run23', 'scripts/run_spatial_2026_evaluation.py')
    assert 'must start with' in m.refusal(BACKEND / 'other-root', BACKEND, CFG)
    assert 'directly inside' in m.refusal(tmp_path / 'rerun-2026-eval-x', BACKEND, CFG)
    assert m.refusal(BACKEND / 'rerun-2026-eval-test-never-created', BACKEND, CFG) is None
    assert 'already exists' in m.refusal(BACKEND / 'notebooks', BACKEND, CFG)


def test_verifier_independent_parsers_and_no_producer_import():
    src = (BACKEND / 'scripts' / 'verify_spatial_2026_evaluation.py').read_text('utf-8')
    assert 'exec(' not in src and 'load_functions' not in src and 'run_spatial_2026_evaluation' not in src and 'import nbformat' not in src
    v = load_module('ver23', 'scripts/verify_spatial_2026_evaluation.py')
    assert v.dmy('29/2/2024') == '2024-02-29' and v.dmy('29/2/2026') is None and v.dmy('2026-01-01') is None
    assert v.hm('24:00') is None and v.hm('6:00') == 21600 and v.hm('7:5') is None
    m = v.metrics(np.array([1.0, 2.0]), np.array([1.0, 1.0]))
    assert m['mae'] == 0.5 and m['wape'] == pytest.approx(1 / 3)
