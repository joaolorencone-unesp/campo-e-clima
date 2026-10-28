"""Daily rain trace/non-trace thresholds are weighted per model, not per member."""
import math
from scripts.collect import mix_days, rain_models_comparison


def test_trace_categories_equal_weight_models():
    models={'ECMWF':{'days':{'2026-10-27':[0.0,0.1,0.2,1.0,5.0,6.0]}},
            'NOAA':{'days':{'2026-10-27':[0.5,2.0]}}}
    result=mix_days(models)[0]
    # ECMWF: 4/6 > 0.1; 2/6 > 1; 1/6 > 5
    # NOAA: 2/2 > 0.1; 1/2 > 1; 0/2 > 5
    assert math.isclose(result['p_gt_0_1_mm'],.8333,abs_tol=0.0001)
    assert math.isclose(result['p_gt_1_mm'],.4167,abs_tol=0.0001)
    assert math.isclose(result['p_gt_5_mm'],.0833,abs_tol=0.0001)
    assert result['model_count']==2
    assert result['member_count']==8
    m=rain_models_comparison(models)
    assert len(m)==2
    assert m[0]['p_gt_0_1_mm']==round(4/6,4)
    assert m[0]['p_gt_1_mm']==round(2/6,4)
    assert m[1]['p_gt_0_1_mm']==1
    assert m[1]['p_gt_1_mm']==.5


def test_boundary_at_0_1_and_1_and_missing_models():
    models={'only':{'days':{'2026-10-28':[0,0.1,1,5]}}}
    r=mix_days(models)[0]
    assert r['p_gt_0_1_mm']==0.5
    assert r['p_gt_1_mm']==0.25
    assert r['p_gt_5_mm']==0
    assert mix_days({'empty':{'days':{'2026-10-28':[]}}})==[]
