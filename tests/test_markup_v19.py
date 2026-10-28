from pathlib import Path
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]

def test_new_map_controls_and_hidden_unvalidated_machine_tab():
    html=BeautifulSoup((ROOT/'site/index.html').read_text(), 'html.parser')
    for name in ['radar-mode','radar-play','radar-refresh','radar-frame','radar-status','history-auto-status','history-auto-table']:
        assert html.select_one('#'+name), name
    assert html.select_one('button[data-tab="machines"]').has_attr('hidden')
    assert html.select_one('section#machines').has_attr('hidden')
    for p in ['site/static/alerts_v19.js','site/static/history_auto_v19.js','site/static/maps_v14.js','site/static/plotly.min.js']:
        assert (ROOT/p).is_file(), p

def test_daily_history_ci_is_routed_after_forecast():
    y=(ROOT/'.github/workflows/pages.yml').read_text()
    assert y.index('Refresh Naviraí gridded history')>y.index('Collect forecasts')
    assert 'python -m scripts.collect_history_v19' in y
