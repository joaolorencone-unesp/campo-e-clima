from scripts.collect import weighted_quantile, mix_days, model_daily_rain, model_daily_gust, mix_gust_days
from scripts.verify import brier_score

def test_equal_weight_per_model_not_per_member():
    sample = {'a': {'days': {'2026-10-27':[0,0,0,0]}},
              'b': {'days': {'2026-10-27':[20]}}}
    out = mix_days(sample)[0]
    assert out['mean_mm'] == 10
    assert out['p_gt_10_mm'] == 0.5
    assert out['model_count'] == 2

def test_weighted_quantile():
    assert weighted_quantile([(0,.75),(20,.25)], .5) == 0
    assert weighted_quantile([(0,.75),(20,.25)], .9) == 20

def test_missing_hour_excludes_member():
    times = [f'2026-10-27T{h:02d}:00' for h in range(24)]
    vals = [0.1]*24
    damaged = [0.2]*24
    damaged[4] = None
    got = model_daily_rain({'hourly': {'time':times,'precipitation_member01':vals,
                                      'precipitation_member02':damaged}})
    assert got['member_count'] == 2
    assert len(got['days']['2026-10-27']) == 1

def test_brier():
    assert brier_score([0,1],[0,1]) == 0


def test_gust_uses_max_not_sum():
    times = [f'2026-10-27T{h:02d}:00' for h in range(24)]
    gusts = [14.0]*24
    gusts[12] = 41
    g = model_daily_gust({'hourly': {'time':times,'wind_gusts_10m_member01':gusts}})
    assert g['days']['2026-10-27'] == [41]
    out = mix_gust_days({'a':g})[0]
    assert out['p_gt_40_kmh'] == 1
    assert out['mean_kmh'] == 41


def test_missing_gust_does_not_mean_zero():
    times = [f'2026-10-27T{h:02d}:00' for h in range(24)]
    gusts = [22.0]*24
    gusts[9] = None
    g = model_daily_gust({'hourly': {'time':times,'wind_gusts_10m_member01':gusts}})
    assert not g['days']['2026-10-27']
    assert mix_gust_days({'a':g}) == []


def test_rain_rejects_negative_and_nan():
    times = [f'2026-10-27T{h:02d}:00' for h in range(24)]
    vals = [0.2]*24
    vals[1] = float('nan')
    assert model_daily_rain({'hourly':{'time':times,'precipitation_member01': vals}})['days']['2026-10-27']==[]
