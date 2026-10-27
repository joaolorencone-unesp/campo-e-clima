"""Static safety checks for historical coordinates/history comparison UI."""
from pathlib import Path

BASE=Path(__file__).resolve().parents[1]


def test_historical_ui_has_per_day_comparison_and_screening():
    page=(BASE/'site/index.html').read_text(encoding='utf-8')
    for key in ('id="hist-period"','id="hist-daily-plot"','id="hist-compare-plot"',
                'id="hist-spray-plot"','id="hist-table"','id="hist-station-table"',
                'id="hist-export"','static/history_v10.js?v=12'):
        assert key in page
    assert 'id="archive-rain-plot"' not in page, 'Old empty ERA5 historical chart must not remain'


def test_nasa_and_era5_utc_day_alignment():
    js=(BASE/'site/static/location.js').read_text(encoding='utf-8')
    hist=(BASE/'site/static/history_v10.js').read_text(encoding='utf-8')
    assert "'time-standard':'UTC'" in js
    assert "timezone:'UTC'" in hist
    assert "if(!hourly || opts.force)" in hist
    assert 'NÃO' in hist or 'não' in hist


def test_station_catalog_is_public_metadata_only():
    collector=(BASE/'scripts/export_inmet_catalog.py').read_text(encoding='utf-8')
    workflow=(BASE/'.github/workflows/pages.yml').read_text(encoding='utf-8')
    assert 'apitempo.inmet.gov.br/estacoes/T' in collector
    assert 'weather' not in collector.lower() or 'NOT measurements' in collector
    assert 'python scripts/export_inmet_catalog.py' in workflow
