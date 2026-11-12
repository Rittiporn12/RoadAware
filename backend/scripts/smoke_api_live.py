"""Live localhost HTTP smoke of the ACTUAL API process (task 019). From the repository root, after the manager filled the notebook-24/config pins:
    .venv/bin/python backend/scripts/smoke_api_live.py --run-root backend/rerun-api-019-004 [--port 8765] [--fixture-port 8766] [--startup-timeout 900]

1. Read-only evidence: hashes a BOUNDED consumed set (the manager lock itself as root trust anchor with its start-of-run sha256, the files it pins,
   accepted component records and the files they pin incl. baseline NPZ, the notebook-22 serving pins + the 4 chosen 22 bundles at models/<unit>/<file>,
   the 11 model manifest + chosen 13 selected/baseline bundles, 14 manifest outputs, 21 manifest + metrics, 23 manifest + metrics) against the trusted
   pins before the run and again after both servers stopped. Every chain link is parsed only after its hash equals its parent's pin; a missing link or
   chosen bundle, or a missing required category, fails the check.
2. Starts its OWN uvicorn subprocess (backend/scripts/run_api_server.py, 127.0.0.1 only), waits for /health then /ready, checks saved notebook-22
   prediction fixtures (both units, selected + baseline, exact results), saved notebook-13 examples, catalog province history vs the hash-verified
   province_monthly.csv, 21 evaluation numbers vs the hash-verified metrics_by_group.csv, geometry page walk/ID round trip, history cutoff and 2026
   period status, error/limit/CORS/body cases and sanitisation, every OpenAPI example with a request (backend/api/openapi_docs.py) and the served
   OpenAPI schemas; stops only that process.
3. TEST FIXTURE (not a production config): a COPY of the manager lock with one deliberately wrong pinned source hash is written inside the new run
   root; this CLI starts the same app with a server-side injected load_runtime(lock_rel=<that copy>) and checks /health 200, /ready 503 with a stable
   unavailable code, and a sanitised prediction 503 (no result, no zero). The real pins/artifacts are never modified; refusal happens before exec.
Writes bounded JSON evidence + the actual OpenAPI ONLY into the NEW run root. Exit 0 iff all checks pass.
"""
import argparse
import csv
import datetime as dt
import hashlib
import json
import os
import platform
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
RESULTS = []
SAMPLES = {}
OUT = {}


def check(name, ok, evidence=None):
    RESULTS.append({'check': name, 'passed': bool(ok), 'evidence': evidence if len(json.dumps(evidence, default=str)) < 2000 else str(evidence)[:2000]})
    print(('PASS ' if ok else 'FAIL ') + name + ('' if ok else ' | ' + str(evidence)[:300]), flush=True)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def jload(p):
    return json.loads(Path(p).read_text('utf-8'))


def port_free(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # TIME_WAIT is not "in use"; a live listener still refuses the bind
    try:
        s.bind(('127.0.0.1', port))
        return True
    except OSError:
        return False
    finally:
        s.close()


def leaks(text):
    return [m for m in ('/Users/', '/home/', 'Traceback', 'File "', '.joblib', 'backend/rerun-', 'event_uid', 'source_row') if m in text]


LOCK_REL = 'workflow/api/input-pins-v3.json'
CONFIG_REL = 'backend/config/backend_api_v3.json'
FIXTURE_DIR = 'fixture_wrong_source_hash'
FIXTURE_LOCK = 'TEST_FIXTURE_input-pins-wrong-source-hash.json'


SPATIAL_UNITS = ('daily', '6h')
ROOT_ANCHOR = 'root_trust_anchor_start_of_run_sha'  # the manager lock: trusted value = its bytes when this run started (it cannot pin itself)
# categories the bounded consumed set MUST contain (exact counts), so an empty or bundle-less set can never pass the read-only checks
REQUIRED_EXACT = {ROOT_ANCHOR: 1, 'spatial_chosen_bundle': 4, 'province_chosen_bundle': 4, 'spatial_baseline_stats': 2, 'evaluation_manifest': 1,
                  'diagnostics_manifest': 1}
REQUIRED_AT_LEAST = {'manager_lock': 1, 'spatial_runtime_record': 1, 'province_runtime_record': 1, 'diagnostics_2026_record': 1, 'spatial_serving_pins': 1,
                     'catalog_record': 3, 'catalog_manifest': 1, 'evaluation_record': 1, 'province_model_manifest': 1}


class ConsumedSetError(Exception):
    pass


def _need(ok, msg):
    if not ok:
        raise ConsumedSetError(msg)


def _safe_rel(rel):
    p = Path(rel)
    _need(not p.is_absolute() and '..' not in p.parts, 'unsafe path in an accepted manifest: ' + str(rel))
    return str(p)


def _verified_json(repo, rel, want, what):
    """Parse a chain link only after its bytes equal the hash pinned by its (already verified) parent; otherwise the chain is refused."""
    p = repo / _safe_rel(rel)
    _need(p.is_file() and not p.is_symlink(), what + ' missing: ' + rel)
    _need(isinstance(want, str) and sha(p) == want, what + ' differs from the hash pinned by its accepted parent: ' + rel)
    return jload(p)


def _bundle_entries(obj):
    """Every {'file': '*.joblib', 'sha256': ...} entry of a pinned notebook-20 model_bundles.json."""
    if isinstance(obj, dict):
        if isinstance(obj.get('file'), str) and obj['file'].endswith('.joblib') and isinstance(obj.get('sha256'), str):
            yield obj
        for v in obj.values():
            yield from _bundle_entries(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _bundle_entries(v)


def consumed_pins(repo=REPO):
    """Bounded consumed set {repo-relative path: (trusted sha256, origins)} taken ONLY from the manager lock and the accepted records/manifests it pins,
    each link parsed only after its hash equals its parent's pin. Not the whole raw history: just what the API startup and its component loaders consume.
    One physical file per path; origins lists every accepted chain that pins it (first = primary), e.g. the 21 manifest is pinned by both the 22 serving
    pins and the evaluation record. A missing chain link or chosen bundle, or one path pinned with two different hashes, raises ConsumedSetError (the
    read-only check then fails); nothing is silently skipped."""
    pins = {}

    def add(rel, s, origin):
        rel = _safe_rel(rel)
        if rel not in pins:
            pins[rel] = (s, (origin,))
            return
        _need(pins[rel][0] == s, 'conflicting trusted hashes for one consumed file (' + '/'.join(pins[rel][1]) + ' vs ' + origin + '): ' + rel)
        if origin not in pins[rel][1]:
            pins[rel] = (s, pins[rel][1] + (origin,))

    add(LOCK_REL, sha(repo / LOCK_REL), ROOT_ANCHOR)
    lock = jload(repo / LOCK_REL)
    for rel, s in lock['files'].items():
        add(rel, s, 'manager_lock')
    recs = {}
    for n, rel in lock['components'].items():
        _need(rel in lock['files'], 'component record not pinned by the manager lock: ' + n)
        recs[n] = _verified_json(repo, rel, lock['files'][rel], n + ' record')
    for n in ('spatial_runtime', 'province_runtime', 'diagnostics_2026'):
        for rel, s in (recs[n].get('files') or {}).items():
            add(rel, s, 'spatial_baseline_stats' if n == 'spatial_runtime' and rel.endswith('.npz') else n + '_record')
    _need(CONFIG_REL in lock['files'], 'API config not pinned by the manager lock')
    cfg = _verified_json(repo, CONFIG_REL, lock['files'][CONFIG_REL], 'API config')
    # notebook 22 serving pins -> notebook 20 model_bundles.json -> the chosen bundles at models/<unit>/<file>
    sp_rel = cfg['components']['spatial_runtime']['pins']
    sp = _verified_json(repo, sp_rel, (recs['spatial_runtime'].get('files') or {}).get(sp_rel), '22 serving pins')
    mb_rel = None
    for rel, s in sp['files'].items():
        add(rel, s, 'spatial_serving_pins')
        if rel.endswith('/model_bundles.json'):
            mb_rel = rel
    _need(mb_rel is not None, '22 serving pins carry no model_bundles.json')
    mb = _verified_json(repo, mb_rel, sp['files'][mb_rel], '20 model_bundles.json')
    for u in SPATIAL_UNITS:
        chosen = sp['selection'][u].split('::')[0]
        es = [e for e in _bundle_entries(mb) if e.get('unit') == u and e.get('config_id') == chosen]
        _need(es, 'no chosen 22 bundle entry for ' + u + ' ' + chosen)
        for e in es:
            _need(Path(e['file']).name == e['file'], 'bundle file is not a bare name: ' + e['file'])
            rel = str(Path(mb_rel).parent / 'models' / u / e['file'])
            _need((repo / rel).is_file(), 'chosen 22 bundle missing: ' + rel)
            add(rel, e['sha256'], 'spatial_chosen_bundle')
    # notebook 13: record -> config + serving manifest -> 11 model manifest -> chosen selected + baseline bundles
    prec = recs['province_runtime']['files']
    pcfg_rel = cfg['components']['province_runtime']['config']
    pcfg = _verified_json(repo, pcfg_rel, prec.get(pcfg_rel), '13 config')
    smf_rel = next((r for r in prec if r.endswith('/serving_manifest.json')), None)
    _need(smf_rel is not None, 'province record pins no serving_manifest.json')
    smf = _verified_json(repo, smf_rel, prec[smf_rel], '13 serving manifest')
    _need(smf.get('config_sha256') == prec[pcfg_rel], '13 serving manifest was produced with another config')
    vih = smf.get('verified_input_hashes') or {}
    anchor = pcfg['trust_anchors']['model_manifest_sha256']
    _need(vih.get('model_manifest') == anchor, '13 config and serving manifest disagree on the 11 model manifest')
    mm_rel = 'backend/' + pcfg['paths']['model_report_dir'] + '/model_manifest.json'
    mm = _verified_json(repo, mm_rel, anchor, '11 model manifest')
    add(mm_rel, anchor, 'province_model_manifest')
    for u, sel in pcfg['expected_selection'].items():
        for m in (sel['recommended_method'], sel['strongest_baseline']):
            want = vih.get('bundle:' + u + ':' + m)
            es = [b for b in mm.get('bundles') or [] if b.get('unit') == u and b.get('method_id') == m]
            _need(want and len(es) == 1 and es[0].get('sha256') == want, 'chosen 13 bundle not pinned consistently by 11/13 manifests: ' + u + ':' + m)
            rel = 'backend/' + pcfg['paths']['model_data_dir'] + '/' + _safe_rel(es[0]['path'])
            _need((repo / rel).is_file(), 'chosen 13 bundle missing: ' + rel)
            add(rel, want, 'province_chosen_bundle')
    c = recs['catalog']
    add(c['source_notebook'], c['source_notebook_sha256'], 'catalog_record')
    add(c['config'], c['config_sha256'], 'catalog_record')
    m14 = c['report_dir'] + '/catalog_manifest.json'
    add(m14, c['manifest_sha256'], 'catalog_record')
    out = _verified_json(repo, m14, c['manifest_sha256'], '14 catalog manifest').get('outputs') or {}
    for f, s in (out.get('report_files') or {}).items():
        add(c['report_dir'] + '/' + f, s, 'catalog_manifest')
    for f, s in (out.get('data_files') or {}).items():
        add(c['data_dir'] + '/' + f, s, 'catalog_manifest')
    e = recs['evaluation']
    m21 = e['root'] + '/' + cfg['components']['evaluation']['manifest']
    add(m21, e['manifest_sha256'], 'evaluation_record')
    met = _verified_json(repo, m21, e['manifest_sha256'], '21 evaluation manifest')['report_files']['metrics_by_group.csv']
    add(e['root'] + '/' + cfg['components']['evaluation']['metrics'], met, 'evaluation_manifest')
    d = recs['diagnostics_2026']
    m23 = d['report_dir'] + '/' + cfg['components']['diagnostics_2026']['manifest']
    met = _verified_json(repo, m23, (d.get('files') or {}).get(m23), '23 diagnostics manifest')['report_files'][cfg['components']['diagnostics_2026']['metrics']]
    add(d['report_dir'] + '/' + cfg['components']['diagnostics_2026']['metrics'], met, 'diagnostics_manifest')
    return pins


def coverage_problems(pins):
    """Required consumed categories missing or with the wrong count (empty list = complete). Counts category memberships, so a file pinned by more
    than one accepted chain satisfies each of its categories while staying one file in the before/after hash checks."""
    n = {}
    for _, origins in pins.values():
        for origin in origins:
            n[origin] = n.get(origin, 0) + 1
    return ([o + ': ' + str(n.get(o, 0)) + ' != ' + str(k) for o, k in REQUIRED_EXACT.items() if n.get(o, 0) != k]
            + [o + ': ' + str(n.get(o, 0)) + ' < ' + str(k) for o, k in REQUIRED_AT_LEAST.items() if n.get(o, 0) < k])


def snapshot(pins):
    return {rel: (sha(REPO / rel) if (REPO / rel).is_file() and not (REPO / rel).is_symlink() else None) for rel in sorted(pins)}


def start_server(cmd, log_path, port, timeout):
    import httpx
    log = open(log_path, 'wb')
    t0 = time.time()
    proc = subprocess.Popen(cmd, cwd=str(REPO), stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    startup = None
    with httpx.Client(base_url='http://127.0.0.1:' + str(port), timeout=10.0) as c:
        while time.time() - t0 < timeout:
            if proc.poll() is not None:
                break
            try:
                if c.get('/health').status_code == 200:
                    startup = round(time.time() - t0, 2)
                    break
            except httpx.HTTPError:
                pass
            time.sleep(1.0)
    return proc, log, startup


def stop_server(proc, log):
    """Stops ONLY the process this CLI started (its own session)."""
    try:
        if proc.poll() is None:
            proc.send_signal(signal.SIGINT)
            try:
                proc.wait(30)
            except subprocess.TimeoutExpired:
                proc.terminate()
                try:
                    proc.wait(15)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(10)
    finally:
        log.close()
    return proc.returncode


def build_parser():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run-root', default=None, help='NEW backend/rerun-api-<id> (required except in the internal fixture child mode)')
    ap.add_argument('--port', type=int, default=8765)
    ap.add_argument('--fixture-port', type=int, default=None, help='port of the labelled fixture-lock server (default --port + 1)')
    ap.add_argument('--startup-timeout', type=float, default=900.0)
    ap.add_argument('--serve-fixture-lock', default=None, help=argparse.SUPPRESS)  # internal child mode of this CLI only
    return ap


def fixture_child_argv(lock_rel, port):
    """argv of the internal fixture child: no --run-root (the child writes nothing); the lock path is re-validated by _fixture_lock_rel in the child."""
    return [sys.executable, str(Path(__file__).resolve()), '--serve-fixture-lock', lock_rel, '--port', str(port)]


def main(argv=None):
    ap = build_parser()
    a = ap.parse_args(argv)
    if a.serve_fixture_lock is not None:
        if a.run_root is not None or a.fixture_port is not None:
            ap.error('--serve-fixture-lock is the internal child mode; it takes only --port')
        return serve_fixture(a.serve_fixture_lock, a.port)
    if a.run_root is None:
        ap.error('--run-root is required')
    fport = a.fixture_port or a.port + 1
    root = (REPO / a.run_root).resolve() if not Path(a.run_root).is_absolute() else Path(a.run_root).resolve()
    if root.parent != BACKEND or not root.name.startswith('rerun-api-'):
        sys.exit('run root must be backend/rerun-api-<id>')
    if os.path.lexists(root):
        sys.exit('refusing existing run root ' + str(root) + '; use a NEW one')
    for p in (a.port, fport):
        if not port_free(p):
            sys.exit('port ' + str(p) + ' on 127.0.0.1 is in use; choose another (no process is killed)')
    import httpx
    root.mkdir()
    OUT['root'] = root
    t0 = time.time()
    base = 'http://127.0.0.1:' + str(a.port)
    exit_code = startup = fexit = None
    try:
        pins = consumed_pins()
        before = snapshot(pins)
        missing_cov = coverage_problems(pins)
        check('bounded consumed set resolved through verified chains with every required category (root lock anchor, 4 chosen 22 bundles, '
              '4 chosen 13 bundles, 2 baseline NPZ, records/catalog/evaluation/diagnostics)', not missing_cov, missing_cov)
    except Exception as e:  # evidence is still written below
        pins, before = {}, {}
        check('bounded consumed set resolved through verified chains from the manager lock and accepted records', False, repr(e)[:300])
    try:
        try:
            proc, log, startup = start_server([sys.executable, str(BACKEND / 'scripts' / 'run_api_server.py'), '--port', str(a.port)], root / 'server.log',
                                              a.port, a.startup_timeout)
            try:
                check('server process started and /health answered 200 (liveness)', startup is not None, {'seconds': startup, 'exit': proc.poll()})
                if startup is not None:
                    with httpx.Client(base_url=base, timeout=300.0) as c:
                        try:
                            run_checks(c)
                        except Exception as e:
                            check('healthy-server checks finished without an unexpected smoke exception', False, repr(e)[:300])
            finally:
                exit_code = stop_server(proc, log)
            check('own server process stopped and its port released (only the process this CLI started)', exit_code is not None and port_free(a.port),
                  {'returncode': exit_code})
        except Exception as e:
            check('healthy server phase finished without an unexpected smoke exception', False, repr(e)[:300])
        try:
            fexit = run_fixture_phase(root, fport, a.startup_timeout)
        except Exception as e:
            check('TEST FIXTURE phase finished without an unexpected smoke exception', False, repr(e)[:300])
    finally:
        after = snapshot(pins) if pins else {}
        ro = {rel: {'origin': pins[rel][1][0], 'origins': list(pins[rel][1]), 'trusted_sha256': pins[rel][0], 'before': before.get(rel),
                    'after': after.get(rel)} for rel in sorted(pins)}
        bad_pin = sorted(r for r, v in ro.items() if v['before'] != v['trusted_sha256'])
        changed = sorted(r for r, v in ro.items() if v['before'] != v['after'])
        check('read-only: every consumed input equals its trusted pin before the run (' + str(len(ro)) + ' files)', bool(ro) and not bad_pin, bad_pin[:20])
        check('read-only: every consumed input is byte-identical after both servers stopped', bool(ro) and not changed, changed[:20])
        anchor = ro.get(LOCK_REL, {})
        check('read-only: manager lock (root trust anchor; trusted value = its start-of-run sha256, not self-pinned) unchanged after both servers stopped',
              anchor.get('origin') == ROOT_ANCHOR and anchor.get('before') is not None and anchor.get('before') == anchor.get('after'),
              {'before': anchor.get('before'), 'after': anchor.get('after')})
        counts = {}
        for v in ro.values():
            for o in v['origins']:  # category memberships (a file in two chains counts once per category; n_files counts it once)
                counts[o] = counts.get(o, 0) + 1
        (root / 'read_only_evidence.json').write_text(json.dumps({'kind': 'roadaware_api_read_only_inputs_019', 'n_files': len(ro), 'origin_counts': counts,
                                                                  'root_trust_anchor': {'path': LOCK_REL, 'note': 'trusted value is the start-of-run sha256; '
                                                                                        'the lock cannot pin itself', 'before': anchor.get('before'),
                                                                                        'after': anchor.get('after')},
                                                                  'mismatched_trusted_pin': bad_pin, 'changed_during_run': changed, 'files': ro},
                                                                 ensure_ascii=False, indent=1), 'utf-8')
    files = {}
    for name, obj in (('sample_responses.json', SAMPLES),):
        (root / name).write_text(json.dumps(obj, ensure_ascii=False, indent=1, allow_nan=False)[:2_000_000], 'utf-8')
    nfail = sum(not r['passed'] for r in RESULTS)
    for p in sorted(root.rglob('*')):
        if p.is_file():
            files[str(p.relative_to(root))] = sha(p)
    import fastapi, pydantic, starlette, uvicorn
    ev = {'kind': 'roadaware_api_live_smoke_019', 'run_root': root.name, 'base_url': base, 'started_utc': dt.datetime.fromtimestamp(t0, dt.timezone.utc).isoformat(),
          'seconds': round(time.time() - t0, 2), 'startup_seconds': startup, 'server_returncode': exit_code, 'fixture_server_returncode': fexit,
          'checks': RESULTS, 'passed': len(RESULTS) - nfail, 'failed': nfail, 'files_sha256': files, 'lock_sha256': sha(REPO / LOCK_REL),
          'environment': {'python': platform.python_version(), 'fastapi': fastapi.__version__, 'starlette': starlette.__version__, 'uvicorn': uvicorn.__version__,
                          'pydantic': pydantic.VERSION, 'httpx': httpx.__version__}, 'production_ready': False}
    (root / 'smoke_evidence.json').write_text(json.dumps(ev, ensure_ascii=False, indent=1, allow_nan=False), 'utf-8')
    print(str(len(RESULTS) - nfail) + '/' + str(len(RESULTS)) + ' live checks passed; evidence in ' + str(root / 'smoke_evidence.json'))
    return 1 if nfail else 0


# ---------- labelled TEST FIXTURE: copied lock with a deliberately wrong pinned source hash ----------
def _fixture_lock_rel(rel):
    p = Path(rel)
    if p.is_absolute() or '..' in p.parts or len(p.parts) != 4 or p.parts[0] != 'backend' or not p.parts[1].startswith('rerun-api-') \
            or p.parts[2] != FIXTURE_DIR or p.name != FIXTURE_LOCK:
        sys.exit('fixture lock must be backend/rerun-api-<id>/' + FIXTURE_DIR + '/' + FIXTURE_LOCK)
    return rel


def serve_fixture(lock_rel, port):
    """Child mode: the SAME app with a server-side injected load_runtime(lock_rel=<fixture copy>). Never a client-chosen path."""
    lock_rel = _fixture_lock_rel(lock_rel)
    if not 1024 <= port <= 65535:
        sys.exit('port must be 1024..65535')
    sys.path.insert(0, str(BACKEND))
    import logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s %(message)s')
    import uvicorn
    from api.app import create_app
    from api.runtime import load_runtime
    app = create_app(runtime_factory=lambda: load_runtime(REPO, lock_rel=lock_rel, config_rel=CONFIG_REL))
    uvicorn.run(app, host='127.0.0.1', port=port, workers=1, limit_concurrency=32, timeout_keep_alive=5, log_level='info', server_header=False,
                proxy_headers=False)
    return 0


def run_fixture_phase(root, port, timeout):
    import httpx
    sys.path.insert(0, str(BACKEND))
    from api import openapi_docs as D
    if not port_free(port):
        check('TEST FIXTURE port free (no process is killed)', False, port)
        return None
    lock = jload(REPO / LOCK_REL)
    target = 'backend/notebooks/24_backend_api_contract.ipynb'
    good = lock['files'].get(target)
    lock['files'][target] = ('0' if not good or good[0] != '0' else '1') * 64
    lock['TEST_FIXTURE'] = 'COPY of the manager lock with a deliberately wrong pinned notebook-24 source hash; NOT a production config'
    (root / FIXTURE_DIR).mkdir()
    rel = str((root / FIXTURE_DIR / FIXTURE_LOCK).relative_to(REPO))
    (REPO / rel).write_text(json.dumps(lock, ensure_ascii=False, indent=1), 'utf-8')
    proc, log, startup = start_server(fixture_child_argv(rel, port), root / FIXTURE_DIR / 'fixture_server.log', port, min(timeout, 300.0))
    try:
        check('TEST FIXTURE server (wrong pinned source hash) started; /health 200 (liveness only)', startup is not None, {'seconds': startup})
        if startup is not None:
            with httpx.Client(base_url='http://127.0.0.1:' + str(port), timeout=60.0) as c:
                r1, r2 = c.get('/ready'), c.get('/ready')
                j = r1.json()
                check('TEST FIXTURE /ready 503, notebook24 unavailable artifact_hash_mismatch, stable across calls', r1.status_code == 503 and r2.status_code == 503
                      and j.get('components', {}).get('notebook24') == {'status': 'unavailable', 'code': 'artifact_hash_mismatch'} and r1.content == r2.content
                      and D.matches(D.EXAMPLES['ready_unavailable']['response'], j), {'status': r1.status_code, 'components': j.get('components')})
                req = D.EXAMPLES['spatial_daily']['request']
                p = post(c, req['path'], req['body'])
                check('TEST FIXTURE prediction 503 backend_not_ready: sanitised, no results, no zero', p.status_code == 503 and code_of(p) == 'backend_not_ready'
                      and 'results' not in p.json() and 'expected_recorded_count' not in p.text and not leaks(p.text)
                      and D.matches(D.EXAMPLES['unavailable_not_ready']['response'], p.json()), {'status': p.status_code, 'body': p.text[:300]})
                SAMPLES['fixture_ready_503'] = j
                SAMPLES['fixture_prediction_503'] = p.json()
    except Exception as e:
        check('TEST FIXTURE checks finished without an unexpected smoke exception', False, repr(e)[:300])
    finally:
        rc = stop_server(proc, log)
    check('TEST FIXTURE server stopped and its port released (only the process this CLI started)', rc is not None and port_free(port), {'returncode': rc})
    return rc


def post(c, path, obj=None, raw=None, ctype='application/json'):
    return c.post(path, content=raw if raw is not None else json.dumps(obj, ensure_ascii=False).encode('utf-8'), headers={'Content-Type': ctype})


def code_of(r):
    try:
        return r.json()['error']['code']
    except Exception:
        return None


def run_checks(c):
    t = time.time()
    while time.time() - t < 60:
        r = c.get('/ready')
        if r.status_code in (200, 503):
            break
    rd = r.json()
    check('/ready 200 research_backend_ready true, production_ready false', r.status_code == 200 and rd.get('research_backend_ready') is True
          and rd.get('production_ready') is False, rd.get('components'))
    SAMPLES['ready'] = rd
    if r.status_code != 200:
        return
    m = c.get('/api/v1/metadata')
    md = m.json()
    check('/api/v1/metadata 200, production_ready false, 3105 segments, colour cutoffs present', m.status_code == 200 and md['production_ready'] is False
          and md['geometry']['segments'] == 3105 and all(md['spatial_runtime']['units'][u]['colour_cutoffs'] for u in ('daily', '6h')))
    SAMPLES['metadata_keys'] = sorted(md)
    e = c.get('/api/v1/evaluation')
    d = e.json().get('diagnostics_2026', {}) if e.status_code == 200 else {}
    cn = d.get('counts', {})
    check('/api/v1/evaluation exposes the accepted 2026 limits/counts (4336 eligible, 4116/4232 cells, 1128 segments, 19 provinces, 17272 window rows)',
          e.status_code == 200 and cn.get('eligible_raw_records') == 4336 and cn.get('positive_cells') == {'daily': 4116, '6h': 4232}
          and cn.get('segments_with_observed_records') == 1128 and cn.get('recorded_provinces') == 19 and cn.get('requested_window_rows') == 17272
          and 'provider_checksum_not_verified' in d.get('source_checksum_status', ''), {'counts': cn, 'mae': d.get('lower_mae_on_this_conditional_cohort')})
    SAMPLES['evaluation'] = e.json()
    check_evaluation_numbers(e.json().get('spatial_evaluation_21', {}) if e.status_code == 200 else {})
    p = c.get('/api/v1/provinces')
    provs = p.json().get('provinces', [])
    check('/api/v1/provinces 200 with 77 provinces', p.status_code == 200 and len(provs) == 77)
    # catalog province history parity vs the hash-verified 14 report table
    crec = jload(REPO / 'workflow/catalog/accepted-runtime-v3.json')
    man14 = jload(REPO / crec['report_dir'] / 'catalog_manifest.json')
    pm = REPO / crec['report_dir'] / 'province_monthly.csv'
    ok_hash = sha(pm) == man14['outputs']['report_files']['province_monthly.csv']
    pk = provs[0]['province_key']
    with open(pm, newline='', encoding='utf-8') as f:
        want = sum(int(row['n_records']) for row in csv.DictReader(f) if row['province_key'] == pk and '2024-01' <= row['year_month'] <= '2024-12')
    h = c.get('/api/v1/history', params={'province_key': pk, 'start_month': '2024-01', 'end_month': '2024-12'})
    got = h.json().get('history', {}).get('total_records') if h.status_code == 200 else None
    check('/api/v1/history total equals hash-verified province_monthly.csv (2024)', ok_hash and got == want, {'got': got, 'want': want})
    h26 = c.get('/api/v1/history', params={'province_key': pk, 'start_month': '2026-01', 'end_month': '2026-03'})
    check('/api/v1/history 2026 refused explicitly (not in accepted catalog; not an empty zero)', h26.status_code == 400, h26.json().get('error'))
    # geometry: full page walk + round trip
    seg_csv = REPO / 'backend/data/v3/spatial_preparation/universe_segments.csv'
    with open(seg_csv, newline='', encoding='utf-8') as f:
        universe = sorted(r['segment_id'] for r in csv.DictReader(f))
    seen, cur, first = [], '0', None
    while cur is not None:
        g = c.get('/api/v1/segments', params={'bbox': '97,5,106,21', 'limit': '500', 'cursor': cur})
        if g.status_code != 200:
            break
        gj = g.json()
        first = first or gj
        seen += [f_['id'] for f_ in gj['features']]
        cur = gj['page']['next_cursor']
    check('/api/v1/segments page walk returns exactly the 3105 universe ids once, sorted', seen == universe and len(seen) == 3105, {'seen': len(seen)})
    SAMPLES['segments_page'] = dict(first, features=first['features'][:2]) if first else None
    f0 = first['features'][0] if first else None
    one = c.get('/api/v1/segments/' + f0['id']) if f0 else None
    check('/api/v1/segments/{id} round trip equals the page feature', one is not None and one.status_code == 200 and one.json()['feature'] == f0)
    check('unknown segment id -> 404 unknown_segment', code_of(c.get('/api/v1/segments/not-a-doh-segment')) == 'unknown_segment')
    for bad in ('106,5,97,21', 'nan,5,106,21', '97,5,106', '1e1,5,106,21', '0,0,90,80'):
        r = c.get('/api/v1/segments', params={'bbox': bad})
        check('bbox ' + bad + ' refused 400', r.status_code == 400, code_of(r))
    check('limit 0 refused', c.get('/api/v1/segments', params={'bbox': '97,5,106,21', 'limit': '0'}).status_code == 400)
    check('unknown query parameter refused', c.get('/api/v1/segments', params={'bbox': '97,5,106,21', 'path': '/etc/passwd'}).status_code == 400)
    # spatial predictions: saved 22 fixtures, exact results, both units, selected + baseline
    srec = jload(REPO / 'workflow/serving/accepted-runtime-v3.json')
    smf = jload(REPO / srec['report_dir'] / 'spatial_serving_manifest.json')
    fx = REPO / srec['data_dir'] / 'prediction_fixtures.json'
    check('saved 22 prediction_fixtures.json hash equals the accepted 22 manifest', sha(fx) == smf['data_files_gitignored']['prediction_fixtures.json'])
    FX = jload(fx)
    seg_hist = None
    for u in ('daily', '6h'):
        for which, path in (('selected', '/api/v1/spatial/predictions'), ('baseline', '/api/v1/spatial/baseline-predictions')):
            saved = next(x for x in FX[u]['responses'] if x['which'] == which)
            r = post(c, path, {'unit': u, 'requests': saved['requests']})
            res = r.json().get('results') if r.status_code == 200 else None
            check('live ' + u + ' ' + which + ' results == saved notebook-22 response (' + str(len(saved['requests'])) + ' rows, order preserved)',
                  res == saved['response']['results'], {'status': r.status_code, 'error': r.json().get('error')})
            if u == 'daily' and which == 'selected':
                SAMPLES['spatial_prediction'] = dict(r.json(), results=(res or [])[:2])
                seg_hist = saved['requests'][0]['segment_id']
    # spatial history cutoff + 2026 period status
    hs = post(c, '/api/v1/spatial/history', {'segment_id': seg_hist, 'target_date': '2024-03-01', 'unit': 'daily'})
    hj = hs.json()
    check('spatial history 2024-03-01: issue 2024-02-29T18:00, cutoff 30 d earlier, within catalog', hs.status_code == 200
          and hj['history']['issue_time_local'] == '2024-02-29T18:00:00+07:00' and hj['history']['history_cutoff_local'] == '2024-01-30T18:00:00+07:00'
          and hj['period_status']['unsupported_after'] is None, hj.get('period_status'))
    SAMPLES['spatial_history'] = hj
    hs2 = post(c, '/api/v1/spatial/history', {'segment_id': seg_hist, 'target_date': '2026-06-01', 'unit': '6h', 'time_block': '12-18'})
    check('spatial history 2026 target marks the post-2025 period unsupported (not zero)', hs2.status_code == 200
          and hs2.json()['period_status']['unsupported_after'] is not None, hs2.json().get('period_status'))
    # province V2 compatibility: saved 13 examples
    ex = jload(BACKEND / 'reports/v2/serving/serving_examples.json')
    pr = post(c, '/api/v1/predictions', {'requests': ex['requests']})
    got = pr.json().get('province_prediction_v2', {}).get('results') if pr.status_code == 200 else None
    diffs = [abs(g['prediction']['expected_recorded_count'] - s['prediction']['expected_recorded_count']) for g, s in zip(got or [], ex['response']['results'])]
    check('POST /api/v1/predictions (V2 province) equals saved notebook-13 examples', got is not None and len(got) == len(ex['response']['results'])
          and max(diffs) <= 1e-12, {'status': pr.status_code, 'max_abs_diff': max(diffs) if diffs else None, 'error': pr.json().get('error')})
    # error / limit / sanitisation cases
    seg = seg_hist
    ok_row = {'segment_id': seg, 'target_date': '2024-03-01'}
    cases = [('malformed JSON', post(c, '/api/v1/spatial/predictions', raw=b'{"unit": "daily", '), 400, 'invalid_json'),
             ('NaN constant', post(c, '/api/v1/spatial/predictions', raw=b'{"unit":"daily","requests":[{"segment_id":"x","target_date":NaN}]}'), 400, 'invalid_json'),
             ('duplicate JSON key', post(c, '/api/v1/spatial/predictions', raw=b'{"unit":"daily","unit":"6h","requests":[]}'), 400, 'invalid_json'),
             ('unknown top-level field', post(c, '/api/v1/spatial/predictions', {'unit': 'daily', 'requests': [ok_row], 'x': 1}), 400, 'invalid_fields'),
             ('bool unit', post(c, '/api/v1/spatial/predictions', {'unit': True, 'requests': [ok_row]}), 400, 'invalid_unit'),
             ('empty batch', post(c, '/api/v1/spatial/predictions', {'unit': 'daily', 'requests': []}), 400, 'batch_size'),
             ('batch 129', post(c, '/api/v1/spatial/predictions', {'unit': 'daily', 'requests': [dict(ok_row, target_date=(dt.date(2024, 1, 1) + dt.timedelta(days=i)).isoformat()) for i in range(129)]}), 400, 'batch_size'),
             ('duplicate rows', post(c, '/api/v1/spatial/predictions', {'unit': 'daily', 'requests': [ok_row, ok_row]}), 400, 'duplicate_keys'),
             ('extra row field', post(c, '/api/v1/spatial/predictions', {'unit': 'daily', 'requests': [dict(ok_row, path='/etc/passwd')]}), 400, 'invalid_fields'),
             ('2023 date (no fold artifact)', post(c, '/api/v1/spatial/predictions', {'unit': 'daily', 'requests': [dict(ok_row, target_date='2023-06-01')]}), 400, 'date_before_artifact_asof'),
             ('2028 date', post(c, '/api/v1/spatial/predictions', {'unit': 'daily', 'requests': [dict(ok_row, target_date='2028-01-01')]}), 400, 'date_out_of_range'),
             ('unknown segment', post(c, '/api/v1/spatial/predictions', {'unit': 'daily', 'requests': [dict(ok_row, segment_id='nope')]}), 404, 'unknown_segment'),
             ('body > 64 KiB', post(c, '/api/v1/spatial/predictions', raw=b'{"unit":"daily","requests":[' + b' ' * 70000 + b']}'), 413, 'body_too_large'),
             ('wrong content type', post(c, '/api/v1/spatial/predictions', raw=b'{}', ctype='text/plain'), 415, 'unsupported_media_type'),
             ('unknown route', c.get('/api/v1/nope'), 404, 'not_found'),
             ('wrong method', c.get('/api/v1/spatial/predictions'), 405, 'method_not_allowed')]
    for name, r, st, code in cases:
        check('error case ' + name + ' -> ' + str(st) + ' ' + code, r.status_code == st and code_of(r) == code and not leaks(r.text),
              {'status': r.status_code, 'code': code_of(r), 'leaks': leaks(r.text)})
    SAMPLES['error_example'] = cases[9][1].json()
    # CORS
    pf = c.options('/api/v1/spatial/predictions', headers={'Origin': 'http://localhost:5173', 'Access-Control-Request-Method': 'POST',
                                                          'Access-Control-Request-Headers': 'content-type'})
    check('CORS preflight from allowed localhost origin echoes it, no credentials, no wildcard', pf.status_code == 200
          and pf.headers.get('access-control-allow-origin') == 'http://localhost:5173' and 'access-control-allow-credentials' not in pf.headers)
    bad = c.options('/api/v1/spatial/predictions', headers={'Origin': 'http://evil.example', 'Access-Control-Request-Method': 'POST'})
    check('CORS preflight from other origin refused (no allow-origin header)', 'access-control-allow-origin' not in bad.headers, bad.status_code)
    g = c.get('/health', headers={'Origin': 'http://evil.example'})
    check('simple GET from other origin carries no allow-origin header', 'access-control-allow-origin' not in g.headers)
    o = c.get('/openapi.json')
    check('OpenAPI served', o.status_code == 200 and '/api/v1/spatial/predictions' in o.json().get('paths', {}))
    SAMPLES['_openapi_paths'] = sorted(o.json().get('paths', {}))
    (OUT['root'] / 'openapi.json').write_text(json.dumps(o.json(), ensure_ascii=False, indent=1, allow_nan=False), 'utf-8')
    check_openapi_and_examples(c, o.json())


# independent of notebook 24: the CSV is re-read here after its sha256 equals the accepted 21 manifest entry (manifest equals the accepted record)
EVAL_NUM = ('n', 'zero_cells', 'nonzero_cells', 'total_actual', 'total_pred', 'pred_over_actual', 'mean_poisson_deviance', 'mae', 'rmse', 'bias', 'wape',
            'exposure_segment_km_periods', 'observed_records_per_km_period', 'predicted_records_per_km_period', 'metric_floor_cells',
            'metric_floor_actual_positive_cells', 'metric_floor_actual_records', 'metric_floor_deviance_sum')


def check_evaluation_numbers(s21):
    import math
    erec = jload(REPO / 'workflow/evaluation/accepted-runtime-v3.json')
    d = REPO / erec['root'] / 'reports/v3/spatial_evaluation'
    man_ok = sha(d / 'spatial_evaluation_manifest.json') == erec['manifest_sha256']
    man = jload(d / 'spatial_evaluation_manifest.json')
    csv_ok = man_ok and sha(d / 'metrics_by_group.csv') == man['report_files']['metrics_by_group.csv']
    with open(d / 'metrics_by_group.csv', newline='', encoding='utf-8') as f:
        want = {(r['unit'], r['scope'], r['role'], r['dimension'], r['group']): r for r in csv.DictReader(f)
                if r['role'] in ('selected', 'baseline') and r['scope'] in ('oof', 'diag') and r['dimension'] in ('pooled', 'period')}
    live = {(m.get('unit'), m.get('scope'), m.get('role'), m.get('dimension'), m.get('group')): m for m in s21.get('metrics') or []}
    bad = []
    for k, r in want.items():
        m = live.get(k)
        if m is None or m.get('method') != r['method'] or m.get('method') != man['selected'][k[0]][k[2]] or (m.get('wape_status') or '') != r['wape_status']:
            bad.append(list(k))
            continue
        for col in EVAL_NUM:
            x = float(r[col]) if r[col] not in ('', None) else None
            x = x if x is not None and math.isfinite(x) else None
            if (x is None) != (m.get(col) is None) or (x is not None and float(m[col]) != x):
                bad.append(list(k) + [col])
    pooled = sorted(k for k in live if k[3] == 'pooled')
    check('/api/v1/evaluation 21 numbers == hash-verified metrics_by_group.csv (selected + strong baseline, oof 2022-23 + seen 2024-25, pooled + period, '
          'both units; ' + str(len(want)) + ' rows)', csv_ok and want and set(live) == set(want) and not bad and len(pooled) == 8,
          {'csv_verified': csv_ok, 'rows_csv': len(want), 'rows_live': len(live), 'pooled_live': len(pooled), 'mismatch': bad[:10]})


def check_openapi_and_examples(c, spec):
    sys.path.insert(0, str(BACKEND))
    from api import openapi_docs as D
    paths = spec.get('paths', {})
    bad = []
    for path, (name, _) in D.REQUEST_EXAMPLES.items():
        rb = paths.get(path, {}).get('post', {}).get('requestBody', {})
        sch = rb.get('content', {}).get('application/json', {}).get('schema', {})
        items = sch.get('properties', {}).get('requests', {})
        if not rb.get('required') or sch.get('additionalProperties') is not False or not sch.get('required') or \
                (items and (items.get('maxItems') != 128 or items.get('minItems') != 1 or items.get('items', {}).get('additionalProperties') is not False)):
            bad.append(path)
    check('served OpenAPI: strict bounded request schemas on all 4 POST routes (required fields, additionalProperties false, 1..128 rows)', not bad, bad)
    text = json.dumps(spec, ensure_ascii=False)
    missing = [n for n in D.EXAMPLES if '"' + n + '"' not in text]
    check('served OpenAPI carries every documented example (success/error/unavailable, both spatial units, province V2)', not missing, missing)
    for name, ex in D.EXAMPLES.items():
        rq = ex.get('request')
        if rq is None:
            continue
        r = post(c, rq['path'], rq['body']) if rq['method'] == 'POST' else c.get(rq['path'], params=rq.get('query'))
        try:
            body = r.json()
        except ValueError:
            body = None
        ok = r.status_code == ex['status'] and D.matches(ex['response'], body) and not leaks(r.text)
        check('OpenAPI example ' + name + ' re-asked live: status ' + str(ex['status']) + ' and the example is a subset of the actual answer', ok,
              {'status': r.status_code, 'leaks': leaks(r.text), 'body': r.text[:300] if not ok else None})
        if name == 'province_history_ok' and r.status_code == 200:
            SAMPLES['province_history'] = body


if __name__ == '__main__':
    sys.exit(main())
