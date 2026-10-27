from scripts.sources.official import parse_inmet_hourly, collect_nearby_station_hourly
from unittest.mock import patch


def test_station_hourly_parsing_time_units_and_nulls():
    rows=[{'CD_ESTACAO':'S735','DT_MEDICAO':'2026-10-27','HR_MEDICAO':'1500',
           'TEM_INS':'28,3','UMD_INS':'64','VEN_VEL':'2,5','VEN_RAJ':'4,0',
           'VEN_DIR':'185','CHUVA':'0,2'},
          {'CD_ESTACAO':'S735','DT_MEDICAO':'2026-10-27','HR_MEDICAO':'1600',
           'TEM_INS':'null','UMD_INS':None,'VEN_VEL':None,'VEN_RAJ':None,'CHUVA':None}]
    out=parse_inmet_hourly(rows,station_code='S735')
    assert out['state']=='ok' and len(out['records'])==1
    row=out['records'][0]
    assert row['valid_at_local'].startswith('2026-10-27T11:00')
    assert row['precipitation_previous_hour_mm']==.2
    assert row['wind_kmh']==9.0 and row['gust_kmh']==14.4


def test_wrong_station_rejected():
    try:
        parse_inmet_hourly([{'CD_ESTACAO':'A752','DT_MEDICAO':'2026-10-27','HR_MEDICAO':'1200','CHUVA':1}],station_code='S735')
    except ValueError as e:
        assert 'another station' in str(e)
    else:assert False, 'Wrong station accepted'


def test_fail_closed_http_without_inventing_observation():
    catalog={'state':'ok','nearest':[{'station_code':'S735','name':'NAVIRAI FAZ SANTA HELENA',
               'distance_km':37.6,'status':'Operante','entity':'SEMADESC-MS'}]}
    with patch('scripts.sources.official.http_json',side_effect=ValueError('bloqueado')):
        response=collect_nearby_station_hourly(catalog)
    assert response['state']=='unavailable'
    assert response['station_code']=='S735'
    assert 'records' not in response
