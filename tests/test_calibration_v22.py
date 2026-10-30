"""Optional ML regression on explicitly synthetic test data, never operational."""
import datetime as dt
import pytest
pytest.importorskip('sklearn')
from scripts.science.database import migrate
from scripts.science.calibration import experiment
from scripts.science.common import iso

def test_shadow_fit_has_independent_test_and_does_not_promote(tmp_path,monkeypatch):
    rows=[]
    for day in range(180):
        for hour in (0,6,12,18):
            t=dt.datetime(2025,1,1,tzinfo=dt.timezone.utc)+dt.timedelta(days=day,hours=hour)
            raw=20+(day%9)*.3+hour*.1
            rows.append({'location_id':'navirai','model_id':'synthetic','variable':'temperature_2m','horizon':'D1',
                'lead_basis':'fixed_offset_24h','station_id':'synthetic','method':'M1','valid_at_utc':iso(t),
                'run_id':f'{day}-{hour}','prediction':raw,'observation':raw+2,'lead_hours':24})
    monkeypatch.setattr('scripts.science.calibration.paired_rows',lambda db:(rows,{}))
    db=tmp_path/'db';migrate(db)
    result=experiment(db,tmp_path/'synthetic-only.json')
    assert result['primary_forecast_replaced'] is False
    item=result['experiments'][0]
    assert item['split']['test']>=50 and item['superiority_claim'] is False
    bias=next(e for e in item['evaluations'] if e['method']=='M3 bias')
    assert bias['metrics']['mae']<1e-8
    assert any(e['method']=='M4 Gradient Boosting' for e in item['evaluations'])
