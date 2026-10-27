"""Tests for honest multi-horizon availability and free-API rate limiting."""
from pathlib import Path
import pytest
from scripts.sources.gefs_extended import parse_gefs_extended,collect_gefs_extended

ROOT=Path(__file__).resolve().parents[1]


def gefs_payload(n=15,days=35):
    from datetime import date,timedelta
    start=date(2026,10,27)
    series={f'precipitation_sum_member{i:02d}':[float((i+j)%18) for j in range(days)] for i in range(n)}
    return {'utc_offset_seconds':-14400,'latitude':-23.,'longitude':-54.25,
            'daily':{'time':[(start+timedelta(days=i)).isoformat() for i in range(days)],**series}}


def test_gefs_extended_yields_only_future_15_35_with_member_dispersion():
    result=parse_gefs_extended(gefs_payload())
    assert result['state']=='ok' and result['model_count']==1 and result['member_count']==15
    assert len(result['days'])==21 and result['days'][0]['date']=='2026-11-10'
    for day in result['days']:
        assert 0<=day['p10_mm']<=day['p50_mm']<=day['p90_mm']
        assert 0<=day['freq_gt_5_mm']<=1


def test_gefs_extended_never_fabricates_missing_members():
    p=gefs_payload(n=8)
    for i in range(8):p['daily'][f'precipitation_sum_member{i:02d}'][15]=None
    result=parse_gefs_extended(p)
    assert result['state']=='ok' and all(d['date']!='2026-11-11' for d in result['days'])
    with pytest.raises(ValueError,match='insuficientes'):parse_gefs_extended(gefs_payload(n=1))
    with pytest.raises(ValueError,match='UTC'):parse_gefs_extended({**gefs_payload(),'utc_offset_seconds':0})


def test_gefs_collector_requests_single_daily_variable_and_35days(monkeypatch):
    captured={}
    class Reply:
        def raise_for_status(self): pass
        def json(self):return gefs_payload()
    def fake_get(url,params,**kw):
        captured.update(params)
        assert url.endswith('/v1/ensemble')
        return Reply()
    monkeypatch.setattr('scripts.sources.gefs_extended.requests.get',fake_get)
    got=collect_gefs_extended()
    assert got['state']=='ok'
    assert captured['models']=='ncep_gefs_seamless'
    assert captured['forecast_days']==35 and captured['daily']=='precipitation_sum'
    assert 'hourly' not in captured


def test_long_range_api_not_called_directly_from_browser():
    browser=(ROOT/'site/static/extended_v12.js').read_text()
    workflow=(ROOT/'.github/workflows/pages.yml').read_text()
    collector=(ROOT/'scripts/collect.py').read_text()
    assert 'seasonal-api.open-meteo.com' not in browser
    assert 'data/latest.json' in browser
    assert 'weekly_sources_cache.json' in collector
    assert 'GEFS_EXTENDED_ENABLE' in workflow
    assert 'SLOW_WEEK' in workflow


def test_ui_has_explainable_restrictions_and_coverage():
    html=(ROOT/'site/index.html').read_text()
    js=(ROOT/'site/static/app.js').read_text()
    assert 'spray-quick-diagnosis' in html
    assert 'calendar-coverage' in html
    assert 'gefs_extended' in js
    assert 'fatores podem ocorrer simultaneamente' in js


def test_ensemble_timeout_falls_back_once_to_reduced_rain_only():
    """A true timeout should not silently remove a valid 4-day rain sample."""
    import scripts.collect as c
    src=(ROOT/'scripts/collect.py').read_text()
    assert 'except requests.Timeout as exc' in src
    assert "'forecast_days':4, 'hourly':'precipitation'" in src
    assert "exc.response.status_code==429" in src


def test_full_collector_partial_timeout_fallback(tmp_path,monkeypatch):
    from datetime import date,timedelta
    import json,requests
    import scripts.collect as c
    start=date(2026,10,27)
    times=[(start+timedelta(days=i)).isoformat()+f'T{h:02d}:00' for i in range(7) for h in range(24)]
    forecast={'utc_offset_seconds':-14400,'hourly':{'time':times,'precipitation':[0]*len(times)},
             'daily':{'time':[(start+timedelta(days=i)).isoformat() for i in range(14)]},
             'current':{'temperature_2m':25}}
    days4=times[:96]
    compact={'utc_offset_seconds':-14400,'latitude':-23,'longitude':-54,
             'hourly':{'time':days4,'precipitation_member00':[.2]*96,'precipitation_member01':[0]*96}}
    calls=[]
    def stub(url,params):
        calls.append((url,params))
        if url==c.FORECAST_URL:return forecast
        if params.get('forecast_days')==4:return compact
        raise requests.Timeout('limit exceeded')
    monkeypatch.setattr(c,'fetch',stub)
    monkeypatch.setattr(c,'MODELS',{'Exemplo de teste':'test_ensemble'})
    monkeypatch.setattr(c.time,'sleep',lambda _:None)
    monkeypatch.setattr(c,'collect_official',lambda: {})
    for name in ['collect_cptec','collect_soil_forecast','collect_nasa_power',
                 'collect_gefs_extended','collect_extended','collect_previous_runs',
                 'collect_climate_era5','collect_openweather_free']:
        monkeypatch.setattr(c,name,lambda *a,**kw: {'state':'unavailable'})
    monkeypatch.chdir(tmp_path)
    target=tmp_path/'out.json';monkeypatch.setenv('OUTPUT_JSON',str(target))
    c.main()
    result=json.loads(target.read_text())
    m=result['ensemble_models']['Exemplo de teste']
    assert m['fallback_short_horizon'] is True
    assert m['coverage_days']==4
    assert m['precipitation_members']==2
    assert len(result['rain_ensemble_daily'])==4
    assert len([r for _,r in calls if r.get('forecast_days')==4])==2 # rain fallback + spray attempt
