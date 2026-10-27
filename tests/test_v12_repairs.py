"""v1.2 regression checks for API semantics and UI contract."""
from pathlib import Path
import pytest
from scripts.sources.supplementary import parse_extended_weekly_mean, collect_extended

ROOT=Path(__file__).resolve().parents[1]

def test_weekly_light_model_preserves_units_and_no_invented_percentiles():
    payload={
      'utc_offset_seconds':-14400,'latitude':-23,'longitude':-54,
      'weekly_units':{'precipitation_mean':'mm'},
      'monthly_units':{'precipitation_mean':'mm'},
      'weekly':{'time':['2026-11-02','2026-11-09'],'precipitation_mean':[14.5,0.0],
                'precipitation_anomaly':[3.1,-1.2],'temperature_2m_mean':[27.1,28.2]},
      'monthly':{'time':['2026-11-01','2026-12-01'],'precipitation_mean':[130.2,None]},
    }
    d=parse_extended_weekly_mean(payload)
    assert d['state']=='ok' and d['product']=='weekly_ensemble_mean'
    assert d['weeks'][0]['rain_week_mean_api']==14.5
    assert d['weeks'][1]['rain_week_mean_api']==0.0  # observed model 0 is valid
    assert d['precipitation_unit']=='mm'
    assert d['months']==[{'start':'2026-11-01','rain_month_mean_api':130.2}]
    assert not any('p10' in key or 'p90' in key for key in d['weeks'][0])


def test_weekly_missing_data_is_not_zero():
    d={'utc_offset_seconds':-14400,'weekly':{'time':['2026-11-02'],'precipitation_mean':[None]}}
    with pytest.raises(ValueError,match='nenhuma semana'):
        parse_extended_weekly_mean(d)
    with pytest.raises(ValueError,match='UTC'):
        parse_extended_weekly_mean({**d,'utc_offset_seconds':0})


def test_collect_extended_calls_only_light_model(monkeypatch):
    seen={}
    def fake_get(url,params,timeout):
        seen.update(params)
        return {'utc_offset_seconds':-14400,'weekly':{
           'time':['2026-11-02'],'precipitation_mean':[3.]}}
    monkeypatch.setattr('scripts.sources.supplementary.get_json',fake_get)
    r=collect_extended(enabled=True)
    assert r['state']=='ok'
    assert 'weekly' in seen and 'monthly' in seen
    assert seen['models']=='ecmwf_seasonal_ensemble_mean_seamless'
    assert 'hourly' not in seen
    assert seen['forecast_days']>=60


def test_restriction_cause_inspector_and_historical_reference():
    html=(ROOT/'site/index.html').read_text(encoding='utf8')
    app=(ROOT/'site/static/app.js').read_text(encoding='utf8')
    hist=(ROOT/'site/static/history_v10.js').read_text(encoding='utf8')
    ext=(ROOT/'site/static/extended_v12.js').read_text(encoding='utf8')
    assert 'id="spray-inspect-hour"' in html and 'id="spray-reason-detail"' in html
    assert 'sprayRestrictionExplanation' in app
    assert 'motivos' in app.lower() and 'podem coexistir' in app
    assert "models:'era5'" in hist and "models:'era5_land'" in hist
    assert "parseDaily(base)" in hist  # validates non-null rainfall before considering success
    assert "precipitation_mean" in ext and 'forecast_days' in ext
    assert "Não" in ext or 'não' in ext
