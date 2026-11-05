"""v3.0 markup: grouped navigation, simple/advanced levels and new scientific panels."""
from pathlib import Path
from bs4 import BeautifulSoup
import yaml

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / 'site/index.html').read_text(encoding='utf-8')
SOUP = BeautifulSoup(HTML, 'html.parser')


def test_every_tab_sits_in_a_named_group_and_ids_are_unique():
    groups = SOUP.select('#tabs .tab-group[data-group]')
    assert [g['data-group'] for g in groups] == ['overview', 'rain', 'operations', 'maps', 'science']
    tabs = [b['data-tab'] for b in SOUP.select('#tabs button[data-tab]')]
    assert len(tabs) == len(set(tabs)) == 12
    assert SOUP.select_one('#nav-groups') is not None and SOUP.select_one('#mode-switch button[data-mode="simple"]')
    ids = [tag['id'] for tag in SOUP.find_all(id=True)]
    assert len(ids) == len(set(ids)), 'duplicate ids'


def test_simple_mode_keeps_essential_sections_and_hides_dense_ones():
    overview = SOUP.select_one('section#overview')
    assert overview.select_one('#farm-summary') is not None
    assert 'advanced-only' not in (overview.select_one('#farm-summary').get('class') or [])
    for ident in ('metrics', 'agro-ensemble-panel'):
        assert 'advanced-only' in overview.select_one('#' + ident).get('class', []), ident
    css = (ROOT / 'site/static/styles.css').read_text(encoding='utf-8')
    assert 'body.mode-simple .advanced-only{display:none!important}' in css


def test_new_scientific_panels_and_captions():
    for ident in ('rain-accumulated-panel', 'rain-agreement-daily-panel', 'run-change-panel', 'freshness-panel', 'diagnostics-card'):
        assert SOUP.select_one('#' + ident) is not None, ident
    text = HTML.lower()
    assert 'não calibradas' in text and 'passo nativo' in text
    assert 'não são independentes entre si' in text  # ECMWF IFS/AIFS, GEFS/AI-GEFS caveat


def test_workflows_persist_state_and_export_diagnostics():
    pages = yaml.safe_load((ROOT / '.github/workflows/pages.yml').read_text(encoding='utf-8'))
    steps = pages['jobs']['build']['steps']
    names = [s.get('name', '') for s in steps]
    assert 'Export central diagnostics (freshness, quota, cadence, archive)' in names
    assert any('runtime/previous_publication' in str(s.get('with', {}).get('path', '')) for s in steps)
    assert pages['jobs']['build']['if'].startswith("github.repository == 'joaolorencone-unesp/campo-e-clima'")
    for name in ('science.yml', 'archive-recovery.yml'):
        assert "github.repository == 'joaolorencone-unesp/campo-e-clima'" in (ROOT / '.github/workflows' / name).read_text(encoding='utf-8')
    assert 'node tests/test_v30_frontend.cjs' in (ROOT / '.github/workflows/pages.yml').read_text(encoding='utf-8')


def test_no_credentials_or_tokens_in_public_assets():
    for path in (ROOT / 'site').rglob('*.js'):
        content = path.read_text(encoding='utf-8', errors='ignore')
        assert 'INMET_API_TOKEN' not in content and 'OPENWEATHER_FREE_API_KEY' not in content, path
    assert 'INMET_API_TOKEN' not in HTML
