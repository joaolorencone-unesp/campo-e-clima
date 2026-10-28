"""Evita publicar o painel sem a biblioteca usada por todos os gráficos."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_plotly_local_asset_is_present_and_complete():
    f = ROOT / "site" / "static" / "plotly.min.js"
    assert f.exists(), "Arquivo Plotly não está versionado: site/static/plotly.min.js"
    assert f.stat().st_size > 1_000_000, "Plotly incompleto ou arquivo placeholder"
    assert "plotly.js v" in f.read_text(encoding="utf-8")[:150]


def test_dashboard_loads_local_plotly_before_scripts():
    html = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
    assert 'src="static/plotly.min.js' in html
    assert html.index('src="static/plotly.min.js') < html.index('src="static/app.js')
