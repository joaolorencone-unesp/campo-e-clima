from scripts.spraying import (get_member_dict, member_vpd, classify_member,
                             read_joint_members, mix_joint_hourly,
                             mix_joint_windows2h)


def make_model(times, config):
    h = {'time': times}
    for key, members in config.items():
        for mid, seq in members.items():
            h[f'{key}_member{mid}'] = seq
    return {'hourly':h}


def base_members(times, wind=(5,5,5,5), rh=(70,70,70,70), precip=(0,0,0,0)):
    def pad(seq): return (list(seq)+[seq[-1]]*len(times))[:len(times)]
    return make_model(times, {
        'temperature_2m':{'01':[23]*len(times)},
        'relative_humidity_2m':{'01':pad(rh)},
        'wind_speed_10m':{'01':pad(wind)},
        'wind_gusts_10m':{'01':[9]*len(times)},
        'wind_direction_10m':{'01':[120]*len(times)},
        'precipitation':{'01':pad(precip)},
    })


def test_vpd_formula():
    assert 0.8 < member_vpd(25,70) < 1.1


def test_identifiers_must_match_not_combine_unrelated_members():
    times=['2026-10-27T09:00','2026-10-27T10:00','2026-10-27T11:00']
    p=base_members(times+['2026-10-27T12:00'])
    p['hourly']['wind_direction_10m_member02']=p['hourly'].pop('wind_direction_10m_member01')
    assert read_joint_members(p)['members_available']==0


def test_rain_next_three_hours_uses_same_member_trajectory():
    times=[f'2026-10-27T{h:02d}:00' for h in range(9,15)]
    p=base_members(times,precip=(0,0,1,0))
    got=read_joint_members(p)
    assert got['times'][times[0]]['01']['herb'][0]=='restrito'
    assert 'chuva_3h' in got['times'][times[0]]['01']['herb'][1]


def test_two_hour_window_restricted_when_one_hour_fails():
    times=[f'2026-10-27T{h:02d}:00' for h in range(9,15)]
    a=read_joint_members(base_members(times,wind=(5,16,5,5)))
    out=mix_joint_windows2h({'A':a})
    assert out[0]['herb']['restrito']==1
    assert out[0]['herb']['passa']==0


def test_model_equal_total_weight_vs_raw_members():
    times=[f'2026-10-27T{h:02d}:00' for h in range(9,15)]
    a=base_members(times, wind=(16,16,16,16))
    b=base_members(times)
    # Two members in model A, one in model B => total model weighting 50/50
    for key in ['temperature_2m','relative_humidity_2m','wind_speed_10m',
                'wind_gusts_10m','wind_direction_10m','precipitation']:
        a['hourly'][key+'_member02']=list(a['hourly'][key+'_member01'])
    got=mix_joint_hourly({'A':read_joint_members(a),'B':read_joint_members(b)})
    assert got[0]['herb']['passa']==0.5
    assert got[0]['herb']['restrito']==0.5
    assert got[0]['herb']['members']==3


def test_nulls_not_zero_and_future_window_required():
    times=[f'2026-10-27T{h:02d}:00' for h in range(9,15)]
    p=base_members(times)
    p['hourly']['wind_speed_10m_member01'][0]=None
    got=read_joint_members(p)
    assert times[0] not in got['times']
    assert times[-2] not in got['times']  # lacks 3 future hours


def test_missing_model_is_not_favorable():
    times=[f'2026-10-27T{h:02d}:00' for h in range(9,15)]
    complete=read_joint_members(base_members(times))
    incomplete=base_members(times)
    del incomplete['hourly']['relative_humidity_2m_member01']
    got=mix_joint_hourly({'good':complete,'missing':read_joint_members(incomplete)})
    assert got[0]['fung']['models']==1
    assert got[0]['fung']['passa']==1


def test_night_without_local_inversion_is_indeterminate_not_favorable():
    from scripts.spraying import classify_member
    values={'temperature_2m':23,'relative_humidity_2m':70,'wind_speed_10m':5,
            'wind_gusts_10m':9,'wind_direction_10m':120,'rain_next_3h_mm':0}
    assert classify_member(values,'herb',local_hour=23)[0]=='indeterminado'
    assert classify_member(values,'herb',local_hour=10)[0]=='passa'
    values['wind_speed_10m']=19
    assert classify_member(values,'herb',local_hour=23)[0]=='restrito'

def test_future_rain_does_not_count_precipitation_from_current_hour():
    times=[f'2026-10-27T{h:02d}:00' for h in range(9,15)]
    got=read_joint_members(base_members(times,precip=(3,0,0,0,0,0)))
    assert got['times'][times[0]]['01']['herb'][0]=='passa'
    got=read_joint_members(base_members(times,precip=(0,0,0,2,0,0)))
    assert got['times'][times[0]]['01']['herb'][0]=='restrito'
