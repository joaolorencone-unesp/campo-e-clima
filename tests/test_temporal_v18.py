"""v1.8: forward horizon, precipitation end-label, member quality and operational separation."""
import datetime as dt
from scripts.collect import next_local_forecast_hour, model_hourly_rain, model_daily_gust, member_validity
from scripts.spraying import read_joint_members, mix_joint_hourly, mix_joint_windows2h


def times(hours=120):
    d=dt.datetime(2026, 10, 27)
    return [(d+dt.timedelta(hours=i)).strftime('%Y-%m-%dT%H:%M') for i in range(hours)]


def test_local_next_hour_not_from_midnight():
    assert next_local_forecast_hour(dt.datetime(2026,10,28,0,14,tzinfo=dt.timezone.utc)) == '2026-10-27T21:00'
    assert next_local_forecast_hour(dt.datetime(2026,10,28,0,59,tzinfo=dt.timezone.utc)) == '2026-10-27T21:00'


def test_future_72_horizon_and_precipitation_end_hour():
    tt=times(120)
    rain=[float(i) for i in range(120)]
    result=model_hourly_rain({'hourly':{'time':tt,'precipitation_member01':rain}},
                             future_start='2026-10-27T20:00')
    assert len(result)==72
    assert list(result)[0]=='2026-10-27T20:00'
    assert list(result)[-1]=='2026-10-30T19:00'
    assert result[tt[20]][1]==[21.0]  # NOT the rain at index 20, before t
    assert result[tt[20]][3]==[21.0+22.0+23.0]
    assert '2026-10-27T00:00' not in result


def test_member_series_declared_is_not_numeric_valid():
    tt=times(24)
    payload={'hourly':{'time':tt,'wind_gusts_10m_member01':[None]*24,
                                'wind_gusts_10m_member02':[20.]*24,
                                'wind_gusts_10m_member03':[None]*23+[15.]}}
    valid=member_validity(payload,'wind_gusts_10m')
    assert valid=={'declared':3,'has_numeric':2,'complete_series':1}
    daily=model_daily_gust(payload)
    assert daily['member_count']==3  # backward-compatible declared count
    assert daily['valid_member_count']==1
    assert daily['valid_members_by_day']['2026-10-27']==1


def test_night_numeric_screening_vs_indeterminate_operation():
    tt=times(40)
    h={'time':tt}
    for key,value in {'temperature_2m':24,'relative_humidity_2m':73,
                      'wind_speed_10m':5,'wind_direction_10m':150,
                      'wind_gusts_10m':9,'precipitation':0}.items():
        h[key+'_member01']=[value]*40
    data=read_joint_members({'hourly':h},future_start='2026-10-27T20:00')
    assert '2026-10-27T00:00' not in data['times']
    one=mix_joint_hourly({'A':data})[0]['herb']
    assert one['indeterminado']==1
    assert one['numeric_passa']==1
    assert one['numeric_restrito']==0
    assert 'inversao_e_estabilidade_nao_verificadas' in one['operational_pending']
    two=mix_joint_windows2h({'A':data})[0]['herb']
    assert two['indeterminado']==1 and two['numeric_passa']==1
