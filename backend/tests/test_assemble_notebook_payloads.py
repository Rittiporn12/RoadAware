"""Tests for the development-only payload assembler tools/assemble_notebook_payloads.py (no kernel, no execution, temp repos only
except the read-only --check of the real notebook-20 spec). Run from the repository root:
    .venv/bin/python -m pytest backend/tests/test_assemble_notebook_payloads.py -q
"""
import importlib.util
import json
import os
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
TOOL = REPO / 'tools' / 'assemble_notebook_payloads.py'
TGT = 'backend/notebooks/x.ipynb'


@pytest.fixture(scope='module')
def A():
    spec = importlib.util.spec_from_file_location('assemble_notebook_payloads', TOOL)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def make_repo(tmp_path, cells=None, target=TGT):
    (tmp_path / 'backend' / 'notebooks').mkdir(parents=True)
    h = tmp_path / 'h'
    h.mkdir()
    (h / 'a.md').write_text('# Title\nไทย\n', 'utf-8')
    (h / 'b.py').write_text('# FUNCTIONS\nx = 1\n\n\n', 'utf-8')
    (h / 'c.py').write_text('y = 2', 'utf-8')  # no trailing newline: must stay exact
    cells = cells if cells is not None else [{'cell_type': 'markdown', 'id': 'c-a', 'source_path': 'h/a.md'},
                                             {'cell_type': 'code', 'id': 'c-b', 'source_path': 'h/b.py'},
                                             {'cell_type': 'code', 'id': 'c_c', 'source_path': 'h/c.py'}]
    spec = {'target': target, 'kernelspec': {'name': 'python3', 'display_name': 'py', 'language': 'python'}, 'note': 'x', 'cells': cells}
    (h / 'notebook_cells.json').write_text(json.dumps(spec), 'utf-8')
    return 'h/notebook_cells.json'


def run(A, tmp_path, spec, target=TGT, check_only=False):
    return A.assemble(spec, target, root=tmp_path, approved=(TGT,), check_only=check_only)


def test_exact_sources_order_and_check(A, tmp_path):
    spec = make_repo(tmp_path)
    lines, probs = run(A, tmp_path, spec)
    assert probs == [] and lines[-1].startswith('wrote ' + TGT)
    nb = json.loads((tmp_path / TGT).read_text('utf-8'))
    assert nb['nbformat'] == 4 and nb['nbformat_minor'] == 5 and nb['metadata']['kernelspec']['name'] == 'python3'
    assert [c['id'] for c in nb['cells']] == ['c-a', 'c-b', 'c_c'] and [c['cell_type'] for c in nb['cells']] == ['markdown', 'code', 'code']
    for c, p in zip(nb['cells'], ('a.md', 'b.py', 'c.py')):
        assert ''.join(c['source']) == (tmp_path / 'h' / p).read_text('utf-8')
    assert all(c['outputs'] == [] and c['execution_count'] is None for c in nb['cells'] if c['cell_type'] == 'code')
    assert 'outputs' not in nb['cells'][0]
    assert run(A, tmp_path, spec, check_only=True)[1] == []
    (tmp_path / 'h' / 'c.py').write_text('y = 3', 'utf-8')
    assert run(A, tmp_path, spec, check_only=True)[1]  # drift detected, nothing written
    assert ''.join(json.loads((tmp_path / TGT).read_text('utf-8'))['cells'][2]['source']) == 'y = 2'
    assert not [p for p in (tmp_path / 'backend' / 'notebooks').iterdir() if p.name != 'x.ipynb']  # no temp left


@pytest.mark.parametrize('cells', [
    [{'cell_type': 'code', 'id': 'd', 'source_path': 'h/b.py'}, {'cell_type': 'code', 'id': 'd', 'source_path': 'h/c.py'}],  # duplicate id
    [{'cell_type': 'raw', 'id': 'r', 'source_path': 'h/b.py'}],
    [{'cell_type': 'code', 'id': 'bad id', 'source_path': 'h/b.py'}],
    [{'cell_type': 'code', 'id': 'm', 'source_path': 'h/missing.py'}],
    [{'cell_type': 'code', 'id': 'e', 'source_path': '../outside.py'}],
    [{'cell_type': 'code', 'id': 'e', 'source_path': 'h/../h/b.py'}],
    [{'cell_type': 'code', 'id': 'e', 'source_path': '/etc/passwd'}],
    [{'cell_type': 'code', 'id': 'o', 'source_path': 'other/b.py'}],  # outside the spec directory
    [{'cell_type': 'code', 'id': 'k', 'source_path': 'h/b.py', 'outputs': []}],  # unknown key
    [],
])
def test_refuses_bad_cells(A, tmp_path, cells):
    (tmp_path / 'other').mkdir()
    (tmp_path / 'other' / 'b.py').write_text('x = 1\n')
    spec = make_repo(tmp_path, cells)
    with pytest.raises(A.AssemblyError):
        run(A, tmp_path, spec)
    assert not (tmp_path / TGT).exists()


def test_refuses_symlinks_targets_and_bad_code(A, tmp_path):
    spec = make_repo(tmp_path, [{'cell_type': 'code', 'id': 'l', 'source_path': 'h/link.py'}])
    (tmp_path / 'h' / 'link.py').symlink_to(tmp_path / 'h' / 'b.py')
    with pytest.raises(A.AssemblyError, match='symlink'):
        run(A, tmp_path, spec)
    for bad_target in ('backend/notebooks/other.ipynb', 'backend/x.ipynb', '../x.ipynb'):
        spec = make_repo_fresh(tmp_path, target=bad_target)
        with pytest.raises(A.AssemblyError):
            A.assemble(spec, bad_target, root=tmp_path, approved=(TGT,))
    spec = make_repo_fresh(tmp_path)
    with pytest.raises(A.AssemblyError, match='differs from the spec target'):
        A.assemble(spec, 'backend/notebooks/y.ipynb', root=tmp_path, approved=(TGT, 'backend/notebooks/y.ipynb'))
    with pytest.raises(A.AssemblyError, match='inside backend/notebooks'):
        spec = make_repo_fresh(tmp_path, target='backend/x.ipynb')
        A.assemble(spec, 'backend/x.ipynb', root=tmp_path, approved=('backend/x.ipynb',))
    spec = make_repo_fresh(tmp_path)
    os.rename(tmp_path / 'backend' / 'notebooks', tmp_path / 'backend' / 'real')
    (tmp_path / 'backend' / 'notebooks').symlink_to(tmp_path / 'backend' / 'real')
    with pytest.raises(A.AssemblyError, match='symlink'):
        run(A, tmp_path, spec)
    for src in ('def f(:\n', "open('.ai-team/x')\n"):
        spec = make_repo_fresh(tmp_path)
        (tmp_path / 'h' / 'b.py').write_text(src)
        with pytest.raises(A.AssemblyError):
            run(A, tmp_path, spec)


def make_repo_fresh(tmp_path, **kw):
    import shutil
    for p in ('backend', 'h'):
        q = tmp_path / p
        if q.is_symlink():
            q.unlink()
        elif q.exists():
            shutil.rmtree(q)
    return make_repo(tmp_path, **kw)


def test_refuses_overwriting_an_executed_target(A, tmp_path):
    spec = make_repo(tmp_path)
    run(A, tmp_path, spec)
    run(A, tmp_path, spec)  # an unexecuted (assembled) target may be re-assembled
    nb = json.loads((tmp_path / TGT).read_text('utf-8'))
    nb['cells'][1]['execution_count'] = 1
    (tmp_path / TGT).write_text(json.dumps(nb), 'utf-8')
    before = (tmp_path / TGT).read_bytes()
    with pytest.raises(A.AssemblyError, match='executed'):
        run(A, tmp_path, spec)
    assert (tmp_path / TGT).read_bytes() == before
    assert run(A, tmp_path, spec, check_only=True)[1] == []  # --check stays read-only and still compares sources


def test_approved_targets_are_exactly_20_14_21_and_22(A):
    assert A.APPROVED_TARGETS == ('backend/notebooks/20_spatial_count_experiments.ipynb', 'backend/notebooks/14_backend_catalog.ipynb',
                                  'backend/notebooks/21_spatial_evaluation_colours.ipynb', 'backend/notebooks/22_spatial_inference_contract.ipynb')


def test_real_notebook22_spec_is_approved_and_well_formed(A):
    """Read-only: the notebook-22 spec loads, targets the approved notebook 22, ids unique, sources compile, five FUNCTIONS cells. Never writes."""
    spec, d = A.read_spec(A.REPO, '.ai-team/handoffs/018/notebook_cells.json')
    assert spec['target'] == 'backend/notebooks/22_spatial_inference_contract.ipynb' and spec['target'] in A.APPROVED_TARGETS
    A.check_target(A.REPO, spec, spec['target'], A.APPROVED_TARGETS)
    cells = A.load_cells(A.REPO, spec, d)
    assert sum(c['source'].lstrip().startswith('# FUNCTIONS') for c in cells) == 5


def test_real_notebook21_spec_is_approved_and_well_formed(A):
    """Read-only: the notebook-21 spec loads, targets the approved notebook 21, ids unique, sources compile, four FUNCTIONS cells. Never writes."""
    spec, d = A.read_spec(A.REPO, '.ai-team/handoffs/017/notebook_cells.json')
    assert spec['target'] == 'backend/notebooks/21_spatial_evaluation_colours.ipynb' and spec['target'] in A.APPROVED_TARGETS
    A.check_target(A.REPO, spec, spec['target'], A.APPROVED_TARGETS)
    cells = A.load_cells(A.REPO, spec, d)
    assert sum(c['source'].lstrip().startswith('# FUNCTIONS') for c in cells) == 4


def test_real_notebook14_spec_is_approved_and_well_formed(A):
    """Read-only: the notebook-14 spec loads, targets the approved notebook 14, ids unique, sources compile, five FUNCTIONS cells. Never writes."""
    spec, d = A.read_spec(A.REPO, '.ai-team/handoffs/020/notebook_cells.json')
    assert spec['target'] == 'backend/notebooks/14_backend_catalog.ipynb' and spec['target'] in A.APPROVED_TARGETS
    A.check_target(A.REPO, spec, spec['target'], A.APPROVED_TARGETS)
    cells = A.load_cells(A.REPO, spec, d)
    assert sum(c['source'].lstrip().startswith('# FUNCTIONS') for c in cells) == 5


def test_real_notebook20_spec_is_approved_and_well_formed(A):
    """Read-only: the real spec loads, its target is the approved notebook 20, ids unique, sources compile. Never writes."""
    spec, d = A.read_spec(A.REPO, '.ai-team/handoffs/016/notebook_cells.json')
    assert spec['target'] in A.APPROVED_TARGETS
    A.check_target(A.REPO, spec, spec['target'], A.APPROVED_TARGETS)
    cells = A.load_cells(A.REPO, spec, d)
    assert sum(c['source'].lstrip().startswith('# FUNCTIONS') for c in cells) == 6
