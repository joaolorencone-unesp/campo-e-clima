"""Derived precipitation products built only from valid member trajectories.

Everything here is a deterministic transformation of the member values already
acquired. No value is imputed: a member that lacks any hour of a window, day or
multi-day span is excluded from that product and the counts say so.

Scientific notes
- Open-Meteo returns hourly series for every ensemble, but several models have a
  native precipitation step of 3 h or 6 h; the API splits those accumulations into
  equal hourly parts (sum preserving). Such series cannot describe 1 h intensity
  or occurrence. ``native_step_hours`` detects the repetition pattern so that
  hourly windows only use models whose native step is not longer than the window.
- Multi-day totals and dry spells are computed per member across consecutive
  complete local days, so the dependence between days inside one trajectory is kept.
- Agreement statistics compare models, not members: they say how many models have
  a member majority on the wet side, not a calibrated probability.
"""
from __future__ import annotations
import datetime as dt
import math
from collections import Counter
from typing import Any

STEP_CHOICES = (1, 3, 6)
ACCUMULATION_THRESHOLDS_MM = (10, 25, 50, 100)
DRY_DAY_MM = 1.0


def finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def native_step_hours(payload: dict, base: str = 'precipitation') -> int | None:
    """Estimate the native accumulation step of an hourly precipitation series.

    Looks only at runs of identical, strictly positive consecutive values across
    all members (zeros carry no information about the step). Returns 1, 3 or 6,
    or ``None`` when the series is not hourly or holds too little rain to decide.
    """
    hourly = payload.get('hourly') or {}
    times = hourly.get('time') or []
    if len(times) < 6:
        return None
    try:
        stamps = [dt.datetime.fromisoformat(t) for t in times[:25]]
    except (TypeError, ValueError):
        return None
    if any(b - a != dt.timedelta(hours=1) for a, b in zip(stamps, stamps[1:])):
        return None
    runs: Counter[int] = Counter()
    for key, series in hourly.items():
        if not key.startswith(base + '_member') or not isinstance(series, list):
            continue
        previous = None
        length = 0
        for value in series + [None]:
            if finite(value) and value > 0 and value == previous:
                length += 1
                continue
            if previous is not None and length:
                runs[length] += 1
            previous = value if finite(value) and value > 0 else None
            length = 1 if previous is not None else 0
    if sum(runs.values()) < 3:
        return None
    # Runs of exactly 6 (or multiples) betray a 6 h accumulation split into hours;
    # runs of exactly 3 (or odd multiples) a 3 h one; anything else is hourly detail.
    six = sum(count for length, count in runs.items() if length % 6 == 0)
    three = sum(count for length, count in runs.items() if length % 3 == 0 and length % 6 != 0)
    other = sum(count for length, count in runs.items() if length % 3 != 0)
    if six >= max(3, 2 * three) and six >= other:
        return 6
    if three + six >= max(3, other):
        return 3
    return 1


def member_day_totals(payload: dict, base: str = 'precipitation', max_days: int = 7) -> dict[str, dict[str, float]]:
    """{member_id: {local_day: total_mm}} for complete local days (01h .. 00h next day)."""
    hourly = payload.get('hourly') or {}
    times = hourly.get('time') or []
    by_date: dict[str, list[int]] = {}
    first_day = times[0][:10] if times else ''
    for index, stamp in enumerate(times):
        try:
            end = dt.datetime.fromisoformat(stamp)
        except (TypeError, ValueError):
            continue
        day = (end - dt.timedelta(hours=1)).date().isoformat()
        if day >= first_day:
            by_date.setdefault(day, []).append(index)
    complete_days = []
    for day, ids in list(by_date.items())[:max_days]:
        if len(ids) != 24:
            continue
        ends = [dt.datetime.fromisoformat(times[i]) for i in ids]
        if ends[0].hour != 1 or ends[-1].hour != 0 or any(b - a != dt.timedelta(hours=1) for a, b in zip(ends, ends[1:])):
            continue
        complete_days.append((day, ids))
    out: dict[str, dict[str, float]] = {}
    for key, series in hourly.items():
        if not key.startswith(base + '_member') or not isinstance(series, list) or len(series) != len(times):
            continue
        member = key[len(base) + len('_member'):]
        totals = {}
        for day, ids in complete_days:
            values = [series[i] for i in ids]
            if any(not finite(v) or v < 0 for v in values):
                continue
            totals[day] = float(sum(values))
        if totals:
            out[member] = totals
    return out


def weighted_quantile(pairs: list[tuple[float, float]], q: float) -> float | None:
    if not pairs:
        return None
    ordered = sorted(pairs)
    total = sum(w for _, w in ordered)
    if total <= 0:
        return None
    acc = 0.0
    for value, weight in ordered:
        acc += weight
        if acc / total >= q - 1e-12:
            return value
    return ordered[-1][0]


def _summary(pairs: list[tuple[float, float]], thresholds, key_unit='mm') -> dict:
    out = {'mean_' + key_unit: round(sum(v * w for v, w in pairs), 3),
           'p10_' + key_unit: round(weighted_quantile(pairs, .1), 3),
           'p50_' + key_unit: round(weighted_quantile(pairs, .5), 3),
           'p90_' + key_unit: round(weighted_quantile(pairs, .9), 3)}
    for threshold in thresholds:
        out[f'p_gt_{str(threshold).replace(".", "_")}_{key_unit}'] = round(sum(w for v, w in pairs if v > threshold), 4)
    return out


def mix_accumulations(member_days_by_model: dict[str, dict[str, dict[str, float]]], spans=(3, 5, 7)) -> list[dict]:
    """Multi-day totals per member starting at the first common forecast day.

    Equal total weight per model, then equal weight per complete member trajectory.
    A span is published only when at least one model has members complete over
    every day of the span.
    """
    days = sorted({day for model in member_days_by_model.values() for member in model.values() for day in member})
    if not days:
        return []
    start = days[0]
    output = []
    for span in spans:
        window = [(dt.date.fromisoformat(start) + dt.timedelta(days=k)).isoformat() for k in range(span)]
        valid = {}
        for name, members in member_days_by_model.items():
            totals = [sum(m[d] for d in window) for m in members.values() if all(d in m for d in window)]
            if totals:
                valid[name] = totals
        if not valid:
            continue
        weight = 1 / len(valid)
        pairs = [(v, weight / len(values)) for values in valid.values() for v in values]
        row = {'span_days': span, 'start': window[0], 'end': window[-1], 'model_count': len(valid),
               'member_count': len(pairs), **_summary(pairs, ACCUMULATION_THRESHOLDS_MM)}
        output.append(row)
    return output


def mix_dry_spells(member_days_by_model: dict[str, dict[str, dict[str, float]]], dry_mm: float = DRY_DAY_MM) -> dict | None:
    """Longest run of consecutive days below ``dry_mm`` inside each complete 7-day member trajectory."""
    days = sorted({day for model in member_days_by_model.values() for member in model.values() for day in member})
    if not days:
        return None
    window = days[:7]
    valid = {}
    for name, members in member_days_by_model.items():
        spells = []
        for member in members.values():
            if not all(d in member for d in window):
                continue
            longest = current = 0
            for day in window:
                current = current + 1 if member[day] < dry_mm else 0
                longest = max(longest, current)
            spells.append(longest)
        if spells:
            valid[name] = spells
    if not valid:
        return None
    weight = 1 / len(valid)
    pairs = [(float(v), weight / len(values)) for values in valid.values() for v in values]
    return {'window_days': len(window), 'start': window[0], 'end': window[-1], 'dry_day_threshold_mm': dry_mm,
            'model_count': len(valid), 'member_count': len(pairs),
            'p50_days': weighted_quantile(pairs, .5), 'p90_days': weighted_quantile(pairs, .9),
            'p_ge_3_days': round(sum(w for v, w in pairs if v >= 3), 4),
            'p_ge_5_days': round(sum(w for v, w in pairs if v >= 5), 4)}


def model_agreement_daily(by_model: dict[str, dict], wet_mm: float = 1.0) -> list[dict]:
    """Per day: how many models have a member majority above ``wet_mm`` and how far their means are apart."""
    dates = sorted({day for item in by_model.values() for day in item.get('days', {})})
    output = []
    for day in dates:
        votes = {}
        means = {}
        for name, item in by_model.items():
            members = item.get('days', {}).get(day)
            if not members:
                continue
            votes[name] = sum(1 for x in members if x > wet_mm) / len(members)
            means[name] = sum(members) / len(members)
        if not votes:
            continue
        wet = sum(1 for v in votes.values() if v >= .5)
        dry = len(votes) - wet
        agreement = max(wet, dry) / len(votes)
        ordered = sorted(means.values())
        median = ordered[len(ordered) // 2] if len(ordered) % 2 else (ordered[len(ordered) // 2 - 1] + ordered[len(ordered) // 2]) / 2
        label = 'alta' if agreement >= .75 and len(votes) >= 3 else 'media' if agreement >= .5 else 'baixa'
        output.append({'date': day, 'models': len(votes), 'wet_majority_models': wet, 'dry_majority_models': dry,
                       'agreement_fraction': round(agreement, 3), 'agreement_label': label,
                       'side': 'chuva' if wet > dry else 'seco' if dry > wet else 'dividido',
                       'model_mean_min_mm': round(ordered[0], 2), 'model_mean_max_mm': round(ordered[-1], 2),
                       'model_mean_median_mm': round(median, 2),
                       'volume_spread_label': 'alta' if ordered[-1] - ordered[0] > max(10, 2 * median) else 'media' if ordered[-1] - ordered[0] > 5 else 'baixa',
                       'wet_threshold_mm': wet_mm})
    return output


def compare_runs(current_daily: list[dict], previous_daily: list[dict], *, previous_issued_at_utc: str | None,
                 min_delta_mm: float = 5.0, min_delta_probability: float = 0.25) -> dict:
    """Difference between this publication and the previous one, day by day.

    A new collection is not a new model run: callers must also publish the
    acquisition times so the reader can tell a refreshed cycle from a cache hit.
    """
    before = {row['date']: row for row in previous_daily or [] if isinstance(row, dict) and 'date' in row}
    days = []
    for row in current_daily or []:
        old = before.get(row.get('date'))
        if not old:
            continue
        delta_p50 = (row.get('p50_mm') or 0) - (old.get('p50_mm') or 0) if finite(row.get('p50_mm')) and finite(old.get('p50_mm')) else None
        delta_p1 = (row.get('p_gt_1_mm') - old.get('p_gt_1_mm')) if finite(row.get('p_gt_1_mm')) and finite(old.get('p_gt_1_mm')) else None
        days.append({'date': row['date'], 'p50_now_mm': row.get('p50_mm'), 'p50_before_mm': old.get('p50_mm'),
                     'delta_p50_mm': round(delta_p50, 2) if delta_p50 is not None else None,
                     'p_gt_1_now': row.get('p_gt_1_mm'), 'p_gt_1_before': old.get('p_gt_1_mm'),
                     'delta_p_gt_1': round(delta_p1, 3) if delta_p1 is not None else None,
                     'models_now': row.get('model_count'), 'models_before': old.get('model_count'),
                     'significant': bool((delta_p50 is not None and abs(delta_p50) >= min_delta_mm) or
                                         (delta_p1 is not None and abs(delta_p1) >= min_delta_probability))})
    return {'state': 'ok' if days else 'no_previous_publication', 'previous_issued_at_utc': previous_issued_at_utc,
            'days': days, 'significant_days': sum(1 for d in days if d['significant']),
            'thresholds': {'p50_mm': min_delta_mm, 'p_gt_1': min_delta_probability},
            'note': 'Diferença entre publicações consecutivas deste painel; só indica rodada meteorológica nova quando os horários de aquisição dos modelos mudaram.'}
