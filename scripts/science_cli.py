"""python -m scripts.science_cli --help (Windows and GitHub Actions)."""
from __future__ import annotations
import argparse
import json
import os
import subprocess
from pathlib import Path
from scripts.science.common import config, location, now, write_json
from scripts.science.database import migrate, backup, counts
from scripts.science.capture import Capture
from scripts.science.ingest import ingest_manifest, export_parquet
from scripts.science.archive import archive_capture, rebuild
from scripts.science.http import FreeClient

def collect(location_id, runtime, *, database=None):
    import scripts.collect as collector
    import scripts.sources.official as official
    from scripts.science import capture as capture_module
    loc=location(location_id)
    directory=Path(runtime)/'captures'/location_id
    cap=Capture(directory,location_id)
    client=FreeClient(Path(runtime)/'http_cache',cap)
    original_official=official.http_json
    original_fetch=collector.fetch;old=(collector.LAT,collector.LON,collector.TZ)
    old_output=os.environ.get('OUTPUT_JSON')
    dest=Path('site/data/latest.json' if location_id=='navirai' else f'site/data/locations/{location_id}/latest.json')
    collector.LAT,collector.LON,collector.TZ=loc['latitude'],loc['longitude'],loc['timezone']
    def fetch(url,params):
        return client.get(url,params,ttl_hours=.45 if 'ensemble-api.' not in url else 6)
    collector.fetch=fetch
    official.http_json=lambda url,timeout=18: client.get(url,{},ttl_hours=0.45,product="official_response")
    os.environ['OUTPUT_JSON']=str(dest)
    try:
        collector.main(include_local_sources=location_id=='navirai')
        public=json.loads(dest.read_text(encoding='utf-8'))
        public.update(system_version='2.2.0',collected_at_utc=public['issued_at_utc'],model_initialization_utc=None)
        public['site']['id']=location_id
        # Cache hits retain the actual acquisition time, never the current UI refresh time.
        for event in cap.manifest['requests']:
            if event.get('http_status')!=200:continue
            if event['source_url']=='https://api.open-meteo.com/v1/forecast' and not event['params'].get('models') and event.get('product')=='operational' and public.get('deterministic'):
                public['deterministic']['collected_at_utc']=event['collected_at_utc']
                public['sources']['Open-Meteo Forecast']['collected_at_utc']=event['collected_at_utc']
            for model in public.get('ensemble_models',{}).values():
                if model.get('code')==event['params'].get('models'):
                    model['collected_at_utc']=event['collected_at_utc']
                    model['cache_hit']=event.get('cache_hit',False)
        write_json(dest,public)
        capture_module.ACTIVE=cap
        capture_module.record_auxiliary_latest(dest)
        if database:
            try:ingest_manifest(database,directory,cap.manifest)
            except Exception as exc:
                cap.manifest['analytic_ingestion_error']=type(exc).__name__+': '+str(exc)[:160]
                cap.flush()
                print('Aviso: banco analítico indisponível; previsão preservada:',type(exc).__name__)
        return {'location':location_id,'requests':len(cap.manifest['requests']),'output':str(dest)}
    except BaseException:
        cap.finish('partial_failure')
        raise
    finally:
        official.http_json=original_official
        collector.fetch=original_fetch;collector.LAT,collector.LON,collector.TZ=old
        capture_module.ACTIVE=None
        if old_output is None:os.environ.pop('OUTPUT_JSON',None)
        else:os.environ['OUTPUT_JSON']=old_output

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=['init','collect','archive','rebuild','backup','parquet','evaluate','train','explain','historical','import-observations','observations','diagnostics'])
    p.add_argument('--db',default='runtime/science.sqlite')
    p.add_argument('--runtime',default='runtime')
    p.add_argument('--archive',default='weather-archive')
    p.add_argument('--location',choices=['navirai','diamantino','all'],default='navirai')
    p.add_argument('--output')
    p.add_argument('--product',choices=['previous_runs','single_run','historical_forecast','reanalysis'],default='previous_runs')
    p.add_argument('--model',default='ecmwf_ifs025')
    p.add_argument('--start');p.add_argument('--end');p.add_argument('--run');p.add_argument('--since')
    p.add_argument('--file');p.add_argument('--station');p.add_argument('--format',default='canonical',choices=['canonical','inmet'])
    a=p.parse_args(argv)
    if a.command=='rebuild':result=rebuild(a.archive,a.output or a.db,since=a.since)
    elif a.command=='collect':
        result=[]
        for loc in (['navirai','diamantino'] if a.location=='all' else [a.location]):
            try:result.append(collect(loc,a.runtime,database=a.db))
            except (Exception,SystemExit) as exc:
                if loc=='navirai':raise
                result.append({'location':loc,'state':'failed','error':type(exc).__name__})
    elif a.command=='archive':
        result=[archive_capture(Path(a.runtime)/'captures'/loc,a.archive) for loc in
                (['navirai','diamantino'] if a.location=='all' else [a.location])]
    else:
        migrate(a.db)
        if a.command=='init':result=counts(a.db)
        elif a.command=='backup':
            if not a.output:p.error('--output obrigatório para backup')
            result=backup(a.db,a.output)
        elif a.command=='parquet':result=export_parquet(a.db,a.output or 'runtime/parquet')
        elif a.command=='evaluate':
            from scripts.science.evaluation import evaluate
            result=evaluate(a.db,a.output or 'site/data/verification.json')
        elif a.command=='train':
            from scripts.science.calibration import experiment
            result=experiment(a.db,a.output or 'site/data/calibration.json')
        elif a.command=='explain':
            from scripts.science.explanations import explain
            report=json.loads(Path(a.file or 'site/data/verification.json').read_text(encoding='utf-8'))
            result=explain(a.db,report,a.output or 'site/data/explanation.json')
        elif a.command in ('historical','import-observations','observations'):
            if a.location=='all':p.error('Escolha uma localidade por importação')
            directory=Path(a.runtime)/'imports'/now().replace(':','').replace('+','')/a.location/a.command
            cap=Capture(directory,a.location)
            if a.command=='historical':
                from scripts.science.historical import request
                if not a.start or not a.end:p.error('--start e --end obrigatórios')
                request(FreeClient(Path(a.runtime)/'http_cache',cap),a.product,a.location,a.model,a.start,a.end,run=a.run)
                cap.finish()
            elif a.command=='observations':
                from scripts.science.stations import collect as collect_station
                try:collect_station(FreeClient(Path(a.runtime)/'http_cache',cap),a.location)
                except Exception:
                    cap.finish('unavailable')
                    raise
            else:
                from scripts.science.observations import import_csv
                if not a.file or not a.station:p.error('--file e --station obrigatórios')
                import_csv(a.file,a.station,cap,format=a.format)
            ingest_manifest(a.db,directory,cap.manifest)
            result=archive_capture(directory,a.archive,force_slot='import')
        else:result={'database':counts(a.db),'policy':config()}
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return result

if __name__=='__main__':main()
