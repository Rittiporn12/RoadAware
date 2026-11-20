"""Fail-closed runtime bootstrap for the local research API (task 019).

Order: manager lock (workflow/api/input-pins-v3.json) structure and the manager-filled notebook-24/config pins -> every lock-pinned file hash ->
notebook-24 FUNCTIONS hash -> per component: accepted record files/hashes -> pinned FUNCTIONS hash -> the component's own loader (13
load_registry, 14 load_catalog, 22 load_service), which re-verifies its downstream chain before any deserialization. Nothing is trusted from
current bytes alone, no client path is ever used, nothing is fitted or downloaded. Any failure leaves that component 'unavailable' with a
stable code; details go to the local log only.
"""
import csv
import hashlib
import json
import logging
import os
import threading
from contextlib import nullcontext
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[2]
# Variant: pilot V3 (default) or national V4, chosen by the server launcher (run_api_server.py --national) before import.
VARIANTS = {'v3': ('workflow/api/input-pins-v3.json', 'backend/config/backend_api_v3.json'),
            'v4': ('workflow/api/input-pins-v4.json', 'backend/config/backend_api_v4.json')}
API_VARIANT = os.environ.get('ROADAWARE_API_VARIANT', 'v3')
if API_VARIANT not in VARIANTS:
    raise ValueError('ROADAWARE_API_VARIANT must be one of ' + ', '.join(VARIANTS))
LOCK_REL, CONFIG_REL = VARIANTS[API_VARIANT]
LOCK_KIND = 'manager_accepted_backend_api_inputs_v3'
COMPONENTS = ('notebook24', 'spatial_runtime', 'province_runtime', 'catalog', 'geometry', 'evaluation', 'diagnostics_2026')
log = logging.getLogger('roadaware.api')


class StartupError(Exception):
    def __init__(self, code, detail):
        super().__init__(code + ': ' + detail)
        self.code, self.detail = code, detail


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def _is_sha(v):
    return isinstance(v, str) and len(v) == 64 and all(c in '0123456789abcdef' for c in v)


def safe_rel(rel):
    p = Path(rel)
    if not isinstance(rel, str) or not rel or p.is_absolute() or '..' in p.parts:
        raise StartupError('artifact_inconsistent', 'pinned path must be repository-relative: ' + repr(rel))
    return rel


def verify_file(repo, rel, expected, label):
    if not _is_sha(expected):
        raise StartupError('artifact_unavailable', label + ': no trusted sha256 (fail closed)')
    p = Path(repo) / safe_rel(rel)
    if p.is_symlink() or not p.is_file():
        raise StartupError('artifact_missing', label + ': missing ' + str(p))
    got = sha256_file(p)
    if got != expected:
        raise StartupError('artifact_hash_mismatch', label + ': sha256 ' + got[:12] + ' != trusted ' + expected[:12] + ' (' + str(p) + ')')
    return p


def read_strict_json(path):
    def bad(c):
        raise StartupError('artifact_inconsistent', 'non-finite JSON constant in ' + str(path))
    return json.loads(Path(path).read_text('utf-8'), parse_constant=bad)


def exec_functions(nb_path, n_cells, join, expected_sha, label):
    """Exec ONLY the '# FUNCTIONS' code cells after their count and joined sha equal the trusted pin (the notebook file is pinned too)."""
    if not _is_sha(expected_sha):
        raise StartupError('artifact_unavailable', label + ': no trusted FUNCTIONS sha256 (fail closed)')
    nb = json.loads(Path(nb_path).read_text('utf-8'))
    srcs = [''.join(c['source']) if isinstance(c['source'], list) else c['source'] for c in nb['cells'] if c.get('cell_type') == 'code']
    funcs = [s for s in srcs if s.lstrip().startswith('# FUNCTIONS')]
    sha = hashlib.sha256(join.join(funcs).encode('utf-8')).hexdigest()
    if len(funcs) != int(n_cells) or sha != expected_sha:
        raise StartupError('artifact_hash_mismatch', label + ' FUNCTIONS sha ' + sha[:12] + ' (' + str(len(funcs)) + ' cells) != trusted ' + expected_sha[:12])
    ns = {'__name__': label + '_functions'}
    for i, s in enumerate(funcs):
        exec(compile(s, label + ':FUNCTIONS[' + str(i) + ']', 'exec'), ns)
    return ns


def check_lock(lock, cfg_required):
    """Structure + manager-filled API pins, checked BEFORE hashing anything big. Missing 24/config pins -> api_pins_pending (fail closed)."""
    if not isinstance(lock, dict) or lock.get('kind') != LOCK_KIND or not isinstance(lock.get('files'), dict) or not isinstance(lock.get('components'), dict):
        raise StartupError('artifact_unavailable', 'manager lock missing or of the wrong kind')
    pend = [r for r in cfg_required if not _is_sha(lock['files'].get(r))]
    fn = lock.get('notebook24_functions')
    if pend or not (isinstance(fn, dict) and _is_sha(fn.get('sha256')) and isinstance(fn.get('cells'), int) and fn.get('join') == '\n\n'):
        raise StartupError('api_pins_pending', 'manager has not pinned notebook 24 / backend_api_v3.json yet: ' + str(pend or ['notebook24_functions']))
    return fn


def _unavailable(code):
    return {'status': 'unavailable', 'code': code}


class Runtime:
    """Immutable-after-start holder of verified components. Methods return API bodies or raise the notebook-24 ApiError."""

    def __init__(self, components, h24=None, cfg=None, lock_sha=None, **parts):
        self.components, self.h24, self.cfg, self.lock_sha = components, h24, cfg, lock_sha
        self.spatial, self.ns22 = parts.get('spatial'), parts.get('ns22')
        self.registry, self.ns13 = parts.get('registry'), parts.get('ns13')
        self.catalog, self.ns14 = parts.get('catalog'), parts.get('ns14')
        self.geometry, self.eval21, self.diag23 = parts.get('geometry'), parts.get('eval21'), parts.get('diag23')
        self.spatial_meta, self.province_summary = parts.get('spatial_meta'), parts.get('province_summary')
        self._infer = threading.Lock()  # one inference at a time; bundles/caches are read-only

    @property
    def ready(self):
        req = (self.cfg or {}).get('required_components') or [c for c in COMPONENTS if c != 'province_runtime']
        return self.h24 is not None and all(self.components.get(c, {}).get('status') == 'available' for c in req)

    def public_components(self):
        return {k: dict(v) for k, v in self.components.items()}

    def _need(self, name):
        if self.h24 is None:
            raise StartupError('artifact_unavailable', 'notebook 24 not loaded')
        if self.components.get(name, {}).get('status') != 'available':
            raise self.h24['ApiError']('component_unavailable', 'unavailable', name + ' unavailable')

    def _limits(self):
        try:
            from threadpoolctl import threadpool_limits
            return threadpool_limits(limits=int(self.cfg['limits']['inference_threads']))
        except ImportError:
            return nullcontext()

    # ---------- read endpoints ----------
    def metadata(self):
        self._need('notebook24')
        h = self.h24
        cs = self.ns14['catalog_summary'](self.catalog) if self.catalog is not None else None
        ev = {'evaluation': self.components.get('evaluation'), 'diagnostics_2026': self.components.get('diagnostics_2026')}
        return h['api_metadata'](self.cfg, self.public_components(), self.spatial_meta, cs, self.province_summary, self.geometry, ev)

    def evaluation(self):
        self._need('evaluation')
        if 'diagnostics_2026' in ((self.cfg or {}).get('required_components') or COMPONENTS):
            self._need('diagnostics_2026')
        return self.h24['ok_body']({'spatial_evaluation_21': self.eval21, 'diagnostics_2026': self.diag23})

    def provinces(self):
        self._need('catalog')
        return self.h24['ok_body'](self.ns14['list_provinces'](self.catalog))

    def province_history(self, params):
        self._need('catalog')
        h = self.h24
        q = h['strict_query'](params, ('province_key', 'start_month', 'end_month', 'categories', 'top_k'), 'history')
        req = h['province_history_request'](q, self.cfg['limits']['history']['max_top_k'])
        try:
            return h['ok_body']({'history': self.ns14['query_province_history'](self.catalog, req)})
        except self.ns14['CatalogQueryError'] as e:
            raise h['catalog_query_error'](e.errors)
        except self.ns14['CatalogError'] as e:
            raise self._catalog_guard(e)

    def _catalog_guard(self, e):
        log.error('notebook-14 internal guard refused an answer: %s', e)
        return self.h24['ApiError']('catalog_internal_guard', 'unavailable', 'catalog refused to answer')

    def spatial_history(self, body):
        self._need('catalog')
        h = self.h24
        req = h['spatial_history_body'](body)
        try:
            res = self.ns14['query_spatial_history'](self.catalog, req)
        except self.ns14['CatalogQueryError'] as e:
            raise h['catalog_query_error'](e.errors)
        except self.ns14['CatalogError'] as e:
            raise self._catalog_guard(e)
        return h['spatial_history_period'](res, self.catalog['months'][0], self.catalog['months'][-1])

    def segments(self, params):
        self._need('geometry')
        h, L = self.h24, self.cfg['limits']['geometry']
        q = h['strict_query'](params, ('bbox', 'limit', 'cursor'), 'segments')
        bbox = h['parse_bbox'](q.get('bbox'), L)
        lim, cur = h['parse_page'](q, L)
        return h['query_segments'](self.geometry, bbox, lim, cur, self.cfg['geometry']['snapshot'])

    def segment(self, segment_id):
        self._need('geometry')
        uns = self.spatial['ctx']['unsupported'] if self.spatial is not None else frozenset()
        return self.h24['get_segment'](self.geometry, segment_id, uns, self.cfg['geometry']['snapshot'])

    # ---------- predictions ----------
    def spatial_predict(self, body, which):
        self._need('spatial_runtime')
        h = self.h24
        unit, reqs = h['spatial_prediction_body'](body)
        fn = self.ns22['predict_batch' if which == 'selected' else 'predict_baseline_batch']
        with self._infer, self._limits():
            res = fn(self.spatial, unit, reqs)
        return h['spatial_answer'](res)

    def province_predict(self, body):
        self._need('province_runtime')
        h = self.h24
        reqs = h['province_prediction_body'](body)
        try:
            with self._infer, self._limits():
                res = self.ns13['predict_batch'](self.registry, reqs)
        except self.ns13['RequestValidationError'] as e:
            raise h['province_request_error'](e.errors)
        except (self.ns13['DependencyError'], ValueError) as e:  # registry/prediction refused server-side: never a fallback
            log.error('notebook-13 prediction refused: %s', e)
            raise h['ApiError']('prediction_invalid', 'unavailable', 'province runtime refused the prediction')
        return h['ok_body']({'province_prediction_v2': res})


def _record(repo, lock, name):
    rel = lock['components'][name]
    if rel not in lock['files']:
        raise StartupError('artifact_unavailable', 'component record ' + name + ' not pinned by the manager lock')
    return read_strict_json(Path(repo) / rel)


def _verify_record_files(repo, rec, label):
    for rel, sha in sorted((rec.get('files') or {}).items()):
        verify_file(repo, rel, sha, label + ' ' + rel)


def _load_spatial(repo, lock, cfg, parts):
    rec, C = _record(repo, lock, 'spatial_runtime'), cfg['components']['spatial_runtime']
    _verify_record_files(repo, rec, 'spatial record')
    for k in ('notebook', 'config', 'pins'):
        if C[k] not in rec['files']:
            raise StartupError('artifact_unavailable', 'spatial ' + k + ' not pinned by the accepted record')
    F = rec['functions']
    ns = exec_functions(Path(repo) / C['notebook'], F['cells'], F['join'], F['sha256'], 'notebook22')
    srec_rel = rec['report_dir'] + '/' + C['serving_record']
    if srec_rel not in rec['files']:
        raise StartupError('artifact_unavailable', 'serving record not pinned')
    srec = read_strict_json(Path(repo) / srec_rel)
    bf = {}
    for u, v in srec['baseline_stats'].items():
        rel = rec['data_dir'] + '/' + v['file']
        if rec['files'].get(rel) != v['sha256']:
            raise StartupError('artifact_inconsistent', 'baseline stats ' + u + ' differ from the accepted record')
        bf[u] = (Path(repo) / rel, v['sha256'])
    svc = ns['load_service'](Path(repo) / 'backend', read_strict_json(Path(repo) / C['config']), read_strict_json(Path(repo) / C['pins']), bf,
                             selftest=bool(C.get('selftest', True)))
    if svc['status'] != 'available':
        log.error('notebook-22 load_service unavailable: %s', dict(svc['error']))
        raise StartupError(svc['error']['code'], 'notebook-22 service unavailable')
    parts.update(spatial=svc, ns22=ns, spatial_meta=ns['metadata'](svc))


def _load_province(repo, lock, cfg, parts):
    rec, C = _record(repo, lock, 'province_runtime'), cfg['components']['province_runtime']
    _verify_record_files(repo, rec, 'province record')
    for k in ('notebook', 'config'):
        if C[k] not in rec['files']:
            raise StartupError('artifact_unavailable', 'province ' + k + ' not pinned by the accepted record')
    F = rec['functions']
    ns = exec_functions(Path(repo) / C['notebook'], F['cells'], F['join'], F['sha256'], 'notebook13')
    try:
        reg = ns['load_registry'](Path(repo) / 'backend')
    except ns['DependencyError'] as e:
        log.error('notebook-13 load_registry refused: %s', e)
        raise StartupError('artifact_unavailable', 'notebook-13 registry unavailable')
    parts.update(registry=reg, ns13=ns, province_summary=ns['json_safe'](ns['registry_summary'](reg)) if 'json_safe' in ns else ns['registry_summary'](reg))


def _load_catalog(repo, lock, cfg, parts):
    rec, C = _record(repo, lock, 'catalog'), cfg['components']['catalog']
    verify_file(repo, rec['source_notebook'], rec['source_notebook_sha256'], 'catalog source notebook')
    verify_file(repo, rec['config'], rec['config_sha256'], 'catalog config')
    ns = exec_functions(Path(repo) / rec['source_notebook'], C['functions_cells'], C['functions_join'], rec['functions_sha256'], 'notebook14')
    try:
        cat = ns['load_catalog'](Path(repo) / rec['report_dir'], Path(repo) / rec['data_dir'], Path(repo) / rec['config'], rec['manifest_sha256'],
                                 rec['functions_sha256'], rec['config_sha256'], Path(repo) / rec['source_notebook'])
    except ns['CatalogError'] as e:
        log.error('notebook-14 load_catalog refused: %s', e)
        raise StartupError('artifact_unavailable', 'catalog unavailable')
    parts.update(catalog=cat, ns14=ns)


def _load_geometry(repo, lock, cfg, h24, parts):
    G = cfg['geometry']
    for rel in (G['manifest'], G['geojson'], G['segments_csv']):
        if rel not in lock['files']:
            raise StartupError('artifact_unavailable', 'geometry file not pinned by the manager lock: ' + rel)
    man = read_strict_json(Path(repo) / G['manifest'])
    d = man.get('data_files_gitignored') or {}
    if man.get('status') != 'complete' or d.get(Path(G['geojson']).name) != lock['files'][G['geojson']] or d.get(Path(G['segments_csv']).name) != lock['files'][G['segments_csv']]:
        raise StartupError('artifact_inconsistent', 'geometry files differ from the accepted notebook-19 manifest')
    fc = read_strict_json(Path(repo) / G['geojson'])
    seg = pd.read_csv(Path(repo) / G['segments_csv'], dtype=str, keep_default_na=False)
    expected = list(parts['spatial']['seg_index']) if parts.get('spatial') is not None else None
    parts['geometry'] = h24['build_geometry_index'](fc, seg, expected, cfg['limits']['geometry'])


def _load_evaluation(repo, lock, cfg, h24, parts):
    rec, C = _record(repo, lock, 'evaluation'), cfg['components']['evaluation']
    p = verify_file(repo, rec['root'] + '/' + C['manifest'], rec['manifest_sha256'], 'spatial evaluation manifest')
    man = read_strict_json(p)
    mp = verify_file(repo, rec['root'] + '/' + C['metrics'], (man.get('report_files') or {}).get(Path(C['metrics']).name), 'spatial evaluation metrics')
    with open(mp, newline='', encoding='utf-8') as f:  # read only after its sha256 equals the pinned 21 manifest entry
        rows = list(csv.DictReader(f))
    parts['eval21'] = h24['evaluation_21_summary'](rec, man, rows)


def _load_diagnostics(repo, lock, cfg, h24, parts):
    rec, C = _record(repo, lock, 'diagnostics_2026'), cfg['components']['diagnostics_2026']
    _verify_record_files(repo, rec, 'diagnostics record')
    mrel = rec['report_dir'] + '/' + C['manifest']
    if mrel not in rec['files']:
        raise StartupError('artifact_unavailable', '2026 manifest not pinned by the accepted record')
    man = read_strict_json(Path(repo) / mrel)
    mp = verify_file(repo, rec['report_dir'] + '/' + C['metrics'], (man.get('report_files') or {}).get(C['metrics']), '2026 metrics')
    with open(mp, newline='', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    parts['diag23'] = h24['diagnostics_2026_summary'](rec, man, rows)


def load_runtime(repo=REPO, lock_rel=LOCK_REL, config_rel=CONFIG_REL):
    """Never raises: returns a Runtime whose components are each 'available' or 'unavailable' with a stable code."""
    repo = Path(repo)
    comps = {c: _unavailable('not_loaded') for c in COMPONENTS}
    try:
        lock = read_strict_json(repo / lock_rel)
        cfg_required = lock.get('required_api_files_pending_manager_review') or [config_rel]
        fn24 = check_lock(lock, sorted(set(cfg_required) | {config_rel}))
        for rel, sha in sorted(lock['files'].items()):
            verify_file(repo, rel, sha, 'manager lock ' + rel)
        cfg = read_strict_json(repo / config_rel)
        if cfg.get('manager_lock') != lock_rel or cfg['notebook24']['path'] not in lock['files']:
            raise StartupError('artifact_inconsistent', 'config does not name this manager lock / notebook 24 is not lock-pinned')
        h24 = exec_functions(repo / cfg['notebook24']['path'], fn24['cells'], fn24['join'], fn24['sha256'], 'notebook24')
        if fn24['cells'] != cfg['notebook24']['functions_cells']:
            raise StartupError('artifact_inconsistent', 'notebook-24 FUNCTIONS cell count differs from the config')
    except StartupError as e:
        log.error('API startup refused: %s', e)
        comps['notebook24'] = _unavailable(e.code)
        return Runtime(comps)
    except Exception as e:  # malformed lock/config: explicit unavailable, never a partial service
        log.exception('API startup failed')
        comps['notebook24'] = _unavailable('artifact_unavailable')
        return Runtime(comps)
    comps['notebook24'] = {'status': 'available', 'code': None}
    parts = {}
    optional_absent = {n for n in ('diagnostics_2026',) if n not in lock['components'] and n not in (cfg.get('required_components') or [])}
    steps = (('spatial_runtime', lambda: _load_spatial(repo, lock, cfg, parts)), ('province_runtime', lambda: _load_province(repo, lock, cfg, parts)),
             ('catalog', lambda: _load_catalog(repo, lock, cfg, parts)), ('geometry', lambda: _load_geometry(repo, lock, cfg, h24, parts)),
             ('evaluation', lambda: _load_evaluation(repo, lock, cfg, h24, parts)), ('diagnostics_2026', lambda: _load_diagnostics(repo, lock, cfg, h24, parts)))
    api_error = h24.get('ApiError', StartupError)
    for name, fn in steps:
        if name in optional_absent:
            comps[name] = {'status': 'unavailable', 'code': 'not_configured', 'note': 'optional component not part of this API variant'}
            continue
        try:
            fn()
            comps[name] = {'status': 'available', 'code': None}
        except StartupError as e:
            log.error('component %s unavailable: %s', name, e)
            comps[name] = _unavailable(e.code)
        except api_error as e:
            log.error('component %s unavailable: %s', name, e)
            comps[name] = _unavailable(e.code)
        except Exception:
            log.exception('component %s failed', name)
            comps[name] = _unavailable('artifact_unavailable')
    if cfg['components']['province_runtime'].get('optional') and comps['province_runtime']['status'] != 'available':
        comps['province_runtime']['note'] = 'optional V2 compatibility service unavailable: POST /api/v1/predictions answers 503'
    return Runtime(comps, h24, cfg, lock_sha=sha256_file(repo / lock_rel), **parts)
