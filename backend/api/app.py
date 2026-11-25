"""Thin local FastAPI transport (task 019). Business logic lives in the pinned notebook FUNCTIONS (13/14/22/24) behind backend/api/runtime.py;
this module only does HTTP: lifespan, readiness, bounded strict JSON bodies, CORS allowlist, sanitised error envelopes and finite JSON output.

    create_app()                      -> real fail-closed runtime loaded in the lifespan (load_runtime)
    create_app(runtime_factory=f)     -> tests inject a tiny fake/fixture runtime (clearly labelled there)
"""
import json
import logging
import os
import math
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import openapi_docs as D
from .runtime import StartupError, load_runtime

log = logging.getLogger('roadaware.api')
API_VERSION = 'roadaware-api-v3.0'
# transport constants (needed before the config is verified); mirrored in backend/config/backend_api_v3.json "transport"/"limits"
MAX_BODY_BYTES = 65536
CORS_ORIGINS = ('http://localhost:5173', 'http://127.0.0.1:5173', 'http://localhost:3000', 'http://127.0.0.1:3000')
# Demo hosting: extra exact https origins (e.g. the GitHub Pages site) from ROADAWARE_CORS_EXTRA="https://a,https://b".
# Exact origins only — no wildcard, no credentials, never http (except the localhost defaults above).
CORS_ORIGINS = CORS_ORIGINS + tuple(o.strip().rstrip('/') for o in os.environ.get('ROADAWARE_CORS_EXTRA', '').split(',')
                                    if o.strip().startswith('https://') and '*' not in o)
GENERIC = {'unavailable': 'a required accepted artifact is unavailable or failed verification; details are in the local server log only',
           'internal': 'internal error; the request was not answered (no partial or zero result)'}


def _finite(o):
    if isinstance(o, float):
        if not math.isfinite(o):
            raise ValueError('non-finite float')
    elif isinstance(o, dict):
        for k, v in o.items():
            if not isinstance(k, str):
                raise ValueError('non-string key')
            _finite(v)
    elif isinstance(o, (list, tuple)):
        for v in o:
            _finite(v)
    return o


class StrictJSONResponse(Response):
    """Refuses NaN/Infinity (never silently nulls); UTF-8 without ASCII escaping."""
    media_type = 'application/json'

    def render(self, content):
        _finite(content)
        return json.dumps(content, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode('utf-8')


def transport_error(status, code, family, message):
    msg = GENERIC.get(family, message)
    return StrictJSONResponse({'ok': False, 'api_version': API_VERSION, 'production_ready': False,
                               'error': {'code': code, 'family': family, 'message': msg}}, status_code=status)


def _send(body, status=200):
    try:
        return StrictJSONResponse(body, status_code=status)
    except (ValueError, TypeError):
        log.exception('refusing a non-finite or non-JSON response')
        return transport_error(500, 'response_invalid', 'internal', '')


async def read_body(request):
    ct = request.headers.get('content-type', '')
    if ct.split(';')[0].strip().lower() != 'application/json':
        raise _Transport(415, 'unsupported_media_type', 'media_type', 'Content-Type must be application/json')
    cl = request.headers.get('content-length')
    if cl is not None and (not cl.isdigit() or int(cl) > MAX_BODY_BYTES):
        raise _Transport(413, 'body_too_large', 'too_large', 'request body exceeds ' + str(MAX_BODY_BYTES) + ' bytes')
    buf = bytearray()
    async for chunk in request.stream():
        buf += chunk
        if len(buf) > MAX_BODY_BYTES:
            raise _Transport(413, 'body_too_large', 'too_large', 'request body exceeds ' + str(MAX_BODY_BYTES) + ' bytes')
    return bytes(buf)


class _Transport(Exception):
    def __init__(self, status, code, family, message):
        super().__init__(code)
        self.args4 = (status, code, family, message)


def _responses(method, path, *codes):
    return D.responses(method, path, *codes)


def create_app(runtime_factory=None):
    factory = runtime_factory or load_runtime
    from .review import ReviewData, ReviewError
    from .runtime import REPO as _REPO
    review_data = ReviewData(_REPO)

    @asynccontextmanager
    async def lifespan(app):
        app.state.runtime = None
        app.state.runtime = await run_in_threadpool(factory)
        log.info('runtime components: %s', app.state.runtime.public_components())
        yield
        app.state.runtime = None

    app = FastAPI(title='RoadAware local research API', version=API_VERSION, lifespan=lifespan, docs_url=None, redoc_url=None,
                  default_response_class=StrictJSONResponse,
                  description='Local research backend (127.0.0.1). production_ready is always false. Quantities are expected recorded-count rates, '
                              'not probabilities; no routing, no auth, no deployment.')
    app.add_middleware(CORSMiddleware, allow_origins=list(CORS_ORIGINS), allow_credentials=False, allow_methods=['GET', 'POST', 'OPTIONS'],
                       allow_headers=['Content-Type'], max_age=600)

    def rt_or_raise(request):
        rt = getattr(request.app.state, 'runtime', None)
        if rt is None or not rt.ready:
            raise _Transport(503, 'backend_not_ready', 'unavailable', '')
        return rt

    async def answer(request, fn, *args):
        try:
            rt = rt_or_raise(request)
            body = await run_in_threadpool(getattr(rt, fn), *args)
            return _send(body)
        except _Transport as t:
            return transport_error(*t.args4)
        except StartupError:
            return transport_error(503, 'component_unavailable', 'unavailable', '')
        except Exception as e:
            rt = getattr(request.app.state, 'runtime', None)
            if rt is not None and rt.h24 is not None and isinstance(e, rt.h24['ApiError']):
                if e.family in ('unavailable', 'internal'):
                    log.error('request refused as %s: %s', e.code, e)
                return _send(rt.h24['error_body'](e), e.status)
            log.exception('unexpected failure in %s', fn)
            return transport_error(500, 'internal_error', 'internal', '')

    async def answer_body(request, fn, *extra):
        try:
            raw = await read_body(request)
            rt = rt_or_raise(request)
        except _Transport as t:
            return transport_error(*t.args4)
        try:
            obj = rt.h24['parse_json_body'](raw, MAX_BODY_BYTES)
        except rt.h24['ApiError'] as e:
            return _send(rt.h24['error_body'](e), e.status)
        return await answer(request, fn, obj, *extra)

    @app.post('/api/v1/review/actual', include_in_schema=False)
    async def review_actual(request: Request):
        """Look-back view: recorded accidents per segment per day (2024-25 seen diagnostic years, 2026 Jan-Sep unseen test)."""
        try:
            raw = await read_body(request)
        except _Transport as t:
            return transport_error(*t.args4)
        try:
            obj = json.loads(raw.decode('utf-8'))
            return _send(await run_in_threadpool(review_data.query, obj))
        except ReviewError as e:
            return transport_error(e.status, e.code, 'unavailable' if e.status >= 500 else 'invalid', e.message)
        except (ValueError, UnicodeDecodeError):
            return transport_error(400, 'invalid_json', 'invalid', 'body must be JSON')

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request, exc):
        if exc.status_code == 404:
            return transport_error(404, 'not_found', 'not_found', 'no such route')
        if exc.status_code == 405:
            return transport_error(405, 'method_not_allowed', 'method', 'method not allowed for this route')
        return transport_error(exc.status_code, 'http_error', 'invalid', 'request refused')

    @app.exception_handler(Exception)
    async def unexpected(request, exc):
        log.exception('unhandled error')
        return transport_error(500, 'internal_error', 'internal', '')

    @app.get('/health', summary='Liveness (process up); not readiness', responses=_responses('get', '/health'))
    async def health():
        return {'status': 'alive', 'api_version': API_VERSION, 'production_ready': False}

    @app.get('/ready', summary='Readiness: 200 research_backend_ready or 503', responses=_responses('get', '/ready', 503))
    async def ready(request: Request):
        rt = getattr(request.app.state, 'runtime', None)
        comps = rt.public_components() if rt is not None else {'runtime': {'status': 'starting', 'code': None}}
        ok = rt is not None and rt.ready
        return _send({'ok': ok, 'api_version': API_VERSION, 'research_backend_ready': ok, 'production_ready': False, 'components': comps},
                     200 if ok else 503)

    @app.get('/api/v1/metadata', summary='Versions, limits, components, colour cutoffs and coverage rules', responses=_responses('get', '/api/v1/metadata', 503))
    async def metadata(request: Request):
        return await answer(request, 'metadata')

    @app.get('/api/v1/evaluation', summary='Accepted 21 summary with numeric selected/baseline OOF 2022-23 + seen 2024-25 metrics; separate 2026 diagnostic aggregates',
             responses=_responses('get', '/api/v1/evaluation', 503))
    async def evaluation(request: Request):
        return await answer(request, 'evaluation')

    @app.get('/api/v1/provinces', summary='77 catalog provinces (representative label points only)', responses=_responses('get', '/api/v1/provinces', 503))
    async def provinces(request: Request):
        return await answer(request, 'provinces')

    @app.get('/api/v1/history', summary='Province retrospective monthly history 2021-01..2025-12 (V2 compatibility)',
             responses=_responses('get', '/api/v1/history', 400, 404, 503), openapi_extra=D.query_params('/api/v1/history'))
    async def history(request: Request):
        return await answer(request, 'province_history', list(request.query_params.multi_items()))

    @app.get('/api/v1/segments', summary='Qualified DOH segment GeoJSON by bbox with limit/cursor', responses=_responses('get', '/api/v1/segments', 400, 503),
             openapi_extra=D.query_params('/api/v1/segments'))
    async def segments(request: Request):
        return await answer(request, 'segments', list(request.query_params.multi_items()))

    @app.get('/api/v1/segments/{segment_id}', summary='One qualified segment (unknown/unsupported -> 404 coverage)',
             responses=_responses('get', '/api/v1/segments/{segment_id}', 400, 404, 503))
    async def segment(request: Request, segment_id: str):
        if request.query_params:
            return transport_error(400, 'invalid_fields', 'invalid', 'this route takes no query parameters')
        return await answer(request, 'segment', segment_id)

    @app.post('/api/v1/spatial/history', summary='Segment history before the SAME target issue/label cutoff (notebook 14) + period status',
              responses=_responses('post', '/api/v1/spatial/history', 400, 404, 413, 415, 503), openapi_extra=D.request_body('/api/v1/spatial/history'))
    async def spatial_history(request: Request):
        return await answer_body(request, 'spatial_history')

    @app.post('/api/v1/spatial/predictions', summary='Notebook-22 selected policy: {unit, requests[1..128]}',
              responses=_responses('post', '/api/v1/spatial/predictions', 400, 404, 413, 415, 503), openapi_extra=D.request_body('/api/v1/spatial/predictions'))
    async def spatial_predictions(request: Request):
        return await answer_body(request, 'spatial_predict', 'selected')

    @app.post('/api/v1/spatial/baseline-predictions', summary='Notebook-22 locked strong baseline (comparison only)',
              responses=_responses('post', '/api/v1/spatial/baseline-predictions', 400, 404, 413, 415, 503),
              openapi_extra=D.request_body('/api/v1/spatial/baseline-predictions'))
    async def spatial_baseline(request: Request):
        return await answer_body(request, 'spatial_predict', 'baseline')

    @app.post('/api/v1/predictions', summary='Preserved V2 province predictions via notebook 13 (province scope; never rescaled to roads)',
              responses=_responses('post', '/api/v1/predictions', 400, 413, 415, 503), openapi_extra=D.request_body('/api/v1/predictions'))
    async def province_predictions(request: Request):
        return await answer_body(request, 'province_predict')

    return app
