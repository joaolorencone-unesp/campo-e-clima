"""Small daily deterministic backfill; public two-location scope only."""
import datetime as dt
from pathlib import Path
from scripts.science.common import now, write_json
from scripts.science_cli import main

def run():
    end=dt.datetime.now(dt.timezone.utc).date()-dt.timedelta(days=2)
    start=end-dt.timedelta(days=6)
    results=[]
    for loc in ('navirai','diamantino'):
        try:
            result=main(['historical','--product','previous_runs','--location',loc,
                '--model','gfs_global','--start',str(start),'--end',str(end),'--archive','runtime/import-archive'])
            results.append({'location':loc,'state':'ok','result':result})
        except Exception as exc:results.append({'location':loc,'state':'failed','error':str(exc)[:180]})
    for loc in ('navirai','diamantino'):
        try:
            result=main(['observations','--location',loc,'--archive','runtime/import-archive'])
            results.append({'location':loc,'product':'observations','state':'ok','result':result})
        except Exception as exc:results.append({'location':loc,'product':'observations','state':'unavailable','error':str(exc)[:180]})
    write_json('runtime/daily_status.json',{'collected_at_utc':now(),'results':results})
    if all(x['state']!='ok' for x in results):raise RuntimeError('Todos os históricos falharam; consultar daily_status.json')
if __name__=='__main__':run()
