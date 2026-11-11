"""Read-only verification (development evidence only; not ML/application logic): compare the y arrays saved by a notebook-20 run root with
Codex's independent label oracles in .ai-team/references/016-label-oracles. Executes no notebook FUNCTIONS and writes nothing.

Usage from the repository root:
    .venv/bin/python backend/scripts/verify_spatial_label_oracles.py --run-root backend/rerun-spatial-model-016-002
Prints one JSON object (per array: shapes, dtypes, file sha256, oracle-manifest sha match, records, positive cells, exact value equality).
Exit 0 only if every oracle matches; 1 on any mismatch or missing array; 2 on a refused/invalid path.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
ORACLE_DIR = REPO / '.ai-team' / 'references' / '016-label-oracles'
CONFIG = BACKEND / 'config' / 'spatial_experiment_v3.json'
KEYS = ('oof_daily', 'oof_6h', 'diag_daily', 'diag_6h', 'transfer_daily', 'transfer_6h')


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def run_root(arg):
    """Only an existing, non-symlinked backend/rerun-spatial-model-* directory directly inside backend/."""
    p = Path(arg)
    p = p if p.is_absolute() else REPO / p
    if p.is_symlink() or not p.is_dir() or p.resolve().parent != BACKEND.resolve() or not p.name.startswith('rerun-spatial-model-'):
        raise ValueError('run root must be an existing backend/rerun-spatial-model-* directory: ' + str(arg))
    return p.resolve()


def run_array(data_dir, key):
    prefix, unit = key.split('_', 1)
    d = data_dir / 'arrays' / ('transfer' if prefix == 'transfer' else '')
    return d / (prefix + '_' + unit + '_y.npy')


def compare(root):
    data_dir = root / json.loads(CONFIG.read_text('utf-8'))['outputs']['data_dir']
    man = json.loads((ORACLE_DIR / 'manifest.json').read_text('utf-8'))
    out, ok = {}, True
    for key in KEYS:
        m, orc, got = man[key], ORACLE_DIR / (key + '_y.npy'), run_array(data_dir, key)
        r = {'run_file': str(got.relative_to(REPO)) if got.is_file() else None, 'oracle_file': str(orc.relative_to(REPO))}
        if not got.is_file() or got.is_symlink():
            r['error'] = 'run array missing or symlinked: ' + str(got)
            out[key], ok = r, False
            continue
        a = np.load(orc, mmap_mode='r', allow_pickle=False)
        b = np.load(got, mmap_mode='r', allow_pickle=False)
        r.update(oracle_shape=list(a.shape), run_shape=list(b.shape), oracle_dtype=str(a.dtype), run_dtype=str(b.dtype),
                 oracle_sha256=sha256_file(orc), run_sha256=sha256_file(got), oracle_manifest_rows=m['rows'])
        r['oracle_sha_matches_manifest'] = r['oracle_sha256'] == m['sha256']
        r['same_shape'] = a.shape == b.shape == (int(m['rows']),)
        r['run_all_finite'] = bool(np.isfinite(b).all()) if r['same_shape'] else None
        r['exact_equal_values'] = bool(r['same_shape'] and np.array_equal(a, b))
        r['identical_file_bytes'] = r['oracle_sha256'] == r['run_sha256']
        r['oracle_records'], r['run_records'] = float(a.sum()), float(b.sum())
        r['oracle_positive_cells'], r['run_positive_cells'] = int((a > 0).sum()), int((b > 0).sum())
        r['matches_manifest_counts'] = r['run_records'] == m['records'] and r['run_positive_cells'] == m['positive_cells']
        r['passed'] = bool(r['oracle_sha_matches_manifest'] and r['exact_equal_values'] and r['matches_manifest_counts'])
        ok = ok and r['passed']
        out[key] = r
    return {'run_root': str(root.relative_to(REPO)), 'all_passed': ok, 'arrays': out}


def main(argv=None):
    ap = argparse.ArgumentParser(description='Read-only comparison of saved notebook-20 y arrays with the independent label oracles.')
    ap.add_argument('--run-root', required=True)
    a = ap.parse_args(argv)
    try:
        root = run_root(a.run_root)
    except ValueError as e:
        print('REFUSED: ' + str(e), file=sys.stderr)
        return 2
    res = compare(root)
    print(json.dumps(res, indent=2))
    return 0 if res['all_passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
