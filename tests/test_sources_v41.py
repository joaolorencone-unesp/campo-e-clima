"""v4.1 sources: CEMADEN parsers, INMET alerts RSS fallback, frost thresholds (offline fixtures)."""
import datetime as dt
from scripts.sources import cemaden, official
from scripts import agro_ensemble


def test_cemaden_catalog_and_rain_parsers_are_tolerant():
    catalog = [{'codEstacao': '500570701A', 'nomeEstacao': 'Naviraí centro', 'latitude': '-23.07', 'longitude': '-54.20', 'codIbge': 5005707, 'municipio': 'NAVIRAÍ', 'tipoEstacao': 'Pluviométrica'},
               {'codEstacao': 'X', 'latitude': '-20.0', 'longitude': '-54.0'}, 'lixo']
    near = cemaden.parse_stations(catalog, -23.065, -54.19, radius_km=80)
    assert [s['code'] for s in near] == ['500570701A'] and near[0]['distance_km'] < 2
    since = dt.datetime(2026, 11, 4, 12, tzinfo=dt.timezone.utc)
    text = 'cabecalho qualquer\nmunicipio;codEstacao;uf;nomeEstacao;latitude;longitude;datahora;sensor;valor\nNAVIRAI;500570701A;MS;Centro;-23.07;-54.20;2026-11-04 13:00:00;chuva;1,2\nNAVIRAI;500570701A;MS;Centro;-23.07;-54.20;2026-11-04 11:00:00;chuva;9.9\nNAVIRAI;500570701A;MS;Centro;-23.07;-54.20;2026-11-04 14:10:00;chuva;0.8\nNAVIRAI;500570701A;MS;Centro;-23.07;-54.20;2026-11-04 15:10:00;temperatura;25'
    rain = cemaden.parse_rain(text, codes={'500570701A'}, since_utc=since)
    assert rain['500570701A']['rain_24h_mm'] == 2.0 and rain['500570701A']['readings'] == 2 and rain['500570701A']['last_reading_utc'].startswith('2026-11-04T14:10')
    rows = [{'codestacao': '500570701A', 'datahora': '2026-11-04T13:00:00', 'sensor': 'chuva', 'valor': 3}]
    assert cemaden.parse_rain(rows, codes={'500570701A'}, since_utc=since)['500570701A']['rain_24h_mm'] == 3
    assert cemaden.collect_cemaden(-23.065, -54.19, enabled=False)['state'] == 'disabled'
    import os
    os.environ.pop('CEMADEN_TOKEN', None)
    assert cemaden.collect_cemaden(-23.065, -54.19, enabled=True)['state'] == 'requires_registration', 'no request without a token'


def test_inmet_rss_fallback_filters_the_municipality():
    xml = '''<rss><channel><item><title>Aviso de Tempestade - Perigo Potencial</title><link>https://alertas2.inmet.gov.br/1</link><guid>1</guid>
    <description><![CDATA[Início: 2026-11-05 10:00 Fim: 2026-11-06 09:59 Municípios: Naviraí - MS, Juti - MS]]></description><pubDate>Thu, 05 Nov 2026 09:00:00</pubDate></item>
    <item><title>Aviso de Chuvas Intensas - Perigo</title><guid>2</guid><description>Municípios: Campo Grande - MS</description></item></channel></rss>'''
    out = official.parse_alerts_rss(xml)
    assert out['state'] == 'ok' and len(out['municipal_alerts']) == 1
    a = out['municipal_alerts'][0]
    assert a['severity'] == 'Perigo Potencial' and a['start_date_source'] == '2026-11-05' and a['end_hour_source'] == '09:59' and a['municipal_coverage_confirmed'] is False
    assert official.parse_alerts_rss('<rss><channel></channel></rss>')['warnings'][-1].startswith('Consulta retornou zero')


def test_frost_thresholds_present_in_blend():
    labels = [name for name, _ in agro_ensemble.THRESHOLDS['temperature_2m']]
    assert {'p_le_5', 'p_le_3', 'p_le_1'} <= set(labels)
