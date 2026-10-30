"""Explicitly distinct historical products; no synthetic issue-time reconstruction."""
from __future__ import annotations
import datetime as dt
from .common import config, instant, location

ENDPOINTS={
    'previous_runs':'https://previous-runs-api.open-meteo.com/v1/forecast',
    'single_run':'https://single-runs-api.open-meteo.com/v1/forecast',
    'historical_forecast':'https://historical-forecast-api.open-meteo.com/v1/forecast',
    'reanalysis':'https://archive-api.open-meteo.com/v1/archive'}

def request(client, product, location_id, model, start, end, *, run=None,
            variables=('temperature_2m','precipitation','wind_speed_10m','wind_gusts_10m','wind_direction_10m'),days=(1,2,3,7)):
    loc=location(location_id)
    first,last=dt.date.fromisoformat(start),dt.date.fromisoformat(end)
    if last<first or (last-first).days+1>config()['historical_max_days_per_request']:
        raise ValueError('Janela histórica exige 1–31 dias; executar blocos controlados')
    if product not in ENDPOINTS:raise ValueError('Produto histórico desconhecido')
    if not model or ',' in model or model=='best_match':raise ValueError('Modelo determinístico explícito obrigatório')
    initialization=None
    fields=list(variables)
    params={k:loc[k] for k in ('latitude','longitude')}
    params.update(timezone='UTC',timeformat='unixtime',models=model,start_date=start,end_date=end)
    if product=='previous_runs':
        if any(d not in (1,2,3,7) for d in days):raise ValueError('Antecedências permitidas: D1, D2, D3, D7')
        fields=[f'{v}_previous_day{d}' for v in variables for d in days]
    if product=='single_run':
        if run is None:raise ValueError('Inicialização UTC obrigatória para Single Runs')
        initialization=instant(run).isoformat()
        params['run']=instant(run).strftime('%Y-%m-%dT%H:%M')
        # Live endpoint explicitly rejects start_date/end_date for a single run.
        params.pop('start_date');params.pop('end_date')
        params['forecast_days']=16
    params['hourly']=','.join(fields)
    return client.get(ENDPOINTS[product],params,ttl_hours=24*30,product=product,initialization=initialization)
