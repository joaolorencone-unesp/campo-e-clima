"""Member-aligned agro-meteorological ensemble diagnostics (uncalibrated).

Reuses the existing weather-member payload; does not issue new HTTP requests.
Each weather variable is validated independently. VPD pairs T/RH by SAME member.
"""
from __future__ import annotations
import math
from collections import defaultdict
from scripts.spraying import get_member_dict, member_vpd

FIELDS = ('temperature_2m', 'relative_humidity_2m', 'wind_speed_10m', 'wind_gusts_10m', 'vpd_kpa')
BOUNDS = {'temperature_2m':(-70,65), 'relative_humidity_2m':(0,100),
          'wind_speed_10m':(0,250), 'wind_gusts_10m':(0,300), 'vpd_kpa':(0,15)}

def valid(field, value):
    lo, hi = BOUNDS[field]
    return (isinstance(value,(int,float)) and not isinstance(value,bool)
            and math.isfinite(value) and lo <= value <= hi)

def model_samples(payload, *, future_start=None, max_hours=72):
    """Return {local timestamp: {field: [valid member values]}}."""
    h=payload.get('hourly') or {}
    times=h.get('time') or []
    raw={key:get_member_dict(payload,key) for key in FIELDS if key!='vpd_kpa'}
    out={}
    for i,stamp in enumerate(times):
        if future_start and stamp < future_start:continue
        if len(out)>=max_hours:break
        values={}
        for key in FIELDS:
            if key=='vpd_kpa':
                ids=set(raw['temperature_2m']) & set(raw['relative_humidity_2m'])
                series=[]
                for member in ids:
                    t=raw['temperature_2m'][member];rh=raw['relative_humidity_2m'][member]
                    if i>=len(t) or i>=len(rh):continue
                    if valid('temperature_2m',t[i]) and valid('relative_humidity_2m',rh[i]):
                        v=member_vpd(t[i],rh[i])
                        if valid(key,v):series.append(v)
            else:
                series=[s[i] for s in raw[key].values() if i<len(s) and valid(key,s[i])]
            if series:values[key]=series
        if values:out[stamp]=values
    return out

def _quantile(pairs, quantile):
    ordered=sorted(pairs,key=lambda p:p[0]);weight=sum(w for _,w in ordered)
    total=0
    for value,w in ordered:
        total+=w
        if total>=weight*quantile-1e-12:return round(value,3)
    return round(ordered[-1][0],3)

def blend_samples(by_model, max_hours=72):
    """Each available MODEL gets equal weight; no pooled-member bias."""
    stamps=sorted({t for rows in by_model.values() for t in rows})[:max_hours]
    output=[]
    for stamp in stamps:
        variables={}
        for key in FIELDS:
            groups=[model[stamp][key] for model in by_model.values()
                    if stamp in model and model[stamp].get(key)]
            if not groups:continue
            pairs=[(v,1/len(groups)/len(values)) for values in groups for v in values]
            total=sum(v*w for v,w in pairs)
            row={'model_count':len(groups),'member_count':len(pairs),
                 'p10':_quantile(pairs,.1),'p50':_quantile(pairs,.5),
                 'p90':_quantile(pairs,.9),'mean':round(total,3)}
            if key=='temperature_2m':row['p_ge_30']=round(sum(w for v,w in pairs if v>=30),4)
            if key=='relative_humidity_2m':row['p_lt_55']=round(sum(w for v,w in pairs if v<55),4)
            if key=='vpd_kpa':row['p_ge_1_5']=round(sum(w for v,w in pairs if v>=1.5),4)
            if key=='wind_speed_10m':row['p_gt_10']=round(sum(w for v,w in pairs if v>10),4)
            if key=='wind_gusts_10m':row['p_gt_30']=round(sum(w for v,w in pairs if v>30),4)
            variables[key]=row
        if variables:output.append({'time':stamp,'variables':variables})
    return output
