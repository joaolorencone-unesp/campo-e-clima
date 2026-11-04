import pytest
from scripts.agro_ensemble import model_samples, blend_samples


def payload(t=28, rh=50, wind=7, gust=21):
    return {'hourly': {'time': ['2026-11-04T14:00','2026-11-04T15:00'],
        'temperature_2m_member01':[t,t], 'temperature_2m_member02':[30,31],
        'relative_humidity_2m_member01':[rh,rh], 'relative_humidity_2m_member02':[65,65],
        'wind_speed_10m_member01':[wind,wind], 'wind_gusts_10m_member01':[gust,gust]}}


def test_vpd_pairs_same_member_not_cross_member():
    m=model_samples(payload(),future_start='2026-11-04T14:00')
    assert sorted(m['2026-11-04T14:00']['vpd_kpa']) == pytest.approx([1.485, 1.889],abs=.003)


def test_invalid_rh_excludes_member_vpd_without_excluding_wind():
    x=payload();x['hourly']['relative_humidity_2m_member02']=[None,120]
    m=model_samples(x)
    assert len(m['2026-11-04T14:00']['vpd_kpa'])==1
    assert m['2026-11-04T15:00']['wind_gusts_10m']==[21]
    assert len(m['2026-11-04T14:00']['temperature_2m'])==2


def test_no_fake_gust_and_equal_model_weight():
    a=model_samples(payload(t=20,gust=20))
    b=model_samples(payload(t=40,gust=40))
    x=blend_samples({'a':a,'b':b})[0]['variables']
    assert x['wind_gusts_10m']['model_count']==2
    assert x['wind_gusts_10m']['p_gt_30']==pytest.approx(.5)
    assert x['temperature_2m']['member_count']==4
    del b['2026-11-04T14:00']['wind_gusts_10m']
    x=blend_samples({'a':a,'b':b})[0]['variables']
    assert x['wind_gusts_10m']['model_count']==1
    assert x['wind_gusts_10m']['p_gt_30']==0
    assert x['temperature_2m']['model_count']==2


def test_missing_all_data_leaves_blank():
    assert blend_samples({'a':model_samples({'hourly':{'time':['2026-11-04T14:00']}})})==[]
