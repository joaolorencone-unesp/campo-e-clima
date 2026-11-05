"""INMET public catalogue and hourly observations, independently for each locality.

Station choice: operating stations within 50 km, preferring those operated by
INMET itself (entity ``INMET``), because the public ``apitempo`` station route
has only answered for INMET-operated automatic stations in our captures;
partner-network stations (e.g. SEMADESC-MS) appear in the catalogue but return
HTTP 204 on the observation route. Distance is the tie-breaker inside each tier.

Token: INMET grants a free API token on request. When ``INMET_API_TOKEN`` is set
the token route is used; the token is placed in the URL path by INMET's design,
so the recorded (archived) URL is always the redacted public route.
"""
from __future__ import annotations
import datetime as dt
import math
import os
from .common import haversine, instant, iso, location, now, packed
from .ingest import VARIABLES

CATALOG='https://apitempo.inmet.gov.br/estacoes/T'
MAX_DISTANCE_KM=50

def candidates(payload,loc,*,max_distance_km=MAX_DISTANCE_KM):
    """Operating stations within range, ordered by (entity tier, distance)."""
    out=[]
    for row in payload:
        try:
            if str(row.get('CD_SITUACAO','')).lower()!='operante':continue
            entity=str(row.get('SG_ENTIDADE') or 'INMET catálogo')
            meta={'id':'INMET:'+str(row['CD_ESTACAO']),'institution':entity,
                'name':row['DC_NOME'],'latitude':float(str(row['VL_LATITUDE']).replace(',','.')),
                'longitude':float(str(row['VL_LONGITUDE']).replace(',','.')),
                'altitude_m':float(str(row['VL_ALTITUDE']).replace(',','.')) if row.get('VL_ALTITUDE') else None,
                'timezone':loc['timezone'],'identity_status':'catalog_verified','evidence_url':CATALOG,
                'operating_since':row.get('DT_INICIO_OPERACAO')}
            distance=haversine(loc,meta)
            if distance<=max_distance_km:out.append((0 if entity.strip().upper()=='INMET' else 1,distance,meta))
        except (KeyError,ValueError,TypeError):continue
    out.sort(key=lambda x:(x[0],x[1]))
    return [(distance,meta) for _,distance,meta in out]

def nearest(payload,loc):
    options=candidates(payload,loc)
    return options[0] if options else None

def observation_urls(code,start,end):
    """(request_url, recorded_url): the recorded one never contains the token."""
    public=f'https://apitempo.inmet.gov.br/estacao/{start}/{end}/{code}'
    token=os.environ.get('INMET_API_TOKEN','').strip()
    if token:
        return f'https://apitempo.inmet.gov.br/token/estacao/{start}/{end}/{code}/{token}',public
    return public,public

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
    """Try the preferred stations in order; stop at the first with numeric observations."""
    loc=location(location_id)
    registry=client.get(CATALOG,{},ttl_hours=24,product='official_response')
    if not isinstance(registry,list):raise ValueError('Catálogo INMET inválido')
    options=candidates(registry,loc)
    if not options:raise ValueError('Nenhuma estação operante identificada até 50 km')
    today=dt.datetime.now(dt.timezone.utc).date()
    problems=[]
    for distance,station in options[:3]:
        code=station['id'].split(':')[-1]
        url,recorded=observation_urls(code,today-dt.timedelta(days=3),today)
        try:
            raw=client.get(url,{},ttl_hours=1,product='official_response',record_url=recorded)
            if not isinstance(raw,list):raise ValueError('Sem lista de observações horárias válidas')
            payload=normalize_hourly(raw,station)
            if not any(r['value'] is not None for r in payload['records']):raise ValueError('Nenhum registro observado numérico disponível')
        except Exception as exc:
            problems.append(f'{code}: {type(exc).__name__}: {str(exc)[:80]}')
            continue
        client.capture.record(recorded,{},content=packed(payload),status=200,product='station_import')
        client.capture.finish()
        return {'station':station['id'],'distance_km':distance,'records':len(payload['records']),'entity':station['institution'],
                'token_used':bool(os.environ.get('INMET_API_TOKEN','').strip()),'skipped':problems}
    raise ValueError('Nenhuma estação respondeu com observações: '+'; '.join(problems)[:300])
