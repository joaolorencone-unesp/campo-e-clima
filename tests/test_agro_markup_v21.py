from pathlib import Path
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1]
def test_agro_navigation_and_accessibility():
    soup=BeautifulSoup((ROOT/'site/index.html').read_text(encoding='utf-8'),'html.parser')
    assert soup.select_one('button[data-tab="agro"]')
    assert soup.select_one('section#agro')
    for ident in ('agro-operation','agro-horizon','agro-product','agro-hours-table','agro-recent-table','agro-plan-result','agro-flight-height'):
        assert len(soup.select('#'+ident)) == 1, ident
    src=[s.get('src','') for s in soup.find_all('script')]
    assert 'static/agro_cockpit_v21.js?v=21' in src
    assert src.index('static/agro_cockpit_v21.js?v=21')>next(i for i,s in enumerate(src) if s.startswith('static/app.js'))
def test_scientific_caveats_are_visible():
    doc=(ROOT/'site/index.html').read_text(encoding='utf-8')
    assert 'NÃO observação de estação' in doc
    assert 'sem liberação automática' in doc
    assert 'não determina altura' in doc
    yml=(ROOT/'.github/workflows/pages.yml').read_text()
    assert 'node tests/test_agro_cockpit_v21.cjs' in yml
