"""Free, allowlisted HTTP with bounded retries, quotas and on-disk response cache."""
from __future__ import annotations
import datetime as dt
import json
import math
import time
from pathlib import Path
from urllib.parse import urlsplit
import requests
from .capture import ALLOWED_HOSTS
from .common import atomic, config, digest, instant, now, packed, safe_parameters, write_json

class FreeClient:
    def __init__(self, root, capture=None, session=None):
        self.root=Path(root); self.root.mkdir(parents=True,exist_ok=True)
        self.capture=capture
        self.session=session or requests.Session()
        self.limits=config()

    def get(self,url,params,*,ttl_hours=6,product='operational',initialization=None):
        parsed=urlsplit(url)
        if parsed.scheme!='https' or parsed.hostname not in ALLOWED_HOSTS or parsed.query or parsed.username:
            raise ValueError('Endpoint gratuito não aprovado')
        safe_parameters(params)
        key=digest(packed([url,params])); cache=self.root/f'{key}.json'
        if cache.exists():
            old=json.loads(cache.read_text(encoding='utf-8'))
            body=self.root/f'{key}.body'
            if body.exists() and digest(body.read_bytes())==old['sha256'] and (instant(now())-instant(old['collected_at_utc'])).total_seconds()<ttl_hours*3600:
                payload=json.loads(body.read_bytes())
                if self.capture:
                    event=self.capture.record(url,params,content=body.read_bytes(),status=200,product=product,initialization=initialization)
                    event.update(collected_at_utc=old['collected_at_utc'],cache_hit=True)
                    self.capture.flush()
                return payload
        variables=len(str(params.get('hourly','')).split(','))
        members=51 if 'ensemble-api.' in parsed.hostname else 1
        # Conservative project estimate, not the provider's billing/account counter.
        equivalent=max(1,math.ceil(variables*members/10))*max(1,math.ceil(float(params.get('forecast_days',7))/14))
        ledger=self.root/'usage.json'
        usage=json.loads(ledger.read_text(encoding='utf-8')) if ledger.exists() else {}
        day=now()[:10]
        if usage.get('day')!=day:usage={'day':day,'equivalent_calls':0,'http_requests':0}
        for attempt in range(self.limits['http_max_attempts']):
            if usage['equivalent_calls']+equivalent>self.limits['weather_max_equivalent_calls_per_day']:
                raise ValueError('Cota conservadora gratuita atingida')
            usage['equivalent_calls']+=equivalent;usage['http_requests']+=1
            write_json(ledger,usage)
            try:
                response=self.session.get(url,params=params,timeout=self.limits['http_timeout_seconds'],
                    headers={'User-Agent':'Campo-e-Clima/2.2 open-research'},allow_redirects=False)
            except requests.RequestException as exc:
                if self.capture:self.capture.record(url,params,error=type(exc).__name__,product=product)
                if attempt+1==self.limits['http_max_attempts']:raise
                time.sleep(2**attempt);continue
            if self.capture:self.capture.record(url,params,content=response.content,status=response.status_code,
                product=product,initialization=initialization,headers=dict(response.headers))
            if response.status_code==429:
                # No repeated attempts after a quota response.
                response.raise_for_status()
            if 500<=response.status_code<600 and attempt+1<self.limits['http_max_attempts']:
                retry=response.headers.get('Retry-After','2')
                try:delay=float(retry)
                except ValueError:delay=60
                if delay>10:response.raise_for_status()
                time.sleep(max(1,delay));continue
            if 300<=response.status_code<400:raise ValueError('Redirecionamento não permitido')
            response.raise_for_status()
            payload=response.json()
            if not isinstance(payload,(dict,list)) or isinstance(payload,dict) and payload.get('error'):
                raise ValueError('Produto inválido')
            atomic(self.root/f'{key}.body',response.content)
            write_json(cache,{'collected_at_utc':now(),'sha256':digest(response.content)})
            time.sleep(1)
            return payload
        raise RuntimeError('Tentativas esgotadas')
