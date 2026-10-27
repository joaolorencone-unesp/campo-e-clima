"""Meteorological-only joint-member screening for agricultural drone spraying.

No result constitutes approval to apply pesticides. Product labels, local wind,
nocturnal inversion, downwind receptors, operator rules and law prevail.
All screening limits in this prototype are configurable and *not* universal
scientific/label limits.
"""
from __future__ import annotations
import datetime as dt
import math
import re
from collections import defaultdict
from typing import Any

# Explicit experimental defaults; not DJI manufacturer limits or pesticide label.
SCREEN = {
    'wind_min_kmh': 3.0,
    'wind_max_kmh': 10.0,
    'gust_max_kmh': 25.0,
    'temperature_max_c': 30.0,
    'rh_min_pct': 55.0,
    'rain_next_3h_max_mm': 0.1,
    'daylight_start_hour': 7,
    'daylight_end_hour_exclusive': 18,
    'vpd_max_kpa': {'herb': 1.2, 'fung': 1.5, 'insect': 1.4},
}
SPECS = ('temperature_2m', 'relative_humidity_2m', 'wind_speed_10m',
         'wind_gusts_10m', 'wind_direction_10m', 'precipitation')
CATEGORIES = ('herb', 'fung', 'insect')


def get_member_dict(payload: dict[str, Any], key: str) -> dict[str, list]:
    """Identify matching member IDs, not mere position in a list."""
    out = {}
    for column, series in (payload.get('hourly') or {}).items():
        match = re.fullmatch(re.escape(key) + r'_member(\d+)', column)
        if match and isinstance(series, list):
            out[match.group(1)] = series
    return out


def finite(value: Any) -> bool:
    return isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value)


def member_vpd(t: float, rh: float) -> float:
    """FAO saturation vapor pressure formula using T (°C) and RH (%)."""
    return 0.6108 * math.exp(17.27 * t / (t + 237.3)) * (1 - rh / 100.0)


def classify_member(values: dict[str, float], kind: str, local_hour: int | None = None) -> tuple[str, set[str]]:
    reasons = set()
    t, rh = values['temperature_2m'], values['relative_humidity_2m']
    wind, gust = values['wind_speed_10m'], values['wind_gusts_10m']
    rain3 = values['rain_next_3h_mm']
    vpd = member_vpd(t, rh)
    if not (0 <= rh <= 100 and wind >= 0 and gust >= 0 and 0 <= values['wind_direction_10m'] <= 360 and rain3 >= 0):
        return 'invalid', {'valor_invalido'}
    if wind < SCREEN['wind_min_kmh'] or wind > SCREEN['wind_max_kmh']: reasons.add('vento')
    if gust > SCREEN['gust_max_kmh']: reasons.add('rajadas')
    if t >= SCREEN['temperature_max_c']: reasons.add('temperatura')
    if rh < SCREEN['rh_min_pct']: reasons.add('umidade')
    if vpd >= SCREEN['vpd_max_kpa'][kind]: reasons.add('vpd')
    if rain3 > SCREEN['rain_next_3h_max_mm']: reasons.add('chuva_3h')
    if reasons: return 'restrito', reasons
    # Night/early morning: grid weather alone cannot rule out inversion or
    # weak turbulence. Do not rank a night hour as suitable to spray.
    if local_hour is not None and not (SCREEN['daylight_start_hour'] <= local_hour < SCREEN['daylight_end_hour_exclusive']):
        return 'indeterminado', {'inversao_nao_verificada'}
    # Potentially borderline even if strict screening thresholds have not been crossed.
    if (wind > 8 or gust > 20 or rh < 60 or t >= 28 or
        vpd > SCREEN['vpd_max_kpa'][kind]*0.85 or rain3 > 0):
        return 'marginal', set()
    return 'passa', set()


def read_joint_members(payload: dict, max_hours: int = 74) -> dict:
    """Return member-correlated weather screening events by timestamp.

    Incomplete future 3h rain window and any missing essential variable exclude
    that member/hour; never treat missing as favorable.
    """
    hourly = payload.get('hourly') or {}
    times = hourly.get('time') or []
    keyed = {name: get_member_dict(payload, name) for name in SPECS}
    member_ids = set.intersection(*(set(v) for v in keyed.values())) if keyed else set()
    if not member_ids:
        return {'members_available': 0, 'times': {}}
    out: dict[str, dict] = {}
    for i, stamp in enumerate(times[:max_hours]):
        # We need current data at i and the three FUTURE rain hours i+1..i+3.
        if i + 4 > len(times):
            continue
        try:
            t = [dt.datetime.fromisoformat(s) for s in times[i:i+4]]
            if any((b-a) != dt.timedelta(hours=1) for a,b in zip(t,t[1:])):
                continue
        except ValueError:
            continue
        event = {}
        for member in sorted(member_ids):
            try:
                values = {name: keyed[name][member][i] for name in SPECS}
                rain = keyed['precipitation'][member][i+1:i+4]
                if len(rain) != 3 or any(not finite(x) for x in rain):
                    continue
                if any(not finite(x) for x in values.values()):
                    continue
                values['rain_next_3h_mm'] = sum(rain)
                statuses = {kind: classify_member(values, kind, dt.datetime.fromisoformat(stamp).hour) for kind in CATEGORIES}
                if any(v[0]=='invalid' for v in statuses.values()):
                    continue
                event[member] = statuses
            except (IndexError, TypeError, ValueError, OverflowError):
                continue
        if event: out[stamp] = event
    return {'members_available': len(member_ids), 'times': out}


def _summarize(candidates: dict[str, dict[str, tuple[str, set[str]]]], kind: str) -> dict | None:
    """Weight models equally, then their valid correlated members equally."""
    valid = {name: members for name, members in candidates.items() if members}
    if not valid: return None
    model_weight = 1/len(valid)
    mass = {'passa': 0., 'marginal': 0., 'restrito': 0., 'indeterminado': 0.}
    reason_mass = defaultdict(float)
    n = 0
    for model, members in valid.items():
        n += len(members)
        w = model_weight/len(members)
        for statuses in members.values():
            cls, reasons = statuses[kind]
            if cls == 'invalid': continue
            mass[cls] += w
            for reason in reasons:
                reason_mass[reason] += w
    return {'models': len(valid), 'members': n,
            'passa': round(mass['passa'],4), 'marginal': round(mass['marginal'],4),
            'restrito': round(mass['restrito'],4),
            'indeterminado': round(mass['indeterminado'],4),
            'reasons': {key:round(v,4) for key,v in sorted(reason_mass.items())}}


def mix_joint_hourly(by_model: dict[str, dict]) -> list[dict]:
    times = sorted({stamp for item in by_model.values() for stamp in item.get('times', {})})
    output=[]
    for stamp in times:
        candidates={name:item['times'][stamp] for name,item in by_model.items() if item.get('times',{}).get(stamp)}
        row={'time':stamp}
        for kind in CATEGORIES: row[kind]=_summarize(candidates,kind)
        if any(row[kind] for kind in CATEGORIES): output.append(row)
    return output


def mix_joint_windows2h(by_model: dict[str, dict]) -> list[dict]:
    """A two-hour window passes only if THE SAME member passes both hours."""
    times = sorted({stamp for item in by_model.values() for stamp in item.get('times', {})})
    out=[]
    for start in times:
        try: end = (dt.datetime.fromisoformat(start)+dt.timedelta(hours=1)).isoformat(timespec='minutes')
        except ValueError: continue
        candidates={}
        for name,item in by_model.items():
            a=item.get('times',{}).get(start,{})
            b=item.get('times',{}).get(end,{})
            if not a or not b: continue
            common=set(a).intersection(b)
            if not common: continue
            candidates[name]={}
            for member in common:
                combined={}
                for kind in CATEGORIES:
                    ca,ra=a[member][kind];cb,rb=b[member][kind]
                    if 'invalid' in (ca,cb):c='invalid'
                    elif 'restrito' in (ca,cb):c='restrito'
                    elif 'indeterminado' in (ca,cb):c='indeterminado'
                    elif 'marginal' in (ca,cb):c='marginal'
                    else:c='passa'
                    combined[kind]=(c,ra|rb)
                candidates[name][member]=combined
        if candidates:
            row={'start':start,'end':end}
            for kind in CATEGORIES:row[kind]=_summarize(candidates,kind)
            out.append(row)
    return out
