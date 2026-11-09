"""Fixture tests for the RoadAware data notebooks (no original dataset, no Jupyter kernel needed).

Each test executes the notebook's own '# FUNCTIONS' code cell, so the logic under test is exactly what the
notebooks run. Run from the repository root:
    .venv/bin/python -m pytest backend/tests -q
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

BACKEND = Path(__file__).resolve().parents[1]
NB_DIR = BACKEND / 'notebooks'
CFG = json.loads((BACKEND / 'config' / 'data_pipeline.json').read_text('utf-8'))


def load_functions(*names):
    """exec the single '# FUNCTIONS' code cell of each notebook into one namespace."""
    ns = {}
    for name in names:
        nb = json.loads((NB_DIR / (name + '.ipynb')).read_text('utf-8'))
        srcs = [''.join(c['source']) if isinstance(c['source'], list) else c['source']
                for c in nb['cells'] if c['cell_type'] == 'code']
        hits = [s for s in srcs if s.lstrip().startswith('# FUNCTIONS')]
        assert len(hits) == 1, name + ': expected exactly one FUNCTIONS cell'
        exec(compile(hits[0], name + ':FUNCTIONS', 'exec'), ns)
    return ns


@pytest.fixture(scope='module')
def f01():
    return load_functions('01_data_collection')


@pytest.fixture(scope='module')
def f02():
    return load_functions('02_eda')


@pytest.fixture(scope='module')
def f03():
    return load_functions('03_cleaning_preparation')


@pytest.fixture(scope='module')
def f045():
    return load_functions('04_split_strategy', '05_data_leakage')


# ---------------------------------------------------------------- 01 snapshot / provenance

def test_snapshot_import_is_idempotent_and_refuses_mismatch(f01, tmp_path):
    src = tmp_path / 'src.csv'
    src.write_bytes(b'a,b\n1,2\n')
    dst = tmp_path / 'snap.csv'
    assert f01['import_snapshot'](src, dst)[0] == 'copied_hash_match'
    assert f01['import_snapshot'](src, dst)[0] == 'already_present_hash_match'
    dst.write_bytes(b'a,b\n1,3\n')  # locally altered snapshot
    with pytest.raises(RuntimeError, match='refusing'):
        f01['import_snapshot'](src, dst)
    assert dst.read_bytes() == b'a,b\n1,3\n', 'mismatched snapshot must not be overwritten'


def test_prior_manifest_hash_change_is_rejected(f01):
    prior = {'files': [{'file': 'x.csv', 'sha256': 'aaa'}]}
    assert f01['check_prior_manifest'](prior, {'x.csv': 'aaa'}) == ['x.csv']
    with pytest.raises(RuntimeError, match='x.csv'):
        f01['check_prior_manifest'](prior, {'x.csv': 'bbb'})


def test_csv_record_count_handles_multiline_fields(f01, tmp_path):
    p = tmp_path / 'm.csv'
    p.write_text('a,b\n1,"line1\nline2"\n2,x\n', 'utf-8')
    assert f01['count_csv_records'](p, 'utf-8') == 2


def test_hash_audit_detects_altered_and_missing_files(f045, tmp_path):
    p = tmp_path / 'data.csv'
    p.write_bytes(b'abc')
    entry = {'path': 'data.csv', 'sha256': f045['hashlib'].sha256(b'abc').hexdigest()}
    assert f045['audit_hashes'](tmp_path, [entry]) == []
    p.write_bytes(b'abd')
    assert f045['audit_hashes'](tmp_path, [entry]) == ['sha256 mismatch data.csv']
    p.unlink()
    assert f045['audit_hashes'](tmp_path, [entry]) == ['missing data.csv']


# ---------------------------------------------------------------- 02 descriptive classifiers

def test_eda_confirmed_hour_rejects_invalid_minutes_and_24h(f02):
    s = pd.Series(['23:59', '12:99', '24:00', '7:05:61', '0.5', 'nan', 'inf', '', '0.99999999'])
    h = f02['confirmed_hour'](s)
    assert h.iloc[0] == 23 and h.iloc[4] == 12
    assert h.iloc[[1, 2, 3, 5, 6, 7, 8]].isna().all()


def test_eda_confirmed_month_requires_a_real_calendar_date(f02):
    s = pd.Series(['13/03/2021', '03/13/2021', '05/05/2021', '05/03/2021', '31/02/2021', '44197', '30/02/2564'])
    m = f02['confirmed_month'](s)
    assert m.iloc[0] == 3 and m.iloc[1] == 3 and m.iloc[2] == 5 and m.iloc[5] == 1
    assert pd.isna(m.iloc[3]), 'ambiguous slash date must not get a month'
    assert pd.isna(m.iloc[4]) and pd.isna(m.iloc[6]), 'impossible dates must not be counted as confirmed'


# ---------------------------------------------------------------- 03 parsers

@pytest.mark.parametrize('raw,expected', [
    ('nan', (None, 'invalid')), ('NaN', (None, 'invalid')), ('inf', (None, 'invalid')), ('-inf', (None, 'invalid')),
    ('24:00', (None, 'invalid')), ('12:99', (None, 'invalid')), ('12:30:60', (None, 'invalid')),
    ('', (None, 'missing')), ('  ', (None, 'missing')),
    ('7:05', (7 * 3600 + 300, 'ok')), ('23:59:59', (86399, 'ok')), ('0.5', (43200, 'ok')), ('0', (0, 'ok')),
    ('0.999999', (None, 'invalid')),  # rounds to next midnight -> would change the event date
    ('1.5', (None, 'invalid')), ('-0.1', (None, 'invalid')), ('abc', (None, 'invalid')),
])
def test_parse_time(f03, raw, expected):
    assert f03['parse_time'](raw) == expected


def test_parse_time_near_midnight_keeps_same_day(f03):
    sec, st = f03['parse_time']('0.99998')  # 86398.27 s -> 86398
    assert st == 'ok' and sec == 86398


def test_parse_date_ambiguous_slash_is_quarantined_with_both_candidates(f03):
    d, rule, status, cands = f03['parse_date']('05/03/2021', 2021)
    assert d is None and status == 'ambiguous' and rule == 'slash_dmy_vs_mdy'
    assert cands == ('2021-03-05', '2021-05-03')


@pytest.mark.parametrize('raw,year,iso,status', [
    ('13/03/2021', 2021, '2021-03-13', 'ok'),
    ('03/13/2021', 2021, '2021-03-13', 'ok'),
    ('04/04/2021', 2021, '2021-04-04', 'ok'),
    ('13/03/2564', 2021, '2021-03-13', 'ok'),       # Buddhist era
    ('44197', 2021, '2021-01-01', 'ok'),            # Excel serial, origin 1899-12-30
    ('2021-06-30', 2021, '2021-06-30', 'ok'),
    ('13/03/2020', 2021, None, 'year_mismatch'),
    ('31/02/2021', 2021, None, 'invalid'),
    ('2021-02-30', 2021, None, 'invalid'),
    ('12345', 2021, None, 'invalid'),
    ('yesterday', 2021, None, 'invalid'),
    ('', 2021, None, 'missing'),
])
def test_parse_date_rules(f03, raw, year, iso, status):
    d, _, st, _ = f03['parse_date'](raw, year)
    assert st == status
    assert (d.isoformat() if d else None) == iso


def test_coord_status_bbox_and_nonfinite(f03):
    lat = pd.Series(['13.7', 'nan', '50', '', 'inf'])
    lon = pd.Series(['100.5', '100', '100', '100', '100'])
    _, _, st = f03['coord_status'](lat, lon, CFG['thailand_bbox'])
    assert list(st) == ['ok', 'missing_or_nonfinite', 'outside_broad_bbox', 'missing_or_nonfinite', 'missing_or_nonfinite']


def test_schema_validation_fails_before_mapping(f03):
    al = CFG['schema_aliases']
    req = CFG['required_fields']
    full = [v[0] for v in al.values()]
    assert f03['validate_schema'](full, al, req, False, 'ok.csv')
    no_id = [c for c in full if c != 'ACC_CODE']
    assert f03['validate_schema'](no_id, al, req, True, '2569.csv')
    with pytest.raises(ValueError, match='acc_code'):
        f03['validate_schema'](no_id, al, req, False, '2566.csv')
    with pytest.raises(ValueError, match='several aliases'):
        f03['validate_schema'](full + ['ก.ม.'], al, req, False, 'dup.csv')


def _events(rows):
    cols = ['source_year', 'source_row', 'acc_code', 'row_reasons', 'event_date', 'time_sec', 'lat', 'lon', 'province']
    return pd.DataFrame(rows, columns=cols)


def test_dispositions_whitespace_ids_duplicates_and_conflicts(f03):
    ok = ('2021-03-13', 3600, 13.7, 100.5, 'P1')
    ev = _events([
        (2564, 2, ' 123 ', '') + ok[:4] + ok[4:],      # exact duplicate after whitespace normalization
        (2564, 3, '123', '') + ok,
        (2565, 4, '123', '') + ok,                      # same code, different year -> separate event
        (2564, 5, 'A', '') + ok,                        # time/location conflict
        (2564, 6, 'A', '', '2021-03-13', 7200, 13.7, 100.5, 'P1'),
        (2564, 7, 'B', '') + ok,                        # other-field conflict only
        (2564, 8, 'B', '', '2021-03-13', 3600, 13.7, 100.5, 'P2'),
        (2564, 9, 'C', '') + ok,                        # identical, but one member invalid
        (2564, 10, 'C', 'time_invalid') + ok,
        (2564, 11, '', 'coord_missing_or_nonfinite') + ok,  # no ID -> diagnostic, flags kept
        (2564, 12, '  ', '') + ok,
    ])
    out = f03['assign_dispositions'](ev, ['event_date', 'time_sec', 'lat', 'lon', 'province']).set_index('source_row')
    d = out['disposition']
    assert d[2] == 'retained' and d[3] == 'collapsed' and out.loc[3, 'kept_source_row'] == 2
    assert out.loc[2, 'acc_code'] == '123'
    assert d[4] == 'retained'
    assert d[5] == d[6] == 'quarantined' and out.loc[5, 'reasons'] == 'id_conflict_time_location'
    assert d[7] == d[8] == 'quarantined' and out.loc[7, 'reasons'] == 'id_conflict_other_fields'
    assert d[9] == d[10] == 'quarantined'
    assert out.loc[9, 'reasons'] == 'id_group_member_invalid' and out.loc[10, 'reasons'] == 'time_invalid'
    assert d[11] == d[12] == 'diagnostic'
    assert out.loc[11, 'reasons'] == 'no_acc_code;coord_missing_or_nonfinite' and out.loc[12, 'reasons'] == 'no_acc_code'
    assert set(d) <= set(f03['DISPOSITIONS']) and len(out) == len(ev)


def test_undercount_flags_cover_all_candidates_and_missing_province(f03):
    rows = pd.DataFrame({
        'disposition': ['quarantined', 'diagnostic', 'retained', 'quarantined'],
        'province': ['P1', '', 'P1', 'P1'],
        'date_candidates': ['2021-03-05;2021-05-03', '2021-07-01', '2021-03-05', ''],
        'reasons': ['date_ambiguous', 'no_acc_code', '', 'date_invalid'],
    })
    f = f03['undercount_flags'](rows)
    keys = set(zip(f['province'], f['date']))
    assert keys == {('P1', '2021-03-05'), ('P1', '2021-05-03'), ('*ALL*', '2021-07-01')}
    assert int(f['n_flagged_records'].sum()) == 3


# ---------------------------------------------------------------- 04 split + 05 audits on a fixture

def _fixture(f):
    """Two provinces in Train; P3 appears only in validation; diagnostic and quarantined rows included."""
    rows = []
    def add(uid, date, prov, kind='label_candidate', cands=None):
        rows.append({'event_uid': uid, 'source_file': 'f', 'source_year': date[:4], 'source_row': str(len(rows) + 2),
                     'event_date': date, 'province': prov, 'assignment': kind, 'reasons': '',
                     'date_candidates': date if cands is None else cands})
    add('2564:1', '2021-01-01', 'P1'); add('2564:2', '2021-01-01', 'P1'); add('2564:3', '2022-05-05', 'P2')
    add('2566:4', '2023-12-31', 'P1')                      # boundary label
    add('2567:5', '2024-01-01', 'P2'); add('2567:6', '2024-03-03', 'P3')  # P3 not in Train
    add('2568:7', '2025-02-02', 'P1')
    add('diag:f:9', '2026-01-05', 'P1', 'excluded_no_acc_code_diagnostic')
    add('diag:f:10', '', '', 'excluded_no_acc_code_diagnostic', cands='')  # cannot be localized
    add('2564:8', '', 'P2', 'excluded_quarantined_in_03', cands='2021-02-03;2021-03-02')
    assign = pd.DataFrame(rows)
    flags = pd.DataFrame({'province': ['P2', 'P2', '*ALL*'], 'date': ['2021-02-03', '2021-03-02', '2024-06-01'],
                          'n_flagged_records': ['1', '1', '2'], 'flag_reasons': ['date_ambiguous', 'date_ambiguous', 'no_acc_code']})
    sp = f['split_table'](CFG)
    fc, tz = CFG['forecast'], CFG['timezone_assumption']
    assign['split'] = f['assign_split'](assign['event_date'], sp)
    scope = f['train_scope'](assign)
    first = f['first_issue_times'](sp, fc['issue_hour_local'], fc['issue_days_before_target'], tz)
    days = pd.concat([pd.Series(pd.date_range(s, e, freq='D')) for s, e in zip(sp['start'], sp['end'])], ignore_index=True)
    bm = f['boundary_mask'](f['assign_split'](days, sp), f['forecast_window'](days, fc['issue_hour_local'], fc['issue_days_before_target'], tz)['target_end'],
                            list(sp['name']), first)
    labels = list(sp.loc[sp['is_label_split'], 'name'])
    assign = f['finalize_assignments'](assign, scope, labels, set(days[bm.to_numpy()]))
    panel = f['build_panel'](assign, scope, sp, fc, tz, flags)
    return assign, panel, sp, scope, first


def test_forecast_window_issue_18h_previous_day(f045):
    w = f045['forecast_window'](pd.Series(['2024-01-01']), 18, 1, 'Asia/Bangkok').iloc[0]
    assert w['issue_time'] == pd.Timestamp('2023-12-31 18:00', tz='Asia/Bangkok')
    assert w['target_start'] == pd.Timestamp('2024-01-01 00:00', tz='Asia/Bangkok')
    assert w['target_end'] == pd.Timestamp('2024-01-02 00:00', tz='Asia/Bangkok')


def test_assign_split_never_guesses_unknown_dates(f045):
    sp = f045['split_table'](CFG)
    s = f045['assign_split'](pd.Series(['2023-12-31', '2024-01-01', '2025-12-31', '2026-03-01', '2020-05-01', '']), sp)
    assert list(s) == ['train', 'validation', 'reused_test_2025', 'diagnostic_2026', 'outside_split_ranges', 'unknown_date']


def test_split_panel_scope_boundary_flags_and_counts(f045):
    assign, panel, sp, scope, first = _fixture(f045)
    a = assign.set_index('event_uid')['assignment']
    assert scope == ['P1', 'P2']
    assert a['2567:6'] == 'excluded_province_not_in_train_scope'
    assert a['2566:4'] == 'label_counted_boundary_excluded'
    assert a['diag:f:9'] == 'excluded_no_acc_code_diagnostic' and a['diag:f:10'] == 'excluded_no_acc_code_diagnostic'
    assert 'diagnostic_2026' not in set(panel['split']) and set(panel['province']) == {'P1', 'P2'}
    cell = panel.set_index(['province', 'target_date'])
    assert cell.loc[('P1', pd.Timestamp('2021-01-01')), 'y_recorded_count'] == 2  # unique event_uid
    # 2564:1, 2564:2, 2564:3, 2566:4 (boundary row still counts), 2567:5, 2568:7; P3 and no-ID rows excluded
    assert int(panel['y_recorded_count'].sum()) == 6
    assert bool(cell.loc[('P1', pd.Timestamp('2023-12-31')), 'boundary_excluded'])
    assert not bool(cell.loc[('P1', pd.Timestamp('2023-12-30')), 'boundary_excluded'])
    assert not panel.loc[panel['boundary_excluded'], 'training_eligible'].any()
    for key in [('P2', '2021-02-03'), ('P2', '2021-03-02'), ('P1', '2024-06-01'), ('P2', '2024-06-01')]:
        r = cell.loc[(key[0], pd.Timestamp(key[1]))]
        assert bool(r['possibly_undercounted']) and not bool(r['training_eligible'])
    assert not bool(cell.loc[('P1', pd.Timestamp('2021-02-03')), 'possibly_undercounted'])
    zero = cell.loc[('P2', pd.Timestamp('2021-01-01'))]
    assert zero['y_recorded_count'] == 0 and zero['label_status'] == 'zero_selected_recorded_events' and zero['completeness'] == 'unverified'
    assert (panel['issue_time'] < panel['target_start']).all()


def test_flags_and_eligibility_never_in_allowlist(f045):
    v = f045['audit_feature_names'](CFG['feature_allowlist'], CFG)
    assert v == []
    for bad in ('possibly_undercounted', 'training_eligible', 'n_flagged_records', 'deaths', 'acc_code', 'event_uid', 'lag_1d_count', 'era5_rain'):
        assert f045['audit_feature_names']([bad], CFG), bad


ORDER = [s['name'] for s in CFG['splits']] + [CFG['diagnostic_split']['name']]


def _diag_cutoff(f):
    sp = f['split_table'](CFG)
    fc = CFG['forecast']
    first = f['first_issue_times'](sp, fc['issue_hour_local'], fc['issue_days_before_target'], CFG['timezone_assumption'])
    return {CFG['diagnostic_split']['name']: first[CFG['diagnostic_split']['name']]}


def _audits(f, panel, assign, features):
    la = f['LABEL_ASSIGNMENTS']
    return {
        'names': f['audit_feature_names'](features, CFG),
        'values': f['audit_feature_values'](panel, features),
        'flags': f['audit_flags_not_features'](panel, features),
        'time': f['audit_time_order'](panel, ORDER),
        'boundary': f['audit_label_boundary'](panel, ORDER, _diag_cutoff(f)),
        'groups': f['audit_group_disjoint'](assign, la),
        'scope': f['audit_scope'](panel, assign, la),
    }


def test_audits_pass_on_clean_fixture(f045):
    assign, panel, *_ = _fixture(f045)
    res = _audits(f045, panel, assign, list(CFG['feature_allowlist']))
    assert all(v == [] for v in res.values()), res


def test_negative_control_deaths_feature_is_rejected(f045):
    assign, panel, *_ = _fixture(f045)
    p = panel.copy()
    p['deaths'] = p['y_recorded_count']
    res = _audits(f045, p, assign, list(CFG['feature_allowlist']) + ['deaths'])
    assert any('deaths' in v for v in res['names'])
    assert any('deaths' in v and 'target_same_day' in v for v in res['values'])


def test_negative_control_future_feature_rejected_by_values_not_name(f045):
    assign, panel, *_ = _fixture(f045)
    p = panel.sort_values(['province', 'target_date']).copy()
    p['smooth_signal'] = p.groupby('province')['y_recorded_count'].shift(-1).fillna(0)
    v = f045['audit_feature_values'](p, list(CFG['feature_allowlist']) + ['smooth_signal'])
    assert v == ['smooth_signal: values match target_future_+1d']
    p['smooth_signal'] = p['day_of_year'] * 2.0  # harmless deterministic calendar transform is not flagged
    assert f045['audit_feature_values'](p, ['smooth_signal']) == []


def test_negative_control_temporal_overlap(f045):
    assign, panel, *_ = _fixture(f045)
    # a Train target date re-appearing under Validation is a real overlap
    row = panel[(panel['split'] == 'train') & (panel['target_date'] == pd.Timestamp('2022-05-05'))].head(1).assign(split='validation')
    p = pd.concat([panel, row], ignore_index=True)
    assert len(p) == len(panel) + 1
    v = f045['audit_time_order'](p, ORDER)
    assert any('train target dates reach' in x for x in v), v
    # adjacent, non-overlapping ranges are not a violation
    assert f045['audit_time_order'](panel, ORDER) == []


def test_negative_control_label_crossing_next_issue(f045):
    assign, panel, *_ = _fixture(f045)
    cut = _diag_cutoff(f045)
    assert f045['audit_label_boundary'](panel, ORDER, cut) == []
    q = panel.copy()
    m = (q['split'] == 'train') & q['boundary_excluded']
    q.loc[m, 'training_eligible'] = True
    assert int(m.sum()) == 2  # 2023-12-31 for P1 and P2
    v = f045['audit_label_boundary'](q, ORDER, cut)
    assert v == ['2 eligible train labels end after first validation issue 2023-12-31 18:00:00+07:00'], v
    # last label split vs absent diagnostic split: uses the explicit cutoff, and an unknown cutoff is not skipped
    r = panel.copy()
    r.loc[(r['split'] == 'reused_test_2025') & r['boundary_excluded'], 'training_eligible'] = True
    assert any('diagnostic_2026' in x for x in f045['audit_label_boundary'](r, ORDER, cut))
    assert any('no first-issue cutoff' in x for x in f045['audit_label_boundary'](panel, ORDER))


def test_negative_control_repeated_source_id_group(f045):
    assign, panel, *_ = _fixture(f045)
    la = f045['LABEL_ASSIGNMENTS']
    row = assign[assign['event_uid'] == '2564:3'].copy()
    row['split'], row['event_date'] = 'validation', '2024-06-01'
    v = f045['audit_group_disjoint'](pd.concat([assign, row], ignore_index=True), la)
    assert any('more than one split' in x for x in v) and any('repeated event_uid' in x for x in v)
    diag = assign[assign['event_uid'] == 'diag:f:9'].assign(assignment='label_counted')
    assert any('no-ID' in x for x in f045['audit_group_disjoint'](pd.concat([assign, diag], ignore_index=True), la))


def test_negative_control_scope_and_flag_feature(f045):
    assign, panel, *_ = _fixture(f045)
    extra = panel[panel['split'] == 'validation'].head(2).assign(province='P3')
    assert f045['audit_scope'](pd.concat([panel, extra], ignore_index=True), assign, f045['LABEL_ASSIGNMENTS'])
    p = panel.copy()
    p.loc[p['possibly_undercounted'], 'training_eligible'] = True
    assert f045['audit_flags_not_features'](p, [])
    assert f045['audit_flags_not_features'](panel, ['possibly_undercounted'])


def test_enforce_and_negative_control_wrapper(f045):
    with pytest.raises(f045['LeakageAuditError']):
        f045['enforce']('x', ['boom'])
    assert f045['enforce']('x', []) is True
    caught = f045['negative_control']('c', lambda: f045['enforce']('x', ['boom']))
    missed = f045['negative_control']('c', lambda: f045['enforce']('x', []))
    assert caught['caught'] and not missed['caught']


def test_feature_matrix_allows_only_allowlist(f045):
    _, panel, *_ = _fixture(f045)
    m = f045['feature_availability_matrix'](CFG, list(panel.columns))
    assert set(m.loc[m['allowed'], 'feature']) == set(CFG['feature_allowlist'])
    blocked = set(m.loc[~m['allowed'], 'feature'])
    for c in ('y_recorded_count', 'possibly_undercounted', 'training_eligible', 'deaths', 'acc_code', '(group) historical_lags'):
        assert c in blocked, c
