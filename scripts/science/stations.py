"""INMET public catalogue and hourly observations, independently for each locality."""
from __future__ import annotations
import datetime as dt
import math
from .common import haversine, instant, iso, location, now, packed
from .ingest import VARIABLES

CATALOG='https://apitempo.inmet.gov.br/estacoes/T'

def nearest(payload,loc):
    candidates=[]
    for row in payload:
        try:
            if str(row.get('CD_SITUACAO','')).lower()!='operante':continue
            meta={'id':'INMET:'+str(row['CD_ESTACAO']),'institution':str(row.get('SG_ENTIDADE') or 'INMET catálogo'),
                'name':row['DC_NOME'],'latitude':float(str(row['VL_LATITUDE']).replace(',','.')),
                'longitude':float(str(row['VL_LONGITUDE']).replace(',','.')),
                'altitude_m':float(str(row['VL_ALTITUDE']).replace(',','.')) if row.get('VL_ALTITUDE') else None,
                'timezone':loc['timezone'],'identity_status':'catalog_verified','evidence_url':CATALOG}
            distance=haversine(loc,meta)
            if distance<=50:candidates.append((distance,meta))
        except (KeyError,ValueError,TypeError):continue
    return min(candidates,key=lambda x:x[0]) if candidates else None

def normalize_hourly(payload,station):
    code=station['id'].split(':')[-1]
    mapping={'TEM_INS':'temperature_2m','UMD_INS':'relative_humidity_2m',
        'CHUVA':'precipitation','VEN_VEL':'wind_speed_10m',
        'VEN_RAJ':'wind_gusts_10m','VEN_DIR':'wind_direction_10m'}
    records=[];seen=set();available=now()
    for row in payload:
        if not isinstance(row,dict):continue
        if str(row.get('CD_ESTACAO') or '').strip()!=code:
            raise ValueError('Identidade da estação ausente ou divergente na resposta')
        hour=str(row.get('HR_MEDICAO','')).strip().zfill(4)
        if len(hour)!=4 or not hour.isdigit():raise ValueError('Hora UTC inválida')
        t=instant(f"{str(row.get('DT_MEDICAO',''))[:10]}T{hour[:2]}:{hour[2:]}:00+00:00")
        if iso(t) in seen:raise ValueError('Hora observada duplicada; revisão necessária')
        seen.add(iso(t))
        for key,var in mapping.items():
            raw=row.get(key)
            try:value=float(str(raw).replace(',','.'))
            except (ValueError,TypeError):value=None
            if value is not None and (not math.isfinite(value) or value==-9999):value=None
            # Leave negative/out-of-range native values to the scientific QC quarantine.
            unit='m/s' if key in ('VEN_VEL','VEN_RAJ') else VARIABLES[var][0]
            records.append({'valid_at_utc':iso(t),'variable':var,'unit':unit,'value':value,
                'interval_start_utc':iso(t-dt.timedelta(hours=1)) if var=='precipitation' else None,
                'interval_end_utc':iso(t) if var=='precipitation' else None,'available_at_utc':available})
    return {'station':station,'records':records,'normalizer_version':'inmet-hourly-v22'}

def collect(client,location_id):
    loc=location(location_id)
    registry=client.get(CATALOG,{},ttl_hours=24,product='official_response')
    if not isinstance(registry,list):raise ValueError('Catálogo INMET inválido')
    selected=nearest(registry,loc)
    if selected is None:raise ValueError('Nenhuma estação operante identificada até 50 km')
    distance,station=selected
    today=dt.datetime.now(dt.timezone.utc).date()
    url=f'https://apitempo.inmet.gov.br/estacao/{today-dt.timedelta(days=3)}/{today}/{station["id"].split(":")[-1]}'
    raw=client.get(url,{},ttl_hours=1,product='official_response')
    if not isinstance(raw,list):raise ValueError('Sem lista de observações horárias válidas')
    payload=normalize_hourly(raw,station)
    if not any(r['value'] is not None for r in payload['records']):raise ValueError('Nenhum registro observado numérico disponível')
    client.capture.record(url,{},content=packed(payload),status=200,product='station_import')
    client.capture.finish()
    return {'station':station['id'],'distance_km':distance,'records':len(payload['records'])}
