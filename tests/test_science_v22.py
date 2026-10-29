"""Synthetic fixtures are test-only; never copied to site/data as weather."""
import datetime as dt
import gzip
import json
from pathlib import Path
import pytest
from scripts.science.common import digest, instant, iso, location, packed, write_json
from scripts.science.capture import Capture
from scripts.science.database import migrate, connect, counts, backup
from scripts.science.ingest import normalize, ingest_manifest, quality, export_parquet
from scripts.science.archive import archive_capture, rebuild, verify_manifest
from scripts.science.metrics import deterministic, brier_score, brier_skill_score, crps, reliability, events, monotone_probabilities
from scripts.science.evaluation import paired_rows, evaluate
from scripts.science.calibration import chronological_split
from scripts.science.explanations import explain, validate_selection

def fixture_capture(tmp_path, *, loc='navirai', product='operational', negative=False, members=False):
    root=tmp_path/'capture';cap=Capture(root,loc,execution_id='synthetic-test',collected_at='2026-01-01T00:00:00Z')
    l=location(loc);field='precipitation_member01' if members else 'precipitation'
    payload={'latitude':l['latitude'],'longitude':l['longitude'],'timezone':'UTC','elevation':400,
        'hourly':{'time':['2026-01-02T01:00','2026-01-02T02:00','2026-01-02T03:00'],
          field:[0,-.1 if negative else 2,3], 'temperature_2m':[20,None,22]},
        'hourly_units':{field:'mm','temperature_2m':'°C'}}
    event=cap.record('https://api.open-meteo.com/v1/forecast',{'latitude':l['latitude'],'longitude':l['longitude'],'models':'test_model'},
        content=packed(payload),status=200,product=product)
    event['collected_at_utc']='2026-01-01T00:00:00+00:00';cap.finish()
    return cap,payload,event

def observation(cap,*,loc='navirai',quality='verified_by_official_metadata',rain=2,interval_start='2026-01-02T01:00:00Z'):
    l=location(loc)
    station={'id':'INMET:S735','institution':'INMET test fixture','name':'Synthetic station',
        'latitude':l['latitude'],'longitude':l['longitude'],'altitude_m':400,'timezone':l['timezone'],
        'identity_status':quality,'evidence_url':'https://portal.inmet.gov.br/'}
    payload={'station':station,'records':[{'valid_at_utc':'2026-01-02T02:00:00Z','variable':'precipitation',
        'unit':'mm','value':rain,'interval_start_utc':interval_start,'interval_end_utc':'2026-01-02T02:00:00Z'}]}
    cap.record('https://apitempo.inmet.gov.br/',{},content=packed(payload),status=200,product='station_import');cap.finish()
    return payload

def test_migration_idempotent_fk_and_wal(tmp_path):
    db=tmp_path/'science.sqlite';migrate(db);migrate(db)
    with connect(db) as con:
        assert con.execute('PRAGMA user_version').fetchone()[0]==2
        assert con.execute('PRAGMA foreign_keys').fetchone()[0]==1
        assert con.execute('PRAGMA journal_mode').fetchone()[0]=='wal'
        assert con.execute('SELECT count(*) FROM locations').fetchone()[0]==2
        with pytest.raises(Exception):con.execute("INSERT INTO weather_models VALUES('x','unknown','bad')")

def test_ingest_archive_restore_idempotent_and_parquet(tmp_path):
    cap,_,_=fixture_capture(tmp_path);observation(cap)
    db=tmp_path/'science.sqlite';ingest_manifest(db,cap.root,cap.manifest)
    first=counts(db);ingest_manifest(db,cap.root,cap.manifest);assert counts(db)==first
    assert first['forecast_values']==6
    archive=tmp_path/'archive';result=archive_capture(cap.root,archive)
    assert result['state']=='archived'
    assert archive_capture(cap.root,archive)['state']=='already_archived'
    target=tmp_path/'restored.sqlite';result=rebuild(archive,target)
    assert result['integrity']=='ok';assert counts(target)==first
    b=backup(target,tmp_path/'backup.sqlite');assert b['sha256']==digest((tmp_path/'backup.sqlite').read_bytes())
    assert export_parquet(target,tmp_path/'parquet')['forecast_values.parquet']
    pairs,_=paired_rows(target);assert len(pairs)==1;assert pairs[0]['prediction']==2

def test_negative_rain_and_missing_never_zero(tmp_path):
    cap,p,event=fixture_capture(tmp_path,negative=True)
    rows=normalize(p,event,cap.location)
    bad=[r for r in rows if r['qc']=='out_of_range'][0]
    assert bad['original_value']==-.1 and bad['value'] is None
    assert rows[0]['qc']=='unknown_initial_interval'
    assert any(r['qc']=='missing' and r['value'] is None for r in rows)
    db=tmp_path/'db';ingest_manifest(db,cap.root,cap.manifest)
    assert counts(db)['data_quality_flags']==1

def test_no_assumed_initialization_and_all_members_preserved(tmp_path):
    cap,p,e=fixture_capture(tmp_path,members=True)
    p['hourly']['precipitation_member99']=[0,3,4];p['hourly_units']['precipitation_member99']='mm'
    rows=normalize(p,e,cap.location)
    assert {r['member_id'] for r in rows if r['variable']=='precipitation'}=={'01','99'}
    assert all(r['lead_hours'] is None for r in rows)

@pytest.mark.parametrize('zone',['America/Campo_Grande','America/Cuiaba'])
def test_iana_utc(zone):
    assert iso('2026-10-28T00:00',zone)=='2026-10-28T04:00:00+00:00'
    with pytest.raises(ValueError):iso('2026-10-28T00:00')

def test_forecast_observation_temporal_and_location_gates(tmp_path):
    cap,p,e=fixture_capture(tmp_path)
    with pytest.raises(ValueError):normalize(p,e,location('diamantino'))
    observation(cap,interval_start='2026-01-01T02:00:00Z')
    db=tmp_path/'db';ingest_manifest(db,cap.root,cap.manifest)
    pairs,excluded=paired_rows(db);assert not pairs;assert excluded['interval_or_unit_mismatch']

@pytest.mark.parametrize('product',['reanalysis','historical_forecast','single_run'])
def test_modelled_history_cannot_be_validated_forecast(tmp_path,product):
    cap,_,_=fixture_capture(tmp_path,product=product);observation(cap)
    db=tmp_path/'db';ingest_manifest(db,cap.root,cap.manifest)
    assert not paired_rows(db)[0]
    if product=='reanalysis':assert counts(db)['reanalysis_values']==6

def test_provisional_observation_excluded(tmp_path):
    cap,_,_=fixture_capture(tmp_path);observation(cap,quality='provisional')
    db=tmp_path/'db';ingest_manifest(db,cap.root,cap.manifest)
    report=evaluate(db,tmp_path/'verification.json')
    assert not report['results'];assert all(not l['calibration_validated'] for l in report['locations'])

def test_conflicting_observation_versions_excluded(tmp_path):
    cap,_,_=fixture_capture(tmp_path);observation(cap,rain=2);observation(cap,rain=9)
    db=tmp_path/'db';ingest_manifest(db,cap.root,cap.manifest)
    pairs,flags=paired_rows(db);assert not pairs;assert flags['conflicting_reference_versions']

def test_archive_hash_corruption_and_safe_restore(tmp_path):
    cap,_,_=fixture_capture(tmp_path);root=tmp_path/'archive';out=archive_capture(cap.root,root)
    obj=root/cap.manifest['requests'][0]['relative_path'];obj.write_bytes(b'corrupt')
    with pytest.raises(ValueError,match='SHA-256'):rebuild(root,tmp_path/'recovered.sqlite')
    assert not (tmp_path/'recovered.sqlite').exists()
    existing=tmp_path/'exists';existing.write_text('original')
    with pytest.raises(FileExistsError):rebuild(root,existing)
    assert existing.read_text()=='original'

def test_archive_rejects_traversal_and_no_success(tmp_path):
    cap,_,_=fixture_capture(tmp_path)
    cap.manifest['requests'][0]['relative_path']='../outside.gz';cap.flush()
    with pytest.raises(ValueError,match='inseguro'):archive_capture(cap.root,tmp_path/'a')
    cap.manifest['requests'][0]['http_status']=500;cap.flush()
    with pytest.raises(ValueError,match='Nenhum produto'):archive_capture(cap.root,tmp_path/'a')

def test_metrics_known_results():
    m=deterministic([1,3],[2,1]);assert m['mae']==1.5;assert m['bias']==.5;assert m['rmse']==pytest.approx(2.5**.5)
    assert deterministic([359],[1],circular=True)['mae']==2
    assert brier_score([.25,.75],[0,1])==.0625
    assert brier_skill_score([.25,.75],[0,1],[.5,.5])==.75
    assert brier_skill_score([0,1],[0,1],[0,1]) is None
    assert crps([0,2],1)==.5
    assert crps([0,2],1,[.25,.75])==.625
    assert events([.9,.8,.1,.2],[1,0,1,0])['csi']==pytest.approx(1/3)
    assert sum(b['n'] for b in reliability([0,1],[0,1]))==2
    assert monotone_probabilities([.9,.4,.6,-.1])==[.9,.5,.5,0]

@pytest.mark.parametrize('f,o',[([1],[1,2]),([float('nan')],[1]),([None],[0]),([],[])])
def test_metrics_reject_bad_pairs(f,o):
    with pytest.raises(ValueError):deterministic(f,o)

def test_probabilities_bounds():
    for values in ([-.1],[1.1],[float('nan')]):
        with pytest.raises(ValueError):brier_score(values,[1])

def split_fixture():
    return [{'valid_at_utc':iso(dt.datetime(2025,1,1,tzinfo=dt.timezone.utc)+dt.timedelta(days=i)),
             'run_id':str(i)} for i in range(150)]

def test_temporal_purge_and_round_groups():
    rows=split_fixture();train,cal,test=chronological_split(rows)
    assert instant(cal[0]['valid_at_utc'])-instant(train[-1]['valid_at_utc'])>dt.timedelta(days=7)
    assert instant(test[0]['valid_at_utc'])-instant(cal[-1]['valid_at_utc'])>dt.timedelta(days=7)
    rows[1]['run_id']=rows[-1]['run_id']
    with pytest.raises(ValueError,match='rodada'):chronological_split(rows)

def test_training_reference_not_available_at_origin():
    rows=split_fixture();rows[0]['observation_available_at_utc']='2026-01-01T00:00:00Z'
    rows[-1]['available_at_utc']='2025-05-20T00:00:00Z'
    with pytest.raises(ValueError,match='após origem'):chronological_split(rows)

def test_ai_none_and_invalid_reply(tmp_path,monkeypatch):
    db=tmp_path/'db';migrate(db)
    monkeypatch.setenv('AI_ENABLE','0')
    with pytest.raises(ValueError):validate_selection({'fact_ids':['invented']},{'real':'fact'})
    with pytest.raises(ValueError):validate_selection({'fact_ids':['real'],'dose':5},{'real':'fact'})
    out=explain(db,{'locations':[]},tmp_path/'ai.json');assert out['effective_provider']=='none'
    monkeypatch.setenv('AI_ENABLE','1');monkeypatch.setenv('AI_PROVIDER','paid_unknown')
    out=explain(db,{'locations':[]},tmp_path/'ai2.json');assert out['validation_status']=='rules_fallback'

def test_capture_credentials_blocked(tmp_path):
    cap=Capture(tmp_path/'cap','navirai')
    with pytest.raises(ValueError):cap.record('https://api.open-meteo.com/v1/forecast',{'api_key':'secret'})
    with pytest.raises(ValueError):cap.record('https://not-approved.invalid/',{})

def test_units_and_rain_timestep(tmp_path):
    assert quality('wind_speed_10m',10,'m/s')[0]==36
    assert quality('temperature_2m',-5,'°C')[0]==-5
    assert quality('precipitation',1,'inches')[2]=='unknown_unit'
    cap,p,e=fixture_capture(tmp_path);p['hourly']['time'][1]='2026-01-02T02:30'
    assert normalize(p,e,cap.location)[1]['value'] is None

def test_free_client_quota_and_cache(tmp_path,monkeypatch):
    from scripts.science.http import FreeClient
    class Session:
        calls=0
        def get(self,*args,**kwargs):
            self.calls+=1
            class Response:
                status_code=200;content=b'{"value":7}';headers={}
                def raise_for_status(self):pass
                def json(self):return {'value':7}
            return Response()
    monkeypatch.setattr('scripts.science.http.time.sleep',lambda _:None)
    session=Session();client=FreeClient(tmp_path/'cache',session=session)
    args=('https://api.open-meteo.com/v1/forecast',{'latitude':-23,'longitude':-54})
    assert client.get(*args)==client.get(*args);assert session.calls==1
    client.limits['weather_max_equivalent_calls_per_day']=0
    with pytest.raises(ValueError,match='Cota'):client.get(args[0],{'latitude':-24})

def test_historical_products_params():
    from scripts.science.historical import request
    class Client:
        def get(self,*args,**kwargs):return args,kwargs
    args,kw=request(Client(),'previous_runs','diamantino','gfs_global','2026-01-01','2026-01-02')
    assert 'temperature_2m_previous_day7' in args[1]['hourly'];assert kw['initialization'] is None
    with pytest.raises(ValueError):request(Client(),'single_run','navirai','gfs_global','2026-01-01','2026-01-02')
    with pytest.raises(ValueError):request(Client(),'previous_runs','navirai','best_match','2026-01-01','2026-01-02')

def test_static_precision_and_existing_operations():
    root=Path(__file__).resolve().parents[1]
    html=(root/'site/index.html').read_text(encoding='utf-8')
    assert 'data-tab="precision"' in html and 'data-tab="maps"' in html and 'data-tab="agro"' in html
    assert 'AI_PROVIDER' not in html
    js=(root/'site/static/precision_v22.js').read_text(encoding='utf-8')
    assert 'data/verification.json' in js and 'api_key' not in js

def test_rain_daily_uses_interval_end_next_midnight():
    from scripts.collect import model_daily_rain
    times=[f'2026-10-28T{h:02d}:00' for h in range(24)]+['2026-10-29T00:00']
    values=[99]+[1]*23+[.5]
    assert model_daily_rain({'hourly':{'time':times,'precipitation_member01':values}})['days']['2026-10-28']==[23.5]
    assert not model_daily_rain({'hourly':{'time':times[:-1],'precipitation_member01':values[:-1]}})['days']

def test_storage_guard_preserves_previous_archive(tmp_path,monkeypatch):
    cap,_,_=fixture_capture(tmp_path)
    from scripts.science import archive
    monkeypatch.setattr(archive,'config',lambda:{'archive_max_bundle_bytes':1,'archive_max_bytes':10})
    with pytest.raises(ValueError,match='armazenamento'):archive_capture(cap.root,tmp_path/'archive')
    assert not (tmp_path/'archive/manifests').exists()

def test_fixed_lead_and_single_run_request_contract(tmp_path):
    from scripts.science.historical import request
    class Client:
        def get(self,*args,**kwargs):return args,kwargs
    args,kwargs=request(Client(),'single_run','navirai','gfs_global','2026-01-01','2026-01-02',run='2026-01-01T00:00:00Z')
    assert 'start_date' not in args[1] and args[1]['forecast_days']==16
    cap,p,e=fixture_capture(tmp_path)
    p['hourly']={'time':p['hourly']['time'],'temperature_2m_previous_day3':[20,21,22]}
    p['hourly_units']={'temperature_2m_previous_day3':'°C'}
    assert all(r['lead_hours']==72 and r['lead_basis']=='fixed_offset_72h' for r in normalize(p,e,cap.location))

def test_inmet_csv_keeps_station_and_unit_provenance():
    from scripts.science.observations import parse_inmet_csv
    content='CODIGO (WMO):;S735\nData;Hora UTC;PRECIPITACAO TOTAL, HORARIO (mm);VENTO, VELOCIDADE HORARIA (m/s);\n2026/10/28;0100 UTC;0,0;2,0;\n'
    rows=parse_inmet_csv(content,{'id':'INMET:S735'})
    assert rows[0]['value']==0 and rows[0]['interval_start_utc']=='2026-10-28T00:00:00+00:00'
    assert rows[1]['unit']=='m/s' and rows[1]['value']==2
    with pytest.raises(ValueError,match='Código'):parse_inmet_csv(content,{'id':'INMET:OTHER'})

def test_429_has_no_retry_and_is_recorded(tmp_path,monkeypatch):
    import requests
    from scripts.science.http import FreeClient
    class Session:
        calls=0
        def get(self,*args,**kwargs):
            self.calls+=1
            r=requests.Response();r.status_code=429;r._content=b'{"error":"quota"}';r.headers={'Retry-After':'3600'};return r
    cap=Capture(tmp_path/'cap','navirai');session=Session();client=FreeClient(tmp_path/'cache',cap,session)
    with pytest.raises(requests.HTTPError):client.get('https://api.open-meteo.com/v1/forecast',{})
    assert session.calls==1 and cap.manifest['requests'][0]['headers']['Retry-After']=='3600'

def test_workflows_keep_main_deployment_and_separate_archive_writer():
    root=Path(__file__).resolve().parents[1]
    pages=(root/'.github/workflows/pages.yml').read_text(encoding='utf-8')
    writer=(root/'scripts/archive_git.py').read_text(encoding='utf-8')
    assert "7,37 * * * *" in pages and 'actions/deploy-pages@v4' in pages
    assert 'weather-archive-writer' in pages and 'retention-days: 7' in pages
    assert "BRANCH='weather-archive'" in writer and "'--force'" not in writer

def test_ensemble_direction_uses_circular_mean(tmp_path):
    cap,p,e=fixture_capture(tmp_path,members=True)
    p['hourly']={'time':p['hourly']['time'],'wind_direction_10m_member01':[359]*3,'wind_direction_10m_member02':[1]*3}
    p['hourly_units']={'wind_direction_10m_member01':'°','wind_direction_10m_member02':'°'}
    # Replace the fixture response with its circular-direction case.
    cap.manifest['requests']=[]
    e=cap.record('https://api.open-meteo.com/v1/forecast',{'latitude':cap.location['latitude'],'longitude':cap.location['longitude'],'models':'test_model'},content=packed(p),status=200)
    e['collected_at_utc']='2026-01-01T00:00:00Z'
    payload=observation(cap)
    payload['records']=[{'valid_at_utc':'2026-01-02T02:00:00Z','variable':'wind_direction_10m','unit':'degree','value':0}]
    cap.record('https://apitempo.inmet.gov.br/',{},content=packed(payload),status=200,product='station_import');cap.finish()
    db=tmp_path/'db';ingest_manifest(db,cap.root,cap.manifest)
    rows,_=paired_rows(db);directions=[r for r in rows if r['variable']=='wind_direction_10m']
    assert directions and all(min(r['prediction'],360-r['prediction'])<1e-10 for r in directions)


def test_archive_date_filter_counts_only_selected_manifests(tmp_path):
    cap,_,_=fixture_capture(tmp_path);archive=tmp_path/'archive'
    archive_capture(cap.root,archive)
    result=rebuild(archive,tmp_path/'filtered.sqlite',since='2026-01-02')
    assert result['manifests']==0 and result['available_manifests']==1
    assert result['counts']['forecast_runs']==0
    with pytest.raises(ValueError):rebuild(archive,tmp_path/'bad.sqlite',since='tomorrow')
    assert not (tmp_path/'bad.sqlite.building').exists()


def test_station_catalog_keeps_localities_separate():
    from scripts.science.stations import nearest
    rows=[{'CD_SITUACAO':'Operante','CD_ESTACAO':code,'DC_NOME':loc,
           'VL_LATITUDE':location(loc)['latitude'],'VL_LONGITUDE':location(loc)['longitude']}
          for code,loc in [('S735','navirai'),('A901','diamantino')]]
    for code,loc in [('S735','navirai'),('A901','diamantino')]:
        distance,station=nearest(rows,location(loc))
        assert station['id']=='INMET:'+code and distance<.001
    assert nearest([rows[0]],location('diamantino')) is None


def test_station_hourly_preserves_invalid_native_rain_and_full_period(tmp_path):
    from scripts.science.stations import normalize_hourly
    cap,_,_=fixture_capture(tmp_path);meta=observation(cap)['station']
    start=dt.datetime(2026,1,1,tzinfo=dt.timezone.utc)
    raw=[{'CD_ESTACAO':'S735','DT_MEDICAO':(start+dt.timedelta(hours=i)).date().isoformat(),
          'HR_MEDICAO':(start+dt.timedelta(hours=i)).strftime('%H%M'),
          'CHUVA':'-0,1' if i==0 else '0,0','VEN_VEL':'2,34','TEM_INS':'-9999'} for i in range(96)]
    payload=normalize_hourly(raw,meta)
    rain=[r for r in payload['records'] if r['variable']=='precipitation']
    assert len(rain)==96 and rain[0]['value']==-.1
    wind=next(r for r in payload['records'] if r['variable']=='wind_speed_10m')
    assert wind['unit']=='m/s' and wind['value']==2.34
    cap.record('https://apitempo.inmet.gov.br/',{},content=packed(payload),status=200,product='station_import');cap.finish()
    db=tmp_path/'qc.sqlite';ingest_manifest(db,cap.root,cap.manifest)
    with connect(db) as con:
        invalid=con.execute("SELECT original_value,value,qc FROM observations WHERE original_value<0").fetchone()
        assert tuple(invalid)==(-.1,None,'out_of_range')
    with pytest.raises(ValueError,match='estação'):normalize_hourly([{**raw[0],'CD_ESTACAO':'OTHER'}],meta)
    with pytest.raises(ValueError,match='duplicada'):normalize_hourly([raw[0],raw[0]],meta)
