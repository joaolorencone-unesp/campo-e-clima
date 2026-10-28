"""Daily rolling gridded history for Naviraí, independently sourced.

ERA5 and NASA POWER are gridded products, not independent station observations.
Does not invent rain zeros, silently merge sources, or imply a verified station.
Failures are tracked and do not prevent forecast deployment.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import os
from pathlib import Path
from typing import Any

import requests

LAT, LON = -23.065, -54.190
OPEN_METEO = 'https://archive-api.open-meteo.com/v1/archive'
NASA = 'https://power.larc.nasa.gov/api/temporal/daily/point'
TODAY_TZ = dt.timezone(dt.timedelta(hours=-4))


def valid(v: Any, *, nonneg=False) -> float | None:
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        return None
    if v <= -9000 or (nonneg and v < 0):
        return None
    return float(v)


def parse_era5(payload: dict) -> dict[str, dict]:
    if payload.get('utc_offset_seconds') != 0:
        raise ValueError('ERA5: período não referenciado em UTC')
    d = payload.get('daily') or {}
    times = d.get('time') or []
    rain = d.get('precipitation_sum') or []
    if not times or len(times) != len(rain):
        raise ValueError('ERA5: chuva/datas incompletas')
    rows = {}
    for i, date in enumerate(times):
        if not isinstance(date, str) or len(date) != 10 or date in rows:
            raise ValueError('ERA5: data inválida ou repetida')
        rows[date] = {
            'precipitation_mm': valid(rain[i], nonneg=True),
            'temperature_mean_c': valid((d.get('temperature_2m_mean') or [None] * len(times))[i]),
        }
    if not any(v['precipitation_mm'] is not None for v in rows.values()):
        raise ValueError('ERA5: precipitação numérica indisponível')
    return rows


def parse_nasa(payload: dict) -> dict[str, dict]:
    p = (payload.get('properties') or {}).get('parameter') or {}
    rain = p.get('PRECTOTCORR') or {}
    temp = p.get('T2M') or {}
    if not isinstance(rain, dict) or not rain:
        raise ValueError('NASA POWER: precipitação não retornada')
    rows = {}
    for k, v in rain.items():
        if not (isinstance(k, str) and len(k) == 8 and k.isdigit()):
            continue
        date = k[:4] + '-' + k[4:6] + '-' + k[6:8]
        rows[date] = {'precipitation_mm': valid(v, nonneg=True), 'temperature_mean_c': valid(temp.get(k))}
    if not any(v['precipitation_mm'] is not None for v in rows.values()):
        raise ValueError('NASA POWER: chuva numérica indisponível')
    return rows


def paired(era: dict, nasa: dict) -> dict:
    dates = sorted(set(era) | set(nasa))
    rows = [{'date': date, 'era5_mm': era.get(date, {}).get('precipitation_mm'),
             'nasa_mm': nasa.get(date, {}).get('precipitation_mm'),
             'era5_temperature_c': era.get(date, {}).get('temperature_mean_c'),
             'nasa_temperature_c': nasa.get(date, {}).get('temperature_mean_c')}
            for date in dates]
    overlap = [r for r in rows if r['era5_mm'] is not None and r['nasa_mm'] is not None]
    return {'rows': rows, 'n_era5': sum(x['era5_mm'] is not None for x in rows),
            'n_nasa': sum(x['nasa_mm'] is not None for x in rows),
            'n_paired': len(overlap),
            'mean_nasa_minus_era5_mm': round(sum(r['nasa_mm'] - r['era5_mm'] for r in overlap) / len(overlap), 3) if overlap else None,
            'note': 'Duas estimativas de grade no mesmo dia UTC; diferenças não são erros contra estação observada.'}


def get(url, params, timeout=28):
    r = requests.get(url, params=params, timeout=timeout,
                     headers={'User-Agent': 'Campo-e-Clima/1.9 research historical service'})
    r.raise_for_status()
    out = r.json()
    if not isinstance(out, dict) or out.get('error'):
        raise ValueError(str(out.get('reason', 'Resposta histórica não é JSON válido')))
    return out


def collect(today: dt.date | None = None, fetcher=get) -> dict:
    today = today or dt.datetime.now(TODAY_TZ).date()
    end = today - dt.timedelta(days=7)  # avoid mixing recent data with lagging reanalysis
    start = end - dt.timedelta(days=89)
    ea, na, errors = {}, {}, {}
    try:
        data = fetcher(OPEN_METEO, {'latitude': LAT, 'longitude': LON, 'start_date': start.isoformat(),
                                   'end_date': end.isoformat(), 'timezone': 'GMT', 'models': 'era5',
                                   'daily': 'precipitation_sum,temperature_2m_mean'}, 28)
        ea = parse_era5(data)
    except (requests.RequestException, ValueError, TypeError, IndexError) as ex:
        errors['era5'] = str(ex)[:180]
    try:
        data = fetcher(NASA, {'latitude': LAT, 'longitude': LON,
                              'start': start.strftime('%Y%m%d'), 'end': end.strftime('%Y%m%d'),
                              'community': 'AG', 'parameters': 'PRECTOTCORR,T2M',
                              'format': 'JSON', 'time-standard': 'UTC'}, 28)
        na = parse_nasa(data)
    except (requests.RequestException, ValueError, TypeError, IndexError) as ex:
        errors['nasa_power'] = str(ex)[:180]
    merge = paired(ea, na)
    return {'state': 'ok' if (ea or na) else 'unavailable',
            'issued_at_utc': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'),
            'locality': 'Naviraí–MS', 'latitude': LAT, 'longitude': LON,
            'reference_day': 'UTC', 'start_date': start.isoformat(), 'end_date': end.isoformat(),
            'sources': {'era5': OPEN_METEO, 'nasa_power': NASA},
            'source_errors': errors, **merge}


def publish(cache: Path, public: Path, *, today=None, fetcher=get) -> dict:
    today = today or dt.datetime.now(TODAY_TZ).date()
    old = None
    if cache.exists():
        try:
            old = json.loads(cache.read_text(encoding='utf-8'))
            if old.get('state') in ('ok', 'stale', 'unavailable') and old.get('collected_day') == today.isoformat():
                public.parent.mkdir(parents=True, exist_ok=True)
                public.write_text(json.dumps(old, ensure_ascii=False), encoding='utf-8')
                return old
        except (OSError, ValueError):
            old = None
    new = collect(today, fetcher=fetcher)
    new['collected_day'] = today.isoformat()
    if new['state'] != 'ok' and old and old.get('state') == 'ok':
        new = {**old, 'state': 'stale', 'collected_day': today.isoformat(), 'source_errors': new['source_errors'],
               'note': 'Última coleta válida preservada; dados desatualizados. Não interpretar ausência como zero.'}
    cache.parent.mkdir(parents=True, exist_ok=True)
    public.parent.mkdir(parents=True, exist_ok=True)
    if new['state'] in ('ok', 'stale', 'unavailable'):
        cache.write_text(json.dumps(new, ensure_ascii=False), encoding='utf-8')
    public.write_text(json.dumps(new, ensure_ascii=False), encoding='utf-8')
    return new


if __name__ == '__main__':
    out = publish(Path('site/data/history_daily_cache.json'), Path('site/data/history_navirai.json'))
    print('Historical archive:', out['state'], out.get('n_era5'), out.get('n_nasa'), 'days')
