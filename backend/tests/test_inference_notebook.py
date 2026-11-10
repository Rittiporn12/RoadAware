"""Tests for V2 notebook 13 (research inference / serving contract) and the runner's serve-check stage. No network, no kernel.

The notebook's own '# FUNCTIONS' cells are executed (plus the accepted notebook 10/11 FUNCTIONS for the pinned helpers), so the logic under
test is what the service runs. Fixture expectations are worked out by hand. Integration tests at the bottom use the real accepted artifacts
under backend/ and are skipped (with the reason) when those gitignored files are absent. Run from the repository root:
    .venv/bin/python -m pytest backend/tests/test_inference_notebook.py -q
"""
import datetime as dt
import importlib.util
import json
import math
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
NB13 = BACKEND / 'notebooks' / '13_inference_robustness_contract.ipynb'
NB10 = BACKEND / 'notebooks' / '10_v2_preparation_features_leakage.ipynb'
NB11 = BACKEND / 'notebooks' / '11_v2_model_experiments.ipynb'
RUNNER = BACKEND / 'scripts' / 'run_v2_notebooks.py'
CFG = json.loads((BACKEND / 'config' / 'inference_v2.json').read_text('utf-8'))
FCFG = json.loads((BACKEND / 'config' / 'feature_pipeline_v2.json').read_text('utf-8'))
SCFG = json.loads((BACKEND / 'config' / 'external_sources_v2.json').read_text('utf-8'))
REAL = (BACKEND / 'data' / 'v2' / 'models' / 'bundles').is_dir() and (BACKEND / 'reports' / 'v2' / 'models' / 'model_manifest.json').is_file()


def code_cells(nb):
    d = json.loads(nb.read_text('utf-8'))
    return [''.join(c['source']) if isinstance(c['source'], list) else c['source'] for c in d['cells'] if c['cell_type'] == 'code']


def exec_functions(nb):
    ns = {}
    for i, s in enumerate(s for s in code_cells(nb) if s.lstrip().startswith('# FUNCTIONS')):
        exec(compile(s, f'{nb.stem}:FUNCTIONS[{i}]', 'exec'), ns)
    return ns


@pytest.fixture(scope='module')
def f():
    return exec_functions(NB13)


@pytest.fixture(scope='module')
def runner():
    spec = importlib.util.spec_from_file_location('run_v2_notebooks', RUNNER)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class FakePipe:
    """Stands in for a fitted bundle: records the matrix it received; mean = 0.5 + 0.25 for the 18-24 block + 0.1 when traffic is NaN."""

    def __init__(self, out=None):
        self.seen, self.out = [], out

    def predict(self, X):
        self.seen.append(X)
        if self.out is not None:
            return np.full(len(X), self.out)
        v = np.full(len(X), 0.5)
        if 'time_block' in X:
            v = v + 0.25 * (X['time_block'].to_numpy() == '18-24')
        return v + 0.1 * np.isnan(X['trf_mean_aadt'].to_numpy(float))


CALREC = pd.DataFrame({'date': ['2024-05-06', '2024-05-10'], 'action': ['add', 'add'], 'known_from': ['2023-12-01', '2024-05-10'],
                       'applied': [True, True], 'source_id': ['base_2024', 'late_special']})
TMETA = pd.DataFrame({'survey_year_ce': ['2022', '2023', '2024'], 'normalize_status': ['normalized'] * 3,
                      'available_from_proxy_utc': ['2023-03-01T00:00:00+00:00', '2024-06-01T00:00:00+00:00', '2024-01-02T00:00:00+00:00']})
TSUM = pd.DataFrame({'province_key': ['P1', 'P1', 'P1'], 'survey_year_ce': ['2022', '2023', '2024'], 'mean_total_aadt': ['1000', '2000', '9999'],
                     'median_total_aadt': ['900', '1800', '9999'], 'mean_heavy_share_pct': ['10', '20', '99'], 'n_station_rows': ['5', '6', '7']})


def pinned(f, nb, used):
    """The exact helper container load_registry() builds: notebook 13's exec_pinned_functions over the accepted notebook's FUNCTIONS."""
    return f['exec_pinned_functions'](nb, f['sha256_bytes'](f['functions_cells_source'](nb).encode('utf-8')), nb.stem, used)


@pytest.fixture()
def reg(f):
    fn10, fn11 = pinned(f, NB10, f['FN10_USED']), pinned(f, NB11, f['FN11_USED'])
    allow_d = [x['name'] for x in FCFG['features'] if 'daily' in x['panels']]
    allow_b = [x['name'] for x in FCFG['features'] if '6h' in x['panels'] and not x['name'].startswith('wx_')]
    cols_b = ['province', 'time_block'] + [c for c in allow_b if c not in ('province', 'time_block')]
    wxd = pd.DataFrame({'province_key': ['P1'], 'target_date': ['2024-05-01'], 'wx_rain_sum_mm_d2': [3.5], 'wx_temp_mean_c_d2': [28.0]})
    wxb = pd.DataFrame({'province_key': ['P1'], 'target_date': ['2024-05-01'], 'time_block': ['18-24'], 'wx_block_rain_sum_mm_d2': [1.0],
                        'wx_block_temp_mean_c_d2': [27.0]})
    bstate = {'id': 'province_mean', 'spec': {'id': 'province_mean', 'levels': [['province_key']]}, 'n_train': 3, 'global_mean': 1.0,
              'levels': [{'cols': ['province_key'], 'table': {'P1': [6.0, 3]}}], 'smooth': None, 'recent': None, 'frozen_at': None}
    unit = lambda mid, cols, cats: {'method_id': mid, 'family': 'hgb', 'variant': 'x', 'bundle_sha256': 'b' * 64, 'feature_columns': cols, 'categorical': cats,
                                    'pipeline': FakePipe(), 'baseline_method_id': 'baseline_province_mean', 'baseline_sha256': 'c' * 64, 'baseline_state': bstate,
                                    'fit_cutoff_local': '2023-12-31T18:00:00+07:00'}
    return {'cfg': CFG, 'province_set': {'P1', 'P2'}, 'provinces': ['P1', 'P2'], 'aliases': {'Alias One': 'P1'}, 'fn10': fn10, 'fn11': fn11,
            'feature_config': FCFG, 'panel': FCFG['panel'], 'issue': {'issue_hour': 18, 'days_before': 1}, 'threads': 1, 'models_loaded': True,
            'sources_config': {'calendar': {'recurring_fixed_festivals': SCFG['calendar']['recurring_fixed_festivals'],
                                            'sources': [{'id': 'base_2024', 'role': 'annual_base', 'years': [2024]}]}},
            'cache': {'calendar_records': CALREC, 'traffic_meta': TMETA, 'traffic_summary': TSUM,
                      'wx_daily': wxd.set_index(['province_key', 'target_date']), 'wx_block': wxb.set_index(['province_key', 'target_date', 'time_block'])},
            'units': {'daily': unit('m_daily', allow_d, ['province']), '6h': unit('m_6h', cols_b, ['province', 'time_block'])},
            'registry_id': 'test', 'coverage': {'weather_last_feature_date': {'wx_': '2024-05-01'}},
            'preparation_manifest': {'next_stage_interface': {'categorical': ['province', 'time_block'],
                                                              'feature_groups': {'weather': ['wx_rain_sum_mm_d2', 'wx_temp_mean_c_d2', 'wx_block_rain_sum_mm_d2',
                                                                                             'wx_block_temp_mean_c_d2']}}}}


def codes(f, reg, req):
    with pytest.raises(f['RequestValidationError']) as ex:
        f['validate_requests'](reg, req)
    return sorted({e['code'] for e in ex.value.errors})


D = {'province_key': 'P1', 'target_date': '2024-05-01', 'unit': 'daily'}
B = {'province_key': 'P1', 'target_date': '2024-05-01', 'unit': '6h', 'time_block': '18-24'}


# ---------- structure ----------
def test_notebook_structure_self_contained():
    cells = code_cells(NB13)
    assert cells[0].startswith('# SETUP') and cells[1].startswith('# FUNCTIONS') and cells[2].startswith('# FUNCTIONS')
    assert sum(c.startswith('# FUNCTIONS') for c in cells) == 2
    for c in cells:
        compile(c, 'cell', 'exec')
        assert '.ai-team' not in c and 'handoffs' not in c and 'urllib' not in c and 'requests.get' not in c
        assert '.fit(' not in c and 'GridSearch' not in c
    fn = cells[1] + cells[2]
    assert 'joblib.load' in fn and fn.index('verify_file(p, expected_sha, label)') < fn.index('return loader(p)')
    builder = fn[fn.index('# ---------- training numeric representation contract'):fn.index('def model_matrix')]
    assert 'def training_numeric_representation' in builder and 'def build_raw_feature_frame' in builder
    for bad in ('training_eligible', 'y_recorded_count', 'panel_daily', 'panel_6h', "['y']", 'split', 'features_daily', 'features_6h', 'round('):
        assert bad not in builder, bad
    # 008b: the only prediction feature path applies the training numeric representation; the raw builder is never fed to a bundle in FUNCTIONS
    bff = fn[fn.index('def build_feature_frame'):fn.index('def build_raw_feature_frame')]
    assert 'training_numeric_representation(raw, num)' in bff
    assert fn.count('build_raw_feature_frame(') == 2 and fn.count('build_feature_frame(') >= 4
    body = '\n'.join(cells[3:])
    assert body.index('REG = load_registry(') < body.index('predict_frame(') and 'serving_manifest.json' in cells[-1]
    assert 'public_predict_batch_matches_saved_11' in body and 'public_predict_batch_vs_11' in cells[-1]


# ---------- pinned helper container (regression 008a: dict namespace, attribute access raised AttributeError) ----------
def test_pinned_helper_container_mapping_access_everywhere(f):
    import re
    cells = code_cells(NB13)
    for c in cells:
        assert not re.search(r"\b(fn10|fn11|FN10|FN11)\s*\.\s*[A-Za-z_]", c), 'pinned helpers are a dict: use fn10[...] / fn11[...]'
        assert not re.search(r"\['fn1[01]'\]\s*\.", c)
    fn = cells[1] + cells[2]
    used10 = set(re.findall(r"\bfn10\['(\w+)'\]", fn)) | set(re.findall(r"\['fn10'\]\['(\w+)'\]", fn))
    used11 = set(re.findall(r"\bfn11\['(\w+)'\]", fn)) | set(re.findall(r"\['fn11'\]\['(\w+)'\]", fn)) | \
             set(re.findall(r"\bFN11\['(\w+)'\]", '\n'.join(cells)))
    assert used10 and used10 <= set(f['FN10_USED']), used10 - set(f['FN10_USED'])
    assert used11 and used11 <= set(f['FN11_USED']), used11 - set(f['FN11_USED'])
    assert set(CFG['pinned_functions']['notebook10']['required']) <= set(f['FN10_USED'])
    assert set(CFG['pinned_functions']['notebook11']['required']) <= set(f['FN11_USED'])


def test_exec_pinned_functions_returns_dict_with_every_used_helper(f):
    for nb, used in ((NB10, f['FN10_USED']), (NB11, f['FN11_USED'])):
        ns = pinned(f, nb, used)
        assert type(ns) is dict and all(callable(ns[n]) for n in used)
        assert not hasattr(ns, used[0])                                 # attribute access on this container can never work
    with pytest.raises(f['DependencyError']):
        pinned(f, NB10, tuple(f['FN10_USED']) + ('not_a_notebook10_helper',))


# ---------- request validation (hand-written cases) ----------
def test_valid_requests_normalized(f, reg):
    out = f['validate_requests'](reg, [D, B, {'province_key': 'Alias One', 'target_date': '2030-12-31', 'unit': 'daily', 'time_block': None}])
    assert [c['index'] for c in out] == [0, 1, 2]
    assert out[1]['time_block'] == '18-24' and out[0]['time_block'] is None
    assert out[2]['province_key'] == 'P1' and out[2]['alias_applied'] and out[2]['province_key_input'] == 'Alias One'


@pytest.mark.parametrize('req,code', [
    ([dict(D, province_key='P9')], 'unknown_province'), ([dict(D, province_key=' P1')], 'unknown_province'), ([dict(D, province_key=1)], 'invalid_type'),
    ([dict(D, target_date='2025-02-29')], 'invalid_date'), ([dict(D, target_date='2024-02-29T00:00')], 'invalid_format'),
    ([dict(D, target_date='2024-5-01')], 'invalid_format'), ([dict(D, target_date='๒๐๒๔-05-01')], 'invalid_format'),
    ([dict(D, target_date='2567-05-01')], 'buddhist_era_year'), ([dict(D, target_date=True)], 'invalid_type'),
    ([dict(D, target_date=float('nan'))], 'invalid_type'), ([dict(D, target_date=float('inf'))], 'invalid_type'),
    ([dict(D, target_date=dt.date(2024, 5, 1))], 'invalid_type'), ([dict(D, target_date='2023-12-31')], 'out_of_service_range'),
    ([dict(D, target_date='2031-01-01')], 'out_of_service_range'), ([dict(D, unit='weekly')], 'invalid_unit'),
    ([{k: v for k, v in B.items() if k != 'time_block'}], 'missing_field'), ([dict(B, time_block='06-18')], 'invalid_time_block'),
    ([dict(D, time_block='00-06')], 'incompatible_unit'), ([dict(D, y_recorded_count=0)], 'unknown_field'),
    ([dict(D, training_eligible=True)], 'unknown_field'), ([dict(D, bundle_path='/tmp/x.joblib')], 'unknown_field'),
    ([dict(D, trf_mean_aadt=1.0)], 'unknown_field'), ([D, dict(D)], 'duplicate_request'), ([D, dict(D, province_key='Alias One')], 'duplicate_request'),
    ([], 'batch_size'), ([dict(D, target_date=(dt.date(2024, 1, 1) + dt.timedelta(days=i)).isoformat()) for i in range(129)], 'batch_size'),
    ({'requests': [D]}, 'invalid_type'), (['x'], 'invalid_type')])
def test_invalid_requests_rejected(f, reg, req, code):
    assert code in codes(f, reg, req)


def test_batch_limit_inclusive(f, reg):
    req = [dict(D, target_date=(dt.date(2024, 1, 1) + dt.timedelta(days=i)).isoformat()) for i in range(128)]
    assert len(f['validate_requests'](reg, req)) == 128


# ---------- feature builder (hand-calculated) ----------
def test_builder_date_festival_season_hand_values(f, reg):
    cells = [dict(province_key='P1', target_date=d) for d in ('2024-02-29', '2024-04-13', '2024-04-10', '2024-04-18', '2024-12-30', '2025-01-01', '2025-01-02')]
    fr = f['build_feature_frame'](reg, cells, 'daily').set_index('target_date')
    r = fr.loc['2024-02-29']
    assert (r['day_of_week'], r['month'], r['day_of_month'], r['is_weekend']) == (3, 2, 29, 0)
    assert math.isclose(r['doy_sin'], math.sin(2 * math.pi * 59 / 366), abs_tol=1e-15) and r['season_cool'] == 1 and r['season_hot'] == 0
    assert fr.loc['2024-04-13', 'fest_songkran_in'] == 1 and fr.loc['2024-04-13', 'fest_songkran_dist'] == 0
    assert fr.loc['2024-04-10', 'fest_songkran_dist'] == -3 and fr.loc['2024-04-10', 'fest_songkran_pre_1_3'] == 1
    assert fr.loc['2024-04-18', 'fest_songkran_dist'] == 3 and fr.loc['2024-04-18', 'fest_songkran_post_1_3'] == 1
    assert fr.loc['2024-12-30', 'fest_new_year_dist'] == -1 and fr.loc['2025-01-01', 'fest_new_year_in'] == 1
    assert fr.loc['2025-01-02', 'fest_new_year_dist'] == 1 and fr.loc['2025-01-02', 'fest_new_year_post_1_3'] == 1


def test_builder_asof_negative_controls(f, reg):
    cells = [dict(province_key=p, target_date=d) for p, d in (('P1', '2024-05-06'), ('P1', '2024-05-10'), ('P1', '2025-05-06'), ('P1', '2024-05-01'),
                                                             ('P1', '2024-07-01'), ('P1', '2023-02-01'), ('P2', '2024-07-01'))]
    fr = f['build_feature_frame'](reg, cells, 'daily')
    assert fr['bank_holiday_asof'].iloc[0] == 1.0                                  # base record known well before issue
    assert fr['bank_holiday_asof'].iloc[1] == 0.0                                  # announced on the target day: unknown at issue -> not a holiday
    assert np.isnan(fr['bank_holiday_asof'].iloc[2]) and fr['bank_calendar_known_asof'].iloc[2] == 0   # no reviewed 2025 calendar: NaN, not ordinary 0
    assert fr['trf_vintage_survey_year_ce'].iloc[3] == 2022 and fr['trf_mean_aadt'].iloc[3] == 1000.0  # 2023 survey revised after issue
    assert fr['trf_vintage_survey_year_ce'].iloc[4] == 2023 and fr['trf_mean_aadt'].iloc[4] == 2000.0  # never the same-year 2024 survey
    assert np.isnan(fr['trf_mean_aadt'].iloc[5])                                   # nothing available yet
    assert np.isnan(fr['trf_mean_aadt'].iloc[6])                                   # province absent from the vintage stays NaN
    assert fr['wx_rain_sum_mm_d2'].iloc[3] == 3.5 and fr['wx_rain_sum_mm_d2'].iloc[[0, 1, 2, 4]].isna().all()   # cached guard-passed weather only


def test_weather_after_issue_is_nan_not_backfilled(reg):
    fn10 = reg['fn10']
    wx = pd.DataFrame({'province_code': ['10'], 'date': ['2024-05-10'], 'time_block': ['day'], 'rain_sum': ['5.0'], 'temp_mean': ['30.0'],
                       'rain_missing': ['False'], 'temp_missing': ['False'], 'issue_bound_ok': ['False'], 'latest_issue_bound_utc': ['2024-05-09T10:00:00+00:00']})
    out, _ = fn10['weather_features'](wx, {10: 'P1'}, 6, 18, 1, 25200, 'wx_')
    assert out['wx_rain_sum_mm_d2'].isna().all()


def test_builder_preserves_order_and_6h_blocks(f, reg):
    cells = [dict(province_key='P2', target_date='2024-05-02', time_block=b) for b in ('18-24', '00-06', '12-18', '06-12')] + \
            [dict(province_key='P1', target_date='2024-05-01', time_block='18-24')]
    fr = f['build_feature_frame'](reg, cells, '6h')
    assert fr['time_block'].tolist() == ['18-24', '00-06', '12-18', '06-12', '18-24'] and fr['province'].tolist() == ['P2'] * 4 + ['P1']
    assert fr['wx_block_rain_sum_mm_d2'].iloc[4] == 1.0 and fr['wx_block_rain_sum_mm_d2'].iloc[:4].isna().all()


# ---------- training numeric representation (regression 008b: 1-ulp doy_sin/doy_cos differences flipped tree thresholds on 2025) ----------
def accepted_10_to_11_boundary(fn10, frame, num_cols, str_cols, path):
    """Independent reference, NOT the 13 helper: the accepted notebook 10 writer itself, then the exact notebook 11 load_unit_frame parse."""
    fn10['write_csv_gz'](path, frame)
    back = pd.read_csv(path, dtype={c: str for c in str_cols}, keep_default_na=False, na_values=[''])
    return {c: pd.to_numeric(back[c], errors='raise').astype(float).to_numpy() for c in num_cols}


def test_training_numeric_representation_equals_accepted_10_writer_11_parser(f, reg, tmp_path):
    fn10 = reg['fn10']
    dates = pd.date_range('2021-01-01', '2025-12-31').strftime('%Y-%m-%d').tolist()
    raw = fn10['core_date_features'](dates)
    num = [c for c in raw.columns if c != 'target_date' and pd.api.types.is_numeric_dtype(raw[c])]
    assert {'doy_sin', 'doy_cos', 'day_of_week'} <= set(num)
    raw = raw.assign(wx_x=np.where(np.arange(len(raw)) % 3 == 0, np.nan, np.arange(len(raw)) / 7.0), province='P1')
    num.append('wx_x')
    want = accepted_10_to_11_boundary(fn10, raw, num, ['target_date', 'province'], tmp_path / 'f.csv.gz')
    got = f['training_numeric_representation'](raw, num)
    assert list(got.columns) == list(raw.columns) and got['target_date'].tolist() == dates and got['province'].eq('P1').all()
    for c in num:
        assert got[c].dtype == np.float64 and np.array_equal(got[c].to_numpy(), want[c], equal_nan=True), c
    # the boundary is real for the accepted 10 date features: without the contract some cyclical values differ (by 1 ulp) from training
    changed = {c: int((raw[c].to_numpy(float) != want[c]).sum()) for c in ('doy_sin', 'doy_cos')}
    assert sum(changed.values()) > 0, changed
    assert max(np.abs(raw[c].to_numpy(float) - want[c]).max() for c in ('doy_sin', 'doy_cos')) < 1e-15
    # deterministic, idempotent and batch independent (each value written/parsed on its own; future dates behave the same)
    again = f['training_numeric_representation'](got, num)
    assert all(np.array_equal(again[c].to_numpy(), got[c].to_numpy(), equal_nan=True) for c in num)
    for i in (0, 59, 1154, len(raw) - 1):
        one = f['training_numeric_representation'](raw.iloc[[i]].reset_index(drop=True), num)
        assert all(np.array_equal(one[c].to_numpy(), got[c].to_numpy()[[i]], equal_nan=True) for c in num)
    rev = f['training_numeric_representation'](raw.iloc[::-1].reset_index(drop=True), num)
    assert all(np.array_equal(rev[c].to_numpy()[::-1], got[c].to_numpy(), equal_nan=True) for c in num)
    with pytest.raises(ValueError):
        f['training_numeric_representation'](raw.assign(wx_x=np.inf), num)
    with pytest.raises(ValueError):
        f['training_numeric_representation'](raw.assign(wx_x='abc'), num)
    with pytest.raises(ValueError):
        f['training_numeric_representation'](raw, num + ['absent'])


def test_builder_output_is_in_training_numeric_representation(f, reg, tmp_path):
    cells = [dict(province_key=p, target_date=d) for p in ('P1', 'P2') for d in pd.date_range('2025-01-01', '2025-12-31').strftime('%Y-%m-%d')]
    raw = f['build_raw_feature_frame'](reg, cells, 'daily')
    fr = f['build_feature_frame'](reg, cells, 'daily')
    num = [x['name'] for x in FCFG['features'] if 'daily' in x['panels'] and x['name'] != 'province']
    want = accepted_10_to_11_boundary(reg['fn10'], raw[['province_key', 'target_date', 'province'] + num], num, ['province_key', 'target_date', 'province'],
                                      tmp_path / 'b.csv.gz')
    for c in num:
        assert fr[c].dtype == np.float64 and np.array_equal(fr[c].to_numpy(), want[c], equal_nan=True), c
        assert np.array_equal(np.isnan(fr[c].to_numpy()), np.isnan(raw[c].to_numpy(float))), c
    assert fr[['province_key', 'target_date', 'province', 'bank_calendar_coverage']].equals(raw[['province_key', 'target_date', 'province', 'bank_calendar_coverage']])
    assert (fr['doy_sin'].to_numpy() != raw['doy_sin'].to_numpy(float)).any() or (fr['doy_cos'].to_numpy() != raw['doy_cos'].to_numpy(float)).any()
    X = f['model_matrix'](fr, reg['units']['daily'])
    assert list(X.columns) == reg['units']['daily']['feature_columns'] and X['province'].dtype == object


# ---------- model matrix, prediction, response ----------
def test_model_matrix_exact_order_and_types(f):
    e = {'feature_columns': ['province', 'time_block', 'x'], 'categorical': ['province', 'time_block']}
    fr = pd.DataFrame({'x': [1.0, np.nan], 'junk': [9, 9], 'time_block': ['00-06', '18-24'], 'province': ['P2', 'P1']})
    X = f['model_matrix'](fr, e)
    assert list(X.columns) == ['province', 'time_block', 'x'] and X['province'].dtype == object and np.isnan(X['x'].iloc[1])
    with pytest.raises(ValueError):
        f['model_matrix'](fr.assign(x=[np.inf, 1.0]), e)


def test_predict_batch_order_baseline_limitations(f, reg):
    req = [B, D, dict(D, province_key='P2', target_date='2027-01-01'), dict(B, time_block='00-06')]
    out = f['predict_batch'](reg, req)
    r = out['results']
    assert [x['index'] for x in r] == [0, 1, 2, 3] and [x['unit'] for x in r] == ['6h', 'daily', 'daily', '6h']
    assert r[0]['prediction']['expected_recorded_count'] == 0.75 and r[3]['prediction']['expected_recorded_count'] == 0.5
    assert math.isclose(r[2]['prediction']['expected_recorded_count'], 0.6)                       # traffic NaN branch of the fake model
    assert r[1]['baseline_comparator']['expected_recorded_count'] == 2.0 and r[2]['baseline_comparator']['expected_recorded_count'] == 1.0   # 6/3 and global
    assert r[1]['cell'] == {'issue_time_local': '2024-04-30T18:00:00+07:00', 'target_start_local': '2024-05-01T00:00:00+07:00',
                            'target_end_local': '2024-05-02T00:00:00+07:00', 'timezone': 'Asia/Bangkok', 'utc_offset': '+07:00'}
    assert r[0]['cell']['target_start_local'] == '2024-05-01T18:00:00+07:00' and r[0]['cell']['target_end_local'] == '2024-05-02T00:00:00+07:00'
    assert 'within_evaluated_period_previously_seen_diagnostic' in r[1]['limitations'] and 'stale_model' not in r[1]['limitations']
    assert {'out_of_evaluated_period', 'stale_model', 'traffic_covariates_missing', 'bank_calendar_unknown', 'weather_covariates_missing'} <= set(r[2]['limitations'])
    assert r[2]['model_age']['days_from_training_cutoff_to_target'] == (dt.date(2027, 1, 1) - dt.date(2023, 12, 31)).days
    assert out['production_ready'] is False and all(x['research_status']['operational_status'] == 'BLOCKED' for x in r)
    json.dumps(out, allow_nan=False)


def test_first_use_predict_batch_single_unit_and_mixed(f, reg):
    """Regression 008a: the unit-selection comprehension read the outer loop variable before it was bound (NameError on the first call)."""
    q = 'expected_recorded_count'
    only_b = f['predict_batch'](reg, [B, dict(B, time_block='00-06')])['results']     # first call on a fresh registry, 6h only
    assert [x['unit'] for x in only_b] == ['6h', '6h'] and reg['units']['daily']['pipeline'].seen == []
    only_d = f['predict_batch'](reg, [D, dict(D, province_key='P2')])['results']
    assert [x['unit'] for x in only_d] == ['daily', 'daily'] and len(reg['units']['6h']['pipeline'].seen) == 1
    mixed = f['predict_batch'](reg, [B, D, dict(B, time_block='00-06'), dict(D, province_key='P2')])['results']
    assert [x['index'] for x in mixed] == [0, 1, 2, 3] and [x['unit'] for x in mixed] == ['6h', 'daily', '6h', 'daily']
    assert [(x['province_key'], x['time_block']) for x in mixed] == [('P1', '18-24'), ('P1', None), ('P1', '00-06'), ('P2', None)]
    for m, s in zip(mixed, [only_b[0], only_d[0], only_b[1], only_d[1]]):
        assert m['prediction'][q] == s['prediction'][q] and m['baseline_comparator'][q] == s['baseline_comparator'][q]


def test_batch_permutation_invariant_and_no_outcome_input(f, reg):
    req = [dict(D, province_key=p, target_date=d) for p in ('P1', 'P2') for d in ('2024-05-01', '2026-03-03', '2024-02-29')]
    a = [x['prediction']['expected_recorded_count'] for x in f['predict_batch'](reg, req)['results']]
    perm = [5, 0, 3, 1, 4, 2]
    b = [x['prediction']['expected_recorded_count'] for x in f['predict_batch'](reg, [req[i] for i in perm])['results']]
    assert [a[i] for i in perm] == b
    seen = reg['units']['daily']['pipeline'].seen[-1]
    assert list(seen.columns) == reg['units']['daily']['feature_columns'] and not any('eligib' in c or 'y_recorded' in c for c in seen.columns)


def test_nonfinite_or_negative_prediction_is_an_error_not_a_fallback(f, reg):
    for bad in (np.nan, -0.1, np.inf):
        reg['units']['daily']['pipeline'] = FakePipe(out=bad)
        with pytest.raises(ValueError):
            f['predict_batch'](reg, [D])


def test_registry_without_models_refuses(f, reg):
    reg['models_loaded'] = False
    with pytest.raises(f['DependencyError']):
        f['predict_batch'](reg, [D])


# ---------- trust: tampering is rejected BEFORE deserialization ----------
def test_tampered_bundle_rejected_before_load(f, tmp_path):
    p = tmp_path / 'm.joblib'
    p.write_bytes(b'abc')
    calls = []
    loader = lambda q: calls.append(q) or 'loaded'
    good = f['sha256_file'](p)
    assert f['verified_joblib_load'](p, good, 'b', tmp_path, loader) == 'loaded' and len(calls) == 1
    p.write_bytes(b'abd')
    with pytest.raises(f['DependencyError']):
        f['verified_joblib_load'](p, good, 'b', tmp_path, loader)
    with pytest.raises(f['DependencyError']):
        f['verified_joblib_load'](tmp_path / 'absent.joblib', good, 'b', tmp_path, loader)
    with pytest.raises(f['DependencyError']):
        f['verified_joblib_load'](p, f['sha256_file'](p), 'b', tmp_path / 'other_root', loader)
    assert len(calls) == 1


def test_pinned_functions_hash_and_scope(f, tmp_path):
    cells = ['# FUNCTIONS a\ndef g():\n    return 7', 'raise RuntimeError("report cell must never run")']
    nb = {'cells': [{'cell_type': 'code', 'id': f'c{i}', 'metadata': {}, 'source': s, 'outputs': [], 'execution_count': None} for i, s in enumerate(cells)],
          'metadata': {}, 'nbformat': 4, 'nbformat_minor': 5}
    p = tmp_path / 'x.ipynb'
    p.write_text(json.dumps(nb), 'utf-8')
    sha = f['sha256_bytes'](cells[0].encode())
    ns = f['exec_pinned_functions'](p, sha, 'x', ('g',))
    assert ns['g']() == 7
    with pytest.raises(f['DependencyError']):
        f['exec_pinned_functions'](p, '0' * 64, 'x')
    with pytest.raises(f['DependencyError']):
        f['exec_pinned_functions'](p, sha, 'x', ('missing_fn',))


def test_version_policy(f):
    import sklearn, joblib, sys
    rec = {'python': sys.version.split()[0], 'numpy': np.__version__, 'pandas': pd.__version__, 'scikit-learn': sklearn.__version__, 'joblib': joblib.__version__}
    assert f['check_versions'](rec, CFG['version_policy'])['scikit-learn'] == sklearn.__version__
    with pytest.raises(f['DependencyError']):
        f['check_versions'](dict(rec, **{'scikit-learn': '0.0.1'}), CFG['version_policy'])


def test_root_override_whitelist(f):
    with pytest.raises(ValueError):
        f['resolve_roots'](BACKEND, CFG, {'anything': '/tmp'})


# ---------- runner ----------
def test_runner_serve_check_explicit_only(runner, tmp_path):
    assert runner.notebooks_for_stage('serve-check') == ['13_inference_robustness_contract']
    assert '13_inference_robustness_contract' not in runner.notebooks_for_stage('all')
    assert runner.run_log_path(tmp_path, 'serve-check') == tmp_path / 'reports' / 'v2' / 'run_manifest_serving.json'
    r = runner.resolve_roots(output_dir=tmp_path / 'out', stage='serve-check')
    assert r['serving_reports'] == (tmp_path / 'out' / 'reports' / 'v2' / 'serving').resolve()
    assert not runner._inside(runner.run_log_path(r['output'], 'serve-check'), r['serving_reports'])
    env = runner.build_env(r, base={})
    assert env['ROADAWARE_V2_SERVING_DATA_ROOT'] == str(r['serving_data']) and env['ROADAWARE_V2_ANALYSIS_REPORT_DIR'] == str(r['analysis_dir'])


def test_runner_rejects_overlap_and_preserves_outputs(runner, tmp_path):
    with pytest.raises(ValueError):
        runner.resolve_roots(output_dir=BACKEND, stage='serve-check', analysis_dir=BACKEND / 'reports' / 'v2' / 'serving')
    with pytest.raises(ValueError):
        runner.resolve_roots(output_dir=tmp_path, stage='serve-check', model_data_dir=tmp_path / 'data' / 'v2' / 'serving' / 'm')
    out = tmp_path / 'o'
    r = runner.resolve_roots(output_dir=out, stage='serve-check', model_dir=tmp_path / 'm' / 'reports' / 'v2' / 'models', analysis_dir=tmp_path / 'a')
    assert 'not found' in runner.serve_preconditions(r)
    (tmp_path / 'm' / 'reports' / 'v2' / 'models').mkdir(parents=True)
    (tmp_path / 'm' / 'reports' / 'v2' / 'models' / 'model_manifest.json').write_text('{}')
    (tmp_path / 'a').mkdir()
    (tmp_path / 'a' / 'analysis_manifest.json').write_text('{}')
    assert runner.serve_preconditions(r) is None
    r['serving_reports'].mkdir(parents=True)
    (r['serving_reports'] / 'serving_manifest.json').write_text('{}')
    assert 'already exist' in runner.serve_preconditions(r)


# ---------- integration with the real accepted artifacts (skipped when absent) ----------
@pytest.fixture(scope='module')
def real(f):
    if not REAL:
        pytest.skip('accepted V2 model artifacts are not present under backend/ (gitignored data)')
    return f['load_registry'](BACKEND)


def test_real_public_load_registry_without_models(f):
    """Exactly the call that failed in the 008 preflight (AttributeError on the pinned 10 dict): public function, no patching."""
    if not REAL:
        pytest.skip('accepted V2 model artifacts are not present under backend/ (gitignored data)')
    reg = f['load_registry'](backend=BACKEND, load_models=False)
    assert type(reg['fn10']) is dict and type(reg['fn11']) is dict and reg['models_loaded'] is False
    assert all(callable(reg['fn10'][n]) for n in f['FN10_USED']) and all(callable(reg['fn11'][n]) for n in f['FN11_USED'])
    assert len(reg['provinces']) == FCFG['panel']['expected_provinces'] and 'pipeline' not in reg['units']['daily']
    with pytest.raises(f['DependencyError']):
        f['predict_batch'](reg, [{'province_key': reg['provinces'][0], 'target_date': '2024-05-01', 'unit': 'daily'}])


def test_real_predict_batch_matches_saved_11_daily_6h_mixed(f, real):
    """Public predict_batch on hash-verified saved 11 diagnostic cells (incl. leap day): daily only, 6h only, interleaved mixed (6h first)."""
    q, it, tol = 'expected_recorded_count', real['model_manifest']['next_stage_interface'], float(CFG['evaluation']['reload_parity_max_abs_diff'])
    reqs, refs = {}, {}
    for u, keys in f['UNIT_KEYS'].items():
        d, e = it['diagnostic_predictions'][u], real['units'][u]
        p = real['roots']['model_data_dir'] / d['path']
        f['verify_file'](p, d['sha256'], f'11 diagnostic predictions {u}')
        dg = pd.read_csv(p, dtype={k: str for k in keys}, keep_default_na=False, na_values=[''])
        idx = np.unique(np.r_[np.linspace(0, len(dg) - 1, 24).round().astype(int), np.flatnonzero(dg['target_date'].eq('2024-02-29').to_numpy())[:4]])
        s = dg.iloc[idx].reset_index(drop=True)
        reqs[u] = [{k: r[k] for k in keys} | {'unit': u} for r in s.to_dict('records')]
        refs[u] = s[[e['method_id'], e['baseline_method_id']]].apply(pd.to_numeric, errors='raise').to_numpy(dtype=float)

    def check(batch, expect):
        r = f['predict_batch'](real, batch)['results']
        assert [x['index'] for x in r] == list(range(len(batch)))
        assert [(x['province_key'], x['target_date'], x['unit'], x['time_block']) for x in r] == \
               [(b['province_key'], b['target_date'], b['unit'], b.get('time_block')) for b in batch]
        got = np.array([[x['prediction'][q], x['baseline_comparator'][q]] for x in r])
        assert np.isfinite(got).all() and np.abs(got - expect).max() <= tol, np.abs(got - expect).max()

    check(reqs['daily'], refs['daily'])
    check(reqs['6h'], refs['6h'])
    order = [(u, j) for j in range(max(len(v) for v in reqs.values())) for u in ('6h', 'daily') if j < len(reqs[u])]
    check([reqs[u][j] for u, j in order], np.array([refs[u][j] for u, j in order]))


def test_real_2025_cyclical_boundary_matches_saved_10_and_11(f, real):
    """Regression 008b on the actual saved artifacts: 2025 saved-11 diagnostic rows. doy_sin/doy_cos from the request builder must be bitwise
    equal to the accepted 10 feature table, every 2025 selected + baseline prediction must match the saved 11 values, and a mixed public batch
    made of exactly the rows where the contract changed a cyclical value must match too (order kept)."""
    q, tol = 'expected_recorded_count', float(CFG['evaluation']['reload_parity_max_abs_diff'])
    it, pm = real['model_manifest']['next_stage_interface'], real['preparation_manifest']
    cats, pm_sha = list(pm['next_stage_interface']['categorical']), {o['path']: o['sha256'] for o in pm['data_outputs']}
    picked, saved = {}, {}
    for u, keys in f['UNIT_KEYS'].items():
        e, d = real['units'][u], it['diagnostic_predictions'][u]
        p = real['roots']['model_data_dir'] / d['path']
        f['verify_file'](p, d['sha256'], f'11 diagnostic predictions {u}')
        dg = pd.read_csv(p, dtype={k: str for k in keys}, keep_default_na=False, na_values=[''])
        dg = dg[dg['target_date'].str.startswith('2025-')].reset_index(drop=True)
        assert len(dg) > 0
        fp = real['roots']['preparation_data_dir'] / it['panels_and_features'][u]['features']
        f['verify_file'](fp, pm_sha[it['panels_and_features'][u]['features']], f'10 {u} features')
        ref = dg[keys].merge(f['load_feature_rows'](fp, keys, ['doy_sin', 'doy_cos'], cats)[keys + ['doy_sin', 'doy_cos']], on=keys, how='left',
                             validate='one_to_one')
        cells = dg[keys].to_dict('records')
        raw, built = f['build_raw_feature_frame'](real, cells, u), f['build_feature_frame'](real, cells, u)
        assert built[keys].astype(str).equals(dg[keys].astype(str))
        hit = np.zeros(len(dg), dtype=bool)
        for c in ('doy_sin', 'doy_cos'):
            assert np.array_equal(built[c].to_numpy(), ref[c].to_numpy(float)), f'{u} {c} not bitwise equal to the saved 10 features'
            hit |= raw[c].to_numpy(float) != built[c].to_numpy()
        assert hit.any(), f'{u}: no 2025 row crosses the 10 -> 11 text boundary (regression would go undetected)'
        mu, b = f['predict_frame'](real, built, u)
        for m, got in ((e['method_id'], mu), (e['baseline_method_id'], b)):
            want = pd.to_numeric(dg[m], errors='raise').to_numpy(float)
            assert np.abs(got - want).max() <= tol, (u, m, float(np.abs(got - want).max()))
        idx = np.flatnonzero(hit)[np.linspace(0, hit.sum() - 1, min(40, int(hit.sum()))).round().astype(int)]
        s = dg.iloc[np.unique(idx)].reset_index(drop=True)
        picked[u] = [{k: r[k] for k in keys} | {'unit': u} for r in s.to_dict('records')]
        saved[u] = s[[e['method_id'], e['baseline_method_id']]].apply(pd.to_numeric, errors='raise').to_numpy(dtype=float)
    order = [(u, j) for j in range(max(len(v) for v in picked.values())) for u in ('6h', 'daily') if j < len(picked[u])]
    batch = [picked[u][j] for u, j in order]
    assert len(batch) <= CFG['request']['max_batch']
    r = f['predict_batch'](real, batch)['results']
    assert [(x['index'], x['province_key'], x['target_date'], x['unit'], x['time_block']) for x in r] == \
           [(i, b['province_key'], b['target_date'], b['unit'], b.get('time_block')) for i, b in enumerate(batch)]
    got = np.array([[x['prediction'][q], x['baseline_comparator'][q]] for x in r])
    assert np.abs(got - np.array([saved[u][j] for u, j in order])).max() <= tol


def test_real_registry_selected_methods(real):
    assert {u: e['method_id'] for u, e in real['units'].items()} == {'daily': 'hgb_poisson__full', '6h': 'hgb_poisson__calendar_traffic'}
    assert real['units']['6h']['feature_columns'][:2] == ['province', 'time_block']


def test_real_predictions_finite_fractional_missing_inputs(f, real):
    req = [{'province_key': 'กรุงเทพมหานคร', 'target_date': '2024-02-29', 'unit': 'daily'},
           {'province_key': 'พระนครศรีอยุธยา', 'target_date': '2029-12-31', 'unit': '6h', 'time_block': '00-06'}]
    r = f['predict_batch'](real, req)['results']
    for x in r:
        v = x['prediction']['expected_recorded_count']
        assert isinstance(v, float) and math.isfinite(v) and v >= 0
    assert r[1]['province_key'] == 'อยุธยา' and 'out_of_evaluated_period' in r[1]['limitations']
    assert r[0]['source_coverage']['weather_values_available'] is False      # no 2024/25 weather archive: NaN handled natively


def test_real_missing_bundle_rejected_before_load(f, real, tmp_path):
    calls = []
    with pytest.raises(f['DependencyError']):
        f['load_registry'](BACKEND, roots={'model_data_dir': str(tmp_path)}, loader=lambda p: calls.append(p))
    shutil.copytree(BACKEND / 'data' / 'v2' / 'models' / 'bundles', tmp_path / 'bundles')
    p = tmp_path / 'bundles' / 'daily' / 'hgb_poisson__full.joblib'
    b = bytearray(p.read_bytes())
    b[-1] ^= 0xFF
    p.write_bytes(bytes(b))
    with pytest.raises(f['DependencyError']):
        f['load_registry'](BACKEND, roots={'model_data_dir': str(tmp_path)}, loader=lambda q: calls.append(q))
    assert calls == []
