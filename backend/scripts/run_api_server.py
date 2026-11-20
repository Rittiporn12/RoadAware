"""Start the local research API on 127.0.0.1 only (task 019). From the repository root:
    .venv/bin/python backend/scripts/run_api_server.py            # http://127.0.0.1:8000  (stop with Ctrl+C)
    .venv/bin/python backend/scripts/run_api_server.py --port 8765
    .venv/bin/python backend/scripts/run_api_server.py --national   # national V4 (26,740 DOH segments) instead of the pilot
One process, one worker, bounded concurrency, BLAS/OpenMP threads limited before numpy is imported. Never binds a public interface.
"""
import argparse
import logging
import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--port', type=int, default=8000)
    ap.add_argument('--national', action='store_true', help='serve the national V4 artifacts (default: pilot V3)')
    ap.add_argument('--log-level', default='info', choices=('info', 'warning', 'error'))
    a = ap.parse_args(argv)
    if not 1024 <= a.port <= 65535:
        sys.exit('port must be 1024..65535')
    for v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
        os.environ.setdefault(v, '2')
    os.environ['ROADAWARE_API_VARIANT'] = 'v4' if a.national else 'v3'
    sys.path.insert(0, str(BACKEND))
    logging.basicConfig(level=getattr(logging, a.log_level.upper()), format='%(asctime)s %(levelname)s %(name)s %(message)s')
    import uvicorn
    from api.app import create_app
    uvicorn.run(create_app(), host='127.0.0.1', port=a.port, workers=1, limit_concurrency=32, timeout_keep_alive=5, log_level=a.log_level,
                server_header=False, proxy_headers=False)


if __name__ == '__main__':
    main()
