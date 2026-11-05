"""Member-aligned agrometeorological ensemble diagnostics (uncalibrated).

Reuses the joint 80-hour member payload already requested for spraying; it issues
no HTTP request of its own. Each variable is validated independently, so a model
that lacks gusts still contributes temperature. VPD is derived only from the
temperature and relative humidity of the SAME member and hour (FAO-56 Tetens).

Thresholds published here are exploratory references, not operational limits.
"""
from __future__ import annotations
import math
from scripts.spraying import get_member_dict, member_vpd

FIELDS = ('temperature_2m', 'relative_humidity_2m', 'wind_speed_10m', 'wind_gusts_10m', 'vpd_kpa')
BOUNDS = {'temperature_2m': (-70, 65), 'relative_humidity_2m': (0, 100),
          'wind_speed_10m': (0, 250), 'wind_gusts_10m': (0, 300), 'vpd_kpa': (0, 15)}
# Exceedance frequencies published per variable (uncalibrated member frequencies).
THRESHOLDS = {
    'temperature_2m': (('p_ge_30', lambda v: v >= 30), ('p_ge_35', lambda v: v >= 35), ('p_le_5', lambda v: v <= 5), ('p_le_3', lambda v: v <= 3), ('p_le_1', lambda v: v <= 1)),
    'relative_humidity_2m': (('p_lt_55', lambda v: v < 55), ('p_lt_40', lambda v: v < 40), ('p_ge_90', lambda v: v >= 90)),
    'vpd_kpa': (('p_ge_1_5', lambda v: v >= 1.5), ('p_ge_2_5', lambda v: v >= 2.5), ('p_lt_0_5', lambda v: v < .5)),
    'wind_speed_10m': (('p_gt_10', lambda v: v > 10), ('p_gt_15', lambda v: v > 15), ('p_lt_3', lambda v: v < 3)),
    'wind_gusts_10m': (('p_gt_25', lambda v: v > 25), ('p_gt_30', lambda v: v > 30), ('p_gt_40', lambda v: v > 40)),
}


def valid(field, value):
    low, high = BOUNDS[field]
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value) and low <= value <= high)


def model_samples(payload, *, future_start=None, max_hours=72):
    """Return {local timestamp: {field: [valid member values]}} for one model."""
    hourly = payload.get('hourly') or {}
    times = hourly.get('time') or []
    raw = {key: get_member_dict(payload, key) for key in FIELDS if key != 'vpd_kpa'}
    out = {}
    for index, stamp in enumerate(times):
        if future_start and stamp < future_start:
            continue
        if len(out) >= max_hours:
            break
        values = {}
        for key in FIELDS:
            if key == 'vpd_kpa':
                ids = set(raw['temperature_2m']) & set(raw['relative_humidity_2m'])
                series = []
                for member in ids:
                    t = raw['temperature_2m'][member]
                    rh = raw['relative_humidity_2m'][member]
                    if index >= len(t) or index >= len(rh):
                        continue
                    if valid('temperature_2m', t[index]) and valid('relative_humidity_2m', rh[index]):
                        v = member_vpd(t[index], rh[index])
                        if valid(key, v):
                            series.append(v)
            else:
                series = [s[index] for s in raw[key].values() if index < len(s) and valid(key, s[index])]
            if series:
                values[key] = series
        if values:
            out[stamp] = values
    return out


def _quantile(pairs, quantile):
    ordered = sorted(pairs, key=lambda p: p[0])
    weight = sum(w for _, w in ordered)
    total = 0
    for value, w in ordered:
        total += w
        if total >= weight * quantile - 1e-12:
            return round(value, 3)
    return round(ordered[-1][0], 3)


def blend_samples(by_model, max_hours=72):
    """Each available MODEL gets equal weight per variable and hour; members share it equally."""
    stamps = sorted({t for rows in by_model.values() for t in rows})[:max_hours]
    output = []
    for stamp in stamps:
        variables = {}
        for key in FIELDS:
            groups = [(name, model[stamp][key]) for name, model in by_model.items()
                      if stamp in model and model[stamp].get(key)]
            if not groups:
                continue
            pairs = [(v, 1 / len(groups) / len(values)) for _, values in groups for v in values]
            row = {'model_count': len(groups), 'member_count': len(pairs),
                   'models': sorted(name for name, _ in groups),
                   'p10': _quantile(pairs, .1), 'p50': _quantile(pairs, .5), 'p90': _quantile(pairs, .9),
                   'mean': round(sum(v * w for v, w in pairs), 3)}
            for label, test in THRESHOLDS.get(key, ()):
                row[label] = round(sum(w for v, w in pairs if test(v)), 4)
            variables[key] = row
        if variables:
            output.append({'time': stamp, 'variables': variables})
    return output


def variable_coverage(by_model):
    """Which models provided each variable at least once (transparency for the UI)."""
    coverage = {key: sorted({name for name, rows in by_model.items() if any(key in r for r in rows.values())}) for key in FIELDS}
    return {key: {'models': models, 'model_count': len(models)} for key, models in coverage.items()}


__all__ = ['FIELDS', 'THRESHOLDS', 'model_samples', 'blend_samples', 'variable_coverage']
