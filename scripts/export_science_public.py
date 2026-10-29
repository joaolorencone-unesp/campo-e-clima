"""Copy already archived public reports; keep prior timestamps on failure."""
import json
from pathlib import Path
import requests

def main():
    root='https://raw.githubusercontent.com/joaolorencone-unesp/campo-e-clima/weather-archive/public/'
    for name in ('verification.json','calibration.json','explanation.json','archive_status.json'):
        try:
            response=requests.get(root+name,timeout=20)
            response.raise_for_status();value=response.json()
            if not isinstance(value,dict):raise ValueError('Relatório inválido')
            if name=='verification.json' and (value.get('schema_version')!=1 or not isinstance(value.get('locations'),list)):
                raise ValueError('Esquema científico incompatível')
            dest=Path('site/data')/name;dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_text(json.dumps(value,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
        except (requests.RequestException,ValueError) as exc:
            print(name,'indisponível:',type(exc).__name__,'; relatório anterior mantém sua data')
if __name__=='__main__':main()
