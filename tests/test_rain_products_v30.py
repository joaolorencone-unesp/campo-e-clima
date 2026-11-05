"""v3.0 derived rain products: native step, multi-day totals, dry spells, agreement, run change."""
import datetime as dt
import pytest
from scripts.rain_products import (native_step_hours, member_day_totals, mix_accumulations, mix_dry_spells,
                                   model_agreement_daily, compare_runs)
from scripts.collect import model_hourly_rain, mix_hourly_rain, model_daily_rain


def hours(n=168, start='2026-11-04T00:00'):
    base = dt.datetime.fromisoformat(start)
    return [(base + dt.timedelta(hours=i)).strftime('%Y-%m-%dT%H:%M') for i in range(n)]


def disaggregated(step, totals, n=168):
    """Provider style: each native accumulation split into ``step`` equal hourly values."""
    series = []
    for block in range(n // step):
        series += [totals[block % len(totals)] / step] * step
    return series[:n]


def test_native_step_detects_hourly_three_and_six_hour_models():
    t = hours()
    six = {'hourly': {'time': t, 'precipitation_member01': disaggregated(6, [0, 12, 0, 3, 0, 0, 6]),
                      'precipitation_member02': disaggregated(6, [6, 0, 0, 0, 1.2, 0, 0])}}
    three = {'hourly': {'time': t, 'precipitation_member01': disaggregated(3, [0, 0, 3, 0, 1.5, 0, 0, 9])}}
    one = {'hourly': {'time': t, 'precipitation_member01': [0, 0, 1, 2.5, 0.3, 0, 0, 4, 1, 0] * 17}}
    assert native_step_hours(six) == 6
    assert native_step_hours(three) == 3
    assert native_step_hours(one) == 1


def test_native_step_unknown_when_no_rain_or_non_hourly_grid():
    t = hours()
    assert native_step_hours({'hourly': {'time': t, 'precipitation_member01': [0] * 168}}) is None
    assert native_step_hours({'hourly': {'time': ['2026-11-04T00:00', '2026-11-04T03:00', '2026-11-04T06:00'] * 3,
                                         'precipitation_member01': [1, 1, 1] * 3}}) is None


def test_hourly_windows_exclude_models_coarser_than_the_window():
    t = hours(24)
    coarse = {'hourly': {'time': t, 'precipitation_member01': [2.0] * 24}}   # pretend 6 h native
    fine = {'hourly': {'time': t, 'precipitation_member01': [0.0] * 24}}
    models = {'six': model_hourly_rain(coarse), 'one': model_hourly_rain(fine)}
    mixed = mix_hourly_rain(models, native_steps={'six': 6, 'one': 1})
    first = mixed[0]['windows']
    assert first['1']['models'] == 1 and first['1']['models_excluded_by_resolution'] == 1
    assert first['3']['models'] == 1
    assert first['6']['models'] == 2 and first['6']['models_excluded_by_resolution'] == 0
    assert first['1']['p_gt_1_mm'] == 0.0  # the 6 h model's flat 2 mm/h never counts as hourly rain
    # Unknown step (no rain) stays eligible and the legacy call keeps all models.
    assert mix_hourly_rain(models)[0]['windows']['1']['models'] == 2


def test_member_day_totals_keep_identity_and_skip_incomplete_days():
    t = [f'2026-11-04T{h:02d}:00' for h in range(1, 24)] + ['2026-11-05T00:00'] + [f'2026-11-05T{h:02d}:00' for h in range(1, 24)] + ['2026-11-06T00:00']
    good = [1.0] * 48
    broken = [1.0] * 48
    broken[30] = None
    totals = member_day_totals({'hourly': {'time': t, 'precipitation_member07': good, 'precipitation_member12': broken}})
    assert totals['07'] == {'2026-11-04': 24.0, '2026-11-05': 24.0}
    assert totals['12'] == {'2026-11-04': 24.0}
    acc = mix_accumulations({'m': totals}, spans=(2,))
    assert acc[0]['member_count'] == 1 and acc[0]['p50_mm'] == 48.0 and acc[0]['p_gt_25_mm'] == 1.0
    assert mix_accumulations({'m': totals}, spans=(3,)) == []


def test_multi_day_totals_use_equal_model_weight_and_per_member_sums():
    days = ['2026-11-04', '2026-11-05', '2026-11-06']
    a = {'01': dict(zip(days, [10, 10, 10])), '02': dict(zip(days, [0, 0, 0]))}
    b = {'01': dict(zip(days, [40, 40, 40]))}
    acc = mix_accumulations({'a': a, 'b': b}, spans=(3,))[0]
    assert acc['model_count'] == 2 and acc['member_count'] == 3
    assert acc['mean_mm'] == pytest.approx((30 + 0) / 2 * .5 + 120 * .5)
    assert acc['p_gt_100_mm'] == pytest.approx(.5)


def test_dry_spell_is_longest_run_of_days_below_one_mm_per_member():
    days = [f'2026-11-{d:02d}' for d in range(4, 11)]
    wet_then_dry = dict(zip(days, [5, 0, 0, 0, 0, 3, 0]))
    always_wet = dict(zip(days, [5] * 7))
    out = mix_dry_spells({'m': {'a': wet_then_dry, 'b': always_wet}})
    assert out['member_count'] == 2 and out['p_ge_3_days'] == 0.5 and out['p90_days'] == 4.0


def test_model_agreement_counts_models_not_members():
    by_model = {'a': {'days': {'2026-11-05': [0, 0, 0, 5]}}, 'b': {'days': {'2026-11-05': [20, 30]}},
                'c': {'days': {'2026-11-05': [0.2, 0.0]}}, 'd': {'days': {'2026-11-05': [0, 0]}}}
    row = model_agreement_daily(by_model)[0]
    assert row['models'] == 4 and row['wet_majority_models'] == 1 and row['dry_majority_models'] == 3
    assert row['agreement_fraction'] == 0.75 and row['agreement_label'] == 'alta' and row['side'] == 'seco'
    assert row['model_mean_max_mm'] == 25.0


def test_compare_runs_flags_significant_changes_only():
    now = [{'date': '2026-11-06', 'p50_mm': 12.0, 'p_gt_1_mm': 0.9, 'model_count': 8},
           {'date': '2026-11-07', 'p50_mm': 0.4, 'p_gt_1_mm': 0.2, 'model_count': 8}]
    before = [{'date': '2026-11-06', 'p50_mm': 2.0, 'p_gt_1_mm': 0.5, 'model_count': 8},
              {'date': '2026-11-07', 'p50_mm': 0.1, 'p_gt_1_mm': 0.15, 'model_count': 7}]
    out = compare_runs(now, before, previous_issued_at_utc='2026-11-05T00:00:00+00:00')
    assert out['state'] == 'ok' and out['significant_days'] == 1
    assert out['days'][0]['delta_p50_mm'] == 10.0 and out['days'][0]['significant'] is True
    assert out['days'][1]['significant'] is False
    assert compare_runs(now, [], previous_issued_at_utc=None)['state'] == 'no_previous_publication'


def test_daily_rain_and_member_totals_agree():
    t = hours(48)
    payload = {'hourly': {'time': t, 'precipitation_member01': [0.5] * 48}}
    assert model_daily_rain(payload)['days']['2026-11-04'] == [12.0]
    assert member_day_totals(payload)['01']['2026-11-04'] == 12.0
