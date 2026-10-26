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
try:
    from scripts.spraying import read_joint_members, mix_joint_hourly, mix_joint_windows2h
except ModuleNotFoundError:  # CLI invocation: python scripts/collect.py
    from spraying import read_joint_members, mix_joint_hourly, mix_joint_windows2h
try:
    from scripts.sources.free_research import collect_climate_era5, collect_previous_runs, compare_export_provisional, collect_openweather_free
    from scripts.sources.official import collect_official
    from scripts.sources.embrapa import load_optional
    from scripts.sources.supplementary import (collect_cptec, collect_openweather, collect_soil_forecast, collect_nasa_power, collect_extended, load_export_provisional)
except ModuleNotFoundError:
    from sources.free_research import collect_climate_era5, collect_previous_runs, compare_export_provisional, collect_openweather_free
    from sources.official import collect_official
    from sources.embrapa import load_optional
    from sources.supplementary import (collect_cptec, collect_openweather, collect_soil_forecast, collect_nasa_power, collect_extended, load_export_provisional)

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



def model_hourly_rain(payload: dict, max_hours: int = 72) -> dict:
    """Complete-member rainfall totals for forward 1h, 3h and 6h windows.

    Uses member trajectories, not multiplication of marginal probabilities.
    Only timestamps aligned across members/models are compared. Open-Meteo can
    interpolate coarser-native-time products to the requested hourly grid.
    """
    h = payload.get('hourly') or {}
    times = h.get('time') or []
    raw = get_members(payload, 'precipitation')
    output = {}
    for start, stamp in enumerate(times[:max_hours]):
        for duration in (1, 3, 6):
            if start + duration > len(times):
                continue
            # Must be contiguous clock hours; incomplete/coarse timestamps excluded.
            try:
                datetimes = [dt.datetime.fromisoformat(t) for t in times[start:start+duration]]
                if any((b-a) != dt.timedelta(hours=1) for a,b in zip(datetimes,datetimes[1:])):
                    continue
            except ValueError:
                continue
            totals = []
            for member in raw:
                if len(member) != len(times):
                    continue
                xs = member[start:start+duration]
                if len(xs) != duration or any(not isinstance(x,(int,float)) or not math.isfinite(x) or x < 0 for x in xs):
                    continue
                totals.append(sum(float(x) for x in xs))
            if totals:
                output.setdefault(stamp,{})[duration] = totals
    return output


def mix_hourly_rain(by_model: dict[str,dict]) -> list[dict]:
    """Mixture: 1/M total model weight, 1/n per valid model member for each window."""
    stamps = sorted({t for model in by_model.values() for t in model})
    out = []
    for stamp in stamps:
        row = {'time':stamp, 'windows':{}}
        for duration in (1,3,6):
            valid = {name:item[stamp][duration] for name,item in by_model.items()
                     if stamp in item and item[stamp].get(duration)}
            if not valid:
                continue
            model_weight = 1 / len(valid)
            pairs = [(value,model_weight/len(members)) for members in valid.values() for value in members]
            summary = {
                'models':len(valid),
                'members':sum(len(members) for members in valid.values()),
                'mean_mm':round(sum(v*w for v,w in pairs),3),
                'p10_mm':round(weighted_quantile(pairs,.1),3),
                'p50_mm':round(weighted_quantile(pairs,.5),3),
                'p90_mm':round(weighted_quantile(pairs,.9),3),
            }
            for threshold in (0.1,1,3,5,10,20):
                summary['p_gt_'+str(threshold).replace('.','_')+'_mm'] = round(sum(w for v,w in pairs if v>threshold),4)
            row['windows'][str(duration)] = summary
        if row['windows']:
            out.append(row)
    return out


def rain_models_comparison(by_model: dict[str,dict]) -> list[dict]:
    """Daily member-based means and exceedances, grouped by named model."""
    result = []
    for name,item in by_model.items():
        for day,members in sorted(item.get('days',{}).items()):
            if not members:
                continue
            result.append({'model':name,'date':day,'members':len(members),
                           'mean_mm':round(sum(members)/len(members),3),
                           'p_gt_5_mm':round(sum(x>5 for x in members)/len(members),4)})
    return result

def main():
    recorded = dt.datetime.now(dt.timezone.utc).isoformat()
    result: dict[str, Any] = {'schema_version': 4, 'issued_at_utc': recorded,
             'site': {'latitude': LAT, 'longitude': LON, 'timezone': TZ},
             'methodology': 'Equal total weight per valid ensemble model; uncalibrated member frequencies; forward 1/3/6h totals from joint member trajectories; interpolated hourly grids not independent measurements',
             'sources': {}, 'deterministic': None, 'rain_ensemble_daily': [], 'gust_ensemble_daily': [], 'rain_ensemble_hourly': [], 'rain_models_daily': [], 'ensemble_models': {},
             'spray_joint_hourly': [], 'spray_joint_windows_2h': [], 'spray_joint_model_status': {},
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
    by_model_hourly = {}
    by_model_gust = {}
    by_model_spray = {}
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
            hourly_rain = model_hourly_rain(e)
            result['ensemble_models'][name] = {
                'code': code, 'precipitation_members': d['member_count'],
                'gust_members': g['member_count'],
                'grid_lat': e.get('latitude'), 'grid_lon': e.get('longitude'),
                'collected_at_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
                'gust_request_error': gust_request_error,
                'state': 'ok' if any(d['days'].values()) else 'no_valid_daily_rain_members'}
            if any(d['days'].values()):
                by_model[name] = d
            if hourly_rain:
                by_model_hourly[name] = hourly_rain
            if any(g['days'].values()):
                by_model_gust[name] = g
            # Separate 4-day request avoids duplicating huge 7-day member arrays.
            # Not all models have all spraying inputs. Missing => excluded,
            # NEVER classified as meteorologically favorable.
            try:
                spray_params = {**base_params(), 'forecast_days': 4,
                                'hourly': ','.join(['precipitation','temperature_2m',
                                  'relative_humidity_2m','wind_speed_10m',
                                  'wind_direction_10m','wind_gusts_10m'])}
                spray = fetch(ENSEMBLE_URL, {**spray_params, 'models': code})
                joint = read_joint_members(spray)
                result['spray_joint_model_status'][name] = {
                    'member_fields_complete':joint['members_available'],
                    'member_hour_available':sum(len(x) for x in joint['times'].values()),
                    'status':'ok' if joint['times'] else 'sem_membros_conjuntos_validos'}
                if joint['times']:by_model_spray[name] = joint
            except Exception as spray_err:
                result['spray_joint_model_status'][name] = {
                    'status':'indisponivel', 'detail':str(spray_err)[:180],
                    'member_fields_complete':0}
        except Exception as exc:
            result['ensemble_models'][name] = {'code': code, 'state': 'error', 'detail': str(exc)[:220]}
        time.sleep(.2)
    result['rain_ensemble_daily'] = mix_days(by_model)
    result['rain_ensemble_hourly'] = mix_hourly_rain(by_model_hourly)
    result['rain_models_daily'] = rain_models_comparison(by_model)
    result['gust_ensemble_daily'] = mix_gust_days(by_model_gust)
    result['spray_joint_hourly'] = mix_joint_hourly(by_model_spray)
    result['spray_joint_windows_2h'] = mix_joint_windows2h(by_model_spray)
    if not result['spray_joint_hourly']:
        result['warnings'].append('No ensemble has all six variables aligned by member for spraying: no joint screening frequencies')
    if not result['rain_ensemble_daily']:
        result['warnings'].append('No complete member/day precipitation sample; ensemble chart unavailable')
    if not result['gust_ensemble_daily']:
        result['warnings'].append('No complete member/day gust sample; gust exceedance probabilities unavailable')

    # Official observations/alerts are separate products, NOT extra model members.
    # Errors only affect their own section, never conceal validated ensemble data.
    result['official'] = collect_official()
    provisional = pathlib.Path('data/observacoes/embrapa_exportacao_provisoria.csv')
    result['embrapa_observations'] = load_export_provisional(provisional) if provisional.is_file() else load_optional(pathlib.Path(
        os.environ.get('EMBRAPA_CSV', 'data/observacoes/embrapa_navirai.csv')))
    # Independent comparator feeds. None counts as an additional Open-Meteo ensemble member.
    # Slow-changing products can be cached across half-hourly GitHub Actions runs
    # using actions/cache keyed by the local calendar day.
    slow_cache=pathlib.Path('site/data/slow_sources_cache.json')
    slow_day=dt.datetime.now(dt.timezone(dt.timedelta(hours=-4))).date().isoformat()
    previous={}
    if slow_cache.is_file():
        try:
            previous=json.loads(slow_cache.read_text(encoding='utf-8'))
            if previous.get('cache_day')!=slow_day:previous={}
        except (ValueError,OSError):previous={}
    if previous:
        slow_sources=previous.get('sources',{})
    else:
        slow_sources={
          'nasa_power':collect_nasa_power(enabled=os.environ.get('NASA_POWER_ENABLE')=='1'),
          'ecmwf_extended':collect_extended(enabled=os.environ.get('ECMWF_EXTENDED_ENABLE')=='1'),
          'previous_runs':collect_previous_runs(enabled=True)}
        slow_cache.parent.mkdir(parents=True,exist_ok=True)
        slow_cache.write_text(json.dumps({'cache_day':slow_day,'sources':slow_sources},ensure_ascii=False),encoding='utf-8')
    # Thirty-year ERA5-Land baseline refreshes once per local month, separately
    # from the daily supplementary-product cache.
    climate_cache=pathlib.Path('site/data/climate_cache.json')
    climate_month=slow_day[:7]
    climate=None
    if climate_cache.is_file():
        try:
            old=json.loads(climate_cache.read_text(encoding='utf-8'))
            if old.get('cache_month')==climate_month: climate=old.get('data')
        except (ValueError,OSError):pass
    if climate is None:
        climate=collect_climate_era5(enabled=True)
        climate_cache.parent.mkdir(parents=True,exist_ok=True)
        climate_cache.write_text(json.dumps({'cache_month':climate_month,'data':climate},ensure_ascii=False),encoding='utf-8')
    result['historical_comparison'] = compare_export_provisional(
        slow_sources.get('previous_runs',{}),result['embrapa_observations'])
    result['complementary'] = {
       'cptec': collect_cptec(),
       'openweather': collect_openweather_free(),
       'soil_forecast': collect_soil_forecast(),
       'nasa_power': slow_sources.get('nasa_power',{'state':'requires_setup'}),
       'ecmwf_extended': slow_sources.get('ecmwf_extended',{'state':'requires_setup'}),
       'previous_runs':slow_sources.get('previous_runs',{'state':'unavailable'}),
       'era5_climatology':climate,
       'goes_satellite': {'state':'requires_setup','source':'CPTEC/INPE DSAT GOES-19',
          'source_url':'https://www.cptec.inpe.br/dsat/',
          'note':'Visualizador oficial disponível. Integração de tiles e imagem automática exige validar licença, camada, atualização e cobertura; sem imagem sem timestamp.'},
       'gpm_imerg':{'state':'requires_registration','source':'NASA GPM IMERG',
          'source_url':'https://gpm.nasa.gov/data/imerg',
          'note':'Acesso operacional a dados de precipitação exige cadastro Earthdata/PPS e tratamento de arquivos GeoTIFF/HDF5; não há leitura numérica nesta versão.'},
       'soilgrids':{'state':'service_paused','source':'ISRIC SoilGrids',
          'source_url':'https://docs.isric.org/globaldata/soilgrids/',
          'note':'API REST suspensa; WCS, Earth Engine e WebDAV são alternativas a implementar para atributos estáticos.'},
    }
    for source_name,item in result['complementary'].items():
        result['sources'][source_name]={'state':item.get('state'),
            'source_url':item.get('source_url'),
            'queried_at_utc':item.get('queried_at_utc')}

    for source_name, item in result['official'].items():
        result['sources'][source_name] = {
            'state':item['state'], 'source_url':item.get('source_url'),
            'queried_at_utc':item.get('queried_at_utc')}
    result['sources']['Embrapa Guia Clima'] = {
        'state':result['embrapa_observations']['state'],
        'source_url':result['embrapa_observations'].get('source_url')}

    dest = pathlib.Path(os.environ.get('OUTPUT_JSON', 'site/data/latest.json'))
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(result, ensure_ascii=False, separators=(',',':')), encoding='utf-8')
    print('Wrote', dest, '; deterministic:', bool(result['deterministic']), '; ensemble models:', len(by_model))
    if not result['deterministic'] and not by_model:
        raise SystemExit('No fresh weather values available: not publishing a misleading successful update')

if __name__ == '__main__':
    main()
