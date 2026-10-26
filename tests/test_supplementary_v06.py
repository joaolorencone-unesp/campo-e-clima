import datetime as dt
from pathlib import Path
import pytest
from scripts.sources.embrapa_export import parse_export, save_csv_from_export
from scripts.sources.supplementary import (parse_cptec_xml,parse_openweather,parse_nasa_power,
                                           parse_extended_ecmwf,load_export_provisional)

def test_html_export_quarantines_before_station_started():
    html='<table id="tabela"><tbody>'
    def row(day,rain):
        vals=[day,'25.0','30.0','12:00','20','04:00','70','90','01:00','40','14:00','1.0','N','6','12:00',str(rain),'15','4.5']
        return '<tr>'+''.join(f'<td>{x}</td>' for x in vals)+'</tr>'
    html+=row('30/11/2024',5)+row('01/12/2024',0)+row('02/12/2024',8)+'</tbody></table>'
    output=parse_export(html,asof=dt.date(2026,10,26))
    assert output['state']=='provisional'
    assert output['station_id'] is None
    assert output['record_count']==2
    assert output['quarantined_count']==1
    assert output['records'][0]['precipitation_mm']==0


def test_real_export_covers_complete_2024_2026():
    p=Path('data/observacoes/embrapa_exportacao_provisoria.csv')
    r=load_export_provisional(p)
    assert r['state']=='provisional'
    assert r['station_verified'] is False
    assert r['record_count']==694
    assert r['date_first']=='2024-12-01'
    assert r['date_last']=='2026-10-25'
    assert r['rain_nonmissing_days']==694


def test_cptec_xml_municipality_validates_name_and_state():
    xml='<cidade><nome>Naviraí</nome><uf>MS</uf><atualizacao>2026-10-26</atualizacao><previsao><dia>2026-10-27</dia><tempo>pc</tempo><maxima>28</maxima><minima>19</minima><iuv>10</iuv></previsao></cidade>'
    r=parse_cptec_xml(xml,asof=dt.date(2026,10,26))
    assert r['state']=='ok' and r['days'][0]['tmax_c']==28
    assert 'p_gt' not in str(r)
    with pytest.raises(ValueError):parse_cptec_xml(xml.replace('<uf>MS</uf>','<uf>PR</uf>'),asof=dt.date(2026,10,26))
    with pytest.raises(ValueError):parse_cptec_xml(xml.replace('2026-10-26</atualizacao>','2026-10-01</atualizacao>'),asof=dt.date(2026,10,26))


def test_power_fills_and_grid_provenance():
    p={'properties':{'parameter':{'PRECTOTCORR':{'20261020':8.2,'20261021':-999.0,'20261022':0.0}}}}
    r=parse_nasa_power(p)
    assert len(r['records'])==2
    assert r['records'][1]['precipitation_estimated_mm']==0
    assert 'grade' in r['note']


def test_openweather_not_fake_ensemble_member():
    r=parse_openweather({'lat':-23.065,'lon':-54.190,
       'daily':[{'dt':1793059200,'pop':0.7,'rain':4.8,'temp':{'max':28,'min':17}}]})
    assert len(r['daily'])==1
    assert 'não adicionar' in r['note']
    with pytest.raises(ValueError):parse_openweather({'lat':-30,'lon':-50,'daily':[]})


def test_ecmwf_weekly_correct_6hourly_integration():
    d0=dt.date(2026,10,26)
    times=[(dt.datetime.combine(d0,dt.time())+dt.timedelta(hours=6*i)).strftime('%Y-%m-%dT%H:%M') for i in range(240)]
    p={'utc_offset_seconds':-14400,'hourly':{'time':times,'precipitation_member00':[0.5]*240,'precipitation_member01':[1.0]*240}}
    r=parse_extended_ecmwf(p,day0=d0)
    assert r['state']=='ok'
    assert r['weeks'][0]['rain_week_p10_mm']==14.0
    assert r['weeks'][0]['rain_week_p90_mm']==28.0
    assert r['weeks'][0]['member_count']==2
    with pytest.raises(ValueError):parse_extended_ecmwf({'utc_offset_seconds':0,'hourly':p['hourly']},day0=d0)
