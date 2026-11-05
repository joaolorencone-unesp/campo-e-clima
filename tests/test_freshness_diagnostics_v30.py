"""Freshness summary, diagnostics export, run-aware cache and station preference."""
import datetime as dt
import json
from pathlib import Path
import pytest
import requests
from scripts.freshness import summarize, minutes_between
from scripts.science.http import FreeClient
from scripts.science.stations import candidates, observation_urls, collect as collect_station
from scripts.science.capture import Capture
from scripts.science.common import packed


def test_freshness_separates_run_acquisition_and_publication():
    now = dt.datetime(2026, 11, 5, 4, 0, tzinfo=dt.timezone.utc)
    public = {'ensemble_models': {
        'ECMWF IFS': {'state': 'ok', 'precipitation_members': 50, 'gust_members': 50, 'cache_hit': True,
                      'collected_at_utc': '2026-11-04T23:36:49+00:00', 'precipitation_native_step_hours': 3,
                      'model_run': {'state': 'ok', 'last_run_initialisation_utc': '2026-11-04T12:00:00+00:00',
                                    'last_run_availability_utc': '2026-11-05T02:10:00+00:00'}},
        'GEM Canada': {'state': 'error', 'detail': 'timeout', 'model_run': {'state': 'unavailable'}}},
        'deterministic': {'collected_at_utc': '2026-11-05T03:44:14+00:00', 'current': {'time': '2026-11-04T23:30'}},
        'deterministic_extended': {'state': 'ok', 'collected_at_utc': '2026-11-05T03:44:20+00:00'},
        'agro_ensemble_coverage': {'vpd_kpa': {'model_count': 6, 'models': []}}}
    f = summarize(public, now=now)
    ifs = f['ensembles']['ECMWF IFS']
    assert ifs['acquisition_age_min'] == 263 and ifs['run_age_min'] == 960 and ifs['cache_hit'] is True
    assert ifs['newer_run_available_than_acquired'] is True
    assert f['models_with_newer_run_pending'] == ['ECMWF IFS']
    assert f['models_valid_rain'] == 1 and f['models_valid_by_variable']['vpd_kpa'] == 6
    assert f['deterministic']['acquisition_age_min'] == 16
    assert f['ensembles']['GEM Canada']['acquired_utc'] is None
    assert minutes_between('bad', None) is None


def test_diagnostics_export_writes_summary_and_log(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    import scripts.export_diagnostics as diag
    monkeypatch.setattr(diag, 'PUBLIC', {'navirai': tmp_path / 'latest.json', 'diamantino': tmp_path / 'missing.json'})
    monkeypatch.setattr(diag, 'LOG', tmp_path / 'runtime' / 'collection_log.json')
    monkeypatch.setattr(diag, 'OUT', tmp_path / 'site' / 'data' / 'diagnostics.json')
    (tmp_path / 'latest.json').write_text(json.dumps({'issued_at_utc': '2026-11-05T03:44:13+00:00', 'schema_version': 5,
        'ensemble_models': {'A': {'state': 'ok', 'cache_hit': True}}, 'sources': {'X': {'state': 'unavailable', 'error': 'HTTP 503'}},
        'freshness': {'models_valid_rain': 8, 'models_valid_gusts': 3, 'ensemble_oldest_acquisition_age_min': 250,
                      'deterministic': {'acquisition_age_min': 2}}, 'warnings': [], 'official': {}}))
    out = diag.main(now=dt.datetime(2026, 11, 5, 4, tzinfo=dt.timezone.utc))
    assert out['locations']['navirai']['models_valid_rain'] == 8 and out['locations']['navirai']['cache_hits'] == ['A']
    assert out['locations']['diamantino']['state'] == 'missing' and out['overall_state'] == 'degraded'
    assert out['locations']['navirai']['errors'] == {'X': 'HTTP 503'}
    assert json.loads((tmp_path / 'runtime' / 'collection_log.json').read_text())[0]['models_valid_rain']['navirai'] == 8
    again = diag.main(now=dt.datetime(2026, 11, 5, 5, tzinfo=dt.timezone.utc))
    assert again['cadence']['runs_logged'] == 2 and again['cadence']['median_gap_min'] == 60


def test_fresh_after_bypasses_cache_inside_ttl(tmp_path, monkeypatch):
    class Session:
        calls = 0
        def get(self, *a, **k):
            self.calls += 1
            r = requests.Response(); r.status_code = 200
            r._content = json.dumps({'hourly': {'time': ['2026-11-05T00:00'], 'temperature_2m': [24 + self.calls]}}).encode(); return r
    session = Session(); monkeypatch.setattr('scripts.science.http.time.sleep', lambda _: None)
    url = 'https://ensemble-api.open-meteo.com/v1/ensemble'; params = {'models': 'x'}
    client = FreeClient(tmp_path / 'cache', session=session)
    assert client.get(url, params, ttl_hours=12)['hourly']['temperature_2m'] == [25]
    assert client.get(url, params, ttl_hours=12)['hourly']['temperature_2m'] == [25]  # cache hit inside TTL
    future = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=1)).isoformat()
    assert client.get(url, params, ttl_hours=12, fresh_after=future)['hourly']['temperature_2m'] == [26]
    assert session.calls == 2


def test_station_candidates_prefer_inmet_entity_and_token_is_never_recorded(tmp_path, monkeypatch):
    loc = {'latitude': -23.065, 'longitude': -54.190, 'timezone': 'America/Campo_Grande', 'id': 'navirai'}
    registry = [
        {'CD_ESTACAO': 'S735', 'DC_NOME': 'NAVIRAI (PARCEIRA)', 'SG_ENTIDADE': 'SEMADESC-MS', 'CD_SITUACAO': 'Operante', 'VL_LATITUDE': '-22.899909', 'VL_LONGITUDE': '-53.869219', 'VL_ALTITUDE': '303'},
        {'CD_ESTACAO': 'A752', 'DC_NOME': 'ITAQUIRAI', 'SG_ENTIDADE': 'INMET', 'CD_SITUACAO': 'Operante', 'VL_LATITUDE': '-23.44944444', 'VL_LONGITUDE': '-54.18194443', 'VL_ALTITUDE': '337.82'},
        {'CD_ESTACAO': 'A749', 'DC_NOME': 'JUTI', 'SG_ENTIDADE': 'INMET', 'CD_SITUACAO': 'Pane', 'VL_LATITUDE': '-22.857', 'VL_LONGITUDE': '-54.605', 'VL_ALTITUDE': '375'},
        {'CD_ESTACAO': 'A709', 'DC_NOME': 'IVINHEMA', 'SG_ENTIDADE': 'INMET', 'CD_SITUACAO': 'Operante', 'VL_LATITUDE': '-22.3005', 'VL_LONGITUDE': '-53.8227', 'VL_ALTITUDE': '377'}]
    ranked = candidates(registry, loc)
    assert [m['id'] for _, m in ranked] == ['INMET:A752', 'INMET:S735']  # INMET-operated first, broken and distant ones out
    monkeypatch.setenv('INMET_API_TOKEN', 'SECRET-TOKEN')
    request_url, recorded = observation_urls('A752', '2026-11-02', '2026-11-05')
    assert 'SECRET-TOKEN' in request_url and 'SECRET-TOKEN' not in recorded and recorded.endswith('/A752')

    class Client:
        def __init__(self, cap): self.capture = cap; self.urls = []
        def get(self, url, params, **kw):
            self.urls.append((url, kw.get('record_url')))
            if url.endswith('estacoes/T'): return registry
            if '/A752/' in url:  # first candidate answers with no content, like a 204
                raise ValueError('Sem lista de observações horárias válidas')
            return [{'CD_ESTACAO': 'S735', 'DT_MEDICAO': '2026-11-05', 'HR_MEDICAO': '0300', 'TEM_INS': '21.4', 'CHUVA': '0.2', 'UMD_INS': '88', 'VEN_VEL': '2.1', 'VEN_RAJ': '4.0', 'VEN_DIR': '120'}]
    cap = Capture(tmp_path / 'cap', 'navirai'); client = Client(cap)
    result = collect_station(client, 'navirai')
    assert result['station'] == 'INMET:S735' and result['token_used'] is True and result['skipped']
    manifest = json.loads((cap.root / 'manifest.json').read_text())
    assert all('SECRET-TOKEN' not in r['source_url'] for r in manifest['requests'])
    assert any('SECRET-TOKEN' in u for u, _ in client.urls) and all(rec is None or 'SECRET' not in rec for _, rec in client.urls)


def test_public_official_collector_prefers_inmet_station_and_redacts_token(monkeypatch):
    import scripts.sources.official as official
    monkeypatch.setenv('INMET_API_TOKEN', 'TOP-SECRET')
    catalog = {'state': 'ok', 'nearest': [
        {'station_code': 'S735', 'name': 'NAVIRAI (PARCEIRA)', 'distance_km': 37.6, 'status': 'Operante', 'entity': 'SEMADESC-MS', 'latitude': -22.9, 'longitude': -53.87},
        {'station_code': 'A752', 'name': 'ITAQUIRAI', 'distance_km': 42.8, 'status': 'Operante', 'entity': 'INMET', 'latitude': -23.45, 'longitude': -54.18}]}
    seen = []
    def fake_http(url, timeout=18, record_url=None):
        seen.append((url, record_url))
        if '/A752/' in url:
            return [{'CD_ESTACAO': 'A752', 'DT_MEDICAO': '2026-11-05', 'HR_MEDICAO': '0300', 'TEM_INS': '21.4', 'CHUVA': '0.2', 'UMD_INS': '88', 'VEN_VEL': '2.1', 'VEN_RAJ': '4.0', 'VEN_DIR': '120'}]
        raise ValueError('no content')
    monkeypatch.setattr(official, 'http_json', fake_http)
    out = official.collect_nearby_station_hourly(catalog)
    assert out['state'] == 'ok' and out['station_code'] == 'A752' and out['entity'] == 'INMET'
    assert 'TOP-SECRET' in seen[0][0] and 'TOP-SECRET' not in seen[0][1] and 'TOP-SECRET' not in out['source_url']
    assert 'TOP-SECRET' not in str(out)
    daily = official.collect_nearby_station_daily(catalog)
    assert daily['state'] == 'ok' and daily['station_code'] == 'A752' and 'TOP-SECRET' not in str(daily)
