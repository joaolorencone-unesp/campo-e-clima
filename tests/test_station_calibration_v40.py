"""Station files, QC, local-day aggregation and out-of-sample bias correction (offline, synthetic forecasts)."""
import datetime as dt
import json
from pathlib import Path
import pytest
from scripts.science import station_files as sf
from scripts.science import station_calibration as sc
from tests.synthetic_station_forecasts import build_fixture

ROOT = Path(__file__).resolve().parents[1]


def test_inmet_portal_parser_and_qc_rules():
    text = ('"Data";"Hora (UTC)";"Temp. Ins. (C)";"Temp. Max. (C)";"Temp. Min. (C)";"Umi. Ins. (%)";"Umi. Max. (%)";"Umi. Min. (%)";'
            '"Pto Orvalho Ins. (C)";"Pto Orvalho Max. (C)";"Pto Orvalho Min. (C)";"Pressao Ins. (hPa)";"Pressao Max. (hPa)";"Pressao Min. (hPa)";'
            '"Vel. Vento (m/s)";"Dir. Vento (m/s)";"Raj. Vento (m/s)";"Radiacao (KJ/m²)";"Chuva (mm)"\n'
            '"05/05/2026";"0000";"22,4";"22,8";"22,4";"83,0";"83,0";"81,0";"19,4";"19,5";"19,4";"978,5";"978,5";"978,0";"1,3";"138,0";"2,0";"";"0,0"\n'
            '"05/05/2026";"0100";"";"";"";"";"";"";"";"";"";"";"";"";"";"";"";"";""\n'
            '"05/05/2026";"0200";"35,0";"22,0";"21,0";"120,0";"88,0";"85,0";"40,0";"19,4";"19,3";"979,3";"979,3";"978,9";"5,0";"129,0";"1,0";"";"-9999"\n')
    rows, summary = sf.qc_hourly(sf.parse_inmet_portal_hourly(text))
    assert len(rows) == 3 and rows[0]['wind_speed_10m'] == pytest.approx(4.68) and rows[0]['wind_gusts_10m'] == pytest.approx(7.2)
    assert rows[1]['clean']['temperature_2m'] is None and rows[1]['qc']['precipitation'] == 'missing'
    assert rows[2]['qc']['temperature_2m'] == 'inconsistent_extremes' and rows[2]['qc']['relative_humidity_2m'] == 'out_of_range'
    assert rows[2]['qc']['wind_gusts_10m'] == 'gust_below_speed' and rows[2]['qc']['precipitation'] == 'missing'
    assert summary['fully_missing_rows'] == 1 and summary['rows'] == 3
    with pytest.raises(ValueError):
        sf.parse_inmet_portal_hourly(text + '"05/05/2026";"0200";"1";"1";"1";"1";"1";"1";"1";"1";"1";"1";"1";"1";"1";"1";"1";"";"0"\n')


def test_local_day_aggregation_requires_complete_rain_and_uses_hour_ending_labels():
    records = []
    for i in range(72):
        stamp = (dt.datetime(2026, 5, 4, 0, tzinfo=dt.timezone.utc) + dt.timedelta(hours=i)).isoformat(timespec='seconds')
        clean = {k: None for k in sf.HOURLY_FIELDS}
        clean.update(temperature_2m=20.0, temperature_hour_max=21.0, temperature_hour_min=19.0, precipitation=1.0 if stamp.startswith('2026-05-05T05') else 0.0)
        records.append({'valid_at_utc': stamp, 'clean': clean})
    days = {d['date']: d for d in sf.aggregate_local_days(records, -4)}
    # 05:00 UTC = 01:00 local on 5 May; the rain labelled there belongs to local day 5 May.
    assert days['2026-05-05']['rain_mm'] == 1.0 and days['2026-05-05']['rain_hours'] == 24 and days['2026-05-05']['t_max'] == 21.0
    # The file starts at 00:00 UTC on 4 May (20:00 local on 3 May): 3 May is incomplete, 4 May complete, 6 May truncated.
    assert days['2026-05-03']['rain_mm'] is None and days['2026-05-03']['rain_hours'] == 5 and days['2026-05-03']['t_mean'] is None
    assert days['2026-05-04']['rain_mm'] == 0.0 and days['2026-05-04']['rain_hours'] == 24 and days['2026-05-04']['t_mean'] == 20.0
    assert days['2026-05-06']['rain_mm'] is None and days['2026-05-06']['rain_hours'] == 19


def test_real_station_files_parse_with_documented_gaps():
    for entry in sf.registry(ROOT / 'data/stations/stations.json'):
        data = sf.load_station(entry, ROOT, asof=dt.date(2026, 11, 5))
        assert data['period'] and data['daily']
        if entry['id'].startswith('INMET'):
            assert len(data['hourly']) == 4440 and data['qc']['hourly']['rows'] == 4440
            assert all(d['rain_mm'] is None for d in data['daily'] if d['rain_hours'] < 24)
            assert not any(d['rain_mm'] is not None and d['rain_mm'] < 0 for d in data['daily'])
        else:
            assert data['hourly'] == [] and len(data['daily']) == 183 and data['daily'][0]['wind_mean_kmh_note']


def test_corrections_and_quantile_mapping_are_sane():
    x = [10.0, 12.0, 14.0, 16.0]
    assert sc.apply(sc.fit('bias', x, [11, 13, 15, 17]), x).tolist() == [11, 13, 15, 17]
    assert sc.apply(sc.fit('ratio', [2.0, 4.0], [3.0, 6.0]), [10.0]).tolist() == [15.0]
    hb = sc.fit('hourly_bias', [20.0] * 48, [21.0] * 24 + [20.0] * 24, list(range(24)) * 2)
    assert hb['global_bias'] == pytest.approx(0.5) and abs(hb['by_hour']['0'] - 0.5) < 0.5
    import numpy as np
    rng = np.random.default_rng(1)
    obs = np.where(rng.random(400) < .3, rng.gamma(1.2, 8, 400), 0.0)
    fc = np.where(rng.random(400) < .5, obs * 1.4 + rng.gamma(1, 1, 400), 0.0)
    qm = sc.fit('quantile_map', fc, obs)
    corrected = sc.apply(qm, fc, variable='rain_mm')
    assert corrected.min() >= 0 and abs(np.mean(corrected > .2) - np.mean(obs > .2)) < 0.12
    # The mapped distribution follows the observed one (mean within 25 %), not the forecast one.
    assert abs(np.mean(corrected) - np.mean(obs)) < 0.25 * np.mean(obs)


def test_pipeline_recovers_known_bias_out_of_sample(tmp_path, monkeypatch):
    monkeypatch.setattr(sc, 'BOOTSTRAP', 200)
    entries = sf.registry(ROOT / 'data/stations/stations.json')
    fixture = {}
    for entry in entries:
        data = sf.load_station(entry, ROOT, asof=dt.date(2026, 11, 5))
        fixture[entry['id']] = build_fixture(data, models=('modelo_a',), leads=(1, 3))
    path = tmp_path / 'fixture.json'
    path.write_text(json.dumps(fixture), encoding='utf-8')
    index, reports = sc.run(fixture=str(path), output_dir=tmp_path / 'out', root=ROOT, asof=dt.date(2026, 11, 5))
    assert {s['id'] for s in index['stations']} == {e['id'] for e in entries}
    navirai = next(r for r in reports if r['station']['id'] == 'INMET:S735')
    temp = next(v for v in navirai['verification'] if v['variable'] == 'temperature_2m' and v['lead_days'] == 1 and v['model'] == 'modelo_a')
    assert temp['status'] == 'evaluated' and temp['raw_test']['bias'] > 1.2
    assert temp['recommended'] and temp['recommended']['method'] in ('bias', 'hourly_bias', 'linear')
    assert abs(temp['recommended']['parameters'].get('bias', temp['recommended']['parameters'].get('global_bias', -1.8)) + 1.8) < 0.4 or temp['recommended']['method'] == 'linear'
    assert temp['recommended']['evidence']['delta_mae_ci95'][1] < 0
    rain = next(v for v in navirai['verification'] if v['variable'] == 'rain_mm' and v['lead_days'] == 1 and v['model'] == 'modelo_a')
    assert rain['status'] in ('evaluated', 'insufficient_test_sample') and rain['raw_contingency'][0]['threshold_mm'] == 1
    embrapa = next(r for r in reports if r['station']['id'].startswith('EMBRAPA'))
    assert embrapa['forecast_point']['source'] == 'municipal_reference_point' and embrapa['limitations'][0].startswith('Coordenadas')
    assert any(v['variable'] == 't_max' and v['status'] == 'evaluated' for v in embrapa['verification'])
    out = json.loads((tmp_path / 'out' / 'inmet_s735_navirai.json').read_text(encoding='utf-8'))
    assert out['series']['modelo_a']['dates'] and len(out['observations']['daily']) == navirai['observations']['daily_rows']
    assert (tmp_path / 'out' / 'index.json').exists()
