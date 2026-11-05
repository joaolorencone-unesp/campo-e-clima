"""Multi-model deterministic comparison: combined request, per-model fallback on HTTP 400, spread."""
import requests
import scripts.collect as collector


def payload(models, days=3):
    daily = {'time': [f'2026-11-0{d}' for d in range(5, 5 + days)]}
    hourly = {'time': [f'2026-11-05T{h:02d}:00' for h in range(24)]}
    for i, m in enumerate(models):
        suffix = f'_{m}' if len(models) > 1 else ''
        daily[f'precipitation_sum{suffix}'] = [2.0 * (i + 1)] * days
        daily[f'temperature_2m_max{suffix}'] = [30 + i] * days
        daily[f'temperature_2m_min{suffix}'] = [18 + i] * days
        daily[f'wind_gusts_10m_max{suffix}'] = [40] * days
        daily[f'weather_code{suffix}'] = [61] * days
        hourly[f'precipitation{suffix}'] = [0.1] * 24
        hourly[f'temperature_2m{suffix}'] = [24] * 24
    return {'latitude': -23.1, 'longitude': -54.2, 'utc_offset_seconds': -14400, 'daily': daily, 'hourly': hourly}


def http_error(status):
    response = requests.Response(); response.status_code = status
    return requests.HTTPError(f'HTTP {status}', response=response)


def test_combined_request_gives_per_model_blocks_and_spread():
    ids = ['ecmwf_ifs025', 'gfs_global', 'icon_seamless']
    calls = []
    def fetcher(url, params):
        calls.append(params['models']); return payload(ids)
    out = collector.forecast_models(fetcher=fetcher, model_ids=ids)
    assert calls == ['ecmwf_ifs025,gfs_global,icon_seamless'] and out['state'] == 'ok' and out['models_ok'] == sorted(ids)
    day = out['spread_daily'][0]
    assert day['models'] == 3 and day['rain_min_mm'] == 2.0 and day['rain_median_mm'] == 4.0 and day['rain_max_mm'] == 6.0
    assert day['models_wet_1mm'] == 3 and day['models_wet_10mm'] == 0 and day['tmax_min'] == 30 and day['tmax_max'] == 32
    assert out['models']['gfs_global']['hourly']['precipitation'] == [0.1] * 24


def test_invalid_id_falls_back_to_individual_requests_and_isolates_it():
    ids = ['ecmwf_ifs025', 'modelo_invalido']
    def fetcher(url, params):
        if ',' in params['models'] or params['models'] == 'modelo_invalido':
            raise http_error(400)
        return payload([params['models']])
    out = collector.forecast_models(fetcher=fetcher, model_ids=ids)
    assert out['state'] == 'ok' and out['fallback'].startswith('pedido combinado rejeitado')
    assert out['models']['ecmwf_ifs025']['state'] == 'ok' and out['models']['modelo_invalido'] == {'state': 'unavailable', 'label': 'modelo_invalido', 'error': 'HTTP 400'}
    assert out['spread_daily'][0]['models'] == 1


def test_rate_limit_and_transport_errors_do_not_raise():
    out = collector.forecast_models(fetcher=lambda u, p: (_ for _ in ()).throw(http_error(429)), model_ids=['a'])
    assert out['state'] == 'unavailable' and '429' in out['error'] and out['spread_daily'] == []
    out = collector.forecast_models(fetcher=lambda u, p: (_ for _ in ()).throw(requests.Timeout('t')), model_ids=['a'])
    assert out['state'] == 'unavailable' and out['error'].startswith('Timeout')


def test_plain_payload_without_model_fields_is_reported_not_crashed():
    out = collector.forecast_models(fetcher=lambda u, p: {'daily': {'time': ['2026-11-05'], 'precipitation_sum': [1.0]}}, model_ids=['a', 'b'])
    assert out['state'] == 'unavailable' and all(b['state'] == 'unavailable' for b in out['models'].values())


def test_ragged_series_and_rate_limited_fallback_keep_every_model_listed():
    ragged = payload(['a', 'b'])
    ragged['daily']['precipitation_sum_a'] = [1.0]  # shorter than daily.time
    out = collector.forecast_models(fetcher=lambda u, p: ragged, model_ids=['a', 'b'])
    assert out['state'] == 'ok' and out['spread_daily'][0]['models'] == 2 and out['spread_daily'][2]['models'] == 1
    calls = []
    def fetcher(url, params):
        calls.append(params['models'])
        if ',' in params['models']:
            raise http_error(400)
        raise http_error(429) if params['models'] == 'a' else http_error(400)
    out = collector.forecast_models(fetcher=fetcher, model_ids=['a', 'b', 'c'])
    assert set(out['models']) == {'a', 'b', 'c'} and out['models']['b']['error'] == 'não consultado após HTTP 429' and calls == ['a,b,c', 'a']
