"""Prevent empty panels that escape from their intended tab."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / 'site/index.html').read_text(encoding='utf-8')
JS = (ROOT / 'site/static/app.js').read_text(encoding='utf-8')


def test_historical_charts_belong_to_quality_tab():
    quality_start = HTML.index('<section class="tab" id="verification">')
    extended_start = HTML.index('<section class="tab" id="extended">')
    quality = HTML[quality_start:extended_start]
    for id_ in ('historical-evidence','climate-era5-card','climate-era5-plot',
                'previous-runs-card','previous-runs-plot'):
        assert quality.count(f'id="{id_}"') == 1
        assert HTML.count(f'id="{id_}"') == 1


def test_button_has_a_real_direct_forecast_and_explains_ensemble_limits():
    assert 'id="refresh-feedback"' in HTML
    assert 'fetchDirectForecast' in JS
    assert 'https://api.open-meteo.com/v1/forecast' in JS
    assert "$('refresh').addEventListener('click',()=>refresh(true))" in JS
    assert 'Ensembles: última publicação do GitHub' in JS


def test_empty_charts_are_collapsed_instead_of_occupying_space():
    assert 'function clearPlot' in JS
    assert "$('climate-era5-card').hidden=!climateAvailable" in JS
    assert "$('previous-runs-card').hidden=!previousAvailable" in JS
    assert '.plot.is-empty' in (ROOT / 'site/static/styles.css').read_text(encoding='utf-8')
