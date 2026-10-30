from __future__ import annotations
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
UTC = dt.timezone.utc

def config():
    return json.loads((ROOT / 'config/free_resources.json').read_text(encoding='utf-8'))

def location(ident):
    return next(x for x in config()['locations'] if x['id'] == ident)

def now():
    return dt.datetime.now(UTC).isoformat(timespec='seconds')

def instant(value, timezone=None):
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        d = dt.datetime.fromtimestamp(value, UTC)
    else:
        d = dt.datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    if d.tzinfo is None:
        if timezone is None:
            raise ValueError('Timestamp sem fuso explícito')
        d = d.replace(tzinfo=ZoneInfo(timezone))
    return d.astimezone(UTC)

def iso(value, timezone=None):
    return instant(value, timezone).isoformat(timespec='seconds')

def digest(content):
    return hashlib.sha256(content).hexdigest()

def packed(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')

def write_json(path, obj):
    atomic(path, packed(obj))

def atomic(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + f'.{os.getpid()}.tmp')
    temp.write_bytes(content)
    os.replace(temp, path)

def finite(v):
    return isinstance(v, (float, int)) and not isinstance(v, bool) and math.isfinite(v)

def haversine(a, b):
    lat1, lon1, lat2, lon2 = map(math.radians, [a['latitude'],a['longitude'],b['latitude'],b['longitude']])
    x = math.sin((lat2-lat1)/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin((lon2-lon1)/2)**2
    return 6371.0088 * 2 * math.asin(min(1, math.sqrt(x)))

def safe_parameters(params):
    forbidden = ('key', 'token', 'secret', 'password', 'authorization', 'credential')
    if any(any(s in k.lower() for s in forbidden) for k in params):
        raise ValueError('Credencial não permitida no arquivo científico')
    return params
