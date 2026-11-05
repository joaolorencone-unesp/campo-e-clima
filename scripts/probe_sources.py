"""Live probe of free external sources (read-only, prints what each endpoint answers).

Run in CI as a non-blocking job; nothing is stored or published. Used to confirm formats and
identifiers (CEMADEN catalogue/data, INMET alerts JSON+RSS, INMET WIS 2.0, GIBS GLM layer ids,
CPTEC MERGE daily figure) before the site relies on them.
"""
import datetime as dt
import json
import re
import requests

H = {'User-Agent': 'Campo-e-Clima/4.1 (pesquisa não comercial; sondagem de formato)'}


def show(label, fn):
    try:
        print(f'\n=== {label}\n' + str(fn())[:1500])
    except Exception as exc:  # noqa: BLE001
        print(f'\n=== {label}\nERRO {type(exc).__name__}: {str(exc)[:300]}')


def main():
    now = dt.datetime.now(dt.timezone.utc)
    show('CEMADEN catálogo MS', lambda: (lambda r: f'HTTP {r.status_code} {r.headers.get("content-type")} ' + r.text[:900])(
        requests.get('https://sws.cemaden.gov.br/PED/rest/pcds-cadastro/estacoes', params={'uf': 'MS'}, timeout=40, headers=H)))
    since = now - dt.timedelta(hours=24)
    show('CEMADEN dados Naviraí 24h', lambda: (lambda r: f'HTTP {r.status_code} {r.headers.get("content-type")} ' + r.text[:900])(
        requests.get('https://sws.cemaden.gov.br/PED/rest/pcds/dados_pcd', params={'rede': 11, 'uf': 'MS', 'inicio': since.strftime('%Y%m%d%H%M'), 'fim': now.strftime('%Y%m%d%H%M'), 'codibge': '5005707'}, timeout=60, headers=H)))
    show('INMET avisos JSON', lambda: (lambda r: f'HTTP {r.status_code} ' + r.text[:400])(requests.get('https://apiprevmet3.inmet.gov.br/avisos/ativos', timeout=30, headers=H)))
    show('INMET avisos RSS', lambda: (lambda r: f'HTTP {r.status_code} itens={r.text.count("<item>")} ' + r.text[:500])(requests.get('https://apiprevmet3.inmet.gov.br/avisos/rss', timeout=30, headers=H)))
    show('INMET WIS2 estações (S735/A949)', lambda: (lambda r: f'HTTP {r.status_code} ' + json.dumps([f.get('properties') for f in r.json().get('features', []) if re.search('NAVIRA|DIAMANTINO', json.dumps(f.get('properties')).upper())][:4], ensure_ascii=False)[:1200])(
        requests.get('https://wis2bra.inmet.gov.br/oapi/collections/stations/items', params={'f': 'json', 'limit': 2000}, timeout=60, headers=H)))
    show('INMET WIS2 synop últimas', lambda: (lambda r: f'HTTP {r.status_code} ' + json.dumps([f.get('properties') for f in r.json().get('features', [])][:3], ensure_ascii=False)[:1200])(
        requests.get('https://wis2bra.inmet.gov.br/oapi/collections/urn:wmo:md:br-inmet:synop/items', params={'f': 'json', 'limit': 3, 'sortby': '-reportTime'}, timeout=60, headers=H)))
    show('GIBS camadas GOES/GLM/IMERG (GetCapabilities)', lambda: (lambda r: f'HTTP {r.status_code} ' + ' | '.join(sorted(set(re.findall(r'<ows:Identifier>((?:GOES-East|IMERG)[^<]*)</ows:Identifier>', r.text))))[:1500])(
        requests.get('https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/wmts.cgi', params={'SERVICE': 'WMTS', 'REQUEST': 'GetCapabilities', 'VERSION': '1.0.0'}, timeout=90, headers=H)))
    y = now - dt.timedelta(days=1)
    url = f'https://data.inpe.br/bdc/data/prec_merge_daily/FIG/DAILY/{y:%Y/%m}/MERGE_DAILY_{y:%Y%m%d}.png'
    show('CPTEC MERGE figura de ontem ' + url, lambda: (lambda r: f'HTTP {r.status_code} {r.headers.get("content-type")} {r.headers.get("content-length")}')(requests.head(url, timeout=30, headers=H, allow_redirects=True)))


if __name__ == '__main__':
    main()
