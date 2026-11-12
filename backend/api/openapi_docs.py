"""OpenAPI documentation for the task-019 local API: bounded request-body schemas and ACTUAL public examples. Documentation only.

The single validation authority is the pinned notebook FUNCTIONS behind backend/api/runtime.py: notebook 24 (strict JSON, exact top-level fields,
64 KiB body), notebook 22 predict_batch (unit, 1..128 rows, row fields, dates, coverage), notebook 14 (history queries) and notebook 13
validate_requests (V2 province rows). The schemas below mirror those contracts for client authors; nothing here validates a request.

Examples are copied from actual saved public outputs (no event rows, no paths): the accepted notebook-22 prediction_fixtures.json (first saved row of
the daily/6h selected and daily baseline batches, re-asked as a one-row batch), the saved notebook-13 serving_examples.json, the hash-verified
notebook-14 province_monthly.csv / 21 metrics_by_group.csv rows, the live 001 smoke sample_responses.json and the fixed notebook-24/transport
messages. A response example is a SUBSET of the actual answer (trimmed lists such as geometry coordinates are marked); smoke_api_live.py re-asks
every example with a request against the live server and checks it with matches().
"""
import math

API_VERSION = 'roadaware-api-v3.0'
MAX_BATCH = 128  # mirrors backend_api_v3.json limits.max_batch (checked by the tests)
TIME_BLOCKS = ['00-06', '06-12', '12-18', '18-24']
GENERIC_UNAVAILABLE = 'a required accepted artifact is unavailable or failed verification; details are in the local server log only'
_DATE = {'type': 'string', 'pattern': '^[0-9]{4}-[0-9]{2}-[0-9]{2}$', 'description': 'local calendar date YYYY-MM-DD (Asia/Bangkok)'}
_SEG = {'type': 'string', 'minLength': 1, 'maxLength': 200, 'description': 'stable qualified DOH segment id (see GET /api/v1/segments)'}
_TB = {'type': 'string', 'enum': TIME_BLOCKS, 'description': 'required for unit 6h; omit for daily'}
_UNIT = {'type': 'string', 'enum': ['daily', '6h']}
AUTHORITY = ('Documentation of the accepted contract; the server validates only through the pinned notebook FUNCTIONS (24 strict JSON/exact fields, '
             '22/14/13 row rules). Unknown fields, duplicate keys, NaN/Infinity and bodies > 65536 bytes are refused.')

SCHEMAS = {
    'SpatialPredictionRequest': {
        'type': 'object', 'additionalProperties': False, 'required': ['unit', 'requests'], 'description': AUTHORITY,
        'properties': {'unit': _UNIT, 'requests': {'type': 'array', 'minItems': 1, 'maxItems': MAX_BATCH, 'items': {
            'type': 'object', 'additionalProperties': False, 'required': ['segment_id', 'target_date'],
            'properties': {'segment_id': _SEG, 'target_date': dict(_DATE, description='2024-01-01..2027-12-31; 2024-25 previously seen, later dates are research scenarios'),
                           'time_block': _TB}}}}},
    'SpatialHistoryRequest': {
        'type': 'object', 'additionalProperties': False, 'required': ['segment_id', 'target_date', 'unit'], 'description': AUTHORITY,
        'properties': {'segment_id': _SEG, 'target_date': dict(_DATE, description='2021-01-01..2027-12-31; history ends at the same issue/label cutoff as the prediction'),
                       'unit': _UNIT, 'time_block': _TB, 'lookback_days': {'type': 'integer', 'minimum': 1, 'maximum': 1827},
                       'categories': {'type': 'array', 'items': {'type': 'string'}}, 'top_k': {'type': 'integer', 'minimum': 1, 'maximum': 10}}},
    'ProvincePredictionRequest': {
        'type': 'object', 'additionalProperties': False, 'required': ['requests'], 'description': AUTHORITY + ' Preserved V2 province scope.',
        'properties': {'requests': {'type': 'array', 'minItems': 1, 'maxItems': MAX_BATCH, 'items': {
            'type': 'object', 'additionalProperties': False, 'required': ['province_key', 'target_date', 'unit'],
            'properties': {'province_key': {'type': 'string', 'description': 'Thai province name as in GET /api/v1/provinces'}, 'target_date': _DATE,
                           'unit': _UNIT, 'time_block': _TB}}}}},
}
HISTORY_QUERY = [
    {'name': 'province_key', 'in': 'query', 'required': True, 'schema': {'type': 'string'}, 'example': 'กรุงเทพมหานคร'},
    {'name': 'start_month', 'in': 'query', 'required': True, 'schema': {'type': 'string', 'pattern': '^[0-9]{4}-[0-9]{2}$'}, 'example': '2024-01'},
    {'name': 'end_month', 'in': 'query', 'required': True, 'schema': {'type': 'string', 'pattern': '^[0-9]{4}-[0-9]{2}$'}, 'example': '2024-12',
     'description': 'within 2021-01..2025-12 (accepted catalog); 2026 is refused, never an empty zero'},
    {'name': 'categories', 'in': 'query', 'required': False, 'schema': {'type': 'string'}, 'description': 'comma-separated recorded category names'},
    {'name': 'top_k', 'in': 'query', 'required': False, 'schema': {'type': 'integer', 'minimum': 1, 'maximum': 10}}]
SEGMENTS_QUERY = [
    {'name': 'bbox', 'in': 'query', 'required': True, 'schema': {'type': 'string'}, 'example': '97,5,106,21', 'description': 'west,south,east,north (lon/lat)'},
    {'name': 'limit', 'in': 'query', 'required': False, 'schema': {'type': 'integer', 'minimum': 1, 'maximum': 500}, 'example': 2},
    {'name': 'cursor', 'in': 'query', 'required': False, 'schema': {'type': 'string'}, 'description': 'next_cursor of the previous page'}]

# ---------- actual saved public values ----------
_MV = 'roadaware-spatial-v3-benchmark-issue-2023-12-31T18'
_SEL = 'hgb_poisson_fixed::routed_context'
_BASE = 'segment_mean_k365'
_QTY = 'expected SELECTED+LINKED recorded count per segment and horizon (lambda); not a probability'
_SEG64 = 'rsv1-rc31f3d87fc7:doh:64:p0:c0:r2000:00003'
_SEG1381 = 'rsv1-rc31f3d87fc7:doh:1381:p0:c0:r2000:00011'
_SEG1036 = 'rsv1-rc31f3d87fc7:doh:1036:p0:c0:r2000:00000'
_CAVEATS = [
    'Expected SELECTED+LINKED recorded-count rate per segment and horizon; not an individual accident probability, not per-vehicle risk; never sum into a route probability.',
    '2024/25 are PREVIOUSLY SEEN diagnostics; target dates after 2025-12-31 are research scenarios with no observed ground truth.',
    "Colour is relative to the 2022-23 OOF reference density of the selected policy; 'base' (lowest band) is NOT safe.",
    'Only the 3105 qualified DOH segments are supported; other roads are outside coverage (no snapping, no fake zero).',
    'Research readiness only: production_ready is false; nothing is deployed.']
_SRC_D = {'weather_daily_rain': 'not_in_weather_archive', 'weather_daily_temp': 'not_in_weather_archive', 'aadt': 'ok', 'bank_calendar': 'known',
          'bank_calendar_coverage': 'reviewed_annual_base_known_later_amendments_unknown'}
_ROW_DAILY = {'segment_id': _SEG64, 'target_date': '2025-12-16', 'time_block': None, 'unit': 'daily', 'horizon': 'local day 2025-12-16 (Asia/Bangkok)',
              'issue_time_local': '2025-12-15T18:00:00+07:00', 'issue_time_utc': '2025-12-15T11:00:00+00:00', 'model_version': _MV, 'method': _SEL,
              'role': 'selected_policy', 'component_used': 'core', 'routing_reason': 'core_fallback_missing_context:wx_rain_sum_mm_d2,wx_temp_mean_c_d2',
              'expected_recorded_count': 0.0013229405634793071, 'segment_km': 1.9999999999995528, 'density_per_km': 0.0006614702817398015, 'colour': 'base',
              'colour_hex': '#2c7fb8', 'colour_text': 'Lower relative predicted recorded density (below the median reference cell). NOT safe and NOT an accident probability.',
              'colour_status': 'relative_contract_relative_density_colour_v3.0', 'research_scenario': False, 'data_period': 'previously_seen_diagnostic_2024_2025',
              'coverage': 'supported_qualified_doh_segment', 'source_availability': _SRC_D}
_ROW_6H = {'segment_id': _SEG1381, 'target_date': '2025-10-04', 'time_block': '00-06', 'unit': '6h', 'horizon': '6 h block 00-06 of 2025-10-04 (Asia/Bangkok)',
           'issue_time_local': '2025-10-03T18:00:00+07:00', 'issue_time_utc': '2025-10-03T11:00:00+00:00', 'model_version': _MV, 'method': _SEL,
           'role': 'selected_policy', 'component_used': 'core',
           'routing_reason': 'core_fallback_missing_context:wx_rain_sum_mm_d2,wx_temp_mean_c_d2,wx_block_rain_sum_mm_d2,wx_block_temp_mean_c_d2',
           'expected_recorded_count': 0.0007776128214300119, 'segment_km': 2.0000000000001776, 'density_per_km': 0.0003888064107149714, 'colour': 'yellow',
           'colour_hex': '#f2c418', 'colour_text': 'Above-median relative predicted recorded density (50th-80th percentile of reference cells).',
           'colour_status': 'relative_contract_relative_density_colour_v3.0', 'research_scenario': False, 'data_period': 'previously_seen_diagnostic_2024_2025',
           'coverage': 'supported_qualified_doh_segment',
           'source_availability': dict(_SRC_D, weather_block_rain='not_in_weather_archive', weather_block_temp='not_in_weather_archive')}
_ROW_BASE = dict(_ROW_DAILY, method=_BASE, role='strong_baseline_comparison', component_used='baseline', routing_reason='baseline_has_no_routing',
                 expected_recorded_count=0.0039009961655522797, density_per_km=0.001950498082776576, colour=None, colour_hex=None, colour_text=None,
                 colour_status='not_applicable_for_baseline')


def _pred(unit, method, row):
    return {'ok': True, 'api_version': API_VERSION, 'production_ready': False, 'unit': unit, 'rows': 1, 'model_version': _MV, 'method': method,
            'quantity': _QTY, 'results': [row], 'caveats': _CAVEATS}


def _err(code, family, message=None, **extra):
    e = {'code': code, 'family': family}
    if message is not None:
        e['message'] = message
    e.update(extra)
    return {'ok': False, 'api_version': API_VERSION, 'production_ready': False, 'error': e}


_GEOM_NOTES = ['current qualified DOH 2000 m segment snapshot (EPSG:4326 lon/lat, RFC 7946 order) applied retrospectively; NOT a routing graph and NOT the '
               'true historical road network of earlier years',
               'roads outside the 3105 qualified DOH segments are unsupported: render them grey / "no data"; the API never returns a prediction, a zero or a '
               'lambda of 0 for them and never snaps a location to a segment']
_SNAPSHOT = ('accepted notebook-19 universe (3105 qualified DOH 2000 m segments), manifest sha256 '
             '8a53b10cd88283e2b8a5c8c7d4f15f9657bf68f6fb9e58076fed2938176e1d73')
_F0 = {'type': 'Feature', 'id': _SEG1036, 'geometry': {'type': 'LineString', 'coordinates': [[100.59975975300006, 13.985689456000047],
                                                                                            [100.59975959600007, 13.985689429000045]]},
       'properties': {'segment_id': _SEG1036, 'route_code': '0346', 'segment_km': 1.9999999999994045, 'province_code': 13,
                      'coverage': 'supported_qualified_doh_segment'}}
_NONZERO_MONTHS = {'2021-05': 1, '2021-10': 1, '2022-02': 1, '2022-05': 1, '2022-11': 1}


def _cat(n_distinct, top):
    return {'denominator_records': 5, 'known_records': 5, 'unknown_records': 0, 'known_share': 1.0, 'distinct_known_values': n_distinct,
            'top_values': [{'value': v, 'records': r} for v, r in top], 'other_known_records': 0}


_HISTORY = {
    'schema': 'roadaware-spatial-history/1', 'catalog_id': 'df65865c4182c314', 'kind': 'spatial_selected_history_as_of', 'segment_id': _SEG64,
    'target_date': '2024-03-01', 'unit': 'daily', 'time_block': None, 'timezone': 'Asia/Bangkok', 'issue_time_local': '2024-02-29T18:00:00+07:00',
    'history_cutoff_local': '2024-01-30T18:00:00+07:00', 'latency_days': 30, 'eligibility': 'target day end <= cutoff',
    'history_window': {'lookback_days': 1827, 'window_start_local_exclusive': '2019-01-29T18:00:00+07:00', 'window_end_local_inclusive': '2024-01-30T18:00:00+07:00',
                       'catalog_data_start_local': '2021-01-01T00:00:00+07:00', 'catalog_data_end_local_exclusive': '2026-01-01T00:00:00+07:00',
                       'covered_days': 1124.75, 'window_fully_inside_catalog_data': False},
    'n_selected_records': 5, 'empty_history_is_not_safety': True, 'counts_by_year': {'2021': 2, '2022': 3},
    'counts_by_month': [{'year_month': '%d-%02d' % (y, m), 'records': _NONZERO_MONTHS.get('%d-%02d' % (y, m), 0)}
                        for y in range(2021, 2025) for m in range(1, 13) if (y, m) <= (2024, 1)],
    'counts_by_time_block': {'00-06': 1, '06-12': 0, '12-18': 2, '18-24': 2},
    'categories': {'accident_type': _cat(4, [('ชนในทิศทางตรงกันข้าม (ไม่ใช่การแซง)', 2), ('ชนสิ่งกีดขวาง (บนผิวจราจร)', 1), ('พลิกคว่ำ/ตกถนนในทางตรง', 1),
                                             ('พลิกคว่ำ/ตกถนนในทางโค้ง', 1)]),
                   'presumed_cause': _cat(1, [('ขับรถเร็วเกินอัตรากำหนด', 5)]), 'weather': _cat(1, [('แจ่มใส', 5)]),
                   'time_block': _cat(3, [('12-18', 2), ('18-24', 2), ('00-06', 1)])},
    'research_status': {'research_only': True, 'production_ready': False, 'operational_status': 'BLOCKED', 'live_data': False, 'forecast': False}}
_PROVINCE_REQ = {'province_key': 'กรุงเทพมหานคร', 'target_date': '2024-05-01', 'unit': 'daily'}
_PROVINCE_RESULT = {
    'index': 0, 'request': dict(_PROVINCE_REQ, time_block=None), 'province_key': 'กรุงเทพมหานคร', 'alias_applied': False, 'target_date': '2024-05-01',
    'unit': 'daily', 'time_block': None,
    'cell': {'issue_time_local': '2024-04-30T18:00:00+07:00', 'target_start_local': '2024-05-01T00:00:00+07:00', 'target_end_local': '2024-05-02T00:00:00+07:00',
             'timezone': 'Asia/Bangkok', 'utc_offset': '+07:00'},
    'prediction': {'expected_recorded_count': 5.069141036330536, 'method_id': 'hgb_poisson__full', 'family': 'hgb', 'variant': 'full',
                   'bundle_sha256': '1b7e794d6278cd6ca298cde93defae889723d1bc58e3b4f45fe51859ff46dc8c', 'registry_id': '2f8a1e2e910fcd01'},
    'baseline_comparator': {'expected_recorded_count': 3.704637497022155, 'method_id': 'baseline_province_month_k30',
                            'sha256': '73b233d4a1fa0eb66a5523ab2404074fb938b7053689c53b48e296a4959c7291'},
    'model_age': {'training_cutoff_local': '2023-12-31T18:00:00+07:00', 'days_from_training_cutoff_to_target': 122},
    'limitations': ['research_only_not_operational', 'no_untouched_test', 'within_evaluated_period_previously_seen_diagnostic', 'weather_covariates_missing',
                    'traffic_vintage_stale']}
_FLOOR0 = {'metric_floor_cells': 0, 'metric_floor_actual_positive_cells': 0, 'metric_floor_actual_records': 0.0, 'metric_floor_deviance_sum': 0.0}


def _metric(scope, role, method, n, dev, mae, rmse, bias, wape, tp, ta, poa, zero, nonzero, expo, obs, pred, floor):
    return dict({'unit': 'daily', 'scope': scope, 'role': role, 'method': method, 'dimension': 'pooled', 'group': 'all', 'n': n, 'mean_poisson_deviance': dev,
                 'mae': mae, 'rmse': rmse, 'bias': bias, 'wape': wape, 'wape_status': 'ok', 'total_pred': tp, 'total_actual': ta, 'pred_over_actual': poa,
                 'zero_cells': zero, 'nonzero_cells': nonzero, 'exposure_segment_km_periods': expo, 'observed_records_per_km_period': obs,
                 'predicted_records_per_km_period': pred}, **floor)


# accepted 21 metrics_by_group.csv rows (daily pooled: oof selected, oof baseline, seen-2024/25 diag selected)
_METRICS = [
    _metric('oof', 'selected', _SEL, 2266650, 0.039898070402242164, 0.008661958157075265, 0.07149566939885867, -0.0004971662011703773, 1.8347469822198532,
            9574.098230117164, 10701.0, 0.8946919194577296, 2256534, 10116, 4307170.314688374, 0.002484461773779248, 0.002222827873201911, _FLOOR0),
    _metric('oof', 'baseline', _BASE, 2266650, 0.040956040048540386, 0.008600932535442429, 0.07151650598946219, -0.0005948456649504975, 1.821820739319744,
            9352.693073539955, 10701.0, 0.8740017824072475, 2256534, 10116, 4307170.314688374, 0.002484461773779248, 0.002171424018605734,
            {'metric_floor_cells': 168780, 'metric_floor_actual_positive_cells': 48, 'metric_floor_actual_records': 48.0,
             'metric_floor_deviance_sum': 2556.5780274710555}),
    _metric('diag', 'selected', _SEL, 2269755, 0.044860353989922774, 0.009614605902971432, 0.07588268571623318, -0.0007915171431695133, 1.7820349355952083,
            10449.450006705281, 12246.0, 0.8532949540017378, 2258139, 11616, 4313070.547996165, 0.0028392765348318823, 0.0024227403401875847, _FLOOR0)]
_ALL_AVAILABLE = {c: {'status': 'available', 'code': None} for c in ('notebook24', 'spatial_runtime', 'province_runtime', 'catalog', 'geometry', 'evaluation',
                                                                       'diagnostics_2026')}

# name -> example. 'request' (method, path, query|body) is re-asked live by the smoke; 'response' is a subset of the actual answer.
EXAMPLES = {
    'health_ok': {'route': ('get', '/health'), 'status': 200, 'source': 'transport liveness', 'request': {'method': 'GET', 'path': '/health'},
                  'response': {'status': 'alive', 'api_version': API_VERSION, 'production_ready': False}},
    'ready_ok': {'route': ('get', '/ready'), 'status': 200, 'source': 'live 001 sample_responses.json', 'request': {'method': 'GET', 'path': '/ready'},
                 'response': {'ok': True, 'api_version': API_VERSION, 'research_backend_ready': True, 'production_ready': False, 'components': _ALL_AVAILABLE}},
    'ready_unavailable': {'route': ('get', '/ready'), 'status': 503, 'source': 'labelled smoke FIXTURE lock with a deliberately wrong pinned hash (not a production config)',
                          'response': {'ok': False, 'api_version': API_VERSION, 'research_backend_ready': False, 'production_ready': False,
                                       'components': {'notebook24': {'status': 'unavailable', 'code': 'artifact_hash_mismatch'}}}},
    'evaluation_ok': {'route': ('get', '/api/v1/evaluation'), 'status': 200, 'source': 'accepted 21 metrics_by_group.csv rows (trimmed: 3 of the pooled/period rows) + accepted 23 counts',
                      'request': {'method': 'GET', 'path': '/api/v1/evaluation'},
                      'response': {'ok': True, 'production_ready': False, 'spatial_evaluation_21': {
                          'status': 'accepted_spatial_evaluation_research_only', 'selected': {u: {'selected': _SEL, 'baseline': _BASE} for u in ('daily', '6h')},
                          'metrics': _METRICS},
                          'diagnostics_2026': {'status': 'available_diagnostic_aggregates_only',
                                               'counts': {'eligible_raw_records': 4336, 'positive_cells': {'daily': 4116, '6h': 4232}}}}},
    'province_history_ok': {'route': ('get', '/api/v1/history'), 'status': 200, 'source': 'hash-verified accepted 14 province_monthly.csv (2024 rows of this province)',
                            'request': {'method': 'GET', 'path': '/api/v1/history', 'query': {'province_key': 'กรุงเทพมหานคร', 'start_month': '2024-01', 'end_month': '2024-12'}},
                            'response': {'ok': True, 'production_ready': False, 'history': {'total_records': 2682, 'zero_months': 0}}},
    'province_history_2026': {'route': ('get', '/api/v1/history'), 'status': 400, 'source': 'notebook-24 catalog_query_error (2026 not in the accepted catalog)',
                              'request': {'method': 'GET', 'path': '/api/v1/history', 'query': {'province_key': 'กรุงเทพมหานคร', 'start_month': '2026-01', 'end_month': '2026-03'}},
                              'response': _err('invalid_request', 'invalid', 'history request rejected by the accepted catalog contract')},
    'segments_page': {'route': ('get', '/api/v1/segments'), 'status': 200, 'source': 'live 001 sample_responses.json (coordinates TRIMMED to 2 points)',
                      'request': {'method': 'GET', 'path': '/api/v1/segments', 'query': {'bbox': '97,5,106,21', 'limit': '2'}},
                      'response': {'ok': True, 'production_ready': False, 'type': 'FeatureCollection', 'bbox': [97.0, 5.0, 106.0, 21.0], 'features': [_F0],
                                   'page': {'limit': 2, 'cursor': '0', 'next_cursor': '2', 'returned': 2, 'total_matched': 3105,
                                            'order': 'segment_id ascending (stable for this geometry snapshot)'},
                                   'coordinate_reference': 'EPSG:4326 longitude, latitude (RFC 7946)', 'geometry_snapshot': _SNAPSHOT, 'notes': _GEOM_NOTES}},
    'segment_ok': {'route': ('get', '/api/v1/segments/{segment_id}'), 'status': 200, 'source': 'live 001 sample_responses.json (coordinates TRIMMED to 2 points)',
                   'request': {'method': 'GET', 'path': '/api/v1/segments/' + _SEG1036},
                   'response': {'ok': True, 'production_ready': False, 'feature': _F0, 'geometry_snapshot': _SNAPSHOT}},
    'segment_unknown': {'route': ('get', '/api/v1/segments/{segment_id}'), 'status': 404, 'source': 'notebook-24 get_segment',
                        'request': {'method': 'GET', 'path': '/api/v1/segments/not-a-doh-segment'},
                        'response': _err('unknown_segment', 'coverage', 'segment outside the qualified DOH universe: unsupported (grey), never zero')},
    'spatial_history_ok': {'route': ('post', '/api/v1/spatial/history'), 'status': 200, 'source': 'live 001 sample_responses.json',
                           'request': {'method': 'POST', 'path': '/api/v1/spatial/history', 'body': {'segment_id': _SEG64, 'target_date': '2024-03-01', 'unit': 'daily'}},
                           'response': {'ok': True, 'production_ready': False, 'history': _HISTORY, 'catalog_period': {'first_month': '2021-01', 'last_month': '2025-12'},
                                        'period_status': {'status': 'partially_unsupported_period', 'unsupported_after': None,
                                                          'unsupported_before': {'from_local_exclusive': '2019-01-29T18:00:00+07:00', 'to_local': '2021-01-01T00:00:00+07:00'}}}},
    'spatial_daily': {'route': ('post', '/api/v1/spatial/predictions'), 'status': 200, 'source': 'accepted 22 prediction_fixtures.json daily selected row 0',
                      'request': {'method': 'POST', 'path': '/api/v1/spatial/predictions', 'body': {'unit': 'daily', 'requests': [{'segment_id': _SEG64, 'target_date': '2025-12-16'}]}},
                      'response': _pred('daily', _SEL, _ROW_DAILY)},
    'spatial_6h': {'route': ('post', '/api/v1/spatial/predictions'), 'status': 200, 'source': 'accepted 22 prediction_fixtures.json 6h selected row 0',
                   'request': {'method': 'POST', 'path': '/api/v1/spatial/predictions',
                               'body': {'unit': '6h', 'requests': [{'segment_id': _SEG1381, 'target_date': '2025-10-04', 'time_block': '00-06'}]}},
                   'response': _pred('6h', _SEL, _ROW_6H)},
    'spatial_date_before_asof': {'route': ('post', '/api/v1/spatial/predictions'), 'status': 400, 'source': 'live 001 sample_responses.json error_example',
                                 'request': {'method': 'POST', 'path': '/api/v1/spatial/predictions', 'body': {'unit': 'daily', 'requests': [{'segment_id': _SEG64, 'target_date': '2023-06-01'}]}},
                                 'response': _err('date_before_artifact_asof', 'invalid', 'the benchmark artifact was fitted as of 2023-12-31 18:00:00 (labels to 2023-12-01 '
                                                  '18:00:00); earlier targets would be a false prospective forecast. Supported 2024-01-01..2027-12-31', rows=[0])},
    'spatial_unknown_segment': {'route': ('post', '/api/v1/spatial/predictions'), 'status': 404, 'source': 'notebook-22 coverage error (offending rows only)',
                                'request': {'method': 'POST', 'path': '/api/v1/spatial/predictions', 'body': {'unit': 'daily', 'requests': [{'segment_id': 'not-a-doh-segment', 'target_date': '2024-03-01'}]}},
                                'response': _err('unknown_segment', 'coverage', rows=[0])},
    'spatial_baseline_daily': {'route': ('post', '/api/v1/spatial/baseline-predictions'), 'status': 200, 'source': 'accepted 22 prediction_fixtures.json daily baseline row 0',
                               'request': {'method': 'POST', 'path': '/api/v1/spatial/baseline-predictions', 'body': {'unit': 'daily', 'requests': [{'segment_id': _SEG64, 'target_date': '2025-12-16'}]}},
                               'response': _pred('daily', _BASE, _ROW_BASE)},
    'province_v2_ok': {'route': ('post', '/api/v1/predictions'), 'status': 200, 'source': 'saved notebook-13 serving_examples.json result 0 (seconds omitted)',
                       'request': {'method': 'POST', 'path': '/api/v1/predictions', 'body': {'requests': [_PROVINCE_REQ]}},
                       'response': {'ok': True, 'production_ready': False, 'province_prediction_v2': {
                           'schema': 'roadaware-v2-research-prediction/1', 'registry_id': '2f8a1e2e910fcd01', 'research_only': True, 'production_ready': False,
                           'operational_status': 'BLOCKED', 'n_results': 1, 'results': [_PROVINCE_RESULT]}}},
    'province_v2_fields': {'route': ('post', '/api/v1/predictions'), 'status': 400, 'source': 'notebook-24 exact_object',
                           'request': {'method': 'POST', 'path': '/api/v1/predictions', 'body': {'requests': [_PROVINCE_REQ], 'model': 'x'}},
                           'response': _err('invalid_fields', 'invalid', "province prediction body fields must be exactly ['requests']")},
    'unavailable_not_ready': {'route': None, 'status': 503, 'source': 'labelled smoke FIXTURE lock (any data route while the runtime is not ready)',
                              'response': _err('backend_not_ready', 'unavailable', GENERIC_UNAVAILABLE)},
    'unavailable_component': {'route': None, 'status': 503, 'source': 'runtime component unavailable (e.g. optional V2 province service)',
                              'response': _err('component_unavailable', 'unavailable', GENERIC_UNAVAILABLE)},
    'body_too_large': {'route': None, 'status': 413, 'source': 'transport', 'response': _err('body_too_large', 'too_large', 'request body exceeds 65536 bytes')},
    'media_type': {'route': None, 'status': 415, 'source': 'transport', 'response': _err('unsupported_media_type', 'media_type', 'Content-Type must be application/json')},
}
REQUEST_EXAMPLES = {'/api/v1/spatial/predictions': ('SpatialPredictionRequest', ['spatial_daily', 'spatial_6h', 'spatial_date_before_asof']),
                    '/api/v1/spatial/baseline-predictions': ('SpatialPredictionRequest', ['spatial_baseline_daily']),
                    '/api/v1/spatial/history': ('SpatialHistoryRequest', ['spatial_history_ok']),
                    '/api/v1/predictions': ('ProvincePredictionRequest', ['province_v2_ok'])}
_SHARED = {400: (), 404: (), 413: ('body_too_large',), 415: ('media_type',), 503: ('unavailable_not_ready', 'unavailable_component')}
_DESC = {200: 'success (production_ready is always false)', 400: 'invalid request (stable code, offending rows; no input echo)',
         404: 'unknown/unsupported identifier: coverage, never a zero', 413: 'body larger than 65536 bytes', 415: 'Content-Type must be application/json',
         503: 'component unavailable or backend not ready (fail closed; details only in the local server log)'}


def responses(method, path, *codes):
    """FastAPI `responses=` for one route: actual examples of this route + shared transport/unavailable examples."""
    out = {}
    for c in (200,) + tuple(codes):
        names = [n for n, e in EXAMPLES.items() if e['route'] == (method, path) and e['status'] == c] + list(_SHARED.get(c, ()))
        ex = {n: {'summary': EXAMPLES[n]['source'], 'value': EXAMPLES[n]['response']} for n in names}
        out[c] = {'description': _DESC[c], 'content': {'application/json': {'examples': ex}}} if ex else {'description': _DESC[c]}
    return out


def request_body(path):
    """FastAPI `openapi_extra=` for one POST route: required JSON body with the bounded schema and the actual request examples."""
    name, ex = REQUEST_EXAMPLES[path]
    return {'requestBody': {'required': True, 'description': AUTHORITY, 'content': {'application/json': {
        'schema': SCHEMAS[name], 'examples': {n: {'summary': EXAMPLES[n]['source'], 'value': EXAMPLES[n]['request']['body']} for n in ex}}}}}


def query_params(path):
    return {'parameters': HISTORY_QUERY if path == '/api/v1/history' else SEGMENTS_QUERY}


def matches(example, live, tol=1e-12, ignore=('seconds',)):
    """True iff `example` is a subset of `live`: dict keys present and matching, list elements each matching some live element (trimmed lists allowed),
    numbers equal within a relative/absolute 1e-12 (bool is not a number), everything else equal."""
    if isinstance(example, dict):
        return isinstance(live, dict) and all(k in ignore or (k in live and matches(v, live[k], tol, ignore)) for k, v in example.items())
    if isinstance(example, list):
        return isinstance(live, list) and all(any(matches(x, y, tol, ignore) for y in live) for x in example)
    if isinstance(example, bool) or isinstance(live, bool):
        return example is live
    if isinstance(example, (int, float)) and isinstance(live, (int, float)):
        return math.isclose(example, live, rel_tol=tol, abs_tol=tol)
    return example == live
