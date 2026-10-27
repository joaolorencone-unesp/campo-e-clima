"""End-to-end local smoke tests; no live HTTP requests or fabricated user data."""
import json

import scripts.collect as collector


def test_collector_builds_json_from_stubbed_api(tmp_path, monkeypatch):
    from datetime import date, timedelta
    day = date(2026, 10, 26)
    times = [(day + timedelta(days=k)).isoformat() + f'T{hour:02d}:00'
             for k in range(7) for hour in range(24)]
    forecast = {
        'utc_offset_seconds': -14400, 'latitude': -23.1, 'longitude': -54.2,
        'hourly': {'time': times, 'temperature_2m': [24]*len(times),
                   'precipitation': [0]*len(times)},
        'daily': {'time': [str(day + timedelta(days=k)) for k in range(7)]},
        'current': {'temperature_2m': 24},
    }
    ensemble = {
        'utc_offset_seconds': -14400, 'latitude': -23.1, 'longitude': -54.2,
        'hourly': {'time': times,
                   'precipitation_member01': [0.5]*len(times),
                   'precipitation_member02': [0.0]*len(times),
                   'wind_gusts_10m_member01': [34]*len(times),
                   'wind_gusts_10m_member02': [20]*len(times)},
    }
    # Stub every external connector, including v0.7 research endpoints: truly offline.
    monkeypatch.setattr(collector, 'collect_official', lambda: {})
    monkeypatch.setattr(collector, 'collect_cptec', lambda: {'state':'unavailable'})
    monkeypatch.setattr(collector, 'collect_soil_forecast', lambda: {'state':'unavailable'})
    monkeypatch.setattr(collector, 'collect_nasa_power', lambda **kw: {'state':'unavailable'})
    monkeypatch.setattr(collector, 'collect_extended', lambda **kw: {'state':'unavailable'})
    monkeypatch.setattr(collector, 'collect_gefs_extended', lambda **kw: {'state':'unavailable'})
    monkeypatch.setattr(collector, 'collect_previous_runs', lambda **kw: {'state':'unavailable'})
    monkeypatch.setattr(collector, 'collect_climate_era5', lambda **kw: {'state':'unavailable'})
    monkeypatch.setattr(collector, 'collect_openweather_free', lambda: {'state':'optional_free_key'})
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(collector, 'MODELS', {'model_A': 'model_a', 'model_B': 'model_b'})
    monkeypatch.setattr(collector.time, 'sleep', lambda _: None)
    monkeypatch.setattr(collector, 'fetch', lambda url, params: forecast if 'forecast' in url else ensemble)
    target = tmp_path / 'latest.json'
    monkeypatch.setenv('OUTPUT_JSON', str(target))
    collector.main()
    obj = json.loads(target.read_text())
    assert obj['deterministic']['current']['temperature_2m'] == 24
    assert len(obj['rain_ensemble_daily']) == 7
    assert obj['rain_ensemble_daily'][0]['p_gt_10_mm'] == 0.5
    assert obj['gust_ensemble_daily'][0]['p_gt_30_kmh'] == 0.5
    assert obj['ensemble_models']['model_A']['gust_members'] == 2
    assert obj['issued_at_utc'].endswith('+00:00')
    assert obj['complementary']['openweather']['state']=='optional_free_key'
    assert 'previous_runs' in obj['complementary']
    assert 'era5_climatology' in obj['complementary']


def test_collector_rejects_mismatched_timezone(monkeypatch):
    class StubResponse:
        def raise_for_status(self):
            return None
        def json(self):
            return {'utc_offset_seconds': -10800}
    monkeypatch.setattr(collector.requests, 'get', lambda *a, **k: StubResponse())
    import pytest
    with pytest.raises(ValueError, match='UTC-4'):
        collector.fetch('https://example.test/forecast', {'timezone': 'America/Campo_Grande'})
