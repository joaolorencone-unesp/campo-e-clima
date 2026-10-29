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
        return root
    if root.exists() and any(root.iterdir()):raise ValueError('Checkout de arquivo exige pasta vazia')
    root.mkdir(parents=True,exist_ok=True)
    git(root,'init','--initial-branch',BRANCH)
    git(root,'remote','add','origin',REPO)
    remote=git(root,'ls-remote','--heads','origin',f'refs/heads/{BRANCH}')
    if remote.stdout.strip():
        git(root,'fetch','--depth=1','origin',BRANCH)
        git(root,'checkout','-B',BRANCH,'FETCH_HEAD')  # New, verified-empty checkout only.
    git(root,'config','user.name','Campo e Clima archive')
    git(root,'config','user.email','41898282+github-actions[bot]@users.noreply.github.com')
    return root

def publish(captures,root,*,push=False,train=False):
    root=prepare(root);out=[]
    for file in sorted(Path(captures).glob('**/manifest.json')):
        # Only capture manifests, never Parquet manifests.
        doc=json.loads(file.read_text(encoding='utf-8'))
        if 'execution_id' not in doc:continue
        if doc.get('status') in ('running','unavailable','failed'):
            out.append({'state':'source_unavailable','location':doc['location']['id'],
                        'requests':[{'source_url':r['source_url'],'status':r.get('http_status'),'error':r.get('error')} for r in doc['requests']]})
            continue
        historical=any(r.get('product') in ('previous_runs','single_run','historical_forecast','reanalysis','station_import') for r in doc['requests'])
        try:out.append(archive_capture(file.parent,root,force_slot='import' if historical else None))
        except (ValueError,OSError) as exc:out.append({'state':'failed','location':doc['location']['id'],'reason':str(exc)})
    changed=any(x['state']=='archived' for x in out)
    if changed or not (root/'public/verification.json').exists():
        # SQLite/Parquet never enter the Git branch or the public website.
        with tempfile.TemporaryDirectory(prefix='campo-science-') as temporary:
            db=Path(temporary)/'science.sqlite'
            replay=rebuild(root,db)
            report=evaluate(db,root/'public/verification.json')
            if train:experiment(db,root/'public/calibration.json')
            explain(db,report,root/'public/explanation.json',provider='none')
            write_json(root/'public/archive_status.json',{'updated_at_utc':now(),'results':out,
                'rebuild_integrity':replay['integrity'],'manifest_count':replay['manifests'],
                'limits_note':'Limite de arquivos 750 MB; Git e serviço remoto precisam de monitoramento adicional'})
        git(root,'add','--','public')
        for folder in ('objects','manifests','imports'):
            if (root/folder).exists():git(root,'add','--',folder)
        if git(root,'diff','--cached','--quiet',check=False).returncode:
            git(root,'commit','-m','Archive verified weather snapshots '+now()[:10])
            if push:
                # Fixed ref destination; rejected concurrent push is surfaced, never forced.
                git(root,'push','origin',f'HEAD:refs/heads/{BRANCH}')
    failures=[x for x in out if x['state']=='failed']
    if failures:raise RuntimeError(json.dumps(failures,ensure_ascii=False))
    return {'results':out,'branch':BRANCH,'pushed':bool(push and changed)}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--captures',default='runtime/captures');p.add_argument('--checkout',default='runtime/archive-git')
    p.add_argument('--push',action='store_true');p.add_argument('--train',action='store_true')
    a=p.parse_args();print(json.dumps(publish(a.captures,a.checkout,push=a.push,train=a.train),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
