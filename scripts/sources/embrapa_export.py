"""Audit the HTML table returned by Embrapa Guia Clima (misnamed .xls).

A downloaded export DOES NOT embed the selected station ID, therefore it cannot
be treated as verified Naviraí observations until provenance is confirmed.
"""
from __future__ import annotations
import datetime as dt
import csv
import math
from html.parser import HTMLParser
from pathlib import Path
from collections import Counter

MIN_CONFIRMED_START = dt.date(2024, 12, 1)
LABELS = ['date','temperature_mean_c','temperature_max_c','time_tmax',
          'temperature_min_c','time_tmin','relative_humidity_mean_pct',
          'relative_humidity_max_pct','time_rhmax','relative_humidity_min_pct',
          'time_rhmin','wind_mean_m_s','wind_dir_text','wind_max_m_s',
          'time_windmax','precipitation_mm','solar_radiation_mj_m2_day','et0_mm_day']
NUMERIC_FIELDS = {0,1,2,4,6,7,9,11,13,15,16,17}

class EmbrapaTableParser(HTMLParser):
    def __init__(self):
        super().__init__();self.active=False;self.in_row=False;self.in_cell=False
        self.rows=[];self.row=[];self.cell=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='table' and a.get('id')=='tabela':self.active=True
        if not self.active:return
        if tag=='tr':self.in_row=True;self.row=[]
        if tag=='td' and self.in_row:self.in_cell=True;self.cell=[]
    def handle_data(self,data):
        if self.in_cell:self.cell.append(data)
    def handle_endtag(self,tag):
        if not self.active:return
        if tag=='td' and self.in_cell:
            self.row.append(''.join(self.cell).strip());self.in_cell=False
        if tag=='tr' and self.in_row:
            if self.row:self.rows.append(self.row)
            self.in_row=False
        if tag=='table':self.active=False

def number(text):
    t=str(text or '').strip()
    if t in ('','-','—','null'):return None
    x=float(t.replace(',','.'))
    if not math.isfinite(x):raise ValueError('nonfinite numeric cell')
    return x

def parse_export(text:str, *,asof:dt.date|None=None):
    asof=asof or dt.datetime.now(dt.timezone(dt.timedelta(hours=-4))).date()
    parser=EmbrapaTableParser();parser.feed(text)
    if not parser.rows:raise ValueError('Tabela #tabela não encontrada; arquivo errado ou inválido.')
    seen=set();good=[];quarantined=[];issues=[]
    for line,cells in enumerate(parser.rows,1):
        try:
            if len(cells)!=len(LABELS):raise ValueError(f'esperadas 18 colunas, recebidas {len(cells)}')
            day=dt.datetime.strptime(cells[0],'%d/%m/%Y').date()
            if day in seen:raise ValueError('duplicação de data')
            seen.add(day)
            if day>asof:raise ValueError('data posterior à exportação')
            row={'date':day.isoformat()}
            for i in (1,2,4,6,7,9,11,13,15,16,17):row[LABELS[i]]=number(cells[i])
            row['wind_dir_text']=cells[12] if cells[12] not in ('-','') else None
            if row['precipitation_mm'] is not None and not 0<=row['precipitation_mm']<=600:raise ValueError('precipitação fora do limite de plausibilidade')
            for i in (6,7,9):
                x=row[LABELS[i]]
                if x is not None and not 0<=x<=100:raise ValueError('UR fora do intervalo 0–100')
            if day < MIN_CONFIRMED_START:
                quarantined.append({'date':row['date'],'reason':'anterior ao início oficial informado para Naviraí: 2024-12-01'})
            else:good.append(row)
        except (ValueError,TypeError) as ex:issues.append({'row':line,'date':cells[0] if cells else None,'reason':str(ex)})
    good.sort(key=lambda r:r['date'])
    if issues:raise ValueError(f'Linhas inválidas {issues[:10]}')
    full_days=(dt.date.fromisoformat(good[-1]['date'])-dt.date.fromisoformat(good[0]['date'])).days+1 if good else 0
    return {'state':'provisional', 'source':'Embrapa Guia Clima • exportação fornecida pelo usuário',
            'source_url':'https://www.cpao.embrapa.br/gc/busca-de-dados',
            'station_id':None, 'station_confirmation':'not_in_export',
            'record_count':len(good), 'date_first':good[0]['date'] if good else None,
            'date_last':good[-1]['date'] if good else None,
            'missing_calendar_days':max(0,full_days-len(good)),
            'rain_nonmissing_days':sum(r['precipitation_mm'] is not None for r in good),
            'quarantined_count':len(quarantined),'quarantined':quarantined,'records':good,
            'note':'Série provisória: exportação não identifica a estação escolhida. Confirmar Naviraí/IFMS (estação 6) antes de validar métricas. Dias anteriores a 01/12/2024 isolados.'}

def parse_export_path(path:Path):
    return parse_export(path.read_text(encoding='utf-8-sig'))

def save_csv_from_export(inp:Path,out:Path):
    result=parse_export_path(inp)
    out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['date']+LABELS[1:])
        w.writeheader();w.writerows(result['records'])
    return result
