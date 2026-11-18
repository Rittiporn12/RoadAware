"""National coverage gate between notebook 19 (preparation) and notebook 20 (experiments).

Usage (repository root, project .venv):
    .venv/bin/python backend/scripts/national_prep_gate.py --run-root backend/rerun-spatial-prep-national-001

1. Verifies the notebook-19 V4 run: run log ok, manifest complete, every check pass, protected files unchanged,
   every report/data file hash equal to the manifest.
2. Promotes (copies, never overwrites) the outputs into backend/reports/v4/spatial_preparation and
   backend/data/v4/spatial_preparation, then re-hashes the copies.
3. Writes the automated gate review reports/v4/spatial_preparation_independent_review.json.
4. Registers the geometry-only national transfer split (workflow/spatial/spatial-transfer-preregistration-v4.json)
   from universe GEOMETRY only (no labels, no scores) with the exact notebook-20 rule.
5. Writes the notebook-20 input pins (workflow/spatial/experiment-input-pins-v4.json) and
   config/spatial_experiment_v4.json (v3 rules unchanged; national sizes, paths, budget and threads).
Refuses to overwrite anything that already exists. Nothing here reads a label for the split or any model score.
"""
import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
PREP_CFG = 'config/spatial_preparation_v4.json'
EXP_V3 = 'config/spatial_experiment_v3.json'
EXP_V4 = 'config/spatial_experiment_v4.json'
PINS_V4 = 'workflow/spatial/experiment-input-pins-v4.json'
PRE_V4 = 'workflow/spatial/spatial-transfer-preregistration-v4.json'
REVIEW = 'reports/v4/spatial_preparation_independent_review.json'
# Contiguous upper-northeast block (Sakon Nakhon, Nakhon Phanom, Mukdahan, Kalasin/Roi Et east, Amnat Charoen, Yasothon, Ubon north)
PREDICATE = {'lon_gte': 103.0, 'lat_gte': 15.5}
BUFFER_M = 1000
THREADS = 6
ARTIFACT_BUDGET = 64 * (1 << 30)


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def fail(msg):
    sys.exit('GATE FAILED: ' + msg + '\nNothing after this point was written.')


def write_new(path, obj):
    path = Path(path)
    if path.exists():
        fail(f'{path} already exists (never overwritten)')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + '\n', 'utf-8')
    return sha(path)


def ids_sha_lines(ids):
    return hashlib.sha256('\n'.join(sorted(ids)).encode('utf-8')).hexdigest()


def transfer_split(seg, geojson_path):
    """Same rule as notebook 20 transfer_split: eval = midpoint lon >= L AND lat >= A; training drops eval-source-OID
    segments and segments within BUFFER_M (EPSG:32647) of any eval segment."""
    from pyproj import Transformer
    from shapely import STRtree
    from shapely.geometry import LineString
    ids = seg.index.to_numpy(object)
    ev = (seg['geom_mid_lon'].to_numpy(float) >= PREDICATE['lon_gte']) & (seg['geom_mid_lat'].to_numpy(float) >= PREDICATE['lat_gte'])
    oid = seg['oid'].to_numpy(float).astype(np.int64)
    eoids = set(oid[ev].tolist())
    same = ~ev & np.isin(oid, list(eoids))
    fc = json.loads(Path(geojson_path).read_text('utf-8'))
    fwd = Transformer.from_crs(4326, 32647, always_xy=True)
    geom = {}
    for f in fc['features']:
        c = np.asarray(f['geometry']['coordinates'], float)
        x, y = fwd.transform(c[:, 0], c[:, 1])
        geom[f['id']] = LineString(np.column_stack([x, y]))
    if set(geom) != set(ids):
        fail('universe geometry ids differ from universe segments')
    eg = [geom[i] for i in ids[ev]]
    tree = STRtree(eg)
    dist = np.full(len(ids), np.inf)
    for j in np.flatnonzero(~ev & ~same):
        g = geom[ids[j]]
        near = tree.query(g, predicate='dwithin', distance=BUFFER_M)
        dist[j] = min((g.distance(eg[k]) for k in near), default=np.inf)
    drop = ~ev & ~same & (dist < BUFFER_M)
    tr = ~ev & ~same & ~drop
    eval_ids, train_ids = sorted(ids[ev].tolist()), sorted(ids[tr].tolist())
    toids = set(oid[tr].tolist())
    return {'eval_ids': eval_ids, 'train_ids': train_ids, 'eval_source_oids': len(eoids), 'train_source_oids': len(toids),
            'removed_same_source_oid': int(same.sum()), 'removed_buffer_additional': int(drop.sum()), 'disjoint': not (eoids & toids)}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--run-root', required=True)
    a = ap.parse_args()
    run = Path(a.run_root).resolve()
    pcfg = json.loads((BACKEND / PREP_CFG).read_text('utf-8'))
    rdir, ddir = pcfg['outputs']['report_dir'], pcfg['outputs']['data_dir']

    # 1. verify the run
    log = json.loads((run / 'reports' / 'v3' / 'run_manifest_spatial_preparation.json').read_text('utf-8'))
    if log.get('status') != 'ok':
        fail('notebook 19 run log status ' + str(log.get('status')))
    man_p = run / rdir / 'spatial_preparation_manifest.json'
    m = json.loads(man_p.read_text('utf-8'))
    if m.get('status') != 'complete' or m.get('version') != pcfg['version']:
        fail(f"manifest status/version {m.get('status')} {m.get('version')}")
    bad = [c['check'] for c in m['checks'] if c.get('status') != 'pass']
    if bad:
        fail('failed notebook checks: ' + str(bad[:5]))
    if m.get('protected_unchanged') is not True:
        fail('protected files changed during the run')
    if m.get('snapshot_tag') != pcfg['snapshot_tag']:
        fail('snapshot tag mismatch')
    for name, h in m['report_files'].items():
        if sha(run / rdir / name) != h:
            fail('report hash mismatch ' + name)
    for name, h in m['data_files_gitignored'].items():
        if sha(run / ddir / name) != h:
            fail('data hash mismatch ' + name)
    for p in (BACKEND / rdir, BACKEND / ddir, BACKEND / REVIEW, BACKEND / EXP_V4, REPO / PINS_V4, REPO / PRE_V4):
        if p.exists():
            fail(f'{p} already exists (never overwritten)')
    print(f"run verified: {len(m['checks'])} checks pass, {len(m['report_files'])} report + {len(m['data_files_gitignored'])} data hashes ok")

    # 2. promote
    shutil.copytree(run / rdir, BACKEND / rdir)
    shutil.copytree(run / ddir, BACKEND / ddir)
    for name, h in m['report_files'].items():
        if sha(BACKEND / rdir / name) != h:
            fail('promoted report hash mismatch ' + name)
    for name, h in m['data_files_gitignored'].items():
        if sha(BACKEND / ddir / name) != h:
            fail('promoted data hash mismatch ' + name)
    print('promoted to', rdir, 'and', ddir)

    # 3. automated gate review
    s = m.get('summary', {})
    review = {'status': 'accepted_spatial_count_preparation_v4_automated_gate', 'all_checks_pass': True,
              'reviewer': 'automated gate (scripts/national_prep_gate.py); Claude re-checks before any model is accepted',
              'run_root': str(run.relative_to(REPO)), 'manifest_sha256': m['report_files'].get('spatial_preparation_manifest.json') or sha(man_p),
              'checks': len(m['checks']), 'report_hashes': len(m['report_files']), 'data_hashes': len(m['data_files_gitignored']),
              'snapshot_tag': m['snapshot_tag'], 'summary': s, 'protected_unchanged': True}
    write_new(BACKEND / REVIEW, review)

    # 4. geometry-only transfer preregistration
    seg = pd.read_csv(BACKEND / ddir / 'universe_segments.csv', dtype={'segment_id': str, 'route_code': str}).set_index('segment_id')
    sp = transfer_split(seg, BACKEND / ddir / 'universe_geometry.geojson')
    pre = {'status': 'geometry_only_preregistered_split_no_labels_or_scores_read', 'universe_segments': int(len(seg)),
           'eval_midpoint_predicate': PREDICATE, 'buffer_m_epsg32647': BUFFER_M, 'exclude_training_features_sharing_eval_source_oid': True,
           'eval_segments': len(sp['eval_ids']), 'eval_source_oids': sp['eval_source_oids'], 'train_segments': len(sp['train_ids']),
           'train_source_oids': sp['train_source_oids'], 'removed_same_source_oid': sp['removed_same_source_oid'],
           'removed_buffer_additional': sp['removed_buffer_additional'], 'train_source_oids_disjoint': sp['disjoint'],
           'eval_segment_ids_sha256': ids_sha_lines(sp['eval_ids']), 'train_segment_ids_sha256': ids_sha_lines(sp['train_ids']),
           'interpretation': 'National V4: contiguous upper-northeast unseen-sections transfer diagnostic (midpoint lon>=103.0, lat>=15.5), registered from geometry only after notebook 19 and before notebook 20. Not all-new-route or untouched-future evaluation; never reranks the temporal winner.'}
    if not pre['eval_segments'] or not pre['train_segments'] or not sp['disjoint']:
        fail('degenerate transfer split ' + json.dumps({k: v for k, v in pre.items() if 'sha' not in k}))
    pre_sha = write_new(REPO / PRE_V4, pre)
    print(f"transfer split: eval {pre['eval_segments']} / train {pre['train_segments']} of {pre['universe_segments']}")

    # 5. pins + experiment config v4
    c3 = json.loads((BACKEND / EXP_V3).read_text('utf-8'))
    p3 = json.loads((REPO / c3['pins']['path'].replace('../', '')).read_text('utf-8'))
    files = {'backend/' + rdir + '/spatial_preparation_manifest.json': sha(BACKEND / rdir / 'spatial_preparation_manifest.json'),
             'backend/' + REVIEW: sha(BACKEND / REVIEW), 'backend/' + PREP_CFG: sha(BACKEND / PREP_CFG),
             'workflow/spatial-model-protocol-v3-draft.md': sha(REPO / 'workflow/spatial-model-protocol-v3-draft.md'),
             'workflow/spatial-model-protocol-v3-addendum.md': sha(REPO / 'workflow/spatial-model-protocol-v3-addendum.md'),
             PRE_V4: pre_sha}
    pins = {'registered_before_spatial_model_scores': True, 'files': files,
            'notebook19_functions_sha256': m['functions_cells_sha256'], 'notebook19_code_cells_sha256': m['code_cells_sha256'],
            'prepared_data_hashes': m['data_files_gitignored'], 'feature_columns': m['feature_columns']}
    if set(pins) != set(p3):
        fail('pins keys differ from v3 layout: ' + str(set(pins) ^ set(p3)))
    write_new(REPO / PINS_V4, pins)

    c = json.loads(json.dumps(c3))
    c['version'] = 'spatial_experiment_v4.0'
    c['registered_by'] = 'national-coverage (2026-11-18): v3 rules, candidates, metrics and selection unchanged; national inputs, sizes, split, artifact budget and threads'
    c['scope_label'] = 'V4 national'
    I = c['inputs']
    I['preparation_manifest'].update(path=rdir + '/spatial_preparation_manifest.json', pins_key='backend/' + rdir + '/spatial_preparation_manifest.json')
    I['preparation_review'].update(path=REVIEW, pins_key='backend/' + REVIEW)
    I['preparation_config'].update(path=PREP_CFG, pins_key='backend/' + PREP_CFG)
    I['transfer_preregistration'].update(path='../' + PRE_V4, pins_key=PRE_V4)
    I['prepared_data_dir'] = ddir
    c['pins'] = {'path': '../' + PINS_V4, 'note': c3['pins']['note'],
                 'expect': {'preparation_manifest_sha256': files['backend/' + rdir + '/spatial_preparation_manifest.json'],
                            'notebook19_functions_sha256': m['functions_cells_sha256'],
                            'protocol_draft_sha256': files['workflow/spatial-model-protocol-v3-draft.md'],
                            'protocol_addendum_sha256': files['workflow/spatial-model-protocol-v3-addendum.md'],
                            'transfer_preregistration_sha256': pre_sha}}
    axes = json.loads((BACKEND / ddir / 'population_axes.json').read_text('utf-8'))
    n = len(axes['segments'])
    f0, f1 = pd.Timestamp(c['time']['folds'][0]['start']), pd.Timestamp(c['time']['folds'][-1]['end'])
    days = (f1 - f0).days + 1
    c['time']['expected_oof_rows'] = {'daily': n * days, '6h': n * days * len(axes['blocks'])}
    c['resources'].update(artifact_budget_bytes=ARTIFACT_BUDGET, threads=THREADS)
    for cc in c['candidates']['configs']:
        if 'n_jobs' in cc['params']:
            cc['params']['n_jobs'] = THREADS  # compute only: fixed random_state, results do not depend on n_jobs
    extra = ['config/spatial_experiment_v3.json', 'config/spatial_preparation_v4.json',
             'reports/v4/road_collection', 'data/v4/road_collection', 'reports/v4/linkage_audit', 'data/v4/linkage_audit',
             'reports/v4/spatial_preparation', 'data/v4/spatial_preparation', REVIEW,
             'reports/v3/spatial_preparation', 'data/v3/spatial_preparation', 'rerun-spatial-model-016-002']
    c['protected_paths'] = c3['protected_paths'] + [p for p in extra if p and p not in c3['protected_paths'] and (BACKEND / p).exists()]
    c['outputs'] = {'report_dir': 'reports/v4/spatial_experiments', 'data_dir': 'data/v4/spatial_experiments'}
    write_new(BACKEND / EXP_V4, c)
    print(f"experiment config v4 written: universe {n} segments, expected OOF rows {c['time']['expected_oof_rows']}")
    print('GATE OK')


if __name__ == '__main__':
    main()
