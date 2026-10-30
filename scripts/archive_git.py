"""Commit immutable scientific files only to weather-archive, never main.

Local default is no push. Actions must pass --push explicitly. No force-push.
An Actions artifact is only a transport envelope for the same collected response.
"""
from __future__ import annotations
import argparse
import base64
import json
import os
from pathlib import Path
import subprocess
import tempfile
from scripts.science.archive import archive_capture, rebuild
from scripts.science.common import now, write_json
from scripts.science.evaluation import evaluate
from scripts.science.calibration import experiment
from scripts.science.explanations import explain
from scripts.science.storage import inventory, warn

REPO='https://github.com/joaolorencone-unesp/campo-e-clima.git'
BRANCH='weather-archive'

def git(root,*args,check=True):
    env=os.environ.copy()
    # Token stays in the subprocess environment, never in URL, files or printed args.
    token=env.get('GH_TOKEN')
    if token:
        auth=base64.b64encode(('x-access-token:'+token).encode()).decode()
        env.update(GIT_CONFIG_COUNT='1',GIT_CONFIG_KEY_0='http.https://github.com/.extraheader',GIT_CONFIG_VALUE_0='AUTHORIZATION: basic '+auth)
    return subprocess.run(['git','-C',str(root),*args],env=env,text=True,capture_output=True,check=check)

def prepare(root):
    root=Path(root)
    if (root/'.git').exists():
        branch=git(root,'branch','--show-current').stdout.strip()
        if branch!=BRANCH:raise ValueError('Destino não é weather-archive')
        if git(root,'status','--porcelain').stdout.strip():raise ValueError('Checkout de arquivo tem alterações locais; preservar e revisar')
        return root
    if root.exists() and any(root.iterdir()):raise ValueError('Checkout de arquivo exige pasta vazia')
    root.parent.mkdir(parents=True,exist_ok=True)
    remote=git(root.parent,'ls-remote','--heads',REPO,f'refs/heads/{BRANCH}')
    if not remote.stdout.strip():
        raise ValueError('Branch weather-archive ausente no remoto: publicar o backup aprovado antes de arquivar; criação vazia bloqueada')
    root.mkdir(parents=True,exist_ok=True)
    git(root,'init','--initial-branch',BRANCH)
    git(root,'remote','add','origin',REPO)
    if remote.stdout.strip():
        # Full archive history is required for the Git byte budget to be meaningful.
        git(root,'fetch','origin',BRANCH)
        git(root,'checkout','-B',BRANCH,'FETCH_HEAD')  # New, verified-empty checkout only.
    git(root,'config','user.name','Campo e Clima archive')
    git(root,'config','user.email','41898282+github-actions[bot]@users.noreply.github.com')
    return root

def publish(captures,root,*,push=False,train=False):
    files=sorted(Path(captures).glob('**/manifest.json'))
    if not files:
        return {'results':[],'state':'no_capture','branch':BRANCH,'pushed':False,
                'note':'Artifact/captura ausente: nenhum checkout, relatório ou histórico foi alterado'}
    root=prepare(root);out=[]
    if push and git(root,'remote','get-url','origin').stdout.strip()!=REPO:
        raise ValueError('Destino remoto divergente; push bloqueado')
    for file in files:
        # Only capture manifests, never Parquet manifests.
        try:doc=json.loads(file.read_text(encoding='utf-8'))
        except (ValueError,OSError):
            out.append({'state':'failed','reason':'Manifesto de captura inválido'});continue
        if 'execution_id' not in doc:continue
        if doc.get('status') in ('running','unavailable','failed'):
            out.append({'state':'source_unavailable','location':doc['location']['id'],
                        'requests':[{'source_url':r['source_url'],'status':r.get('http_status'),'error':r.get('error')} for r in doc['requests']]})
            continue
        historical=any(r.get('product') in ('previous_runs','single_run','historical_forecast','reanalysis','station_import') for r in doc['requests'])
        try:out.append(archive_capture(file.parent,root,force_slot='import' if historical else None))
        except (ValueError,OSError) as exc:out.append({'state':'failed','location':doc['location']['id'],'reason':str(exc)})
    changed=any(x['state']=='archived' for x in out)
    status_file=root/'public/archive_status.json'
    previous=json.loads(status_file.read_text(encoding='utf-8')) if status_file.exists() else {}
    report_error=None
    reports_refreshed=False
    if changed or previous.get('report_status')=='previous_preserved' or (not (root/'public/verification.json').exists() and list(root.glob('manifests/**/*.json'))):
        # SQLite/Parquet never enter the Git branch or the public website.
        try:
            with tempfile.TemporaryDirectory(prefix='campo-science-') as temporary:
                temp=Path(temporary);db=temp/'science.sqlite';replay=rebuild(root,db)
                report=evaluate(db,temp/'verification.json')
                if train or not (root/'public/calibration.json').exists():experiment(db,temp/'calibration.json')
                explain(db,report,temp/'explanation.json',provider='none')
                for p in temp.glob('*.json'):
                    from scripts.science.common import atomic
                    atomic(root/'public'/p.name,p.read_bytes())
                reports_refreshed=True
        except Exception as exc:
            # RAW remains publishable, prior derived reports remain byte-for-byte intact.
            report_error=type(exc).__name__+': '+str(exc)[:180]
            out.append({'state':'failed','reason':'Relatório derivado falhou; RAW preservado','error':report_error})
    storage=inventory(root);warn(storage)
    failures=[x for x in out if x['state'] in ('failed','source_unavailable')]
    update_status=changed or reports_refreshed or not previous or previous.get('storage',{}).get('severity')!=storage['severity'] or previous.get('failures')!=failures
    if update_status:
        write_json(status_file,{'updated_at_utc':now(),'results':out,'failures':failures,'storage':storage,
            'report_status':'previous_preserved' if report_error else 'current' if reports_refreshed else previous.get('report_status','unchanged'),
            'manifest_count':len(list(root.glob('manifests/**/*.json')))+len(list(root.glob('imports/**/*.json'))),
            'recovery_note':'Capturas sem publicação permanecem no artifact temporário por 7 dias. Restaurar explicitamente antes de expirar.'})
    for folder in ('objects','manifests','imports','public'):
        if (root/folder).exists():git(root,'add','--',folder)
    committed=False;pushed=False
    if git(root,'diff','--cached','--quiet',check=False).returncode:
        git(root,'commit','-m','Archive verified weather snapshots '+now()[:10]);committed=True
    if push:
        # Also retries a previous unpublished local commit. Never overwrites divergent history.
        git(root,'push','origin',f'HEAD:refs/heads/{BRANCH}');pushed=True
    failures=[x for x in out if x['state']=='failed']
    if failures:raise RuntimeError(json.dumps(failures,ensure_ascii=False))
    return {'results':out,'branch':BRANCH,'pushed':pushed,'committed':committed,'storage':storage}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--captures',default='runtime/captures');p.add_argument('--checkout',default='runtime/archive-git')
    p.add_argument('--push',action='store_true');p.add_argument('--train',action='store_true')
    a=p.parse_args();print(json.dumps(publish(a.captures,a.checkout,push=a.push,train=a.train),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
