"""Copy already archived public reports; keep prior timestamps on failure."""
import json
import re
from pathlib import Path
import requests
from scripts.science.common import atomic

def validate(name,value):
    if not isinstance(value,dict):raise ValueError('Relatório inválido')
    if name=='verification.json':
        if value.get('schema_version')!=1 or not isinstance(value.get('locations'),list) or not isinstance(value.get('results'),list):raise ValueError('Esquema científico incompatível')
        from scripts.science.common import config
        expected={l['id']:l for l in config()['locations']}
        ids=[l['id'] for l in value['locations']]
        if len(ids)!=len(set(ids)):raise ValueError('Localidade duplicada')
        for loc in value['locations']:
            if loc['id'] not in expected or any(abs(loc[k]-expected[loc['id']][k])>1e-6 for k in ('latitude','longitude')):raise ValueError('Coordenadas científicas divergentes')
        if any(r['location_id'] not in ids for r in value['results']):raise ValueError('Resultado sem localidade cadastrada')
    if name=='calibration.json' and value.get('primary_forecast_replaced') is not False:raise ValueError('Promoção de calibrador não autorizada')
    if name=='explanation.json' and value.get('effective_provider')!='none':raise ValueError('IA externa não autorizada')
    return value

def main():
    try:
        ref=requests.get('https://api.github.com/repos/joaolorencone-unesp/campo-e-clima/git/ref/heads/weather-archive',timeout=20)
        ref.raise_for_status();commit=ref.json()['object']['sha']
        if not re.fullmatch('[0-9a-f]{40}',commit):raise ValueError('Referência Git inválida')
        root=f'https://raw.githubusercontent.com/joaolorencone-unesp/campo-e-clima/{commit}/public/'
        pending={}
        for name in ('verification.json','calibration.json','explanation.json','archive_status.json'):
            response=requests.get(root+name,timeout=20)
            if name=='archive_status.json' and response.status_code==404:continue
            response.raise_for_status();value=response.json()
            validate(name,value)
            pending[name]=json.dumps({**value,'archive_commit':commit},ensure_ascii=False,separators=(',',':')).encode('utf-8')
        for name,body in pending.items():
            dest=Path('site/data')/name;dest.parent.mkdir(parents=True,exist_ok=True)
            atomic(dest,body)
        return {'state':'ok','archive_commit':commit}
    except (requests.RequestException,ValueError,KeyError,TypeError) as exc:
        print('Arquivo científico indisponível:',type(exc).__name__,'; relatórios anteriores mantêm suas datas')
        return {'state':'previous_preserved','error':type(exc).__name__}
if __name__=='__main__':main()
