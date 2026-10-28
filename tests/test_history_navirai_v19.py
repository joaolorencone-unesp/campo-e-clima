"""No external API calls. Synthetic values exercise historical parsing only."""
import datetime as dt
import json

from scripts.sources.history_navirai_v19 import collect, paired, parse_era5, parse_nasa, publish


def test_parse_era5_preserves_missing_and_zero():
    rows = parse_era5({'utc_offset_seconds': 0,
                       'daily': {'time': ['2026-10-01', '2026-10-02', '2026-10-03'],
                                 'precipitation_sum': [0, None, 4.2],
                                 'temperature_2m_mean': [25, 26, 24]}})
    assert rows['2026-10-01']['precipitation_mm'] == 0
    assert rows['2026-10-02']['precipitation_mm'] is None
    assert rows['2026-10-03']['precipitation_mm'] == 4.2


def test_parse_nasa_does_not_create_missing_rain():
    rows = parse_nasa({'properties': {'parameter': {'PRECTOTCORR': {'20261001': -999, '20261002': 0, '20261003': 4.5}}}})
    assert rows['2026-10-01']['precipitation_mm'] is None
    assert rows['2026-10-02']['precipitation_mm'] == 0
    assert rows['2026-10-03']['precipitation_mm'] == 4.5


def test_paired_sources_do_not_mix_missing_days():
    pair = paired({'2026-10-01': {'precipitation_mm': 0}, '2026-10-02': {'precipitation_mm': None}},
                  {'2026-10-01': {'precipitation_mm': 2}, '2026-10-02': {'precipitation_mm': 3}})
    assert pair['n_paired'] == 1
    assert pair['mean_nasa_minus_era5_mm'] == 2
    assert pair['rows'][1]['era5_mm'] is None


def test_collect_separate_sources_and_utc():
    calls = []

    def fake(url, params, timeout):
        calls.append(params)
        if 'archive-api' in url:
            return {'utc_offset_seconds': 0,
                    'daily': {'time': ['2026-10-01'], 'precipitation_sum': [1.0]}}
        return {'properties': {'parameter': {'PRECTOTCORR': {'20261001': 2.0}}}}

    result = collect(dt.date(2026, 10, 10), fake)
    assert result['state'] == 'ok'
    assert result['reference_day'] == 'UTC'
    assert result['n_paired'] == 1
    assert calls[0]['models'] == 'era5'
    assert calls[1]['time-standard'] == 'UTC'
    assert result['end_date'] == '2026-10-03'


def test_daily_cache_skips_repeat_requests(tmp_path):
    calls = []

    def fake(url, params, timeout):
        calls.append(url)
        if 'archive-api' in url:
            return {'utc_offset_seconds': 0, 'daily': {'time': ['2026-10-01'], 'precipitation_sum': [0]}}
        return {'properties': {'parameter': {'PRECTOTCORR': {'20261001': 0}}}}

    cache, public = tmp_path / 'cache.json', tmp_path / 'public.json'
    a = publish(cache, public, today=dt.date(2026, 10, 10), fetcher=fake)
    b = publish(cache, public, today=dt.date(2026, 10, 10), fetcher=fake)
    assert len(calls) == 2
    assert a == b
    assert json.loads(public.read_text())['state'] == 'ok'


def test_last_good_cache_preserved_on_failure(tmp_path):
    cache, public = tmp_path / 'cache.json', tmp_path / 'public.json'
    cache.write_text(json.dumps({'state': 'ok', 'collected_day': '2026-10-09', 'rows': [{'date': '2026-10-01'}]}))

    def fail(*args):
        raise ValueError('fora do ar')

    out = publish(cache, public, today=dt.date(2026, 10, 10), fetcher=fail)
    assert out['state'] == 'stale'
    assert len(json.loads(public.read_text())['rows']) == 1
