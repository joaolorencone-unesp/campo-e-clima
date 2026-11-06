"""Recover missed Pages schedules from one external runner. Default is read-only."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys

import requests

from scripts.freshness import minutes_between

DIAGNOSTICS = 'https://joaolorencone-unesp.github.io/campo-e-clima/data/diagnostics.json'
WORKFLOW = 'https://api.github.com/repos/joaolorencone-unesp/campo-e-clima/actions/workflows/pages.yml'
API_HEADERS = {'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2026-03-10'}
LOCATIONS = ('navirai', 'diamantino')
MAX_AGE_MIN = 35
MIN_RUN_INTERVAL_MIN = 25


def check(session, *, now=None, token=None):
    now = (now or dt.datetime.now(dt.timezone.utc)).isoformat()
    snapshot = session.get(DIAGNOSTICS, timeout=15, headers={'Cache-Control': 'no-cache'})
    snapshot.raise_for_status()
    locations = snapshot.json()['locations']
    ages = {loc: minutes_between(now, locations[loc]['issued_at_utc']) for loc in LOCATIONS}
    if any(age is None or age < 0 for age in ages.values()):
        raise ValueError('Horário de publicação ausente, inválido ou no futuro')
    result = {'publication_age_min': ages}
    if max(ages.values()) < MAX_AGE_MIN:
        return {**result, 'state': 'recent_publication'}

    response = session.get(f'{WORKFLOW}/runs', params={'branch': 'main', 'per_page': 20},
                           headers=API_HEADERS, timeout=15)
    response.raise_for_status()
    for run in response.json()['workflow_runs']:
        if run['status'] != 'completed':
            return {**result, 'state': 'run_active', 'run_id': run['id']}
        age = minutes_between(now, run['created_at'])
        if age is None or age < 0:
            raise ValueError('Horário de execução do Actions inválido ou no futuro')
        if age < MIN_RUN_INTERVAL_MIN:
            return {**result, 'state': 'recent_run', 'run_id': run['id']}

    if not token:
        return {**result, 'state': 'would_dispatch'}
    try:
        response = session.post(f'{WORKFLOW}/dispatches', json={'ref': 'main'},
                                headers={**API_HEADERS, 'Authorization': f'Bearer {token}'},
                                timeout=15, allow_redirects=False)
    except requests.RequestException as exc:
        raise ValueError(f'GitHub não confirmou o disparo ({type(exc).__name__})') from None
    # A timeout or unexpected response is ambiguous. Leave retries to the next poll.
    if response.status_code not in (200, 204):
        raise ValueError(f'GitHub recusou ou não confirmou o disparo (HTTP {response.status_code})')
    return {**result, 'state': 'dispatch_accepted'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dispatch', action='store_true', help='Autoriza o POST se a publicação estiver atrasada')
    args = parser.parse_args()
    token = os.environ.get('CAMPO_PAGES_DISPATCH_TOKEN', '').strip() if args.dispatch else None
    if args.dispatch and not token:
        parser.error('Defina CAMPO_PAGES_DISPATCH_TOKEN no ambiente do agendador')
    try:
        with requests.Session() as session:
            print(json.dumps(check(session, token=token), ensure_ascii=False))
    except (requests.RequestException, KeyError, TypeError, ValueError) as exc:
        print(f'Verificação interrompida ({type(exc).__name__}): {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
