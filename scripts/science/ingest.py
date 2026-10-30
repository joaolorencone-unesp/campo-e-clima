"""Lossless source archive, explicit QC and normalized analytic derivatives."""
from __future__ import annotations
import datetime as dt
import json
import re
from pathlib import Path
from . import PIPELINE_VERSION, SYSTEM_VERSION
from .archive import checked_object
from .common import digest, finite, haversine, instant, iso, packed
from .database import connect, migrate

# Canonical units and conservative physical screening, not sensor certification.
VARIABLES={
    'temperature_2m':('degC',-90,65), 'relative_humidity_2m':('%',0,100),
    'precipitation':('mm',0,500), 'wind_speed_10m':('km/h',0,300),
    'wind_gusts_10m':('km/h',0,450), 'wind_direction_10m':('degree',0,360),
    'dew_point_2m':('degC',-100,65), 'vapour_pressure_deficit':('kPa',0,20),
    'pressure_msl':('hPa',800,1100), 'cloud_cover':('%',0,100),
    'precipitation_probability':('%',0,100)}
UNIT_ALIASES={'°C':'degC','C':'degC','degC':'degC','°':'degree','degrees':'degree',
    'km/h':'km/h','kmh':'km/h','%':'%','mm':'mm','hPa':'hPa','kPa':'kPa'}

def quality(variable, value, unit):
    canonical,low,high=VARIABLES[variable]
    if value is None:
        return None,canonical,'missing'
    if not finite(value) or value<=-9000:
        return None,canonical,'invalid_numeric'
    u=UNIT_ALIASES.get(unit,unit)
    converted=value*3.6 if unit=='m/s' and canonical=='km/h' else value
    if not (u==canonical or (unit=='m/s' and canonical=='km/h')):
        return None,canonical,'unknown_unit'
    if not low<=converted<=high:
        return None,canonical,'out_of_range'
    return float(converted),canonical,'valid'

def normalize(payload, event, loc):
    if not isinstance(payload,dict) or payload.get('error'):
        raise ValueError('Resposta não contém produto meteorológico válido')
    lat,lon=payload.get('latitude'),payload.get('longitude')
    if not finite(lat) or not finite(lon) or haversine(loc,{'latitude':lat,'longitude':lon})>150:
        raise ValueError('Grade ausente ou incompatível com a localidade')
    query=event['params']
    if any(abs(float(query[k])-loc[k])>1e-6 for k in ('latitude','longitude')):
        raise ValueError('Consulta pertence a outra localidade')
    hour=payload.get('hourly') or {}
    stamps=hour.get('time') or []
    timezone=payload.get('timezone')
    if not timezone:
        raise ValueError('Fuso de origem ausente')
    # Unix time is UTC regardless of presentation timezone.
    times=[instant(t,timezone) for t in stamps]
    if not times or any(b<=a for a,b in zip(times,times[1:])):
        raise ValueError('Horários ausentes, duplicados ou fora de ordem')
    units=payload.get('hourly_units') or {}
    output=[]
    for field,values in hour.items():
        match=re.fullmatch(r'(.+?)(?:_member(\d+))?(?:_previous_day([0-7]))?',field)
        if not match or match[1] not in VARIABLES or not isinstance(values,list):
            continue
        variable,member,previous=match.groups()
        if len(values)!=len(times):
            raise ValueError(f'Comprimento inconsistente: {field}')
        for index,(stamp,value) in enumerate(zip(times,values)):
            unit=units.get(field,units.get(variable))
            val,canonical,qc=quality(variable,value,unit)
            init=event.get('initialization_utc')
            lead=(stamp-instant(init)).total_seconds()/3600 if init else None
            basis='initialization' if init else 'unknown'
            if previous is not None:
                lead=int(previous)*24
                basis=f'fixed_offset_{lead}h'
            start=end=None
            if variable=='precipitation':
                end=iso(stamp)
                if index>0:
                    start=iso(times[index-1])
                    if stamp-times[index-1]!=dt.timedelta(hours=1):
                        val,qc=None,'unsupported_accumulation_interval'
                else:
                    val,qc=None,'unknown_initial_interval'
            output.append({'valid_at_utc':iso(stamp),'variable':variable,'member_id':member,
                'original_unit':unit,'unit':canonical,'interval_start_utc':start,'interval_end_utc':end,
                'lead_hours':lead,'lead_basis':basis,'original_value':float(value) if finite(value) else None,
                'value':val,'qc':qc,'missing':int(val is None)})
    return output

def register_raw(con,entry):
    con.execute('INSERT OR IGNORE INTO raw_assets VALUES(?,?,?)',
        (entry['raw_sha256'],entry['relative_path'],entry['byte_count']))

def ingest_manifest(db, root, manifest):
    migrate(db,manifest.get('git_commit'))
    loc=manifest['location']
    exid=manifest['execution_id']
    written=0
    with connect(db) as con:
        con.execute('INSERT OR IGNORE INTO pipeline_executions VALUES(?,?,?,?,?,?)',
            (exid,loc['id'],manifest['collected_at_utc'],SYSTEM_VERSION,manifest['status'],digest(packed(manifest))))
        con.execute('INSERT OR IGNORE INTO weather_sources VALUES(?,?,?,?)',
            ('open-meteo','Open-Meteo','https://open-meteo.com/en/docs','model'))
        for event in manifest['requests']:
            if not event.get('raw_sha256'):
                continue
            body=checked_object(root,event)
            register_raw(con,event)
            # Extended daily members stay in immutable RAW + the public summary.
            # They are not hourly forecasts or observation/forecast verification pairs.
            if event.get('http_status')!=200 or not event.get('payload_valid',True) or event.get('product') in ('official_response','extended_ensemble'):
                continue
            try:
                payload=json.loads(body)
                if event.get('product')=='station_import':
                    ingest_observations(con,payload,event,loc)
                    continue
                rows=normalize(payload,event,loc)
            except (ValueError,KeyError,TypeError) as exc:
                flag=digest(packed([exid,event['raw_sha256'],'invalid_payload']))
                con.execute('INSERT OR IGNORE INTO data_quality_flags VALUES(?,?,?,?,?)',
                    (flag,None,event['raw_sha256'],'invalid_payload',str(exc)[:200]))
                continue
            model=str(event['params'].get('models') or 'best_match_unspecified')
            con.execute('INSERT OR IGNORE INTO weather_models VALUES(?,?,?)',(model,'open-meteo',model))
            product=event.get('product','operational')
            runid=digest(packed([loc['id'],product,model,event['raw_sha256'],event['params']]))
            # Provider initialization is never set from query/collection clock.
            available=event['collected_at_utc'] if product=='operational' else None
            con.execute('''INSERT OR IGNORE INTO forecast_runs VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                (runid,exid,loc['id'],model,None,product,event.get('initialization_utc'),event['collected_at_utc'],
                 available,payload['latitude'],payload['longitude'],payload.get('elevation'),None,payload.get('timezone'),
                 event['source_url'],packed(event['params']).decode(),event['raw_sha256'],PIPELINE_VERSION,
                 'provider_hourly_grid_may_be_interpolated'))
            con.execute('INSERT OR IGNORE INTO forecast_run_keys(run_id) VALUES(?)',(runid,))
            run_key=con.execute('SELECT run_key FROM forecast_run_keys WHERE run_id=?',(runid,)).fetchone()[0]
            for row in rows:
                if product=='reanalysis':
                    key=digest(packed([runid,row['valid_at_utc'],row['variable']]))
                    con.execute('INSERT OR IGNORE INTO reanalysis_values VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                        (key,loc['id'],'open-meteo',row['valid_at_utc'],row['variable'],row['unit'],
                         row['interval_start_utc'],row['interval_end_utc'],row['value'],row['qc'],event['raw_sha256']))
                    continue
                columns=['valid_at_utc','variable','original_unit','unit','interval_start_utc','interval_end_utc',
                         'lead_hours','lead_basis','original_value','value','qc','missing']
                table='forecast_values'
                if row['member_id'] is not None:
                    table='ensemble_forecasts'
                    columns.insert(2,'member_id')
                    con.execute('INSERT OR IGNORE INTO ensemble_members VALUES(?,?)',(model,row['member_id']))
                vals=[run_key]+[row[k] for k in columns]
                con.execute(f"INSERT OR IGNORE INTO {table} VALUES({','.join('?' for _ in vals)})",vals)
                written+=1
                if row['qc'] not in ('valid','missing','unknown_initial_interval'):
                    key=digest(packed([runid,row['valid_at_utc'],row['variable'],row['member_id'],row['lead_basis']]))
                    con.execute('INSERT OR IGNORE INTO data_quality_flags VALUES(?,?,?,?,?)',
                        (key,runid,key,row['qc'],'Valor original preservado; excluído do cálculo'))
        snapshot=manifest.get('public_snapshot')
        if snapshot:
            register_raw(con,snapshot)
            # Provisional Embrapa deliberately remains only in RAW/public snapshot.
            data=json.loads(checked_object(root,snapshot))
            official=data.get('official') or {}
            hourly=official.get('inmet_hourly_nearby') or {}
            station=next((s for s in (official.get('inmet_stations') or {}).get('nearest',[])
                          if s.get('station_code')==hourly.get('station_code')),None)
            if station and hourly.get('state')=='ok':
                mapping={'temperature_c':'temperature_2m','rh_pct':'relative_humidity_2m',
                    'precipitation_previous_hour_mm':'precipitation','wind_kmh':'wind_speed_10m',
                    'gust_kmh':'wind_gusts_10m','wind_from_deg':'wind_direction_10m'}
                meta={'id':'INMET:'+station['station_code'],'institution':str(station.get('entity') or 'INMET catálogo'),
                    'name':station['name'],'latitude':station['latitude'],'longitude':station['longitude'],
                    'altitude_m':station.get('altitude_m'),'timezone':loc['timezone'],
                    'identity_status':'catalog_verified','evidence_url':hourly.get('source_url','https://portal.inmet.gov.br/')}
                records=[]
                for record in hourly['records']:
                    for src,var in mapping.items():
                        t=instant(record['valid_at_utc'])
                        records.append({'valid_at_utc':iso(t),'variable':var,'unit':VARIABLES[var][0],
                            'value':record.get(src),'interval_start_utc':iso(t-dt.timedelta(hours=1)) if var=='precipitation' else None,
                            'interval_end_utc':iso(t) if var=='precipitation' else None,
                            'available_at_utc':hourly.get('queried_at_utc')})
                ingest_observations(con,{'station':meta,'records':records},snapshot,loc)
    return written

def ingest_observations(con,payload,event,loc):
    meta=payload['station']
    required=('id','institution','name','latitude','longitude','timezone','identity_status','evidence_url')
    if any(k not in meta for k in required) or not str(meta['evidence_url']).startswith('https://'):
        raise ValueError('Identidade e fonte da estação obrigatórias')
    if meta['id'].startswith('EMBRAPA:') and meta['identity_status']!='verified_by_official_metadata':
        meta={**meta,'identity_status':'provisional'}
    quality_name='observed_basic_qc' if meta['identity_status'] in ('catalog_verified','verified_by_official_metadata') else 'provisional'
    con.execute('INSERT OR IGNORE INTO observing_stations VALUES(?,?,?,?,?,?,?,?,?,?)',
        (meta['id'],meta['institution'],meta['name'],meta['latitude'],meta['longitude'],meta.get('altitude_m'),
         meta['timezone'],meta['identity_status'],meta['evidence_url'],packed(meta).decode()))
    existing=con.execute('SELECT metadata_json FROM observing_stations WHERE id=?',(meta['id'],)).fetchone()[0]
    if existing!=packed(meta).decode():
        raise ValueError('Metadados da estação mudaram: exige revisão versionada')
    for row in payload['records']:
        variable=row['variable']
        if variable not in VARIABLES:
            continue
        t=iso(row['valid_at_utc'])
        value,unit,qc=quality(variable,row.get('value'),row.get('unit'))
        start=iso(row['interval_start_utc']) if row.get('interval_start_utc') else None
        end=iso(row['interval_end_utc']) if row.get('interval_end_utc') else None
        if variable=='precipitation' and (not start or not end or end!=t or instant(end)<=instant(start)):
            value,qc=None,'unknown_accumulation_interval'
        ident=digest(packed([meta['id'],t,variable,event['raw_sha256']]))
        con.execute('INSERT OR IGNORE INTO observations VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
            (ident,meta['id'],loc['id'],t,variable,unit,start,end,row.get('value') if finite(row.get('value')) else None,
             value,qc,quality_name,event['raw_sha256'],row.get('available_at_utc')))

def export_parquet(db, target):
    import pyarrow as pa
    import pyarrow.parquet as pq
    target=Path(target);target.mkdir(parents=True,exist_ok=True)
    with connect(db) as con:
        for name in ('forecast_runs','forecast_run_keys','forecast_values','ensemble_forecasts','observations','reanalysis_values'):
            cursor=con.execute(f'SELECT * FROM {name}')
            writer=None
            try:
                while rows:=cursor.fetchmany(10000):
                    table=pa.Table.from_pylist([dict(r) for r in rows])
                    # Initial all-null columns are common (unknown issue/version); stable schema from SQLite.
                    types={r['name']:r['type'] for r in con.execute(f'PRAGMA table_info({name})')}
                    schema=pa.schema([(k,pa.float64() if types[k]=='REAL' else pa.int64() if types[k]=='INTEGER' else pa.string()) for k in table.column_names])
                    table=table.cast(schema)
                    if writer is None:writer=pq.ParquetWriter(target/f'{name}.parquet',schema,compression='zstd')
                    writer.write_table(table)
            finally:
                if writer:writer.close()
    files={p.name:digest(p.read_bytes()) for p in target.glob('*.parquet')}
    from .common import write_json
    write_json(target/'manifest.json',{'format_version':'1.0.0','files':files})
    return files
