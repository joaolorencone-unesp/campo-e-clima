"""No-key scientific comparator services for Campo e Clima.

Avoids charging services. All errors are source-local and explicitly reported.
ERA5-Land is gridded reanalysis, not an independent rain gauge.
Previous-runs are fixed lead-hour forecasts, not stored original ensemble runs.
"""
from __future__ import annotations

import datetime as dt
import math
from collections import defaultdict
from typing import Any

import requests

LAT = -23.065
LON = -54.190
TZ = 'America/Campo_Grande'
ARCHIVE_URL = 'https://archive-api.open-meteo.com/v1/archive'
PREVIOUS_URL = 'https://previous-runs-api.open-meteo.com/v1/forecast'
SOURCE_ARCHIVE = 'https://open-meteo.com/en/docs/historical-weather-api'
SOURCE_PREVIOUS = 'https://open-meteo.com/en/docs/previous-runs-api'


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')


def unavailable(source: str, url: str, detail: str, state: str='unavailable') -> dict:
    return {'state':state,'source':source,'source_url':url,
            'queried_at_utc':utc_now(), 'error':detail[:220],
            'note':'Dado não disponível; isso não significa ausência de chuva ou risco.'}


def get_json(url: str, params: dict, timeout: int = 65) -> dict:
    r=requests.get(url,params=params,timeout=timeout,
                   headers={'User-Agent':'Campo-e-Clima-research/0.7 (non-commercial, public scientific dashboard)'})
    r.raise_for_status()
    data=r.json()
    if not isinstance(data,dict) or data.get('error'):
        raise ValueError(str(data.get('reason','Formato inválido')) if isinstance(data,dict) else 'Resposta inválida')
    if data.get('utc_offset_seconds') != -14400:
        raise ValueError('Timezone inesperado: dados não importados')
    return data


def _valid_mm(value: Any) -> bool:
    return type(value) in (int,float) and math.isfinite(value) and 0 <= value <= 600


def parse_climate_era5(payload: dict) -> dict:
    """30-year monthly rainfall climatology from DAILY ERA5-Land, not station observations.

    Only complete month-year samples are used, including leap years. Any missing
    daily value excludes its month-year to prevent understated accumulations.
    """
    daily=payload.get('daily') or {}
    stamps=daily.get('time') or []
    rain=daily.get('precipitation_sum') or []
    if len(stamps)!=len(rain) or not stamps:
        raise ValueError('Climatologia: calendário e precipitação incompletos')
    by_month=defaultdict(list)
    for stamp,val in zip(stamps,rain):
        d=dt.date.fromisoformat(stamp)
        if 1991 <= d.year <= 2020:
            by_month[(d.year,d.month)].append((d,val))
    result=[]
    for month in range(1,13):
        totals=[]
        for year in range(1991,2021):
            vals=by_month.get((year,month)) or []
            start=dt.date(year,month,1)
            expected=(dt.date(year+1,1,1) if month==12 else dt.date(year,month+1,1))-start
            dates={v[0] for v in vals}
            if len(vals)!=expected.days or len(dates)!=expected.days or any(not _valid_mm(v) for _,v in vals):
                continue
            totals.append(sum(float(v) for _,v in vals))
        if totals:
            result.append({'month':month,'month_name':('Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez')[month-1],
                           'mean_monthly_rain_mm':round(sum(totals)/len(totals),1),
                           'years_complete':len(totals)})
    if len(result)!=12:
        raise ValueError('Climatologia: faltam meses completos; não divulgar série parcial como normal')
    return {'state':'ok','source':'ERA5-Land via Open-Meteo Archive — climatologia em grade',
            'source_url':SOURCE_ARCHIVE,'queried_at_utc':utc_now(),
            'grid_lat':payload.get('latitude'),'grid_lon':payload.get('longitude'),
            'baseline_start':'1991-01-01','baseline_end':'2020-12-31',
            'months':result,'yearly_mean_sum_mm':round(sum(m['mean_monthly_rain_mm'] for m in result),1),
            'note':'Referência pluviométrica modelada/reanálise ERA5-Land 1991–2020, não observação do IFMS. Resolução da grade limita comparações com talhões. Não somar como membro ou como estação.'}


def collect_climate_era5(enabled: bool=True) -> dict:
    if not enabled:
        return unavailable('ERA5-Land climatologia',ARCHIVE_URL,'Coleta de climatologia desabilitada',state='disabled')
    try:
        data=get_json(ARCHIVE_URL,{'latitude':LAT,'longitude':LON,
             'start_date':'1991-01-01','end_date':'2020-12-31','daily':'precipitation_sum',
             'models':'era5_land','timezone':TZ},timeout=85)
        return parse_climate_era5(data)
    except (requests.RequestException,ValueError,TypeError,KeyError) as exc:
        return unavailable('ERA5-Land climatologia',ARCHIVE_URL,str(exc))


def parse_previous_runs(payload: dict, *,asof:dt.date|None=None) -> dict:
    """Daily totals of fixed-lead hourly forecasts (24 valid local hours/day).

    Each day total is a sum of 24 hourly values each at a similar fixed offset;
    NOT one forecast run's fixed 24h accumulation. This distinction matters.
    """
    h=payload.get('hourly') or {}
    stamps=h.get('time') or []
    if not stamps:
        raise ValueError('Previous Runs: faltam horários')
    keys=('precipitation_previous_day1','precipitation_previous_day3')
    if all(not isinstance(h.get(k),list) for k in keys):
        raise ValueError('Previous Runs: variáveis com antecedência não retornadas')
    asof=asof or dt.datetime.now(dt.timezone(dt.timedelta(hours=-4))).date()
    days=defaultdict(list)
    for i,s in enumerate(stamps):
        when=dt.datetime.fromisoformat(s)
        if not (asof-dt.timedelta(days=70) <= when.date() < asof):
            continue
        days[when.date().isoformat()].append(i)
    out=[]
    for day,ids in sorted(days.items()):
        valid_times=[stamps[i] for i in ids]
        if len(ids)!=24 or len(set(valid_times))!=24 or sorted(s[11:] for s in valid_times)!=[f'{i:02d}:00' for i in range(24)]:
            continue
        row={'date':day}
        for lead,key in ((1,keys[0]),(3,keys[1])):
            arr=h.get(key)
            if not isinstance(arr,list) or len(arr)!=len(stamps):
                row[f'lead{lead}_rain_mm']=None;continue
            values=[arr[i] for i in ids]
            row[f'lead{lead}_rain_mm']=round(sum(values),2) if all(_valid_mm(v) for v in values) else None
        if any(row[k] is not None for k in ('lead1_rain_mm','lead3_rain_mm')):
            out.append(row)
    if not out:raise ValueError('Previous Runs: nenhum dia com 24 horas completas')
    return {'state':'ok','source':'Open-Meteo Previous Runs — previsão passada 24h e 72h',
            'source_url':SOURCE_PREVIOUS,'queried_at_utc':utc_now(),
            'models_requested':'best_match (seleção automática do provedor; não identifica um centro único)',
            'date_first':out[0]['date'],'date_last':out[-1]['date'],'days':out[-70:],
            'note':'Cada acumulado agrega 24 horas de previsões com lead fixo (1d/3d); não é uma única rodada emitida às 07h. Referência best_match pode mudar de modelo com o tempo. Não representa retrospectiva dos oito ensembles.'}


def collect_previous_runs(enabled: bool=True, *,asof:dt.date|None=None) -> dict:
    if not enabled:
        return unavailable('Open-Meteo Previous Runs',PREVIOUS_URL,'Verificação histórica desabilitada',state='disabled')
    today=asof or dt.datetime.now(dt.timezone(dt.timedelta(hours=-4))).date()
    try:
        data=get_json(PREVIOUS_URL,{'latitude':LAT,'longitude':LON,'timezone':TZ,
               'start_date':(today-dt.timedelta(days=65)).isoformat(),
               'end_date':(today-dt.timedelta(days=1)).isoformat(),
               'hourly':'precipitation_previous_day1,precipitation_previous_day3'},timeout=55)
        return parse_previous_runs(data,asof=today)
    except (requests.RequestException,ValueError,TypeError,KeyError) as exc:
        return unavailable('Open-Meteo Previous Runs',PREVIOUS_URL,str(exc))


def compare_export_provisional(previous:dict, embrapa:dict) -> dict:
    """Match days for *exploratory* display, NEVER present skill as validated.

    Identity of the exported Embrapa station was not present in the spreadsheet.
    Means and scores require provenance confirmation and additional study.
    """
    if previous.get('state')!='ok' or embrapa.get('state') not in ('ok','provisional'):
        return {'state':'not_ready','note':'Comparação depende de previsão anterior válida e histórico de estação auditado.'}
    obs={r['date']:r.get('precipitation_mm') for r in embrapa.get('records',[]) if _valid_mm(r.get('precipitation_mm'))}
    pairs=[]
    for r in previous.get('days',[]):
        day=r['date']
        if day not in obs:continue
        forecast1=r.get('lead1_rain_mm');forecast3=r.get('lead3_rain_mm')
        if forecast1 is None and forecast3 is None:continue
        pairs.append({'date':day,'export_mm':obs[day],
                      'previous_lead1_mm':forecast1,'previous_lead3_mm':forecast3})
    if not pairs:return {'state':'no_overlapping_days','note':'Ainda não há dias comuns entre previsão histórica e exportação.'}
    return {'state':'exploratory','source':'Embrapa exportação não identificada × Previous Runs Open-Meteo',
            'days_overlapping':len(pairs),'paired_days':pairs[-40:],'station_verified':False,
            'note':'COMPARAÇÃO EXPLORATÓRIA: identidade da estação no .xls não confirmada; sem cálculo/afirmação de acurácia, MAE, Brier ou CRPS. Previous Runs é best_match e não representa mistura de oito ensembles.'}

# OpenWeather 5-day/3-hour public free-plan endpoint. STRICTLY no One Call calls.
FREE_OPENWEATHER_URL = 'https://api.openweathermap.org/data/2.5/forecast'


def parse_openweather_free(payload: dict) -> dict:
    if str(payload.get('cod')) != '200':
        raise ValueError('OpenWeather Free retornou falha: ' + str(payload.get('message',''))[:70])
    city=payload.get('city') or {}
    coord=city.get('coord') or {}
    try:
        if abs(float(coord['lat'])-LAT)>0.2 or abs(float(coord['lon'])-LON)>0.2:
            raise ValueError('Coordenadas da previsão OpenWeather Free distantes de Naviraí')
    except (TypeError,KeyError):
        raise ValueError('OpenWeather Free sem coordenadas verificáveis') from None
    rec=[]
    for row in payload.get('list') or []:
        try:
            stamp=dt.datetime.fromtimestamp(int(row['dt']),dt.timezone.utc).astimezone(dt.timezone(dt.timedelta(hours=-4)))
            rain=(row.get('rain') or {}).get('3h')
            wind=row.get('wind') or {}
            pop=row.get('pop')
            rec.append({'time_local':stamp.isoformat(timespec='minutes'),
                'temp_c':(row.get('main') or {}).get('temp'),
                'wind_kmh':float(wind['speed'])*3.6 if wind.get('speed') is not None else None,
                'wind_from_deg':wind.get('deg'),
                'rain_3h_mm':round(float(rain),2) if _valid_mm(rain) else None,
                'pop':float(pop) if type(pop) in (float,int) and 0<=pop<=1 else None})
        except (ValueError,TypeError,KeyError,OverflowError):
            continue
    if len(rec)<5:raise ValueError('OpenWeather Free: menos de cinco pontos horários válidos')
    return {'state':'ok','source':'OpenWeather Free — 5 dias, resolução 3 horas',
            'source_url':'https://openweathermap.org/api/forecast5',
            'queried_at_utc':utc_now(), 'coverage':'5 dias / 3 horas',
            'latitude':float(coord['lat']),'longitude':float(coord['lon']),
            'forecast':rec[:40],
            'note':'Fonte externa FREE para comparação descritiva apenas: chuva em blocos de 3h e PoP proprietária. Não duplicar ensemble, não misturar com frequência de membros. Ausência de rain.3h é NA, não chuva zero.'}


def collect_openweather_free() -> dict:
    """Optional, FREE endpoint only. Never reads the leaked historical keys.

    A *newly rotated* OPENWEATHER_FREE_API_KEY must be configured as a GitHub
    Actions secret. No secret = no outbound request, no expense.
    """
    import os
    key=os.environ.get('OPENWEATHER_FREE_API_KEY','').strip()
    if not key:
        return {'state':'optional_free_key','source':'OpenWeather Free 5d / 3h',
                'source_url':'https://openweathermap.org/api/forecast5',
                'note':'Opcional e gratuito: requer nova chave com plano Free em GitHub Secret OPENWEATHER_FREE_API_KEY. Não usar credencial exposta anteriormente. Nenhuma consulta foi feita.'}
    try:
        data=get_json_no_timezone_check(FREE_OPENWEATHER_URL,{'lat':LAT,'lon':LON,
                                 'appid':key,'units':'metric','lang':'pt_br'},timeout=20)
        return parse_openweather_free(data)
    except (requests.RequestException,ValueError,TypeError,KeyError) as ex:
        # Do not include URL with query (contains key), request object, or API body.
        # Some HTTP libraries include full request URL in exception strings; redact.
        error='Falha de autenticação ou acesso no endpoint gratuito' if isinstance(ex,requests.HTTPError) else ex.__class__.__name__
        return unavailable('OpenWeather Free 5d / 3h',FREE_OPENWEATHER_URL,error)


def get_json_no_timezone_check(url: str, params: dict, timeout: int=20) -> dict:
    """OpenWeather uses UTC timestamps, not Open-Meteo utc_offset_seconds."""
    r=requests.get(url,params=params,timeout=timeout,headers={'User-Agent':'Campo-e-Clima/0.7 (free only)'})
    r.raise_for_status()
    value=r.json()
    if not isinstance(value,dict):raise ValueError('Resposta inválida')
    return value
