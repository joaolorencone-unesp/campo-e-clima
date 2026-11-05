"""CEMADEN automatic rain gauges (public national network) near a point: last 24 h totals.

Free public service (Centro Nacional de Monitoramento e Alertas de Desastres Naturais).
Endpoints are the ones used by CEMADEN's own data platform; their formats are not formally
documented, so both parsers are tolerant and every failure is reported, never hidden.
Disabled unless ``CEMADEN_ENABLE=1`` (offline tests and local runs stay network-free). The
service answers HTTP 400 "O parâmetro token não pode ser vazio" without a token (confirmed
05/11/2026): CEMADEN issues tokens free of charge on request; set ``CEMADEN_TOKEN`` as a secret.
"""
from __future__ import annotations
import csv
import datetime as dt
import io
import json
import math
import os
from typing import Any
import requests

BASE = 'https://sws.cemaden.gov.br/PED/rest'
SOURCE_URL = 'https://mapainterativo.cemaden.gov.br/'
UF_BY_LOCATION = {'navirai': 'MS', 'diamantino': 'MT'}


def _num(v):
    try:
        x = float(str(v).replace(',', '.'))
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) else None


def haversine_km(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(math.radians, (lat1, lon1, lat2, lon2))
    a = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 6371.0088 * 2 * math.asin(min(1, math.sqrt(a)))


def parse_stations(payload: Any, lat: float, lon: float, *, radius_km: float = 80) -> list[dict]:
    """Gauges within ``radius_km``; accepts a JSON list or {'estacoes': [...]} with CEMADEN field names."""
    rows = payload.get('estacoes') if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise ValueError('Catálogo CEMADEN não é uma lista')
    out = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        la, lo = _num(r.get('latitude')), _num(r.get('longitude'))
        if la is None or lo is None:
            continue
        d = haversine_km(lat, lon, la, lo)
        if d <= radius_km:
            out.append({'code': str(r.get('codEstacao') or r.get('codestacao') or ''), 'name': str(r.get('nomeEstacao') or r.get('nome') or ''),
                        'municipality': str(r.get('municipio') or r.get('cidade') or ''), 'ibge': str(r.get('codIbge') or r.get('codibge') or ''),
                        'latitude': la, 'longitude': lo, 'distance_km': round(d, 1), 'kind': str(r.get('tipoEstacao') or r.get('tipo') or '')})
    out.sort(key=lambda x: x['distance_km'])
    return out


def parse_rain(payload: Any, *, codes: set[str], since_utc: dt.datetime) -> dict[str, dict]:
    """Per gauge: sum of 'chuva' readings after ``since_utc``; JSON rows or ';'-separated text."""
    rows: list[dict] = []
    if isinstance(payload, str):
        text = payload.strip()
        try:
            payload = json.loads(text)
        except ValueError:
            lines = [l for l in text.splitlines() if ';' in l]
            if not lines:
                raise ValueError('Resposta CEMADEN sem registros reconhecíveis')
            start = next((i for i, l in enumerate(lines) if 'codEstacao' in l or 'codestacao' in l.lower()), 0)
            rows = list(csv.DictReader(io.StringIO('\n'.join(lines[start:])), delimiter=';'))
    if isinstance(payload, dict):
        payload = payload.get('cemaden') or payload.get('dados') or payload.get('registros') or []
    if isinstance(payload, list):
        rows = [r for r in payload if isinstance(r, dict)]
    out: dict[str, dict] = {}
    for r in rows:
        keys = {k.lower().strip(): k for k in r}
        code = str(r.get(keys.get('codestacao', ''), '') or '').strip()
        if code not in codes:
            continue
        sensor = str(r.get(keys.get('sensor', ''), '') or '').lower()
        if sensor and 'chuva' not in sensor:
            continue
        stamp = str(r.get(keys.get('datahora', ''), '') or '').replace('T', ' ')[:19]
        try:
            when = dt.datetime.strptime(stamp, '%Y-%m-%d %H:%M:%S').replace(tzinfo=dt.timezone.utc)
        except ValueError:
            continue
        value = _num(r.get(keys.get('valor', ''), None))
        if value is None or value < 0 or value > 200:
            continue
        if when < since_utc:
            continue
        slot = out.setdefault(code, {'rain_24h_mm': 0.0, 'readings': 0, 'last_reading_utc': None})
        slot['rain_24h_mm'] = round(slot['rain_24h_mm'] + value, 2)
        slot['readings'] += 1
        iso = when.isoformat(timespec='seconds')
        if slot['last_reading_utc'] is None or iso > slot['last_reading_utc']:
            slot['last_reading_utc'] = iso
    return out


def collect_cemaden(lat: float, lon: float, *, location_id: str = 'navirai', radius_km: float = 80, enabled: bool | None = None, session=None) -> dict:
    enabled = (os.environ.get('CEMADEN_ENABLE') == '1') if enabled is None else enabled
    now = dt.datetime.now(dt.timezone.utc)
    base = {'source': 'CEMADEN — pluviômetros automáticos', 'source_url': SOURCE_URL, 'queried_at_utc': now.isoformat(timespec='seconds'),
            'note': 'Leituras de pluviômetros públicos próximos; chuva medida nos últimos 24 h, não previsão. Distâncias em linha reta.'}
    if not enabled:
        return {**base, 'state': 'disabled'}
    token = os.environ.get('CEMADEN_TOKEN', '').strip()
    if not token:
        return {**base, 'state': 'requires_registration', 'note': base['note'] + ' O serviço exige token (gratuito, solicitado ao CEMADEN); defina o segredo CEMADEN_TOKEN.'}
    uf = UF_BY_LOCATION.get(location_id, 'MS')
    session = session or requests.Session()
    headers = {'User-Agent': 'Campo-e-Clima/4.1 (pesquisa não comercial)'}
    try:
        catalog = session.get(f'{BASE}/pcds-cadastro/estacoes', params={'uf': uf, 'token': token}, timeout=30, headers=headers)
        catalog.raise_for_status()
        stations = parse_stations(catalog.json(), lat, lon, radius_km=radius_km)
        if not stations:
            return {**base, 'state': 'no_station_in_range', 'radius_km': radius_km, 'uf': uf}
        since = now - dt.timedelta(hours=24)
        params = {'rede': 11, 'uf': uf, 'inicio': since.strftime('%Y%m%d%H%M'), 'fim': now.strftime('%Y%m%d%H%M'), 'token': token}
        ibges = sorted({s['ibge'] for s in stations if s['ibge']})
        rain: dict[str, dict] = {}
        for ibge in ibges[:6]:
            r = session.get(f'{BASE}/pcds/dados_pcd', params={**params, 'codibge': ibge}, timeout=40, headers=headers)
            r.raise_for_status()
            body = r.text
            rain.update(parse_rain(body, codes={s['code'] for s in stations}, since_utc=since))
        for s in stations:
            s.update(rain.get(s['code'], {'rain_24h_mm': None, 'readings': 0, 'last_reading_utc': None}))
        return {**base, 'state': 'ok', 'radius_km': radius_km, 'uf': uf, 'stations': stations[:12], 'with_readings': sum(1 for s in stations if s['readings'])}
    except (requests.RequestException, ValueError, TypeError, KeyError) as exc:
        return {**base, 'state': 'unavailable', 'error': f'{type(exc).__name__}: {str(exc)[:140]}'.replace(token, '***')}
