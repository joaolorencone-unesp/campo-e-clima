"""Regression of failure recovery, storage policy and the publication boundary."""
import json
from pathlib import Path
import subprocess
import pytest
import yaml
from scripts.archive_git import publish
from scripts.archive_backup import create,verify
from scripts.archive_transport import needs_upload,locate,REPOSITORY
from scripts.science.capture import Capture
from scripts.science.archive import archive_capture,rebuild
from scripts.science.common import packed
from scripts.science.storage import inventory
from scripts.science.database import counts

def capture(tmp_path,day='01'):
    cap=Capture(tmp_path/'captures/navirai','navirai',collected_at=f'2026-01-{day}T00:00:00Z')
    payload={'latitude':-23.065,'longitude':-54.19,'timezone':'UTC','hourly':{'time':[f'2026-01-{day}T01:00'],'temperature_2m':[25]},'hourly_units':{'temperature_2m':'°C'}}
    event=cap.record('https://api.open-meteo.com/v1/forecast',{'latitude':-23.065,'longitude':-54.19,'models':'synthetic'},content=packed(payload),status=200)
    event['collected_at_utc']=f'2026-01-{day}T00:00:00Z';cap.finish();return cap

def repo(root):
    root.mkdir()
    def git(*args):return subprocess.run(['git','-C',str(root),*args],capture_output=True,text=True,check=True).stdout.strip()
    git('init','--initial-branch','weather-archive');git('config','user.name','Local test');git('config','user.email','test@example.invalid')
    return git

def test_missing_artifact_does_not_create_or_modify_archive(tmp_path,monkeypatch):
    monkeypatch.setattr('scripts.archive_git.prepare',lambda _:pytest.fail('Must not touch Git'))
    result=publish(tmp_path/'missing',tmp_path/'archive')
    assert result['state']=='no_capture' and not (tmp_path/'archive').exists()

def test_archive_checkout_includes_history_for_storage_monitoring(tmp_path,monkeypatch):
    import scripts.archive_git as writer
    source=tmp_path/'source';git=repo(source)
    for value in ('first','second'):
        (source/'data').write_text(value);git('add','data');git('commit','-m',value)
    monkeypatch.setattr(writer,'REPO',str(source))
    target=writer.prepare(tmp_path/'checkout')
    assert writer.git(target,'rev-list','--count','HEAD').stdout.strip()=='2'
    assert writer.git(target,'rev-parse','--is-shallow-repository').stdout.strip()=='false'

def test_derived_failure_preserves_raw_and_previous_reports(tmp_path,monkeypatch):
    root=tmp_path/'archive';git=repo(root);cap=capture(tmp_path)
    publish(tmp_path/'captures',root);before=(root/'public/verification.json').read_bytes();commit=git('rev-parse','HEAD')
    capture(tmp_path,'02')
    def failure(*args):raise RuntimeError('simulated report failure')
    monkeypatch.setattr('scripts.archive_git.evaluate',failure)
    with pytest.raises(RuntimeError,match='RAW preservado'):publish(tmp_path/'captures',root)
    assert git('rev-parse','HEAD')!=commit and git('status','--porcelain')==''
    assert (root/'public/verification.json').read_bytes()==before
    assert len(list(root.glob('manifests/**/*.json')))==2
    assert json.loads((root/'public/archive_status.json').read_text())['report_status']=='previous_preserved'

def test_monthly_backup_restore_reconstruct_and_corruption(tmp_path):
    cap=capture(tmp_path);root=tmp_path/'archive';archive_capture(cap.root,root)
    original=tmp_path/'original.sqlite';rebuild(root,original)
    result=create(root,tmp_path/'backup');assert result['parts']==1
    verify(tmp_path/'backup',tmp_path/'restored');rebuild(tmp_path/'restored',tmp_path/'restored.sqlite')
    assert counts(original)==counts(tmp_path/'restored.sqlite')
    with pytest.raises(FileExistsError):create(root,tmp_path/'backup')
    z=next((tmp_path/'backup').glob('*.zip'));z.write_bytes(z.read_bytes()+b'corrupt')
    with pytest.raises(ValueError,match='volume'):verify(tmp_path/'backup')

@pytest.mark.parametrize('size,severity',[(10,'ok'),(50,'notice'),(70,'warning'),(85,'rotation_required'),(95,'critical'),(100,'blocked')])
def test_progressive_storage_alerts_preserve_all_files(tmp_path,size,severity):
    (tmp_path/'data').write_bytes(b'x'*size)
    result=inventory(tmp_path,limits={'archive_max_bytes':100})
    assert result['severity']==severity and (tmp_path/'data').stat().st_size==size
    assert result['estimated_days_to_limit'] is None

def test_storage_missing_archive_is_not_reported_as_healthy(tmp_path):
    with pytest.raises(FileNotFoundError):inventory(tmp_path/'missing')

def test_transport_only_unarchived_slots(tmp_path):
    cap=capture(tmp_path);root=tmp_path/'archive';status=tmp_path/'status.json'
    assert needs_upload(tmp_path/'captures',status)
    archive_capture(cap.root,root);status.write_text(json.dumps({'storage':inventory(root)}))
    assert not needs_upload(tmp_path/'captures',status)
    capture(tmp_path,'02');assert needs_upload(tmp_path/'captures',status)
    assert not needs_upload(tmp_path/'absent',status)

def test_recovery_missing_expired_and_foreign_artifact():
    class Session:
        branch='main';expired=False;artifacts=True
        def get(self,url,**kwargs):
            value={'head_branch':self.branch,'head_repository':{'full_name':REPOSITORY},'path':'.github/workflows/pages.yml'}
            if '/artifacts?' in url:value={'artifacts':[{'name':'science-capture-123','expired':self.expired}] if self.artifacts else []}
            class Response:
                status_code=200
                def raise_for_status(self):pass
                def json(self):return value
            return Response()
    s=Session();assert locate(123,s)=='science-capture-123'
    s.expired=True;assert locate(123,s)==''
    s.branch='feature/untrusted'
    with pytest.raises(ValueError,match='main'):locate(123,s)

def test_workflow_failure_boundaries_and_offline_pr_ci():
    root=Path(__file__).resolve().parents[1]
    docs={p.stem:yaml.safe_load(p.read_text()) for p in (root/'.github/workflows').glob('*.yml')}
    pages=docs['pages']['jobs'];assert pages['deploy']['needs']=='build'
    assert 'capture_artifact' in pages['archive']['if'] and 'always()' in pages['archive']['if']
    assert pages['archive']['concurrency']['queue']=='max'
    assert pages['deploy']['permissions']=={'pages':'write','id-token':'write'}
    ci=(root/'.github/workflows/ci.yml').read_text()
    assert 'pull_request:' in ci and 'pull_request_target:' not in ci and 'CAMPO_OFFLINE_TESTS' in ci
    assert 'contents: write' not in ci and 'secrets.' not in ci
    assert docs['science']['concurrency']['group']==docs['archive-recovery']['concurrency']['group']=='weather-archive-writer'

def test_export_rejects_wrong_coordinates_and_keeps_previous_on_failure(tmp_path,monkeypatch):
    import scripts.export_science_public as exporter
    from scripts.science.common import location
    value={'schema_version':1,'locations':[{**location('navirai'),'latitude':-14.408}],'results':[]}
    with pytest.raises(ValueError,match='Coordenadas'):exporter.validate('verification.json',value)
    monkeypatch.chdir(tmp_path);dest=tmp_path/'site/data/verification.json';dest.parent.mkdir(parents=True);dest.write_text('{"old":true}')
    import requests
    monkeypatch.setattr(exporter.requests,'get',lambda *args,**kwargs:(_ for _ in ()).throw(requests.ConnectionError()))
    assert exporter.main()['state']=='previous_preserved' and dest.read_text()=='{"old":true}'
