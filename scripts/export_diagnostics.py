"""Central operational diagnostics for the public site (site/data/diagnostics.json).

Combines, without a server: the two published forecast files, the conservative
HTTP quota ledger, the scientific archive status and a rolling log of
collections. Written after each collection; failures never block publication.
"""
from __future__ import annotations
import datetime as dt
import json
import os
from pathlib import Path
from scripts.freshness import collection_context, minutes_between

PUBLIC = {'navirai': Path('site/data/latest.json'), 'diamantino': Path('site/data/locations/diamantino/latest.json')}
LOG = Path(os.environ.get('COLLECTION_LOG_PATH', 'runtime/collection_log.json'))
OUT = Path('site/data/diagnostics.json')
MAX_LOG = 400


def read_json(path: Path):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None


def location_summary(public: dict | None, path: Path) -> dict:
    if not public:
        return {'state': 'missing', 'path': str(path)}
    fresh = public.get('freshness') or {}
    sources = public.get('sources') or {}
    models = public.get('ensemble_models') or {}
    errors = {name: (item.get('detail') or item.get('error')) for name, item in {**sources, **models}.items()
              if isinstance(item, dict) and item.get('state') in ('error', 'unavailable', 'invalid')}
    comparison = public.get('previous_run_comparison') or {}
    state = 'previous_preserved' if public.get('publication_state') == 'previous_preserved' else 'ok'
    return {'state': state, 'path': str(path), 'issued_at_utc': public.get('issued_at_utc'), 'schema_version': public.get('schema_version'),
            'system_version': public.get('system_version'),
            'models_valid_rain': fresh.get('models_valid_rain'), 'models_valid_gusts': fresh.get('models_valid_gusts'),
            'models_valid_by_variable': fresh.get('models_valid_by_variable'),
            'ensemble_oldest_acquisition_age_min': fresh.get('ensemble_oldest_acquisition_age_min'),
            'ensemble_newest_acquisition_age_min': fresh.get('ensemble_newest_acquisition_age_min'),
            'models_with_newer_run_pending': fresh.get('models_with_newer_run_pending'),
            'cache_hits': sorted(name for name, item in models.items() if item.get('cache_hit')),
            'deterministic_age_min': (fresh.get('deterministic') or {}).get('acquisition_age_min'),
            'deterministic_extended_state': (public.get('deterministic_extended') or {}).get('state'),
            'sources': {name: item.get('state') for name, item in sources.items() if isinstance(item, dict)},
            'errors': errors, 'warnings': public.get('warnings'),
            'previous_run_comparison': {'state': comparison.get('state'), 'significant_days': comparison.get('significant_days'),
                                        'models_with_new_acquisition': comparison.get('models_with_new_acquisition')},
            'observations': {'inmet_hourly': ((public.get('official') or {}).get('inmet_hourly_nearby') or {}).get('state'),
                             'inmet_daily': ((public.get('official') or {}).get('inmet_daily_nearby') or {}).get('state'),
                             'embrapa': (public.get('embrapa_observations') or {}).get('state')}}


def update_log(entry: dict) -> list:
    log = read_json(LOG) or []
    if not isinstance(log, list):
        log = []
    log.append(entry)
    log = log[-MAX_LOG:]
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        LOG.write_text(json.dumps(log, ensure_ascii=False), encoding='utf-8')
    except OSError:
        pass
    return log


def cadence(log: list) -> dict:
    stamps = []
    for row in log:
        try:
            stamps.append(dt.datetime.fromisoformat(str(row.get('finished_utc')).replace('Z', '+00:00')))
        except (TypeError, ValueError):
            continue
    stamps.sort()
    gaps = [(b - a).total_seconds() / 60 for a, b in zip(stamps, stamps[1:]) if (b - a).total_seconds() > 0]
    day = [s for s in stamps if stamps and (stamps[-1] - s).total_seconds() <= 86400]
    return {'runs_logged': len(stamps), 'runs_last_24h': len(day), 'expected_runs_per_day': 48,
            'median_gap_min': sorted(gaps)[len(gaps) // 2] if gaps else None, 'max_gap_min': max(gaps) if gaps else None,
            'note': 'Contagem de execuções registradas por este log (persistido via cache do Actions); o agendamento do GitHub é melhor esforço.'}


def main(now: dt.datetime | None = None) -> dict:
    now = now or dt.datetime.now(dt.timezone.utc)
    locations = {loc: location_summary(read_json(path), path) for loc, path in PUBLIC.items()}
    usage = read_json(Path('runtime/http_cache/usage.json')) or {}
    archive = read_json(Path('site/data/archive_status.json')) or {}
    context = collection_context(now)
    entry = {'finished_utc': context['finished_utc'], 'run_id': context['run_id'], 'event': context['event'],
             'models_valid_rain': {loc: item.get('models_valid_rain') for loc, item in locations.items()},
             'cache_hits': {loc: len(item.get('cache_hits') or []) for loc, item in locations.items()},
             'issued_at_utc': {loc: item.get('issued_at_utc') for loc, item in locations.items()}}
    log = update_log(entry)
    overall = 'ok'
    for item in locations.values():
        if item.get('state') != 'ok' or (item.get('models_valid_rain') or 0) < 4:
            overall = 'degraded'
    age = max([item.get('ensemble_oldest_acquisition_age_min') or 0 for item in locations.values()] + [0])
    if age > 12 * 60:
        overall = 'stale'
    diagnostics = {'generated_utc': context['finished_utc'], 'overall_state': overall, 'collection': context,
                   'locations': locations, 'http_quota_ledger': usage,
                   'archive': {'severity': (archive.get('storage') or {}).get('severity'), 'updated_at_utc': archive.get('updated_at_utc'),
                               'manifest_count': archive.get('manifest_count'), 'failures': archive.get('failures'),
                               'archive_commit': archive.get('archive_commit')},
                   'cadence': cadence(log), 'recent_runs': log[-48:],
                   'limits': {'open_meteo_free': 'não comercial, <10.000 chamadas/dia, 5.000/h, 600/min (termos públicos); contador conservador local em http_quota_ledger',
                              'github_pages': 'site estático; sem servidor nem segredo exposto'},
                   'risks': [r for r in [
                       'Agendamento do GitHub Actions está entregando poucas execuções por dia' if (cadence(log).get('runs_last_24h') or 0) < 8 and len(log) >= 3 else None,
                       'Observações oficiais INMET indisponíveis sem token: verificação local bloqueada' if any((item.get('observations') or {}).get('inmet_hourly') not in ('ok',) for item in locations.values() if item.get('state') == 'ok') else None,
                   ] if r]}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(diagnostics, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    print('Diagnostics:', overall, '| locations:', {k: v.get('state') for k, v in locations.items()})
    return diagnostics


if __name__ == '__main__':
    main()
