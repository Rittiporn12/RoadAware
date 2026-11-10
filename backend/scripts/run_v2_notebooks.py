"""Headless runner for RoadAware V2 notebooks (no browser; real kernel via nbclient): 09 collection, 10 preparation.

Usage (from the repository root):
    .venv/bin/python backend/scripts/run_v2_notebooks.py [--stage {collect,prepare,all}] [--output-dir DIR] [--external-root DIR]
                                                         [--data-root DIR] [--preflight-dir DIR] [--sources-dir DIR] [--timeout SEC]
                                                         [--offline | --refresh]

* --stage collect runs 09 (external collection + date evidence); --stage prepare runs 10 (date repair, panels, features, leakage
  audit; no network, no model fit) against an existing accepted 09 run; --stage all runs 09 then 10.
* --sources-dir is the READ-ONLY 09 report dir used by 10 (default: <output>/reports/v2/sources for --stage all, else
  backend/reports/v2/sources). 10 writes reports to <output>/reports/v2/preparation and row/panel matrices to <output>/data/v2.
* Must be launched with the project interpreter <repo>/.venv; each notebook runs in a fresh kernel from that interpreter.
* --data-root (default backend/) is the READ-ONLY v1 root. Its protected v1 locations (data/raw, data/interim, data/processed,
  data/model, reports/data, reports/models) may not overlap any V2 write root and are hashed before and after the run; any change
  fails the run.
* --external-root (default backend/data/external_v2) receives raw/cached sources, registry.json and row-level derived data.
* --output-dir (default backend/) receives reports/v2/sources/, reports/v2/run_manifest.json and, when given, notebooks/.
  Without --output-dir the executed notebook is saved in place (backend/notebooks) for review in VS Code.
* --offline uses only hash-verified cached files (no network); --refresh re-downloads (changed bytes become new versions).
* All collection/business logic lives in the notebook; this runner only sets roots/env, executes and records a log.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import sys
import time
import traceback
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
NB_DIR = BACKEND / 'notebooks'
COLLECT = ['09_external_collection_date_evidence']
PREPARE = ['10_v2_preparation_features_leakage']
STAGES = {'collect': list(COLLECT), 'prepare': list(PREPARE), 'all': COLLECT + PREPARE}
KERNEL_NAME = 'roadaware-venv'
V1_PROTECTED = [Path('data') / 'raw', Path('data') / 'interim', Path('data') / 'processed', Path('data') / 'model', Path('reports') / 'data',
                Path('reports') / 'models']
ENV_KEYS = ('ROADAWARE_BACKEND_ROOT', 'ROADAWARE_V2_EXTERNAL_ROOT', 'ROADAWARE_V2_OUTPUT_ROOT', 'ROADAWARE_V1_DATA_ROOT',
            'ROADAWARE_V2_PREFLIGHT_DIR', 'ROADAWARE_V2_OFFLINE', 'ROADAWARE_V2_REFRESH', 'ROADAWARE_V2_SOURCES_DIR', 'ROADAWARE_V2_DATA_ROOT')


def venv_python():
    for rel in ('bin/python', 'Scripts/python.exe'):
        p = REPO / '.venv' / rel
        if p.exists():
            return p  # deliberately not resolved: resolving the symlink would escape the venv
    return None


def ensure_venv():
    py = venv_python()
    if py is None:
        sys.exit(f'Project interpreter not found under {REPO / ".venv"}.\n'
                 'Create it: python3 -m venv .venv && .venv/bin/pip install -r backend/requirements-data.txt')
    if Path(sys.prefix).resolve() != (REPO / '.venv').resolve():
        sys.exit(f'Refusing to run with {sys.executable} (prefix {sys.prefix}).\nRun: {py} backend/scripts/run_v2_notebooks.py ...')
    return py


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def notebooks_for_stage(stage):
    if stage not in STAGES:
        raise ValueError(f'unknown stage {stage!r}; choose one of {sorted(STAGES)}')
    return list(STAGES[stage])


def _inside(p, root):
    p, root = Path(p).resolve(), Path(root).resolve()
    return p == root or root in p.parents


def resolve_roots(output_dir=None, external_root=None, data_root=None, preflight_dir=None, sources_dir=None, stage='collect'):
    """Absolute roots; raises ValueError when a V2 write location overlaps a protected v1 location (or, for 10, its read-only inputs)."""
    roots = {'backend': BACKEND,
             'output': Path(output_dir).resolve() if output_dir else BACKEND,
             'external': Path(external_root).resolve() if external_root else BACKEND / 'data' / 'external_v2',
             'data': Path(data_root).resolve() if data_root else BACKEND,
             'preflight': Path(preflight_dir).resolve() if preflight_dir else BACKEND / 'data' / 'external_v2' / 'evidence'}
    roots['v2_data'] = roots['output'] / 'data' / 'v2'
    if sources_dir:
        roots['sources'] = Path(sources_dir).resolve()
    else:
        roots['sources'] = (roots['output'] if stage == 'all' else BACKEND) / 'reports' / 'v2' / 'sources'
    writes = {'external root': roots['external'], 'report dir': roots['output'] / 'reports' / 'v2', 'v2 data root': roots['v2_data']}
    for label, w in writes.items():
        for rel in V1_PROTECTED:
            v = roots['data'] / rel
            if _inside(w, v) or _inside(v, w):
                raise ValueError(f'{label} {w} overlaps protected v1 location {v}')
    if stage in ('prepare', 'all'):
        for label, w in (('v2 data root', roots['v2_data']), ('preparation report dir', roots['output'] / 'reports' / 'v2' / 'preparation')):
            for rl, r in (('external root', roots['external']), ('09 sources dir', roots['sources'])):
                if _inside(w, r) or _inside(r, w):
                    raise ValueError(f'{label} {w} overlaps read-only {rl} {r}')
    return roots


def build_env(roots, offline=False, refresh=False, base=None):
    """Environment for the kernel: every V2 key set explicitly (inherited stale values are removed)."""
    if offline and refresh:
        raise ValueError('--offline and --refresh are mutually exclusive')
    env = {k: v for k, v in (os.environ if base is None else base).items() if k not in ENV_KEYS}
    env.update(ROADAWARE_BACKEND_ROOT=str(roots['backend']), ROADAWARE_V2_EXTERNAL_ROOT=str(roots['external']),
               ROADAWARE_V2_OUTPUT_ROOT=str(roots['output']), ROADAWARE_V1_DATA_ROOT=str(roots['data']),
               ROADAWARE_V2_PREFLIGHT_DIR=str(roots['preflight']), ROADAWARE_V2_SOURCES_DIR=str(roots['sources']),
               ROADAWARE_V2_DATA_ROOT=str(roots['v2_data']))
    if offline:
        env['ROADAWARE_V2_OFFLINE'] = '1'
    if refresh:
        env['ROADAWARE_V2_REFRESH'] = '1'
    return env


def protected_v1_hashes(data_root):
    """sha256 of every file under the protected v1 locations of data_root (relative path -> hash)."""
    out = {}
    for rel in V1_PROTECTED:
        base = Path(data_root) / rel
        if base.is_dir():
            for p in sorted(base.rglob('*')):
                if p.is_file():
                    out[p.relative_to(data_root).as_posix()] = sha256(p)
    return out


def write_kernelspec(py, out):
    """Run-local kernelspec pinned to the .venv interpreter; found via JUPYTER_PATH."""
    kdir = out / '.runner' / 'jupyter' / 'kernels' / KERNEL_NAME
    kdir.mkdir(parents=True, exist_ok=True)
    spec = {'argv': [str(py), '-m', 'ipykernel_launcher', '-f', '{connection_file}'], 'display_name': 'RoadAware .venv', 'language': 'python'}
    (kdir / 'kernel.json').write_text(json.dumps(spec, indent=2), 'utf-8')
    os.environ['JUPYTER_PATH'] = os.pathsep.join(
        [str(out / '.runner' / 'jupyter')] + [p for p in os.environ.get('JUPYTER_PATH', '').split(os.pathsep) if p])
    return spec


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--stage', choices=sorted(STAGES), default='collect', help='collect = 09 (default); prepare = 10; all = 09 then 10')
    ap.add_argument('--sources-dir', help='read-only 09 report dir for 10 (default <output>/reports/v2/sources for all, else backend/reports/v2/sources)')
    ap.add_argument('--output-dir', help='report root (reports/v2/...) and executed notebooks/')
    ap.add_argument('--external-root', help='raw/cache/derived root (default backend/data/external_v2)')
    ap.add_argument('--data-root', help='read-only v1 root holding data/raw/accidents (default backend/)')
    ap.add_argument('--preflight-dir', help='read-only Codex preflight evidence (default backend/data/external_v2/evidence)')
    ap.add_argument('--timeout', type=int, default=7200, help='per-cell timeout in seconds (weather collection can take ~30 min)')
    g = ap.add_mutually_exclusive_group()
    g.add_argument('--offline', action='store_true', help='cache only: no network requests')
    g.add_argument('--refresh', action='store_true', help='re-download sources; changed bytes become new versions')
    a = ap.parse_args(argv)

    py = ensure_venv()
    import nbformat  # imported after the venv check so a wrong interpreter fails clearly
    from nbclient import NotebookClient

    try:
        roots = resolve_roots(a.output_dir, a.external_root, a.data_root, a.preflight_dir, a.sources_dir, a.stage)
    except ValueError as e:
        sys.exit(str(e))
    if not (roots['data'] / 'data' / 'raw' / 'accidents' / 'source_manifest.json').is_file():
        sys.exit(f"{roots['data']} has no data/raw/accidents/source_manifest.json; pass --data-root")
    out = roots['output']
    nb_out = out / 'notebooks' if a.output_dir else NB_DIR
    nb_out.mkdir(parents=True, exist_ok=True)
    manifest_path = out / 'reports' / 'v2' / 'run_manifest.json'
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    env = build_env(roots, a.offline, a.refresh)
    os.environ.clear()
    os.environ.update(env)
    spec = write_kernelspec(py, out)
    order = notebooks_for_stage(a.stage)
    v1_before = protected_v1_hashes(roots['data'])
    log = {'started_utc': dt.datetime.now(dt.timezone.utc).isoformat(), 'stage': a.stage, 'notebook_order': order,
           'runner_sha256': sha256(Path(__file__).resolve()), 'runner_python': sys.executable, 'kernel_argv': spec['argv'],
           'roots': {k: str(v) for k, v in roots.items()}, 'offline': a.offline, 'refresh': a.refresh,
           'v1_protected_files_hashed': len(v1_before), 'status': 'running', 'notebooks': []}

    def save_log():
        manifest_path.write_text(json.dumps(log, indent=2, ensure_ascii=False, allow_nan=False), 'utf-8')

    rc = 0
    for name in order:
        src = NB_DIR / f'{name}.ipynb'
        entry = {'notebook': name, 'source': str(src), 'status': 'missing', 'error': None, 'cells_completed': 0,
                 'current_cell_index': None, 'cell_log': []}
        log['notebooks'].append(entry)
        if not src.exists():
            entry['error'] = f'{src} not found'
            rc = 1
            save_log()
            break
        entry['source_sha256_before'] = sha256(src)
        nb = nbformat.read(src, as_version=4)
        original_kernelspec = nb.metadata.get('kernelspec')
        n_code = sum(1 for c in nb.cells if c.cell_type == 'code')
        entry['status'] = 'running'
        t0, cell_t0 = time.time(), {}

        def on_start(cell, cell_index, **kw):
            cell_t0[cell_index] = time.time()
            entry['current_cell_index'] = cell_index
            if cell.cell_type == 'code':
                print(f"  [{name}] cell {cell_index} start ({entry['cells_completed'] + 1}/{n_code} code cells)", flush=True)

        def on_executed(cell, cell_index, **kw):
            if cell.cell_type != 'code':
                return
            entry['cells_completed'] += 1
            secs = round(time.time() - cell_t0.get(cell_index, time.time()), 1)
            errored = any(o.get('output_type') == 'error' for o in cell.get('outputs', []))
            entry['cell_log'].append({'cell_index': cell_index, 'seconds': secs, 'status': 'error' if errored else 'ok'})
            print(f'  [{name}] cell {cell_index} done in {secs}s', flush=True)
            for o in cell.get('outputs', []):  # echo the cell's stdout tail (weather progress is printed per chunk)
                if o.get('output_type') == 'stream':
                    for line in o.get('text', '').rstrip().splitlines()[-15:]:
                        print(f'      {line}', flush=True)
            save_log()

        try:
            NotebookClient(nb, timeout=a.timeout, kernel_name=KERNEL_NAME, resources={'metadata': {'path': str(NB_DIR)}},
                           on_cell_start=on_start, on_cell_executed=on_executed).execute()
            entry['status'] = 'ok'
        except Exception as e:  # CellExecutionError, timeouts, dead kernel: keep evidence
            entry['status'] = 'failed'
            entry['error'] = {'type': type(e).__name__, 'ename': getattr(e, 'ename', None), 'evalue': getattr(e, 'evalue', None),
                              'message': str(e)[-6000:], 'runner_traceback': traceback.format_exc()[-3000:]}
            failed = [i for i, c in enumerate(nb.cells) if c.cell_type == 'code' and any(o.get('output_type') == 'error' for o in c.get('outputs', []))]
            entry['failed_cell_index'] = failed[0] if failed else entry['current_cell_index']
            rc = 1
        if original_kernelspec is not None:
            nb.metadata['kernelspec'] = original_kernelspec  # keep VS Code-selectable metadata
        dst = nb_out / f'{name}.ipynb'
        try:
            nbformat.validate(nb)
            entry['nbformat_valid'] = True
        except Exception as e:
            entry['nbformat_valid'] = False
            entry['nbformat_error'] = str(e)[-2000:]
            rc = 1
        nbformat.write(nb, dst)
        entry.update(seconds=round(time.time() - t0, 2), output=str(dst), output_sha256=sha256(dst))
        save_log()
        print(f"[{entry['status']}] {name} ({entry['seconds']}s) -> {dst}", flush=True)
        if rc:
            break

    v1_after = protected_v1_hashes(roots['data'])
    changed = sorted(k for k in set(v1_before) | set(v1_after) if v1_before.get(k) != v1_after.get(k))
    log['v1_protected_unchanged'] = not changed
    log['v1_protected_changed_files'] = changed
    if changed:
        rc = 1
        print(f'ERROR: protected v1 files changed during the V2 run: {changed[:20]}', flush=True)
    log['status'] = 'ok' if rc == 0 else 'failed'
    log['finished_utc'] = dt.datetime.now(dt.timezone.utc).isoformat()
    save_log()
    print(f"V2 run manifest: {manifest_path} (status={log['status']})", flush=True)
    return rc


if __name__ == '__main__':
    sys.exit(main())
