"""Generic, mechanical nbformat-v4 notebook assembler for worker-authored cell payloads (development tooling; NOT runtime code).

Usage from the repository root (Python >= 3.9, standard library only; nbformat validation runs only if nbformat is importable):
    .venv/bin/python tools/assemble_notebook_payloads.py --spec .ai-team/handoffs/016/notebook_cells.json \
        --target backend/notebooks/20_spatial_count_experiments.ipynb            # write (replaces the approved target)
    .venv/bin/python tools/assemble_notebook_payloads.py --spec .ai-team/handoffs/020/notebook_cells.json \
        --target backend/notebooks/14_backend_catalog.ipynb
    .venv/bin/python tools/assemble_notebook_payloads.py --spec ... --target ... --check   # compare only, never writes; exit 1 on drift

Spec format (the existing notebook_cells.json): {"target": <repo-relative .ipynb>, "kernelspec": {name, display_name, language},
"cells": [{"cell_type": "code"|"markdown", "id": <nbformat id>, "source_path": <repo-relative file>}, ...]} (other top-level keys ignored).

Refuses (nothing written): --target differing from the spec target or not in APPROVED_TARGETS (all under backend/notebooks/); absolute paths,
'..', symlinked path components or files outside the repository; source files outside the spec's directory, missing or non-regular; invalid
cell types/ids, duplicate ids, unknown cell keys; non-UTF-8 sources; code cells that do not compile or reference '.ai-team'; an existing
target that has outputs or execution counts (an executed notebook is never overwritten). Every cell
source is the exact file content. Code cells get no outputs and execution_count null. Nothing is executed. After writing, the notebook is
re-read and every cell source is compared byte-for-byte with its payload.
"""
import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path, PurePosixPath

REPO = Path(__file__).resolve().parents[1]
APPROVED_TARGETS = ('backend/notebooks/20_spatial_count_experiments.ipynb', 'backend/notebooks/14_backend_catalog.ipynb',
                    'backend/notebooks/21_spatial_evaluation_colours.ipynb', 'backend/notebooks/22_spatial_inference_contract.ipynb',
                    'backend/notebooks/23_2026_record_diagnostics.ipynb', 'backend/notebooks/24_backend_api_contract.ipynb')
TARGET_DIR = 'backend/notebooks'
CELL_TYPES = ('code', 'markdown')
CELL_KEYS = {'cell_type', 'id', 'source_path'}
ID_RE = re.compile(r'^[A-Za-z0-9_-]{1,64}$')


class AssemblyError(Exception):
    pass


def safe_path(root, rel, label, inside=None):
    """Resolve a repo-relative POSIX path with no absolute/'..' parts and no symlinked component; optionally require it under `inside`."""
    if not isinstance(rel, str) or not rel or '\\' in rel or '\x00' in rel:
        raise AssemblyError(label + ': invalid path ' + repr(rel))
    pp = PurePosixPath(rel)
    if pp.is_absolute() or any(part in ('..', '.', '') for part in pp.parts) or pp.as_posix() != rel:
        raise AssemblyError(label + ': path must be a normalised repository-relative path: ' + repr(rel))
    root = Path(root).resolve()
    cur = root
    for part in pp.parts:
        cur = cur / part
        if os.path.islink(cur):
            raise AssemblyError(label + ': symlinked path component refused: ' + str(cur))
    full = root.joinpath(*pp.parts)
    try:
        full.resolve().relative_to(root)
    except ValueError:
        raise AssemblyError(label + ': escapes the repository: ' + rel)
    if inside is not None and PurePosixPath(inside) not in pp.parents:
        raise AssemblyError(label + ': must be inside ' + inside + '/: ' + rel)
    return full


def read_spec(root, spec_rel):
    spec_path = safe_path(root, spec_rel, 'spec')
    if not spec_path.is_file():
        raise AssemblyError('spec not found: ' + spec_rel)
    spec = json.loads(spec_path.read_text('utf-8'))
    if not isinstance(spec, dict) or not isinstance(spec.get('cells'), list) or not spec['cells'] or not isinstance(spec.get('target'), str):
        raise AssemblyError('spec needs a string "target" and a non-empty "cells" list')
    ks = spec.get('kernelspec')
    if not (isinstance(ks, dict) and all(isinstance(ks.get(k), str) and ks.get(k) for k in ('name', 'display_name', 'language'))):
        raise AssemblyError('spec kernelspec needs non-empty string name, display_name and language')
    return spec, PurePosixPath(spec_rel).parent.as_posix()


def load_cells(root, spec, spec_dir):
    seen, out = set(), []
    for i, c in enumerate(spec['cells']):
        if not isinstance(c, dict) or set(c) != CELL_KEYS:
            raise AssemblyError('cell ' + str(i) + ': keys must be exactly ' + str(sorted(CELL_KEYS)))
        if c['cell_type'] not in CELL_TYPES:
            raise AssemblyError('cell ' + str(i) + ': invalid cell_type ' + repr(c['cell_type']))
        cid = c['id']
        if not isinstance(cid, str) or not ID_RE.match(cid):
            raise AssemblyError('cell ' + str(i) + ': invalid id ' + repr(cid))
        if cid in seen:
            raise AssemblyError('duplicate cell id ' + cid)
        seen.add(cid)
        p = safe_path(root, c['source_path'], 'cell ' + cid, inside=spec_dir)
        if not p.is_file():
            raise AssemblyError('cell ' + cid + ': source file missing or not a regular file: ' + c['source_path'])
        try:
            src = p.read_bytes().decode('utf-8')
        except UnicodeDecodeError:
            raise AssemblyError('cell ' + cid + ': source is not UTF-8')
        if c['cell_type'] == 'code':
            if '.ai-team' in src:
                raise AssemblyError('cell ' + cid + ': code references .ai-team; notebooks must not depend on handoff files')
            try:
                compile(src, c['source_path'], 'exec')
            except SyntaxError as e:
                raise AssemblyError('cell ' + cid + ': does not compile: ' + str(e))
        out.append({'cell_type': c['cell_type'], 'id': cid, 'source_path': c['source_path'], 'source': src})
    return out


def check_target(root, spec, target_rel, approved):
    if target_rel != spec['target']:
        raise AssemblyError('--target ' + repr(target_rel) + ' differs from the spec target ' + repr(spec['target']))
    if target_rel not in approved:
        raise AssemblyError('target not approved for assembly: ' + target_rel + ' (approved: ' + ', '.join(approved) + ')')
    p = safe_path(root, target_rel, 'target', inside=TARGET_DIR)
    if p.suffix != '.ipynb':
        raise AssemblyError('target must be an .ipynb file')
    if not p.parent.is_dir():
        raise AssemblyError('target directory does not exist: ' + str(p.parent))
    if p.exists() and not p.is_file():
        raise AssemblyError('target exists and is not a regular file')
    return p


def refuse_executed(path):
    """An existing target carrying outputs or execution counts is an executed notebook: never overwritten (executed copies live in rerun roots)."""
    if not path.is_file():
        return
    try:
        cells = json.loads(path.read_text('utf-8')).get('cells', [])
    except ValueError:
        raise AssemblyError('existing target is not valid JSON; refusing to overwrite it')
    if any(c.get('outputs') or c.get('execution_count') is not None for c in cells if isinstance(c, dict) and c.get('cell_type') == 'code'):
        raise AssemblyError('existing target has outputs/execution counts (executed notebook); refusing to overwrite it')


def build_notebook(spec, cells):
    nb_cells = []
    for c in cells:
        cell = {'cell_type': c['cell_type'], 'id': c['id'], 'metadata': {}, 'source': c['source'].splitlines(keepends=True)}
        if c['cell_type'] == 'code':
            cell['execution_count'] = None
            cell['outputs'] = []
        nb_cells.append(cell)
    ks = spec['kernelspec']
    return {'cells': nb_cells, 'metadata': {'kernelspec': {'display_name': ks['display_name'], 'language': ks['language'], 'name': ks['name']},
                                            'language_info': {'name': 'python'}}, 'nbformat': 4, 'nbformat_minor': 5}


def notebook_bytes(nb):
    return (json.dumps(nb, indent=1, ensure_ascii=False) + '\n').encode('utf-8')


def drift(path, cells):
    """Differences between an existing notebook and the payloads (cell count, order, ids, types, exact sources)."""
    d = json.loads(Path(path).read_text('utf-8'))
    got = d.get('cells', [])
    probs = [] if len(got) == len(cells) else ['cell count ' + str(len(got)) + ' != ' + str(len(cells))]
    for i, (g, c) in enumerate(zip(got, cells)):
        s = g.get('source', '')
        s = ''.join(s) if isinstance(s, list) else s
        if g.get('id') != c['id'] or g.get('cell_type') != c['cell_type'] or s != c['source']:
            probs.append('cell ' + str(i) + ' (' + c['id'] + ') differs from ' + c['source_path'])
    return probs


def validate_nbformat(path):
    try:
        import nbformat
    except ImportError:
        return 'nbformat not importable; validate separately'
    nbformat.validate(nbformat.reads(Path(path).read_text('utf-8'), as_version=4))
    return 'nbformat.validate: ok'


def assemble(spec_rel, target_rel, root=REPO, approved=APPROVED_TARGETS, check_only=False):
    """Returns (status lines, drift problems). Writes only the approved target, atomically, unless check_only."""
    root = Path(root).resolve()
    spec, spec_dir = read_spec(root, spec_rel)
    target = check_target(root, spec, target_rel, approved)
    cells = load_cells(root, spec, spec_dir)
    lines = [c['id'] + ' ' + c['cell_type'] + ' sha256=' + hashlib.sha256(c['source'].encode('utf-8')).hexdigest() + ' <- ' + c['source_path'] for c in cells]
    if check_only:
        if not target.is_file():
            return lines, ['target does not exist: ' + target_rel]
        return lines, drift(target, cells)
    refuse_executed(target)
    data = notebook_bytes(build_notebook(spec, cells))
    tmp = target.with_name('.' + target.name + '.assemble-' + str(os.getpid()))
    fh = open(tmp, 'xb')  # exclusive: never reuses or follows an existing temp path
    try:
        with fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, target)
    finally:
        if os.path.lexists(tmp):
            os.unlink(tmp)
    probs = drift(target, cells)
    if probs:
        raise AssemblyError('written notebook differs from payloads: ' + '; '.join(probs))
    lines.append(validate_nbformat(target))
    lines.append('wrote ' + target_rel + ' (' + str(len(cells)) + ' cells, ' + str(sum(c['cell_type'] == 'code' for c in cells)) + ' code) sha256=' +
                 hashlib.sha256(target.read_bytes()).hexdigest())
    return lines, []


def main(argv=None):
    ap = argparse.ArgumentParser(description='Mechanically assemble an approved notebook from ordered payload files (no execution).')
    ap.add_argument('--spec', required=True, help='repository-relative notebook_cells.json')
    ap.add_argument('--target', required=True, help='repository-relative approved notebook path; must equal the spec target')
    ap.add_argument('--check', action='store_true', help='compare the existing target with the payloads; never writes')
    a = ap.parse_args(argv)
    try:
        lines, probs = assemble(a.spec, a.target, check_only=a.check)
    except (AssemblyError, json.JSONDecodeError, OSError) as e:
        print('REFUSED: ' + str(e), file=sys.stderr)
        return 2
    for ln in lines:
        print(ln)
    if probs:
        print('DRIFT: ' + '; '.join(probs), file=sys.stderr)
        return 1
    print('check: target matches payloads' if a.check else 'ok')
    return 0


if __name__ == '__main__':
    sys.exit(main())
