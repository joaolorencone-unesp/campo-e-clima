"""Strict paired metrics; missing values must be filtered with recorded counts upstream."""
from __future__ import annotations
import math
from .common import finite

def pairs(forecasts,observations):
    f,o=list(forecasts),list(observations)
    if not f or len(f)!=len(o):raise ValueError('Séries vazias ou comprimentos diferentes')
    if any(not finite(x) for x in f+o):raise ValueError('Métrica requer pares numéricos finitos')
    return f,o

def deterministic(forecasts,observations,*,circular=False):
    f,o=pairs(forecasts,observations)
    errors=[(x-y+180)%360-180 if circular else x-y for x,y in zip(f,o)]
    bias=sum(errors)/len(errors)
    if circular:
        # Circular mean signed error, not an arithmetic average at the branch cut.
        sine=sum(math.sin(math.radians(e)) for e in errors)
        cosine=sum(math.cos(math.radians(e)) for e in errors)
        bias=math.degrees(math.atan2(sine,cosine)) if math.hypot(sine,cosine)>1e-12 else None
    return {'n':len(f),'mae':sum(abs(e) for e in errors)/len(f),
        'rmse':math.sqrt(sum(e*e for e in errors)/len(f)),'bias':bias,'circular':circular,
        'sine_error_sum':sum(math.sin(math.radians(e)) for e in errors) if circular else None,
        'cosine_error_sum':sum(math.cos(math.radians(e)) for e in errors) if circular else None}

def brier_score(probabilities,observations):
    p,y=pairs(probabilities,observations)
    if any(not 0<=x<=1 for x in p) or any(x not in (0,1) for x in y):raise ValueError('Probabilidade ou evento inválido')
    return sum((a-b)**2 for a,b in zip(p,y))/len(p)

def brier_skill_score(probabilities,observations,reference):
    score=brier_score(probabilities,observations)
    base=brier_score(reference,observations)
    return None if base<=0 else 1-score/base

def reliability(probabilities,observations,bins=10):
    brier_score(probabilities,observations)
    result=[]
    for i in range(bins):
        ids=[j for j,p in enumerate(probabilities) if min(int(p*bins),bins-1)==i]
        result.append({'lower':i/bins,'upper':(i+1)/bins,'n':len(ids),
            'forecast_mean':sum(probabilities[j] for j in ids)/len(ids) if ids else None,
            'observed_frequency':sum(observations[j] for j in ids)/len(ids) if ids else None})
    return result

def crps(members,observation,weights=None):
    if not members or not finite(observation) or any(not finite(x) for x in members):raise ValueError('Distribuição incompleta')
    weights=list(weights) if weights is not None else [1/len(members)]*len(members)
    if len(weights)!=len(members) or any(not finite(w) or w<0 for w in weights) or sum(weights)<=0:raise ValueError('Pesos inválidos')
    total=sum(weights)
    ordered=sorted(zip(members,[w/total for w in weights]))
    first=sum(w*abs(x-observation) for x,w in ordered)
    prefix_w=prefix_x=pair=0
    for x,w in ordered:
        pair+=w*(x*prefix_w-prefix_x)
        prefix_w+=w;prefix_x+=w*x
    return max(0,first-pair)

def events(probabilities,observations,cutoff=.5):
    brier_score(probabilities,observations)
    hit=sum(p>=cutoff and y==1 for p,y in zip(probabilities,observations))
    miss=sum(p<cutoff and y==1 for p,y in zip(probabilities,observations))
    false=sum(p>=cutoff and y==0 for p,y in zip(probabilities,observations))
    correct=sum(p<cutoff and y==0 for p,y in zip(probabilities,observations))
    return {'hits':hit,'misses':miss,'false_alarms':false,'correct_negatives':correct,
        'pod':hit/(hit+miss) if hit+miss else None,'far':false/(hit+false) if hit+false else None,
        'csi':hit/(hit+miss+false) if hit+miss+false else None}

def monotone_probabilities(values):
    """PAVA projection onto a decreasing bounded sequence; preserves missingness."""
    if any(not finite(x) for x in values):raise ValueError('Probabilidades incompletas')
    blocks=[]
    for v in values:
        blocks.append([min(1,max(0,v)),1])
        while len(blocks)>1 and blocks[-2][0]<blocks[-1][0]:
            b=blocks.pop();a=blocks.pop();n=a[1]+b[1]
            blocks.append([(a[0]*a[1]+b[0]*b[1])/n,n])
    return [value for value,n in blocks for _ in range(n)]
