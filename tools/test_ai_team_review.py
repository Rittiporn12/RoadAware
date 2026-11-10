"""Review bookkeeping must not overwrite a newer worker's live status."""
import importlib.util
import json
from pathlib import Path

import pytest


@pytest.fixture
def bridge(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location('review_bridge', Path(__file__).with_name('ai_team.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, 'STATE', tmp_path)
    monkeypatch.setattr(module, 'note', lambda message: None)
    return module


def completed(bridge, run_id, error=False):
    path = bridge.STATE / 'runs' / run_id
    path.mkdir(parents=True)
    (path / 'result.json').write_text(json.dumps({'is_error': error, 'result': 'worker report'}))
    return path


def test_completed_previous_run_preserves_live_worker(bridge):
    prior = completed(bridge, 'prior')
    bridge.status('running', run_id='active')
    before = (bridge.STATE / 'status.json').read_bytes()
    bridge.review('pass', 'independently verified', 'prior')
    assert (bridge.STATE / 'status.json').read_bytes() == before
    assert json.loads((prior / 'review.json').read_text())['verdict'] == 'pass'
    with pytest.raises(ValueError, match='already been reviewed'):
        bridge.review('fail', 'duplicate', 'prior')


def test_current_review_requires_completion_and_updates_status(bridge):
    completed(bridge, 'current')
    bridge.status('running', run_id='current')
    with pytest.raises(ValueError, match='awaiting review'):
        bridge.review('pass', 'too early')
    bridge.status('awaiting_codex_review', run_id='current')
    bridge.review('fail', 'observed failure')
    assert json.loads((bridge.STATE / 'status.json').read_text())['stage'] == 'needs_changes'


def test_missing_failed_and_invalid_reports_rejected(bridge):
    bridge.status('running', run_id='active')
    completed(bridge, 'failed', error=True)
    for target in ('missing', 'failed', '../escape', '..'):
        with pytest.raises(ValueError):
            bridge.review('pass', 'cannot accept', target)
