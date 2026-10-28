from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / 'site/index.html').read_text(encoding='utf-8')
JS = (ROOT / 'site/static/maps_v14.js').read_text(encoding='utf-8')


def test_radar_controls_and_sources_in_markup():
    doc = BeautifulSoup(HTML, 'html.parser')
    assert doc.select_one('script[src*="maps_v14.js?v=20"]')
    for id_ in ('radar-mode', 'radar-prev', 'radar-next', 'radar-speed', 'radar-frame',
                'radar-frame-time', 'radar-loading', 'radar-play', 'map-product-legend',
                'map-product-source', 'map-variable', 'map-hour'):
        assert doc.find(id=id_), id_
    assert doc.select_one('link[href*="styles.css?v=20"]')


def test_future_map_layers_and_scientific_disclaimers():
    doc = BeautifulSoup(HTML, 'html.parser')
    values = {item.get('value') for item in doc.select('#map-variable option')}
    assert {'cloud_cover', 'precipitation', 'temperature_2m', 'relative_humidity_2m',
            'wind_speed_10m', 'wind_gusts_10m', 'cape', 'precipitation_probability'} <= values
    assert 'radar observado' in HTML.lower()
    assert 'previsão futura' in HTML.lower() or 'campos previstos' in HTML.lower()
    assert 'dBZ' in JS and 'não mm/h' in JS


def test_radar_loading_and_unmixed_sources():
    assert 'layer.on(\'load\'' in JS
    assert 'radarLayerEntry(radarIndex+1)' in JS
    assert "radarTile=entry.layer" in JS
    assert 'map.removeLayer(imageLayer)' in JS  # distinct images should not be merged
    assert 'maxNativeZoom:7' in JS
    assert 'api.rainviewer.com/public/weather-maps.json' in JS
