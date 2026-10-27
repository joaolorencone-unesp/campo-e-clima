"""Export public INMET station CATALOG to the static site for arbitrary coordinates.

This stores metadata only, NOT current or historic meteorological readings.
Any failure creates an explicit unavailable status. Uses no API key.
"""
from __future__ import annotations
import json
import datetime as dt
from pathlib import Path
import requests

URL = 'https://apitempo.inmet.gov.br/estacoes/T'
DEST = Path('site/data/inmet_stations.json')


def normalize(payload):
    if not isinstance(payload, list):
        raise ValueError('INMET stations endpoint did not return a list')
    stations=[]
    for r in payload:
        if not isinstance(r,dict):continue
        try:
            lat=float(str(r.get('VL_LATITUDE')).replace(',','.'))
            lon=float(str(r.get('VL_LONGITUDE')).replace(',','.'))
            if not(-90<=lat<=90 and -180<=lon<=180):continue
            code=str(r.get('CD_ESTACAO') or '').strip()
            if not code:continue
        except (TypeError,ValueError):continue
        stations.append({'code':code,'name':str(r.get('DC_NOME') or code)[:100],
                         'uf':str(r.get('SG_ESTADO') or ''),'latitude':lat,'longitude':lon,
                         'status':str(r.get('CD_SITUACAO') or 'Não informado')[:55]})
    return list({s['code']:s for s in stations}.values())


def main():
    DEST.parent.mkdir(parents=True, exist_ok=True)
    now=dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
    try:
        res=requests.get(URL,timeout=23,headers={'User-Agent':'Campo-e-Clima/1.0 educational weather dashboard'})
        res.raise_for_status()
        stations=normalize(res.json())
        if not stations:raise ValueError('INMET station catalog was empty')
        value={'state':'ok','source':'INMET (public catalog, NOT measurements)',
               'source_url':URL,'collected_at_utc':now,'stations':stations}
    except (requests.RequestException,ValueError,TypeError) as e:
        value={'state':'unavailable','source':'INMET station catalog','source_url':URL,
               'collected_at_utc':now,'stations':[], 'error':str(e)[:150]}
    DEST.write_text(json.dumps(value,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    print(f'INMET station catalog: {value["state"]} stations={len(value["stations"])}')


if __name__=='__main__': main()
