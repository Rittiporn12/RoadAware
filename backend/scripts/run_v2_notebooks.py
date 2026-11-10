"""Headless runner for RoadAware V2 notebooks (no browser; real kernel via nbclient): 09 collection, 10 preparation, 11 model experiment.

Usage (from the repository root):
    .venv/bin/python backend/scripts/run_v2_notebooks.py [--stage {collect,prepare,all,model}] [--output-dir DIR] [--external-root DIR]
                                                         [--data-root DIR] [--preflight-dir DIR] [--sources-dir DIR] [--timeout SEC]
                                                         [--preparation-dir DIR] [--prep-data-dir DIR] [--experiment-lock FILE]
                                                         [--offline | --refresh]

* --stage collect runs 09 (external collection + date evidence); --stage prepare runs 10 (date repair, panels, features, leakage
  audit; no network, no model fit) against an existing accepted 09 run; --stage all runs 09 then 10.
* --stage model runs ONLY 11 (explicit; never part of 'all') against the accepted 10 outputs: --preparation-dir (default
  backend/reports/v2/preparation) and --prep-data-dir (default backend/data/v2) are READ-ONLY; --experiment-lock (default
  workflow/model-protocol-v2-lock.json, created by the manager after acceptance) must exist or 11 stops before fitting. 11 writes
  aggregates to <output>/reports/v2/models and row-level predictions/bundles to <output>/data/v2/models (gitignored). This run log sits
  OUTSIDE the model report dir, at <output>/reports/v2/run_manifest_model.json (older runs wrote it into reports/v2/models). An existing
  model run log in the output root is never overwritten. Default per-cell timeout for this stage is 21600 s (OOF backtests are long).
* --stage evaluate runs ONLY 12 (explicit; never part of 'all'; no fit) against a completed 11 run: --model-dir (default
  backend/reports/v2/models), --model-data-dir (default backend/data/v2/models), --preparation-dir, --prep-data-dir and --experiment-lock
  are READ-ONLY. 12 writes aggregates/PNG to <output>/reports/v2/analysis and row diagnostics to <output>/data/v2/analysis (gitignored);
  this run log: <output>/reports/v2/run_manifest_analysis.json. An existing analysis_manifest.json in the output root is never overwritten.
* --stage serve-check runs ONLY 13 (explicit; never part of 'all'; no fit, no tuning) against the accepted 09-12 outputs: --model-dir,
  --model-data-dir, --preparation-dir, --prep-data-dir, --sources-dir, --external-root, --analysis-dir and --experiment-lock are READ-ONLY
  (13 additionally checks them against the trust anchors in backend/config/inference_v2.json). 13 writes aggregates to
  <output>/reports/v2/serving and row-level stress rows to <output>/data/v2/serving (gitignored); this run log:
  <output>/reports/v2/run_manifest_serving.json (outside the serving report dir). An existing serving_manifest.json is never overwritten.
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
MODEL = ['11_v2_model_experiments']
EVALUATE = ['12_v2_evaluation_error_analysis']
SERVE = ['13_inference_robustness_contract']
STAGES = {'collect': list(COLLECT), 'prepare': list(PREPARE), 'all': COLLECT + PREPARE, 'model': list(MODEL), 'evaluate': list(EVALUATE),
          'serve-check': list(SERVE)}
STAGE_TIMEOUT = {'model': 21600}
KERNEL_NAME = 'roadaware-venv'
V1_PROTECTED = [Path('data') / 'raw', Path('data') / 'interim', Path('data') / 'processed', Path('data') / 'model', Path('reports') / 'data',
                Path('reports') / 'models']
ENV_KEYS = ('ROADAWARE_BACKEND_ROOT', 'ROADAWARE_V2_EXTERNAL_ROOT', 'ROADAWARE_V2_OUTPUT_ROOT', 'ROADAWARE_V1_DATA_ROOT',
            'ROADAWARE_V2_PREFLIGHT_DIR', 'ROADAWARE_V2_OFFLINE', 'ROADAWARE_V2_REFRESH', 'ROADAWARE_V2_SOURCES_DIR', 'ROADAWARE_V2_DATA_ROOT',
            'ROADAWARE_V2_PREPARATION_DIR', 'ROADAWARE_V2_MODEL_DATA_ROOT', 'ROADAWARE_V2_EXPERIMENT_LOCK', 'ROADAWARE_V2_MODEL_REPORT_DIR',
            'ROADAWARE_V2_ANALYSIS_DATA_ROOT', 'ROADAWARE_V2_MODEL_NOTEBOOK', 'ROADAWARE_V2_ANALYSIS_REPORT_DIR', 'ROADAWARE_V2_SERVING_DATA_ROOT')


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


def resolve_roots(output_dir=None, external_root=None, data_root=None, preflight_dir=None, sources_dir=None, stage='collect',
                  preparation_dir=None, prep_data_dir=None, experiment_lock=None, model_dir=None, model_data_dir=None, analysis_dir=None):
    """Absolute roots; raises ValueError when a V2 write location overlaps a protected v1 location (or, for 10/11, its read-only inputs)."""
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
    if stage == 'model':
        roots['preparation'] = Path(preparation_dir).resolve() if preparation_dir else BACKEND / 'reports' / 'v2' / 'preparation'
        roots['prep_data'] = Path(prep_data_dir).resolve() if prep_data_dir else BACKEND / 'data' / 'v2'
        roots['model_data'] = roots['output'] / 'data' / 'v2' / 'models'
        roots['model_reports'] = roots['output'] / 'reports' / 'v2' / 'models'
        roots['lock'] = Path(experiment_lock).resolve() if experiment_lock else REPO / 'workflow' / 'model-protocol-v2-lock.json'
        for label, w in (('model data root', roots['model_data']), ('model report dir', roots['model_reports'])):
            for rel in V1_PROTECTED:
                if _inside(w, roots['data'] / rel) or _inside(roots['data'] / rel, w):
                    raise ValueError(f'{label} {w} overlaps protected v1 location {roots["data"] / rel}')
            for rl in ('preparation', 'sources'):
                if _inside(w, roots[rl]) or _inside(roots[rl], w):
                    raise ValueError(f'{label} {w} overlaps read-only {rl} dir {roots[rl]}')
        if _inside(roots['prep_data'], roots['model_data']):
            raise ValueError(f"model data root {roots['model_data']} equals or contains the read-only 10 data root {roots['prep_data']}")
        if _inside(roots['model_reports'], roots['prep_data']) or _inside(roots['prep_data'], roots['model_reports']):
            raise ValueError('model report dir overlaps the read-only 10 data root')
    if stage == 'evaluate':  # 12: every 09/10/11 location is READ-ONLY; 12 writes only reports/v2/analysis and data/v2/analysis under output
        roots['preparation'] = Path(preparation_dir).resolve() if preparation_dir else BACKEND / 'reports' / 'v2' / 'preparation'
        roots['prep_data'] = Path(prep_data_dir).resolve() if prep_data_dir else BACKEND / 'data' / 'v2'
        roots['model_reports'] = Path(model_dir).resolve() if model_dir else BACKEND / 'reports' / 'v2' / 'models'
        roots['model_data'] = Path(model_data_dir).resolve() if model_data_dir else BACKEND / 'data' / 'v2' / 'models'
        roots['lock'] = Path(experiment_lock).resolve() if experiment_lock else REPO / 'workflow' / 'model-protocol-v2-lock.json'
        roots['analysis_reports'] = roots['output'] / 'reports' / 'v2' / 'analysis'
        roots['analysis_data'] = roots['output'] / 'data' / 'v2' / 'analysis'
        for label in ('analysis_reports', 'analysis_data'):
            w = roots[label]
            for rel in V1_PROTECTED:
                if _inside(w, roots['data'] / rel) or _inside(roots['data'] / rel, w):
                    raise ValueError(f'{label} {w} overlaps protected v1 location {roots["data"] / rel}')
            for rl in ('preparation', 'sources', 'model_reports', 'model_data'):
                if _inside(w, roots[rl]) or _inside(roots[rl], w):
                    raise ValueError(f'{label} {w} overlaps read-only {rl} dir {roots[rl]}')
            if _inside(roots['prep_data'], w):
                raise ValueError(f'{label} {w} equals or contains the read-only 10 data root {roots["prep_data"]}')
        if _inside(roots['analysis_reports'], roots['prep_data']):
            raise ValueError('analysis report dir lies inside the read-only 10 data root')
    if stage == 'serve-check':  # 13: every 09-12 location is READ-ONLY; 13 writes only reports/v2/serving and data/v2/serving under output
        roots['preparation'] = Path(preparation_dir).resolve() if preparation_dir else BACKEND / 'reports' / 'v2' / 'preparation'
        roots['prep_data'] = Path(prep_data_dir).resolve() if prep_data_dir else BACKEND / 'data' / 'v2'
        roots['model_reports'] = Path(model_dir).resolve() if model_dir else BACKEND / 'reports' / 'v2' / 'models'
        roots['model_data'] = Path(model_data_dir).resolve() if model_data_dir else BACKEND / 'data' / 'v2' / 'models'
        roots['analysis_dir'] = Path(analysis_dir).resolve() if analysis_dir else BACKEND / 'reports' / 'v2' / 'analysis'
        roots['lock'] = Path(experiment_lock).resolve() if experiment_lock else REPO / 'workflow' / 'model-protocol-v2-lock.json'
        roots['serving_reports'] = roots['output'] / 'reports' / 'v2' / 'serving'
        roots['serving_data'] = roots['output'] / 'data' / 'v2' / 'serving'
        for label in ('serving_reports', 'serving_data'):
            w = roots[label]
            for rel in V1_PROTECTED:
                if _inside(w, roots['data'] / rel) or _inside(roots['data'] / rel, w):
                    raise ValueError(f'{label} {w} overlaps protected v1 location {roots["data"] / rel}')
            for rl in ('preparation', 'sources', 'external', 'model_reports', 'model_data', 'analysis_dir'):
                if _inside(w, roots[rl]) or _inside(roots[rl], w):
                    raise ValueError(f'{label} {w} overlaps read-only {rl} dir {roots[rl]}')
            if _inside(roots['prep_data'], w):
                raise ValueError(f'{label} {w} equals or contains the read-only 10 data root {roots["prep_data"]}')
    return roots


RUN_LOG_NAMES = {'model': 'run_manifest_model.json', 'evaluate': 'run_manifest_analysis.json', 'serve-check': 'run_manifest_serving.json'}


def run_log_path(out, stage):
    """Runner log of a stage: always directly under <out>/reports/v2, never inside a report dir a notebook hashes into its manifest."""
    return Path(out) / 'reports' / 'v2' / RUN_LOG_NAMES.get(stage, 'run_manifest.json')


def model_run_logs(model_reports):
    """11 runner logs for a model report dir: canonical (its parent, reports/v2) and legacy (inside it, older runners)."""
    rep = Path(model_reports)
    return [rep.parent / RUN_LOG_NAMES['model'], rep / RUN_LOG_NAMES['model']]


def evaluate_preconditions(roots):
    """Stage evaluate: a completed 11 manifest and its runner log must exist and an earlier 12 result in the output root is never overwritten
    (12 itself verifies the log status and every hash)."""
    man = roots['model_reports'] / 'model_manifest.json'
    if not man.is_file():
        return f'{man} not found: run and verify notebook 11 first (12 never analyses an incomplete experiment)'
    if not any(p.is_file() for p in model_run_logs(roots['model_reports'])):
        return f"no 11 runner log at {[str(p) for p in model_run_logs(roots['model_reports'])]}: run notebook 11 via --stage model first"
    if (roots['analysis_reports'] / 'analysis_manifest.json').exists():
        return (f"{roots['analysis_reports'] / 'analysis_manifest.json'} already exists (earlier notebook 12 run). Use a fresh root, e.g.\n"
                f'  {sys.executable} backend/scripts/run_v2_notebooks.py --stage evaluate --output-dir backend/rerun-analysis-<UTC-stamp>')
    return None


def serve_preconditions(roots):
    """Stage serve-check: completed 11 and 12 manifests must exist; an earlier 13 result (or its run log) in the output root is never overwritten."""
    for p, what in ((roots['model_reports'] / 'model_manifest.json', 'notebook 11'), (roots['analysis_dir'] / 'analysis_manifest.json', 'notebook 12')):
        if not p.is_file():
            return f'{p} not found: run and verify {what} first (13 only serves accepted, completed runs)'
    old = [p for p in (roots['serving_reports'] / 'serving_manifest.json', run_log_path(roots['output'], 'serve-check')) if p.exists()]
    if old:
        return (f'{[str(p) for p in old]} already exist (earlier notebook 13 run). Use a fresh root, e.g.\n'
                f'  {sys.executable} backend/scripts/run_v2_notebooks.py --stage serve-check --output-dir backend/rerun-serving-<UTC-stamp>')
    return None


def completed_model_outputs(roots):
    """Artifacts of an earlier 11 run under the model roots (same markers the notebook checks before fitting)."""
    rep, md = roots['model_reports'], roots['model_data']
    hits = [rep / n for n in ('selection_lock.json', 'model_manifest.json', 'oof_metrics_pooled.csv', 'fit_log.csv') if (rep / n).exists()]
    for pat in ('oof_predictions_*.csv.gz', 'diagnostic_predictions_*.csv.gz', 'bundles'):
        hits += sorted(md.glob(pat))
    hits += [p for p in model_run_logs(rep) if p.exists()]  # an earlier attempt's log is evidence too: never overwritten
    return [str(h) for h in hits]


def build_env(roots, offline=False, refresh=False, base=None):
    """Environment for the kernel: every V2 key set explicitly (inherited stale values are removed)."""
    if offline and refresh:
        raise ValueError('--offline and --refresh are mutually exclusive')
    env = {k: v for k, v in (os.environ if base is None else base).items() if k not in ENV_KEYS}
    env.update(ROADAWARE_BACKEND_ROOT=str(roots['backend']), ROADAWARE_V2_EXTERNAL_ROOT=str(roots['external']),
               ROADAWARE_V2_OUTPUT_ROOT=str(roots['output']), ROADAWARE_V1_DATA_ROOT=str(roots['data']),
               ROADAWARE_V2_PREFLIGHT_DIR=str(roots['preflight']), ROADAWARE_V2_SOURCES_DIR=str(roots['sources']),
               ROADAWARE_V2_DATA_ROOT=str(roots['v2_data']))
    if 'model_data' in roots:  # stage model: 10 matrices are READ-ONLY inputs; 11 writes its own model data root
        env.update(ROADAWARE_V2_DATA_ROOT=str(roots['prep_data']), ROADAWARE_V2_PREPARATION_DIR=str(roots['preparation']),
                   ROADAWARE_V2_MODEL_DATA_ROOT=str(roots['model_data']), ROADAWARE_V2_EXPERIMENT_LOCK=str(roots['lock']))
    if 'analysis_reports' in roots:  # stage evaluate: 11 reports/data are READ-ONLY too; 12 writes only its analysis roots
        env.update(ROADAWARE_V2_MODEL_REPORT_DIR=str(roots['model_reports']), ROADAWARE_V2_ANALYSIS_DATA_ROOT=str(roots['analysis_data']),
                   ROADAWARE_V2_MODEL_NOTEBOOK=str(NB_DIR / f'{MODEL[0]}.ipynb'))
    if 'serving_reports' in roots:  # stage serve-check: 11/12 reports and data are READ-ONLY; 13 writes only its serving roots
        env.update(ROADAWARE_V2_MODEL_REPORT_DIR=str(roots['model_reports']), ROADAWARE_V2_ANALYSIS_REPORT_DIR=str(roots['analysis_dir']),
                   ROADAWARE_V2_SERVING_DATA_ROOT=str(roots['serving_data']))
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
    ap.add_argument('--stage', choices=sorted(STAGES), default='collect',
                    help='collect = 09 (default); prepare = 10; all = 09 then 10; model = 11 only; evaluate = 12 only; serve-check = 13 only')
    ap.add_argument('--analysis-dir', help='stage serve-check: read-only accepted 12 report dir (default backend/reports/v2/analysis)')
    ap.add_argument('--model-dir', help='stage evaluate: read-only completed 11 report dir (default backend/reports/v2/models)')
    ap.add_argument('--model-data-dir', help='stage evaluate: read-only 11 row predictions (default backend/data/v2/models)')
    ap.add_argument('--preparation-dir', help='stage model: read-only accepted 10 report dir (default backend/reports/v2/preparation)')
    ap.add_argument('--prep-data-dir', help='stage model: read-only accepted 10 matrices (default backend/data/v2)')
    ap.add_argument('--experiment-lock', help='stage model: manager experiment lock (default workflow/model-protocol-v2-lock.json)')
    ap.add_argument('--sources-dir', help='read-only 09 report dir for 10 (default <output>/reports/v2/sources for all, else backend/reports/v2/sources)')
    ap.add_argument('--output-dir', help='report root (reports/v2/...) and executed notebooks/')
    ap.add_argument('--external-root', help='raw/cache/derived root (default backend/data/external_v2)')
    ap.add_argument('--data-root', help='read-only v1 root holding data/raw/accidents (default backend/)')
    ap.add_argument('--preflight-dir', help='read-only Codex preflight evidence (default backend/data/external_v2/evidence)')
    ap.add_argument('--timeout', type=int, default=None, help='per-cell timeout in seconds (default 7200; 21600 for --stage model)')
    g = ap.add_mutually_exclusive_group()
    g.add_argument('--offline', action='store_true', help='cache only: no network requests')
    g.add_argument('--refresh', action='store_true', help='re-download sources; changed bytes become new versions')
    a = ap.parse_args(argv)

    py = ensure_venv()
    import nbformat  # imported after the venv check so a wrong interpreter fails clearly
    from nbclient import NotebookClient

    try:
        roots = resolve_roots(a.output_dir, a.external_root, a.data_root, a.preflight_dir, a.sources_dir, a.stage,
                              a.preparation_dir, a.prep_data_dir, a.experiment_lock, a.model_dir, a.model_data_dir, a.analysis_dir)
    except ValueError as e:
        sys.exit(str(e))
    timeout = a.timeout if a.timeout is not None else STAGE_TIMEOUT.get(a.stage, 7200)
    if a.stage in ('evaluate', 'serve-check'):
        why = (evaluate_preconditions if a.stage == 'evaluate' else serve_preconditions)(roots)
        if why:
            sys.exit(why)
    if a.stage == 'model' and not roots['lock'].is_file():
        sys.exit(f"experiment lock {roots['lock']} not found: it is created by the manager only after 09/10 acceptance; no V2 fit without it")
    if a.stage == 'model':
        old = completed_model_outputs(roots)
        if old:  # preserve earlier locks/results and their run log; never spend the OOF runtime only to fail at the lock
            sys.exit(f'{old[:4]} already exist (earlier notebook 11 run). Use a fresh root, e.g.\n'
                     f'  {sys.executable} backend/scripts/run_v2_notebooks.py --stage model --output-dir backend/rerun-model-<UTC-stamp>')
    if not (roots['data'] / 'data' / 'raw' / 'accidents' / 'source_manifest.json').is_file():
        sys.exit(f"{roots['data']} has no data/raw/accidents/source_manifest.json; pass --data-root")
    out = roots['output']
    nb_out = out / 'notebooks' if a.output_dir else NB_DIR
    nb_out.mkdir(parents=True, exist_ok=True)
    # stages model/evaluate keep their own run logs so the 09/10 run log is never overwritten; both sit OUTSIDE reports/v2/models and
    # reports/v2/analysis so the runner never rewrites a file that 11 or 12 hashes into its manifest
    manifest_path = run_log_path(out, a.stage)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    env = build_env(roots, a.offline, a.refresh)
    os.environ.clear()
    os.environ.update(env)
    spec = write_kernelspec(py, out)
    order = notebooks_for_stage(a.stage)
    v1_before = protected_v1_hashes(roots['data'])
    log = {'started_utc': dt.datetime.now(dt.timezone.utc).isoformat(), 'stage': a.stage, 'notebook_order': order,
           'runner_sha256': sha256(Path(__file__).resolve()), 'runner_python': sys.executable, 'kernel_argv': spec['argv'],
           'roots': {k: str(v) for k, v in roots.items()}, 'offline': a.offline, 'refresh': a.refresh, 'cell_timeout_seconds': timeout,
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
            NotebookClient(nb, timeout=timeout, kernel_name=KERNEL_NAME, resources={'metadata': {'path': str(NB_DIR)}},
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
