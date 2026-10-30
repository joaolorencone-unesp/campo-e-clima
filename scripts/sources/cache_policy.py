"""Successful slow products last one day; transient failures retry at most every six hours."""
import datetime as dt

def refresh_daily(previous,loaders,*,now=None):
    now=now or dt.datetime.now(dt.timezone.utc)
    sources=previous.get('sources',{}) if isinstance(previous,dict) else {}
    result={}
    for name,loader in loaders.items():
        old=sources.get(name,{})
        if old.get('state')=='ok':
            result[name]=old;continue
        stamp=old.get('last_attempted_at_utc') or old.get('queried_at_utc')
        try:age=(now-dt.datetime.fromisoformat(stamp.replace('Z','+00:00'))).total_seconds()
        except (AttributeError,TypeError,ValueError):age=None
        if age is not None and 0<=age<6*3600:
            result[name]=old;continue
        value=loader()
        result[name]={**value,'last_attempted_at_utc':now.isoformat()}
    return result
