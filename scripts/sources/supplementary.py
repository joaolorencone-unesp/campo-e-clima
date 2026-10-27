"""Extra services. Source failures are explicit; never invent observations or estimates."""
from __future__ import annotations
import datetime as dt
import json
import math
import os
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any
import requests
from .embrapa_export import MIN_CONFIRMED_START

LAT,LON=-23.065,-54.190
TZ='America/Campo_Grande'
URL_CPTEC=f'https://servicos.cptec.inpe.br/XML/cidade/7dias/{LAT}/{LON}/previsaoLatLon.xml'
URL_OPENWEATHER='https://api.openweathermap.org/data/3.0/onecall'
URL_POWER='https://power.larc.nasa.gov/api/temporal/daily/point'
URL_SOIL='https://api.open-meteo.com/v1/forecast'
URL_EXTENDED='https://seasonal-api.open-meteo.com/v1/seasonal'


def now_utc(): return dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')

def failure(source,url,ex, *,state='unavailable'):
    return {'source':source,'source_url':url,'state':state,'queried_at_utc':now_utc(),
            'error':str(ex)[:240], 'note':'Sem coleta verificada; ausência de dados não significa ausência de risco.'}

def get_json(url,params,timeout=25):
    r=requests.get(url,params=params,timeout=timeout,headers={'User-Agent':'Campo-e-Clima/0.6 (public weather research dashboard)'})
    r.raise_for_status()
    data=r.json()
    if data.get('error'):raise ValueError(str(data.get('reason') or 'API error'))
    return data

def norm(s):
    return ''.join(c for c in unicodedata.normalize('NFKD', str(s or '')) if not unicodedata.combining(c)).casefold().strip()


def parse_cptec_xml(xml_text:str, *,asof:dt.date|None=None):
    """CPTEC independent textual weather code and temperatures; NO precipitation probabilities."""
    asof=asof or dt.datetime.now(dt.timezone(dt.timedelta(hours=-4))).date()
    if len(xml_text)>1_000_000:raise ValueError('XML muito grande')
    root=ET.fromstring(xml_text)
    if root.tag!='cidade':raise ValueError('CPTEC: documento não é <cidade>')
    name=(root.findtext('nome') or '').strip(); uf=(root.findtext('uf') or '').strip().upper()
    if norm(name)!='navirai' or uf!='MS':raise ValueError(f'CPTEC retornou outra localidade: {name}/{uf}')
    upd=root.findtext('atualizacao')
    if not upd:raise ValueError('CPTEC sem horário/data de atualização')
    upd_day=dt.date.fromisoformat(upd.strip()[:10])
    if upd_day>asof or (asof-upd_day).days>3:raise ValueError('CPTEC produto datado fora da janela de frescor')
    days=[]
    for node in root.findall('previsao'):
        day=dt.date.fromisoformat((node.findtext('dia') or '').strip())
        if day<asof-dt.timedelta(days=1) or day>asof+dt.timedelta(days=14):continue
        def optnum(key):
            raw=(node.findtext(key) or '').strip()
            if not raw or raw=='-':return None
            x=float(raw)
            return x if math.isfinite(x) else None
        days.append({'date':day.isoformat(),'weather_code':node.findtext('tempo'),
                     'tmax_c':optnum('maxima'),'tmin_c':optnum('minima'),'uv_index':optnum('iuv')})
    if not days:raise ValueError('CPTEC sem datas futuras úteis')
    return {'state':'ok','source':'CPTEC/INPE — previsão qualitativa 7 dias',
            'source_url':URL_CPTEC,'queried_at_utc':now_utc(),
            'product_updated_date':upd_day.isoformat(),'place':name,'uf':uf,'days':days,
            'note':'Códigos qualitativos e temperatura previstas por CPTEC: não integrar matematicamente aos membros Open-Meteo. Sem acumulados mm e sem probabilidades de chuva.'}


def collect_cptec():
    try:
        r=requests.get(URL_CPTEC,timeout=16,headers={'User-Agent':'Campo-e-Clima-research/0.6'})
        r.raise_for_status()
        return parse_cptec_xml(r.text)
    except (requests.RequestException, ValueError, ET.ParseError) as ex:
        return failure('CPTEC/INPE',URL_CPTEC,ex)


def parse_openweather(data:dict):
    if abs(float(data['lat'])-LAT)>0.15 or abs(float(data['lon'])-LON)>0.15:raise ValueError('Grade OpenWeather distante da localização solicitada')
    current=data.get('current') or {}
    daily=[]
    for r in data.get('daily') or []:
        when=dt.datetime.fromtimestamp(int(r['dt']),dt.timezone.utc).astimezone(dt.timezone(dt.timedelta(hours=-4))).date()
        rain=r.get('rain')
        daily.append({'date':when.isoformat(),'pop':r.get('pop'),
                      'rain_mm':rain if isinstance(rain,(float,int)) else None,
                      'tmax_c':(r.get('temp') or {}).get('max'),
                      'tmin_c':(r.get('temp') or {}).get('min')})
    return {'state':'ok','source':'OpenWeather One Call 3.0','source_url':'https://openweathermap.org/api/one-call-3',
            'queried_at_utc':now_utc(),'daily':daily,'current_dt_utc':current.get('dt'),
            'note':'Previsão externa para comparação; não adicionar como ensemble independente. POP é probabilidade calculada pelo provedor, metodologia diferente dos membros Open-Meteo.'}


def collect_openweather():
    key=os.getenv('OPENWEATHER_API_KEY','').strip()
    if not key:return failure('OpenWeather One Call',URL_OPENWEATHER,'Necessária chave própria com acesso a One Call 3.0',state='requires_key')
    try:
        data=get_json(URL_OPENWEATHER,{'lat':LAT,'lon':LON,'appid':key,'units':'metric','lang':'pt','exclude':'minutely,alerts'},timeout=19)
        return parse_openweather(data)
    except (requests.RequestException,ValueError,TypeError,KeyError) as ex:return failure('OpenWeather One Call',URL_OPENWEATHER,ex)


def collect_soil_forecast():
    """Model grid soil moisture; not in-situ soil, no trafficability authorization."""
    combos=['soil_moisture_0_to_7cm,soil_temperature_0_to_7cm,et0_fao_evapotranspiration',
            'soil_moisture_0_to_1cm,soil_temperature_0cm,et0_fao_evapotranspiration']
    problems=[]
    for vars_ in combos:
        try:
            data=get_json(URL_SOIL,{'latitude':LAT,'longitude':LON,'timezone':TZ,'forecast_days':4,'hourly':vars_},timeout=20)
            if data.get('utc_offset_seconds')!=-14400:raise ValueError('Fuso da grade incorreto')
            hourly=data.get('hourly') or {}; keys=[k for k in hourly if k.startswith('soil_moisture_')]
            if not keys:raise ValueError('API não retornou umidade do solo')
            return {'state':'ok','source':'Open-Meteo Forecast • umidade do solo em grade','source_url':'https://open-meteo.com/en/docs',
                    'queried_at_utc':now_utc(),'grid_lat':data.get('latitude'),'grid_lon':data.get('longitude'),
                    'hourly':{'time':hourly.get('time',[])[:96],**{k:v[:96] for k,v in hourly.items() if k!='time'}},
                    'soil_moisture_keys':keys,
                    'note':'Estimativa de solo de modelo, não medição nem medição do perfil real do talhão. Não autoriza entrada de máquinas.'}
        except (requests.RequestException,ValueError,TypeError) as ex:problems.append(str(ex)[:120])
    return failure('Open-Meteo solo estimado',URL_SOIL,' | '.join(problems))


def parse_nasa_power(data, *,asof=None):
    """NASA POWER gridded historical estimate, not rain gauge."""
    parameter=(data.get('properties') or {}).get('parameter') or {}
    rain=parameter.get('PRECTOTCORR') or {}
    if not isinstance(rain,dict) or not rain:raise ValueError('NASA POWER: série PRECTOTCORR não retornada')
    out=[]
    for key,val in sorted(rain.items()):
        date=dt.datetime.strptime(key,'%Y%m%d').date()
        if val is None:continue
        v=float(val)
        if v<=-900:continue # NASA fill value
        if not 0<=v<=600:continue
        out.append({'date':date.isoformat(),'precipitation_estimated_mm':v})
    if not out:raise ValueError('NASA POWER: todos valores ausentes')
    return {'state':'ok','source':'NASA POWER — estimativa de precipitação em grade',
            'source_url':'https://power.larc.nasa.gov/docs/services/api/temporal/daily/',
            'queried_at_utc':now_utc(),'records':out,
            'note':'Estimativa em grade/assimilação; NÃO é pluviômetro do IFMS/Embrapa e não permite validar modelo com observação totalmente independente.'}


def collect_nasa_power(*,enabled=False):
    if not enabled:return {'state':'requires_setup','source':'NASA POWER','source_url':URL_POWER,
      'note':'Conector implementado. Desativado em coleta de 30 minutos para evitar requisições diárias redundantes conforme política NASA POWER. Executar em rotina diária com cache persistente.'}
    today=dt.datetime.now(dt.timezone.utc).date();start=today-dt.timedelta(days=21);end=today-dt.timedelta(days=4)
    try:
        data=get_json(URL_POWER,{'parameters':'PRECTOTCORR','community':'AG',
                  'latitude':LAT,'longitude':LON,'start':start.strftime('%Y%m%d'),
                  'end':end.strftime('%Y%m%d'),'format':'JSON'},timeout=40)
        return parse_nasa_power(data)
    except (requests.RequestException,ValueError,KeyError) as ex:return failure('NASA POWER',URL_POWER,ex)


def parse_extended_weekly_mean(payload: dict) -> dict:
    """Lightweight ECMWF EC46/SEAS5 seasonal *ensemble MEAN*, not member quantiles.

    weekly.precipitation_mean units are taken from API metadata, never assumed
    to be mm/week. No daily forecast is synthesized from weekly means.
    """
    if payload.get('utc_offset_seconds') != -14400:
        raise ValueError('Seasonal API: esperado America/Campo_Grande UTC−4')
    w = payload.get('weekly') or {}
    stamps = w.get('time') or []
    precip = w.get('precipitation_mean')
    temp = w.get('temperature_2m_mean')
    anomaly = w.get('precipitation_anomaly')
    if not stamps or not isinstance(precip,list) or len(precip)!=len(stamps):
        raise ValueError('EC46: ausente série semanal de precipitation_mean')
    unit = (payload.get('weekly_units') or {}).get('precipitation_mean')
    weeks=[]
    for i,stamp in enumerate(stamps):
        try: date=dt.date.fromisoformat(str(stamp)[:10])
        except ValueError: continue
        v=precip[i]
        if isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) and v>=0:
            tv=temp[i] if isinstance(temp,list) and i<len(temp) else None
            av=anomaly[i] if isinstance(anomaly,list) and i<len(anomaly) else None
            weeks.append({'start':date.isoformat(),'rain_week_mean_api':round(v,2),
              'temperature_mean_c':round(tv,1) if isinstance(tv,(int,float)) and math.isfinite(tv) else None,
              'rain_anomaly_api':round(av,2) if isinstance(av,(int,float)) and math.isfinite(av) else None})
    if not weeks: raise ValueError('EC46: nenhuma semana com precipitação numérica válida')
    mon=payload.get('monthly') or {}; months=[]
    mm=mon.get('precipitation_mean');
    for i,stamp in enumerate(mon.get('time') or []):
        v=mm[i] if isinstance(mm,list) and i<len(mm) else None
        if isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) and v>=0:
            months.append({'start':str(stamp)[:10],'rain_month_mean_api':round(v,2)})
    return {'state':'ok','source':'ECMWF EC46/SEAS5 (ensemble mean), via Open-Meteo Seasonal',
      'source_url':'https://open-meteo.com/en/docs/seasonal-forecast-api',
      'queried_at_utc':now_utc(),'product':'weekly_ensemble_mean','weeks':weeks,'months':months,'monthly_precipitation_unit':(payload.get('monthly_units') or {}).get('precipitation_mean','unidade não informada'),
      'precipitation_unit':unit or 'unidade não informada',
      'grid_lat':payload.get('latitude'),'grid_lon':payload.get('longitude'),
      'note':'MÉDIA de ensemble em grade (~36 km), sem P10/P50/P90. Não é chuva diária; NÃO é previsão calibrada para talhão. O campo precipitation_mean conserva a unidade reportada pela API.'}


def collect_extended(*,enabled=False):
    if not enabled: return {'state':'disabled','source':'ECMWF EC46/SEAS5','source_url':URL_EXTENDED,
       'note':'Tendência semanal desativada; não extrapolar previsão determinística diária a 60 dias.'}
    try:
        # One small call with weekly model MEAN; no 51-member x 60-day 6h payload.
        data=get_json(URL_EXTENDED,{'latitude':LAT,'longitude':LON,'timezone':TZ,'forecast_days':63,
            'models':'ecmwf_seasonal_ensemble_mean_seamless',
            'weekly':'precipitation_mean,precipitation_anomaly,temperature_2m_mean',
            'monthly':'precipitation_mean'},timeout=45)
        return parse_extended_weekly_mean(data)
    except (requests.RequestException, ValueError, TypeError) as ex:
        return failure('ECMWF tendência semanal — ensemble mean',URL_EXTENDED,ex)


def load_export_provisional(path:Path):
    """Returns audited CSV as *provisional*; NEVER assigns a station ID not in input."""
    import csv
    if not path.exists():return {'state':'not_integrated','note':'Exportação histórica ainda não incorporada'}
    rows=[]; seen=set()
    try:
        with path.open(encoding='utf-8-sig',newline='') as f:
            for row in csv.DictReader(f):
                day=dt.date.fromisoformat(row['date'])
                if day<MIN_CONFIRMED_START:raise ValueError('Data anterior ao período presumido de Naviraí')
                if day in seen:raise ValueError('Data duplicada')
                seen.add(day)
                def x(k):
                    v=row.get(k)
                    return float(v) if v not in (None,'') else None
                rain=x('precipitation_mm')
                if rain is not None and not 0<=rain<=600:raise ValueError('Valor inválido de chuva')
                rows.append({'date':day.isoformat(),'precipitation_mm':rain,
                             'temperature_mean_c':x('temperature_mean_c'),
                             'relative_humidity_mean_pct':x('relative_humidity_mean_pct'),
                             'wind_mean_m_s':x('wind_mean_m_s'),
                             'et0_mm_day':x('et0_mm_day'),
                             'solar_radiation_mj_m2_day':x('solar_radiation_mj_m2_day')})
        rows.sort(key=lambda r:r['date'])
        return {'state':'provisional','source':'Embrapa Guia Clima — exportação do usuário',
                'source_url':'https://www.cpao.embrapa.br/gc/busca-de-dados',
                'station_id':None,'station_verified':False,'record_count':len(rows),
                'rain_nonmissing_days':sum(r['precipitation_mm'] is not None for r in rows),
                'date_first':rows[0]['date'] if rows else None,'date_last':rows[-1]['date'] if rows else None,
                'excluded_early_records':6,'records':rows,
                'note':'694 dias provisórios; exportação sem ID da estação, 6 registros anteriores a 01/12/2024 excluídos. Confirmar Naviraí/IFMS na interface antes de usar como verdade observacional.'}
    except (OSError,UnicodeError,ValueError,KeyError) as ex:
        return failure('Embrapa Guia Clima',str(path),ex,state='invalid')


# Backward-compatible parser for historical 6-hour-member test fixtures; no longer used for live collection.
def parse_extended_ecmwf(payload:dict, *,day0:dt.date|None=None):
    """Summarize EC46/SEAS5 seamless into week-scale 7-day member scenarios.

    The data are 6-hourly amounts per member; missing intervals invalidate the week/member.
    """
    if payload.get('utc_offset_seconds')!=-14400:raise ValueError('Seasonal API timezone not UTC-4')
    h=payload.get('hourly') or payload.get('six_hourly') or {}
    times=h.get('time') or []
    if not times:raise ValueError('Seasonal API returned no time')
    member_keys=[k for k in h if k.startswith('precipitation_member')]
    if not member_keys:raise ValueError('No valid member fields precipitation_member*')
    first=dt.date.fromisoformat(times[0][:10]); day0=day0 or first
    weeks=[]
    for start in range(14,56,7):
        beg=day0+dt.timedelta(days=start);end=beg+dt.timedelta(days=6)
        idx=[i for i,t in enumerate(times) if beg<=dt.date.fromisoformat(t[:10])<=end]
        # EC46/SEAS5 6h intervals => normally 28 samples per full week
        if len(idx)!=28:continue
        totals=[]
        for key in member_keys:
            series=h[key]
            if len(series)!=len(times):continue
            vals=[series[i] for i in idx]
            if any(v is None or not isinstance(v,(int,float)) or not math.isfinite(v) or v<0 for v in vals):continue
            totals.append(sum(vals))
        if not totals:continue
        ordered=sorted(totals)
        def qt(q):return ordered[min(len(ordered)-1,math.ceil(q*len(ordered))-1)]
        weeks.append({'start':beg.isoformat(),'end':end.isoformat(),'member_count':len(totals),
                      'rain_week_p10_mm':round(qt(.1),1),'rain_week_p50_mm':round(qt(.5),1),
                      'rain_week_p90_mm':round(qt(.9),1),'rain_week_mean_mm':round(sum(totals)/len(totals),1),
                      'model_note':'EC46 ≤46 dias, extensão SEAS5 após 46 dias; séries e resoluções mudam conforme produto'})
    if not weeks:raise ValueError('No complete 7-day sub-seasonal member samples')
    return {'state':'ok','source':'ECMWF EC46/SEAS5 via Open-Meteo Seasonal',
            'source_url':'https://open-meteo.com/en/docs/seasonal-forecast-api',
            'queried_at_utc':now_utc(),'weeks':weeks,
            'note':'Cenários NÃO calibrados, resolução espacial ~36km. Não extrapolar para chuva diária ou agendar pulverização.'}

