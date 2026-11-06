import json
from pathlib import Path
from unittest.mock import Mock

import pytest
import requests

from scripts import ai_bulletin, export_diagnostics, science_cli
from scripts.science.common import location


def forecast(loc, stamp):
    return {
        'site': location(loc), 'issued_at_utc': stamp,
        'deterministic': {'collected_at_utc': stamp, 'hourly': {
            'time': ['2026-11-06T11:00'], 'precipitation': [0],
        }},
    }


@pytest.mark.parametrize('failed', ['navirai', 'diamantino'])
def test_pages_preserves_only_failed_location(tmp_path, monkeypatch, failed):
    monkeypatch.chdir(tmp_path)
    original = forecast(failed, '2026-11-06T12:00:00+00:00')
    monkeypatch.setattr(science_cli, 'now', lambda: '2026-11-06T13:05:00+00:00')
    fetch = Mock(return_value=Mock(status_code=200, json=lambda: original))
    monkeypatch.setattr(science_cli.requests, 'get', fetch)

    def collect(loc, *args, **kwargs):
        path = science_cli.forecast_path(loc)
        path.parent.mkdir(parents=True, exist_ok=True)
        if loc == failed:
            path.write_text('{}', encoding='utf-8')  # A partial file may exist after collection fails.
            raise SystemExit('empty forecast')
        path.write_text(json.dumps(forecast(loc, '2026-11-06T13:00:00+00:00')), encoding='utf-8')
        return {'location': loc, 'output': str(path)}

    monkeypatch.setattr(science_cli, 'collect', collect)
    result = science_cli.main(['collect', '--location', 'all', '--preserve-published'])
    assert result[-1]['state'] == 'previous_preserved'
    path = science_cli.forecast_path(failed)
    public = json.loads(path.read_text(encoding='utf-8'))
    assert public['issued_at_utc'] == public['deterministic']['collected_at_utc'] == '2026-11-06T12:00:00+00:00'
    assert export_diagnostics.location_summary(public, path)['state'] == 'previous_preserved'
    fetch.assert_called_once_with(science_cli.PUBLIC_SITE + path.relative_to('site').as_posix(),
                                  headers={'Cache-Control': 'no-cache'}, timeout=12, allow_redirects=False)
    monkeypatch.setattr(ai_bulletin, 'generate', Mock(side_effect=AssertionError('Forecast was preserved')))
    assert ai_bulletin.main(['--input', str(path)]) == []


def test_pages_refuses_to_deploy_after_total_outage(monkeypatch):
    monkeypatch.setattr(science_cli, 'collect', Mock(side_effect=requests.Timeout))
    restore = Mock(side_effect=AssertionError('Neither location was updated'))
    monkeypatch.setattr(science_cli, 'restore_published_forecast', restore)
    with pytest.raises(RuntimeError, match='Nenhuma localidade atualizada'):
        science_cli.main(['collect', '--location', 'all', '--preserve-published'])
    restore.assert_not_called()


def test_successful_pages_update_does_not_read_existing_site(monkeypatch):
    monkeypatch.setattr(science_cli, 'collect', lambda loc, *args, **kwargs: {'location': loc})
    restore = Mock(side_effect=AssertionError('Both locations updated'))
    monkeypatch.setattr(science_cli, 'restore_published_forecast', restore)
    assert science_cli.main(['collect', '--location', 'all', '--preserve-published']) == [
        {'location': 'navirai'}, {'location': 'diamantino'},
    ]
    restore.assert_not_called()


def test_restore_rejects_other_location_and_empty_forecast(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(science_cli, 'now', lambda: '2026-11-06T13:05:00+00:00')
    other = forecast('diamantino', '2026-11-06T12:00:00+00:00')
    empty = {**forecast('navirai', '2026-11-06T12:00:00+00:00'), 'deterministic': None}
    monkeypatch.setattr(science_cli.requests, 'get', Mock(side_effect=[
        Mock(status_code=200, json=lambda: other), Mock(status_code=200, json=lambda: empty),
    ]))
    for reason in ('Identidade divergente', 'sem dados válidos'):
        with pytest.raises(ValueError, match=reason):
            science_cli.restore_published_forecast('navirai')
    assert not science_cli.forecast_path('navirai').exists()


def test_collection_failure_without_valid_raw_is_recorded_as_unavailable(tmp_path, monkeypatch):
    import scripts.collect as collector

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(collector, 'main', Mock(side_effect=requests.Timeout))
    with pytest.raises(requests.Timeout):
        science_cli.collect('navirai', tmp_path / 'runtime')
    manifest = json.loads(Path('runtime/captures/navirai/manifest.json').read_text(encoding='utf-8'))
    assert manifest['status'] == 'unavailable'
