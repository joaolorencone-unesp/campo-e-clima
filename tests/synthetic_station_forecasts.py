"""Synthetic forecast payloads for station tests (never real weather, never published).

Builds Previous-Runs-like payloads from the station's own observations plus a known bias and
noise, so the calibration pipeline can be checked for recovering that bias out of sample.
"""
from __future__ import annotations
import datetime as dt
import math
import random


def _hourly_from_daily(daily, offset_hours):
    """A smooth diurnal cycle for daily-only stations (test scaffolding only)."""
    rows = []
    for d in daily:
        tmax, tmin, rain = d.get('t_max'), d.get('t_min'), d.get('rain_mm')
        if tmax is None or tmin is None:
            continue
        day = dt.datetime.fromisoformat(d['date'] + 'T00:00:00')
        for h in range(24):
            local = day + dt.timedelta(hours=h)
            utc = (local - dt.timedelta(hours=offset_hours)).replace(tzinfo=dt.timezone.utc)
            temp = tmin + (tmax - tmin) * (0.5 - 0.5 * math.cos(2 * math.pi * ((h - 5) % 24) / 24))
            rows.append({'valid_at_utc': utc.isoformat(timespec='seconds'), 'clean': {
                'temperature_2m': temp, 'relative_humidity_2m': max(20, min(100, 100 - 2.5 * (temp - tmin))),
                'precipitation': (rain or 0) / 4 if h in (15, 16, 17, 18) else 0.0,
                'wind_speed_10m': (d.get('wind_mean_kmh') or 8), 'wind_gusts_10m': (d.get('wind_mean_kmh') or 8) * 2.2,
                'shortwave_radiation': max(0, 800 * math.sin(math.pi * (h - 6) / 12)) if 6 <= h <= 18 else 0.0,
                'et0_fao_evapotranspiration': ((d.get('et0_mm') or 3) / 12) if 6 <= h <= 18 else 0.0}})
    return rows


def build_fixture(data, *, models=('modelo_a', 'modelo_b'), leads=(1, 2, 3, 7), bias=None, seed=7):
    """{model: {lead: payload}} with per-model additive/multiplicative distortions."""
    rng = random.Random(seed)
    bias = bias or {'modelo_a': {'temperature_2m': 1.8, 'precipitation': 1.35, 'wind_speed_10m': 1.4}, 'modelo_b': {'temperature_2m': -0.6, 'precipitation': 0.8, 'wind_speed_10m': 1.0}}
    offset = data['station'].get('utc_offset_hours', -4)
    base = data['hourly'] or _hourly_from_daily(data['daily'], offset)
    out = {}
    last = {}
    for model in models:
        b = bias.get(model, {})
        out[model] = {}
        for lead in leads:
            noise_scale = 1 + 0.35 * (lead - 1)
            times, columns = [], {k: [] for k in ('temperature_2m', 'relative_humidity_2m', 'precipitation', 'wind_speed_10m', 'wind_gusts_10m', 'shortwave_radiation', 'et0_fao_evapotranspiration')}
            for row in base:
                clean = row['clean']
                stamp = int(dt.datetime.fromisoformat(row['valid_at_utc']).timestamp())
                times.append(stamp)
                for key in columns:
                    value = clean.get(key)
                    if value is None:
                        value = last.get(key, 20.0 if key == 'temperature_2m' else 0.0)
                    last[key] = value
                    if key == 'temperature_2m':
                        value = value + b.get(key, 0) + rng.gauss(0, 1.2 * noise_scale)
                    elif key == 'relative_humidity_2m':
                        value = min(100, max(0, value + rng.gauss(0, 6 * noise_scale)))
                    elif key == 'precipitation':
                        value = max(0.0, value * b.get(key, 1) * (1 + rng.gauss(0, 0.3 * noise_scale)) + (0.15 if rng.random() < 0.03 * noise_scale else 0.0))
                    elif key in ('wind_speed_10m', 'wind_gusts_10m'):
                        value = max(0.0, value * b.get('wind_speed_10m', 1) + rng.gauss(0, 2 * noise_scale))
                    else:
                        value = max(0.0, value * (1 + rng.gauss(0, 0.1 * noise_scale)))
                    columns[key].append(round(value, 3))
            hourly = {'time': times}
            for key, values in columns.items():
                hourly[f'{key}_previous_day{lead}'] = values
            out[model][str(lead)] = {'latitude': data['station'].get('latitude') or -23.0, 'longitude': data['station'].get('longitude') or -54.0, 'elevation': 320,
                                     'timezone': 'GMT', 'hourly': hourly}
    return out
