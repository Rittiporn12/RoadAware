"""Offline fixture tests for V2 notebook 09 (external collection / date evidence) and its runner. No network, no kernel.

Tests execute the notebook's own '# FUNCTIONS' cells (and the SETUP cell for root handling), so the logic under test is what
the notebook runs. Expected values are worked out by hand from tiny fixtures. Run from the repository root:
    .venv/bin/python -m pytest backend/tests/test_v2_notebooks.py -q
"""
import datetime as dt
import importlib.util
import io
import json
from email.message import Message
from pathlib import Path
from urllib.error import HTTPError

import numpy as np
import pandas as pd
import pytest

BACKEND = Path(__file__).resolve().parents[1]
NB09 = BACKEND / 'notebooks' / '09_external_collection_date_evidence.ipynb'
RUNNER = BACKEND / 'scripts' / 'run_v2_notebooks.py'
CFG = json.loads((BACKEND / 'config' / 'external_sources_v2.json').read_text('utf-8'))


def code_cells():
    nb = json.loads(NB09.read_text('utf-8'))
    return [''.join(c['source']) if isinstance(c['source'], list) else c['source'] for c in nb['cells'] if c['cell_type'] == 'code']


def load_functions():
    ns = {}
    for i, s in enumerate(s for s in code_cells() if s.lstrip().startswith('# FUNCTIONS')):
        exec(compile(s, f'09:FUNCTIONS[{i}]', 'exec'), ns)
    return ns


@pytest.fixture(scope='module')
def f():
    return load_functions()


NET = {'allowed_hosts': ['example.org'], 'user_agent': 't', 'timeout_seconds': 1, 'max_retries': 2, 'backoff_seconds': 2.0,
       'max_retry_after_seconds': 5, 'max_response_bytes': 100}


class Resp:
    def __init__(self, body, url, status=200):
        self.body, self.url, self.status, self.headers = body, url, status, {}

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def geturl(self):
        return self.url

    def read(self, n=-1):
        return self.body if n < 0 else self.body[:n]


def http_error(url, code, retry_after=None):
    h = Message()
    if retry_after is not None:
        h['Retry-After'] = str(retry_after)
    return HTTPError(url, code, 'err', h, io.BytesIO(b'x'))


def opener_from(seq):
    calls = []

    def op(req, timeout):
        calls.append(req.full_url)
        item = seq.pop(0)
        if isinstance(item, Exception):
            raise item
        return item
    op.calls = calls
    return op


# ---------- notebook / config structure ----------
def test_notebook_has_two_function_cells_then_setup_before_sections():
    cells = code_cells()
    heads = [c.lstrip().split('\n', 1)[0] for c in cells]
    assert sum(h.startswith('# FUNCTIONS') for h in heads) == 2
    assert heads[0].startswith('# FUNCTIONS') and heads[1].startswith('# FUNCTIONS') and heads[2].startswith('# SETUP')
    for tag in ('# A.', '# B.', '# C.', '# D.', '# E.', '# F.', '# G.', '# Final checks'):
        assert sum(h.startswith(tag) for h in heads) == 1, tag
    for i, c in enumerate(cells):
        compile(c, f'09:cell{i}', 'exec')


def test_config_probe_url_hosts_and_reviewed_calendar(f):
    assert 'latitude=13.75' in CFG['preflight_files']['weather_probe']['url']
    assert 'latitude=14.0' not in json.dumps(CFG)
    assert not any('scene7' in h for h in CFG['http']['allowed_hosts'])
    ents = f['calendar_entries'](CFG['calendar'])
    by_src = pd.DataFrame(ents).groupby('source_id').size().to_dict()
    assert by_src['bot_holidays_2021_png'] == 20 and by_src['bot_holidays_2022_pdf'] == 17
    assert by_src['bot_holidays_2023_pdf'] == 15 and by_src['bot_holidays_2024_pdf'] == 18 and by_src['bot_holidays_2025_pdf'] == 17
    am = [e for e in ents if e['source_id'] == 'bot_yearend_amendment_2023_pdf']
    assert {(e['date'], e['action']) for e in am} == {('2024-01-02', 'remove'), ('2023-12-29', 'add')}
    assert all(e['known_from'] == '2023-11-13' for e in am)
    assert all(e['known_from'] == '2021-01-06' for e in ents if e['source_id'] == 'bot_holidays_2021_png')
    assert CFG['weather']['max_requests_per_run'] <= CFG['http']['max_network_requests_per_run'] == 500


# ---------- network: retries, 429, budget, allowlist, size cap ----------
def test_http_get_retries_5xx_then_succeeds(f):
    sleeps = []
    op = opener_from([http_error('https://example.org/a', 503), Resp(b'ok', 'https://example.org/a')])
    r = f['http_get']('https://example.org/a', NET, f['RequestBudget'](10), opener=op, sleep=sleeps.append, log=lambda *a: None)
    assert r['body'] == b'ok' and r['attempts'] == 2 and sleeps == [2.0]


def test_http_get_429_handling_and_budget(f):
    with pytest.raises(f['RateLimited']):
        f['http_get']('https://example.org/a', NET, f['RequestBudget'](10), opener=opener_from([http_error('u', 429)]), sleep=lambda s: None)
    sleeps = []
    op = opener_from([http_error('u', 429, retry_after=1), Resp(b'ok', 'https://example.org/a')])
    assert f['http_get']('https://example.org/a', NET, f['RequestBudget'](10), opener=op, sleep=sleeps.append, log=lambda *a: None)['body'] == b'ok'
    assert sleeps == [1.0]
    with pytest.raises(f['RateLimited']):  # Retry-After above the cap -> stop instead of waiting
        f['http_get']('https://example.org/a', NET, f['RequestBudget'](10), opener=opener_from([http_error('u', 429, 600)]), sleep=lambda s: None)
    parent = f['RequestBudget'](1)
    child = f['RequestBudget'](5, parent=parent)
    op = opener_from([http_error('u', 503), Resp(b'ok', 'https://example.org/a')])
    with pytest.raises(f['BudgetExhausted']):
        f['http_get']('https://example.org/a', NET, child, opener=op, sleep=lambda s: None)


def test_http_get_allowlist_and_size_cap(f):
    b = f['RequestBudget'](10)
    with pytest.raises(f['FetchError']):
        f['http_get']('https://evil.test/a', NET, b, opener=opener_from([]))
    with pytest.raises(f['FetchError']):
        f['http_get']('http://example.org/a', NET, b, opener=opener_from([]))
    with pytest.raises(f['FetchError']):
        f['http_get']('https://example.org/a', NET, b, opener=opener_from([Resp(b'x', 'https://evil.test/a')]))
    with pytest.raises(f['FetchError']):
        f['http_get']('https://example.org/a', NET, b, opener=opener_from([Resp(b'x' * 101, 'https://example.org/a')]))


def test_exact_asset_only(f):
    assets = CFG['calendar']['exact_embedded_assets']
    url = assets[0]['url']
    assert not f['host_allowed'](url, CFG['http']['allowed_hosts'])
    net = f['exact_asset_net'](CFG['http'], url, assets)
    assert f['host_allowed'](url, net['allowed_hosts'])
    with pytest.raises(f['FetchError']):
        f['exact_asset_net'](CFG['http'], 'https://s7ap1.scene7.com/is/image/bot/other?fmt=png', assets)


# ---------- hash-verified cache ----------
def test_cache_hit_mutation_new_version_and_unavailable(f, tmp_path):
    reg, b = {'resources': {}}, f['RequestBudget'](20)
    url = 'https://example.org/x.json'
    e = f['cached_fetch']('x', url, 'raw/x.json', tmp_path, reg, NET, b, opener=opener_from([Resp(b'{"a":1}', url)]))
    assert e['last_status'] == 'downloaded' and (tmp_path / 'raw/x.json').read_bytes() == b'{"a":1}'
    e = f['cached_fetch']('x', url, 'raw/x.json', tmp_path, reg, NET, b, opener=opener_from([]))  # no network call
    assert e['last_status'] == 'cache_hit_hash_verified'
    e = f['cached_fetch']('x', url, 'raw/x.json', tmp_path, reg, NET, b, offline=True)
    assert e['last_status'] == 'cache_hit_hash_verified'
    e = f['cached_fetch']('x', url, 'raw/x.json', tmp_path, reg, NET, b, refresh=True, opener=opener_from([Resp(b'{"a":2}', url)]))
    assert e['last_status'] == 'remote_bytes_changed_new_version' and e['path'] == 'raw/x.v2.json'
    assert (tmp_path / 'raw/x.json').read_bytes() == b'{"a":1}' and len(e['versions']) == 1
    (tmp_path / 'raw/x.v2.json').write_bytes(b'tampered')
    with pytest.raises(f['CacheIntegrityError']):
        f['cached_fetch']('x', url, 'raw/x.json', tmp_path, reg, NET, b, opener=opener_from([]))
    (tmp_path / 'raw/y.json').write_bytes(b'stray')
    with pytest.raises(f['CacheIntegrityError']):
        f['cached_fetch']('y', url, 'raw/y.json', tmp_path, reg, NET, b, opener=opener_from([]))
    with pytest.raises(f['FetchError']):
        f['cached_fetch']('z', url, 'raw/z.json', tmp_path, reg, NET, b, offline=True)
    u = f['try_fetch']('w', url, 'raw/w.json', tmp_path, reg, NET, b, opener=opener_from([http_error(url, 404)]), sleep=lambda s: None)
    assert u['last_status'] == 'unavailable' and u['sha256'] is None and not (tmp_path / 'raw/w.json').exists()


def test_cache_rejects_changed_url_and_mutated_preflight(f, tmp_path):
    reg, b = {'resources': {}}, f['RequestBudget'](5)
    u1, u2 = 'https://example.org/q?lat=13.75', 'https://example.org/q?lat=14.0'
    f['cached_fetch']('q', u1, 'raw/q.json', tmp_path, reg, NET, b, opener=opener_from([Resp(b'{}', u1)]))
    with pytest.raises(f['CacheIntegrityError']):  # a cached snapshot of another query is never relabelled
        f['cached_fetch']('q', u2, 'raw/q.json', tmp_path, reg, NET, b, opener=opener_from([]))
    pre = tmp_path / 'pre.pdf'
    pre.write_bytes(b'%PDF-1 reviewed')
    e = f['register_preflight']('preflight:x', 'https://example.org/x.pdf', pre, reg, 'test')
    assert e['last_status'] == 'preflight_hash_registered' and e['original_download_time'] == 'unknown'
    assert f['register_preflight']('preflight:x', 'https://example.org/x.pdf', pre, reg, 'test')['last_status'] == 'preflight_hash_verified'
    pre.write_bytes(b'%PDF-1 changed')
    with pytest.raises(f['CacheIntegrityError']):
        f['register_preflight']('preflight:x', 'https://example.org/x.pdf', pre, reg, 'test')


def _year_payload(lat=13.75, units=None, rain=None, extra=None):
    t = pd.date_range('2021-01-01 00:00', '2021-01-02 23:00', freq='h').strftime('%Y-%m-%dT%H:%M').tolist()
    h = {'time': t, 'temperature_2m_previous_day2': [25.0] * 48, 'precipitation_previous_day2': rain or [0.0] * 48}
    h.update(extra or {})
    return {'latitude': lat, 'longitude': 100.5, 'timezone': 'Asia/Bangkok', 'utc_offset_seconds': 25200, 'hourly': h,
            'hourly_units': units or {'time': 'iso8601', 'temperature_2m_previous_day2': '°C', 'precipitation_previous_day2': 'mm'}}


def test_weather_payload_validation(f):
    w = CFG['weather']
    batch = pd.DataFrame({'province_code': [10], 'lat': [13.7563], 'lon': [100.5018]})

    def check(p, start='2021-01-01', end='2021-01-02', n=batch):
        f['validate_weather_payload'](p, n, w['hourly_variables'], w['hourly_units'], start, end, [w['rain_var']], w['max_grid_distance_deg'])
    rain = [0.0] * 48
    rain[5] = None
    check(_year_payload(rain=rain))  # nulls are coverage gaps, not errors
    bad = [
        _year_payload(units={'temperature_2m_previous_day2': '°F', 'precipitation_previous_day2': 'mm'}),
        _year_payload(extra={'precipitation_previous_day20': [0.0] * 48}),
        _year_payload(rain=[-0.1] + [0.0] * 47),
        _year_payload(rain=['x'] + [0.0] * 47),
        _year_payload(lat=40.0),
    ]
    for p in bad:
        with pytest.raises(ValueError):
            check(p)
    with pytest.raises(ValueError):  # period mismatch
        check(_year_payload(), end='2021-01-03')
    with pytest.raises(ValueError):  # location count mismatch
        check([_year_payload(), _year_payload()])
    dup = _year_payload()
    dup['hourly']['time'][1] = dup['hourly']['time'][0]
    with pytest.raises(ValueError):
        check(dup)
    renamed = _year_payload()
    renamed['hourly']['precipitation_previous_day20'] = renamed['hourly'].pop('precipitation_previous_day2')
    with pytest.raises(ValueError):  # prefix lookalike never accepted as the exact variable
        check(renamed)


# ---------- date evidence ----------
def test_candidates_never_choose(f):
    c = f['csv_date_candidates']('03/04/2022', 2022)
    assert c['kind'] == 'slash' and set(c['candidates']) == {dt.date(2022, 3, 4), dt.date(2022, 4, 3)}
    assert f['csv_date_candidates']('01/13/2022', 2022)['candidates'] == (dt.date(2022, 1, 13),)
    assert f['csv_date_candidates']('44562', 2022)['candidates'] == (dt.date(2022, 1, 1),)


def _date_fixture():
    csv = pd.DataFrame({'source_row': [2, 3, 4, 5, 6, 7, 8], 'acc_code': ['A', 'B', 'C', 'D', 'D', 'E', 'F'],
                        'date_raw': ['03/04/2022', '01/13/2022', '05/06/2022', '07/08/2022', '08/07/2022', '02/02/2022', '09/10/2022']})
    x = pd.DataFrame({'acc_code': ['A', 'B', 'C', 'C', 'D', 'F'],
                      'xlsx_date': ['2022-04-03', '2022-01-13', '2022-05-06', '2022-06-05', '2022-07-08', '2022-11-11'],
                      'xlsx_kind': ['typed_datetime'] * 6})
    return csv, x


def test_audit_by_id_resolves_only_unique_agreeing_ids(f):
    csv, x = _date_fixture()
    rows, s = f['audit_dates_by_id'](csv, x, 2022)
    st = dict(zip(rows['source_row'], rows['resolution_status']))
    assert st == {2: 'resolved', 3: 'resolved', 4: 'xlsx_id_conflicting_dates', 5: 'csv_id_conflicting_dates',
                  6: 'csv_id_conflicting_dates', 7: 'id_absent_in_xlsx', 8: 'mismatch'}
    rd = dict(zip(rows['source_row'], rows['xlsx_reading']))
    assert rd[2] == 'dmy' and rd[3] == 'mdy'
    assert s['conclusion'] == 'mixed_readings_per_id_resolution_only' and s['n_ids_xlsx_only_not_added'] == 0


def test_context_check_and_both_rule_agreement(f):
    csv, x = _date_fixture()
    rows, _ = f['audit_dates_by_id'](csv, x, 2022)
    fields = [{'field': 'province', 'header': 'จังหวัด', 'kind': 'text'}, {'field': 'time', 'header': 'เวลา', 'kind': 'time'}]
    cctx = pd.DataFrame({'source_row': csv['source_row'], 'province': ['กรุงเทพมหานคร', 'ชลบุรี', '', '', '', '', ''],
                         'time': ['09:05', '10:00', '', '', '', '', '']})
    xctx = pd.DataFrame({'acc_code': ['A', 'B', 'C', 'C', 'D', 'F'], 'province': ['กรุงเทพมหานคร', 'ชลบุรี', '', '', '', ''],
                         'time': ['09:05', '11:00', '', '', '', '']})
    out, counts = f['apply_context_check'](rows, cctx, xctx, fields)
    st = dict(zip(out['source_row'], out['resolution_status']))
    assert st[2] == 'resolved' and st[3] == 'context_conflict'
    assert out.loc[out['source_row'] == 3, 'resolved_date'].isna().all() and bool(out.loc[out['source_row'] == 3, 'typed_candidate_match'].iloc[0])
    assert counts == {'not_evaluated': 5, 'agree': 1, 'conflict': 1}
    xmiss = xctx.assign(time=None)  # header absent in XLSX -> unverified, never assumed
    out2, _ = f['apply_context_check'](rows, cctx, xmiss, fields)
    assert dict(zip(out2['source_row'], out2['resolution_status']))[2] == 'context_unverified'
    r = f['candidate_rule_agreement'](csv, x, 2022)  # compared: A, B, F (C conflicting, D csv-conflicting, E absent)
    assert r['rule_compared'] == 3 and r['rule_mdy_agree'] == 1 and r['rule_dmy_agree'] == 1 and r['rule_neither'] == 1
    assert r['rule_ambiguous_compared'] == 2 and r['rule_unambiguous_agree'] == 1


def test_yearly_evidence_not_global(f):
    x21 = pd.DataFrame({'acc_code': ['A'], 'xlsx_date': ['2021-03-04'], 'xlsx_kind': ['typed_date']})
    x22 = pd.DataFrame({'acc_code': ['A'], 'xlsx_date': ['2022-04-03'], 'xlsx_kind': ['typed_date']})
    c21 = pd.DataFrame({'source_row': [2], 'acc_code': ['A'], 'date_raw': ['03/04/2021']})
    c22 = pd.DataFrame({'source_row': [2], 'acc_code': ['A'], 'date_raw': ['03/04/2022']})
    assert f['audit_dates_by_id'](c21, x21, 2021)[0]['xlsx_reading'].iloc[0] == 'mdy'
    assert f['audit_dates_by_id'](c22, x22, 2022)[0]['xlsx_reading'].iloc[0] == 'dmy'
    untyped = pd.DataFrame({'acc_code': ['A'], 'xlsx_date': [None], 'xlsx_kind': ['untyped_numeric']})
    assert f['audit_dates_by_id'](c22, untyped, 2022)[0]['resolution_status'].iloc[0] == 'xlsx_untyped_or_missing_date'


def test_norm_time(f):
    nt = f['norm_time']
    assert nt(dt.time(9, 5)) == '09:05' and nt(dt.datetime(2022, 1, 1, 23, 59)) == '23:59' and nt(0.5) == '12:00'
    assert nt('9:05') == '09:05' and nt('09.05 น.') == '09:05' and nt('25:00') == '' and nt(None) == '' and nt('') == ''


# ---------- calendar ----------
def _cal():
    return {'entry_fields': ['date', 'name', 'action', 'page'], 'sources': [
        {'id': 'base24', 'kind': 'pdf', 'role': 'annual_base', 'years': [2024], 'url': 'https://www.bot.or.th/a.pdf', 'known_from': '2023-07-26',
         'entries': [['2024-01-01', 'NewYear', 'add', 'p2'], ['2024-01-02', 'Obs', 'add', 'p2']]},
        {'id': 'amend', 'kind': 'pdf', 'role': 'amendment', 'years': [2023, 2024], 'url': 'https://www.bot.or.th/b.pdf', 'known_from': '2023-11-13',
         'entries': [['2024-01-02', 'Obs', 'remove', 'p3'], ['2023-12-29', 'Sp', 'add', 'p3']]}]}


def _records(f, cal, applied=None):
    ents = f['calendar_entries'](cal)
    return pd.DataFrame([{**e, 'applied': True if applied is None else applied.get(e['source_id'], True)} for e in ents])


def test_calendar_as_of_add_remove_end_of_day(f):
    cal = _cal()
    rec = _records(f, cal)
    asof = f['bank_holidays_as_of']
    assert asof(rec, dt.datetime(2023, 7, 26, 18)) == set()  # known_from day itself: not yet (end of day)
    assert asof(rec, dt.datetime(2023, 7, 27, 0)) == {'2024-01-01', '2024-01-02'}
    assert asof(rec, dt.datetime(2023, 11, 13, 23, 59)) == {'2024-01-01', '2024-01-02'}
    assert asof(rec, dt.datetime(2023, 11, 14, 0)) == {'2024-01-01', '2023-12-29'}
    cov = f['calendar_year_coverage']
    assert cov(rec, cal['sources'], 2024, dt.datetime(2023, 7, 1)) == 'unknown_annual_source_not_yet_known'
    assert cov(rec, cal['sources'], 2024, dt.datetime(2023, 8, 1)) == 'reviewed_annual_base_known_later_amendments_unknown'
    assert cov(rec, cal['sources'], 2023, dt.datetime(2024, 1, 1)) == 'unknown_no_applied_reviewed_annual_source'
    not_applied = _records(f, cal, {'amend': False})  # unverified amendment: original Jan2 stays, Dec29 never invented
    assert asof(not_applied, dt.datetime(2024, 1, 1)) == {'2024-01-01', '2024-01-02'}


def test_calendar_entry_validation(f):
    bad = _cal()
    bad['sources'][0]['entries'].append(['2024-01-01', 'NewYear', 'add', 'p2'])
    with pytest.raises(ValueError):
        f['calendar_entries'](bad)
    amb = _cal()
    amb['sources'][1]['known_from'] = '2023-07-26'
    amb['sources'][1]['entries'] = [['2024-01-02', 'Obs', 'remove', 'p3']]
    with pytest.raises(ValueError):
        f['calendar_entries'](amb)
    yr = _cal()
    yr['sources'][0]['entries'] = [['2025-01-01', 'X', 'add', 'p2']]
    with pytest.raises(ValueError):
        f['calendar_entries'](yr)
    act = _cal()
    act['sources'][0]['entries'] = [['2024-01-01', 'X', 'maybe', 'p2']]
    with pytest.raises(ValueError):
        f['calendar_entries'](act)


def test_review_source_status_requires_matching_bytes(f):
    rs = f['review_source_status']
    pdf = {'kind': 'pdf', 'reviewed_sha256': None}
    assert rs(pdf, 'aa', 'aa') == (True, 'live_bytes_identical_to_reviewed_copy')
    assert rs(pdf, 'aa', None) == (True, 'reviewed_copy_only_live_unavailable')
    assert rs(pdf, 'aa', 'bb') == (False, 'live_bytes_differ_from_reviewed_copy')
    assert rs(pdf, None, 'bb') == (False, 'reviewed_copy_missing')
    assert rs({'kind': 'pdf', 'reviewed_sha256': 'cc'}, 'aa', 'aa') == (False, 'reviewed_copy_hash_differs_from_config_pin')
    assert rs({'kind': 'pdf', 'reviewed_sha256': 'cc'}, None, 'cc') == (True, 'live_bytes_match_pinned_reviewed_sha256')
    assert rs({'kind': 'pdf', 'reviewed_sha256': 'cc'}, None, 'dd') == (False, 'reviewed_copy_missing')
    html = {'kind': 'html'}
    assert rs(html, None, 'h', {'2024-04-12'}, ['2024-04-12'])[0] is True
    assert rs(html, None, 'h', set(), ['2024-04-12'])[0] is False and rs(html, None, None, set(), ['2024-04-12'])[0] is False
    assert f['extract_thai_dates']('ประกาศ วันที่ ๑๒ เมษายน ๒๕๖๗', 2024)[0]['date'] == '2024-04-12'


def test_festival_rules_do_not_need_bank_membership(f):
    rec = _records(f, _cal())
    ev = f['festival_rule_evidence'](rec, CFG['calendar']['recurring_fixed_festivals'], [2024])
    ny = ev[ev['festival_id'] == 'new_year'].iloc[0]
    assert ny['rule_dates'] == '2024-12-31;2024-01-01' and ny['reviewed_bank_holiday_dates'] == '2024-01-01'
    assert ev[ev['festival_id'] == 'songkran'].iloc[0]['reviewed_bank_holiday_dates'] == ''


# ---------- weather ----------
def _payload(rain, tz='Asia/Bangkok', off=25200):
    times = [f'2021-01-0{1 + h // 24}T{h % 24:02d}:00' for h in range(48)]
    return {'latitude': 13.75, 'longitude': 100.5, 'elevation': 4.0, 'timezone': tz, 'utc_offset_seconds': off,
            'hourly': {'time': times, 'temperature_2m_previous_day2': [25.0] * 48, 'precipitation_previous_day2': rain}}


def test_weather_utc_lead_complete_hours_and_null_not_zero(f):
    batch = pd.DataFrame({'province_code': [10], 'lat': [13.7563], 'lon': [100.5018]})
    rain = [0.5] * 48
    rain[30] = None  # value valid 2021-01-02 06:00 = interval 05-06 -> the 00-06 rain block of 2021-01-02
    h = f['normalize_weather_payload'](_payload(rain), batch, ['temperature_2m_previous_day2', 'precipitation_previous_day2'],
                                       'jma_gsm', 'Asia/Bangkok', 25200, 48)
    assert h['valid_time_utc'].iloc[0] == pd.Timestamp('2020-12-31 17:00')
    assert h['nominal_issue_bound_utc'].iloc[0] == pd.Timestamp('2020-12-29 17:00')
    assert h['grid_lat'].iloc[0] == 13.75 and h['requested_lat'].iloc[0] == pytest.approx(13.7563)
    kw = dict(temp_col='temperature_2m_previous_day2', rain_col='precipitation_previous_day2', buffer_hours=6, issue_hour_local=18,
              utc_offset_seconds=25200)
    d = f['aggregate_weather'](h, 24, **kw).set_index('date')
    assert d.loc['2021-01-01', 'rain_sum'] == pytest.approx(12.0) and not d.loc['2021-01-01', 'rain_missing']  # values 01:00..01-02 00:00
    assert np.isnan(d.loc['2021-01-02', 'rain_sum']) and d.loc['2021-01-02', 'rain_missing']  # null hour + no next-midnight value
    assert d.loc['2021-01-02', 'temp_mean'] == pytest.approx(25.0) and not d.loc['2021-01-02', 'temp_missing']
    assert d['issue_bound_ok'].all()  # latest bound (rain interval end D+1 00:00) - 48 h + 6 h <= D-1 18:00
    b6 = f['aggregate_weather'](h, 6, **kw)
    assert len(b6) == 8 and list(b6['time_block'][:4]) == ['00-06', '06-12', '12-18', '18-24']  # temperature grid keys only
    miss = b6[(b6['date'] == pd.Timestamp('2021-01-02')) & (b6['time_block'] == '00-06')].iloc[0]
    assert np.isnan(miss['rain_sum']) and miss['n_valid_rain'] == 5
    ok = b6[(b6['date'] == pd.Timestamp('2021-01-02')) & (b6['time_block'] == '06-12')].iloc[0]
    assert ok['rain_sum'] == pytest.approx(3.0)
    allnull = f['aggregate_weather'](h.assign(precipitation_previous_day2=np.nan), 24, **kw)
    assert allnull['rain_sum'].isna().all()  # all-null is never summed to 0
    short = f['normalize_weather_payload'](_payload([0.0] * 48), batch, ['temperature_2m_previous_day2', 'precipitation_previous_day2'],
                                           'jma_gsm', 'Asia/Bangkok', 25200, 12)
    assert not f['aggregate_weather'](short, 24, **kw)['issue_bound_ok'].any()  # post-issue hours flagged
    with pytest.raises(ValueError):
        f['normalize_weather_payload'](_payload(rain, tz='GMT', off=0), batch, ['temperature_2m_previous_day2'], 'jma_gsm', 'Asia/Bangkok', 25200, 48)


def test_weather_rain_is_preceding_hour_sum(f):
    batch = pd.DataFrame({'province_code': [10], 'lat': [13.7563], 'lon': [100.5018]})
    variables = ['temperature_2m_previous_day2', 'precipitation_previous_day2']
    h = f['normalize_weather_payload'](_payload([float(i) for i in range(48)]), batch, variables, 'jma_gsm', 'Asia/Bangkok', 25200, 48)
    kw = dict(temp_col='temperature_2m_previous_day2', rain_col='precipitation_previous_day2', buffer_hours=6, issue_hour_local=18,
              utc_offset_seconds=25200)
    b6 = f['aggregate_weather'](h, 6, **kw).set_index(['date', 'time_block'])
    d1, d2 = pd.Timestamp('2021-01-01'), pd.Timestamp('2021-01-02')
    assert b6.loc[(d1, '00-06'), 'rain_sum'] == 21.0  # values valid 01..06 (1+..+6), not 00..05 (= 15)
    assert b6.loc[(d1, '18-24'), 'rain_sum'] == 129.0  # 19..23 plus next-day 00:00 (24)
    last = b6.loc[(d2, '18-24')]
    assert np.isnan(last['rain_sum']) and last['rain_missing'] and last['n_valid_rain'] == 5 and not last['temp_missing']
    assert b6.index.get_level_values('date').min() == d1  # first midnight rain (interval 2020-12-31 23-24) makes no stray bucket
    d = f['aggregate_weather'](h, 24, **kw).set_index('date')
    assert d.loc[d1, 'rain_sum'] == 300.0 and d.loc[d1, 'rain_latest_valid_time_local'] == pd.Timestamp('2021-01-02 00:00')
    assert d.loc[d1, 'latest_issue_bound_utc'] == pd.Timestamp('2020-12-30 17:00')  # from rain's interval end, not the 23:00 temperature
    assert d['issue_bound_ok'].all() and (d['rain_interval_convention'] == f['RAIN_INTERVAL_CONVENTION']).all()
    # year boundary: the 2021 chunk alone lacks the 2022-01-01 00:00 value; the concatenated adjacent chunk completes 2021-12-31
    shift = pd.Timedelta(days=364)
    y = h.assign(**{c: h[c] + shift for c in ('valid_time_local', 'valid_time_utc', 'nominal_issue_bound_utc')})
    dec, both = f['aggregate_weather'](y.iloc[:24], 24, **kw).set_index('date'), f['aggregate_weather'](y, 24, **kw).set_index('date')
    dec31 = pd.Timestamp('2021-12-31')
    assert np.isnan(dec.loc[dec31, 'rain_sum']) and dec.loc[dec31, 'rain_missing'] and len(dec) == 1
    assert both.loc[dec31, 'rain_sum'] == 300.0 and not both.loc[dec31, 'rain_missing']


def _five_location_payload():
    """5 locations x 48 h (2021-01-01..02); location 2 has ONE -0.1 mm hour (valid 03:00 = interval 02-03), location 4 one null rain
    hour (valid 10:00) and location 0 a legitimate negative temperature."""
    items = []
    for i in range(5):
        items.append(_year_payload(lat=13.0 + i, rain=[0.5] * 48))
    items[2]['hourly']['precipitation_previous_day2'][3] = -0.1
    items[4]['hourly']['precipitation_previous_day2'][10] = None
    items[0]['hourly']['temperature_2m_previous_day2'][5] = -1.0
    return items


def test_weather_negative_rain_masked_per_hour(f, tmp_path):
    import copy
    w = CFG['weather']
    assert w['negative_value_policy'] == 'mask'
    rain, temp = w['rain_var'], w['temp_var']
    batch = pd.DataFrame({'province_code': [10, 11, 12, 13, 14], 'lat': [13.0 + i for i in range(5)], 'lon': [100.5] * 5})
    payload = _five_location_payload()
    before = copy.deepcopy(payload)

    def check(p, policy, end='2021-01-02'):
        f['validate_weather_payload'](p, batch, w['hourly_variables'], w['hourly_units'], '2021-01-01', end, [rain], w['max_grid_distance_deg'],
                                      negative_policy=policy)
    with pytest.raises(ValueError):  # strict mode still rejects the batch
        check(payload, 'strict')
    with pytest.raises(ValueError):
        check(payload, 'clip')
    check(payload, 'mask')
    # structural checks stay strict under the masking policy
    bad_unit = copy.deepcopy(payload)
    bad_unit[1]['hourly_units'][rain] = 'inch'
    bad_grid = copy.deepcopy(payload)
    bad_grid[3]['hourly']['time'][7] = bad_grid[3]['hourly']['time'][6]
    for p, end in ((bad_unit, '2021-01-02'), (bad_grid, '2021-01-02'), (payload, '2021-01-03')):
        with pytest.raises(ValueError):
            check(p, 'mask', end)
    h = f['normalize_weather_payload'](payload, batch, w['hourly_variables'], 'jma_gsm', 'Asia/Bangkok', 25200, 48)
    m, flags, audit = f['apply_weather_value_policy'](h, w['hourly_variables'], [rain])
    assert payload == before  # raw payload never mutated
    assert len(m) == 240 and m[temp].notna().all() and set(m['province_code']) == {10, 11, 12, 13, 14}
    assert m.loc[m['province_code'].eq(10), temp].min() == -1.0  # temperature is not a non-negative variable: kept
    assert m[rain].isna().sum() == 2 and not (m[rain] < 0).any()
    hit = m[(m['province_code'] == 12) & (m['valid_time_local'] == pd.Timestamp('2021-01-01 03:00'))].iloc[0]
    assert np.isnan(hit[rain]) and hit[rain + '_quality'] == 'negative_value_masked' and hit[temp] == 25.0
    nul = m[(m['province_code'] == 14) & (m['valid_time_local'] == pd.Timestamp('2021-01-01 10:00'))].iloc[0]
    assert np.isnan(nul[rain]) and nul[rain + '_quality'] == 'null_in_source'  # null stays null, not a value-quality mask
    assert len(flags) == 1 and flags.iloc[0]['province_code'] == 12 and flags.iloc[0]['raw_value'] == -0.1
    a = audit.set_index(['province_code', 'variable'])
    assert a.loc[(12, rain), 'n_negative_masked'] == 1 and a.loc[(12, rain), 'min_raw'] == -0.1 and a.loc[(12, rain), 'n_valid'] == 47
    assert a.loc[(12, rain), 'quality_reason'] == 'negative_value_masked_to_nan' and a.loc[(12, temp), 'n_valid'] == 48
    assert a.loc[(14, rain), 'n_null_in_source'] == 1 and a.loc[(14, rain), 'n_negative_masked'] == 0 and a.loc[(10, rain), 'quality_reason'] == 'ok'
    kw = dict(temp_col=temp, rain_col=rain, buffer_hours=6, issue_hour_local=18, utc_offset_seconds=25200)
    d = f['aggregate_weather'](m, 24, **kw).set_index(['province_code', 'date'])
    d1 = pd.Timestamp('2021-01-01')
    assert np.isnan(d.loc[(12, d1), 'rain_sum']) and d.loc[(12, d1), 'rain_missing'] and d.loc[(12, d1), 'n_rain_value_masked'] == 1
    assert d.loc[(12, d1), 'rain_missing_reason'] == 'negative_value_masked'  # never a partial sum
    assert d.loc[(12, d1), 'temp_mean'] == 25.0 and not d.loc[(12, d1), 'temp_missing']
    assert d.loc[(14, d1), 'rain_missing_reason'] == 'null_in_source'
    for p in (10, 11, 13):
        assert d.loc[(p, d1), 'rain_sum'] == pytest.approx(12.0) and d.loc[(p, d1), 'rain_missing_reason'] == ''
    assert d.loc[(12, pd.Timestamp('2021-01-02')), 'rain_missing_reason'] == 'hours_not_returned'  # no next-midnight value
    b6 = f['aggregate_weather'](m, 6, **kw).set_index(['province_code', 'date', 'time_block'])
    assert np.isnan(b6.loc[(12, d1, '00-06'), 'rain_sum']) and b6.loc[(12, d1, '00-06'), 'n_rain_value_masked'] == 1
    assert b6.loc[(12, d1, '06-12'), 'rain_sum'] == pytest.approx(3.0) and b6.loc[(11, d1, '00-06'), 'rain_sum'] == pytest.approx(3.0)
    assert np.isnan(b6.loc[(14, d1, '06-12'), 'rain_sum']) and b6.loc[(14, d1, '12-18'), 'rain_sum'] == pytest.approx(3.0)
    # a hash-verified cached negative payload is reused offline (no network) and sanitized in memory; cached bytes unchanged
    url = 'https://example.org/weather.json'
    body = json.dumps(payload).encode('utf-8')
    reg, b, net = {'resources': {}}, f['RequestBudget'](5), dict(NET, max_response_bytes=10 ** 7)
    f['cached_fetch']('wx', url, 'raw/weather/wx.json', tmp_path, reg, net, b, opener=opener_from([Resp(body, url)]),
                      validate=f['weather_validator'](5))
    used = b.used
    e = f['cached_fetch']('wx', url, 'raw/weather/wx.json', tmp_path, reg, net, b, offline=True, validate=f['weather_validator'](5))
    assert e['last_status'] == 'cache_hit_hash_verified' and b.used == used
    cached = json.loads((tmp_path / e['path']).read_text('utf-8'))
    check(cached, 'mask')
    _, fl2, _ = f['apply_weather_value_policy'](f['normalize_weather_payload'](cached, batch, w['hourly_variables'], 'jma_gsm', 'Asia/Bangkok',
                                                                                25200, 48), w['hourly_variables'], [rain])
    assert len(fl2) == 1 and (tmp_path / e['path']).read_bytes() == body and f['sha256_file'](tmp_path / e['path']) == e['sha256']


# ---------- traffic ----------
def test_aadt_normalize_duplicates_nonnumeric_and_summary(f):
    t = CFG['traffic']
    comps = t['total_components']
    base = {'ทางหลวงหมายเลข': ['1', '1', '2'], 'ตอนควบคุม': ['0101', '0101', '0200'], 'กม.จุดสำรวจ': ['10', '10', '5'],
            'จังหวัด': ['ชลบุรี', 'ชลบุรี', ' ระยอง '], 'รวม': ['1,000', '1,000', '-'], '%ของยานยนต์หนัก': ['10', '10', '']}
    for c in comps:
        base[c] = ['100', '100', '']
    raw = pd.DataFrame(base)
    norm, rep = f['normalize_aadt'](raw, t['aliases'], t['required_fields'], comps, t['heavy_components'], 2564)
    assert rep['status'] == 'normalized' and rep['duplicate_key_rows'] == 2
    assert np.isnan(norm['total_aadt'].iloc[2])  # '-' is missing, never 0
    assert rep['total_check']['n_mismatch_gt1'] == 0 and rep['heavy_check']['n_mismatch_gt0_05pp'] == 2
    rows, aud = f['aadt_station_rows'](raw, norm, rep, {}, ['ชลบุรี', 'ระยอง'])
    assert aud['rows_duplicate_key'] == 2 and aud['rows_station'] == 1 and aud['rows_blank_nonrecord'] == 0
    s = f['aadt_province_summary'](rows, ['ชลบุรี', 'ระยอง'])
    ch = s[s['province_key'] == 'ชลบุรี'].iloc[0]
    assert ch['n_rows'] == 2 and ch['n_duplicate_key_rows'] == 2 and ch['n_station_rows'] == 0 and ch['n_valid_total'] == 0
    ry = s[s['province_key'] == 'ระยอง'].iloc[0]
    assert ry['n_valid_total'] == 0 and bool(ry['in_v1_panel']) and not any('sum' in c for c in s.columns)
    assert f['aadt_unit_flags'](['รวม', 'PCU/วัน', 'คันต่อชม.'], t['unsupported_unit_patterns']) == ['PCU/วัน', 'คันต่อชม.']


def _aadt_rows_fixture(f):
    """r0/r1 real duplicate key; r2 alias province (raw padded) with heavy share 150; r3/r4 fully blank lines; r5 blank survey point;
    r6 negative total; r7 valid with a negative class count; r8 unknown province."""
    t = CFG['traffic']
    raw = pd.DataFrame({'ทางหลวงหมายเลข': ['1', '1', '2', '', '', '3', '4', '5', '6'],
                        'ตอนควบคุม': ['0101', '0101', '0200', '', ' ', '0300', '0400', '0500', '0600'],
                        'กม.จุดสำรวจ': ['10', '10', '5', '', '', '', '7', '8', '9'],
                        'จังหวัด': ['ชลบุรี', 'ชลบุรี', ' พระนครศรีอยุธยา ', '', '', 'ชลบุรี', 'ชลบุรี', 'ชลบุรี', 'ไม่รู้'],
                        'รวม': ['1,000', '1,000', '500', '', '', '700', '-5', '300', '100'],
                        '%ของยานยนต์หนัก': ['10', '10', '150', '', '', '', '20', '5', ''],
                        t['total_components'][0]: ['1', '1', '1', '', '', '1', '1', '-3', '1']})
    norm, rep = f['normalize_aadt'](raw, t['aliases'], t['required_fields'], t['total_components'], t['heavy_components'], 2564)
    return raw, norm, rep


def test_aadt_blank_nonrecords_duplicates_incomplete_invalid_and_alias(f):
    raw, norm, rep = _aadt_rows_fixture(f)
    assert rep['status'] == 'normalized' and rep['duplicate_key_rows'] == 4  # the naive count wrongly includes the two blank lines
    aliases, panel = {'พระนครศรีอยุธยา': 'อยุธยา'}, ['ชลบุรี', 'อยุธยา']
    rows, aud = f['aadt_station_rows'](raw, norm, rep, aliases, panel)
    assert (aud['rows_parsed'], aud['rows_blank_nonrecord'], aud['rows_incomplete_identity'], aud['rows_duplicate_key'], aud['rows_station']) == (9, 2, 1, 2, 4)
    assert len(rows) == 7 and not rows['row_class'].eq('blank_nonrecord').any()
    assert rows.set_index('csv_data_row_index')['row_class'].to_dict() == {0: 'duplicate_key', 1: 'duplicate_key', 2: 'station', 5: 'incomplete_identity',
                                                                           6: 'station', 7: 'station', 8: 'station'}
    assert aud['station_valid_total_rows'] == 3 and aud['nonblank_invalid_total_value_rows'] == 1
    assert aud['nonblank_invalid_heavy_share_value_rows'] == 1 and aud['nonblank_invalid_count_value_rows'] == 1
    assert aud['province_key_status_counts'] == {'not_in_v1_panel': 1, 'v1_panel_audited_alias': 1, 'v1_panel_exact': 5}
    assert aud['province_alias_values'] == {'พระนครศรีอยุธยา': 'อยุธยา'} and aud['provinces_not_in_v1_panel'] == ['ไม่รู้']
    ay = rows[rows['csv_data_row_index'] == 2].iloc[0]
    assert ay['province_raw'] == ' พระนครศรีอยุธยา ' and ay['province_text'] == 'พระนครศรีอยุธยา' and ay['province_key'] == 'อยุธยา'
    assert not ay['heavy_share_valid'] and ay['total_valid']
    s = f['aadt_province_summary'](rows, panel).set_index('province_key')
    ch = s.loc['ชลบุรี']
    assert (ch['n_rows'], ch['n_station_rows'], ch['n_duplicate_key_rows'], ch['n_incomplete_identity_rows']) == (5, 2, 2, 1)
    assert ch['n_valid_total'] == 1 and ch['n_invalid_total_value'] == 1 and ch['mean_total_aadt'] == 300 and ch['median_total_aadt'] == 300
    assert ch['n_valid_heavy_share'] == 2 and ch['mean_heavy_share_pct'] == 12.5 and bool(ch['in_v1_panel'])
    ay = s.loc['อยุธยา']
    assert ay['mean_total_aadt'] == 500 and ay['n_valid_heavy_share'] == 0 and ay['n_invalid_heavy_share_value'] == 1
    assert ay['province_text_values'] == 'พระนครศรีอยุธยา' and ay['province_key_status'] == 'v1_panel_audited_alias' and bool(ay['in_v1_panel'])
    assert not bool(s.loc['ไม่รู้', 'in_v1_panel']) and not any('sum' in c for c in s.columns)


def test_province_keys_exact_alias_only(f):
    k = f['province_keys'](['อยุธยา', 'พระนครศรีอยุธยา', 'จ.พระนครศรีอยุธยา', '', None, ' กรุงเทพมหานคร '], {'พระนครศรีอยุธยา': 'อยุธยา'}, ['อยุธยา'])
    assert k['province_key_status'].tolist() == ['v1_panel_exact', 'v1_panel_audited_alias', 'not_in_v1_panel', 'blank', 'blank', 'not_in_v1_panel']
    assert k['province_key'].tolist()[:3] == ['อยุธยา', 'อยุธยา', 'จ.พระนครศรีอยุธยา']  # no prefix stripping or fuzzy guess
    assert k['province_raw'].tolist()[5] == ' กรุงเทพมหานคร ' and k['province_text'].tolist()[5] == 'กรุงเทพมหานคร'
    assert f['province_keys'](['x'], {}, [])['province_key_status'].tolist() == ['v1_panel_unavailable']
    alias = CFG['province_aliases']['map']
    assert alias == {'พระนครศรีอยุธยา': 'อยุธยา'}  # exactly the audited alias, nothing else


def test_deterministic_gzip_tables(f, tmp_path):
    import gzip
    df = pd.DataFrame({'a': [1, 2], 'b': ['x', 'ไทย']})
    p1, p2 = f['write_csv_gz'](tmp_path / 'one' / 't.csv.gz', df), f['write_csv_gz'](tmp_path / 'two.csv.gz', df)
    b1, b2 = p1.read_bytes(), p2.read_bytes()
    assert b1 == b2 and b1[4:8] == b'\x00\x00\x00\x00'  # header mtime 0 and no stored file name
    assert gzip.decompress(b1).decode('utf-8') == df.to_csv(index=False)
    try:
        import pyarrow  # noqa: F401
    except ImportError:
        assert Path(f['write_table'](tmp_path / 'w', df)).read_bytes() == b1


# ---------- pinned local-first geography ----------
def test_config_geography_pins():
    g = CFG['geography']
    pins = {k: v for k, v in g['pinned_sources'].items() if not k.startswith('_')}
    assert set(pins) == {'geoboundaries_api', 'geoboundaries_tha_adm1_geojson', 'thailand_provinces_json'}
    assert pins['geoboundaries_tha_adm1_geojson']['url'] == g['pinned_gj_download_url'] and pins['thailand_provinces_json']['url'] == g['province_table_url']
    assert pins['geoboundaries_api']['url'] == g['geoboundaries_api'] and not pins['geoboundaries_api']['required']
    assert pins['geoboundaries_tha_adm1_geojson']['required'] and pins['thailand_provinces_json']['required']
    assert all(len(p['expected_sha256']) == 64 and int(p['expected_sha256'], 16) >= 0 for p in pins.values())
    assert g['metadata_http']['timeout_seconds'] <= 10 and g['metadata_http']['max_retries'] <= 1


def test_pinned_source_local_first_offline_refresh_and_mismatch(f, tmp_path):
    import hashlib
    body = b'{"features": []}'
    pin = hashlib.sha256(body).hexdigest()
    url = 'https://example.org/geo.json'
    spec = {'file': 'geo.json', 'url': url, 'expected_sha256': pin, 'resource_id': 'geo_dl', 'rel': 'raw/geo.json', 'required': True}
    pre_dir, root = tmp_path / 'pre', tmp_path / 'ext'
    pre_dir.mkdir()
    (pre_dir / 'geo.json').write_bytes(body)
    reg, budget = {'resources': {}}, f['RequestBudget'](20)

    def fetcher(seq, offline=False, refresh=False, reg=reg):
        op = opener_from(seq)

        def _f(rid, u, rel, **kw):
            return f['try_fetch'](rid, u, rel, root, reg, NET, budget, opener=op, offline=offline, refresh=refresh, sleep=lambda s: None, **kw)
        _f.op = op
        return _f
    fx = fetcher([])  # any network call would fail (empty opener)
    e, path, info = f['pinned_source']('geo', spec, pre_dir, root, reg, fx)
    assert info['used'] == 'codex_preflight_registered_pin_verified' and path == pre_dir / 'geo.json' and fx.op.calls == []
    assert e['path'] is None and f['entry_file'](e, root) == pre_dir / 'geo.json'  # preflight entry: path None -> preflight_path
    assert info['original_download_time'] == 'unknown' and info['cache_mtime_utc'] and info['retrieved_at_utc'] is None
    # refresh: remote differs -> kept as registry bytes, never used, flagged for review
    fr = fetcher([Resp(b'{"features": [1]}', url)], refresh=True)
    e, path, info = f['pinned_source']('geo', spec, pre_dir, root, reg, fr, refresh=True)
    assert info['used'] == 'codex_preflight_registered_pin_verified' and info['remote_matches_pin'] is False and info['remote_checked']
    assert reg['resources']['geo_dl']['sha256'] != pin and (root / 'raw/geo.json').is_file()
    # fresh environment without preflight: download once, then offline cache hit without network
    reg2, empty = {'resources': {}}, tmp_path / 'nopre'
    root2 = tmp_path / 'ext2'

    def fetcher2(seq, offline=False):
        op = opener_from(seq)
        return lambda rid, u, rel, **kw: f['try_fetch'](rid, u, rel, root2, reg2, NET, budget, opener=op, offline=offline, sleep=lambda s: None, **kw)
    e, path, info = f['pinned_source']('geo', spec, empty, root2, reg2, fetcher2([Resp(body, url)]))
    assert info['used'] == 'notebook_download_pin_verified' and path == root2 / 'raw/geo.json' and e['provenance'] == 'downloaded_by_notebook09'
    e, path, info = f['pinned_source']('geo', spec, empty, root2, reg2, fetcher2([], offline=True))
    assert info['used'] == 'notebook_cache_pin_verified' and path.read_bytes() == body
    # offline without any copy: honest gap, no points source
    reg3, root3 = {'resources': {}}, tmp_path / 'ext3'
    f3 = lambda rid, u, rel, **kw: f['try_fetch'](rid, u, rel, root3, reg3, NET, budget, opener=opener_from([]), offline=True, **kw)  # noqa: E731
    e, path, info = f['pinned_source']('geo', spec, empty, root3, reg3, f3)
    assert e is None and path is None and 'no preflight copy' in info['error'] and reg3['resources']['geo_dl']['last_status'] == 'unavailable'
    # downloaded bytes that differ from the pin: required -> refuse (bytes preserved in the registry); optional -> gap
    reg4, root4 = {'resources': {}}, tmp_path / 'ext4'
    f4 = lambda rid, u, rel, **kw: f['try_fetch'](rid, u, rel, root4, reg4, NET, budget, opener=opener_from([Resp(b'{"x": 2}', url)]), **kw)  # noqa: E731
    with pytest.raises(f['CacheIntegrityError']):
        f['pinned_source']('geo', spec, empty, root4, reg4, f4)
    assert reg4['resources']['geo_dl']['sha256'] and (root4 / 'raw/geo.json').read_bytes() == b'{"x": 2}'
    f4c = lambda rid, u, rel, **kw: f['try_fetch'](rid, u, rel, root4, reg4, NET, budget, opener=opener_from([]), **kw)  # noqa: E731
    e, path, info = f['pinned_source']('geo', dict(spec, required=False), empty, root4, reg4, f4c)  # cached mismatch, optional
    assert e is None and 'configured pin' in info['error']
    # a preflight copy that differs from the pin is refused for a required source
    (pre_dir / 'bad.json').write_bytes(b'{"bad": 1}')
    with pytest.raises(f['CacheIntegrityError']):
        f['pinned_source']('bad', dict(spec, file='bad.json'), pre_dir, root, {'resources': {}}, fetcher([]))


def test_traffic_availability_proxy(f):
    a = f['traffic_available_from']({'created': '2022-03-01T04:00:00', 'last_modified': '2023-05-10T00:00:00.123456'}, 1)
    assert a['available_from_proxy_utc'].startswith('2023-05-11T00:00:00') and a['available_from_basis'] == 'max(created,last_modified)+1d'
    assert f['traffic_available_from']({'created': '2022-03-01T04:00:00'}, 1)['available_from_basis'] == 'created_only+1d'
    assert f['traffic_available_from']({}, 1)['available_from_proxy_utc'] is None
    use = f['traffic_vintage_usable']
    issue = '2024-03-01T11:00:00+00:00'
    assert use(2022, '2023-05-11T00:00:00+00:00', dt.date(2024, 3, 2), issue)
    assert not use(2024, '2023-05-11T00:00:00+00:00', dt.date(2024, 3, 2), issue)  # target-year annual actual
    assert not use(2023, '2024-06-01T00:00:00+00:00', dt.date(2024, 3, 2), issue)  # published after issue
    assert not use(2022, None, dt.date(2024, 3, 2), issue)


# ---------- geography ----------
def test_province_join_iso_exact_name_unresolved(f):
    prov = pd.DataFrame({'province_code': [10, 20, 45], 'name_th': ['กรุงเทพมหานคร', 'ชลบุรี', 'ร้อยเอ็ด'],
                         'name_en': ['Bangkok', 'Chon Buri', 'Roi Et']})
    shapes = pd.DataFrame({'shape_index': [0, 1, 2, 3, 4], 'shape_name': ['x', 'Chon Buri', 'Chon Buri Province', 'Roi-Et', 'y'],
                           'shape_iso': ['TH-10', None, None, 'TH-45', 'TH-45']})
    j = f['join_shapes'](shapes, prov).set_index('shape_index')
    assert j.loc[0, 'join_method'] == 'iso_3166_2_code' and j.loc[0, 'province_code'] == 10
    assert j.loc[1, 'join_method'] == 'exact_normalized_english_name' and j.loc[1, 'province_code'] == 20
    assert j.loc[2, 'join_method'] == 'unresolved_no_iso_or_exact_name'  # no fuzzy/substring match
    assert j.loc[3, 'join_method'] == j.loc[4, 'join_method'] == 'unresolved_duplicate_code'


def test_representative_point_inside_concave_polygon(f):
    u_shape = {'type': 'Polygon', 'coordinates': [[[0, 0], [3, 0], [3, 3], [2, 3], [2, 1], [1, 1], [1, 3], [0, 3], [0, 0]]]}
    pts = f['representative_points']([{'properties': {'shapeName': 'U', 'shapeISO': 'TH-99'}, 'geometry': u_shape}, {'properties': {}, 'geometry': None}])
    assert bool(pts.loc[0, 'point_within_polygon']) and bool(pts.loc[0, 'geometry_valid'])
    assert not (1 < pts.loc[0, 'lon'] < 2 and pts.loc[0, 'lat'] > 1)  # not in the notch where a centroid would fall
    assert not pts.loc[1, 'point_within_polygon'] and pd.isna(pts.loc[1, 'lat'])


# ---------- setup cell and runner roots ----------
def _setup_ns(f, monkeypatch, tmp_path, ext=None, out=None):
    v1 = tmp_path / 'v1'
    (v1 / 'data' / 'raw' / 'accidents').mkdir(parents=True)
    (v1 / 'data' / 'raw' / 'accidents' / 'source_manifest.json').write_text('{"files": []}', 'utf-8')
    (v1 / 'data' / 'interim').mkdir(parents=True)
    (v1 / 'data' / 'interim' / 'i.csv').write_text('v1 interim', 'utf-8')
    for k, v in {'ROADAWARE_BACKEND_ROOT': BACKEND, 'ROADAWARE_V1_DATA_ROOT': v1, 'ROADAWARE_V2_EXTERNAL_ROOT': ext or tmp_path / 'ext',
                 'ROADAWARE_V2_OUTPUT_ROOT': out or tmp_path / 'out', 'ROADAWARE_V2_PREFLIGHT_DIR': tmp_path / 'pre'}.items():
        monkeypatch.setenv(k, str(v))
    monkeypatch.setenv('ROADAWARE_V2_OFFLINE', '1')
    monkeypatch.delenv('ROADAWARE_V2_REFRESH', raising=False)
    setup = next(c for c in code_cells() if c.lstrip().startswith('# SETUP'))
    ns = dict(f)
    exec(compile(setup, '09:SETUP', 'exec'), ns)
    return ns, v1


def test_setup_cell_honours_roots_and_protects_v1(f, monkeypatch, tmp_path):
    ns, v1 = _setup_ns(f, monkeypatch, tmp_path)
    assert ns['REP'] == (tmp_path / 'out' / 'reports' / 'v2' / 'sources').resolve() and ns['REP'].is_dir()
    assert ns['EXT'] == (tmp_path / 'ext').resolve() and ns['OFFLINE'] is True and ns['REFRESH'] is False
    assert ns['REGISTRY_PATH'] == ns['EXT'] / 'registry.json' and ns['V1'] == v1.resolve()
    with pytest.raises(ValueError):
        _setup_ns(f, monkeypatch, tmp_path / 'b', ext=tmp_path / 'b' / 'v1' / 'data' / 'raw' / 'cache')
    assert ns['V1_TREE_BEFORE'] == {'data/interim/i.csv': ns['sha256_file'](v1 / 'data' / 'interim' / 'i.csv'),
                                    'data/raw/accidents/source_manifest.json': ns['sha256_file'](v1 / 'data' / 'raw' / 'accidents' / 'source_manifest.json')}


def test_setup_cell_rejects_v1_interim_roots(f, monkeypatch, tmp_path):
    with pytest.raises(ValueError):  # external root = v1 data/interim
        _setup_ns(f, monkeypatch, tmp_path / 'c', ext=tmp_path / 'c' / 'v1' / 'data' / 'interim')
    with pytest.raises(ValueError):  # reports would land under v1 data/interim
        _setup_ns(f, monkeypatch, tmp_path / 'd', out=tmp_path / 'd' / 'v1' / 'data' / 'interim')
    with pytest.raises(ValueError):  # external root containing data/interim
        _setup_ns(f, monkeypatch, tmp_path / 'e', ext=tmp_path / 'e' / 'v1' / 'data')
    for sub in 'cde':
        assert (tmp_path / sub / 'v1' / 'data' / 'interim' / 'i.csv').read_text('utf-8') == 'v1 interim'
        assert sorted(p.name for p in (tmp_path / sub / 'v1' / 'data' / 'interim').iterdir()) == ['i.csv']


@pytest.fixture(scope='module')
def runner():
    spec = importlib.util.spec_from_file_location('run_v2_notebooks', RUNNER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_runner_stages_roots_and_env(runner, tmp_path):
    assert runner.notebooks_for_stage('collect') == ['09_external_collection_date_evidence']
    assert runner.notebooks_for_stage('prepare') == ['10_v2_preparation_features_leakage']
    assert runner.notebooks_for_stage('all') == ['09_external_collection_date_evidence', '10_v2_preparation_features_leakage']
    with pytest.raises(ValueError):
        runner.notebooks_for_stage('train')
    roots = runner.resolve_roots(tmp_path / 'out', tmp_path / 'ext', tmp_path / 'v1', tmp_path / 'pre')
    assert roots['external'] == (tmp_path / 'ext').resolve() and roots['data'] == (tmp_path / 'v1').resolve()
    default = runner.resolve_roots()
    assert default['external'] == runner.BACKEND / 'data' / 'external_v2' and default['output'] == runner.BACKEND
    with pytest.raises(ValueError):
        runner.resolve_roots(tmp_path / 'out', tmp_path / 'v1' / 'data' / 'raw' / 'x', tmp_path / 'v1')
    with pytest.raises(ValueError):
        runner.resolve_roots(tmp_path / 'out', tmp_path / 'v1' / 'reports', tmp_path / 'v1')  # would contain reports/data
    env = runner.build_env(roots, offline=True, base={'ROADAWARE_V2_REFRESH': '1', 'PATH': '/bin'})
    assert env['ROADAWARE_V2_OFFLINE'] == '1' and 'ROADAWARE_V2_REFRESH' not in env and env['PATH'] == '/bin'
    assert env['ROADAWARE_V1_DATA_ROOT'] == str(roots['data'])
    with pytest.raises(ValueError):
        runner.build_env(roots, offline=True, refresh=True, base={})
    (tmp_path / 'v1' / 'data' / 'raw').mkdir(parents=True)
    (tmp_path / 'v1' / 'data' / 'raw' / 'a.csv').write_text('x', 'utf-8')
    assert list(runner.protected_v1_hashes(tmp_path / 'v1')) == ['data/raw/a.csv']
    (tmp_path / 'v1' / 'data' / 'interim').mkdir(parents=True)
    (tmp_path / 'v1' / 'data' / 'interim' / 'i.csv').write_text('y', 'utf-8')
    assert list(runner.protected_v1_hashes(tmp_path / 'v1')) == ['data/raw/a.csv', 'data/interim/i.csv']


# ---------- notebook 10 (preparation): synthetic fixtures only, never real collection ----------
NB10 = BACKEND / 'notebooks' / '10_v2_preparation_features_leakage.ipynb'
FCFG10 = json.loads((BACKEND / 'config' / 'feature_pipeline_v2.json').read_text('utf-8'))
ALIAS = {'พระนครศรีอยุธยา': 'อยุธยา'}


def code_cells10():
    nb = json.loads(NB10.read_text('utf-8'))
    return [''.join(c['source']) if isinstance(c['source'], list) else c['source'] for c in nb['cells'] if c['cell_type'] == 'code']


@pytest.fixture(scope='module')
def g():
    ns = {}
    for i, s in enumerate(s for s in code_cells10() if s.lstrip().startswith('# FUNCTIONS')):
        exec(compile(s, f'10:FUNCTIONS[{i}]', 'exec'), ns)
    return ns


def test_nb10_structure_no_network_and_config_allowlists(g):
    heads = [c.lstrip().split('\n', 1)[0] for c in code_cells10()]
    assert heads[0].startswith('# FUNCTIONS') and heads[1].startswith('# FUNCTIONS') and heads[2].startswith('# SETUP')
    for tag in ('# A.', '# B.', '# C.', '# D.', '# E.', '# F.', '# G.', '# H.', '# Final checks'):
        assert sum(h.startswith(tag) for h in heads) == 1, tag
    src = '\n'.join(code_cells10())
    for net in ('urlopen', 'build_opener', 'requests.', 'http.client', 'socket.'):
        assert net not in src, net
    assert 'import run_v2' not in src and '09_patch' not in src and 'importlib' not in src  # business logic lives in the notebook itself
    allow = {u: [f['name'] for f in FCFG10['features'] if u in f['panels']] for u in ('daily', '6h')}
    for u in allow:
        g['validate_feature_columns'](allow[u], allow[u], FCFG10['forbidden_feature_names'], FCFG10['forbidden_feature_substrings'])
    assert 'time_block' in allow['6h'] and 'time_block' not in allow['daily']
    assert FCFG10['readiness']['production_ready'] is False and FCFG10['readiness']['operational_status'] == 'BLOCKED'
    assert 'PENDING' in FCFG10['pending_groups']['history']


def test_nb10_allowlist_rejects_outcomes_masks_ids(g):
    allow = ['province', 'month']
    for bad in ('accident_type', 'deaths', 'y_recorded_count', 'training_eligible', 'possibly_undercounted', 'event_uid', 'acc_code',
                'target_date', 'split', 'weather', 'n_involved', 'wx_rain_missing', 'trf_vintage_survey_year_ce'):
        with pytest.raises(ValueError):
            g['validate_feature_columns'](allow + [bad], allow + [bad], FCFG10['forbidden_feature_names'], FCFG10['forbidden_feature_substrings'])
    with pytest.raises(ValueError):  # not allowlisted even if harmless-looking
        g['validate_feature_columns'](['province', 'other'], ['province'], [], [])


def test_nb10_v1_parsers_mixed_2022_be_years_and_24h(g):
    p = g['parse_date_v1']
    assert p('13/1/2022', 2022)[2] == 'ok' and p('13/1/2022', 2022)[0] == dt.date(2022, 1, 13)
    assert p('1/13/2022', 2022)[0] == dt.date(2022, 1, 13)  # mixed formats inside one file: per-row readings, no global parser
    assert p('2/3/2022', 2022)[2] == 'ambiguous' and p('2/3/2022', 2022)[3] == ('2022-02-03', '2022-03-02')
    assert p('2/3/2565', 2022)[3] == ('2022-02-03', '2022-03-02')  # BE year
    assert p('5/5/2021', 2022)[2] == 'year_mismatch'
    t = g['parse_time_v1']
    assert t('24:00') == (None, 'invalid') and t('23:59:59') == (86399, 'ok') and t('6:00') == (21600, 'ok') and t('0.25') == (21600, 'ok')
    assert g['time_minute'](dt.time(9, 5)) == g['time_minute']('9:05') == 545 and g['time_minute']('24:00') is None


def test_nb10_independent_context_match_conflict_alias_unavailable(g):
    x = pd.DataFrame({'acc_code': ['1', '2', '3', '3', '4', 5.0], 'province': ['อยุธยา', 'ตาก', 'ตาก', 'ตาก', 'ตาก', 'ตาก'],
                      'time': [dt.time(9, 5), dt.time(1, 0), dt.time(2, 0), dt.time(2, 1), None, dt.time(3, 0)]})
    rows = pd.DataFrame({'acc_code': ['1', '2', '3', '4', '5', '6'], 'province': ['พระนครศรีอยุธยา', 'น่าน', 'ตาก', 'ตาก', 'ตาก', 'ตาก'],
                         'time_raw': ['9:05', '1:00', '2:00', '7:00', '3:00', '1:00']})
    s = g['independent_context'](rows, x, ALIAS).tolist()
    assert s == ['agree', 'conflict_province', 'conflict_time', 'unavailable_time', 'agree', 'unavailable_xlsx_id']
    assert set(g['independent_context'](rows, None, ALIAS)) == {'unavailable_xlsx_file'}


def _rows(**cols):
    base = dict(disposition='quarantined', date_status='ambiguous', date_candidates='2021-02-03;2021-03-02', source_year_ce=2021,
                ev09_status='resolved', ev09_resolved_date='2021-03-02', ctx10_status='agree')
    n = max(len(v) for v in cols.values() if isinstance(v, list)) if any(isinstance(v, list) for v in cols.values()) else 1
    return pd.DataFrame({k: (v if isinstance(v, list) else [v] * n) for k, v in {**base, **cols}.items()})


def test_nb10_date_decisions_only_candidate_context_verified(g):
    r = _rows(ev09_resolved_date=['2021-03-02', '2021-03-05', '2021-03-02', '2021-03-02', '2021-03-02', '2021-03-02'],
              ctx10_status=['agree', 'agree', 'conflict_time', 'unavailable_province', 'agree', 'agree'],
              ev09_status=['resolved'] * 4 + ['mismatch', 'resolved'], source_year_ce=[2021] * 5 + [2024])
    dec, d = g['date_decisions'](r, [2021, 2022, 2023])
    assert dec.tolist() == [g['REPAIRED'], 'ambiguous_09_date_not_a_candidate', 'ambiguous_ctx10_conflict_time', 'ambiguous_ctx10_unavailable_province',
                            'ambiguous_09_mismatch', 'ambiguous_no_xlsx_year']
    assert d.tolist()[0] == '2021-03-02' and all(v is None for v in d.tolist()[1:])
    dec2, _ = g['date_decisions'](r, [2021, 2022, 2023], accept_partial=True)  # only an explicit config switch accepts partial context
    assert dec2.tolist()[3] == g['REPAIRED']
    ok = _rows(disposition='retained', date_status='ok', date_candidates='2021-05-20', ev09_resolved_date='2021-05-21', ev09_status='mismatch')
    assert g['date_decisions'](ok, [2021])[0].tolist() == ['v1_date_kept']  # unambiguous v1 date never replaced
    diag = _rows(disposition='diagnostic', source_year_ce=2026)
    assert g['date_decisions'](diag, [2021])[0].tolist() == ['diagnostic_not_label']


def test_nb10_redecide_groups_preserves_strict_conflicts(g):
    R = g['REPAIRED']
    rows = pd.DataFrame({
        'source_year': ['2564'] * 8, 'source_row': [2, 3, 4, 5, 6, 7, 8, 9],
        'acc_code': ['A', 'B', 'B', 'C', 'C', 'D', 'D', 'E'],
        'disposition': ['quarantined'] * 7 + ['quarantined'],
        'reasons': ['date_ambiguous', 'date_ambiguous;time_invalid', 'id_group_member_invalid', 'date_ambiguous', 'date_ambiguous',
                    'id_conflict_other_fields', 'id_conflict_other_fields', 'date_ambiguous'],
        'kept_source_row': [''] * 8,
        'date_decision': [R, R, 'v1_date_kept', R, R, 'v1_date_kept', 'v1_date_kept', 'ambiguous_ctx10_conflict_time']})
    sigs = {('2564', 5): ('s', 't'), ('2564', 6): ('s', 't')}
    o = g['redecide_groups'](rows, sigs)
    assert o['v2_disposition'].tolist() == ['retained', 'quarantined', 'quarantined', 'retained', 'collapsed', 'quarantined', 'quarantined', 'quarantined']
    assert o['v2_reasons'].tolist()[1:3] == ['time_invalid', 'id_group_member_invalid']
    assert o['v2_reasons'].tolist()[5:7] == ['id_conflict_other_fields'] * 2 and not o['v2_redecided'].iloc[5]  # strict v1 conflict untouched
    assert o['v2_kept_source_row'].iloc[4] == '5'
    o2 = g['redecide_groups'](rows, {('2564', 5): ('s', 't'), ('2564', 6): ('s2', 't')})
    assert o2['v2_disposition'].tolist()[3:5] == ['quarantined'] * 2 and o2['v2_reasons'].iloc[3] == 'id_conflict_other_fields'
    with pytest.raises(KeyError):
        g['redecide_groups'](rows, {})


def test_nb10_unknown_flags_all_provinces_repaired_and_no_candidate(g):
    prov, dates = ['ก', 'ข', 'ค'], ['2021-01-01', '2021-01-02', '2021-01-03']
    x = pd.DataFrame({'province_key': ['ก', '', 'ข', 'ค', 'ก'], 'flag_dates': ['2021-01-01;2021-01-02', '2021-01-03', '2021-01-02', '', '2026-01-01'],
                      'reasons': ['date_ambiguous', 'province_missing', 'id_conflict_other_fields', 'date_invalid', 'no_acc_code'],
                      'source_year_ce': [2021] * 4 + [2026], 'flag_kind': ['quarantined'] * 4 + ['diagnostic']})
    fl, up, st = g['unknown_flags'](x, prov, dates)
    keys = set(zip(fl['province_key'], fl['date']))
    assert keys == {('ก', '2021-01-01'), ('ก', '2021-01-02'), ('ข', '2021-01-02'), ('ก', '2021-01-03'), ('ข', '2021-01-03'), ('ค', '2021-01-03')}
    assert st['dates_outside_panel'] == 1 and st['rows_without_candidate_date'] == 1 and up.to_dict('records') == [{'province_key': 'ค', 'year_ce': 2021, 'n_rows': 1}]
    fl2, _, _ = g['unknown_flags'](x, prov, dates, {2021: dates}, policy='flag_province_year')
    assert {('ค', d) for d in dates} <= set(zip(fl2['province_key'], fl2['date']))
    # a repaired row flags only its repaired date: the other candidate is no longer flagged
    rep = x.iloc[[0]].assign(flag_dates='2021-01-02')
    assert set(g['unknown_flags'](rep, prov, dates)[0]['date']) == {'2021-01-02'}
    assert g['expand_v1_flags'](pd.DataFrame({'province': ['*ALL*'], 'date': ['2021-01-01']}), prov) == {(p, '2021-01-01') for p in prov}


def test_nb10_time_block_boundaries(g):
    b = g['time_block_index']
    assert [b(s) for s in (0, 21599, 21600, 43199, 43200, 64800, 86399)] == [0, 0, 1, 1, 2, 3, 3]
    with pytest.raises(ValueError):
        b(86400)
    with pytest.raises(ValueError):
        b(None)
    assert [g['block_label'](i) for i in range(4)] == ['00-06', '06-12', '12-18', '18-24']


def test_nb10_panels_daily_equals_sum_of_blocks_and_flags_broadcast(g):
    ev = pd.DataFrame({'province_key': ['ก', 'ก', 'ข', 'ข'], 'event_date': ['2021-01-01', '2021-01-01', '2021-01-02', '2021-01-02'],
                       'time_sec': [21600, 64799, 0, 86399]})
    flags = pd.DataFrame({'province_key': ['ข'], 'date': ['2021-01-01'], 'n_flagged_rows': [2], 'flag_reasons': ['date_ambiguous']})
    up = pd.DataFrame(columns=['province_key', 'year_ce', 'n_rows'])
    splits = [{'name': 'train', 'start': '2021-01-01', 'end': '2021-12-31'}]
    d, blk = g['build_panels'](ev, ['ก', 'ข'], ['2021-01-01', '2021-01-02'], flags, up, splits, 18, 1, 25200)
    chk = g['reconcile_panels'](d, blk, 4)
    assert all(chk.values()) and len(d) == 4 and len(blk) == 16
    r = d.set_index(['province_key', 'target_date'])
    assert r.loc[('ก', '2021-01-01'), 'y_recorded_count'] == 2 and r.loc[('ข', '2021-01-01'), 'training_eligible'] == False  # noqa: E712
    assert r.loc[('ก', '2021-01-01'), 'issue_time_local'] == '2020-12-31T18:00:00+07:00'
    assert r.loc[('ก', '2021-01-01'), 'issue_time_utc'] == '2020-12-31T11:00:00+00:00'
    bb = blk.set_index(['province_key', 'target_date', 'time_block'])
    assert bb.loc[('ก', '2021-01-01', '06-12'), 'y_recorded_count'] == 1 and bb.loc[('ก', '2021-01-01', '12-18'), 'y_recorded_count'] == 1
    assert bb.loc[('ข', '2021-01-02', '18-24'), 'target_end_local'] == '2021-01-03T00:00:00+07:00'
    assert (~bb.xs('2021-01-01', level='target_date').loc['ข', 'training_eligible']).all()
    bad = ev.assign(province_key=['ก', 'ก', 'ข', 'X'])
    with pytest.raises(ValueError):
        g['build_panels'](bad, ['ก', 'ข'], ['2021-01-01', '2021-01-02'], flags, up, splits, 18, 1, 25200)
    broken = blk.copy()
    broken.loc[0, 'y_recorded_count'] += 1
    with pytest.raises(AssertionError):
        g['reconcile_panels'](d, broken, 4)


def test_nb10_festival_cross_year_windows_and_clip(g):
    fests = [{'id': 'songkran', 'month_days': [[4, 13], [4, 14], [4, 15]]}, {'id': 'new_year', 'month_days': [[12, 31], [1, 1]]}]
    f = g['festival_features'](['2021-12-26', '2021-12-30', '2022-01-01', '2022-01-02', '2022-01-08', '2021-04-10', '2021-04-16', '2021-06-01'],
                               fests, 14, FCFG10['festivals']['windows']).set_index('target_date')
    assert f.loc['2021-12-30', 'fest_new_year_dist'] == -1 and f.loc['2021-12-30', 'fest_new_year_pre_1_3'] == 1
    assert f.loc['2021-12-26', 'fest_new_year_pre_4_7'] == 1 and f.loc['2022-01-01', 'fest_new_year_in'] == 1
    assert f.loc['2022-01-02', 'fest_new_year_dist'] == 1 and f.loc['2022-01-08', 'fest_new_year_post_4_7'] == 1
    assert f.loc['2021-04-10', 'fest_songkran_dist'] == -3 and f.loc['2021-04-16', 'fest_songkran_post_1_3'] == 1
    assert f.loc['2021-06-01', 'fest_songkran_dist'] == 14 and f.loc['2021-06-01', 'fest_new_year_dist'] in (-14, 14)
    s = g['season_features'](['2021-03-01', '2021-06-01', '2021-02-01'], FCFG10['season']['months'])
    assert s[['season_hot', 'season_wet', 'season_cool']].to_numpy().tolist() == [[1, 0, 0], [0, 1, 0], [0, 0, 1]]


def test_nb10_bank_calendar_late_announcement_remove_and_unknown(g):
    rec = pd.DataFrame({'date': ['2024-01-02', '2024-01-02', '2024-04-12', '2024-01-01'], 'action': ['add', 'remove', 'add', 'add'],
                        'known_from': ['2023-07-26', '2023-11-13', '2024-02-21', '2023-07-26'], 'applied': [True, True, True, True],
                        'source_id': ['base', 'amend', 'special', 'base']})
    src = [{'id': 'base', 'role': 'annual_base', 'years': [2024]}]
    f = g['bank_calendar_features'](['2024-01-01', '2024-01-02', '2024-04-12', '2025-01-01'], rec, src, 18, 1).set_index('target_date')
    assert f.loc['2024-01-01', 'bank_holiday_asof'] == 1.0
    assert f.loc['2024-01-02', 'bank_holiday_asof'] == 0.0  # removal known 2023-11-13 applies before the 2024-01-01 issue
    assert f.loc['2024-04-12', 'bank_holiday_asof'] == 1.0  # announced 2024-02-21: known well before
    assert np.isnan(f.loc['2025-01-01', 'bank_holiday_asof']) and f.loc['2025-01-01', 'bank_calendar_known_asof'] == 0  # unknown != ordinary day
    late = g['bank_calendar_features'](['2024-02-21'], rec.assign(date=['2024-02-21'] * 4, action=['add'] * 4), src, 18, 1)
    assert late['bank_holiday_asof'].iloc[0] == 1.0  # base add (known 2023) still applies; the late source alone would not
    only_late = rec.iloc[[2, 3]].assign(date=['2024-02-21', '2024-01-01'])
    assert g['bank_calendar_features'](['2024-02-21'], only_late, src, 18, 1)['bank_holiday_asof'].iloc[0] == 0.0
    with pytest.raises(ValueError):
        g['load_calendar_records'](io.StringIO('date,action,known_from,applied,source_id\n2024-01-01,add,2023-07-26,maybe,base\n'))


def test_nb10_traffic_asof_rejects_future_vintage(g):
    meta = pd.DataFrame({'survey_year_ce': ['2020', '2021', '2022', '2023'], 'normalize_status': ['normalized'] * 3 + ['failed'],
                         'available_from_proxy_utc': ['2024-06-01T07:41:10+00:00', '2022-03-25T06:10:50+00:00', '2023-01-05T00:00:00+00:00', '2023-01-01T00:00:00+00:00']})
    v = g['traffic_vintage_by_date'](meta, ['2021-06-01', '2022-06-01', '2023-01-05', '2023-01-06', '2024-03-01'], 18, 1, 25200).set_index('target_date')
    assert np.isnan(v.loc['2021-06-01', 'trf_vintage_survey_year_ce'])  # 2020 bytes revised 2024: unavailable, never backfilled
    assert v.loc['2022-06-01', 'trf_vintage_survey_year_ce'] == 2021
    assert v.loc['2023-01-05', 'trf_vintage_survey_year_ce'] == 2021  # 2022 vintage available only after the issue time
    assert v.loc['2023-01-06', 'trf_vintage_survey_year_ce'] == 2022 and v.loc['2024-03-01', 'trf_vintage_survey_year_ce'] == 2022  # failed 2023 unused
    summ = pd.DataFrame({'survey_year_ce': ['2021'], 'province_key': ['ก'], 'mean_total_aadt': ['100.5'], 'median_total_aadt': ['90'],
                         'mean_heavy_share_pct': ['12'], 'n_station_rows': ['3']})
    t = g['traffic_features'](summ, v.reset_index(), ['ก', 'ข']).set_index(['province_key', 'target_date'])
    assert t.loc[('ก', '2022-06-01'), 'trf_mean_aadt'] == 100.5 and np.isnan(t.loc[('ข', '2022-06-01'), 'trf_mean_aadt'])
    assert np.isnan(t.loc[('ก', '2021-06-01'), 'trf_mean_aadt'])


def test_nb10_weather_complete_hours_and_issue_guard(g):
    issue_utc = pd.Timestamp('2021-03-01 11:00')  # 2021-03-02 target: issue 2021-03-01 18:00 local
    wx = pd.DataFrame({'province_code': ['10', '10', '11'], 'date': ['2021-03-02', '2021-03-03', '2021-03-02'], 'time_block': ['day'] * 3,
                       'rain_sum': ['1.5', '', '2.0'], 'temp_mean': ['30', '29', '31'], 'rain_missing': ['False', 'True', 'False'],
                       'temp_missing': ['False', 'False', 'False'], 'issue_bound_ok': ['True', 'True', 'False'],
                       'latest_issue_bound_utc': [str(issue_utc - pd.Timedelta(hours=6)), str(issue_utc + pd.Timedelta(hours=18)),
                                                  str(issue_utc - pd.Timedelta(hours=5))]})
    out, audit = g['weather_features'](wx, {10: 'ก', 11: 'ข'}, 6, 18, 1, 25200, 'wx_')
    o = out.set_index(['province_key', 'target_date'])
    assert o.loc[('ก', '2021-03-02'), 'wx_rain_sum_mm_d2'] == 1.5  # exactly bound + 6 h == issue is allowed
    assert np.isnan(o.loc[('ก', '2021-03-03'), 'wx_rain_sum_mm_d2']) and o.loc[('ก', '2021-03-03'), 'wx_temp_mean_c_d2'] == 29.0  # incomplete rain stays NaN
    assert np.isnan(o.loc[('ข', '2021-03-02'), 'wx_rain_sum_mm_d2'])  # 1 h too late for the issue time
    assert audit['rows_guard_failed'] == 1
    with pytest.raises(g['DependencyError']):  # 09 says ok but the independent recomputation disagrees
        g['weather_features'](wx.assign(issue_bound_ok='True'), {10: 'ก', 11: 'ข'}, 6, 18, 1, 25200, 'wx_')


def test_nb10_negative_controls_all_rejected(g):
    allow = [f['name'] for f in FCFG10['features'] if '6h' in f['panels']]
    res = g['leakage_negative_controls']([], allow, FCFG10['forbidden_feature_names'], FCFG10['forbidden_feature_substrings'], 6, 18, 1, 25200)
    assert len(res) >= 12 and all(r['rejected'] for r in res), [r for r in res if not r['rejected']]


def test_nb10_dependency_tamper_and_deterministic_gzip(g, tmp_path):
    p = tmp_path / 'in.csv'
    p.write_text('a\n1\n', 'utf-8')
    h = g['sha256_file'](p)
    assert g['verify_file'](p, h, 'x') == h
    p.write_text('a\n2\n', 'utf-8')
    with pytest.raises(g['DependencyError']):
        g['verify_file'](p, h, 'x')
    with pytest.raises(g['DependencyError']):
        g['verify_file'](tmp_path / 'missing.csv', h, 'x')
    df = pd.DataFrame({'a': [1, 2], 'b': ['x', 'ย']})
    g['write_csv_gz'](tmp_path / 'a.csv.gz', df)
    g['write_csv_gz'](tmp_path / 'b.csv.gz', df)
    assert g['sha256_file'](tmp_path / 'a.csv.gz') == g['sha256_file'](tmp_path / 'b.csv.gz')
    with pytest.raises(ValueError):
        g['write_csv'](tmp_path / 'inf.csv', pd.DataFrame({'a': [np.inf]}))


def test_runner_prepare_roots_isolated_from_read_only_inputs(runner, tmp_path):
    r = runner.resolve_roots(tmp_path / 'out', tmp_path / 'ext', tmp_path / 'v1', stage='prepare')
    assert r['v2_data'] == (tmp_path / 'out').resolve() / 'data' / 'v2'
    assert r['sources'] == runner.BACKEND / 'reports' / 'v2' / 'sources'
    assert runner.resolve_roots(tmp_path / 'out', stage='all')['sources'] == (tmp_path / 'out').resolve() / 'reports' / 'v2' / 'sources'
    r2 = runner.resolve_roots(tmp_path / 'out', tmp_path / 'ext', tmp_path / 'v1', sources_dir=tmp_path / 'src', stage='prepare')
    env = runner.build_env(r2, base={'ROADAWARE_V2_DATA_ROOT': '/stale', 'ROADAWARE_V2_SOURCES_DIR': '/stale'})
    assert env['ROADAWARE_V2_DATA_ROOT'] == str(r2['v2_data']) and env['ROADAWARE_V2_SOURCES_DIR'] == str((tmp_path / 'src').resolve())
    with pytest.raises(ValueError):  # 10 must never write inside the read-only external root
        runner.resolve_roots(tmp_path / 'out', tmp_path / 'out' / 'data', tmp_path / 'v1', stage='prepare')
    with pytest.raises(ValueError):  # ... nor inside the 09 sources dir
        runner.resolve_roots(tmp_path / 'out', tmp_path / 'ext', tmp_path / 'v1', sources_dir=tmp_path / 'out' / 'reports' / 'v2' / 'preparation', stage='prepare')
    with pytest.raises(ValueError):  # v2 data root under the protected v1 data/ tree
        runner.resolve_roots(tmp_path / 'v1' / 'data' / 'raw', tmp_path / 'ext', tmp_path / 'v1', stage='prepare')


def test_runner_rejects_v1_interim_roots(runner, tmp_path):
    v1 = tmp_path / 'v1'
    with pytest.raises(ValueError):
        runner.resolve_roots(tmp_path / 'out', v1 / 'data' / 'interim', v1)
    with pytest.raises(ValueError):
        runner.resolve_roots(tmp_path / 'out', v1 / 'data' / 'interim' / 'ext', v1)
    with pytest.raises(ValueError):  # report dir <output>/reports/v2 under data/interim
        runner.resolve_roots(v1 / 'data' / 'interim', tmp_path / 'ext', v1)
    default = runner.resolve_roots()
    assert default['output'] == runner.BACKEND and default['external'] == runner.BACKEND / 'data' / 'external_v2'
    with pytest.raises(ValueError):  # the real backend interim is protected too (read-only check, nothing is written)
        runner.resolve_roots(external_root=runner.BACKEND / 'data' / 'interim')
    assert not v1.exists()
