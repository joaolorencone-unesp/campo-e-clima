"""Verification and bias correction of deterministic forecasts at physical stations.

Data
- Observations: ``scripts.science.station_files`` (QC'd hourly and local-day values).
- Forecasts: Open-Meteo Previous Runs API at the station coordinates (free, non-commercial),
  one explicit model per request, fixed nominal leads D1, D2, D3 and D7 (``*_previous_dayN``:
  the forecast issued N days before the valid day; 24N to 24N+23 h ahead).

Method (per station × model × lead × variable)
- Pairs are built on identical UTC hours (hourly variables) or identical local days (daily).
- Corrections are evaluated strictly out of sample with a rolling origin by calendar month:
  each month is predicted with parameters fitted only on earlier months, with a purge gap of
  lead + 1 days, so no observation from the test period (or later) influences the fit.
- Candidate corrections are deliberately simple: additive bias, hour-of-day bias (shrunk),
  linear regression, multiplicative ratio and empirical quantile mapping with wet-day
  frequency adaptation for daily rain. All are refit on the full sample only to publish the
  operational parameters of a method that already proved itself out of sample.
- A correction is "recommended" only when its out-of-sample MAE is lower than the raw
  forecast with a 95 % block-bootstrap interval excluding zero, at least 5 % better and with a
  minimum test size. Otherwise the raw forecast stays and the reason is published.
"""
from __future__ import annotations
import collections
import datetime as dt
import json
import math
import os
from pathlib import Path
import numpy as np
from .common import digest, haversine, now, packed, write_json
from .station_files import aggregate_local_days, load_station, registry, HOURLY_FIELDS

PREVIOUS_RUNS_URL = 'https://previous-runs-api.open-meteo.com/v1/forecast'
DEFAULT_MODELS = ('ecmwf_ifs025', 'gfs_global', 'icon_seamless', 'gem_global', 'meteofrance_arpege_world', 'ukmo_global_deterministic_10km', 'jma_gsm')
LEADS = (1, 2, 3, 7)
CORE_VARIABLES = ('temperature_2m', 'relative_humidity_2m', 'precipitation', 'wind_speed_10m', 'wind_gusts_10m')
EXTRA_VARIABLES = ('shortwave_radiation', 'et0_fao_evapotranspiration')
MULTIMODEL = 'multimodelo_media'
HOURLY_TARGETS = {'temperature_2m': ('bias', 'hourly_bias', 'linear'), 'relative_humidity_2m': ('bias', 'linear'),
                  'wind_speed_10m': ('ratio', 'linear'), 'wind_gusts_10m': ('ratio', 'linear')}
DAILY_TARGETS = {'t_max': ('bias', 'linear'), 't_min': ('bias', 'linear'), 'rain_mm': ('ratio', 'quantile_map'),
                 'radiation_mj': ('bias', 'linear'), 'et0_mm': ('bias', 'linear'), 'wind_mean_kmh': ('ratio', 'linear'), 'gust_max_kmh': ('ratio', 'linear')}
CLIP = {'relative_humidity_2m': (0, 100), 'wind_speed_10m': (0, None), 'wind_gusts_10m': (0, None), 'rain_mm': (0, None),
        'radiation_mj': (0, None), 'et0_mm': (0, None), 'wind_mean_kmh': (0, None), 'gust_max_kmh': (0, None)}
MIN_TRAIN = {'hourly': 500, 'daily': 25}
MIN_TEST = {'hourly': 300, 'daily': 45}
MIN_IMPROVEMENT = 0.05
WET_MM = 0.2
BOOTSTRAP = 1000
SEED = 22


# ----------------------------------------------------------------------------- forecasts
def forecast_point(station):
    if station.get('latitude') is not None and station.get('longitude') is not None:
        return {'latitude': station['latitude'], 'longitude': station['longitude'], 'source': 'station_coordinates'}
    fallback = station.get('forecast_point_fallback') or {}
    return {'latitude': fallback['latitude'], 'longitude': fallback['longitude'], 'source': 'municipal_reference_point'}


def blocks(start, end, days=31):
    first, last = dt.date.fromisoformat(start), dt.date.fromisoformat(end)
    while first <= last:
        stop = min(last, first + dt.timedelta(days=days - 1))
        yield first.isoformat(), stop.isoformat()
        first = stop + dt.timedelta(days=1)


def hourly_fields(variables, leads=LEADS):
    return [f'{v}_previous_day{n}' for v in variables for n in leads]


def payload_to_records(payload, leads=LEADS):
    """Per lead, hourly records in the station shape (``clean`` holds canonical units)."""
    hourly = payload.get('hourly') or {}
    times = hourly.get('time') or []
    if not times:
        raise ValueError('Resposta sem eixo de tempo')
    stamps = [dt.datetime.fromtimestamp(t, dt.timezone.utc).isoformat(timespec='seconds') if isinstance(t, (int, float)) else str(t) for t in times]
    out = {}
    for n in leads:
        rows = []
        for i, stamp in enumerate(stamps):
            clean = {}
            for v in CORE_VARIABLES + EXTRA_VARIABLES:
                values = hourly.get(f'{v}_previous_day{n}')
                value = values[i] if isinstance(values, list) and i < len(values) else None
                clean[v] = float(value) if isinstance(value, (int, float)) and math.isfinite(value) else None
            clean['temperature_hour_max'] = clean['temperature_hour_min'] = clean['temperature_2m']
            clean['rh_hour_max'] = clean['rh_hour_min'] = clean['relative_humidity_2m']
            rows.append({'valid_at_utc': stamp, 'clean': clean})
        out[n] = rows
    return out


def fetch_station_forecasts(client, station, start, end, *, models=DEFAULT_MODELS, leads=LEADS):
    """One explicit model per request, 31-day blocks; an invalid model id (HTTP 400) is isolated."""
    point = forecast_point(station)
    result = {'point': point, 'models': {}, 'leads': list(leads)}
    for model in models:
        state = {'state': 'ok', 'blocks': 0, 'errors': [], 'variables': list(CORE_VARIABLES + EXTRA_VARIABLES)}
        merged = {n: [] for n in leads}
        variables = CORE_VARIABLES + EXTRA_VARIABLES
        for first, last in blocks(start, end):
            params = {'latitude': point['latitude'], 'longitude': point['longitude'], 'models': model, 'start_date': first, 'end_date': last,
                      'timezone': 'UTC', 'timeformat': 'unixtime', 'hourly': ','.join(hourly_fields(variables, leads))}
            payload = None
            for attempt in range(2):
                try:
                    payload = client.get(PREVIOUS_RUNS_URL, params, ttl_hours=24 * 30, product='station_previous_runs')
                    break
                except Exception as exc:  # noqa: BLE001 - per-model isolation is the point
                    message = f'{type(exc).__name__}: {str(exc)[:140]}'
                    status = getattr(getattr(exc, 'response', None), 'status_code', None)
                    if status == 400 and attempt == 0 and variables != CORE_VARIABLES:
                        # Some models lack radiation/ET0 in this product: retry once with the core set.
                        variables = CORE_VARIABLES
                        params['hourly'] = ','.join(hourly_fields(variables, leads))
                        state['variables'] = list(variables)
                        continue
                    state['errors'].append({'block': [first, last], 'error': message, 'http_status': status})
                    break
            if payload is None:
                if any(e.get('http_status') == 400 for e in state['errors']) and state['blocks'] == 0:
                    state['state'] = 'unavailable'
                    break
                continue
            try:
                per_lead = payload_to_records(payload, leads)
            except ValueError as exc:
                state['errors'].append({'block': [first, last], 'error': str(exc)})
                continue
            for n in leads:
                merged[n].extend(per_lead[n])
            state['blocks'] += 1
            state.setdefault('grid', {'latitude': payload.get('latitude'), 'longitude': payload.get('longitude'), 'elevation_m': payload.get('elevation')})
        if state['state'] == 'ok' and state['blocks'] == 0:
            state['state'] = 'unavailable'
        if state['state'] == 'ok' and state['errors']:
            state['state'] = 'partial'
        state['hourly'] = merged if state['state'] != 'unavailable' else {}
        result['models'][model] = state
    return result


def add_multimodel_mean(forecasts, leads=LEADS):
    """Equal-weight mean of the models available at each hour (rain included: mean of amounts)."""
    available = [m for m, s in forecasts['models'].items() if s['state'] in ('ok', 'partial') and s.get('hourly')]
    if len(available) < 2:
        return forecasts
    merged = {}
    for n in leads:
        by_time = collections.defaultdict(list)
        for m in available:
            for row in forecasts['models'][m]['hourly'].get(n, []):
                by_time[row['valid_at_utc']].append(row['clean'])
        rows = []
        for stamp in sorted(by_time):
            cleans = by_time[stamp]
            clean = {}
            for key in cleans[0]:
                values = [c[key] for c in cleans if c.get(key) is not None]
                clean[key] = sum(values) / len(values) if len(values) == len(available) else None
            rows.append({'valid_at_utc': stamp, 'clean': clean})
        merged[n] = rows
    forecasts['models'][MULTIMODEL] = {'state': 'ok', 'blocks': None, 'errors': [], 'members': available, 'hourly': merged,
                                       'variables': list(CORE_VARIABLES + EXTRA_VARIABLES)}
    return forecasts


# ----------------------------------------------------------------------------- pairing
def pair_hourly(obs_records, fc_records, variable, offset_hours):
    fc = {r['valid_at_utc']: r['clean'].get(variable) for r in fc_records}
    pairs = []
    for r in obs_records:
        y = r['clean'].get(variable)
        x = fc.get(r['valid_at_utc'])
        if y is None or x is None:
            continue
        local = dt.datetime.fromisoformat(r['valid_at_utc']) + dt.timedelta(hours=offset_hours)
        pairs.append({'date': local.date().isoformat(), 'hour': local.hour, 'x': x, 'y': y})
    return pairs


def pair_daily(obs_daily, fc_daily, field):
    fc = {d['date']: d.get(field) for d in fc_daily}
    pairs = []
    for d in obs_daily:
        y = (d.get('clean') or {}).get(field, d.get(field))
        x = fc.get(d['date'])
        if y is None or x is None:
            continue
        pairs.append({'date': d['date'], 'hour': None, 'x': x, 'y': y})
    return pairs


# ----------------------------------------------------------------------------- corrections
def fit(method, x, y, hours=None):
    x, y = np.asarray(x, float), np.asarray(y, float)
    if method == 'bias':
        return {'method': method, 'bias': float(np.mean(y - x))}
    if method == 'ratio':
        total = float(np.sum(x))
        return {'method': method, 'ratio': float(np.sum(y) / total) if total > 0 else 1.0}
    if method == 'linear':
        if len(x) < 30 or float(np.var(x)) <= 1e-9:
            return {'method': method, 'slope': 1.0, 'intercept': float(np.mean(y - x))}
        slope, intercept = np.polyfit(x, y, 1)
        return {'method': method, 'slope': float(slope), 'intercept': float(intercept)}
    if method == 'hourly_bias':
        hours = np.asarray(hours)
        global_bias = float(np.mean(y - x))
        table = {}
        for h in range(24):
            mask = hours == h
            n = int(mask.sum())
            local = float(np.mean((y - x)[mask])) if n else global_bias
            # Shrink sparse hours toward the global bias (k = 10 pseudo-observations).
            table[str(h)] = round((n * local + 10 * global_bias) / (n + 10), 4)
        return {'method': method, 'global_bias': global_bias, 'by_hour': table}
    if method == 'quantile_map':
        wet_obs = float(np.mean(y > WET_MM))
        wet_fc = float(np.mean(x > WET_MM))
        threshold = WET_MM
        if wet_fc > wet_obs and wet_obs > 0:
            threshold = float(np.quantile(x, 1 - wet_obs))
        xs, ys = np.sort(x[x > threshold]), np.sort(y[y > WET_MM])
        probs = np.linspace(0.02, 0.98, 25)
        if len(xs) < 10 or len(ys) < 10:
            return {'method': method, 'threshold': threshold, 'qx': [], 'qy': [], 'fallback_ratio': fit('ratio', x, y)['ratio']}
        return {'method': method, 'threshold': threshold, 'qx': np.quantile(xs, probs).round(3).tolist(), 'qy': np.quantile(ys, probs).round(3).tolist(),
                'wet_frequency_obs': round(wet_obs, 4), 'wet_frequency_forecast': round(wet_fc, 4)}
    raise ValueError(method)


def apply(params, x, hours=None, variable=None):
    x = np.asarray(x, float)
    method = params['method']
    if method == 'bias':
        out = x + params['bias']
    elif method == 'ratio':
        out = x * params['ratio']
    elif method == 'linear':
        out = params['intercept'] + params['slope'] * x
    elif method == 'hourly_bias':
        table = params['by_hour']
        out = x + np.asarray([table[str(int(h))] for h in hours], float)
    elif method == 'quantile_map':
        qx, qy = np.asarray(params.get('qx') or [], float), np.asarray(params.get('qy') or [], float)
        if len(qx) < 2:
            out = x * params.get('fallback_ratio', 1.0)
        else:
            out = np.where(x > params['threshold'], np.interp(x, qx, qy), 0.0)
            # Beyond the highest training quantile scale by the top-quantile ratio (no flat cap).
            high = x > qx[-1]
            out = np.where(high, x * (qy[-1] / qx[-1] if qx[-1] > 0 else 1.0), out)
    else:
        raise ValueError(method)
    low, high = CLIP.get(variable, (None, None))
    if low is not None:
        out = np.maximum(out, low)
    if high is not None:
        out = np.minimum(out, high)
    return out


def rolling_origin(pairs, methods, *, kind, lead_days, variable):
    """Out-of-sample predictions month by month; returns pooled arrays per method."""
    months = sorted({p['date'][:7] for p in pairs})
    pooled = {'y': [], 'raw': [], 'date': [], 'hour': [], 'month': []}
    predictions = {m: [] for m in methods}
    folds = []
    for month in months[1:]:
        first_test = dt.date.fromisoformat(month + '-01')
        cutoff = (first_test - dt.timedelta(days=lead_days + 1)).isoformat()
        train = [p for p in pairs if p['date'] < cutoff]
        test = [p for p in pairs if p['date'][:7] == month]
        if len(train) < MIN_TRAIN[kind] or not test:
            continue
        tx, ty, th = [p['x'] for p in train], [p['y'] for p in train], [p['hour'] for p in train]
        sx, sh = [p['x'] for p in test], [p['hour'] for p in test]
        for m in methods:
            params = fit(m, tx, ty, th)
            predictions[m].extend(apply(params, sx, sh, variable).tolist())
        pooled['y'].extend(p['y'] for p in test); pooled['raw'].extend(sx); pooled['date'].extend(p['date'] for p in test)
        pooled['hour'].extend(sh); pooled['month'].extend([month] * len(test))
        folds.append({'test_month': month, 'train_n': len(train), 'test_n': len(test), 'train_until': cutoff})
    return pooled, predictions, folds


def metrics(pred, y):
    e = np.asarray(pred, float) - np.asarray(y, float)
    return {'n': int(len(e)), 'mae': round(float(np.mean(np.abs(e))), 3), 'rmse': round(float(np.sqrt(np.mean(e * e))), 3), 'bias': round(float(np.mean(e)), 3)}


def contingency(pred, y, threshold):
    p, o = np.asarray(pred) > threshold, np.asarray(y) > threshold
    hits, misses, false = int((p & o).sum()), int((~p & o).sum()), int((p & ~o).sum())
    return {'threshold_mm': threshold, 'hits': hits, 'misses': misses, 'false_alarms': false, 'correct_negatives': int((~p & ~o).sum()),
            'pod': round(hits / (hits + misses), 3) if hits + misses else None, 'far': round(false / (hits + false), 3) if hits + false else None,
            'csi': round(hits / (hits + misses + false), 3) if hits + misses + false else None,
            'frequency_bias': round((hits + false) / (hits + misses), 3) if hits + misses else None}


def block_bootstrap_delta_mae(pred, raw, y, block_keys, *, resamples=BOOTSTRAP, seed=SEED):
    """95 % interval of MAE(pred) − MAE(raw), resampling whole blocks (days or ISO weeks)."""
    pred, raw, y = np.asarray(pred, float), np.asarray(raw, float), np.asarray(y, float)
    keys = np.asarray(block_keys)
    unique, inverse = np.unique(keys, return_inverse=True)
    if len(unique) < 5:
        return None
    diff = np.abs(pred - y) - np.abs(raw - y)
    sums = np.bincount(inverse, weights=diff, minlength=len(unique))
    counts = np.bincount(inverse, minlength=len(unique)).astype(float)
    rng = np.random.default_rng(seed)
    draws = rng.integers(0, len(unique), size=(resamples, len(unique)))
    deltas = sums[draws].sum(axis=1) / counts[draws].sum(axis=1)
    return [round(float(np.percentile(deltas, 2.5)), 4), round(float(np.percentile(deltas, 97.5)), 4)]


def week_key(date):
    y, w, _ = dt.date.fromisoformat(date).isocalendar()
    return f'{y}-W{w:02d}'


def evaluate_group(pairs, *, kind, lead_days, variable, methods):
    if len(pairs) < MIN_TRAIN[kind]:
        return {'status': 'insufficient_pairs', 'n_pairs': len(pairs)}
    pooled, predictions, folds = rolling_origin(pairs, methods, kind=kind, lead_days=lead_days, variable=variable)
    n_test = len(pooled['y'])
    raw_all = metrics([p['x'] for p in pairs], [p['y'] for p in pairs])
    result = {'status': 'evaluated', 'n_pairs': len(pairs), 'n_test': n_test, 'raw_all_pairs': raw_all, 'folds': folds, 'methods': []}
    if variable == 'rain_mm':
        result['raw_contingency'] = [contingency([p['x'] for p in pairs], [p['y'] for p in pairs], t) for t in (1, 10)]
    if n_test < MIN_TEST[kind]:
        result['status'] = 'insufficient_test_sample'
        return result
    raw_test = metrics(pooled['raw'], pooled['y'])
    result['raw_test'] = raw_test
    blocks_keys = pooled['date'] if kind == 'hourly' else [week_key(d) for d in pooled['date']]
    best = None
    for m in methods:
        pred = predictions[m]
        item = {'name': m, **metrics(pred, pooled['y'])}
        item['skill_mae'] = round(1 - item['mae'] / raw_test['mae'], 4) if raw_test['mae'] > 0 else None
        item['delta_mae_ci95'] = block_bootstrap_delta_mae(pred, pooled['raw'], pooled['y'], blocks_keys)
        if variable == 'rain_mm':
            item['contingency'] = [contingency(pred, pooled['y'], t) for t in (1, 10)]
        ci = item['delta_mae_ci95']
        item['significant_improvement'] = bool(ci and ci[1] < 0 and item['skill_mae'] is not None and item['skill_mae'] >= MIN_IMPROVEMENT)
        result['methods'].append(item)
        if item['significant_improvement'] and (best is None or item['mae'] < best['mae']):
            best = item
    if best:
        params = fit(best['name'], [p['x'] for p in pairs], [p['y'] for p in pairs], [p['hour'] for p in pairs])
        result['recommended'] = {'method': best['name'], 'parameters': params, 'fitted_on': {'n': len(pairs), 'start': pairs[0]['date'], 'end': pairs[-1]['date']},
                                 'evidence': {'n_test': n_test, 'mae_raw': raw_test['mae'], 'mae_corrected': best['mae'], 'skill_mae': best['skill_mae'],
                                              'delta_mae_ci95': best['delta_mae_ci95'], 'months_tested': [f['test_month'] for f in folds]},
                                 'status': 'validated_out_of_sample'}
    else:
        result['recommended'] = None
        result['reason'] = 'Nenhuma correção reduziu o MAE fora da amostra com intervalo de confiança excluindo zero e ganho ≥ 5 %.'
    return result


def diagnostics_hourly(pairs):
    by_hour, by_month = collections.defaultdict(list), collections.defaultdict(list)
    for p in pairs:
        by_hour[p['hour']].append(p['x'] - p['y']); by_month[p['date'][:7]].append(p['x'] - p['y'])
    return {'bias_by_local_hour': [{'hour': h, 'n': len(v), 'bias': round(float(np.mean(v)), 2), 'mae': round(float(np.mean(np.abs(v))), 2)} for h, v in sorted(by_hour.items())],
            'bias_by_month': [{'month': m, 'n': len(v), 'bias': round(float(np.mean(v)), 2), 'mae': round(float(np.mean(np.abs(v))), 2)} for m, v in sorted(by_month.items())]}


# ----------------------------------------------------------------------------- station report
def station_report(data, forecasts, *, generated=None):
    station = data['station']
    offset = station.get('utc_offset_hours', -4)
    report = {'schema_version': 1, 'generated_at_utc': generated or now(), 'station': {k: v for k, v in station.items() if k != 'files'},
              'forecast_point': forecasts.get('point'), 'leads_days': forecasts.get('leads', list(LEADS)),
              'observations': {'period': data['period'], 'hourly_rows': len(data['hourly']), 'daily_rows': len(data['daily']), 'qc': data['qc'], 'sources': data['sources'],
                               'daily': [{k: d.get(k) for k in ('date', 't_max', 't_min', 't_mean', 'rain_mm', 'rain_hours', 'rain_partial_mm', 'rh_min', 'rh_max', 'gust_max_kmh', 'wind_mean_kmh', 'radiation_mj', 'et0_mm')}
                                         for d in data['daily']]},
              'models': {m: {k: v for k, v in s.items() if k != 'hourly'} for m, s in forecasts.get('models', {}).items()},
              'verification': [], 'series': {}, 'limitations': [
                  'Previsões do Previous Runs API: antecedência nominal de N dias (24N a 24N+23 h); grade ~9–25 km interpolada pelo provedor.',
                  'Extremos diários do modelo vêm de valores horários instantâneos; a estação mede extremos dentro de cada hora (diferença sistemática esperada).',
                  'Rajada do modelo é a máxima da hora na grade; a estação mede rajada de 3 s no ponto.',
                  'Correções recomendadas foram validadas fora da amostra em ~6 meses de uma estação; não há garantia de estabilidade em outras estações do ano.',
                  'Percentuais e acertos de chuva usam limiares fixos (0,2 mm úmido; 1 e 10 mm nas tabelas de contingência).']}
    if forecasts.get('point', {}).get('source') == 'municipal_reference_point':
        report['limitations'].insert(0, 'Coordenadas da estação não informadas: previsão consultada no ponto de referência municipal; comparação aproximada.')
    if station.get('latitude') is not None and forecasts.get('point'):
        report['station_to_forecast_point_km'] = round(haversine(station, forecasts['point']), 2)
    reference_model = None
    for model, state in forecasts.get('models', {}).items():
        if state.get('state') not in ('ok', 'partial') or not state.get('hourly'):
            continue
        for lead, fc_hourly in state['hourly'].items():
            lead = int(lead)
            fc_daily = aggregate_local_days(fc_hourly, offset, extremes_from_hourly=True)
            if data['hourly']:
                for variable, methods in HOURLY_TARGETS.items():
                    pairs = pair_hourly(data['hourly'], fc_hourly, variable, offset)
                    item = evaluate_group(pairs, kind='hourly', lead_days=lead, variable=variable, methods=methods)
                    entry = {'model': model, 'lead_days': lead, 'variable': variable, 'kind': 'hourly', **item}
                    if lead == 1 and pairs:
                        entry['diagnostics'] = diagnostics_hourly(pairs)
                    report['verification'].append(entry)
            for field, methods in DAILY_TARGETS.items():
                if field in ('wind_mean_kmh', 'gust_max_kmh') and data['hourly']:
                    continue  # hourly wind already evaluated; daily wind only for daily-only stations
                pairs = pair_daily(data['daily'], fc_daily, field)
                if not pairs:
                    continue
                item = evaluate_group(pairs, kind='daily', lead_days=lead, variable=field, methods=methods)
                report['verification'].append({'model': model, 'lead_days': lead, 'variable': field, 'kind': 'daily', **item})
            if lead == 1:
                by_date = {d['date']: d for d in fc_daily}
                series = {'dates': [], 'obs_t_max': [], 'fc_t_max': [], 'obs_t_min': [], 'fc_t_min': [], 'obs_rain_mm': [], 'fc_rain_mm': []}
                for d in data['daily']:
                    f = by_date.get(d['date'])
                    if not f:
                        continue
                    series['dates'].append(d['date'])
                    for key in ('t_max', 't_min', 'rain_mm'):
                        series[f'obs_{key}'].append(d.get(key)); series[f'fc_{key}'].append(f.get(key))
                report['series'][model] = {'lead_days': 1, **series}
    # Headline: best raw MAE per daily target at D1 across models, plus recommendations count.
    headline = {}
    for field in ('t_max', 't_min', 'rain_mm'):
        candidates = [v for v in report['verification'] if v['variable'] == field and v['lead_days'] == 1 and v.get('raw_all_pairs')]
        if candidates:
            best = min(candidates, key=lambda v: v['raw_all_pairs']['mae'])
            headline[field] = {'model': best['model'], 'mae_raw': best['raw_all_pairs']['mae'], 'bias_raw': best['raw_all_pairs']['bias'], 'n': best['raw_all_pairs']['n'],
                               'recommended': (best.get('recommended') or {}).get('method')}
    report['headline'] = headline
    report['recommendations'] = sum(1 for v in report['verification'] if v.get('recommended'))
    report['groups_evaluated'] = sum(1 for v in report['verification'] if v.get('status') == 'evaluated')
    report['dataset_sha256'] = digest(packed([data['period'], len(data['hourly']), len(data['daily']), sorted(forecasts.get('models', {}))]))
    return report


def write_reports(reports, output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    index = {'schema_version': 1, 'generated_at_utc': now(), 'stations': []}
    for report in reports:
        slug = report['station']['slug']
        write_json(output_dir / f'{slug}.json', report)
        daily = [d for d in report['observations']['daily'] if d.get('t_max') is not None or d.get('rain_mm') is not None]
        recent = [{k: d.get(k) for k in ('date', 't_max', 't_min', 'rain_mm')} for d in daily[-7:]]
        check = None
        reference = (report['headline'].get('rain_mm') or report['headline'].get('t_max') or {}).get('model')
        series = report['series'].get(reference) if reference else None
        if series:
            for i in range(len(series['dates']) - 1, -1, -1):
                if series['obs_rain_mm'][i] is not None and series['fc_rain_mm'][i] is not None:
                    check = {'date': series['dates'][i], 'model': reference, 'obs_rain_mm': series['obs_rain_mm'][i], 'fc_rain_mm': round(series['fc_rain_mm'][i], 1),
                             'obs_t_max': series['obs_t_max'][i], 'fc_t_max': round(series['fc_t_max'][i], 1) if series['fc_t_max'][i] is not None else None}
                    break
        index['stations'].append({'recent': recent, 'yesterday_check': check,'id': report['station']['id'], 'slug': slug, 'name': report['station']['name'], 'location_id': report['station']['location_id'],
                                  'file': f'{slug}.json', 'period': report['observations']['period'], 'daily_rows': report['observations']['daily_rows'],
                                  'models': {m: s.get('state') for m, s in report['models'].items()}, 'headline': report['headline'],
                                  'recommendations': report['recommendations'], 'groups_evaluated': report['groups_evaluated'],
                                  'forecast_point': report['forecast_point'], 'state': 'ok' if report['groups_evaluated'] else 'observations_only'})
    write_json(output_dir / 'index.json', index)
    return index


def run(*, fetch=False, fixture=None, output_dir='site/data/stations', runtime='runtime', models=None, stations=None, root='.', asof=None):
    """Build all station reports. ``fixture`` (offline) maps station id → {model: {lead: payload}}."""
    models = tuple(models or (os.environ.get('STATION_MODELS', '').split(',') if os.environ.get('STATION_MODELS') else DEFAULT_MODELS))
    models = tuple(m.strip() for m in models if m.strip())
    fixture_data = json.loads(Path(fixture).read_text(encoding='utf-8')) if fixture else None
    reports = []
    for entry in registry(Path(root) / 'data/stations/stations.json'):
        if stations and entry['id'] not in stations and entry['slug'] not in stations:
            continue
        data = load_station(entry, root, asof=asof)
        forecasts = {'point': forecast_point(entry), 'models': {}, 'leads': list(LEADS)}
        if fixture_data is not None:
            for model, per_lead in (fixture_data.get(entry['id']) or {}).items():
                forecasts['models'][model] = {'state': 'ok', 'blocks': 1, 'errors': [], 'variables': list(CORE_VARIABLES),
                                              'hourly': {int(n): payload_to_records(payload, (int(n),))[int(n)] for n, payload in per_lead.items()}}
        elif fetch and data['period']:
            from .capture import Capture
            from .http import FreeClient
            directory = Path(runtime) / 'imports' / now().replace(':', '').replace('+', '') / entry['location_id'] / 'stations' / entry['slug']
            cap = Capture(directory, entry['location_id'])
            client = FreeClient(Path(runtime) / 'http_cache', cap)
            try:
                forecasts = fetch_station_forecasts(client, entry, data['period'][0], data['period'][1], models=models)
            finally:
                cap.finish()
        forecasts = add_multimodel_mean(forecasts)
        reports.append(station_report(data, forecasts))
    return write_reports(reports, output_dir), reports
