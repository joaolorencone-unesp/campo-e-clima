"""Verify full rain windows from archived forecasts available before the window."""
from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
import gzip
from itertools import groupby
from math import fsum
from zoneinfo import ZoneInfo
from zlib import error as CompressionError

from .common import ROOT, digest, finite, haversine, instant, iso
from .metrics import deterministic, events
from .station_files import load_station, registry

HOUR = timedelta(hours=1)
DURATIONS = (3, 24)
LEAD_LIMITS = (24, 48, 72)
THRESHOLD_MM = 1


def observation_hour(row):
    """Return the start of an explicitly documented, complete hourly interval."""
    if not finite(row['value']) or row['value'] < 0:
        return None
    try:
        start = instant(row['interval_start_utc'])
        end = instant(row['interval_end_utc'])
        valid = instant(row['valid_at_utc'])
    except (TypeError, ValueError):
        return None
    if valid == end and end - start == HOUR and not (start.minute or start.second or start.microsecond):
        return start
    return None


def file_observations(root):
    """Read versioned INMET exports as references without importing into SQLite."""
    entries = registry(root / 'data/stations/stations.json')
    unavailable = []
    loaded = []
    for station in entries:
        if station['identity_status'] != 'catalog_verified' or not station['id'].startswith('INMET:'):
            continue
        try:
            for file in station['files']:
                path = root / file['path']
                raw = path.read_bytes()
                if path.suffix == '.gz':
                    raw = gzip.decompress(raw)
                if file['format'] != 'inmet_portal_hourly' or digest(raw) != file['original_sha256']:
                    raise ValueError('Formato ou SHA-256 de estação divergente')
            loaded.append(load_station(station, root))
        except (OSError, EOFError, CompressionError, TypeError, ValueError, KeyError):
            unavailable.append(station['id'])
    return loaded, unavailable


def observed_windows(con, locations, root):
    stations = {}
    hourly = defaultdict(lambda: defaultdict(set))
    for row in con.execute("""SELECT o.*, s.latitude, s.longitude FROM observations o
        JOIN observing_stations s ON s.id=o.station_id WHERE o.variable='precipitation'
        AND o.unit='mm' AND o.qc='valid' AND o.reference_quality='observed_basic_qc'"""):
        start = observation_hour(row)
        if start is not None:
            key = (row['location_id'], row['station_id'])
            stations[key] = {'latitude': row['latitude'], 'longitude': row['longitude']}
            hourly[key][start].add(row['value'])

    sources, unavailable = file_observations(root)
    for source in sources:
        station = source['station']
        key = (station['location_id'], station['id'])
        # Never merge references if coordinates disagree materially for the same ID.
        if key in stations and haversine(stations[key], station) > 1:
            unavailable.append(station['id'])
            continue
        stations[key] = station
        for row in source['hourly']:
            value = row['clean']['precipitation']
            end = instant(row['valid_at_utc'])
            if finite(value) and end == end.replace(minute=0, second=0, microsecond=0):
                hourly[key][end - HOUR].add(value)

    windows = defaultdict(lambda: defaultdict(list))
    for (loc, station_id), values in hourly.items():
        if loc not in locations:
            continue
        station = stations[loc, station_id]
        distance = haversine(locations[loc], station)
        if distance > 50:
            continue
        timezone = ZoneInfo(locations[loc]['timezone'])
        for start in sorted(values):
            local = start.astimezone(timezone).replace(tzinfo=None)
            for duration in DURATIONS:
                end = start + duration * HOUR
                # Local non-overlapping intervals; exclude ambiguous 23/25 h days.
                if local.minute or local.hour % duration or end.astimezone(timezone).replace(tzinfo=None) != local + duration * HOUR:
                    continue
                hours = [values.get(start + step * HOUR, ()) for step in range(duration)]
                if all(len(value) == 1 for value in hours):
                    observed = fsum(next(iter(value)) for value in hours)
                    windows[loc][start].append((station_id, station, distance, duration, observed))
    return windows, sorted(set(unavailable))


def forecast_pairs(con, location_id, windows):
    """Retain the most recently acquired complete run per lead bucket and interval."""
    if not windows:
        return {}
    rows = con.execute("""SELECT v.*, r.id AS canonical_id, r.model_id, r.available_at_utc,
        r.collected_at_utc, r.grid_latitude AS latitude, r.grid_longitude AS longitude
        FROM forecast_values v JOIN forecast_run_keys k ON k.run_key=v.run_id
        JOIN forecast_runs r ON r.id=k.run_id
        WHERE v.variable='precipitation' AND v.unit='mm' AND v.qc='valid'
        AND v.valid_at_utc BETWEEN ? AND ? AND r.location_id=?
        AND r.product='operational' AND r.available_at_utc IS NOT NULL
        AND r.source_url='https://api.open-meteo.com/v1/forecast'
        AND r.grid_latitude IS NOT NULL AND r.grid_longitude IS NOT NULL
        ORDER BY v.run_id, v.valid_at_utc""",
        (iso(min(windows) + HOUR), iso(max(windows) + max(DURATIONS) * HOUR), location_id))
    pairs = {}
    for _, run_rows in groupby(rows, key=lambda row: row['run_id']):
        values = {}
        for row in run_rows:
            run = dict(row)
            start = observation_hour(row)
            if start is not None:
                values[start] = row['value']
        available = max(instant(run['available_at_utc']), instant(run['collected_at_utc']))
        rank = (available, run['canonical_id'])
        for start in values.keys() & windows.keys():
            lead = (start - available) / HOUR
            if not 0 < lead <= LEAD_LIMITS[-1]:
                continue
            lead_max = next(limit for limit in LEAD_LIMITS if lead <= limit)
            for station_id, station, distance, duration, observed in windows[start]:
                key = (station_id, run['model_id'], duration, lead_max, start)
                if key in pairs and rank <= pairs[key][0]:
                    continue
                if haversine(run, station) > 75:
                    continue
                forecast = [values.get(start + step * HOUR) for step in range(duration)]
                if all(value is not None for value in forecast):
                    pairs[key] = (rank, fsum(forecast), observed, distance)
    return pairs


def report(con, *, root=ROOT):
    locations = {row['id']: dict(row) for row in con.execute('SELECT * FROM locations')}
    observations, unavailable = observed_windows(con, locations, root)
    results = []
    for loc, windows in sorted(observations.items()):
        pairs = forecast_pairs(con, loc, windows)
        for group, rows in groupby(sorted(pairs), key=lambda key: key[:-1]):
            station, model, duration, lead_max = group
            keys = list(rows)
            sample = [pairs[key] for key in keys]
            forecast = [row[1] for row in sample]
            observed = [row[2] for row in sample]
            metrics = deterministic(forecast, observed)
            counts = events([int(value > THRESHOLD_MM) for value in forecast],
                            [int(value > THRESHOLD_MM) for value in observed])
            results.append({'location_id': loc, 'station_id': station, 'model': model,
                            'duration_hours': duration, 'lead_max_hours': lead_max,
                            'start_utc': iso(keys[0][-1]), 'end_utc': iso(keys[-1][-1] + duration * HOUR),
                            'distance_km': round(sample[0][3], 1), 'n': len(sample),
                            'mae_mm': metrics['mae'], 'bias_mm': metrics['bias'],
                            'hits': counts['hits'], 'misses': counts['misses'], 'false_alarms': counts['false_alarms']})
    return {'threshold_mm': THRESHOLD_MM, 'results': results, 'station_files_unavailable': unavailable,
            'calibration_validated': False}
