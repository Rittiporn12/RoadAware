"""Headless runner for RoadAware V3 notebook 22 (verified spatial inference + robustness contract; real kernel via nbclient).

Usage (from the repository root):
    .venv/bin/python backend/scripts/run_spatial_inference.py --output-dir backend/rerun-spatial-serving-018-001

* --output-dir is required and must be a NEW directory directly inside backend/ named rerun-spatial-serving-* (gitignored by /rerun*/).
  An existing path (directory, file or symlink) is refused.
* Before anything is created, every planned write (notebook report/data dirs, executed notebook, run log, run-local kernel spec) is checked
  against the config protected_paths, the accepted notebook-20/21 roots, the pinned inputs, the prepared-data dir, the manager pins, the source
  notebook and the config (symlink/alias and ancestor overlaps in both directions). The notebook repeats its own guard and every hash check.
* All logic lives in the notebook FUNCTIONS; this runner only sets roots, executes with an explicit .venv kernel and writes a run log at
  <output>/reports/v3/run_manifest_spatial_inference.json (outside the report dir the notebook hashes). No network, no install, no deploy.
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
NOTEBOOK = '22_spatial_inference_contract'
CONFIG = 'config/spatial_inference_v3.json'
KERNEL_NAME = 'roadaware-venv'
ROOT_PREFIX = 'rerun-spatial-serving-'
ENV_PREFIX = 'ROADAWARE_'


def venv_python():
    for rel in ('bin/python', 'Scripts/python.exe'):
        p = REPO / '.venv' / rel
        if p.exists():
            return p
    return None


def ensure_venv():
    py = venv_python()
    if py is None:
        sys.exit(f'Project interpreter not found under {REPO / ".venv"}.')
    if Path(sys.prefix).resolve() != (REPO / '.venv').resolve():
        sys.exit(f'Refusing to run with {sys.executable} (prefix {sys.prefix}).\nRun: {py} backend/scripts/run_spatial_inference.py ...')
    return py


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def config(backend=BACKEND):
    return json.loads((Path(backend) / CONFIG).read_text('utf-8'))


def run_log_path(out):
    return Path(out) / 'reports' / 'v3' / 'run_manifest_spatial_inference.json'


def kernelspec_dir(out):
    return Path(out) / '.runner' / 'jupyter' / 'kernels' / KERNEL_NAME


def planned_writes(out, cfg):
    outs, out = cfg['outputs'], Path(out)
    return {'notebook report dir': out / outs['report_dir'], 'notebook data dir': out / outs['data_dir'],
            'executed notebook': out / 'notebooks' / f'{NOTEBOOK}.ipynb', 'run log': run_log_path(out), 'kernel spec': kernelspec_dir(out) / 'kernel.json'}


def guarded(backend, cfg):
    backend, I = Path(backend), cfg['inputs']
    out = [(backend / p, 'protected') for p in cfg['protected_paths']]
    out += [(backend / I[k]['path'], 'pinned input') for k in ('notebook19', 'notebook20', 'notebook21')]
    out += [(backend / I[k], 'pinned input') for k in ('config19', 'config20', 'config21', 'manifest19')]
    out += [(backend / r, 'accepted root') for r in cfg['guarded_roots']]
    out += [(backend / I['prepared_data_dir'], 'prepared data'), (backend / cfg['pins']['path'], 'manager pins'),
            (backend / 'notebooks' / f'{NOTEBOOK}.ipynb', 'source notebook'), (backend / CONFIG, 'config')]
    return out


def _same(a, b):
    try:
        return os.path.samefile(a, b)
    except OSError:
        return False


def _inside(child, parent):
    c, p = Path(child).resolve(), Path(parent).resolve()
    if c == p or p in c.parents:
        return True
    return p.exists() and any(_same(a, p) for a in (c, *c.parents) if a.exists())


def refusal(out, backend=BACKEND, cfg=None):
    """None when the output root is acceptable; otherwise why the run is refused. Pure check: call before any mkdir/write."""
    backend = Path(backend)
    cfg = config(backend) if cfg is None else cfg
    out = Path(os.path.abspath(out))
    hint = f'\nUse a NEW root, e.g.\n  .venv/bin/python backend/scripts/run_spatial_inference.py --output-dir backend/{ROOT_PREFIX}<id>'
    if os.path.lexists(out):
        kind = 'symlink' if out.is_symlink() else ('directory' if out.is_dir() else 'file')
        return f'Refusing output root {out}: a {kind} already exists there (reused roots are never written).{hint}'
    if not out.name.startswith(ROOT_PREFIX) or out.name == ROOT_PREFIX:
        return f'Refusing output root {out}: the directory name must start with {ROOT_PREFIX} followed by an id.{hint}'
    if not (out.parent.resolve() == backend.resolve() or _same(out.parent, backend)):
        return f'Refusing output root {out}: it must sit directly inside {backend} (gitignored /rerun*/).{hint}'
    hits = []
    for label, w in planned_writes(out, cfg).items():
        for p, kind in guarded(backend, cfg):
            if _inside(w, p):
                hits.append(f'  {label} {w} is inside {kind} {p}')
            elif _inside(p, w):
                hits.append(f'  {label} {w} contains {kind} {p}')
    if hits:
        return f'Refusing output root {out}: planned writes overlap protected paths; nothing was created.\n' + '\n'.join(hits) + hint
    return None


def build_env(out, backend=BACKEND, base=None):
    env = {k: v for k, v in (os.environ if base is None else base).items() if not k.startswith(ENV_PREFIX)}
    env.update(ROADAWARE_BACKEND_ROOT=str(Path(backend).resolve()), ROADAWARE_V3_OUTPUT_ROOT=str(Path(out).resolve()), MPLBACKEND='Agg',
               OMP_NUM_THREADS='2', OPENBLAS_NUM_THREADS='2', MKL_NUM_THREADS='2')
    env['ROADAWARE_STAGE_CONFIG'] = Path(CONFIG).name
    return env


def write_kernelspec(py, out):
    kdir = kernelspec_dir(out)
    kdir.mkdir(parents=True, exist_ok=True)
    spec = {'argv': [str(py), '-m', 'ipykernel_launcher', '-f', '{connection_file}'], 'display_name': 'RoadAware .venv', 'language': 'python'}
    (kdir / 'kernel.json').write_text(json.dumps(spec, indent=2), 'utf-8')
    os.environ['JUPYTER_PATH'] = os.pathsep.join([str(kdir.parents[1])] + [p for p in os.environ.get('JUPYTER_PATH', '').split(os.pathsep) if p])
    return spec


def notebook_status(out, cfg):
    p = Path(out) / cfg['outputs']['report_dir'] / 'spatial_serving_manifest.json'
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text('utf-8')).get('status')
    except ValueError:
        return 'unreadable'


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--output-dir', required=True, help=f'NEW root directly inside backend/, named {ROOT_PREFIX}*')
    ap.add_argument('--timeout', type=int, default=7200, help='per-cell timeout in seconds (default 7200)')
    ap.add_argument('--config', default='spatial_inference_v3.json', help='file name in backend/config (spatial_inference_v4.json = national)')
    return ap.parse_args(argv)


def main(argv=None):
    global CONFIG, NOTEBOOK
    a = parse_args(argv)
    if Path(a.config).name != a.config or not a.config.startswith('spatial_inference_v') or not (BACKEND / 'config' / a.config).is_file():
        sys.exit('--config must name an existing backend/config/spatial_inference_v*.json file')
    CONFIG = 'config/' + a.config
    cfg = config()
    nb_rel = Path(cfg.get('notebook', ''))
    if nb_rel.parent != Path('notebooks') or nb_rel.suffix != '.ipynb' or not (BACKEND / nb_rel).is_file():
        sys.exit(f'config notebook {nb_rel} must be an existing backend/notebooks/*.ipynb file')
    NOTEBOOK = nb_rel.stem  # v3 configs: the accepted pilot notebook; v4 configs: the *_national copy
    why = refusal(a.output_dir, BACKEND, cfg)
    if why:
        sys.exit(why)
    py = ensure_venv()
    import nbformat
    from nbclient import NotebookClient

    src, cfg_path = NB_DIR / f'{NOTEBOOK}.ipynb', BACKEND / CONFIG
    if not src.exists():
        sys.exit(f'{src} not found (assemble it first with tools/assemble_notebook_payloads.py)')
    out = Path(os.path.abspath(a.output_dir))
    out.mkdir(exist_ok=False)
    nb_out = out / 'notebooks'
    nb_out.mkdir()
    log_path = run_log_path(out)
    log_path.parent.mkdir(parents=True)
    env = build_env(out)
    os.environ.clear()
    os.environ.update(env)
    spec = write_kernelspec(py, out)
    log = {'started_utc': dt.datetime.now(dt.timezone.utc).isoformat(), 'notebook': NOTEBOOK, 'runner_sha256': sha256(Path(__file__).resolve()),
           'runner_python': sys.executable, 'kernel_name': KERNEL_NAME, 'kernel_argv': spec['argv'], 'output_root': str(out),
           'env_set': {k: env[k] for k in ('ROADAWARE_BACKEND_ROOT', 'ROADAWARE_V3_OUTPUT_ROOT', 'MPLBACKEND', 'OMP_NUM_THREADS')}, 'cell_timeout_seconds': a.timeout,
           'source_sha256_before': sha256(src), 'config_sha256_before': sha256(cfg_path), 'status': 'running', 'cell_log': []}

    def save_log():
        log_path.write_text(json.dumps(log, indent=2, ensure_ascii=False, allow_nan=False), 'utf-8')

    save_log()
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
    except Exception as e:
        log['status'] = 'failed'
        log['error'] = {'type': type(e).__name__, 'ename': getattr(e, 'ename', None), 'evalue': getattr(e, 'evalue', None),
                        'message': str(e)[-6000:], 'runner_traceback': traceback.format_exc()[-3000:]}
        rc = 1
    if original_kernelspec is not None:
        nb.metadata['kernelspec'] = original_kernelspec
    dst = nb_out / f'{NOTEBOOK}.ipynb'
    nbformat.write(nb, dst)
    nb_status = notebook_status(out, cfg)
    if rc == 0 and nb_status != 'complete':
        log['status'], rc = 'failed', 1
    log.update(seconds=round(time.time() - t0, 2), output_notebook=str(dst), output_notebook_sha256=sha256(dst), notebook_manifest_status=nb_status,
               source_sha256_after=sha256(src), config_sha256_after=sha256(cfg_path), finished_utc=dt.datetime.now(dt.timezone.utc).isoformat())
    save_log()
    print(f"[{log['status']}] {NOTEBOOK} ({log['seconds']}s, manifest status {nb_status}) -> {dst}\nrun log: {log_path}", flush=True)
    return rc


if __name__ == '__main__':
    sys.exit(main())
