"""Free climate and verification comparators: offline fixtures only."""
import datetime as dt
import pytest
from scripts.sources.free_research import (
    parse_climate_era5, parse_previous_runs, compare_export_provisional,
)


def fake_monthly_climate():
    start=dt.date(1991,1,1);end=dt.date(2020,12,31)
    dates=[];rain=[]
    d=start
    while d<=end:
        dates.append(d.isoformat());rain.append(1.0)
        d+=dt.timedelta(days=1)
    return {'daily':{'time':dates,'precipitation_sum':rain},
            'latitude':-23.0,'longitude':-54.2,'utc_offset_seconds':-14400}


def test_climate_30y_complete_months():
    p=parse_climate_era5(fake_monthly_climate())
    assert p['state']=='ok' and len(p['months'])==12
    assert p['months'][1]['mean_monthly_rain_mm']>28 # leap years in February
    assert all(x['years_complete']==30 for x in p['months'])
    assert p['yearly_mean_sum_mm']>365


def test_climate_missing_day_is_not_counted_as_zero():
    p=fake_monthly_climate()
    idx=p['daily']['time'].index('2019-02-09')
    p['daily']['precipitation_sum'][idx]=None
    c=parse_climate_era5(p)
    assert c['months'][1]['years_complete']==29


def past_fixture():
    today=dt.date(2026,10,26)
    stamp=[];p1=[];p3=[]
    for date in (dt.date(2026,10,22),dt.date(2026,10,23)):
        for h in range(24):
            stamp.append(date.isoformat()+f'T{h:02d}:00')
            p1.append(1.0 if date.day==22 else 0)
            p3.append(0.5)
    return {'hourly':{'time':stamp,'precipitation_previous_day1':p1,
                      'precipitation_previous_day3':p3}},today


def test_previous_runs_daily_total_and_provenance():
    raw,today=past_fixture()
    out=parse_previous_runs(raw,asof=today)
    assert out['state']=='ok' and len(out['days'])==2
    assert out['days'][0]['lead1_rain_mm']==24
    assert out['days'][0]['lead3_rain_mm']==12
    assert out['days'][1]['lead1_rain_mm']==0
    assert 'não é uma única' in out['note']


def test_previous_runs_missing_hour_does_not_turn_into_zero():
    raw,today=past_fixture()
    raw['hourly']['precipitation_previous_day1'][0]=None
    p=parse_previous_runs(raw,asof=today)
    assert p['days'][0]['lead1_rain_mm'] is None
    assert p['days'][0]['lead3_rain_mm'] == 12


def test_verification_provisional_no_skill_assertion():
    raw,today=past_fixture()
    previous=parse_previous_runs(raw,asof=today)
    obs={'state':'provisional','records':[{'date':'2026-10-22','precipitation_mm':16.0},
                                      {'date':'2026-10-23','precipitation_mm':0.0}]}
    result=compare_export_provisional(previous,obs)
    assert result['state']=='exploratory' and result['days_overlapping']==2
    assert result['station_verified'] is False
    assert not any(k in result for k in ('mae','brier','crps','skill'))


def test_no_comparison_without_overlapping_observation():
    raw,today=past_fixture()
    result=compare_export_provisional(parse_previous_runs(raw,asof=today),
                                       {'state':'provisional','records':[]})
    assert result['state']=='no_overlapping_days'


def test_climate_no_data_rejected():
    with pytest.raises(ValueError):parse_climate_era5({'daily':{'time':[]}})


def test_openweather_free_missing_rain_is_na_not_zero():
    from scripts.sources.free_research import parse_openweather_free
    rows=[]
    for h in range(3,24,3):
        rows.append({'dt':1793030400+h*3600,'main':{'temp':22.0},
                     'wind':{'speed':2.0,'deg':170},'pop':0.3})
    payload={'cod':'200','city':{'coord':{'lat':-23.065,'lon':-54.190}},'list':rows}
    r=parse_openweather_free(payload)
    assert r['state']=='ok'
    assert r['forecast'][0]['rain_3h_mm'] is None
    assert r['forecast'][0]['wind_kmh']==7.2
    assert r['forecast'][0]['pop']==0.3


def test_openweather_free_no_key_no_http(monkeypatch):
    from scripts.sources import free_research
    monkeypatch.delenv('OPENWEATHER_FREE_API_KEY',raising=False)
    monkeypatch.setattr(free_research.requests,'get',lambda *a,**kw: 1/0)
    result=free_research.collect_openweather_free()
    assert result['state']=='optional_free_key'
