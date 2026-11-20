"""RoadAware voice proxy — turns drive-mode warning sentences into speech with Gemini TTS.

    .venv/bin/python backend/scripts/tts_proxy.py            # http://127.0.0.1:8010  (Ctrl+C to stop)

* The Gemini API key is read from the environment (GEMINI_API_KEY) or from ~/.roadaware-gemini-key, never from
  the browser and never stored in the repository. The website only ever talks to this local proxy.
* POST /tts {"text": "..."} → audio/wav (24 kHz mono 16-bit). GET /health → {"ok": true, "voice": ...}
* Every sentence is cached on disk (backend/rerun-tts-cache/<sha256>.wav, gitignored), so a warning that repeats
  is synthesised only once and costs nothing the second time.
* Only 127.0.0.1, only the website origins below, at most 400 characters per request.
"""
import base64
import hashlib
import json
import os
import struct
import sys
import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
CACHE = BACKEND / 'rerun-tts-cache'
PORT = int(os.environ.get('ROADAWARE_TTS_PORT', '8010'))
MODEL = os.environ.get('ROADAWARE_TTS_MODEL', 'gemini-3.8-flash-tts')
VOICE = os.environ.get('ROADAWARE_TTS_VOICE', 'Puck')
STYLE = 'lively, alert and friendly, like an upbeat Thai radio traffic announcer; clear and quick, never sleepy'
ORIGINS = {'http://127.0.0.1:5173', 'http://localhost:5173', 'http://127.0.0.1:3000', 'http://localhost:3000'}
MAX_CHARS = 400
LOCK = threading.Lock()


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
            return self._json(200, {'ok': bool(api_key()), 'model': MODEL, 'voice': VOICE})
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
        if not api_key():
            return self._json(503, {'error': 'no_api_key'})
        key = hashlib.sha256((MODEL + '|' + VOICE + '|' + STYLE + '|' + text).encode('utf-8')).hexdigest()
        path = CACHE / (key + '.wav')
        try:
            if not path.is_file():
                with LOCK:  # one synthesis at a time keeps the free-tier rate limit happy
                    if not path.is_file():
                        audio = synthesize(text)
                        CACHE.mkdir(exist_ok=True)
                        tmp = path.with_suffix('.tmp')
                        tmp.write_bytes(audio)
                        os.replace(tmp, path)
            audio = path.read_bytes()
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
    if not api_key():
        sys.exit('No Gemini API key: set GEMINI_API_KEY or put the key in ~/.roadaware-gemini-key')
    print(f'RoadAware voice proxy on http://127.0.0.1:{PORT}  (model {MODEL}, voice {VOICE}) — Ctrl+C to stop', flush=True)
    ThreadingHTTPServer(('127.0.0.1', PORT), Handler).serve_forever()


if __name__ == '__main__':
    main()
