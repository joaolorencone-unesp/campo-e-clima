import pytest
from scripts.sources.official import parse_alerts, parse_stations, haversine_km
from scripts.sources.embrapa import read_history


def test_inmet_alerts_by_ibge_never_region_only():
    p={'hoje':[{'id_aviso':11,'descricao':'Tempestade','geocodes':'5005707,5004700','severidade':'Perigo Potencial','data_inicio':'2026-10-26T00:00:00Z','hora_inicio':'12:00'},
               {'id_aviso':12,'descricao':'Vento','geocodes':'5002704'}],
       'futuro':[{'id_aviso':11,'id_sequencia':2,'descricao':'Tempestade alterada','geocodes':['5005707'],'severidade':'Perigo'}]}
    o=parse_alerts(p)
    assert o['records_received']==3
    assert len(o['municipal_alerts'])==1
    assert o['municipal_alerts'][0]['type']=='Tempestade alterada'
    assert o['municipal_alerts'][0]['timezone_confirmed'] is False


def test_region_alert_without_municipal_geocode_never_labeled_local():
    p={'hoje':[{'id_aviso':99,'estados':'MS','descricao':'Aviso','geocodes':'5002704'}], 'futuro':[]}
    assert parse_alerts(p)['municipal_alerts']==[]


def test_inmet_malformed_fails_closed():
    with pytest.raises(ValueError):parse_alerts({'foo':[]})


def test_nearest_inmet_station_sorted():
    p=[{'SG_ESTADO':'MS','VL_LATITUDE':'-23.08','VL_LONGITUDE':'-54.20','CD_ESTACAO':'A001','DC_NOME':'Perto','CD_SITUACAO':'Operante'},
       {'SG_ESTADO':'MS','VL_LATITUDE':'-20','VL_LONGITUDE':'-53','CD_ESTACAO':'A002','DC_NOME':'Longe','CD_SITUACAO':'Pane'},
       {'SG_ESTADO':'MT','VL_LATITUDE':'-23.065','VL_LONGITUDE':'-54.190','CD_ESTACAO':'A003','DC_NOME':'Excluída'}]
    o=parse_stations(p)
    assert o['nearest'][0]['station_code']=='A001'
    assert len(o['nearest'])==2
    assert haversine_km(-23.065,-54.190,-23.065,-54.190)<.00001


def test_embrapa_requires_station_6():
    s='station_id,date,precipitation_mm\n1,2026-10-01,3.0\n'
    x=read_history(s,asof=__import__('datetime').date(2026,10,26))
    assert x['state']=='invalid' and not x['records']


def test_embrapa_missing_is_not_zero():
    import datetime as dt
    s='station_id;date;precipitation_mm;temperature_mean_c\n6;23/10/2026;;24,1\n6;24/10/2026;0,0;23,0\n'
    o=read_history(s,asof=dt.date(2026,10,26))
    assert o['state']=='ok' and o['rain_nonmissing_days']==1
    assert o['records'][0]['precipitation_mm'] is None
    assert o['records'][1]['precipitation_mm']==0.0


def test_embrapa_reject_duplicates_and_future():
    import datetime as dt
    s='station_id,date,precipitation_mm\n6,2026-10-20,2\n6,2026-10-20,3\n6,2026-11-02,4\n'
    o=read_history(s,asof=dt.date(2026,10,26))
    assert o['state']=='invalid' and len(o['errors'])==2


def test_embrapa_no_rows_no_rain_history():
    o=read_history('station_id,date,precipitation_mm\n')
    assert o['state']=='no_data' and not o['records']


def test_inmet_daily_observed_with_station_provenance():
    from scripts.sources.official import parse_inmet_daily
    data=[{'CD_ESTACAO':'A001','DT_MEDICAO':'2026-10-20','CHUVA':'0','TEMP_MED':'25.2','UMID_MED':'74'},
          {'CD_ESTACAO':'A001','DT_MEDICAO':'2026-10-21','CHUVA':None}]
    r=parse_inmet_daily(data,station_code='A001')
    assert r['state']=='ok' and r['records'][0]['precipitation_mm']==0
    assert r['records'][1]['precipitation_mm'] is None
    with pytest.raises(ValueError):parse_inmet_daily([{'CD_ESTACAO':'A999','DT_MEDICAO':'2026-10-20'}],station_code='A001')
