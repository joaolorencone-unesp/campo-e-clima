"""Bounded archive monitoring; never deletes scientific records or rewrites Git."""
from __future__ import annotations
import datetime as dt
import json
import subprocess
from pathlib import Path
from .common import config, instant, now

def inventory(root, *, limits=None):
    root=Path(root);limits=limits or config()
    if not root.is_dir():raise FileNotFoundError('Diretório do arquivo científico não encontrado')
    files=[p for p in root.rglob('*') if p.is_file() and '.git' not in p.relative_to(root).parts and not p.is_symlink()]
    size=sum(p.stat().st_size for p in files)
    objects=sum(p.stat().st_size for p in files if p.relative_to(root).parts[0]=='objects')
    git_bytes=None
    if (root/'.git').exists():
        proc=subprocess.run(['git','-C',str(root),'count-objects','-v'],text=True,capture_output=True)
        if proc.returncode==0:
            stats=dict(line.split(': ',1) for line in proc.stdout.splitlines() if ': ' in line)
            git_bytes=1024*(int(stats.get('size',0))+int(stats.get('size-pack',0)))
    limit=limits['archive_max_bytes'];ratio=size/limit
    thresholds=limits.get('archive_alert_fractions',[.5,.7,.85,.95])
    severity='blocked' if ratio>=1 else 'critical' if ratio>=thresholds[3] else 'rotation_required' if ratio>=thresholds[2] else 'warning' if ratio>=thresholds[1] else 'notice' if ratio>=thresholds[0] else 'ok'
    git_limit=limits.get('archive_git_max_bytes',1_000_000_000)
    if git_bytes is not None and git_bytes>=git_limit:severity='blocked'
    elif git_bytes is not None and git_bytes>=git_limit*.85 and severity in ('ok','notice','warning'):severity='rotation_required'
    dates=[];slots=[]
    for p in sorted(root.glob('manifests/**/*.json')):
        doc=json.loads(p.read_text(encoding='utf-8'));dates.append(instant(doc['collected_at_utc']));slots.append(p.relative_to(root).as_posix())
    rate=None
    if len(dates)>=4 and (max(dates)-min(dates)).total_seconds()>=86400:
        rate=objects/max(1,(max(dates)-min(dates)).total_seconds()/86400)
    return {'checked_at_utc':now(),'archive_bytes':size,'object_bytes':objects,'git_object_bytes':git_bytes,
        'limit_bytes':limit,'git_limit_bytes':git_limit,'used_fraction':round(ratio,5),'severity':severity,
        'threshold_fractions':thresholds,'operational_manifests':len(slots),'archived_slots':slots,
        'observed_bytes_per_day':round(rate) if rate else None,
        'estimated_days_to_limit':round(max(0,limit-size)/rate,1) if rate else None,
        'projection_note':'Taxa observada inclui imports e deduplicação; estimativa indicativa. Sem pelo menos um dia, não extrapolar.',
        'required_action':'Antes de 85%: backup mensal verificado em duas cópias locais; preparar novo repositório público gratuito e catálogo de ligação, com aprovação. Não remover nem reescrever este histórico.'}

def warn(status):
    if status['severity']!='ok':
        print(f"::warning title=Arquivo científico - {status['severity']}::Uso {status['archive_bytes']} / {status['limit_bytes']} bytes. {status['required_action']}")

def main():
    import argparse
    from .common import write_json
    p=argparse.ArgumentParser();p.add_argument('--archive',default='weather-archive');p.add_argument('--output')
    args=p.parse_args();result=inventory(args.archive);warn(result)
    if args.output:write_json(args.output,result)
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
