"""Read-only independent verifier for a notebook-14 historical catalog run (RoadAware V3).

Usage (from the repository root):
    .venv/bin/python backend/scripts/verify_historical_catalog.py --catalog-root backend/rerun-historical-catalog-020-003
    .venv/bin/python backend/scripts/verify_historical_catalog.py --catalog-root backend/rerun-historical-catalog-020-003 \
        --output backend/rerun-historical-catalog-020-003/verification/historical_catalog_verification.json

What it checks (each line is one PASS/FAIL row):
* manager pins and accepted producer membership of every config input (notebook-10 inputs/data_outputs, notebook-19 data_files_gitignored,
  notebook-19 independent review), every needed raw CSV against the raw manifest and the notebook-10 v1_raw_csv record;
* an INDEPENDENT raw oracle: retained lineage -> raw CSV record (iloc = source_row - first_data_row) -> exact BE-year:ACC_CODE == event_uid ->
  the three description fields via the pinned audited aliases, compared with the catalog's recovered descriptions and the legacy V1 file;
* province 77 x 60 monthly counts, known/unknown denominators and category marginals recomputed from accepted events + oracle descriptions;
* notebook-19 selected rows (1:1 join, accepted date/block/province), daily and 6 h recounts vs the accepted 19 counts and the catalog row context;
* the catalog manifest (complete, research-only, every check pass, every output hash, config/notebook FUNCTIONS/code-cell hashes);
* every as-of / retrospective example in query_examples.json re-derived with plain datetime arithmetic from the oracle rows;
* no retained event UID (exact set membership) and no event-level column in any served report/data file.

Independence and safety: notebook-14 code is NEVER imported or executed (FUNCTIONS cells are only hashed as text) and the catalog's recovery
is never called. The oracle logic was written after the manager preflight .ai-team/references/catalog_raw_enrichment_preflight.py (a disclosed
development aid; it is not read or run here). Input paths come from config/catalog_v3.json, description aliases from the pinned
config/data_pipeline.json. Nothing is written unless --output names a NEW .json file outside every protected/guarded path and outside the
catalog report/data dirs; the evidence holds aggregate counts and hashes only (no event UID, source row, coordinate or narrative).
Exit code: 0 every check passed, 1 at least one check failed, 2 refused/usage error.
"""
import argparse
import datetime as dt
import gzip
import hashlib
import json
import os
import re
import sys
import traceback
from pathlib import Path, PurePosixPath

import pandas as pd

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
CONFIG_REL = 'config/catalog_v3.json'
SCHEMA = 'roadaware-historical-catalog-verification/1'
REPORT_EVENT_COLUMNS = {'event_uid', 'source_row', 'acc_code', 'time_sec', 'lat', 'lon', 'latitude', 'longitude', 'chosen_source_oid', 'chosen_part',
                        'chosen_piece'}
PROVENANCE_DATA_FILE = 'recovered_descriptions.csv.gz'  # ignored provenance file kept for this oracle; holds UIDs by design, never served
NOT_RUN = [
    'load_catalog / query_* functions were NOT executed (this verifier never execs notebook code); the examples are re-derived from data instead',
    'raw CSVs are parsed with pandas.read_csv(dtype=str, keep_default_na=False) like the notebook; no second, independent CSV parser is used',
    'figures (PNG) are only checked for presence and hash; their visual content needs a human review',
    'Thai report / serving-interface wording is not reviewed here',
    'random brute-force query controls are trusted from negative_controls.csv (pass flags), not re-run',
    'the notebook kernel run itself and the pytest suites are separate commands',
]


# ---------- small helpers ----------
def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def _no_dup(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise ValueError('duplicate JSON key ' + repr(k)[:80])
        out[k] = v
    return out


def _no_const(c):
    raise ValueError('non-finite JSON constant ' + c)


def read_json(path):
    return json.loads(Path(path).read_text('utf-8'), object_pairs_hook=_no_dup, parse_constant=_no_const)


def read_str(path, **kw):
    return pd.read_csv(path, dtype=str, keep_default_na=False, **kw)


def norm(s):
    # V1 norm_text: whitespace runs -> one space, strip; blank stays '' (= unknown)
    return s.fillna('').astype(str).str.replace(r'\s+', ' ', regex=True).str.strip()


def suffix_match(recorded, rel):
    r = str(recorded).replace('\\', '/')
    return r == rel or r.endswith('/' + rel)


def safe_rel(rel):
    pp = PurePosixPath(str(rel))
    if not rel or pp.is_absolute() or any(p in ('..', '.', '') for p in pp.parts) or '\\' in str(rel):
        raise ValueError('unsafe relative path ' + repr(rel)[:120])
    return pp


def month_range(first, last):
    y, m, out = int(first[:4]), int(first[5:7]), []
    while '%04d-%02d' % (y, m) <= last:
        out.append('%04d-%02d' % (y, m))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def frames_equal(a, b, keys):
    cols = list(a.columns)
    if sorted(cols) != sorted(b.columns):
        return False
    x = a[cols].sort_values(keys, kind='stable').reset_index(drop=True)
    y = b[cols].sort_values(keys, kind='stable').reset_index(drop=True)
    return len(x) == len(y) and x.equals(y)


def uid_counter(uids):
    """Counts retained UIDs in text: exact set membership of tokens starting at '<BE year>:' (not after a digit, not followed by alnum)."""
    U = frozenset(uids)
    lens = sorted({len(u) for u in U})
    rx = re.compile('(?<![0-9])(?:' + '|'.join(re.escape(p) for p in sorted({u.split(':', 1)[0] + ':' for u in U})) + ')')

    def count(text):
        n = 0
        for m in rx.finditer(text):
            tail = text[m.start():m.start() + lens[-1] + 1]
            for L in lens:
                if L > len(tail):
                    break
                if tail[:L] in U and (L == len(tail) or not tail[L].isalnum()):
                    n += 1
                    break
        return n
    return count


class Checks:
    def __init__(self):
        self.rows = []

    def add(self, name, ok, expected=None, observed=None):
        def short(v):
            if v is None or isinstance(v, bool) or (isinstance(v, int) and abs(v) < 2 ** 53):
                return v
            return str(v)[:300]
        self.rows.append({'check': name, 'ok': bool(ok), 'expected': short(expected), 'observed': short(observed)})
        print(('PASS  ' if ok else 'FAIL  ') + name + ('' if ok else '  expected=' + str(short(expected)) + ' observed=' + str(short(observed))), flush=True)
        return bool(ok)

    def section(self, name, fn, *a):
        try:
            return fn(*a)
        except Exception as e:  # a crash is a recorded failure, never a silent pass
            self.add('section ' + name + ' completed without error', False, None, type(e).__name__ + ': ' + str(e)[:240])
            traceback.print_exc()
            return None


# ---------- 1. pins and accepted producers ----------
def verify_inputs(cfg, C):
    I = {k: v['path'] for k, v in cfg['inputs'].items()}
    pins = read_json(REPO / cfg['pins']['path'])
    C.add('manager pins schema and registered flag', pins.get('schema') == cfg['pins']['schema'] and pins.get(cfg['pins']['registered_flag']) is True)
    files = pins.get('files') or {}
    C.add('manager pin file set == config inputs', set(files) == set(I.values()), len(I), len(files))
    sha = {}
    for name, rel in I.items():
        p = BACKEND / safe_rel(rel)
        sha[name] = sha256_file(p) if p.is_file() and not p.is_symlink() else None
    bad = sorted(n for n in I if sha[n] is None or sha[n] != files.get(I[n]))
    C.add('every config input is a regular file whose sha256 == manager pin', not bad, [], bad)
    docs = {n: read_json(BACKEND / I[n]) for n in ('preparation_manifest', 'spatial_preparation_manifest', 'spatial_review', 'raw_manifest', 'data_pipeline')}
    m10, m19, rv, P = docs['preparation_manifest'], docs['spatial_preparation_manifest'], docs['spatial_review'], cfg['producers']
    st = {'producer10_self': m10.get('producer') == P['10']['producer'] and m10.get('schema') == P['10']['schema'] and m10.get('status') == P['10']['status'],
          'producer19_self': m19.get('status') == P['19']['status'], 'review19': rv.get('status') == P['19_review']['status']}
    C.add('notebook-10 manifest is the accepted completed producer', st['producer10_self'], P['10']['status'], m10.get('status'))
    C.add('notebook-19 manifest complete', st['producer19_self'], P['19']['status'], m19.get('status'))
    C.add('notebook-19 independent review accepted', st['review19'], P['19_review']['status'], rv.get('status'))
    nonmember = []
    for name, v in cfg['inputs'].items():
        rule, parent = v['corroborate'], PurePosixPath(I[name]).parent.as_posix()
        if rule['rule'] == 'producer10_input':
            hits = [x for x in m10.get('inputs', []) if x.get('role') == rule['role'] and suffix_match(x.get('path', ''), I[name])]
            ok = len(hits) == 1 and hits[0].get('sha256') == sha[name]
        elif rule['rule'] == 'producer10_data_output':
            hits = [x for x in m10.get('data_outputs', []) if x.get('path') == rule['name']]
            ok = (parent == P['10']['data_dir'] and len(hits) == 1 and hits[0].get('sha256') == sha[name]
                  and int(hits[0].get('bytes', -1)) == (BACKEND / I[name]).stat().st_size)
        elif rule['rule'] == 'producer19_data':
            ok = parent == P['19']['data_dir'] and (m19.get('data_files_gitignored') or {}).get(rule['name']) == sha[name]
        else:
            ok = st.get(rule['rule'], False)
        if not ok:
            nonmember.append(name)
    C.add('every input hash corroborated by its accepted producer record', not nonmember, [], nonmember)
    return I, sha, docs


# ---------- 2. independent raw oracle ----------
def oracle_recovery(cfg, I, docs, C):
    fields, aliases, m10 = list(cfg['recovery']['fields']), docs['data_pipeline']['schema_aliases'], docs['preparation_manifest']
    first = int(cfg['raw']['first_data_row'])
    ev = read_str(BACKEND / I['events_v2'])
    lin = read_str(BACKEND / I['row_lineage_v2'])
    lin = lin[lin['v2_disposition'] == cfg['recovery']['retained_disposition']]
    C.add('accepted events UIDs unique', ev['event_uid'].is_unique, len(ev), int(ev['event_uid'].nunique()))
    C.add('retained lineage UIDs unique', lin['event_uid'].is_unique, len(lin), int(lin['event_uid'].nunique()))
    C.add('retained lineage UID set == accepted events UID set', set(lin['event_uid']) == set(ev['event_uid']), len(ev), len(lin))
    C.add('retained source_row values are plain integers', bool(lin['source_row'].str.fullmatch(r'[0-9]+').all()))
    C.add('retained source coordinates (file, row) unique', not lin.duplicated(['source_file', 'source_row']).any())
    entries = docs['raw_manifest'].get('files') or []
    by_file = {}
    for e in entries:
        by_file.setdefault(e.get('file'), []).append(e)
    frames, files, problems = [], {}, []
    for f, l in lin.groupby('source_file', sort=True):
        es = by_file.get(f, [])
        if len(es) != 1:
            problems.append(f + ': ' + str(len(es)) + ' raw manifest entries')
            continue
        e = es[0]
        rel = safe_rel(e['path'])
        p = BACKEND.joinpath(*rel.parts)
        s = sha256_file(p)
        m10sha = [x.get('sha256') for x in m10.get('inputs', []) if x.get('role') == cfg['raw']['producer10_role'] and suffix_match(x.get('path', ''), rel.as_posix())]
        if s != e.get('sha256') or m10sha != [s]:
            problems.append(f + ': sha differs from raw manifest or notebook-10 v1_raw_csv')
        if e.get('encoding') not in cfg['raw']['allowed_encodings'] or int(e['be_year']) - int(e['ce_year']) != 543:
            problems.append(f + ': encoding/year fields invalid')
        if ('bytes' in e and int(e['bytes']) != p.stat().st_size):
            problems.append(f + ': byte size differs')
        if not (l['source_year_ce'] == str(e['ce_year'])).all():
            problems.append(f + ': lineage source_year_ce differs from raw manifest ce_year')
        raw = read_str(p, encoding=e['encoding'])
        if len(raw) != int(e['rows']):
            problems.append(f + ': records ' + str(len(raw)) + ' != manifest rows ' + str(e['rows']))
        rows = l['source_row'].astype('int64').to_numpy()
        if rows.min() < first or rows.max() > len(raw) + first - 1:
            problems.append(f + ': source_row outside bounds')
            continue
        r = raw.iloc[rows - first].reset_index(drop=True)
        idc = [c for c in aliases['acc_code'] if c in raw.columns]
        if len(idc) != 1:
            problems.append(f + ': ' + str(len(idc)) + ' ACC_CODE headers')
            continue
        uid_bad = int(((str(e['be_year']) + ':' + norm(r[idc[0]])).to_numpy() != l['event_uid'].to_numpy()).sum())
        if uid_bad:
            problems.append(f + ': ' + str(uid_bad) + ' rows where BE-year:ACC_CODE != event_uid')
        out = pd.DataFrame({'event_uid': l['event_uid'].to_numpy(), 'ce_year': str(e['ce_year'])})
        missing = []
        for fld in fields:
            cols = [c for c in aliases[fld] if c in raw.columns]
            if len(cols) > 1:
                problems.append(f + ': ambiguous headers for ' + fld)
            if not cols:
                missing.append(fld)
            out[fld] = norm(r[cols[0]]).to_numpy() if cols else ''
        files[f] = {'sha256': s, 'ce_year': int(e['ce_year']), 'raw_records': len(raw), 'events': len(l), 'missing_headers': missing}
        frames.append(out)
    C.add('every needed raw CSV verified (raw manifest + notebook-10 sha, encoding, years, record count, row bounds, exact BE-year:ACC_CODE, '
          'unambiguous aliases)', not problems, [], problems[:10])
    O = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=['event_uid', 'ce_year'] + fields)
    C.add('oracle recovered exactly the accepted events (no raw-only rows)', len(O) == len(ev) and O['event_uid'].is_unique and set(O['event_uid']) == set(ev['event_uid']),
          len(ev), len(O))
    return ev, O, files


def compare_catalog_recovery(cfg, I, ev, O, data_dir, report_dir, C):
    fields = list(cfg['recovery']['fields'])
    cat = read_str(data_dir / PROVENANCE_DATA_FILE)
    C.add('catalog recovered rows == accepted events (unique, same UID set)', len(cat) == len(ev) and cat['event_uid'].is_unique and set(cat['event_uid']) == set(ev['event_uid']),
          len(ev), len(cat))
    j = O.merge(cat, on='event_uid', how='inner', suffixes=('_oracle', '_catalog'), validate='one_to_one')
    for f in fields:
        mism = int((j[f + '_oracle'] != j[f + '_catalog']).sum())
        C.add('independent raw oracle == catalog ' + f + ' on every accepted event', mism == 0 and len(j) == len(ev), 0, mism)
    C.add('catalog ce_year == raw manifest ce_year', int((j['ce_year_oracle'] != j['ce_year_catalog']).sum()) == 0)
    k = ev[['event_uid', 'event_date', 'time_block', 'province_key']].merge(cat[['event_uid', 'event_date', 'time_block', 'province_key']], on='event_uid',
                                                                          suffixes=('', '_cat'), validate='one_to_one')
    bad = {c: int((k[c] != k[c + '_cat']).sum()) for c in ('event_date', 'time_block', 'province_key')}
    C.add('catalog carries accepted repaired date/time block/province unchanged', not any(bad.values()) and len(k) == len(ev), {}, bad)
    leg = read_str(BACKEND / I['legacy_descriptive'])
    C.add('legacy descriptive UIDs unique', leg['event_uid'].is_unique)
    L = O.merge(leg[['event_uid'] + fields], on='event_uid', how='left', suffixes=('', '_legacy'), validate='one_to_one', indicator=True)
    known = L['_merge'].eq('both')
    ref = cfg['recovery']['preflight_reference']
    cov = read_str(report_dir / 'recovery_coverage.csv').set_index('field')
    summary = {'events': len(L), 'legacy_matched': int(known.sum()), 'repaired_recovered': int((~known).sum()), 'unknown_before': {}, 'unknown_after': {}}
    for f in fields:
        conflicts = int((L.loc[known, f] != L.loc[known, f + '_legacy']).sum())
        C.add('legacy V1 ' + f + ' agrees with the raw oracle on every shared UID', conflicts == 0, 0, conflicts)
        before = int(((~known) | (L[f + '_legacy'].fillna('') == '')).sum())
        after = int((L[f] == '').sum())
        summary['unknown_before'][f], summary['unknown_after'][f] = before, after
        got = (int(cov.loc[f, 'unknown_before_recovery']), int(cov.loc[f, 'unknown_after_recovery']), int(cov.loc[f, 'legacy_value_conflicts']))
        C.add('catalog recovery_coverage.csv ' + f + ' == oracle (unknown before, after, conflicts)', got == (before, after, conflicts), (before, after, conflicts), got)
    C.add('oracle counts vs manager preflight reference (reference only)',
          (summary['events'], summary['legacy_matched'], summary['repaired_recovered'], summary['unknown_before'], summary['unknown_after']) ==
          (ref['events'], ref['legacy_matched'], ref['repaired_recovered'], ref['unknown_before'], ref['unknown_after']),
          {k: ref[k] for k in ('events', 'legacy_matched', 'repaired_recovered', 'unknown_after')},
          {k: summary[k] for k in ('events', 'legacy_matched', 'repaired_recovered', 'unknown_after')})
    st = L[['event_uid']].assign(expected=known.map({True: 'legacy_matched', False: 'repaired_recovered'})).merge(cat[['event_uid', 'legacy_status']], on='event_uid')
    C.add('catalog legacy_status == oracle legacy membership on every event', bool((st['expected'] == st['legacy_status']).all()) and len(st) == len(ev))
    return summary


# ---------- 3. province catalog ----------
def verify_province(cfg, I, ev, O, report_dir, C):
    fields, cats = list(cfg['recovery']['fields']), list(cfg['catalog']['categories'])
    P = read_str(BACKEND / I['province_points'])
    keys = sorted(P['province_key'])
    C.add('province points: expected unique provinces', len(keys) == int(cfg['catalog']['expected_provinces']) and len(set(keys)) == len(keys),
          int(cfg['catalog']['expected_provinces']), len(set(keys)))
    months = month_range(cfg['catalog']['first_month'], cfg['catalog']['last_month'])
    E = ev[['event_uid', 'event_date', 'time_block', 'province_key']].merge(O[['event_uid'] + fields], on='event_uid', validate='one_to_one')
    E = E.assign(year_month=E['event_date'].str[:7])
    outside = int((~E['province_key'].isin(set(keys)) | ~E['year_month'].isin(set(months))).sum())
    C.add('every accepted event inside the 77 provinces x catalog months', outside == 0, 0, outside)
    grid = pd.MultiIndex.from_product([keys, months], names=['province_key', 'year_month'])
    M = E.groupby(['province_key', 'year_month']).size().reindex(grid, fill_value=0).rename('n_records').to_frame()
    for c in cats:
        k = E[E[c] != ''].groupby(['province_key', 'year_month']).size().reindex(grid, fill_value=0)
        M['known_' + c] = k.to_numpy()
        M['unknown_' + c] = M['n_records'].to_numpy() - k.to_numpy()
    M = M.reset_index()
    PM = read_str(report_dir / 'province_monthly.csv')
    num = [c for c in M.columns if c not in ('province_key', 'year_month')]
    if sorted(PM.columns) == sorted(M.columns):
        PM = PM.astype({c: 'int64' for c in num})
        same = frames_equal(M.astype({c: 'int64' for c in num}), PM[list(M.columns)], ['province_key', 'year_month'])
    else:
        same = False
    C.add('province_monthly.csv == oracle (' + str(len(keys)) + ' x ' + str(len(months)) + ' grid, counts, known/unknown per category)', same, len(M), len(PM))
    C.add('province grid total == accepted events', int(M['n_records'].sum()) == len(ev), len(ev), int(M['n_records'].sum()))
    long = []
    for c in cats:
        g = E.groupby(['province_key', 'year_month', c]).size().rename('n_records').reset_index().rename(columns={c: 'value'})
        g.insert(2, 'category', c)
        long.append(g)
    Lx = pd.concat(long, ignore_index=True)
    PC = read_str(report_dir / 'province_category_monthly.csv')
    labels_ok = bool((PC['label_status'] == PC['value'].map(lambda v: 'unknown' if v == '' else 'known')).all())
    same_c = frames_equal(Lx, PC[list(Lx.columns)].astype({'n_records': 'int64'}), ['province_key', 'year_month', 'category', 'value'])
    C.add('province_category_monthly.csv == oracle category marginals (every province/month/category/value)', same_c and labels_ok, len(Lx), len(PC))
    return E, {'provinces': len(keys), 'months': len(months), 'grid_total': int(M['n_records'].sum()), 'zero_province_months': int((M['n_records'] == 0).sum())}


# ---------- 4. spatial catalog ----------
def verify_spatial(cfg, I, docs, E, O, data_dir, report_dir, C):
    fields = list(cfg['recovery']['fields'])
    rv = docs['spatial_review']
    S = read_str(BACKEND / I['selected_events'])
    uni = read_str(BACKEND / I['universe_segments'])['segment_id']
    C.add('selected rows == notebook-19 independent review', len(S) == int(rv.get('selected_events', -1)), rv.get('selected_events'), len(S))
    C.add('universe ids unique and == notebook-19 independent review', uni.is_unique and len(uni) == int(rv.get('universe_segments', -1)), rv.get('universe_segments'), len(uni))
    C.add('selected UIDs unique', S['event_uid'].is_unique)
    J = S.merge(E.merge(O[['event_uid', 'ce_year']], on='event_uid'), on='event_uid', how='left', suffixes=('', '_acc'), validate='one_to_one', indicator=True)
    C.add('every selected UID is an accepted recovered event', bool(J['_merge'].eq('both').all()), len(S), int(J['_merge'].eq('both').sum()))
    bad = {c: int((J[c] != J[c + '_acc']).sum()) for c in ('event_date', 'time_block', 'province_key', 'ce_year')}
    C.add('selected date/time block/province/year == accepted events', not any(bad.values()), {}, bad)
    C.add('selected segments are universe members', bool(J['segment_id_2000m'].isin(set(uni)).all()))
    R = J.rename(columns={'segment_id_2000m': 'segment_id'})[['segment_id', 'event_date', 'time_block', 'ce_year'] + fields].copy()
    d = R.groupby(['segment_id', 'event_date']).size().rename('y_count').reset_index().rename(columns={'event_date': 'target_date'})
    b = R.groupby(['segment_id', 'event_date', 'time_block']).size().rename('y_count').reset_index().rename(columns={'event_date': 'target_date'})
    for label, mine, rel, keys in (('daily', d, 'counts_daily', ['segment_id', 'target_date']), ('6h', b, 'counts_6h', ['segment_id', 'target_date', 'time_block'])):
        acc = read_str(BACKEND / I[rel])[keys + ['y_count']].astype({'y_count': 'int64'})
        C.add('oracle ' + label + ' recount == accepted notebook-19 ' + rel + ' (every cell)', frames_equal(mine, acc, keys), int(acc['y_count'].sum()), int(mine['y_count'].sum()))
    CR = read_str(data_dir / 'selected_history_rows.csv.gz')
    C.add('catalog row context columns are exactly the event-free set', sorted(CR.columns) == sorted(R.columns), sorted(R.columns), sorted(CR.columns))
    C.add('catalog row context == oracle selected rows (multiset, all columns)', sorted(CR.columns) == sorted(R.columns) and frames_equal(R, CR[list(R.columns)], list(R.columns)),
          len(R), len(CR))
    cu = read_str(data_dir / 'universe_segment_ids.csv')['segment_id']
    C.add('catalog universe ids == accepted notebook-19 universe', cu.is_unique and set(cu) == set(uni), len(uni), len(cu))
    seg = read_str(data_dir / 'segment_history_summary.csv').set_index('segment_id')
    n = R.groupby('segment_id').size().reindex(sorted(uni), fill_value=0)
    seg_ok = set(seg.index) == set(uni) and bool((seg.loc[n.index, 'n_selected_total'].astype('int64').to_numpy() == n.to_numpy()).all())
    st_ok = bool((seg['history_status'] == seg['n_selected_total'].astype('int64').map(lambda x: 'has_selected_history' if x > 0 else 'empty_selected_history_not_safety')).all())
    C.add('segment_history_summary.csv covers every universe id with oracle totals (empty history explicit)', seg_ok and st_ok, int(n.sum()), int(seg['n_selected_total'].astype('int64').sum()))
    rec = read_str(report_dir / 'spatial_reconciliation.csv')
    C.add('catalog spatial_reconciliation.csv all ok', bool((rec['ok'] == 'True').all()), len(rec), int((rec['ok'] == 'True').sum()))
    return R, {'selected': len(R), 'universe_segments': len(uni), 'segments_with_history': int((n > 0).sum()), 'daily_cells': len(d), 'six_hour_cells': len(b)}


# ---------- 5. catalog manifest and source hashes ----------
def verify_manifest(cfg, sha, raw_files, report_dir, data_dir, C):
    man = read_json(report_dir / 'catalog_manifest.json')
    C.add('catalog manifest complete, research-only, production_ready false',
          man.get('status') == 'complete' and man.get('research_only') is True and man.get('production_ready') is False, 'complete', man.get('status'))
    checks = man.get('checks') or []
    failed = [c.get('check') for c in checks if c.get('status') != 'pass']
    C.add('catalog manifest records every notebook check as pass', bool(checks) and not failed, [], failed[:10])
    outs = man.get('outputs') or {}
    bad = []
    for base, files in ((report_dir, outs.get('report_files') or {}), (data_dir, outs.get('data_files') or {})):
        for rel, h in sorted(files.items()):
            p = base.joinpath(*safe_rel(rel).parts)
            if p.is_symlink() or not p.is_file() or sha256_file(p) != h:
                bad.append(rel)
    C.add('every manifest report/data file hash matches', not bad and bool(outs.get('report_files')) and bool(outs.get('data_files')), [], bad[:10])
    need = {'province_monthly.csv', 'province_category_monthly.csv', 'query_examples.json', 'negative_controls.csv', 'readiness.csv', 'catalog_report_th.md',
            'serving_interface_th.md', 'figures/recovery_coverage.png', 'figures/selected_history_distribution.png'}
    C.add('required report files registered in the manifest', need <= set(outs.get('report_files') or {}), sorted(need), sorted(need - set(outs.get('report_files') or {})))
    C.add('manifest config sha256 == current config', man.get('config_sha256') == sha256_file(BACKEND / CONFIG_REL))
    nbp = BACKEND / cfg['notebook']
    nb = json.loads(nbp.read_text('utf-8'))
    cells = [(i, str(c.get('id', '')), ''.join(c['source']) if isinstance(c['source'], list) else c['source']) for i, c in enumerate(nb['cells']) if c['cell_type'] == 'code']
    funcs = [s for _, _, s in cells if s.lstrip().startswith('# FUNCTIONS')]
    fsha = hashlib.sha256('\n\n'.join(funcs).encode('utf-8')).hexdigest()
    csha = {str(i) + ':' + cid: hashlib.sha256(s.encode('utf-8')).hexdigest() for i, cid, s in cells}
    C.add('canonical notebook FUNCTIONS sha (text hash, not executed) == manifest', len(funcs) == 5 and fsha == man.get('functions_cells_sha256'), man.get('functions_cells_sha256'), fsha)
    C.add('canonical notebook code-cell hashes == manifest', csha == man.get('code_cells_sha256'))
    C.add('canonical notebook source sha == manifest source sha at start', sha256_file(nbp) == man.get('notebook_source_sha256_at_start'))
    msha = {r.get('input'): r.get('sha256') for r in man.get('inputs') or []}
    C.add('manifest input hashes == verified pinned inputs', msha == sha, len(sha), len(msha))
    rsha = {r.get('source_file'): r.get('raw_sha256') for r in man.get('raw_sources') or []}
    C.add('manifest raw source hashes == independently verified raw CSVs', rsha == {f: v['sha256'] for f, v in raw_files.items()}, len(raw_files), len(rsha))
    prot = man.get('protected_snapshot') or {}
    C.add('protected snapshot unchanged before/after the run', prot.get('changed') == [] and prot.get('before_sha256') == prot.get('after_sha256'), [], prot.get('changed'))
    neg = read_str(report_dir / 'negative_controls.csv')
    C.add('negative_controls.csv: every control ok', bool(len(neg)) and bool((neg['ok'] == 'True').all()), len(neg), int((neg['ok'] == 'True').sum()))
    return man


# ---------- 6. query examples re-derived ----------
def _top(vals, top_k):
    known = {}
    unknown = 0
    for v in vals:
        if v == '':
            unknown += 1
        else:
            known[v] = known.get(v, 0) + 1
    ordered = sorted(known.items(), key=lambda t: (-t[1], t[0]))
    return sum(known.values()), unknown, [list(t) for t in ordered[:top_k]]


def verify_examples(cfg, E, R, report_dir, C):
    Q, cats, blocks = cfg['query'], list(cfg['catalog']['categories']), list(cfg['catalog']['time_blocks'])
    ex = read_json(report_dir / 'query_examples.json')
    C.add('query examples present', bool(ex), '>=1', len(ex))
    by_seg = {k: g.to_dict('records') for k, g in R.groupby('segment_id')}
    for name, item in sorted(ex.items()):
        req, res = item['request'], item['response']
        top_k = int(req.get('top_k', Q['default_top_k']))
        if 'segment_id' in req:
            td = dt.datetime.fromisoformat(req['target_date'])
            issue = td + dt.timedelta(days=int(Q['issue_day_offset']), hours=int(Q['issue_hour_local']))
            cutoff = issue - dt.timedelta(days=int(Q['latency_days']))
            start = cutoff - dt.timedelta(days=int(req.get('lookback_days', Q['default_lookback_days'])))
            sel = []
            for r in by_seg.get(req['segment_id'], []):
                d = dt.datetime.fromisoformat(r['event_date'])
                end = d + (dt.timedelta(days=1) if req['unit'] == 'daily' else dt.timedelta(hours=int(r['time_block'][3:5])))
                if start < end <= cutoff:
                    sel.append(r)
            exp = {'n': len(sel), 'issue': issue.isoformat() + '+07:00', 'cutoff': cutoff.isoformat() + '+07:00',
                   'blocks': {b: sum(1 for r in sel if r['time_block'] == b) for b in blocks},
                   'years': {y: n for y, n in sorted(pd.Series([r['event_date'][:4] for r in sel], dtype=object).value_counts().items())}}
            got = {'n': res.get('n_selected_records'), 'issue': res.get('issue_time_local'), 'cutoff': res.get('history_cutoff_local'),
                   'blocks': res.get('counts_by_time_block'), 'years': {k: v for k, v in sorted((res.get('counts_by_year') or {}).items())}}
            ok = exp == got
            if req['unit'] == '6h':
                ok = ok and res.get('n_same_time_block') == exp['blocks'][req['time_block']]
            for c in (res.get('categories') or {}):
                k, u, top = _top([r[c] for r in sel], top_k)
                blk = res['categories'][c]
                ok = ok and (blk.get('known_records'), blk.get('unknown_records'), [[t['value'], t['records']] for t in blk.get('top_values', [])]) == (k, u, top)
            ok = ok and set(res.get('categories') or {}) == set(req.get('categories', cats))
            C.add('as-of example ' + name + ' re-derived (N, issue/cutoff, block/year counts, category known/unknown/top values)', ok,
                  {'n': exp['n'], 'cutoff': exp['cutoff']}, {'n': got['n'], 'cutoff': got['cutoff']})
        else:
            months = month_range(req['start_month'], req['end_month'])
            g = E[(E['province_key'] == req['province_key']) & E['year_month'].isin(set(months))]
            vc = g['year_month'].value_counts()
            ok = res.get('total_records') == len(g) and [[m['year_month'], m['records']] for m in res.get('months', [])] == [[m, int(vc.get(m, 0))] for m in months]
            ok = ok and res.get('as_of_cutoff') is None
            for c in (res.get('categories') or {}):
                k, u, top = _top(g[c].tolist(), top_k)
                blk = res['categories'][c]
                ok = ok and (blk.get('known_records'), blk.get('unknown_records'), [[t['value'], t['records']] for t in blk.get('top_values', [])]) == (k, u, top)
            C.add('retrospective province example ' + name + ' re-derived (monthly counts, total, category marginals, not as-of)', ok, len(g), res.get('total_records'))


# ---------- 7. served-file privacy scan ----------
def verify_no_leaks(ev, report_dir, data_dir, C):
    count = uid_counter(ev['event_uid'].tolist())
    hits, cols = {}, {}
    files = [p for p in sorted(report_dir.rglob('*')) if p.is_file() and p.suffix in ('.csv', '.json', '.md')]
    files += [p for p in sorted(data_dir.iterdir()) if p.is_file() and p.name != PROVENANCE_DATA_FILE]
    for p in files:
        raw = p.read_bytes()
        text = (gzip.decompress(raw) if p.name.endswith('.gz') else raw).decode('utf-8')
        n = count(text)
        if n:
            hits[p.name] = n
        if '.csv' in p.name:
            header = set(text.split('\n', 1)[0].strip().split(','))
            bad = sorted(header & REPORT_EVENT_COLUMNS)
            if bad:
                cols[p.name] = bad
    C.add('no retained event UID (exact match against ' + str(len(ev)) + ') in any served report/data file (' + str(len(files)) + ' files)', not hits, {}, hits)
    C.add('no event-level column (UID/source row/coordinates/time_sec) in any served CSV', not cols, {}, cols)


# ---------- CLI ----------
def _inside(child, parent):
    c, p = Path(os.path.abspath(child)), Path(os.path.abspath(parent))
    if c == p or p in c.parents:
        return True
    c, p = c.resolve(), p.resolve()
    return c == p or p in c.parents


def output_refusal(out, cfg, root):
    out = Path(os.path.abspath(out))
    if os.path.lexists(out):
        return 'refusing --output ' + str(out) + ': it already exists (evidence files are never overwritten)'
    if out.suffix != '.json':
        return 'refusing --output ' + str(out) + ': must be a .json file'
    rels = cfg['protected_paths'] + cfg['readonly_hashed_paths'] + cfg['write_guard_paths'] + [v['path'] for v in cfg['inputs'].values()]
    guarded = [BACKEND / r for r in rels] + [REPO / r for r in cfg['repo_write_guard_paths']]
    guarded += [REPO / cfg['pins']['path'], BACKEND / CONFIG_REL, BACKEND / cfg['notebook'], BACKEND / cfg['outputs']['report_dir'], BACKEND / cfg['outputs']['data_dir'],
                root / cfg['outputs']['report_dir'], root / cfg['outputs']['data_dir']]
    for g in guarded:
        if _inside(out, g):
            return 'refusing --output ' + str(out) + ': inside protected/guarded path ' + str(g)
    if not _inside(out, REPO):
        return 'refusing --output ' + str(out) + ': must be inside the repository'
    for a in out.parents:
        if a == REPO:
            break
        if os.path.islink(a):
            return 'refusing --output ' + str(out) + ': symlinked path component ' + str(a)
    return None


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--catalog-root', required=True, help='run root holding the catalog outputs, e.g. backend/rerun-historical-catalog-020-003')
    ap.add_argument('--output', help='optional NEW .json evidence path (aggregate counts/hashes only)')
    return ap.parse_args(argv)


def main(argv=None):
    a = parse_args(argv)
    cfg = read_json(BACKEND / CONFIG_REL)
    root = Path(os.path.abspath(a.catalog_root))
    report_dir, data_dir = root / cfg['outputs']['report_dir'], root / cfg['outputs']['data_dir']
    if not report_dir.is_dir() or not data_dir.is_dir():
        print('catalog report/data dirs not found under ' + str(root), file=sys.stderr)
        return 2
    if a.output:
        why = output_refusal(a.output, cfg, root)
        if why:
            print(why, file=sys.stderr)
            return 2
    C = Checks()
    started = dt.datetime.now(dt.timezone.utc).isoformat()
    summary = {}
    got = C.section('inputs', verify_inputs, cfg, C)
    if got:
        I, sha, docs = got
        orc = C.section('raw oracle', oracle_recovery, cfg, I, docs, C)
        if orc:
            ev, O, raw_files = orc
            summary['recovery'] = C.section('catalog recovery vs oracle and legacy', compare_catalog_recovery, cfg, I, ev, O, data_dir, report_dir, C)
            prov = C.section('province', verify_province, cfg, I, ev, O, report_dir, C)
            if prov:
                E, summary['province'] = prov
                sp = C.section('spatial', verify_spatial, cfg, I, docs, E, O, data_dir, report_dir, C)
                if sp:
                    R, summary['spatial'] = sp
                    C.section('query examples', verify_examples, cfg, E, R, report_dir, C)
            man = C.section('manifest', verify_manifest, cfg, sha, raw_files, report_dir, data_dir, C)
            if man:
                summary['catalog_manifest'] = {'status': man.get('status'), 'functions_cells_sha256': man.get('functions_cells_sha256'),
                                               'manifest_sha256': sha256_file(report_dir / 'catalog_manifest.json')}
            C.section('privacy scan', verify_no_leaks, ev, report_dir, data_dir, C)
    ok = bool(C.rows) and all(r['ok'] for r in C.rows)
    n_fail = sum(1 for r in C.rows if not r['ok'])
    print(('[pass] ' if ok else '[FAIL] ') + str(len(C.rows)) + ' checks, ' + str(n_fail) + ' failed', flush=True)
    if a.output:
        rel = lambda p: os.path.relpath(p, REPO)
        ev_json = {'schema': SCHEMA, 'status': 'pass' if ok else 'fail', 'started_utc': started, 'finished_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
                   'verifier': {'path': rel(Path(__file__).resolve()), 'sha256': sha256_file(Path(__file__).resolve())},
                   'catalog_root': rel(root), 'config_sha256': sha256_file(BACKEND / CONFIG_REL), 'checks': C.rows, 'n_checks': len(C.rows), 'n_failed': n_fail,
                   'summary': summary, 'not_run': NOT_RUN,
                   'independence': 'no notebook-14 code imported or executed; raw recovery re-derived from pinned raw CSVs + retained lineage; '
                                   'oracle logic modelled on the disclosed manager preflight (development aid only, not read at runtime)'}
        out = Path(os.path.abspath(a.output))
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, 'x', encoding='utf-8') as f:
            f.write(json.dumps(ev_json, indent=2, ensure_ascii=False, allow_nan=False) + '\n')
        print('evidence written to ' + str(out), flush=True)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
