#!/usr/bin/env python3
"""Campo e Clima: initial Open-Meteo acquisition, equal-model ensemble blend.

No assertions of calibration or real-time alerts. HTTP requests occur only when run.
"""
from __future__ import annotations
import datetime as dt
import json
import os
import pathlib
import math
import time
from typing import Any
import requests

LAT, LON = -23.065, -54.190
TZ = 'America/Campo_Grande'
MODELS = {
    'ECMWF IFS': 'ecmwf_ifs025_ensemble',
    'ECMWF AIFS': 'ecmwf_aifs025_ensemble',
    'NOAA GEFS': 'ncep_gefs_seamless',
    'NOAA AI-GEFS': 'ncep_aigefs025',
    'DWD ICON': 'dwd_icon_seamless_eps',
    'GEM Canada': 'gem_global_ensemble',
    'UKMO': 'ukmo_global_ensemble_20km',
    'Google WeatherNext2': 'google_weathernext2_ensemble',
}
FORECAST_URL = 'https://api.open-meteo.com/v1/forecast'
ENSEMBLE_URL = 'https://ensemble-api.open-meteo.com/v1/ensemble'
TIMEOUT = 35


def fetch(url: str, params: dict[str, Any]) -> dict:
    response = requests.get(url, params=params, timeout=TIMEOUT, headers={'User-Agent': 'Campo-e-Clima-research/0.1'})
    response.raise_for_status()
    payload = response.json()
    if payload.get('error'):
        raise ValueError(str(payload.get('reason', 'API error')))
    if payload.get('utc_offset_seconds') != -14400:
        raise ValueError('Expected America/Campo_Grande = UTC-4; inspect API timezone before ingesting')
    return payload


def base_params():
    return {'latitude': LAT, 'longitude': LON, 'timezone': TZ, 'forecast_days': 7}


def forecast() -> dict:
    params = {**base_params(), 'forecast_days': 14,
              'hourly': ','.join(['temperature_2m','relative_humidity_2m','dew_point_2m','vapour_pressure_deficit',
                                  'precipitation','precipitation_probability','wind_speed_10m',
                                  'wind_direction_10m','wind_gusts_10m','pressure_msl','cloud_cover']),
              'daily': ','.join(['temperature_2m_max','temperature_2m_min','precipitation_sum',
                                  'precipitation_probability_max','wind_gusts_10m_max']),
              'current': ','.join(['temperature_2m','relative_humidity_2m','precipitation','wind_speed_10m','wind_direction_10m'])}
    return fetch(FORECAST_URL, params)


def get_members(payload: dict, base: str) -> list[list[float | None]]:
    """Return member series matching API field prefix; handles 'precipitation_memberNN'.

    The API might also return a non-member control field. It is not assumed to
    be a valid member unless a member-specific key exists.
    """
    hourly = payload.get('hourly', {})
    members = []
    for k, v in hourly.items():
        if k.startswith(base + '_member') and isinstance(v, list):
            members.append(v)
    # Some models may publish 'precipitation' as control when indexed members exist.
    return members


def model_daily_rain(payload: dict) -> dict[str, Any]:
    hourly = payload.get('hourly', {})
    times = hourly.get('time', [])
    raw = get_members(payload, 'precipitation')
    if not raw:
        return {'member_count': 0, 'days': {}}
    by_date: dict[str, list[int]] = {}
    for i, t in enumerate(times):
        by_date.setdefault(t[:10], []).append(i)
    out = {}
    for day, ids in list(by_date.items())[:7]:
        if len(ids) != 24:
            continue   # no daily sum for partial dates / unequal resolution
        sums = []
        for series in raw:
            if len(series) != len(times):
                continue
            values = [series[i] for i in ids]
            if any(x is None or not isinstance(x, (int, float)) or not math.isfinite(x) or x < 0 for x in values):
                continue
            sums.append(sum(float(x) for x in values))
        out[day] = sums
    return {'member_count': len(raw), 'days': out}


def model_daily_gust(payload: dict) -> dict[str, Any]:
    """Maximum 10-m gust in each local day per complete valid member.

    Gust speed is never summed. A missing sample invalidates its member/day.
    """
    hourly = payload.get('hourly', {})
    times = hourly.get('time', [])
    raw = get_members(payload, 'wind_gusts_10m')
    by_date: dict[str, list[int]] = {}
    for i, t in enumerate(times):
        by_date.setdefault(t[:10], []).append(i)
    out = {}
    for day, ids in list(by_date.items())[:7]:
        if len(ids) != 24:
            continue
        maximums = []
        for series in raw:
            if len(series) != len(times):
                continue
            values = [series[i] for i in ids]
            if any(x is None or not isinstance(x, (int, float)) or not math.isfinite(x) or x < 0 for x in values):
                continue
            maximums.append(max(float(x) for x in values))
        out[day] = maximums
    return {'member_count': len(raw), 'days': out}


def mix_gust_days(by_model: dict[str, dict]) -> list[dict]:
    """Daily max-gust distribution, equal total weight for each available model."""
    dates = sorted({day for item in by_model.values() for day in item.get('days', {})})
    result = []
    for day in dates:
        valid = {name: item['days'][day] for name, item in by_model.items()
                 if item.get('days', {}).get(day)}
        if not valid:
            continue
        wm = 1 / len(valid)
        pairs = [(x, wm / len(values)) for values in valid.values() for x in values]
        out = {'date': day, 'model_count': len(valid),
               'member_count': sum(len(values) for values in valid.values()),
               'mean_kmh': round(sum(x*w for x,w in pairs), 2),
               'p10_kmh': round(weighted_quantile(pairs, .1), 2),
               'p50_kmh': round(weighted_quantile(pairs, .5), 2),
               'p90_kmh': round(weighted_quantile(pairs, .9), 2)}
        for threshold in (30, 40, 60, 80):
            out[f'p_gt_{threshold}_kmh'] = round(sum(w for x,w in pairs if x > threshold), 4)
        result.append(out)
    return result


def weighted_quantile(values_and_weights: list[tuple[float, float]], q: float) -> float | None:
    """Weighted inverse empirical CDF: smallest x with F(x) >= q."""
    if not values_and_weights:
        return None
    ordered = sorted(values_and_weights)
    total = sum(w for _, w in ordered)
    if total <= 0:
        return None
    acc = 0.0
    for x, w in ordered:
        acc += w
        if acc / total >= q - 1e-12:
            return x
    return ordered[-1][0]


def mix_days(by_model: dict[str, dict]) -> list[dict]:
    dates = sorted({d for x in by_model.values() for d in x.get('days', {})})
    result = []
    for day in dates:
        valid = {name: model['days'][day] for name, model in by_model.items()
                 if model.get('days', {}).get(day)}
        if not valid:
            continue
        weight = 1 / len(valid)
        pairs = [(value, weight / len(member_values))
                 for member_values in valid.values() for value in member_values]
        rain = {
            'date': day,
            'model_count': len(valid),
            'member_count': sum(len(x) for x in valid.values()),
            'mean_mm': round(sum(x * w for x, w in pairs), 3),
            'p10_mm': round(weighted_quantile(pairs, .1), 3),
            'p50_mm': round(weighted_quantile(pairs, .5), 3),
            'p90_mm': round(weighted_quantile(pairs, .9), 3),
        }
        for threshold in [0.1, 1, 3, 5, 10, 20, 30, 50]:
            rain['p_gt_' + str(threshold).replace('.', '_') + '_mm'] = round(
                sum(w for x, w in pairs if x > threshold), 4)
        result.append(rain)
    return result


def main():
    recorded = dt.datetime.now(dt.timezone.utc).isoformat()
    result: dict[str, Any] = {'schema_version': 1, 'issued_at_utc': recorded,
             'site': {'latitude': LAT, 'longitude': LON, 'timezone': TZ},
             'methodology': 'Equal total weight per valid ensemble model; uncalibrated member frequencies',
             'sources': {}, 'deterministic': None, 'rain_ensemble_daily': [], 'gust_ensemble_daily': [], 'ensemble_models': {},
             'warnings': []}
    try:
        f = forecast()
        result['deterministic'] = {
            'hourly': f.get('hourly'), 'daily': f.get('daily'), 'current': f.get('current'),
            'latitude': f.get('latitude'), 'longitude': f.get('longitude'),
            'elevation': f.get('elevation'), 'utc_offset_seconds': f.get('utc_offset_seconds'),
            'model_used': 'Open-Meteo Forecast auto (not an extra ensemble member)', 'collected_at_utc': recorded}
        result['sources']['Open-Meteo Forecast'] = {'state': 'ok', 'collected_at_utc': recorded}
    except Exception as exc:
        result['sources']['Open-Meteo Forecast'] = {'state':'error', 'detail': str(exc)[:250]}
        result['warnings'].append('Forecast unavailable; no replacement with old data')

    by_model = {}
    by_model_gust = {}
    for name, code in MODELS.items():
        try:
            params = {**base_params(), 'models': code, 'hourly': 'precipitation,wind_gusts_10m'}
            try:
                e = fetch(ENSEMBLE_URL, params)
                gust_request_error = None
            except (ValueError, requests.HTTPError) as exc:
                # Some ensembles do not expose gusts; rain must still be collected.
                gust_request_error = str(exc)[:180]
                e = fetch(ENSEMBLE_URL, {**base_params(), 'models': code, 'hourly': 'precipitation'})
            d = model_daily_rain(e)
            g = model_daily_gust(e)
            result['ensemble_models'][name] = {
                'code': code, 'precipitation_members': d['member_count'],
                'gust_members': g['member_count'],
                'grid_lat': e.get('latitude'), 'grid_lon': e.get('longitude'),
                'collected_at_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
                'gust_request_error': gust_request_error,
                'state': 'ok' if d['days'] else 'no_valid_daily_rain_members'}
            if d['days']:
                by_model[name] = d
            if any(g['days'].values()):
                by_model_gust[name] = g
        except Exception as exc:
            result['ensemble_models'][name] = {'code': code, 'state': 'error', 'detail': str(exc)[:220]}
        time.sleep(.2)
    result['rain_ensemble_daily'] = mix_days(by_model)
    result['gust_ensemble_daily'] = mix_gust_days(by_model_gust)
    if not result['rain_ensemble_daily']:
        result['warnings'].append('No complete member/day precipitation sample; ensemble chart unavailable')
    if not result['gust_ensemble_daily']:
        result['warnings'].append('No complete member/day gust sample; gust exceedance probabilities unavailable')

    dest = pathlib.Path(os.environ.get('OUTPUT_JSON', 'site/data/latest.json'))
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(result, ensure_ascii=False, separators=(',',':')), encoding='utf-8')
    print('Wrote', dest, '; deterministic:', bool(result['deterministic']), '; ensemble models:', len(by_model))
    if not result['deterministic'] and not by_model:
        raise SystemExit('No fresh weather values available: not publishing a misleading successful update')

if __name__ == '__main__':
    main()
