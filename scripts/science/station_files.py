"""Physical station files supplied to the project: parsing, conservative QC and local-day aggregation.

Formats
- ``inmet_portal_hourly``: CSV exported from https://tempo.inmet.gov.br/TabelaEstacoes/<code>
  (semicolon separated, decimal comma, hour labels in UTC). For accumulations and hourly
  extremes the label ``HH00`` covers the hour ending at that label; instantaneous values
  are valid at the label.
- ``embrapa_guiaclima_daily``: HTML table saved as ``.xls`` by Embrapa Guia Clima (daily values
  for the local calendar day; wind measured at 2 m).

Rules
- Missing is never zero: empty cells, ``-9999`` and unreadable numbers become ``None``.
- QC only flags; raw values are preserved and nothing is interpolated or corrected.
- Daily aggregates follow the project's local-day convention (UTC−4): instantaneous
  variables use the labels whose local time falls in [00:00, 24:00); accumulations and
  hourly extremes use the hour-ending labels 01:00..24:00 local.
"""
from __future__ import annotations
import collections
import csv
import datetime as dt
import gzip
import io
import math
import re
import unicodedata
from pathlib import Path

HOURLY_FIELDS = ('temperature_2m', 'temperature_hour_max', 'temperature_hour_min', 'relative_humidity_2m',
                 'rh_hour_max', 'rh_hour_min', 'dew_point_2m', 'surface_pressure', 'wind_speed_10m',
                 'wind_direction_10m', 'wind_gusts_10m', 'shortwave_radiation', 'precipitation')
# Conservative physical screening for lowland stations of central/southern Brazil (not sensor certification).
BOUNDS = {'temperature_2m': (-10, 48), 'temperature_hour_max': (-10, 48), 'temperature_hour_min': (-10, 48),
          'relative_humidity_2m': (1, 100), 'rh_hour_max': (1, 100), 'rh_hour_min': (1, 100), 'dew_point_2m': (-20, 35),
          'surface_pressure': (850, 1050), 'wind_speed_10m': (0, 144), 'wind_direction_10m': (0, 360),
          'wind_gusts_10m': (0, 216), 'shortwave_radiation': (0, 1500), 'precipitation': (0, 120)}
INMET_COLUMNS = (('TEMP. INS.', 'temperature_2m', 1), ('TEMP. MAX.', 'temperature_hour_max', 1), ('TEMP. MIN.', 'temperature_hour_min', 1),
                 ('UMI. INS.', 'relative_humidity_2m', 1), ('UMI. MAX.', 'rh_hour_max', 1), ('UMI. MIN.', 'rh_hour_min', 1),
                 ('PTO ORVALHO INS.', 'dew_point_2m', 1), ('PRESSAO INS.', 'surface_pressure', 1),
                 ('VEL. VENTO', 'wind_speed_10m', 3.6), ('DIR. VENTO', 'wind_direction_10m', 1), ('RAJ. VENTO', 'wind_gusts_10m', 3.6),
                 ('RADIACAO', 'shortwave_radiation', 1000 / 3600), ('CHUVA', 'precipitation', 1))
MIN_HOURS_DAILY = 20          # instantaneous means and extremes need 20 of 24 hours
FLATLINE_TEMPERATURE = 6      # identical consecutive values (0.1 °C resolution) before flagging a stuck sensor
FLATLINE_WIND = 12
STEP_TEMPERATURE = 8.0        # °C between consecutive hours
FAO56_2M_TO_10M = 1 / 0.748   # FAO-56 log profile factor: u2 = 0.748 * u10 for a 10 m reference


def plain(text):
    return ''.join(c for c in unicodedata.normalize('NFD', str(text).upper()) if unicodedata.category(c) != 'Mn')


def read_text(path):
    path = Path(path)
    raw = path.read_bytes()
    if path.suffix == '.gz':
        raw = gzip.decompress(raw)
    try:
        return raw.decode('utf-8-sig')
    except UnicodeDecodeError:
        return raw.decode('latin1')


def number(raw):
    text = str(raw if raw is not None else '').strip()
    if text in ('', '-', '—', 'null', 'NULL', 'NaN', '-9999', '-9999,0', '-9999.0'):
        return None
    try:
        value = float(text.replace(',', '.'))
    except ValueError:
        return None
    return value if math.isfinite(value) and value > -9000 else None


def parse_inmet_portal_hourly(text):
    """Hourly UTC records with canonical units (km/h for wind, W/m² hour mean for radiation)."""
    lines = text.splitlines()
    header = next((i for i, line in enumerate(lines) if plain(line).replace('"', '').startswith('DATA;HORA')), None)
    if header is None:
        raise ValueError('Cabeçalho "Data";"Hora (UTC)" do portal INMET ausente')
    reader = csv.DictReader(io.StringIO('\n'.join(lines[header:])), delimiter=';')
    columns = {plain(k): k for k in (reader.fieldnames or []) if k}
    date_key = next((v for k, v in columns.items() if k.startswith('DATA')), None)
    hour_key = next((v for k, v in columns.items() if k.startswith('HORA')), None)
    if not date_key or not hour_key:
        raise ValueError('Colunas de data/hora ausentes')
    mapping = []
    for prefix, field, factor in INMET_COLUMNS:
        key = next((v for k, v in columns.items() if k.startswith(prefix)), None)
        if key:
            mapping.append((key, field, factor))
    records, seen = [], set()
    for row in reader:
        day, hour = (row.get(date_key) or '').strip(), (row.get(hour_key) or '').strip().replace(' UTC', '').replace(':', '')
        if not day or not hour:
            continue
        try:
            stamp = dt.datetime.strptime(f'{day} {hour.zfill(4)}', '%d/%m/%Y %H%M').replace(tzinfo=dt.timezone.utc)
        except ValueError as exc:
            raise ValueError(f'Data/hora inválida no arquivo INMET: {day} {hour}') from exc
        iso = stamp.isoformat(timespec='seconds')
        if iso in seen:
            raise ValueError(f'Data/hora duplicada no arquivo INMET: {iso}')
        seen.add(iso)
        record = {'valid_at_utc': iso}
        for key, field, factor in mapping:
            value = number(row.get(key))
            record[field] = None if value is None else round(value * factor, 3)
        for field in HOURLY_FIELDS:
            record.setdefault(field, None)
        records.append(record)
    if not records:
        raise ValueError('Arquivo INMET sem registros horários')
    records.sort(key=lambda r: r['valid_at_utc'])
    return records


def qc_hourly(records):
    """Attach ``qc`` (flag per variable) and ``clean`` (value or None) to each record; return a summary."""
    counts = collections.defaultdict(collections.Counter)
    out = []
    for record in records:
        flags = {}
        for field in HOURLY_FIELDS:
            value = record.get(field)
            low, high = BOUNDS[field]
            flags[field] = 'missing' if value is None else ('valid' if low <= value <= high else 'out_of_range')
        t, tmax, tmin = record.get('temperature_2m'), record.get('temperature_hour_max'), record.get('temperature_hour_min')
        if all(flags[k] == 'valid' for k in ('temperature_2m', 'temperature_hour_max', 'temperature_hour_min')):
            if not (tmin - 0.3 <= t <= tmax + 0.3) or tmin > tmax + 0.3:
                for k in ('temperature_2m', 'temperature_hour_max', 'temperature_hour_min'):
                    flags[k] = 'inconsistent_extremes'
        rh, rhmax, rhmin = record.get('relative_humidity_2m'), record.get('rh_hour_max'), record.get('rh_hour_min')
        if all(flags[k] == 'valid' for k in ('relative_humidity_2m', 'rh_hour_max', 'rh_hour_min')):
            if not (rhmin - 1 <= rh <= rhmax + 1) or rhmin > rhmax + 1:
                for k in ('relative_humidity_2m', 'rh_hour_max', 'rh_hour_min'):
                    flags[k] = 'inconsistent_extremes'
        if flags['wind_gusts_10m'] == 'valid' and flags['wind_speed_10m'] == 'valid' and record['wind_gusts_10m'] < record['wind_speed_10m'] - 0.5:
            flags['wind_gusts_10m'] = 'gust_below_speed'
        if flags['dew_point_2m'] == 'valid' and flags['temperature_2m'] == 'valid' and record['dew_point_2m'] > record['temperature_2m'] + 0.5:
            flags['dew_point_2m'] = 'dew_above_temperature'
        out.append({**record, 'qc': flags})
    # Temporal tests need the neighbours: step and flat-line on temperature, flat-line on wind speed.
    for i in range(1, len(out)):
        a, b = out[i - 1], out[i]
        if a['qc']['temperature_2m'] == 'valid' and b['qc']['temperature_2m'] == 'valid':
            gap = (dt.datetime.fromisoformat(b['valid_at_utc']) - dt.datetime.fromisoformat(a['valid_at_utc'])).total_seconds()
            if gap == 3600 and abs(b['temperature_2m'] - a['temperature_2m']) > STEP_TEMPERATURE:
                b['qc']['temperature_2m'] = 'step'
    for field, limit, nonzero in (('temperature_2m', FLATLINE_TEMPERATURE, False), ('wind_speed_10m', FLATLINE_WIND, True)):
        run_start = 0
        for i in range(1, len(out) + 1):
            same = i < len(out) and out[i]['qc'][field] == 'valid' and out[run_start]['qc'][field] == 'valid' \
                and out[i][field] == out[run_start][field] and (not nonzero or out[i][field] > 0)
            if not same:
                if i - run_start >= limit and out[run_start]['qc'][field] == 'valid' and (not nonzero or out[run_start][field] > 0):
                    for j in range(run_start, i):
                        out[j]['qc'][field] = 'flatline'
                run_start = i
    for record in out:
        record['clean'] = {field: (record[field] if record['qc'][field] == 'valid' else None) for field in HOURLY_FIELDS}
        for field in HOURLY_FIELDS:
            counts[field][record['qc'][field]] += 1
    summary = {field: dict(counter) for field, counter in counts.items()}
    summary['rows'] = len(out)
    summary['fully_missing_rows'] = sum(1 for r in out if all(r[f] is None for f in HOURLY_FIELDS))
    return out, summary


def local_day(iso_utc, offset_hours, *, hour_ending=False):
    stamp = dt.datetime.fromisoformat(iso_utc) + dt.timedelta(hours=offset_hours)
    if hour_ending:
        stamp -= dt.timedelta(seconds=1)
    return stamp.date().isoformat()


def _mean(values):
    return sum(values) / len(values) if values else None


def aggregate_local_days(records, offset_hours=-4, *, extremes_from_hourly=False):
    """Daily values per local day from QC'd hourly records (``clean`` values only)."""
    inst, ending = collections.defaultdict(list), collections.defaultdict(list)
    for r in records:
        inst[local_day(r['valid_at_utc'], offset_hours)].append(r['clean'])
        ending[local_day(r['valid_at_utc'], offset_hours, hour_ending=True)].append(r['clean'])
    out = []
    for day in sorted(set(inst) | set(ending)):
        a, b = inst.get(day, []), ending.get(day, [])
        pick = lambda rows, key: [x[key] for x in rows if x.get(key) is not None]
        t, tmax, tmin = pick(a, 'temperature_2m'), pick(b, 'temperature_hour_max'), pick(b, 'temperature_hour_min')
        if extremes_from_hourly:
            tmax, tmin = pick(a, 'temperature_2m'), pick(a, 'temperature_2m')
        rh, rhmax, rhmin = pick(a, 'relative_humidity_2m'), pick(b, 'rh_hour_max'), pick(b, 'rh_hour_min')
        if extremes_from_hourly:
            rhmax, rhmin = pick(a, 'relative_humidity_2m'), pick(a, 'relative_humidity_2m')
        wind, gust, rain, rad = pick(a, 'wind_speed_10m'), pick(b, 'wind_gusts_10m'), pick(b, 'precipitation'), pick(b, 'shortwave_radiation')
        et0 = pick(b, 'et0_fao_evapotranspiration')
        enough = lambda values: len(values) >= MIN_HOURS_DAILY
        out.append({'date': day, 'hours_in_file': len(a),
                    'et0_mm': round(sum(et0), 2) if len(et0) == 24 else None,
                    't_mean': round(_mean(t), 2) if enough(t) else None, 't_hours': len(t),
                    't_max': round(max(tmax), 1) if enough(tmax) else None, 't_min': round(min(tmin), 1) if enough(tmin) else None,
                    'rh_mean': round(_mean(rh), 1) if enough(rh) else None,
                    'rh_max': round(max(rhmax), 1) if enough(rhmax) else None, 'rh_min': round(min(rhmin), 1) if enough(rhmin) else None,
                    'wind_mean_kmh': round(_mean(wind), 2) if enough(wind) else None,
                    'gust_max_kmh': round(max(gust), 1) if enough(gust) else None,
                    'rain_mm': round(sum(rain), 2) if len(rain) == 24 else None, 'rain_hours': len(rain),
                    'rain_partial_mm': round(sum(rain), 2) if rain else None,
                    'radiation_mj': round(sum(rad) * 3600 / 1e6, 2) if len(rad) == 24 else None})
    return out


def parse_embrapa_daily(text, *, asof=None):
    """Daily local-day values from the Guia Clima export (reuses the audited table parser)."""
    from scripts.sources.embrapa_export import parse_export
    parsed = parse_export(text, asof=asof)
    out = []
    for r in parsed['records']:
        row = {'date': r['date'], 't_mean': r['temperature_mean_c'], 't_max': r['temperature_max_c'], 't_min': r['temperature_min_c'],
               'rh_mean': r['relative_humidity_mean_pct'], 'rh_max': r['relative_humidity_max_pct'], 'rh_min': r['relative_humidity_min_pct'],
               'wind2m_mean_ms': r['wind_mean_m_s'], 'gust2m_max_ms': r['wind_max_m_s'], 'wind_direction_label': r['wind_dir_text'],
               'rain_mm': r['precipitation_mm'], 'radiation_mj': r['solar_radiation_mj_m2_day'], 'et0_mm': r['et0_mm_day']}
        row['wind_mean_kmh'] = round(r['wind_mean_m_s'] * 3.6 * FAO56_2M_TO_10M, 2) if r['wind_mean_m_s'] is not None else None
        row['wind_mean_kmh_note'] = 'estimado de 2 m para 10 m (FAO-56)'
        out.append(row)
    return out, {'rows': len(out), 'date_first': parsed['date_first'], 'date_last': parsed['date_last'],
                 'missing_calendar_days': parsed['missing_calendar_days']}


def qc_daily(rows):
    """Flag daily rows (ranges and ordering); ``clean`` mirrors the hourly convention."""
    limits = {'t_mean': (-10, 45), 't_max': (-5, 48), 't_min': (-10, 40), 'rh_mean': (1, 100), 'rh_max': (1, 100), 'rh_min': (1, 100),
              'wind_mean_kmh': (0, 100), 'rain_mm': (0, 400), 'radiation_mj': (0, 40), 'et0_mm': (0, 15), 'gust_max_kmh': (0, 216)}
    counts = collections.defaultdict(collections.Counter)
    for row in rows:
        flags = {}
        for key, (low, high) in limits.items():
            value = row.get(key)
            if key not in row:
                continue
            flags[key] = 'missing' if value is None else ('valid' if low <= value <= high else 'out_of_range')
        if all(flags.get(k) == 'valid' for k in ('t_mean', 't_max', 't_min')) and not (row['t_min'] - 0.3 <= row['t_mean'] <= row['t_max'] + 0.3):
            for k in ('t_mean', 't_max', 't_min'):
                flags[k] = 'inconsistent_extremes'
        if all(flags.get(k) == 'valid' for k in ('rh_mean', 'rh_max', 'rh_min')) and not (row['rh_min'] - 1 <= row['rh_mean'] <= row['rh_max'] + 1):
            for k in ('rh_mean', 'rh_max', 'rh_min'):
                flags[k] = 'inconsistent_extremes'
        row['qc'] = flags
        row['clean'] = {k: (row[k] if flags.get(k) == 'valid' else None) for k in flags}
        for k, v in flags.items():
            counts[k][v] += 1
    summary = {k: dict(c) for k, c in counts.items()}
    summary['rows'] = len(rows)
    return rows, summary


def load_station(entry, root='.', *, asof=None):
    """Observations for one station of ``data/stations/stations.json``: hourly (if any), daily, QC summary."""
    root = Path(root)
    hourly, daily, qc = [], [], {}
    sources = []
    for file in entry['files']:
        path = root / file['path']
        text = read_text(path)
        if file['format'] == 'inmet_portal_hourly':
            records, summary = qc_hourly(parse_inmet_portal_hourly(text))
            hourly.extend(records)
            qc['hourly'] = summary
        elif file['format'] == 'embrapa_guiaclima_daily':
            rows, summary = parse_embrapa_daily(text, asof=asof)
            rows, qc_summary = qc_daily(rows)
            daily.extend(rows)
            qc['daily'] = {**summary, **qc_summary}
        else:
            raise ValueError(f'Formato de arquivo de estação não suportado: {file["format"]}')
        sources.append({'path': file['path'], 'format': file['format'], 'original_sha256': file.get('original_sha256')})
    if hourly:
        hourly.sort(key=lambda r: r['valid_at_utc'])
        stamps = [r['valid_at_utc'] for r in hourly]
        if len(stamps) != len(set(stamps)):
            raise ValueError(f'{entry["id"]}: a mesma hora aparece em mais de um arquivo; revisar os períodos em stations.json')
        daily, _ = qc_daily(aggregate_local_days(hourly, entry.get('utc_offset_hours', -4)))
    period = [daily[0]['date'], daily[-1]['date']] if daily else None
    return {'station': entry, 'hourly': hourly, 'daily': daily, 'qc': qc, 'period': period, 'sources': sources}


def registry(path='data/stations/stations.json'):
    import json
    return json.loads(Path(path).read_text(encoding='utf-8'))['stations']
