"""Isolated regressions for the pre-merge failure and recovery paths."""
import json
from pathlib import Path
import subprocess
import pytest
import requests
from scripts.science.http import FreeClient
from scripts.archive_git import publish,prepare
from test_integration_v22 import capture,repo

def test_report_failure_recovers_without_new_weather(tmp_path,monkeypatch):
    root=tmp_path/'archive';git=repo(root);capture(tmp_path)
    publish(tmp_path/'captures',root);capture(tmp_path,'02')
    import scripts.archive_git as writer
    original=writer.evaluate
    with monkeypatch.context() as m:
        m.setattr(writer,'evaluate',lambda *a:(_ for _ in ()).throw(RuntimeError('transient')))
        with pytest.raises(RuntimeError):publish(tmp_path/'captures',root)
    before=json.loads((root/'public/verification.json').read_text())
    calls=[]
    def tracking(*args):calls.append(True);return original(*args)
    monkeypatch.setattr(writer,'evaluate',tracking)
    publish(tmp_path/'captures',root)
    assert calls,'The preserved RAW must be reprocessed even without a new capture'
    assert json.loads((root/'public/archive_status.json').read_text())['report_status']=='current'
    assert git('status','--porcelain')==''

def test_missing_remote_archive_refuses_empty_bootstrap(tmp_path,monkeypatch):
    import scripts.archive_git as writer
    def fake_git(root,*args,**kwargs):return subprocess.CompletedProcess(args,0,stdout='',stderr='')
    monkeypatch.setattr(writer,'git',fake_git)
    with pytest.raises(ValueError,match='weather-archive'):prepare(tmp_path/'new')

def test_rate_limit_stops_following_models_and_clients(tmp_path,monkeypatch):
    class Session:
        calls=0
        def get(self,*a,**k):
            self.calls+=1;r=requests.Response();r.status_code=429;r._content=b'{"error":true}';r.headers={'Retry-After':'3600'};return r
    session=Session();root=tmp_path/'cache'
    for model in ['ecmwf_ifs025_ensemble','ncep_gefs_seamless']:
        with pytest.raises(requests.HTTPError):FreeClient(root,session=session).get('https://ensemble-api.open-meteo.com/v1/ensemble',{'models':model})
    assert session.calls==1,'A 429 must stop subsequent model requests for its cooldown'

def test_corrupt_response_cache_does_not_block_new_acquisition(tmp_path,monkeypatch):
    from scripts.science.common import digest,packed
    url='https://api.open-meteo.com/v1/forecast';params={'latitude':-23.065};root=tmp_path/'cache';root.mkdir()
    (root/(digest(packed([url,params]))+'.json')).write_text('{broken')
    class Session:
        calls=0
        def get(self,*a,**k):
            self.calls+=1;r=requests.Response();r.status_code=200;r._content=b'{"hourly":{"time":["2026-10-29T00:00"],"temperature_2m":[24]}}';return r
    session=Session();monkeypatch.setattr('scripts.science.http.time.sleep',lambda _:None)
    assert FreeClient(root,session=session).get(url,params)['hourly']['temperature_2m']==[24]
    assert session.calls==1

def test_forecast_with_no_weather_is_rejected(monkeypatch):
    import scripts.collect as collector
    monkeypatch.setattr(collector,'fetch',lambda *a:{'utc_offset_seconds':-14400,'hourly':{'time':['2026-10-29T00:00'],'temperature_2m':[None]}})
    with pytest.raises(ValueError):collector.forecast()

def test_scientific_collection_keeps_rain_age_separate_from_spray(tmp_path,monkeypatch):
    import scripts.collect as collector
    import scripts.science_cli as cli
    from scripts.science.common import packed
    class Client:
        def __init__(self,root,cap):self.cap=cap
        def get(self,url,params,**kwargs):
            e=self.cap.record(url,params,content=packed({'hourly':{}}),status=200,product=kwargs.get('product','operational'))
            e['collected_at_utc']='2026-10-29T06:00:00+00:00' if params.get('forecast_days') else '2026-10-29T12:00:00+00:00'
            return {}
    def collection(**kwargs):
        for params in ({'models':'gfs','forecast_days':7,'hourly':'precipitation'},{'models':'gfs','forecast_hours':80,'hourly':'precipitation,temperature_2m'},{'models':'ncep_gefs_seamless','forecast_days':35,'daily':'precipitation_sum'}):collector.fetch(collector.ENSEMBLE_URL,params)
        p=Path('site/data/latest.json');p.parent.mkdir(parents=True);p.write_text(json.dumps({'issued_at_utc':'2026-10-29T12:00:00+00:00','site':{},'ensemble_models':{'GFS':{'code':'gfs'}},'sources':{},'complementary':{'gefs_extended':{'state':'ok','queried_at_utc':'2026-10-29T12:00:00+00:00'}}}))
        Path('site/data/slow_sources_cache.json').write_text('{"sources":{}}')
    monkeypatch.chdir(tmp_path);monkeypatch.setattr(cli,'FreeClient',Client);monkeypatch.setattr(collector,'main',collection)
    cli.collect('navirai',tmp_path/'runtime')
    value=json.loads(Path('site/data/latest.json').read_text())
    assert value['ensemble_models']['GFS']['collected_at_utc']=='2026-10-29T06:00:00+00:00'
    assert value['complementary']['gefs_extended']['collected_at_utc']=='2026-10-29T06:00:00+00:00'
    cached=json.loads(Path('site/data/slow_sources_cache.json').read_text())
    assert cached['sources']['gefs_extended']['collected_at_utc']=='2026-10-29T06:00:00+00:00'

def test_slow_products_retry_failed_gefs_after_six_hours_only():
    import datetime as dt
    from scripts.sources.cache_policy import refresh_daily
    stamp=dt.datetime(2026,10,29,7,tzinfo=dt.timezone.utc);calls=[]
    def failed():calls.append('failed');return {'state':'unavailable'}
    first=refresh_daily({}, {'gefs':failed},now=stamp)
    assert refresh_daily({'sources':first},{'gefs':failed},now=stamp+dt.timedelta(hours=5))==first
    def success():calls.append('success');return {'state':'ok','days':[{'date':'2026-11-15','p50_mm':1}]}
    recovered=refresh_daily({'sources':first},{'gefs':success},now=stamp+dt.timedelta(hours=6))
    assert recovered['gefs']['state']=='ok' and calls==['failed','success']
    assert refresh_daily({'sources':recovered},{'gefs':failed},now=stamp+dt.timedelta(hours=12))==recovered
    assert calls==['failed','success']

def test_rejected_http200_raw_does_not_consume_archive_slot(tmp_path,monkeypatch):
    from scripts.science.capture import Capture
    from scripts.science.archive import archive_capture
    class Session:
        def get(self,*a,**k):
            r=requests.Response();r.status_code=200;r._content=b'{"error":true,"reason":"incomplete"}';return r
    cap=Capture(tmp_path/'capture','navirai');client=FreeClient(tmp_path/'cache',cap,Session())
    with pytest.raises(ValueError):client.get('https://api.open-meteo.com/v1/forecast',{})
    cap.finish('partial_failure')
    assert list(cap.root.glob('objects/**/*.gz')),'Rejected raw response is preserved for diagnosis'
    with pytest.raises(ValueError,match='Nenhum produto'):archive_capture(cap.root,tmp_path/'archive')
    assert not list((tmp_path/'cache').glob('*.body'))

def test_collection_budget_stops_network_before_runner_timeout(tmp_path,monkeypatch):
    import time
    class Session:
        def get(self,*a,**k):pytest.fail('Budget must prevent this request')
    client=FreeClient(tmp_path/'cache',session=Session());client.deadline=time.monotonic()-1
    with pytest.raises(requests.Timeout,match='Orçamento'):client.get('https://api.open-meteo.com/v1/forecast',{})

def test_extended_daily_members_remain_raw_not_hourly_or_observations(tmp_path):
    from scripts.science.capture import Capture
    from scripts.science.common import packed
    from scripts.science.ingest import ingest_manifest
    from scripts.science.database import counts
    cap=Capture(tmp_path/'cap','navirai')
    cap.record('https://ensemble-api.open-meteo.com/v1/ensemble',{'models':'ncep_gefs_seamless','daily':'precipitation_sum'},content=packed({'daily':{'time':['2026-11-10'],'precipitation_sum_member01':[3]}}),status=200,product='extended_ensemble')
    cap.finish();db=tmp_path/'science.sqlite';ingest_manifest(db,cap.root,cap.manifest);n=counts(db)
    assert n['raw_assets']==1 and n['forecast_runs']==n['observations']==n['data_quality_flags']==0
