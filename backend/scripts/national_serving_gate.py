"""National V4: after notebook 21 (evaluation) finished, write config/spatial_inference_v4.json and workflow/serving/input-pins-v4.json.
Usage (repo root): python3 backend/scripts/national_serving_gate.py --eval-root backend/rerun-spatial-eval-national-<stamp>
Refuses unless the 21 run log is ok and its manifest is complete with no failed hard check. Never overwrites."""
import argparse, hashlib, json, sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
EXP_ROOT = 'rerun-spatial-model-national-20261120-150631'
h = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def fail(m):
    sys.exit('SERVING GATE FAILED: ' + m)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--eval-root', required=True)
    a = ap.parse_args()
    ev = Path(a.eval_root).resolve()
    ev_rel = ev.relative_to(BACKEND).as_posix()
    log = json.loads((ev / 'reports/v3/run_manifest_spatial_evaluation.json').read_text())
    if log.get('status') != 'ok':
        fail('notebook 21 run status ' + str(log.get('status')))
    m21 = json.loads((ev / 'reports/v4/spatial_evaluation/spatial_evaluation_manifest.json').read_text())
    hard = [c['check'] for c in m21.get('checks', []) if c.get('status') == 'fail']
    if m21.get('status') != 'complete' or hard:
        fail('notebook 21 manifest ' + str(m21.get('status')) + ' failed ' + str(hard[:3]))
    for name, sha in m21['report_files'].items():
        if h(ev / 'reports/v4/spatial_evaluation' / name) != sha:
            fail('21 report hash mismatch ' + name)
    out_cfg, out_pins = BACKEND / 'config/spatial_inference_v4.json', REPO / 'workflow/serving/input-pins-v4.json'
    for p in (out_cfg, out_pins):
        if p.exists():
            fail(str(p) + ' exists (never overwritten)')
    c = json.loads((BACKEND / 'config/spatial_inference_v3.json').read_text())
    c['version'] = 'spatial_inference_v4.0'
    c['notebook'] = 'notebooks/22_spatial_inference_contract_national.ipynb'
    c['registered_by'] = 'national-coverage (Claude, 2026-11-20) after the national notebook-20 (' + EXP_ROOT + ') and notebook-21 (' + ev_rel + ') runs'
    c['pins'] = dict(c['pins'], path='../workflow/serving/input-pins-v4.json')
    I = c['inputs']
    I['notebook19']['path'] = 'notebooks/19_spatial_count_preparation_national.ipynb'
    I['notebook20']['path'] = 'notebooks/20_spatial_count_experiments_national.ipynb'
    I['notebook21']['path'] = 'notebooks/21_spatial_evaluation_colours_national.ipynb'
    I.update(config19='config/spatial_preparation_v4.json', config20='config/spatial_experiment_v4.json', config21='config/spatial_evaluation_v4.json',
             manifest19='reports/v4/spatial_preparation/spatial_preparation_manifest.json', prepared_data_dir='data/v4/spatial_preparation',
             experiment_root=EXP_ROOT, experiment_report_dir='reports/v4/spatial_experiments', experiment_data_dir='data/v4/spatial_experiments',
             evaluation_root=ev_rel, evaluation_report_dir='reports/v4/spatial_evaluation')
    c['artifact'] = dict(c['artifact'], model_version='roadaware-spatial-v4-national-benchmark-issue-2023-12-31T18')
    c['caveats'] = [x.replace('Only the 3105 qualified DOH segments', 'Only the 26,740 qualified national DOH segments') for x in c['caveats']]
    c['guarded_roots'] = [EXP_ROOT, ev_rel]
    c['protected_paths'] = sorted(set(c['protected_paths'] + [
        'reports/v4/spatial_preparation', 'data/v4/spatial_preparation', EXP_ROOT + '/reports', EXP_ROOT + '/data/v4/spatial_experiments/models',
        EXP_ROOT + '/data/v4/spatial_experiments/arrays_index.json', EXP_ROOT + '/data/v4/spatial_experiments/model_bundles.json', ev_rel + '/reports',
        'config/spatial_preparation_v4.json', 'config/spatial_experiment_v4.json', 'config/spatial_evaluation_v4.json',
        'notebooks/19_spatial_count_preparation_national.ipynb', 'notebooks/20_spatial_count_experiments_national.ipynb',
        'notebooks/21_spatial_evaluation_colours_national.ipynb', 'notebooks/22_spatial_inference_contract.ipynb']))
    c['outputs'] = {'report_dir': 'reports/v4/spatial_serving', 'data_dir': 'data/v4/spatial_serving'}
    p3 = json.loads((REPO / 'workflow/serving/input-pins-v3.json').read_text())
    rels = ['notebooks/20_spatial_count_experiments_national.ipynb', 'config/spatial_experiment_v4.json',
            EXP_ROOT + '/reports/v4/spatial_experiments/spatial_experiments_manifest.json', EXP_ROOT + '/reports/v4/spatial_experiments/experiment_lock.json',
            EXP_ROOT + '/reports/v4/spatial_experiments/selection_frozen.json', EXP_ROOT + '/data/v4/spatial_experiments/arrays_index.json',
            EXP_ROOT + '/data/v4/spatial_experiments/model_bundles.json', 'reports/v4/spatial_preparation/spatial_preparation_manifest.json',
            'notebooks/19_spatial_count_preparation_national.ipynb', 'config/spatial_preparation_v4.json',
            'notebooks/21_spatial_evaluation_colours_national.ipynb', 'config/spatial_evaluation_v4.json',
            ev_rel + '/reports/v4/spatial_evaluation/spatial_evaluation_manifest.json',
            ev_rel + '/reports/v4/spatial_evaluation/colour_contract_daily.json', ev_rel + '/reports/v4/spatial_evaluation/colour_contract_6h.json']
    files = {'backend/' + r: h(BACKEND / r) for r in rels}
    pv4 = json.loads((REPO / 'workflow/spatial/experiment-input-pins-v4.json').read_text())
    sel = json.loads((BACKEND / EXP_ROOT / 'reports/v4/spatial_experiments/selection_frozen.json').read_text())
    pins = {'kind': p3['kind'], 'experiment_root': 'backend/' + EXP_ROOT, 'evaluation_root': 'backend/' + ev_rel, 'files': files,
            'functions_sha256': {'notebook19': pv4['notebook19_functions_sha256'], 'notebook21': m21.get('functions_sha256')},
            'selection': p3['selection'], 'notes': 'national V4 serving pins (Claude) from verified notebook-20/21 runs; ' + p3['notes']}
    out_cfg.write_text(json.dumps(c, indent=2, ensure_ascii=False) + '\n')
    out_pins.write_text(json.dumps(pins, indent=2, ensure_ascii=False) + '\n')
    print('serving gate ok:', len(files), 'pinned files; selection', p3['selection'], '| 21 functions', str(m21.get('functions_sha256'))[:12])


if __name__ == '__main__':
    main()
