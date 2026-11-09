#!/usr/bin/env python3
"""Local Codex-to-Claude bridge with a live, persistent activity timeline."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import selectors
import shutil
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / '.ai-team'


def note(message):
    STATE.mkdir(exist_ok=True)
    stamp = dt.datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S %z')
    line = f'[{stamp}] {message}'
    with (STATE / 'activity.log').open('a', encoding='utf-8') as f:
        f.write(line + '\n')
    print(line, flush=True)


def status(stage, **extra):
    path = STATE / 'status.json'
    temp = STATE / 'status.tmp'
    temp.write_text(json.dumps({'stage': stage, 'updated_at': dt.datetime.now().astimezone().isoformat(), **extra}, ensure_ascii=False, indent=2), encoding='utf-8')
    temp.replace(path)


def describe(event):
    kind = event.get('type')
    if kind == 'system' and event.get('subtype') == 'init':
        note('Claude: connected; model=' + str(event.get('model', 'default')))
    elif kind == 'assistant':
        for part in event.get('message', {}).get('content', []):
            if part.get('type') == 'text':
                for line in part.get('text', '').splitlines():
                    if line.strip():
                        note('Claude: ' + line[:700])
            elif part.get('type') == 'tool_use':
                args = part.get('input', {})
                detail = args.get('file_path') or args.get('path') or args.get('pattern') or args.get('command') or ''
                note(f"Claude tool: {part.get('name', '?')} {str(detail)[:400]}")
    elif kind == 'user':
        content = event.get('message', {}).get('content', [])
        if isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and part.get('type') == 'tool_result':
                    note('Claude tool: ' + ('FAILED' if part.get('is_error') else 'completed'))


def stop(proc):
    if proc.poll() is None:
        os.killpg(proc.pid, signal.SIGTERM)
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()


def run(task_arg):
    task = (ROOT / task_arg).resolve()
    if not task.is_relative_to(ROOT) or not task.is_file():
        raise ValueError('Task must be an existing file inside this project.')
    config = json.loads((ROOT / 'workflow/team.json').read_text())
    timeout = float(config['timeout_seconds'])
    budget = float(config['max_budget_usd'])
    if not 0 < timeout <= 3600 or not 0 < budget <= 20:
        raise ValueError('Timeout must be 1–3600 seconds and budget must be >0 and <=20 USD.')
    executable = shutil.which('claude')
    if not executable:
        raise RuntimeError('claude CLI not found. Install it or correct your Terminal PATH.')
    STATE.mkdir(exist_ok=True)
    lock = STATE / 'worker.lock'
    try:
        lock.mkdir()
    except FileExistsError:
        raise RuntimeError('A worker is active or left a stale lock. Check it before removing .ai-team/worker.lock.')
    proc = None
    try:
        (lock / 'pid').write_text(str(os.getpid()))
        run_id = dt.datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + str(os.getpid())
        out = STATE / 'runs' / run_id
        out.mkdir(parents=True)
        task_text = task.read_text(encoding='utf-8')
        (out / 'task.md').write_text(task_text, encoding='utf-8')
        note('Codex → Claude: ' + str(task.relative_to(ROOT)))
        status('claude_running', task=str(task.relative_to(ROOT)), run_id=run_id)
        tools = ','.join(config['tools'])
        command = [executable, '-p', '--verbose', '--output-format', 'stream-json',
                   '--permission-mode', 'dontAsk', '--tools', tools, '--allowedTools', tools,
                   '--strict-mcp-config', '--mcp-config', '{"mcpServers":{}}',
                   '--max-budget-usd', str(budget), '--no-session-persistence']
        prompt = ('You are the implementation worker for Codex. Follow CLAUDE.md. '
                  'Give short progress updates. Only perform this task:\n\n' + task_text)
        final = None
        with (out / 'stderr.log').open('wb') as err, (out / 'events.jsonl').open('ab') as raw:
            proc = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                    stderr=err, start_new_session=True)
            proc.stdin.write(prompt.encode('utf-8'))
            proc.stdin.close()
            deadline = time.monotonic() + timeout
            pending = b''
            with selectors.DefaultSelector() as selector:
                selector.register(proc.stdout, selectors.EVENT_READ)
                while selector.get_map():
                    if time.monotonic() >= deadline:
                        raise TimeoutError(f'Claude exceeded {timeout:g} seconds.')
                    for key, _ in selector.select(timeout=min(0.5, max(0, deadline-time.monotonic()))):
                        chunk = os.read(key.fileobj.fileno(), 65536)
                        if not chunk:
                            selector.unregister(key.fileobj)
                            continue
                        raw.write(chunk)
                        raw.flush()
                        pending += chunk
                        while b'\n' in pending:
                            line, pending = pending.split(b'\n', 1)
                            try:
                                event = json.loads(line)
                            except (ValueError, UnicodeError):
                                continue
                            describe(event)
                            if event.get('type') == 'result':
                                final = event
                if pending.strip():
                    try:
                        event = json.loads(pending)
                        describe(event)
                        if event.get('type') == 'result':
                            final = event
                    except (ValueError, UnicodeError):
                        pass
            proc.wait(timeout=max(0.1, deadline-time.monotonic()))
        if final is not None:
            (out / 'result.json').write_text(json.dumps(final, ensure_ascii=False, indent=2), encoding='utf-8')
        success = proc.returncode == 0 and final is not None and final.get('subtype') == 'success' and not final.get('is_error', False)
        if not success:
            note('Claude: run failed; inspect ' + str(out.relative_to(ROOT)))
            status('failed', run_id=run_id, exit_code=proc.returncode)
            return 1
        note('Claude → Codex: report ready; independent review required. ' + str(out.relative_to(ROOT)))
        status('awaiting_codex_review', run_id=run_id)
        return 0
    except BaseException as exc:
        if proc is not None:
            stop(proc)
        note('Bridge: stopped — ' + str(exc))
        status('failed', error=str(exc))
        raise
    finally:
        shutil.rmtree(lock)


def monitor():
    STATE.mkdir(exist_ok=True)
    log = STATE / 'activity.log'
    log.touch(exist_ok=True)
    print('RoadAware | Codex ↔ Claude | LIVE\nRecorded stages, tool activity and results. Ctrl+C closes this monitor only.\n', flush=True)
    with log.open(encoding='utf-8') as f:
        history = f.readlines()
        for line in history[-60:]:
            print(line, end='', flush=True)
        if not history:
            print('Waiting for Codex to send a task…', flush=True)
        while True:
            line = f.readline()
            if line:
                print(line, end='', flush=True)
            else:
                time.sleep(0.25)


def review(verdict, message):
    current = json.loads((STATE / 'status.json').read_text(encoding='utf-8'))
    if current.get('stage') != 'awaiting_codex_review':
        raise ValueError('No completed worker run is awaiting review.')
    run_id = current['run_id']
    record = {'run_id': run_id, 'verdict': verdict, 'message': message,
              'reviewed_at': dt.datetime.now().astimezone().isoformat()}
    (STATE / 'runs' / run_id / 'review.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    status('ready' if verdict == 'pass' else 'needs_changes', run_id=run_id, review=record)
    note('Codex review: ' + verdict.upper() + ' — ' + message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    sub.add_parser('monitor')
    sub.add_parser('note').add_argument('message')
    sub.add_parser('run').add_argument('task')
    review_parser = sub.add_parser('review')
    review_parser.add_argument('verdict', choices=['pass', 'fail'])
    review_parser.add_argument('message')
    args = parser.parse_args()
    try:
        if args.action == 'monitor':
            monitor()
        elif args.action == 'note':
            note(args.message)
        elif args.action == 'review':
            review(args.verdict, args.message)
        else:
            return run(args.task)
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
