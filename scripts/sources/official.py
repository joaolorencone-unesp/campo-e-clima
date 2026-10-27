"""Public-official source adapters. Never synthesize observations or warnings.

INMET warnings: include only notices explicitly listing Naviraí IBGE 5005707.
INMET registry: station location/status metadata, not meteorological measurements.
"""
from __future__ import annotations
import datetime as dt
import math
import re
from typing import Any
import requests

NAVIRAI_IBGE = '5005707'
LAT, LON = -23.065, -54.190
ALERTS_URL = 'https://apiprevmet3.inmet.gov.br/avisos/ativos'
STATIONS_URL = 'https://apitempo.inmet.gov.br/estacoes/T'


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')


def http_json(url: str, timeout: int = 18) -> Any:
    r = requests.get(url, timeout=timeout, headers={'User-Agent': 'Campo-e-Clima/0.5 (scientific open weather dashboard)'})
    r.raise_for_status()
    return r.json()


def tokens(value: Any) -> list[str]:
    if value is None: return []
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    return [v.strip() for v in str(value).split(',') if v.strip()]


def parse_alerts(payload: Any) -> dict:
    """Return municipality-confirmed notices, retaining the source time strings.

    API dates and separate clock fields do not explicitly define local timezone;
    the GUI must not silently convert them to UTC-4.
    """
    if not isinstance(payload, dict) or not any(k in payload for k in ('hoje', 'futuro')):
        raise ValueError('INMET response format unexpected (missing hoje/futuro)')
    selected = {}
    total = 0
    for bucket in ('hoje', 'futuro'):
        entries = payload.get(bucket) or []
        if not isinstance(entries, list): raise ValueError(f'Invalid INMET bucket {bucket}')
        for a in entries:
            if not isinstance(a, dict): continue
            total += 1
            geocodes = tokens(a.get('geocodes'))
            if NAVIRAI_IBGE not in geocodes:
                continue
            identifier = str(a.get('id_aviso') or a.get('id') or '').strip()
            if not identifier:
                continue
            seq = int(a.get('id_sequencia') or 0)
            prev = selected.get(identifier)
            if prev is not None and prev['_seq'] > seq: continue
            selected[identifier] = {
                '_seq': seq, 'id': identifier,
                'type': str(a.get('descricao') or 'Aviso meteorológico'),
                'severity': str(a.get('severidade') or 'Não informada'),
                'color': str(a.get('aviso_cor') or ''),
                'start_date_source':str(a.get('data_inicio') or '')[:10],
                'start_hour_source':str(a.get('hora_inicio') or ''),
                'end_date_source':str(a.get('data_fim') or '')[:10],
                'end_hour_source':str(a.get('hora_fim') or ''),
                'timezone_confirmed': False,
                'municipality_name': 'Naviraí — MS', 'ibge':NAVIRAI_IBGE,
                'municipal_coverage_confirmed': True,
                'terminated': bool(a.get('encerrado')),
                'risks':tokens(a.get('riscos'))[:8],
                'instructions':tokens(a.get('instrucoes'))[:8],
                'source_url':ALERTS_URL,
            }
    warnings = []
    if total == 0: warnings.append('Consulta retornou zero avisos: não equivale a ausência de risco meteorológico.')
    alerts = [{k:v for k,v in a.items() if k!='_seq'} for a in selected.values() if not a['terminated']]
    return {'state':'ok', 'source':'INMET', 'source_url':ALERTS_URL, 'queried_at_utc':now_utc(),
            'records_received':total, 'municipal_alerts':alerts,
            'coverage_note':'Filtrado por IBGE 5005707; horário exibido como na fonte, sem conversão de fuso não documentado.',
            'warnings':warnings}


def haversine_km(lat1:float, lon1:float, lat2:float, lon2:float) -> float:
    lat1,lon1,lat2,lon2=map(math.radians,(lat1,lon1,lat2,lon2))
    dlat=lat2-lat1; dlon=lon2-lon1
    a=math.sin(dlat/2)**2+math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return 6371.0088*2*math.asin(min(1,math.sqrt(a)))


def parse_stations(payload: Any, n: int = 16) -> dict:
    if not isinstance(payload, list): raise ValueError('Unexpected INMET stations registry')
    stations=[]
    for row in payload:
        if not isinstance(row,dict):continue
        if row.get('SG_ESTADO') != 'MS': continue
        try:
            lat=float(str(row['VL_LATITUDE']).replace(',','.'))
            lon=float(str(row['VL_LONGITUDE']).replace(',','.'))
            dist=haversine_km(LAT,LON,lat,lon)
        except (TypeError,ValueError,KeyError):continue
        stations.append({'station_code':str(row.get('CD_ESTACAO') or ''),
                        'name':str(row.get('DC_NOME') or ''),
                        'distance_km':round(dist,1),
                        'latitude':lat,'longitude':lon,
                        'status':str(row.get('CD_SITUACAO') or 'Não informado'),
                        'altitude_m':row.get('VL_ALTITUDE'),
                        'entity':row.get('SG_ENTIDADE'),
                        'note':'Somente metadados: nenhuma leitura observada foi obtida desta lista.'})
    stations.sort(key=lambda x:x['distance_km'])
    return {'state':'ok','source':'INMET – catálogo automático','source_url':STATIONS_URL,
            'queried_at_utc':now_utc(), 'ms_stations_seen':len(stations), 'nearest':stations[:n],
            'note':'Distâncias em linha reta até a sede de Naviraí; estação mais próxima pode não representar o talhão.'}


def collect_official() -> dict:
    out={}
    for key,url,parser in [('inmet_alerts',ALERTS_URL,parse_alerts),
                           ('inmet_stations',STATIONS_URL,parse_stations)]:
        try:
            out[key]=parser(http_json(url))
        except (requests.RequestException, ValueError, TypeError) as ex:
            out[key]={'state':'unavailable','source_url':url,'queried_at_utc':now_utc(),
                      'error':str(ex)[:210], 'note':'Falha de coleta não significa ausência de risco.'}
    out['inmet_hourly_nearby']=collect_nearby_station_hourly(out.get('inmet_stations',{}))
    out['inmet_daily_nearby']=collect_nearby_station_daily(out.get('inmet_stations',{}))
    return out



def parse_inmet_hourly(payload: Any, *, station_code: str) -> dict:
    """Parse public INMET-style hourly records; preserve source station identity.

    INMET automatic-station DT_MEDICAO/HR_MEDICAO are conventionally UTC.
    Do not treat observations from a nearby station as measurements at the farm.
    An empty response does not equal calm weather, and a 204 never equals no rain.
    """
    from zoneinfo import ZoneInfo
    if not isinstance(payload, list):
        raise ValueError('INMET hourly response is not a JSON list')
    local=ZoneInfo('America/Campo_Grande');records={}
    for r in payload:
        if not isinstance(r,dict):continue
        station=str(r.get('CD_ESTACAO') or station_code).strip()
        if station != station_code:raise ValueError('INMET returned records from another station')
        raw_day=str(r.get('DT_MEDICAO') or '')[:10]
        raw_hour=str(r.get('HR_MEDICAO') or '').strip().zfill(4)
        if len(raw_hour)!=4 or not raw_hour.isdigit():continue
        hh,mm=int(raw_hour[:2]),int(raw_hour[2:])
        if hh>=24 or mm>=60:continue
        try:utc=dt.datetime.fromisoformat(raw_day).replace(hour=hh,minute=mm,tzinfo=dt.timezone.utc)
        except ValueError:continue
        def obs(*keys,low=-float('inf'),high=float('inf')):
            for key in keys:
                raw=r.get(key)
                if raw is None or str(raw).strip().lower() in ('','null','none','nan','-9999'):continue
                try:
                    val=float(str(raw).replace(',','.'))
                    if math.isfinite(val) and low<=val<=high:return val
                except ValueError:pass
            return None
        wind_ms=obs('VEN_VEL',low=0,high=80)
        gust_ms=obs('VEN_RAJ',low=0,high=120)
        record={
            'valid_at_utc':utc.isoformat(timespec='minutes'),
            'valid_at_local':utc.astimezone(local).isoformat(timespec='minutes'),
            'temperature_c':obs('TEM_INS',low=-50,high=65),
            'rh_pct':obs('UMD_INS',low=0,high=100),
            'precipitation_previous_hour_mm':obs('CHUVA',low=0,high=300),
            'wind_kmh':round(wind_ms*3.6,2) if wind_ms is not None else None,
            'gust_kmh':round(gust_ms*3.6,2) if gust_ms is not None else None,
            'wind_from_deg':obs('VEN_DIR',low=0,high=360),
        }
        if any(record.get(k) is not None for k in ('temperature_c','rh_pct','precipitation_previous_hour_mm','wind_kmh','gust_kmh')):
            records[record['valid_at_utc']]=record
    return {'state':'ok' if records else 'no_data','station_code':station_code,
            'records':sorted(records.values(),key=lambda v:v['valid_at_utc'])[-72:],
            'data_type':'OBSERVAÇÃO DE ESTAÇÃO VIZINHA (NÃO É PREVISÃO)',
            'time_note':'INMET DT_MEDICAO/HR_MEDICAO interpretados como UTC e convertidos para UTC−4. Conferir documentação da estação.',
            'units_note':'VEN_VEL/VEN_RAJ em m/s na origem, convertidos para km/h; CHUVA em mm na hora anterior.',
            'representativeness':'Medições pontuais da estação, não do talhão; interpolação espacial não aplicada.'}


def collect_nearby_station_hourly(station_meta:dict, *, max_distance_km:int=120)->dict:
    """Best-effort *documented observed* hourly endpoint; fail closed on blocks.

    Automatic station data may be restricted to INMET official interfaces.
    We do not automate authentication bypass or scraped portals.
    """
    out={'state':'unavailable','source':'INMET — observações horárias (estação próxima)',
         'queried_at_utc':now_utc(),'source_url':'https://apitempo.inmet.gov.br/',
         'note':'Sem leitura não significa sem vento/sem chuva. Fonte INMET ou rede integrada; conferir entidade operadora.'}
    if station_meta.get('state')!='ok':return {**out,'error':'Catálogo de estações não retornou'}
    options=[x for x in station_meta.get('nearest',[]) if x['distance_km']<=max_distance_km and str(x['status']).casefold()=='operante']
    if not options:return {**out,'state':'not_covered','error':'Sem estação listada como operante nesta distância'}
    station=options[0]
    today=dt.datetime.now(dt.timezone.utc).date()
    start=today-dt.timedelta(days=3)
    url=f'https://apitempo.inmet.gov.br/estacao/{start.isoformat()}/{today.isoformat()}/{station["station_code"]}'
    common={**out,'station_code':station['station_code'],'station_name':station['name'],
            'distance_km':station['distance_km'],'entity':station.get('entity'),'source_url':url}
    try:
        parsed=parse_inmet_hourly(http_json(url, timeout=12),station_code=station['station_code'])
        return {**common,**parsed}
    except (requests.RequestException, ValueError, TypeError) as exc:
        # Errors may include full URL, but no tokens are used in this public call.
        return {**common,'error':str(exc)[:210],
                'fallback_url':'https://tempo.inmet.gov.br/TabelaEstacoes',
                'import_url':'https://portal.inmet.gov.br/dadoshistoricos/',
                'note':'Endpoint de observações não acessível no ambiente de coleta. Tabela oficial e ZIPs históricos são alternativas gratuitas.'}

def parse_inmet_daily(payload:Any, *, station_code:str) -> dict:
    """Read only observed daily INMET station series; not a Naviraí measurement.

    Never silently convert remote station measurements to municipal observations.
    """
    if not isinstance(payload,list): raise ValueError('INMET daily payload is not a list')
    parsed=[]
    for r in payload:
        if not isinstance(r,dict): continue
        if r.get('CD_ESTACAO') and str(r['CD_ESTACAO']).strip()!=station_code:
            raise ValueError('Daily records refer to unexpected station')
        d=str(r.get('DT_MEDICAO') or '')[:10]
        try:dt.date.fromisoformat(d)
        except ValueError:continue
        def v(k):
            raw=r.get(k)
            if raw is None or str(raw).strip() in ('','null','None'):return None
            try:
                x=float(str(raw).replace(',','.'))
                return x if math.isfinite(x) else None
            except ValueError:return None
        rain=v('CHUVA')
        if rain is not None and not 0 <= rain <= 600:rain=None
        parsed.append({'date':d,'precipitation_mm':rain,
                       'temperature_mean_c':v('TEMP_MED'),
                       'relative_humidity_mean_pct':v('UMID_MED')})
    unique={x['date']:x for x in parsed}
    return {'state':'ok' if unique else 'no_data','station_code':station_code,
            'records':sorted(unique.values(),key=lambda x:x['date']),
            'note':'Observações de estação vizinha do INMET; não correspondem necessariamente à sede de Naviraí.'}


def collect_nearby_station_daily(station_meta:dict, *, max_distance_km:int=180) -> dict:
    """Best-effort: daily API may restrict external requests. Fail closed."""
    base={'source':'INMET – estação vizinha (dados diários)',
          'queried_at_utc':now_utc(),
          'source_url':'https://apitempo.inmet.gov.br/',
          'note':'Só observações identificadas por estação, sem interpolação para Naviraí.'}
    if station_meta.get('state')!='ok':return {**base,'state':'unavailable','error':'Cadastro de estações indisponível'}
    candidates=[s for s in station_meta.get('nearest',[]) if s['distance_km']<=max_distance_km and s['status'].casefold()=='operante']
    if not candidates:
        return {**base,'state':'not_covered','error':f'Nenhuma estação operante a até {max_distance_km} km no inventário consultado.'}
    s=candidates[0]
    today=dt.datetime.now(dt.timezone.utc).date()
    start=today-dt.timedelta(days=8)
    url=f'https://apitempo.inmet.gov.br/estacao/diaria/{start.isoformat()}/{today.isoformat()}/{s["station_code"]}'
    try:
        raw=http_json(url)
        out=parse_inmet_daily(raw,station_code=s['station_code'])
        return {**base,**out,'source_url':url,'station_name':s['name'],
                'distance_km':s['distance_km'],'latitude':s['latitude'],'longitude':s['longitude']}
    except (requests.RequestException,ValueError,TypeError) as ex:
        return {**base,'state':'unavailable','station_code':s['station_code'],
                'station_name':s['name'],'distance_km':s['distance_km'],
                'source_url':url,'error':str(ex)[:190],
                'note':'Leituras diárias não disponíveis neste acesso; não considerar ausência de chuva.'}
