"""Independent verifier for a notebook-22 run (spatial inference contract). Usage from the repository root:
    .venv/bin/python backend/scripts/verify_spatial_inference.py --run-root backend/rerun-spatial-serving-018-001 [--no-live] [--save <new evidence.json>]

Re-derives with its own arithmetic (no notebook-22 FUNCTIONS except the optional --live public-API probe):
  * manifest status/readiness, every report/data file hash, manager pins unchanged and every pinned file hash;
  * full 2024/25 populations: runtime selected/baseline/mask arrays vs the hash-verified saved notebook-20 diag arrays (max abs error, streamed);
  * segment_mean_k365 recomputed from the pinned 19 count CSVs, universe lengths/routes and the 20 benchmark cutoff (pandas group sums), compared
    with the persisted serving statistics AND with every cell of the saved 20 diag baseline array;
  * OOF routing arithmetic: where(mask, context, core) from the saved 20 OOF arrays -> pooled mean Poisson deviance (xlogy, floor 1e-12) vs the
    frozen selection; baseline OOF deviance likewise (arrays only; no OOF model replay is claimed);
  * prediction fixtures: response order == request order, seen rows == saved 20 values at their offsets, research flags by date, colour bands
    recomputed from the pinned contract cutoffs and segment km;
  * --live (default): load_service from the run's serving record and pins, fresh deterministic requests (own seed) through predict_batch /
    predict_baseline_batch vs the saved arrays, plus invalid/coverage probes.
Exit 0 only when every check passes.
"""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
CFG = json.loads((BACKEND / 'config' / 'spatial_inference_v3.json').read_text('utf-8'))
RESULTS = []


def v(name, ok, evidence=None):
    RESULTS.append({'check': name, 'passed': bool(ok), 'evidence': evidence})
    print(('PASS ' if ok else 'FAIL ') + name + ('' if ok else ' | ' + str(evidence)[:400]), flush=True)


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def jload(p):
    return json.loads(Path(p).read_text('utf-8'), parse_constant=lambda c: (_ for _ in ()).throw(ValueError('non-finite ' + c)))


def deviance_mean(y, mu, floor=1e-12, chunk=1 << 21):
    from scipy.special import xlogy
    s, n = 0.0, len(y)
    for a in range(0, n, chunk):
        yy, m = np.asarray(y[a:a + chunk], float), np.maximum(np.asarray(mu[a:a + chunk], float), floor)
        s += float((2.0 * (xlogy(yy, yy) - xlogy(yy, m) - (yy - m))).sum())
    return s / n


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--run-root', required=True)
    ap.add_argument('--no-live', action='store_true')
    ap.add_argument('--save')
    a = ap.parse_args(argv)
    root = Path(a.run_root).resolve()
    rep, dat = root / CFG['outputs']['report_dir'], root / CFG['outputs']['data_dir']
    man = jload(rep / 'spatial_serving_manifest.json')
    v('manifest complete, no failed checks, research_ready true, production_ready/serving_deployed false',
      man['status'] == 'complete' and not man['failed_checks'] and man['readiness']['research_ready'] is True
      and man['readiness']['production_ready'] is False and man['readiness']['serving_deployed'] is False, man['readiness'])
    bad = [k for k, h in man['report_files'].items() if sha(rep / k) != h]
    v('every report file hash equals the manifest', not bad, bad)
    bad = [k for k, h in man['data_files_gitignored'].items() if sha(dat / k) != h]
    v('every data file hash equals the manifest', not bad, bad)
    pins_path = BACKEND / CFG['pins']['path']
    pins = jload(pins_path)
    v('manager pins file unchanged since the run', sha(pins_path) == man['pins_sha256'] and pins == man['pins'])
    badp = [k for k, h in pins['files'].items() if not (REPO / k).is_file() or sha(REPO / k) != h]
    v('every manager-pinned file still matches its pin', not badp, badp)
    v('protected paths unchanged during the run', man['protected_unchanged'] is True and not man['protected_changed'])
    I = CFG['inputs']
    rep20 = BACKEND / I['experiment_root'] / I['experiment_report_dir']
    dat20 = BACKEND / I['experiment_root'] / I['experiment_data_dir']
    m20, idx = jload(rep20 / 'spatial_experiments_manifest.json'), jload(dat20 / 'arrays_index.json')
    sel = jload(rep20 / 'selection_frozen.json')
    d20 = m20['data_files_gitignored']
    prep = BACKEND / I['prepared_data_dir']
    m19 = jload(BACKEND / I['manifest19'])
    axj = jload(prep / 'population_axes.json')
    v('19 axes/universe/count files match the pinned 19 manifest',
      all(sha(prep / n) == m19['data_files_gitignored'][n] for n in ('population_axes.json', 'universe_segments.csv', 'counts_daily.csv.gz', 'counts_6h.csv.gz')))
    segs = axj['segments']
    S = len(segs)
    useg = pd.read_csv(prep / 'universe_segments.csv', dtype={'segment_id': str, 'route_code': str}, float_precision='round_trip').set_index('segment_id').loc[segs]
    km = useg['geom_length_m'].to_numpy(float) / 1000.0
    tol = float(CFG['serving']['parity_abs_tolerance'])
    cut = pd.Timestamp(CFG['artifact']['training_label_cutoff_local'])
    start = pd.Timestamp(axj['dates'][0])
    for u in ('daily', '6h'):
        blocks = axj['blocks'] if u == '6h' else ['day']
        nb = len(blocks)
        selm, base = pins['selection'][u], pins['selection']['baseline']
        diag = idx['units'][u]['diag']

        def saved(name):
            f = diag[name]['file']
            ok = sha(dat20 / 'arrays' / f) == d20['arrays/' + f] == diag[name]['sha256']
            return np.load(dat20 / 'arrays' / f, mmap_mode='r', allow_pickle=False), ok
        rt = man['runtime_arrays'][u]
        load_rt = lambda k: np.load(dat / 'parity' / rt[k]['file'], mmap_mode='r', allow_pickle=False)
        hs = [sha(dat / 'parity' / rt[k]['file']) == rt[k]['sha256'] for k in ('selected', 'baseline', 'context_mask')]
        for k, name in (('selected', selm), ('baseline', base)):
            sv, ok = saved(name)
            r = load_rt(k)
            err = 0.0
            for i in range(0, len(sv), 1 << 21):
                err = max(err, float(np.max(np.abs(np.asarray(r[i:i + (1 << 21)], float) - np.asarray(sv[i:i + (1 << 21)], float)))))
            v(u + ' full 2024/25 runtime ' + k + ' == saved 20 ' + name + ' (max abs error ' + repr(err) + ')',
              ok and all(hs) and len(r) == len(sv) and err <= tol, {'rows': len(sv), 'max_abs_error': err})
        sm, ok = saved('context_mask')
        rm = load_rt('context_mask')
        mism = int(sum(int((np.asarray(rm[i:i + (1 << 22)]) != np.asarray(sm[i:i + (1 << 22)])).sum()) for i in range(0, len(sm), 1 << 22)))
        v(u + ' runtime routing mask == saved 20 context mask on every cell', ok and mism == 0, mism)
        # independent segment_mean_k365 from pinned labels
        cnt = pd.read_csv(prep / ('counts_' + u + '.csv.gz'), dtype={'segment_id': str, 'target_date': str, 'time_block': str})
        ends = [24] if u == 'daily' else [int(b.split('-')[1]) for b in blocks]
        T = np.array([((cut - pd.Timedelta(hours=h)).normalize() - start).days + 1 for h in ends], float)
        di = (pd.to_datetime(cnt['target_date'], format='%Y-%m-%d') - start).dt.days.to_numpy()
        bi = np.zeros(len(cnt), int) if u == 'daily' else pd.Index(blocks).get_indexer(cnt['time_block'])
        si = pd.Index(segs).get_indexer(cnt['segment_id'])
        keep = di < T[bi]
        C = np.zeros((S, nb))
        np.add.at(C, (si[keep], bi[keep]), cnt['y_count'].to_numpy(float)[keep])
        route = useg['route_code'].to_numpy(str)
        rC = pd.DataFrame(C).groupby(route).sum()
        rL = pd.Series(km).groupby(route).sum()
        P = (rC.loc[route].to_numpy() / (rL.loc[route].to_numpy()[:, None] * T[None, :])) * km[:, None]
        k = float(base.rsplit('k', 1)[1])
        table = (C + k * P) / (T[None, :] + k)
        st = np.load(dat / ('baseline_stats_' + u + '.npz'), allow_pickle=False)
        e1 = float(np.max(np.abs(st['table'] - table) / np.maximum(1.0, np.abs(table))))
        v(u + ' persisted ' + base + ' statistics == independent recomputation from pinned labels (rel err ' + repr(e1) + ')',
          st['segments'].tolist() == segs and e1 <= 1e-12, e1)
        sb, _ = saved(base)
        days = len(sb) // (S * nb)
        e2 = 0.0
        for d0 in range(0, days, 64):
            blk = np.asarray(sb[d0 * S * nb:min(days, d0 + 64) * S * nb], float).reshape(-1, S, nb)
            e2 = max(e2, float(np.max(np.abs(blk - table[None]))))
        v(u + ' every saved 20 diag baseline cell == independent table (max abs ' + repr(e2) + ')', e2 <= tol, e2)
        # OOF routing arithmetic (arrays only)
        oof = idx['units'][u]['oof']
        cid = selm.split('::')[0]
        ld = lambda name: np.load(dat20 / 'arrays' / oof[name]['file'], mmap_mode='r', allow_pickle=False)
        okh = all(sha(dat20 / 'arrays' / oof[n]['file']) == d20['arrays/' + oof[n]['file']] for n in (cid + '::core', cid + '::context', 'context_mask', 'y', base))
        y, mk = ld('y'), ld('context_mask')
        routed = np.where(np.asarray(mk) == 1, np.asarray(ld(cid + '::context')), np.asarray(ld(cid + '::core')))
        dv, dvb = deviance_mean(y, routed), deviance_mean(y, ld(base))
        su = sel['units'][u]
        v(u + ' OOF routed deviance from arrays == frozen selection (' + repr(dv) + ')',
          okh and math.isclose(dv, su['candidate_pooled']['mean_poisson_deviance'], rel_tol=1e-9), [dv, su['candidate_pooled']['mean_poisson_deviance']])
        v(u + ' OOF baseline deviance from arrays == frozen selection', math.isclose(dvb, su['baseline_pooled']['mean_poisson_deviance'], rel_tol=1e-9),
          [dvb, su['baseline_pooled']['mean_poisson_deviance']])
        del routed
    # prediction fixtures
    fx = jload(dat / 'prediction_fixtures.json')
    rep21 = BACKEND / I['evaluation_root'] / I['evaluation_report_dir']
    kmap = dict(zip(segs, km))
    for u in ('daily', '6h'):
        sel_arr = np.load(dat20 / 'arrays' / idx['units'][u]['diag'][pins['selection'][u]]['file'], mmap_mode='r', allow_pickle=False)
        base_arr = np.load(dat20 / 'arrays' / idx['units'][u]['diag'][pins['selection']['baseline']]['file'], mmap_mode='r', allow_pickle=False)
        cuts = np.asarray(jload(rep21 / ('colour_contract_' + u + '.json'))['raw_cutoffs'], float)
        offs = {(r['segment_id'], r['target_date'], r.get('time_block')): int(r['diag_offset']) for r in fx[u]['requests']}
        errs, order_bad, flag_bad, colour_bad, n_seen = 0.0, 0, 0, 0, 0
        for item in fx[u]['responses']:
            res = item['response']
            for q, out in zip(item['requests'], res['results']):
                order_bad += int((q['segment_id'], q['target_date'], q.get('time_block')) != (out['segment_id'], out['target_date'], out['time_block']))
                o = offs[(q['segment_id'], q['target_date'], q.get('time_block'))]
                flag_bad += int(out['research_scenario'] != (q['target_date'] > CFG['artifact']['observed_diagnostic_end']))
                if o >= 0:
                    n_seen += 1
                    errs = max(errs, abs(out['expected_recorded_count'] - float((sel_arr if item['which'] == 'selected' else base_arr)[o])))
                if item['which'] == 'selected':
                    dens = out['expected_recorded_count'] / kmap[out['segment_id']]
                    colour_bad += int(out['colour'] != ('base', 'yellow', 'orange', 'red')[int((cuts < dens).sum())])
        v(u + ' fixtures: order preserved, seen rows == saved 20 at offsets, research flags, colour bands from pinned cutoffs',
          order_bad == 0 and flag_bad == 0 and colour_bad == 0 and n_seen > 0 and errs <= tol,
          {'order_bad': order_bad, 'flag_bad': flag_bad, 'colour_bad': colour_bad, 'seen': n_seen, 'max_abs_error': errs})
    for name in ('robustness_cases.csv', 'tamper_cases.csv'):
        d = pd.read_csv(rep / name)
        v(name + ' all passed', len(d) > 0 and bool(d['passed'].all()), d[~d['passed']].to_dict('records'))
    sy = pd.read_csv(rep / 'synthetic_routing_fixture_NOT_observed.csv', float_precision='round_trip')
    want_comp = np.where(sy['kind'] == 'context_complete', 'context', 'core')
    want_lam = np.where(want_comp == 'context', sy['context_prediction'], sy['core_prediction'])
    v('synthetic routing fixture: every row labelled SYNTHETIC (not observed), both components per unit, component/output follow the designed row kind',
      len(sy) > 0 and bool(sy['evidence'].str.startswith('SYNTHETIC_FIXTURE').all()) and bool((sy['component_used'] == want_comp).all())
      and float(np.max(np.abs(sy['expected_recorded_count'] - want_lam))) <= tol and bool((sy['baseline_component'] == 'baseline').all())
      and all({'context', 'core'} <= set(g['component_used']) for _, g in sy.groupby('unit')) and set(sy['unit']) == {'daily', '6h'},
      {'rows': len(sy)})
    lat = pd.read_csv(rep / 'latency.csv')
    v('latency rows exist for batch 1 and 128 (actual measurements)', set(lat['batch_size']) == {1, 128} and bool((lat['ms_median'] > 0).all()))
    if not a.no_live:
        live(root, man, pins, idx, dat20, tol)
    nfail = sum(not r['passed'] for r in RESULTS)
    print(str(len(RESULTS) - nfail) + '/' + str(len(RESULTS)) + ' independent checks passed')
    if a.save:
        out = Path(a.save)
        if out.exists():
            sys.exit('refusing to overwrite ' + str(out))
        out.write_text(json.dumps({'run_root': str(root), 'results': RESULTS}, indent=2, default=str), 'utf-8')
    return 1 if nfail else 0


def live(root, man, pins, idx, dat20, tol):
    """Public-path probe with the run's own trusted serving record; requests drawn here (seed 9917) and compared with saved 20 arrays."""
    nb = json.loads((BACKEND / CFG['notebook']).read_text('utf-8'))
    ns = {}
    for s in [''.join(c['source']) for c in nb['cells'] if c['cell_type'] == 'code' and ''.join(c['source']).lstrip().startswith('# FUNCTIONS')]:
        exec(compile(s, 'nb22:FUNCTIONS', 'exec'), ns)
    dat = root / CFG['outputs']['data_dir']
    bf = {u: (dat / r['file'], r['sha256']) for u, r in man['baseline_stats'].items()}
    svc = ns['load_service'](BACKEND, CFG, pins, bf)
    v('live: load_service available from trusted pins + recorded baseline stats', svc['status'] == 'available', svc['error'] and dict(svc['error']))
    if svc['status'] != 'available':
        return
    axj = jload(BACKEND / CFG['inputs']['prepared_data_dir'] / 'population_axes.json')
    segs, dates = axj['segments'], axj['dates']
    d0 = dates.index('2024-01-01')
    rng = np.random.default_rng(9917)
    for u in ('daily', '6h'):
        nbk = len(axj['blocks']) if u == '6h' else 1
        sel = np.load(dat20 / 'arrays' / idx['units'][u]['diag'][pins['selection'][u]]['file'], mmap_mode='r', allow_pickle=False)
        base = np.load(dat20 / 'arrays' / idx['units'][u]['diag'][pins['selection']['baseline']]['file'], mmap_mode='r', allow_pickle=False)
        off = np.sort(rng.choice(len(sel), 256, replace=False))
        reqs = []
        for o in off:
            d, rem = divmod(int(o), len(segs) * nbk)
            s, b = divmod(rem, nbk)
            reqs.append({'segment_id': segs[s], 'target_date': dates[d0 + d], **({'time_block': axj['blocks'][b]} if u == '6h' else {})})
        err = 0.0
        for a in range(0, 256, 128):
            for fn, ref in (('predict_batch', sel), ('predict_baseline_batch', base)):
                r = ns[fn](svc, u, reqs[a:a + 128])
                json.dumps(r, allow_nan=False)
                if not r['ok']:
                    err = math.inf
                    continue
                err = max(err, max(abs(x['expected_recorded_count'] - float(ref[o])) for x, o in zip(r['results'], off[a:a + 128])))
        v('live ' + u + ': 256 fresh requests via public API == saved 20 arrays (max abs ' + repr(err) + ')', err <= tol, err)
        probes = {'invalid_unit': ns['predict_batch'](svc, 'hourly', reqs[:1]), 'batch_size': ns['predict_batch'](svc, u, reqs[:129] if len(reqs) > 128 else reqs * 2),
                  'unknown_segment': ns['predict_batch'](svc, u, [dict(reqs[0], segment_id='x')]),
                  'date_before_artifact_asof': ns['predict_batch'](svc, u, [dict(reqs[0], target_date='2022-05-05')]),
                  'invalid_value': ns['predict_baseline_batch'](svc, u, [dict(reqs[0], target_date=False)])}
        got = {k: (r.get('error') or {}).get('code') for k, r in probes.items()}
        v('live ' + u + ': invalid/coverage/as-of probes return their explicit codes', all(k == g for k, g in got.items()), got)
        # multi-row batches mixing good/bad rows (incl. row 0 and 2+ bad rows): expected code/family/rows fixed HERE, whole batch refused
        q = lambda i, **kw: dict(reqs[i], **kw)
        multi = [('before_asof_rows_0_2', [q(0, target_date='2023-12-31'), q(1), q(2, target_date='2022-05-05'), q(3)], 'date_before_artifact_asof', 'invalid', [0, 2]),
                 ('before_asof_row_0_only', [q(0, target_date='2023-01-01'), q(1)], 'date_before_artifact_asof', 'invalid', [0]),
                 ('after_2027_rows_1_3', [q(0), q(1, target_date='2028-01-01'), q(2), q(3, target_date='2031-01-01')], 'date_out_of_range', 'invalid', [1, 3]),
                 ('unknown_segment_rows_0_1', [q(0, segment_id='x-a'), q(1, segment_id='x-b'), q(2)], 'unknown_segment', 'coverage', [0, 1]),
                 ('duplicate_rows_2_3', [q(0), q(1), q(0), q(1)], 'duplicate_keys', 'invalid', [2, 3])]
        bad = []
        for name, batch, code, fam, rows in multi:
            for fn in ('predict_batch', 'predict_baseline_batch'):
                r = ns[fn](svc, u, batch)
                json.dumps(r, allow_nan=False)
                e = r.get('error') or {}
                if r.get('ok') is not False or 'results' in r or e.get('code') != code or e.get('family') != fam or list(e.get('rows') or []) != rows:
                    bad.append({'probe': name, 'fn': fn, 'ok': r.get('ok'), 'code': e.get('code'), 'family': e.get('family'), 'rows': e.get('rows')})
        v('live ' + u + ': multi-row invalid/coverage batches refused atomically with stable code/family and exact row positions (selected + baseline)',
          not bad, bad)


if __name__ == '__main__':
    sys.exit(main())
