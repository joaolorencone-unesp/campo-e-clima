"""Strict, human-reviewed Embrapa Naviraí daily CSV import.

Header standardized and station verified; no auto-scraping/fictional records.
Data must be explicitly exported for *Naviraí* from the Guia Clima website.
"""
from __future__ import annotations
import csv
import datetime as dt
import io
import math
from pathlib import Path
from typing import Any

SOURCE_URL = 'https://www.cpao.embrapa.br/gc/busca-de-dados'
EXPECTED_STATION = '6'
FIRST_DAY = dt.date(2024,12,1)


def parse_day(v:str) -> dt.date:
    v=(v or '').strip()
    for form in ('%Y-%m-%d','%d/%m/%Y'):
        try:return dt.datetime.strptime(v,form).date()
        except ValueError:continue
    raise ValueError('invalid date')


def num(v:Any):
    if v is None or not str(v).strip():return None
    s=str(v).strip().replace(' ','')
    if ',' in s: s=s.replace('.','').replace(',','.') if '.' in s else s.replace(',','.')
    n=float(s)
    if not math.isfinite(n):raise ValueError('nonfinite number')
    return n


def read_history(csv_text:str, *, asof:dt.date|None=None) -> dict:
    """Only CSV with required normalized schema; manual conversion/QA first.

    Rejects bad rows and *the whole dataset* if duplicates or wrong station found,
    avoiding contamination of forecast verification by a wrong location.
    """
    asof=asof or dt.datetime.now(dt.timezone(dt.timedelta(hours=-4))).date()
    rows=[];errors=[];seen=set()
    if not csv_text.strip():
        return {'state':'no_data','records':[],'errors':['Arquivo CSV vazio']}
    try:
        dialect=csv.Sniffer().sniff(csv_text[:2500],delimiters=';,\t')
        reader=csv.DictReader(io.StringIO(csv_text.lstrip('\ufeff')),dialect=dialect)
    except csv.Error as ex:
        return {'state':'invalid','records':[],'errors':[str(ex)]}
    # Strict, documented template; Excel exports must be manually mapped/checked.
    required={'station_id','date','precipitation_mm'}
    if not required.issubset(set(reader.fieldnames or [])):
        return {'state':'invalid','records':[],
                'errors':['Cabeçalhos obrigatórios: station_id,date,precipitation_mm']}
    for line,row in enumerate(reader,2):
        if not any((v or '').strip() for v in row.values() if isinstance(v,str)):continue
        try:
            if str(row.get('station_id','')).strip() != EXPECTED_STATION:
                raise ValueError('estação incorreta: deveria ser a estação 6 (Naviraí/IFMS)')
            day=parse_day(row['date'])
            if not FIRST_DAY <= day <= asof:
                raise ValueError('data fora do período da estação / data futura')
            if day in seen:raise ValueError('data duplicada')
            seen.add(day)
            rain=num(row['precipitation_mm'])
            if rain is not None and not 0<=rain<=600:
                raise ValueError('chuva fora de faixa de triagem 0–600 mm/dia')
            temp=num(row.get('temperature_mean_c'))
            if temp is not None and not -15<=temp<=50:raise ValueError('temperatura fora de faixa')
            rh=num(row.get('relative_humidity_mean_pct'))
            if rh is not None and not 0<=rh<=100:raise ValueError('UR fora de 0–100%')
            rows.append({'date':day.isoformat(),'precipitation_mm':rain,
                         'temperature_mean_c':temp,'relative_humidity_mean_pct':rh})
        except (ValueError, TypeError) as e: errors.append(f'Linha {line}: {e}')
    if errors:
        return {'state':'invalid','records':[], 'errors':errors[:35],
                'note':'Falha de validação: nenhum dado é publicado até revisão do CSV.'}
    rows.sort(key=lambda r:r['date'])
    nonmissing_rain=sum(r['precipitation_mm'] is not None for r in rows)
    span=(dt.date.fromisoformat(rows[-1]['date'])-dt.date.fromisoformat(rows[0]['date'])).days+1 if rows else 0
    return {'state':'ok' if rows else 'no_data','source':'Embrapa Guia Clima Naviraí/IFMS',
            'source_url':SOURCE_URL,'station_id':EXPECTED_STATION,
            'imported_at_utc':dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'),
            'records':rows,'record_count':len(rows),'rain_nonmissing_days':nonmissing_rain,
            'calendar_span_days':span,'missing_calendar_days':max(span-len(rows),0),
            'note':'Dados históricos importados manualmente. Comparar a validade/intervalo de cada observação antes de calcular habilidade preditiva.'}


def load_optional(path:Path) -> dict:
    if not path.is_file():
        return {'state':'not_integrated','source':'Embrapa Guia Clima Naviraí/IFMS',
                'source_url':SOURCE_URL,'note':'Aguardando CSV exportado/normalizado para estação 6; não há observação validada.'}
    try:
        data=path.read_text(encoding='utf-8-sig')
        return read_history(data)
    except (OSError,UnicodeDecodeError) as ex:
        return {'state':'unavailable','error':str(ex)[:200],'source_url':SOURCE_URL}
