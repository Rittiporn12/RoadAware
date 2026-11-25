"""RoadAware voice proxy — turns drive-mode warning sentences into speech for the website.

Two engines (ROADAWARE_TTS_ENGINE):
* mac (default): the Mac's own `say` command, i.e. the voice chosen in System Settings → Accessibility → Read & Speak
  (System speech language: Thai, System voice: e.g. Siri Voice 1). Free, offline, no limit. Browsers cannot use Siri
  voices directly, so this proxy renders them to audio files for the website.
* gemini: Gemini TTS (needs a key; the free tier allows only ~10 clips a day).

    .venv/bin/python backend/scripts/tts_proxy.py            # http://127.0.0.1:8010  (Ctrl+C to stop)

* The Gemini API key is read from the environment (GEMINI_API_KEY) or from ~/.roadaware-gemini-key, never from
  the browser and never stored in the repository. The website only ever talks to this local proxy.
* POST /tts {"text": "..."} → audio/wav (24 kHz mono 16-bit). GET /health → {"ok": true, "voice": ...}
* Every sentence is cached on disk (backend/rerun-tts-cache/<sha256>.wav, gitignored), so a warning that repeats
  is synthesised only once and costs nothing the second time.
* Only 127.0.0.1, only the website origins below, at most 400 characters per request.
"""
import base64
import collections
import hashlib
import json
import os
import re
import struct
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
CACHE = BACKEND / 'rerun-tts-cache'
PORT = int(os.environ.get('ROADAWARE_TTS_PORT', '8010'))
ENGINE = os.environ.get('ROADAWARE_TTS_ENGINE', 'mac').strip().lower()
SAY_RATE = os.environ.get('ROADAWARE_SAY_RATE', '200')  # words per minute for `say`; lively but clear
# Which Mac voice: 'auto' = best installed Thai voice (Premium > Enhanced > plain; Narisa before Kanya),
# 'system' = whatever Read & Speak's System voice is, or an exact voice name such as "Narisa (Enhanced)".
SAY_VOICE_SETTING = os.environ.get('ROADAWARE_SAY_VOICE', 'system').strip()  # default: the Mac's System voice (e.g. Siri Voice 1)


def thai_say_voices():
    try:
        out = subprocess.run(['say', '-v', '?'], capture_output=True, timeout=20).stdout.decode('utf-8', 'replace')
    except Exception:
        return []
    names = []
    for line in out.splitlines():
        m = re.match(r'^(.+?)\s{2,}(th[_-]TH)\b', line)
        if m:
            names.append(m.group(1).strip())
    return names


def pick_say_voice():
    if SAY_VOICE_SETTING.lower() == 'system':
        return None
    if SAY_VOICE_SETTING.lower() != 'auto':
        return SAY_VOICE_SETTING
    names = thai_say_voices()
    def score(n):
        q = 3 if 'premium' in n.lower() else 2 if 'enhanced' in n.lower() else 1
        return (q, 1 if n.lower().startswith('narisa') else 0)
    return max(names, key=score) if names else None


SAY_VOICE = None
# The System voice can be changed in System Settings at any time, so its clips are kept only for this run.
MAC_CACHE = CACHE / 'mac' / ('system-' + time.strftime('%Y%m%d-%H%M%S') if SAY_VOICE_SETTING.lower() == 'system' else 'named')
MODEL = os.environ.get('ROADAWARE_TTS_MODEL', 'gemini-3.8-flash-tts')
VOICE = os.environ.get('ROADAWARE_TTS_VOICE', 'Puck')
STYLE = 'lively, alert and friendly, like an upbeat Thai radio traffic announcer; clear and quick, never sleepy'
ORIGINS = {'http://127.0.0.1:5173', 'http://localhost:5173', 'http://127.0.0.1:3000', 'http://localhost:3000'}
ORIGINS |= {o.strip().rstrip('/') for o in os.environ.get('ROADAWARE_CORS_EXTRA', '').split(',') if o.strip().startswith('https://') and '*' not in o}
MAX_CHARS = 400
LOCK = threading.Lock()
# Free tier allows only a few requests per minute (3 RPM for the TTS model at the time of writing). Requests are
# paced to stay under it; raise ROADAWARE_TTS_RPM after enabling billing.
RPM = max(1, int(os.environ.get('ROADAWARE_TTS_RPM', '3')))
SENT = collections.deque()


def pace():
    while True:
        now = time.time()
        while SENT and now - SENT[0] >= 61:
            SENT.popleft()
        if len(SENT) < RPM:
            SENT.append(now)
            return
        time.sleep(61 - (now - SENT[0]) + 0.2)


BLOCKED_UNTIL = [0.0]  # set when the DAILY quota is used up: stop calling Gemini until it resets


class QuotaExhausted(Exception):
    pass


def retry_seconds(detail):
    m = re.search(r'retry in ((?:[0-9.]+h)?(?:[0-9.]+m)?(?:[0-9.]+s)?)', detail)
    if not m or not m.group(1):
        return None
    total = 0.0
    for num, unit in re.findall(r'([0-9.]+)([hms])', m.group(1)):
        total += float(num) * {'h': 3600, 'm': 60, 's': 1}[unit]
    return total


def synthesize_mac(text):
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / 'clip.wav'
        cmd = ['say', '--file-format=WAVE', '--data-format=LEI16@24000', '-o', str(out)]
        if SAY_VOICE:
            cmd += ['-v', SAY_VOICE]
        if SAY_RATE:
            cmd += ['-r', SAY_RATE]
        r = subprocess.run(cmd + [text], capture_output=True, timeout=60)
        if r.returncode != 0 or not out.is_file() or out.stat().st_size < 1000:
            raise RuntimeError('say failed: ' + r.stderr.decode('utf-8', 'replace')[:200])
        return out.read_bytes()


def synthesize_paced(text):
    if ENGINE == 'mac':
        return synthesize_mac(text)
    if time.time() < BLOCKED_UNTIL[0]:
        raise QuotaExhausted()
    for attempt in range(3):
        pace()
        try:
            return synthesize(text)
        except urllib.error.HTTPError as e:
            if e.code != 429:
                raise
            detail = e.read()[:400].decode('utf-8', 'replace')
            wait = retry_seconds(detail)
            if 'per day' in detail or (wait is not None and wait > 90):
                BLOCKED_UNTIL[0] = time.time() + (wait if wait else 3600)
                h = (wait or 3600) / 3600
                print(f'DAILY Gemini quota used up — using the Mac voice for new sentences for ~{h:.1f} h. '
                      f'Saved clips still play. (free tier: very few clips per day)', flush=True)
                raise QuotaExhausted()
            if attempt == 2:
                raise QuotaExhausted()
            wait = min(65.0, (wait or 30.0) + 1)
            print(f'quota busy — waiting {wait:.0f}s and retrying (free tier {RPM}/min)', flush=True)
            time.sleep(wait)


def api_key():
    k = os.environ.get('GEMINI_API_KEY', '').strip()
    if not k:
        p = Path.home() / '.roadaware-gemini-key'
        if p.is_file():
            k = p.read_text('utf-8').strip()
    return k


def wav_from_pcm(pcm, rate=24000):
    return b'RIFF' + struct.pack('<I', 36 + len(pcm)) + b'WAVEfmt ' + struct.pack('<IHHIIHH', 16, 1, 1, rate, rate * 2, 2, 16) + b'data' + struct.pack('<I', len(pcm)) + pcm


def synthesize(text):
    body = {
        'model': MODEL,
        'input': [{'type': 'user_input', 'content': [{'type': 'text', 'text': text,
                                                       'annotations': [{'type': 'speech_metadata', 'style': STYLE}]}]}],
        'response_format': {'type': 'audio'},
        'generation_config': {'speech_config': [{'voice': VOICE}]},
    }
    req = urllib.request.Request('https://generativelanguage.googleapis.com/v1beta/interactions', data=json.dumps(body).encode('utf-8'),
                                 headers={'Content-Type': 'application/json', 'x-goog-api-key': api_key()}, method='POST')
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.loads(r.read())
    parts = [c for s in data.get('steps', []) if s.get('type') == 'model_output' for c in s.get('content', []) if c.get('type') == 'audio']
    if parts:
        audio = base64.b64decode(parts[-1]['data'])
        return audio if audio[:4] == b'RIFF' else wav_from_pcm(audio)
    # older generateContent-style answer: candidates[].content.parts[].inlineData (raw PCM)
    for cand in data.get('candidates', []):
        for part in (cand.get('content') or {}).get('parts', []):
            inline = part.get('inlineData') or part.get('inline_data')
            if inline and inline.get('data'):
                audio = base64.b64decode(inline['data'])
                return audio if audio[:4] == b'RIFF' else wav_from_pcm(audio)
    raise ValueError('no audio in the Gemini answer')


class Handler(BaseHTTPRequestHandler):
    def _cors(self):
        origin = self.headers.get('Origin', '')
        if origin in ORIGINS:
            self.send_header('Access-Control-Allow-Origin', origin)
            self.send_header('Vary', 'Origin')
            self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def _json(self, code, obj):
        b = json.dumps(obj).encode('utf-8')
        self.send_response(code); self._cors()
        self.send_header('Content-Type', 'application/json'); self.send_header('Content-Length', str(len(b))); self.end_headers()
        self.wfile.write(b)

    def do_OPTIONS(self):
        self.send_response(204); self._cors(); self.end_headers()

    def do_GET(self):
        if self.path == '/health':
            return self._json(200, {'ok': ENGINE == 'mac' or bool(api_key()), 'engine': ENGINE, 'model': MODEL, 'voice': VOICE})
        self._json(404, {'error': 'not_found'})

    def do_POST(self):
        if self.path != '/tts':
            return self._json(404, {'error': 'not_found'})
        try:
            n = int(self.headers.get('Content-Length', '0'))
            text = str(json.loads(self.rfile.read(min(n, 8192)) or b'{}').get('text', '')).strip()
        except (ValueError, TypeError):
            return self._json(400, {'error': 'bad_request'})
        if not text or len(text) > MAX_CHARS:
            return self._json(400, {'error': 'text_required_max_' + str(MAX_CHARS)})
        if ENGINE != 'mac' and not api_key():
            return self._json(503, {'error': 'no_api_key'})
        sig = ('mac|' + str(SAY_VOICE) + '|' + SAY_RATE) if ENGINE == 'mac' else (MODEL + '|' + VOICE + '|' + STYLE)
        key = hashlib.sha256((sig + '|' + text).encode('utf-8')).hexdigest()
        path = (MAC_CACHE if ENGINE == 'mac' else CACHE) / (key + '.wav')
        try:
            if not path.is_file():
                with LOCK:  # one synthesis at a time keeps the free-tier rate limit happy
                    if not path.is_file():
                        audio = synthesize_paced(text)
                        path.parent.mkdir(parents=True, exist_ok=True)
                        print(f'new voice clip saved ({len(list(path.parent.glob("*.wav"))) + 1} in cache)', flush=True)
                        tmp = path.with_suffix('.tmp')
                        tmp.write_bytes(audio)
                        os.replace(tmp, path)
            audio = path.read_bytes()
        except QuotaExhausted:
            return self._json(503, {'error': 'quota_exhausted'})
        except urllib.error.HTTPError as e:
            detail = e.read()[:300].decode('utf-8', 'replace')
            print('Gemini HTTP', e.code, detail, flush=True)
            return self._json(502, {'error': 'gemini_http_' + str(e.code)})
        except Exception as e:  # network down, quota, unexpected answer → the website falls back to the device voice
            print('TTS failed:', type(e).__name__, str(e)[:200], flush=True)
            return self._json(502, {'error': 'tts_failed'})
        self.send_response(200); self._cors()
        self.send_header('Content-Type', 'audio/wav'); self.send_header('Content-Length', str(len(audio)))
        self.send_header('Cache-Control', 'max-age=86400'); self.end_headers()
        self.wfile.write(audio)

    def log_message(self, fmt, *args):
        if '/tts' in (args[0] if args else ''):
            print('tts', args[1] if len(args) > 1 else '', flush=True)


def main():
    if ENGINE == 'mac':
        global SAY_VOICE
        MAC_CACHE.mkdir(parents=True, exist_ok=True)
        thai = thai_say_voices()
        print('Thai voices usable by the voice proxy:', ', '.join(thai) if thai else 'NONE (download one in Read & Speak → Thai → Voice)', flush=True)
        SAY_VOICE = pick_say_voice()
        print(f'RoadAware voice proxy on http://127.0.0.1:{PORT}  (Mac voice: {SAY_VOICE or "System voice from Read & Speak — set System speech language: Thai, System voice: Siri Voice 1"}, rate {SAY_RATE}) — Ctrl+C to stop', flush=True)
    else:
        if not api_key():
            sys.exit('No Gemini API key: set GEMINI_API_KEY or put the key in ~/.roadaware-gemini-key')
        print(f'RoadAware voice proxy on http://127.0.0.1:{PORT}  (Gemini {MODEL}, voice {VOICE}) — Ctrl+C to stop', flush=True)
    ThreadingHTTPServer(('127.0.0.1', PORT), Handler).serve_forever()


if __name__ == '__main__':
    main()
