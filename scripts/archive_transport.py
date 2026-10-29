"""Decide capture transport and locate a trusted main-branch recovery artifact."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import requests
from scripts.science.common import instant

REPOSITORY='joaolorencone-unesp/campo-e-clima'

def needs_upload(captures,status):
    files=list(Path(captures).glob('**/manifest.json'))
    if not files:return False
    try:slots=set(json.loads(Path(status).read_text(encoding='utf-8'))['storage']['archived_slots'])
    except (OSError,ValueError,KeyError,TypeError):return True
    for p in files:
        try:
            doc=json.loads(p.read_text(encoding='utf-8'));t=instant(doc['collected_at_utc']);slot=t.replace(hour=t.hour//6*6,minute=0,second=0,microsecond=0)
            if any(r.get('product') in ('station_import','previous_runs','single_run','historical_forecast') for r in doc['requests']):return True
            if f"manifests/{slot:%Y-%m}/{slot:%Y%m%dT%H}-{doc['location']['id']}.json" not in slots:return True
        except (ValueError,KeyError,TypeError):return True
    return False

def locate(run_id,session=None):
    if not str(run_id).isdigit():raise ValueError('ID de execução deve ser inteiro')
    session=session or requests.Session();base=f'https://api.github.com/repos/{REPOSITORY}/actions/runs/{run_id}'
    token=os.environ.get('GH_TOKEN');headers={'Accept':'application/vnd.github+json'}
    if token:headers['Authorization']='Bearer '+token
    def get(url):
        response=session.get(url,headers=headers,timeout=20,allow_redirects=False);response.raise_for_status()
        if response.status_code!=200:raise ValueError('Resposta de API inesperada')
        return response.json()
    run=get(base)
    if run.get('head_branch')!='main' or run.get('head_repository',{}).get('full_name')!=REPOSITORY or run.get('path') not in ('.github/workflows/pages.yml','.github/workflows/science.yml'):
        raise ValueError('Recuperação aceita somente workflows conhecidos da main deste repositório')
    artifacts=get(base+'/artifacts?per_page=100')['artifacts']
    expected={f'science-capture-{run_id}',f'science-history-{run_id}'}
    matches=[a for a in artifacts if a['name'] in expected and not a['expired']]
    if len(matches)>1:raise ValueError('Mais de um artifact elegível; revisão necessária')
    return matches[0]['name'] if matches else ''

def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=['needs-upload','locate']);p.add_argument('--captures',default='runtime/captures');p.add_argument('--status',default='site/data/archive_status.json');p.add_argument('--run-id')
    a=p.parse_args();value=str(needs_upload(a.captures,a.status)).lower() if a.command=='needs-upload' else locate(a.run_id)
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'],'a',encoding='utf-8') as f:f.write(('needed' if a.command=='needs-upload' else 'artifact_name')+'='+value+'\n')
    print(value or 'Artifact ausente/expirado; arquivo permanente preservado')
if __name__=='__main__':main()
