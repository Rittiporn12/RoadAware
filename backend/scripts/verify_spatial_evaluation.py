"""Independent, read-only verifier for a notebook-21 run (development evidence; never imported by the notebook or any application).

Usage (from the repository root):
    .venv/bin/python backend/scripts/verify_spatial_evaluation.py --run-root backend/rerun-spatial-eval-017-001 [--save <new evidence.json>]

Re-derives, with its own arithmetic (no notebook FUNCTIONS, no producer metric/threshold/capture code):
  * manifest status, every report-file hash, config/pins hashes, FUNCTIONS-cell count/hash of the source notebook;
  * every consumed accepted-20 array hash (arrays_index + accepted manifest), routed policy derived from mask/components when not stored;
  * colour cutoffs = type-7 quantiles of the selected OOF density computed by explicit sort/interpolation, and the reference band counts;
  * pooled / per-period / per-colour totals (cells, records, predictions, deviance sums, segment-km exposure) and calibration-bin sums;
  * equal-road-km capture shares by an explicit per-period loop;
  * that no report CSV carries row-level (segment x date) outcomes.
Writes nothing unless --save names a NEW file (aggregate evidence only). Exit 0 = all checks pass, 1 = a check failed.
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
CONFIG = BACKEND / 'config' / 'spatial_evaluation_v3.json'


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def jload(p):
    return json.loads(Path(p).read_text('utf-8'))


def q7(sorted_x, q):
    n = sorted_x.size
    h = (n - 1) * q
    lo = int(math.floor(h))
    hi = min(lo + 1, n - 1)
    return float(sorted_x[lo] + (h - lo) * (sorted_x[hi] - sorted_x[lo]))


def unit_dev(y, mu, floor):
    m = np.maximum(mu, floor)
    out = 2.0 * m
    pos = y > 0
    out[pos] = 2.0 * (y[pos] * np.log(y[pos] / m[pos]) - y[pos] + m[pos])
    return out


class V:
    def __init__(self):
        self.checks = []

    def __call__(self, name, ok, evidence=None):
        self.checks.append({'check': name, 'ok': bool(ok), 'evidence': evidence})
        print(('PASS ' if ok else 'FAIL ') + name + ('' if ok else '  ' + str(evidence)[:400]), flush=True)


def close(a, b, rtol=1e-9, atol=1e-12):
    return a is not None and b is not None and not (isinstance(b, float) and math.isnan(b)) and math.isclose(float(a), float(b), rel_tol=rtol, abs_tol=atol)


def verify(run_root):
    cfg = jload(CONFIG)
    v = V()
    I = cfg['inputs']
    rep = Path(run_root) / cfg['outputs']['report_dir']
    man = jload(rep / 'spatial_evaluation_manifest.json')
    v('manifest status complete and no failed checks', man.get('status') == 'complete' and not man.get('failed_checks'), man.get('failed_checks'))
    bad = {k: h for k, h in man['report_files'].items() if sha(rep / k) != h}
    v('every report file hash equals the manifest', not bad, bad)
    v('config hash equals the manifest', sha(CONFIG) == man['config_sha256'])
    pins = jload(BACKEND / cfg['pins']['path'])
    v('pins file hash equals the manifest', sha(BACKEND / cfg['pins']['path']) == man['pins_sha256'])
    badp = {k: h for k, h in pins['files'].items() if sha(BACKEND.parent / k) != h}
    v('every manager-pinned file still matches its pin', not badp, badp)
    nb = jload(BACKEND / cfg['notebook'])
    fsrc = [''.join(c['source']) for c in nb['cells'] if c['cell_type'] == 'code' and ''.join(c['source']).lstrip().startswith('# FUNCTIONS')]
    v('source notebook: four FUNCTIONS cells, hash equals manifest, unexecuted',
      len(fsrc) == 4 and hashlib.sha256(''.join(fsrc).encode('utf-8')).hexdigest() == man['functions_sha256']
      and all(not c.get('outputs') and c.get('execution_count') is None for c in nb['cells'] if c['cell_type'] == 'code'), len(fsrc))

    root = BACKEND / I['accepted_root']
    dat = root / I['data_dir20']
    m20 = jload(root / I['report_dir20'] / 'spatial_experiments_manifest.json')
    idx = jload(dat / 'arrays_index.json')
    sel = jload(root / I['report_dir20'] / 'selection_frozen.json')['units']
    ax = jload(BACKEND / I['prepared_data_dir'] / 'population_axes.json')
    segs = pd.read_csv(BACKEND / I['prepared_data_dir'] / 'universe_segments.csv', dtype={'segment_id': str})
    L = segs.set_index('segment_id').loc[ax['segments'], 'geom_length_m'].to_numpy(float)
    S = L.size
    floor = float(cfg['metrics']['deviance_floor'])
    met = pd.read_csv(rep / 'metrics_by_group.csv', float_precision='round_trip', dtype={'group': str})
    cap = pd.read_csv(rep / 'capture_equal_road_km.csv', float_precision='round_trip')
    evidence = {}

    def arr(unit, scope, name):
        meta = idx['units'][unit][scope][name]
        rel = 'arrays/' + ('transfer/' if scope == 'transfer' else '') + meta['file']
        h = sha(dat / rel)
        if h != meta['sha256'] or h != m20['data_files_gitignored'].get(rel):
            raise SystemExit('array hash mismatch ' + rel)
        a = np.load(dat / rel, mmap_mode='r', allow_pickle=False)
        if str(a.dtype) != meta['dtype'] or list(a.shape) != meta['shape']:
            raise SystemExit('array dtype/shape mismatch ' + rel)
        return np.asarray(a)

    def method(unit, scope, m):
        stored = idx['units'][unit][scope]
        if m in stored:
            return arr(unit, scope, m).astype(np.float64)
        cid = m.split('::')[0]
        mask = arr(unit, scope, 'context_mask')
        return np.where(mask == 1, arr(unit, scope, cid + '::context'), arr(unit, scope, cid + '::core')).astype(np.float64)

    for u in cfg['units']:
        nbk = 1 if u == 'daily' else len(cfg['time']['blocks_6h'])
        con = jload(rep / f'colour_contract_{u}.json')
        roles = {'selected': sel[u]['selected_method'], 'baseline': sel[u]['strongest_baseline']}
        for scope in ('oof', 'diag'):
            y = arr(u, scope, 'y').astype(np.float64)
            n = y.size
            seg = (np.arange(n) // nbk) % S
            km = L[seg] / 1000.0
            periods = idx['units'][u]['oof_periods' if scope == 'oof' else 'diag_periods']
            p_sel = method(u, scope, roles['selected'])
            dens_sel = p_sel / km
            c = np.asarray(con['raw_cutoffs'], float)
            band = (dens_sel > c[0]).astype(np.int64) + (dens_sel > c[1]) + (dens_sel > c[2])
            if scope == 'oof':
                xs = np.sort(dens_sel)
                mine = [q7(xs, q) for q in cfg['colour']['quantiles']]
                v(f'{u}: cutoffs equal independent type-7 quantiles of the selected OOF density',
                  all(math.isclose(a, b, rel_tol=1e-14, abs_tol=0.0) for a, b in zip(mine, con['raw_cutoffs'])), {'mine': mine, 'saved': con['raw_cutoffs']})
                cnt = {lab: int((band == i).sum()) for i, lab in enumerate(['base', 'yellow', 'orange', 'red'])}
                v(f'{u}: reference band counts', cnt == con['reference_cell_counts'], {'mine': cnt, 'saved': con['reference_cell_counts']})
                evidence[u] = {'cutoffs': mine, 'band_counts': cnt}
            for r, m in roles.items():
                p = p_sel if r == 'selected' else method(u, scope, m)
                dv = unit_dev(y, p, floor)
                sub = met[(met.unit == u) & (met.scope == scope) & (met.role == r)]
                tot = {'n': n, 'total_actual': y.sum(), 'total_pred': p.sum(), 'deviance_sum': dv.sum(), 'exposure_segment_km_periods': km.sum()}
                pooled = sub[sub.dimension == 'pooled'].iloc[0]
                v(f'{u} {scope} {r}: pooled totals', all(close(tot[k], pooled[k]) for k in tot), {k: (tot[k], pooled[k]) for k in tot})
                for dim in ('calibration', 'colour', 'route_code', 'province'):
                    s = sub[sub.dimension == dim][list(tot)].sum()
                    v(f'{u} {scope} {r}: {dim} groups sum to the pooled totals', all(close(tot[k], s[k], 1e-8) for k in tot), s.to_dict())
                for i, lab in enumerate(['base', 'yellow', 'orange', 'red']):
                    mk = band == i
                    row = sub[(sub.dimension == 'colour') & (sub.group == lab)].iloc[0]
                    pairs = ((mk.sum(), 'n'), (y[mk].sum(), 'total_actual'), (p[mk].sum(), 'total_pred'), (dv[mk].sum(), 'deviance_sum'), (km[mk].sum(), 'exposure_segment_km_periods'))
                    v(f'{u} {scope} {r}: colour {lab} totals (selected-contract bands)', all(close(a, row[k]) for a, k in pairs), lab)
                for pdef in periods:
                    lo, hi = pdef['row_offset'], pdef['row_offset'] + pdef['rows']
                    row = sub[(sub.dimension == 'period') & (sub.group == pdef['id'])].iloc[0]
                    v(f'{u} {scope} {r}: period {pdef["id"]} mean deviance and records', close(dv[lo:hi].mean(), row['mean_poisson_deviance'])
                      and close(y[lo:hi].sum(), row['total_actual']), pdef['id'])
                if scope == 'oof':
                    T = n // (S * nbk)
                    Y = y.reshape(T, S, nbk).transpose(0, 2, 1).reshape(-1, S)
                    D = (p / km).reshape(T, S, nbk).transpose(0, 2, 1).reshape(-1, S)
                    total_km = L.sum() / 1000.0
                    for f in cfg['capture']['road_km_fractions']:
                        budget, got = f * total_km, 0.0
                        for t in range(Y.shape[0]):
                            order = np.lexsort((np.arange(S), -D[t]))  # descending density, ties by ascending segment index
                            used = 0.0
                            for j in order:
                                lk = L[j] / 1000.0
                                if used + lk <= budget:
                                    got += Y[t, j]
                                    used += lk
                                else:
                                    got += Y[t, j] * (budget - used) / lk
                                    break
                        row = cap[(cap.unit == u) & (cap.scope == 'oof_2022_2023') & (cap.time_block == 'all') & (cap.role == r) & (cap.road_km_fraction == f)].iloc[0]
                        v(f'{u} {r}: capture share at {f:.0%} road-km (explicit per-period loop)', close(got / Y.sum(), row['capture_share'], 1e-8),
                          {'mine': got / Y.sum(), 'saved': row['capture_share']})
                        evidence.setdefault(u + '_capture_' + r, {})[str(f)] = got / Y.sum()
    rowlevel = [k for k in man['report_files'] if k.endswith('.csv') and {'segment_id', 'target_date'} <= set(pd.read_csv(rep / k, nrows=0).columns)]
    v('no report CSV carries row-level segment x date outcomes', not rowlevel, rowlevel)
    return v.checks, evidence


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--run-root', required=True, type=Path)
    ap.add_argument('--save', type=Path, help='NEW JSON file for aggregate evidence (never overwritten)')
    a = ap.parse_args(argv)
    if a.save is not None and a.save.exists():
        sys.exit('refusing to overwrite ' + str(a.save))
    checks, ev = verify(a.run_root)
    ok = all(c['ok'] for c in checks)
    if a.save is not None:
        a.save.write_text(json.dumps({'status': 'pass' if ok else 'fail', 'checks': checks, 'aggregate_evidence': ev}, indent=2, default=float, allow_nan=False) + '\n', 'utf-8')
    print(('ALL PASS ' if ok else 'FAILED ') + str(sum(c['ok'] for c in checks)) + '/' + str(len(checks)))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
