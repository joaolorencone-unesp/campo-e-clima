import datetime as dt
import json
from unittest.mock import Mock

import pytest
import requests

from scripts import dispatch_pages as dispatch


NOW = dt.datetime(2026, 11, 6, 12, tzinfo=dt.timezone.utc)


def timestamp(minutes_ago):
    return (NOW - dt.timedelta(minutes=minutes_ago)).isoformat()


def response(payload, status=200):
    result = requests.Response()
    result.status_code = status
    result._content = json.dumps(payload).encode('utf-8')
    return result


def session_for(ages, runs=(), *, runs_status=200):
    locations = {loc: {'issued_at_utc': timestamp(age)} for loc, age in zip(dispatch.LOCATIONS, ages)}
    session = Mock(spec=requests.Session)
    session.get.side_effect = [response({'locations': locations}), response({'workflow_runs': list(runs)}, runs_status)]
    return session


def test_recent_publication_never_queries_actions_or_dispatches():
    session = session_for([20, 34])
    assert dispatch.check(session, now=NOW, token='secret')['state'] == 'recent_publication'
    session.get.assert_called_once()
    session.post.assert_not_called()


@pytest.mark.parametrize(('status', 'age', 'expected'), [
    ('queued', 65, 'run_active'),
    ('in_progress', 45, 'run_active'),
    ('completed', 10, 'recent_run'),
    ('completed', 25, 'would_dispatch'),
])
def test_delay_in_either_location_checks_queue_and_cooldown(status, age, expected):
    session = session_for([20, 35], [{'id': 10, 'status': status, 'created_at': timestamp(age)}])
    assert dispatch.check(session, now=NOW)['state'] == expected
    assert session.get.call_count == 2
    session.post.assert_not_called()


@pytest.mark.parametrize('status', [200, 204, 302, 401])
def test_only_explicit_dispatch_sends_token_to_fixed_github_endpoint(status):
    session = session_for([45, 45])
    session.post.return_value = response({}, status)
    if status in (200, 204):
        assert dispatch.check(session, now=NOW, token='secret')['state'] == 'dispatch_accepted'
    else:
        with pytest.raises(ValueError, match=f'HTTP {status}'):
            dispatch.check(session, now=NOW, token='secret')
    assert all('Authorization' not in call.kwargs['headers'] for call in session.get.call_args_list)
    session.post.assert_called_once_with(f'{dispatch.WORKFLOW}/dispatches', json={'ref': 'main'},
                                         headers={**dispatch.API_HEADERS, 'Authorization': 'Bearer secret'},
                                         timeout=15, allow_redirects=False)


def test_invalid_publication_or_actions_failure_blocks_dispatch():
    session = session_for([40, -1])
    with pytest.raises(ValueError, match='no futuro'):
        dispatch.check(session, now=NOW, token='secret')
    session.post.assert_not_called()

    session = session_for([50, 50], runs_status=503)
    with pytest.raises(requests.HTTPError, match='503'):
        dispatch.check(session, now=NOW, token='secret')
    session.post.assert_not_called()


def test_dispatch_timeout_is_ambiguous_and_never_retried_inline():
    session = session_for([50, 50])
    session.post.side_effect = requests.Timeout('unexpected secret in transport error')
    with pytest.raises(ValueError, match=r'não confirmou o disparo \(Timeout\)$'):
        dispatch.check(session, now=NOW, token='secret')
    session.post.assert_called_once()
