from scripts.collect import model_hourly_rain, mix_hourly_rain, rain_models_comparison


def test_same_member_windows_and_equal_model_weights():
    times = [f'2026-10-27T{hour:02d}:00' for hour in range(8)]
    a = {'hourly': {'time':times, 'precipitation_member01':[2]*8,
                    'precipitation_member02':[0]*8}}
    b = {'hourly': {'time':times, 'precipitation_member01':[0]*8}}
    models={'A':model_hourly_rain(a),'B':model_hourly_rain(b)}
    hourly=mix_hourly_rain(models)
    row=hourly[0]['windows']['3']
    assert row['models']==2
    assert row['members']==3
    assert row['mean_mm']==1.5  # (A 3.0 + B 0.0)/2
    assert row['p_gt_5_mm']==.25


def test_missing_member_window_excluded_no_imputation():
    times=[f'2026-10-27T{h:02d}:00' for h in range(7)]
    raw={'hourly':{'time':times,
                   'precipitation_member01':[0.5]*7,
                   'precipitation_member02':[1,None,1,1,1,1,1]}}
    row=mix_hourly_rain({'A':model_hourly_rain(raw)})[0]['windows']['3']
    assert row['members']==1
    assert row['p_gt_1_mm']==1.0


def test_non_hourly_grid_excluded_for_long_windows():
    times=['2026-10-27T00:00','2026-10-27T03:00','2026-10-27T06:00']
    got=model_hourly_rain({'hourly':{'time':times,'precipitation_member01':[4,3,2]}})
    assert '1' in {str(k) for k in got[times[0]]}
    assert 3 not in got[times[0]]


def test_model_comparison_uses_member_values():
    out=rain_models_comparison({'IFS': {'days':{'2026-10-27':[0,10]}}})
    assert out[0]['mean_mm']==5
    assert out[0]['p_gt_5_mm']==.5
