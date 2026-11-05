"""Freshness and provenance summary for a published forecast file.

Separates, per product, the instants that the public JSON must never confuse:
model run initialisation (provider), run availability (provider), acquisition
(our HTTP response, possibly from the on-disk cache), publication (this file).
"""
from __future__ import annotations
import datetime as dt
import os
from typing import Any


def _instant(value: Any) -> dt.datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def minutes_between(later: Any, earlier: Any) -> int | None:
    a, b = _instant(later), _instant(earlier)
    if a is None or b is None:
        return None
    return int(round((a - b).total_seconds() / 60))


def collection_context(now: dt.datetime | None = None) -> dict:
    """Where and when this collection ran (GitHub Actions or local)."""
    now = now or dt.datetime.now(dt.timezone.utc)
    env = os.environ
    return {'finished_utc': now.isoformat(timespec='seconds'),
            'runner': 'github-actions' if env.get('GITHUB_ACTIONS') == 'true' else 'local',
            'run_id': env.get('GITHUB_RUN_ID'), 'run_attempt': env.get('GITHUB_RUN_ATTEMPT'),
            'event': env.get('GITHUB_EVENT_NAME'), 'git_sha': env.get('GITHUB_SHA'),
            'schedule_cron_utc': '7,37 * * * *',
            'schedule_note': 'Agendamento é melhor esforço do GitHub: a execução pode atrasar horas ou ser descartada. A idade real dos dados está nos horários de aquisição.'}


def summarize(public: dict, *, now: dt.datetime | None = None) -> dict:
    """Build ``public['freshness']`` from the model metadata already in the file."""
    now = now or dt.datetime.now(dt.timezone.utc)
    published = now.isoformat(timespec='seconds')
    models = {}
    for name, item in (public.get('ensemble_models') or {}).items():
        run = item.get('model_run') or {}
        acquired = item.get('collected_at_utc')
        init = run.get('last_run_initialisation_utc')
        available = run.get('last_run_availability_utc')
        newer_run_pending = None
        if available and acquired:
            newer_run_pending = _instant(available) is not None and _instant(acquired) is not None and _instant(acquired) < _instant(available)
        models[name] = {'state': item.get('state'), 'cache_hit': item.get('cache_hit'),
                        'acquired_utc': acquired, 'acquisition_age_min': minutes_between(published, acquired),
                        'run_initialisation_utc': init, 'run_availability_utc': available,
                        'run_age_min': minutes_between(published, init) if init else None,
                        'run_metadata_state': run.get('state', 'unknown'),
                        'newer_run_available_than_acquired': newer_run_pending,
                        'native_precipitation_step_hours': item.get('precipitation_native_step_hours')}
    deterministic = public.get('deterministic') or {}
    extended = public.get('deterministic_extended') or {}
    ages = [m['acquisition_age_min'] for m in models.values() if m['state'] == 'ok' and m['acquisition_age_min'] is not None]
    valid_rain = sum(1 for m in (public.get('ensemble_models') or {}).values() if m.get('state') == 'ok' and (m.get('precipitation_members') or 0) > 0)
    valid_gust = sum(1 for m in (public.get('ensemble_models') or {}).values() if (m.get('gust_members') or 0) > 0)
    coverage = public.get('agro_ensemble_coverage') or {}
    return {'published_utc': published,
            'deterministic': {'acquired_utc': deterministic.get('collected_at_utc'),
                              'acquisition_age_min': minutes_between(published, deterministic.get('collected_at_utc')),
                              'current_time_local': (deterministic.get('current') or {}).get('time')},
            'deterministic_extended': {'state': extended.get('state'), 'acquired_utc': extended.get('collected_at_utc')},
            'ensembles': models,
            'ensemble_oldest_acquisition_age_min': max(ages) if ages else None,
            'ensemble_newest_acquisition_age_min': min(ages) if ages else None,
            'models_valid_rain': valid_rain, 'models_valid_gusts': valid_gust,
            'models_valid_by_variable': {key: value.get('model_count') for key, value in coverage.items()},
            'models_with_newer_run_pending': sorted(n for n, m in models.items() if m['newer_run_available_than_acquired']),
            'collection': collection_context(now),
            'definitions': {'run_initialisation_utc': 'Hora de inicialização da rodada no centro meteorológico (metadados do provedor).',
                            'run_availability_utc': 'Hora em que o provedor disponibilizou a rodada.',
                            'acquired_utc': 'Hora em que a resposta HTTP foi obtida por este projeto (cache preserva a hora original).',
                            'published_utc': 'Hora em que este arquivo público foi escrito.'}}


def apply_acquisition_times(public: dict, requests: list[dict]) -> dict | None:
    """Copy the real acquisition instants (cache hits keep the original clock) into the public file.

    Returns the extended GEFS event when present so the caller can update its daily cache.
    """
    extended_event = None
    for event in requests:
        if event.get('http_status') != 200:
            continue
        params = event.get('params') or {}
        if event.get('product') == 'extended_ensemble' and event.get('payload_valid', True):
            extended_event = event
            extended = (public.get('complementary') or {}).get('gefs_extended') or {}
            if extended.get('state') == 'ok':
                extended.update(collected_at_utc=event['collected_at_utc'], cache_hit=event.get('cache_hit', False))
        if event.get('source_url') == 'https://api.open-meteo.com/v1/forecast' and not params.get('models') and event.get('product') == 'operational':
            if 'shortwave_radiation' in str(params.get('hourly', '')):
                if (public.get('deterministic_extended') or {}).get('state') == 'ok':
                    public['deterministic_extended']['collected_at_utc'] = event['collected_at_utc']
                    public['deterministic_extended']['cache_hit'] = event.get('cache_hit', False)
            elif public.get('deterministic'):
                public['deterministic']['collected_at_utc'] = event['collected_at_utc']
                public['deterministic']['cache_hit'] = event.get('cache_hit', False)
                if 'Open-Meteo Forecast' in public.get('sources', {}):
                    public['sources']['Open-Meteo Forecast']['collected_at_utc'] = event['collected_at_utc']
        for model in (public.get('ensemble_models') or {}).values():
            if model.get('code') == params.get('models') and params.get('forecast_days') and params.get('hourly'):
                model['collected_at_utc'] = event['collected_at_utc']
                model['cache_hit'] = event.get('cache_hit', False)
            if model.get('code') == params.get('models') and params.get('forecast_hours') and params.get('hourly'):
                model['joint_collected_at_utc'] = event['collected_at_utc']
                model['joint_cache_hit'] = event.get('cache_hit', False)
    return extended_event
