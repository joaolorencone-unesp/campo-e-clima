from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]

def test_map_tab_and_nav_structure():
    soup = BeautifulSoup((ROOT / 'site/index.html').read_text(), 'html.parser')
    assert soup.select_one('button[data-tab="maps"]')
    assert soup.select_one('section.tab#maps')
    for name in ('weather-map', 'map-variable', 'map-satellite', 'map-image-date',
                 'map-hour', 'map-time-label', 'map-status', 'map-legend', 'map-wind-summary',
                 'wind-hour-picker', 'wind-compass-content'):
        assert soup.find(id=name), name
    assert soup.select_one('script[src*="maps_v14.js"]')

def test_nasa_satellite_is_observed_not_forecast():
    html = (ROOT / 'site/index.html').read_text()
    assert 'NASA = imagem observada' in html
    assert 'Open-Meteo = previsão' in html
    assert 'passagem orbital' in html
    assert 'https://gpm.nasa.gov/data/visualization' in html
    assert 'https://www.cptec.inpe.br/dsat/' in html

def test_no_credential_is_required_or_embedded():
    js = (ROOT / 'site/static/maps_v14.js').read_text()
    assert 'gibs.earthdata.nasa.gov' in js
    assert 'api.open-meteo.com/v1/forecast' in js
    assert 'API_KEY=' not in js
    assert 'access_token=' not in js
    assert 'no-store' not in js  # forecast may use browser cache
