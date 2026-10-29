"""Official file ingestion with explicit station metadata; no fabricated station identity."""
from __future__ import annotations
import csv
import base64
import datetime as dt
import io
import json
import unicodedata
from pathlib import Path
from .common import digest, instant, iso, location, packed
from .ingest import VARIABLES

def import_csv(path, station_file, capture, *, format='canonical'):
    station=json.loads(Path(station_file).read_text(encoding='utf-8'))
    content=Path(path).read_bytes()
    try:text=content.decode('utf-8-sig')
    except UnicodeDecodeError:text=content.decode('latin1')
    if format=='canonical':
        rows=list(csv.DictReader(io.StringIO(text)))
        required={'valid_at_utc','variable','unit','value'}
        if not rows or not required<=set(rows[0]):raise ValueError('Cabeçalho canônico incompleto')
        for row in rows:
            row['valid_at_utc']=iso(row['valid_at_utc'])
            raw=row['value'].strip()
            row['value']=None if raw.lower() in ('','nan','null','-9999') else float(raw.replace(',','.'))
    elif format=='inmet':
        rows=parse_inmet_csv(text,station)
    else:raise ValueError('Formato não suportado')
    # The exact original text is embedded with its hash for reproducibility, not served in Pages.
    payload={'station':station,'records':rows,'source_file_sha256':digest(content),
        'source_bytes_base64':base64.b64encode(content).decode('ascii'),
        'format':format,'normalizer_version':'1.0.0'}
    source=station['evidence_url']
    if not source.startswith(('https://portal.inmet.gov.br/','https://apitempo.inmet.gov.br/','https://www.cpao.embrapa.br/')):
        raise ValueError('Arquivo exige referência institucional permitida')
    # File import uses a constant institutional endpoint in the capture; actual evidence stays in payload.
    capture.record('https://apitempo.inmet.gov.br/',{},content=packed(payload),status=200,product='station_import')
    return capture.finish()

def plain(s):
    return ''.join(c for c in unicodedata.normalize('NFD',s.upper()) if unicodedata.category(c)!='Mn')

def parse_inmet_csv(text,station):
    lines=text.splitlines();header=next((i for i,l in enumerate(lines) if plain(l).startswith('DATA;')),None)
    if header is None:raise ValueError('Cabeçalho horário oficial INMET ausente')
    metadata='\n'.join(lines[:header])
    code=station['id'].split(':')[-1]
    if code not in metadata:raise ValueError('Código da estação não confere com o arquivo')
    mappings=[('TEMPERATURA DO AR - BULBO SECO','temperature_2m','degC'),
              ('UMIDADE RELATIVA DO AR, HORARIA','relative_humidity_2m','%'),
              ('PRECIPITACAO TOTAL','precipitation','mm'),
              ('VENTO, VELOCIDADE HORARIA','wind_speed_10m','m/s'),
              ('VENTO, RAJADA MAXIMA','wind_gusts_10m','m/s'),
              ('VENTO, DIRECAO HORARIA','wind_direction_10m','degree')]
    result=[];seen=set()
    for row in csv.DictReader(io.StringIO('\n'.join(lines[header:])),delimiter=';'):
        keys={plain(k):k for k in row if k}
        date_key=next((v for k,v in keys.items() if k.startswith('DATA')),None)
        hour_key=next((v for k,v in keys.items() if k.startswith('HORA')),None)
        if not date_key or not hour_key:raise ValueError('Data/hora INMET ausentes')
        day=row[date_key].replace('/','-');hour=row[hour_key].replace(' UTC','').replace(':','').zfill(4)
        t=instant(f'{day}T{hour[:2]}:{hour[2:4]}:00+00:00')
        if iso(t) in seen:raise ValueError('Data/hora duplicada no arquivo INMET')
        seen.add(iso(t))
        for prefix,var,unit in mappings:
            key=next((v for k,v in keys.items() if k.startswith(prefix)),None)
            if not key:continue
            raw=row[key].strip()
            value=None if raw in ('','-9999','-9999,0') else float(raw.replace(',','.'))
            result.append({'valid_at_utc':iso(t),'variable':var,'unit':unit,'value':value,
                'interval_start_utc':iso(t-dt.timedelta(hours=1)) if var=='precipitation' else None,
                'interval_end_utc':iso(t) if var=='precipitation' else None,'available_at_utc':None})
    return result
