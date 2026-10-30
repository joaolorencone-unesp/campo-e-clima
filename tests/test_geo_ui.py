"""DOM/static checks for coordinate-specific free services in v0.9."""
from pathlib import Path
import re
from html.parser import HTMLParser

BASE = Path(__file__).resolve().parents[1]

class IDs(HTMLParser):
    def __init__(self):
        super().__init__(); self.ids=[];self.tabs=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if a.get('id'):self.ids.append(a['id'])
        if tag=='button' and a.get('data-tab'):self.tabs.append(a['data-tab'])


def test_unique_identifiers_and_every_tab_exists():
    html=(BASE/'site/index.html').read_text(encoding='utf-8')
    d=IDs();d.feed(html)
    assert len(d.ids)==len(set(d.ids)), 'duplicate IDs'
    assert all(k in d.ids for k in d.tabs)
    for el in ('loc-form','loc-lat','loc-lon','loc-share','loc-reset','nasa-status','nasa-rain-plot','nasa-temperature-plot','nasa-annual-table','air-plot','hist-daily-plot','hist-compare-plot','hist-spray-plot','hist-station-table','point-elevation','custom-source-note'):
        assert el in d.ids


def test_modules_loaded_in_order_and_no_leaked_credentials():
    html=(BASE/'site/index.html').read_text(encoding='utf-8')
    assert re.search(r'static/app\.js\?v=\d+',html)
    assert re.search(r'static/location\.js\?v=\d+',html)
    assert html.index('static/app.js?') < html.index('static/location.js?') < html.index('static/history_v10.js?')
    contents='\n'.join(p.read_text(encoding='utf-8') for p in (BASE/'site/static/location.js', BASE/'site/static/app.js',BASE/'site/index.html'))
    assert 'OPENWEATHER_API_KEY=' not in contents
    assert re.search(r'AIzaSy[A-Za-z0-9_-]{30}',contents) is None
    assert re.search(r'eyJ[A-Za-z0-9_-]{100,}',contents) is None


def test_user_selectable_location_isolated_from_navarai_official():
    script=(BASE/'site/static/location.js').read_text(encoding='utf-8')
    assert "$('official-alert-strip').hidden=custom" in script
    assert 'custom:true' in script
    assert "state=null;document.querySelectorAll('.tab:not(#precision) .plot')" in script
    assert "querySelectorAll('.tab:not(#precision) table')" in script
    assert "point.latitude" in script and "point.longitude" in script
    assert 'OPENWEATHER' not in script


def test_nasa_history_uses_correct_point_and_no_secret():
    script=(BASE/'site/static/location.js').read_text(encoding='utf-8')
    for marker in ('PRECTOTCORR','T2M','NASA POWER','parameter','getNASA(point,token)','latitude:point.latitude','longitude:point.longitude'):
        assert marker in script
    assert 'NASA_EARTHDATA_TOKEN' not in script
    assert 'onecall' not in script.casefold()
