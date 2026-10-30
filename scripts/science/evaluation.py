"""Location/interval-safe pairing and reproducible public diagnostics."""
from __future__ import annotations
import collections
import datetime as dt
import json
import math
from . import FORMULA_VERSION
from .common import config, digest, haversine, instant, now, packed, write_json
from .database import connect
from .metrics import deterministic, brier_score, crps, reliability, events

THRESHOLDS=(.1,1,3,5,10,20)
EMPTY_MESSAGE='Histórico de previsões em construção. Ainda não há amostras suficientes para validar uma calibração local.'

def horizon(row):
    lead=row['lead_hours']
    basis=row['lead_basis']
    if lead is None and row.get('available_at_utc'):
        lead=(instant(row['valid_at_utc'])-instant(row['available_at_utc'])).total_seconds()/3600
        basis='since_collection'
    if lead is None or lead<=0:return None,None
    return ('D'+str(max(1,int((lead-1e-8)//24)+1))),basis

def paired_rows(db,*,max_distance_km=50,excluded_by_location=None):
    groups=collections.defaultdict(list)
    rejected=collections.Counter()
    def reject(reason,loc):
        rejected[reason]+=1
        if excluded_by_location is not None:
            group=excluded_by_location.setdefault(loc,{})
            group[reason]=group.get(reason,0)+1
    with connect(db) as con:
        stations={r['id']:dict(r) for r in con.execute('SELECT * FROM observing_stations')}
        locations={r['id']:dict(r) for r in con.execute('SELECT * FROM locations')}
        refs=collections.defaultdict(list)
        for r in con.execute('SELECT * FROM observations'):
            row=dict(r)
            if row['qc']!='valid' or row['reference_quality']!='observed_basic_qc':
                reject('reference_unverified_or_invalid',row['location_id']);continue
            station=stations[row['station_id']]
            if haversine(locations[row['location_id']],station)>max_distance_km:
                reject('station_too_distant',row['location_id']);continue
            refs[(row['location_id'],row['variable'],row['valid_at_utc'])].append(row)
        for table in ('forecast_values','ensemble_forecasts'):
            sql=f'''SELECT v.*,r.id AS canonical_run_id,r.location_id,r.model_id,r.product,r.available_at_utc,
                r.initialization_utc,r.collected_at_utc,r.grid_latitude,r.grid_longitude
                FROM {table} v JOIN forecast_run_keys k ON k.run_key=v.run_id JOIN forecast_runs r ON r.id=k.run_id WHERE v.qc='valid' AND v.value IS NOT NULL'''
            for data in con.execute(sql):
                row=dict(data)
                row['run_id']=row.pop('canonical_run_id')
                if row['product'] in ('historical_forecast','reanalysis'):
                    reject('modelled_history_not_issued_forecast',row['location_id']);continue
                h,basis=horizon(row)
                if h is None:
                    reject('unknown_or_nonpositive_lead',row['location_id']);continue
                if row['product']=='single_run':
                    # Initialization is not publication time. Exact historical availability unknown.
                    reject('single_run_availability_unverified',row['location_id']);continue
                reference=refs.get((row['location_id'],row['variable'],row['valid_at_utc']),[])
                bystation=collections.defaultdict(list)
                for obs in reference:bystation[obs['station_id']].append(obs)
                for station,observations in bystation.items():
                    # Multiple imports of equal measurements are one reference. Conflicts are excluded.
                    comparable=[o for o in observations if o['unit']==row['unit'] and
                        o['interval_start_utc']==row['interval_start_utc'] and o['interval_end_utc']==row['interval_end_utc']]
                    if not comparable:
                        reject('interval_or_unit_mismatch',row['location_id']);continue
                    if len({o['value'] for o in comparable})!=1:
                        reject('conflicting_reference_versions',row['location_id']);continue
                    obs=min(comparable,key=lambda o:(o['available_at_utc'] or '9999',o['id']))
                    if haversine({'latitude':row['grid_latitude'],'longitude':row['grid_longitude']},stations[station])>75:
                        reject('grid_station_too_distant',row['location_id']);continue
                    key=(row['location_id'],row['model_id'],row['variable'],h,basis,station,
                         row['run_id'],row['valid_at_utc'],table)
                    groups[key].append({**row,'observation':obs['value'],'station_id':station,
                        'observation_available_at_utc':obs['available_at_utc'],'reference_quality':obs['reference_quality'],
                        'distance_km':haversine(locations[row['location_id']],stations[station])})
    candidates={}
    for key,items in groups.items():
        loc,model,var,h,basis,station,run,valid,table=key
        items.sort(key=lambda x:(x.get('member_id') or '',x['run_id']))
        samples=[x['value'] for x in items]
        prediction=sum(samples)/len(samples)
        if var=='wind_direction_10m':
            sx=sum(math.sin(math.radians(v)) for v in samples);cx=sum(math.cos(math.radians(v)) for v in samples)
            if math.hypot(sx,cx)<1e-12:continue
            prediction=math.degrees(math.atan2(sx,cx))%360
        record={**items[0],'horizon':h,'lead_basis':basis,'members':samples if table=='ensemble_forecasts' else None,
                'prediction':prediction,'method':'M2' if table=='ensemble_forecasts' else 'M1'}
        # One sample per model, station, valid time, horizon, method and lead convention.
        unique=(loc,model,var,h,basis,station,valid,record['method'])
        if unique not in candidates or record['collected_at_utc']>candidates[unique]['collected_at_utc']:
            candidates[unique]=record
    rows=list(candidates.values())
    # Equal model weights, with each member retaining the source run in lineage.
    blends=collections.defaultdict(list)
    for r in rows:
        if r['method']=='M2':
            blends[(r['location_id'],r['variable'],r['horizon'],r['lead_basis'],r['station_id'],r['valid_at_utc'])].append(r)
    for items in blends.values():
        samples=[v for r in items for v in r['members']]
        weights=[1/len(items)/len(r['members']) for r in items for _ in r['members']]
        prediction=sum(x*w for x,w in zip(samples,weights))
        if items[0]['variable']=='wind_direction_10m':
            sx=sum(w*math.sin(math.radians(v)) for v,w in zip(samples,weights));cx=sum(w*math.cos(math.radians(v)) for v,w in zip(samples,weights))
            if math.hypot(sx,cx)<1e-12:continue
            prediction=math.degrees(math.atan2(sx,cx))%360
        rows.append({**items[0],'model_id':'MULTIMODEL_EQUAL','members':samples,'weights':weights,
            'prediction':prediction,
            'lineage_run_ids':sorted(r['run_id'] for r in items)})
    rows.sort(key=lambda r:tuple(str(r.get(k,'')) for k in ('location_id','model_id','variable','horizon','station_id','valid_at_utc','method','run_id')))
    return rows,dict(rejected)

def evaluate(db,output):
    by_location={}
    rows,rejected=paired_rows(db,excluded_by_location=by_location)
    grouped=collections.defaultdict(list)
    for row in rows:
        month=instant(row['valid_at_utc']).month
        season='DJF' if month in (12,1,2) else 'MAM' if month<6 else 'JJA' if month<9 else 'SON'
        grouped[(row['location_id'],row['model_id'],row['variable'],row['horizon'],row['lead_basis'],row['station_id'],row['method'],season,row['valid_at_utc'][:10])].append(row)
    results=[]
    with connect(db) as con:
        for key,sample in sorted(grouped.items()):
            loc,model,var,h,basis,station,method,season,day=key
            f=[r['prediction'] for r in sample];o=[r['observation'] for r in sample]
            metrics=deterministic(f,o,circular=var=='wind_direction_10m')
            if var=='precipitation':
                rainfall=[]
                for threshold in THRESHOLDS:
                    probabilities=[]
                    for r in sample:
                        members=r['members'] or [r['prediction']]
                        weights=r.get('weights') or [1/len(members)]*len(members)
                        probabilities.append(sum(w for m,w in zip(members,weights) if m>threshold))
                    y=[int(v>threshold) for v in o]
                    rainfall.append({'threshold_mm':threshold,'brier':brier_score(probabilities,y),
                        'brier_skill_score':None,'bss_note':'Sem climatologia independente de treinamento neste resumo bruto',
                        'reliability':reliability(probabilities,y),'events':events(probabilities,y)})
                metrics['rain_thresholds']=rainfall
                metrics['crps']=sum(crps(r['members'] or [r['prediction']],r['observation'],r.get('weights')) for r in sample)/len(sample)
            dataset=digest(packed(sample))
            dates=[r['valid_at_utc'] for r in sample]
            result={'location_id':loc,'model':model,'variable':var,'horizon':h,'lead_basis':basis,
                'station_id':station,'method':method,'season':season,'start_utc':min(dates),'end_utc':max(dates),
                'reference_quality':'observed_basic_qc','n':len(sample),'unit':sample[0]['unit'],
                'metrics':metrics,'dataset_sha256':dataset,'calibrated':False,
                'validation_status':'descriptive_only','superiority_claim':False,
                'note':'Métricas descritivas pareadas; dependência temporal e representatividade da estação não resolvidas.'}
            ident=digest(packed([key,dataset,FORMULA_VERSION]))
            con.execute('INSERT OR IGNORE INTO forecast_verifications VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
                (ident,loc,model,var,h,station,'observed_basic_qc',len(sample),packed(metrics).decode(),dataset,FORMULA_VERSION,now()))
            results.append(result)
        status=[]
        for loc in config()['locations']:
            forecast_count=con.execute('SELECT count(*) FROM forecast_runs WHERE location_id=?',(loc['id'],)).fetchone()[0]
            observation_count=con.execute("SELECT count(*) FROM observations WHERE location_id=? AND qc='valid' AND reference_quality='observed_basic_qc'",(loc['id'],)).fetchone()[0]
            n=sum(1 for r in rows if r['location_id']==loc['id'])
            status.append({**loc,'forecast_runs':forecast_count,'observation_values_basic_qc':observation_count,
                'paired_values':n,'calibration_validated':False,'message':EMPTY_MESSAGE,
                'state':'descriptive_pairs_available' if n else 'insufficient_verified_pairs'})
    report={'schema_version':1,'generated_at_utc':now(),'formula_version':FORMULA_VERSION,
        'locations':status,'results':results,'excluded':rejected,'excluded_by_location':by_location,'ai_provider':'none',
        'limitations':['Sem selo de calibração validada','Chuva horária pode ser interpolada pelo provedor',
                       'Inicialização e disponibilidade histórica são conceitos distintos',
                       'Resultados brutos descritivos não constituem teste independente de um calibrador']}
    write_json(output,report)
    return report
