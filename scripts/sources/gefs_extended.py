"""Free, optional GEFS extended outlook (days 15–35), strictly from valid daily ensemble members.

This is a single-model exploratory scenario product. It must NEVER be merged into
7-day equal-model mixtures or presented as calibrated local probabilities.
"""
from __future__ import annotations
import datetime as dt
import math
import re
import requests

ENDPOINT='https://ensemble-api.open-meteo.com/v1/ensemble'
SOURCE='https://open-meteo.com/en/docs/ensemble-api'


def quantile(values: list[float], p: float) -> float:
    """Linear order-statistic interpolation of valid member totals."""
    xs=sorted(values)
    if not xs:raise ValueError('Amostra vazia')
    at=(len(xs)-1)*p
    lo=int(math.floor(at));hi=int(math.ceil(at))
    return xs[lo]+(xs[hi]-xs[lo])*(at-lo)


def parse_gefs_extended(payload: dict, minimum_members: int=5) -> dict:
    if payload.get('error'):raise ValueError(str(payload.get('reason') or 'Erro remoto'))
    if payload.get('utc_offset_seconds')!=-14400:raise ValueError('GEFS: esperado UTC−4')
    daily=payload.get('daily') or {}
    days=daily.get('time') or []
    if not isinstance(days,list) or len(days)<18:raise ValueError('GEFS: horizonte diário <18 dias')
    members={k:v for k,v in daily.items() if re.fullmatch(r'precipitation_sum_member\d+',k) and isinstance(v,list) and len(v)==len(days)}
    if len(members)<minimum_members:raise ValueError('GEFS: membros diários insuficientes; sem extrapolar')
    rows=[]
    for i,day in enumerate(days):
        if i<14:continue   # dedicated extended segment after first 14 days
        samples=[float(v[i]) for v in members.values() if isinstance(v[i],(int,float)) and math.isfinite(v[i]) and 0<=v[i]<=1000]
        if len(samples)<minimum_members:continue
        mean=sum(samples)/len(samples)
        rows.append({'date':day,'members':len(samples),'mean_mm':round(mean,2),
                     'p10_mm':round(quantile(samples,.1),2),'p50_mm':round(quantile(samples,.5),2),
                     'p90_mm':round(quantile(samples,.9),2),
                     'freq_gt_5_mm':round(sum(x>5 for x in samples)/len(samples),4),
                     'freq_gt_10_mm':round(sum(x>10 for x in samples)/len(samples),4)})
    if not rows:raise ValueError('GEFS: sem dias estendidos com amostra completa')
    return {'state':'ok','source':'NOAA GEFS, horizonte estendido (um modelo)',
            'source_url':SOURCE,'queried_at_utc':dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'),
            'grid_lat':payload.get('latitude'),'grid_lon':payload.get('longitude'),
            'model_count':1,'member_count':len(members),'days':rows,
            'note':'GEFS isolado, frequências de membros NÃO calibradas; resolução maior no prazo longo. Não é previsão multimodelo.'}


def collect_gefs_extended(enabled: bool=True) -> dict:
    if not enabled:return {'state':'disabled','source_url':SOURCE,'note':'Coleta longa desativada.'}
    params={'latitude':-23.065,'longitude':-54.19,'timezone':'America/Campo_Grande',
            'models':'ncep_gefs_seamless','forecast_days':35,'daily':'precipitation_sum'}
    try:
        r=requests.get(ENDPOINT,params=params,timeout=38,headers={'User-Agent':'Campo-e-Clima/1.3 (noncommercial research)'})
        r.raise_for_status()
        return parse_gefs_extended(r.json())
    except (requests.RequestException,ValueError,TypeError) as exc:
        return {'state':'unavailable','source_url':SOURCE,'error':str(exc)[:180],
                'note':'GEFS estendido não confirmou membros válidos. Sem preencher dias ausentes.'}
