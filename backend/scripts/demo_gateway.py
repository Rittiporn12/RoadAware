"""One local address for the presentation tunnel (prepared by Claude).

    .venv/bin/python backend/scripts/demo_gateway.py      # http://127.0.0.1:8020

/voice/...  -> the voice proxy  http://127.0.0.1:8010/...
everything else -> the API      http://127.0.0.1:8000/...
Requests, status codes, bodies and headers (incl. CORS) are passed through unchanged, so a single Cloudflare quick
tunnel serves both — fewer tunnels means fewer "429 too many requests" refusals from trycloudflare.com.
Listens on 127.0.0.1 only; the tunnel is the only way in.
"""
import os
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(os.environ.get('ROADAWARE_GATEWAY_PORT', '8020'))
API = 'http://127.0.0.1:8000'
VOICE = 'http://127.0.0.1:8010'
HOP = {'connection', 'keep-alive', 'proxy-authenticate', 'proxy-authorization', 'te', 'trailers', 'transfer-encoding', 'upgrade', 'host',
       'content-length', 'server', 'date'}
MAX_BODY = 1 << 20


class Gateway(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def _forward(self):
        if self.path.startswith('/voice/') or self.path == '/voice':
            target = VOICE + (self.path[len('/voice'):] or '/')
        else:
            target = API + self.path
        n = int(self.headers.get('Content-Length') or 0)
        body = self.rfile.read(min(n, MAX_BODY)) if n else None
        req = urllib.request.Request(target, data=body, method=self.command,
                                     headers={k: v for k, v in self.headers.items() if k.lower() not in HOP})
        try:
            r = urllib.request.urlopen(req, timeout=90)
            status, headers, data = r.status, r.headers.items(), r.read()
        except urllib.error.HTTPError as e:
            status, headers, data = e.code, e.headers.items(), e.read()
        except Exception:
            status, headers, data = 502, [('Content-Type', 'application/json')], b'{"error":"upstream_unavailable"}'
        self.send_response(status)
        for k, v in headers:
            if k.lower() not in HOP:
                self.send_header(k, v)
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(data)

    do_GET = do_POST = do_OPTIONS = do_HEAD = _forward

    def log_message(self, fmt, *args):
        pass


if __name__ == '__main__':
    print(f'RoadAware demo gateway on http://127.0.0.1:{PORT}  (API {API}, voice {VOICE}/ -> /voice/)', flush=True)
    ThreadingHTTPServer(('127.0.0.1', PORT), Gateway).serve_forever()
