"""Headless runner for RoadAware V3 notebook 16 (spatial data readiness audit; no model fit, no network; real kernel via nbclient).

Usage (from the repository root):
    .venv/bin/python backend/scripts/run_spatial_readiness.py [--output-dir DIR] [--timeout SEC]

* Inputs (READ-ONLY, hash-verified by the notebook against backend/config/spatial_readiness_v3.json): backend/data/v2/{events_v2,
  row_lineage_v2,panel_daily_v2}.csv.gz, backend/data/raw/accidents/*.csv + source_manifest.json, the accepted notebook 10 preparation
  manifest, backend/config/data_pipeline.json and the manager preflight under workflow/spatial/.
* --output-dir (default backend/) receives reports/v3/spatial_readiness/ (aggregates, figures, Thai report, manifest), data/v3/
  spatial_readiness/ (row-level, gitignored) and, when given, notebooks/. Without --output-dir the executed notebook is saved in place.
* An earlier result in the output root is never overwritten: use a NEW root, e.g. backend/rerun-spatial-<UTC-stamp>.
* Before anything is created, every planned write (report/data dirs, executed notebook, run log, kernel spec) is checked against the
  config protected_paths (symlink/alias and ancestor overlaps included); an overlapping root is refused with nothing written.
* All audit logic lives in the notebook; this runner only sets roots/env, executes and records a run log at
  <output>/reports/v3/run_manifest_spatial_readiness.json (outside the report dir the notebook hashes).
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
NOTEBOOK = '16_spatial_data_readiness'
KERNEL_NAME = 'roadaware-venv'
REPORT_REL = Path('reports') / 'v3' / 'spatial_readiness'
ENV_KEYS = ('ROADAWARE_BACKEND_ROOT', 'ROADAWARE_V3_OUTPUT_ROOT', 'ROADAWARE_V3_OFFLINE')


def venv_python():
    for rel in ('bin/python', 'Scripts/python.exe'):
        p = REPO / '.venv' / rel
        if p.exists():
            return p  # deliberately not resolved: resolving the symlink would escape the venv
    return None


def ensure_venv():
    py = venv_python()
    if py is None:
        sys.exit(f'Project interpreter not found under {REPO / ".venv"}.')
    if Path(sys.prefix).resolve() != (REPO / '.venv').resolve():
        sys.exit(f'Refusing to run with {sys.executable} (prefix {sys.prefix}).\nRun: {py} backend/scripts/run_spatial_readiness.py ...')
    return py


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def run_log_path(out):
    return Path(out) / 'reports' / 'v3' / 'run_manifest_spatial_readiness.json'


def config_path():
    return BACKEND / 'config' / 'spatial_readiness_v3.json'


def kernelspec_dir(out):
    return Path(out) / '.runner' / 'jupyter' / 'kernels' / KERNEL_NAME


def planned_writes(out, explicit):
    """Every location this run writes (runner and notebook), known before anything is created."""
    outs = json.loads(config_path().read_text('utf-8'))['outputs']
    out = Path(out)
    nb_dir = out / 'notebooks' if explicit else NB_DIR
    return {'notebook report dir': out / outs['report_dir'], 'notebook row-level data dir': out / outs['data_dir'],
            'executed notebook': nb_dir / f'{NOTEBOOK}.ipynb', 'run log': run_log_path(out), 'kernel spec': kernelspec_dir(out) / 'kernel.json'}


def _same(a, b):
    try:
        return os.path.samefile(a, b)
    except OSError:
        return False


def _inside(child, parent):
    """child is parent or beneath it: by resolved path (symlinks, ..) or by file identity of an existing ancestor (aliases, case-insensitive volumes)."""
    c, p = Path(child).resolve(), Path(parent).resolve()
    if c == p or p in c.parents:
        return True
    return p.exists() and any(_same(a, p) for a in (c, *c.parents) if a.exists())


def write_conflicts(out, explicit):
    """None when no planned write touches a protected input; otherwise why the run is refused. Read-only: call before any mkdir/write."""
    protected = [BACKEND / p for p in json.loads(config_path().read_text('utf-8'))['protected_paths']]
    hits = []
    for label, w in planned_writes(out, explicit).items():
        for p in protected:
            if _inside(w, p):
                hits.append(f'  {label} {w} is inside protected {p}')
            elif _inside(p, w):
                hits.append(f'  {label} {w} contains protected {p}')
    if hits:
        return (f'Refusing output root {out}: planned writes overlap protected inputs ({config_path().name} protected_paths); nothing was '
                f'created.\n' + '\n'.join(hits) + f'\nUse a fresh root, e.g.\n  {sys.executable} backend/scripts/run_spatial_readiness.py '
                f'--output-dir backend/rerun-spatial-<UTC-stamp>')
    return None


def preconditions(out):
    """None when the output root is fresh; otherwise why the run must use a new root (earlier evidence is never overwritten)."""
    rep = Path(out) / REPORT_REL
    old = [p for p in (rep / 'spatial_readiness_manifest.json', run_log_path(out)) if p.exists()]
    if old or (rep.is_dir() and any(rep.iterdir())):
        return (f'{[str(p) for p in old] or str(rep)} already exist (earlier notebook 16 run). Use a fresh root, e.g.\n'
                f'  {sys.executable} backend/scripts/run_spatial_readiness.py --output-dir backend/rerun-spatial-<UTC-stamp>')
    return None


def build_env(out, base=None):
    """Kernel environment: every V3 key set explicitly (stale inherited values removed); offline is always on."""
    env = {k: v for k, v in (os.environ if base is None else base).items() if k not in ENV_KEYS}
    env.update(ROADAWARE_BACKEND_ROOT=str(BACKEND), ROADAWARE_V3_OUTPUT_ROOT=str(Path(out).resolve()), ROADAWARE_V3_OFFLINE='1')
    return env


def write_kernelspec(py, out):
    """Run-local kernelspec pinned to the .venv interpreter; found via JUPYTER_PATH."""
    kdir = kernelspec_dir(out)
    kdir.mkdir(parents=True, exist_ok=True)
    spec = {'argv': [str(py), '-m', 'ipykernel_launcher', '-f', '{connection_file}'], 'display_name': 'RoadAware .venv', 'language': 'python'}
    (kdir / 'kernel.json').write_text(json.dumps(spec, indent=2), 'utf-8')
    os.environ['JUPYTER_PATH'] = os.pathsep.join(
        [str(kdir.parents[1])] +[p for p in os.environ.get('JUPYTER_PATH', '').split(os.pathsep) if p])
    return spec


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--output-dir', help='root for reports/v3, data/v3 and executed notebooks/ (default backend/)')
    ap.add_argument('--timeout', type=int, default=3600, help='per-cell timeout in seconds (default 3600)')
    a = ap.parse_args(argv)

    py = ensure_venv()
    out = Path(a.output_dir).resolve() if a.output_dir else BACKEND
    why = write_conflicts(out, bool(a.output_dir)) or preconditions(out)  # before any mkdir/write
    if why:
        sys.exit(why)
    import nbformat  # imported after the venv check so a wrong interpreter fails clearly
    from nbclient import NotebookClient

    src = NB_DIR / f'{NOTEBOOK}.ipynb'
    if not src.exists():
        sys.exit(f'{src} not found')
    nb_out = out / 'notebooks' if a.output_dir else NB_DIR
    nb_out.mkdir(parents=True, exist_ok=True)
    log_path = run_log_path(out)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    env = build_env(out)
    os.environ.clear()
    os.environ.update(env)
    spec = write_kernelspec(py, out)
    log = {'started_utc': dt.datetime.now(dt.timezone.utc).isoformat(), 'notebook': NOTEBOOK, 'runner_sha256': sha256(Path(__file__).resolve()),
           'runner_python': sys.executable, 'kernel_argv': spec['argv'], 'output_root': str(out), 'offline': True,
           'cell_timeout_seconds': a.timeout, 'source_sha256_before': sha256(src), 'status': 'running', 'cell_log': []}

    def save_log():
        log_path.write_text(json.dumps(log, indent=2, ensure_ascii=False, allow_nan=False), 'utf-8')

    nb = nbformat.read(src, as_version=4)
    original_kernelspec = nb.metadata.get('kernelspec')
    t0, cell_t0 = time.time(), {}

    def on_start(cell, cell_index, **kw):
        cell_t0[cell_index] = time.time()

    def on_executed(cell, cell_index, **kw):
        if cell.cell_type != 'code':
            return
        errored = any(o.get('output_type') == 'error' for o in cell.get('outputs', []))
        secs = round(time.time() - cell_t0.get(cell_index, time.time()), 1)
        log['cell_log'].append({'cell_index': cell_index, 'seconds': secs, 'status': 'error' if errored else 'ok'})
        print(f'  [{NOTEBOOK}] cell {cell_index} done in {secs}s', flush=True)
        save_log()

    rc = 0
    try:
        NotebookClient(nb, timeout=a.timeout, kernel_name=KERNEL_NAME, resources={'metadata': {'path': str(NB_DIR)}},
                       on_cell_start=on_start, on_cell_executed=on_executed).execute()
        log['status'] = 'ok'
    except Exception as e:  # CellExecutionError, timeouts, dead kernel: keep evidence
        log['status'] = 'failed'
        log['error'] = {'type': type(e).__name__, 'ename': getattr(e, 'ename', None), 'evalue': getattr(e, 'evalue', None),
                        'message': str(e)[-6000:], 'runner_traceback': traceback.format_exc()[-3000:]}
        rc = 1
    if original_kernelspec is not None:
        nb.metadata['kernelspec'] = original_kernelspec  # keep VS Code-selectable metadata
    dst = nb_out / f'{NOTEBOOK}.ipynb'
    nbformat.write(nb, dst)
    log.update(seconds=round(time.time() - t0, 2), output_notebook=str(dst), output_notebook_sha256=sha256(dst),
               finished_utc=dt.datetime.now(dt.timezone.utc).isoformat())
    save_log()
    print(f"[{log['status']}] {NOTEBOOK} ({log['seconds']}s) -> {dst}\nrun log: {log_path}", flush=True)
    return rc


if __name__ == '__main__':
    sys.exit(main())
