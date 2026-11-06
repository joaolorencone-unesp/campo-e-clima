"""python -m scripts.science_cli --help (Windows and GitHub Actions)."""
from __future__ import annotations
import argparse
import json
import os
import subprocess
import time
from pathlib import Path
import requests
from scripts.science.common import config, finite, instant, location, now, write_json
from scripts.science.database import migrate, backup, counts
from scripts.science.capture import Capture
from scripts.science.ingest import ingest_manifest, export_parquet
from scripts.science.archive import archive_capture, has_archivable_response, rebuild
from scripts.science.http import FreeClient
from scripts.freshness import summarize as summarize_freshness, apply_acquisition_times

PUBLIC_SITE = 'https://joaolorencone-unesp.github.io/campo-e-clima/'


def forecast_path(location_id):
    return Path('site/data/latest.json' if location_id == 'navirai' else f'site/data/locations/{location_id}/latest.json')


def restore_published_forecast(location_id):
    """Restore a public forecast for the same point with its original acquisition clocks."""
    path = forecast_path(location_id)
    url = PUBLIC_SITE + path.relative_to('site').as_posix()
    response = requests.get(url, headers={'Cache-Control': 'no-cache'}, timeout=12, allow_redirects=False)
    if response.status_code != 200:
        raise ValueError(f'Previsão anterior indisponível para {location_id} (HTTP {response.status_code})')
    public = response.json()
    site = public['site']
    expected = location(location_id)
    if any(site.get(k) != expected[k] for k in ('id', 'latitude', 'longitude', 'timezone')):
        raise ValueError(f'Identidade divergente na previsão anterior de {location_id}')
    issued = instant(public['issued_at_utc'])
    if issued > instant(now()):
        raise ValueError(f'Previsão anterior de {location_id} tem data futura')
    hourly = (public.get('deterministic') or {}).get('hourly') or {}
    times = hourly.get('time') or []
    has_hourly = bool(times) and any(isinstance(series, list) and len(series) == len(times) and any(map(finite, series))
                                    for key, series in hourly.items() if key != 'time')
    has_ensembles = any(finite(row.get('p50_mm')) for row in public.get('rain_ensemble_daily') or [])
    if not (has_hourly or has_ensembles):
        raise ValueError(f'Previsão anterior de {location_id} sem dados válidos')
    public['publication_state'] = 'previous_preserved'
    write_json(path, public)
    return {'location': location_id, 'state': 'previous_preserved', 'issued_at_utc': public['issued_at_utc']}


def collect_pages(runtime, *, database, deadline):
    results, failures = [], []
    for loc in ('navirai', 'diamantino'):
        try:
            results.append(collect(loc, runtime, database=database, deadline=deadline))
        except (Exception, SystemExit) as exc:
            failures.append(loc)
            print(f'::warning::{loc}: coleta indisponível ({type(exc).__name__}).')
    if not results:
        raise RuntimeError('Nenhuma localidade atualizada. A edição pública anterior permanece disponível.')
    for loc in failures:
        previous = restore_published_forecast(loc)
        print(f"::warning::{loc}: edição anterior preservada ({previous['issued_at_utc']}).")
        results.append(previous)
    return results


def collect(location_id, runtime, *, database=None, deadline=None):
    import scripts.collect as collector
    import scripts.sources.official as official
    from scripts.science import capture as capture_module
    loc=location(location_id)
    directory=Path(runtime)/'captures'/location_id
    cap=Capture(directory,location_id)
    client=FreeClient(Path(runtime)/'http_cache',cap)
    client.deadline=deadline
    original_official=official.http_json
    original_fetch=collector.fetch;old=(collector.LAT,collector.LON,collector.TZ)
    os.environ.setdefault('PREVIOUS_PUBLICATION_DIR',str(Path(runtime)/'previous_publication'))
    old_output=os.environ.get('OUTPUT_JSON')
    dest=forecast_path(location_id)
    collector.LAT,collector.LON,collector.TZ=loc['latitude'],loc['longitude'],loc['timezone']
    def fetch(url,params):
        def validate(payload):
            if params.get('daily') and 'ensemble-api.' in url:
                from scripts.sources.gefs_extended import parse_gefs_extended
                parse_gefs_extended(payload)
            else:collector.validate_forecast(payload)
        product='extended_ensemble' if params.get('daily') and 'ensemble-api.' in url else 'operational'
        if 'ensemble-api.' not in url:
            ttl=.45
            fresh_after=None
        else:
            # Run-aware cache: members are reused while the provider has not published a newer
            # run, but never for more than 4 h (observed: a provider metadata file announcing a
            # month-old run kept members 7 h stale). Metadata older than 24 h is ignored.
            fresh_after=collector.RUN_AVAILABILITY.get(params.get('models'))
            if fresh_after:
                try:
                    import datetime as _dt
                    age_h=(_dt.datetime.now(_dt.timezone.utc)-_dt.datetime.fromisoformat(str(fresh_after).replace('Z','+00:00'))).total_seconds()/3600
                    if age_h>24:fresh_after=None
                except (ValueError,TypeError):fresh_after=None
            ttl=4 if fresh_after else 3
        return client.get(url,params,ttl_hours=ttl,validator=validate,product=product,fresh_after=fresh_after)
    def fetch_meta(url):
        return client.get(url,{},ttl_hours=.25,product='model_meta')
    original_meta=collector.fetch_meta
    collector.fetch=fetch
    collector.fetch_meta=fetch_meta
    collector.META_FAILURES['transport']=0
    official.http_json=lambda url,timeout=18,record_url=None: client.get(url,{},ttl_hours=0.45,product="official_response",record_url=record_url)
    os.environ['OUTPUT_JSON']=str(dest)
    try:
        collector.main(include_local_sources=location_id=='navirai')
        public=json.loads(dest.read_text(encoding='utf-8'))
        from scripts.science import SYSTEM_VERSION
        public.update(system_version=SYSTEM_VERSION,collected_at_utc=public['issued_at_utc'],model_initialization_utc=None)
        public['site']['id']=location_id
        # Cache hits retain the actual acquisition time, never the current UI refresh time.
        extended_event=apply_acquisition_times(public,cap.manifest['requests'])
        if extended_event is not None:
            extended=public.get('complementary',{}).get('gefs_extended',{})
            if extended.get('state')=='ok':
                # The daily product cache must also retain the original acquisition clock.
                slow=Path('site/data/slow_sources_cache.json')
                if slow.exists():
                    daily_cache=json.loads(slow.read_text(encoding='utf-8'))
                    daily_cache.setdefault('sources',{})['gefs_extended']=extended
                    write_json(slow,daily_cache)
        public['freshness']=summarize_freshness(public)
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
        cap.finish('partial_failure' if has_archivable_response(cap.manifest) else 'unavailable')
        raise
    finally:
        official.http_json=original_official
        collector.fetch=original_fetch;collector.fetch_meta=original_meta;collector.LAT,collector.LON,collector.TZ=old
        collector.RUN_AVAILABILITY.clear()
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
    p.add_argument('--collection-budget-seconds',type=int,default=900)
    p.add_argument('--preserve-published', action='store_true', help='No Pages, preserva o último JSON público de um ponto se só o outro atualizar')
    a=p.parse_args(argv)
    if a.command=='rebuild':result=rebuild(a.archive,a.output or a.db,since=a.since)
    elif a.command=='collect':
        if not 1<=a.collection_budget_seconds<=1200:p.error('Orçamento de coleta deve ficar entre 1 e 1200 segundos')
        deadline=time.monotonic()+a.collection_budget_seconds
        if a.preserve_published:
            if a.location != 'all':p.error('--preserve-published requer --location all')
            result=collect_pages(a.runtime,database=a.db,deadline=deadline)
        else:
            result=[]
            for loc in (['navirai','diamantino'] if a.location=='all' else [a.location]):
                try:result.append(collect(loc,a.runtime,database=a.db,deadline=deadline))
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
