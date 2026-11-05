"""Rebuild the public forecast file from an archived capture, without any HTTP request.

Reproducibility tool: the same collector code consumes the exact responses that
were archived (manifest + gzip objects), so a published JSON can be regenerated
or a new version of the processing can be compared against an old capture.

    python -m scripts.replay_capture --manifest weather-archive/manifests/2026-11/20261105T00-navirai.json \
        --objects-root weather-archive --location navirai --output runtime/replay/navirai.json

Products that were not archived (slow daily caches, NASA POWER, seasonal) are
reported as ``not_replayed``; nothing is fetched to fill them.
"""
from __future__ import annotations
import argparse
import gzip
import json
import os
from pathlib import Path
from scripts.science.common import location, packed
from scripts.freshness import apply_acquisition_times, summarize


def index_manifest(manifest: dict, objects_root: Path) -> dict:
    table = {}
    for event in manifest.get('requests', []):
        if event.get('http_status') != 200 or not event.get('relative_path'):
            continue
        key = (event['source_url'], packed(event.get('params') or {}).decode())
        path = objects_root / event['relative_path']
        if path.is_file():
            table[key] = (path, event)
    return table


def replay(manifest_path: Path, objects_root: Path, location_id: str, output: Path, *, now=None) -> dict:
    import scripts.collect as collector
    import scripts.sources.official as official
    manifest = json.loads(Path(manifest_path).read_text(encoding='utf-8'))
    loc = location(location_id)
    table = index_manifest(manifest, Path(objects_root))
    missing = []

    def relaxed(url, params):
        """Same URL, model and variables; horizon parameters may differ between code versions."""
        wanted = {k: v for k, v in params.items() if k not in ('forecast_days', 'forecast_hours', 'past_days')}
        for (source, raw), (path, _) in table.items():
            if source != url:
                continue
            stored = json.loads(raw)
            if {k: v for k, v in stored.items() if k not in ('forecast_days', 'forecast_hours', 'past_days')} == wanted:
                return path
        return None

    def fetch(url, params):
        key = (url, packed(params).decode())
        path = table[key][0] if key in table else relaxed(url, params)
        if path is None:
            missing.append(key)
            raise ValueError('Resposta não arquivada para esta consulta')
        return json.loads(gzip.open(path, 'rb').read())

    def http_json(url, timeout=18, record_url=None):
        for (source, params), (path, event) in table.items():
            if source == url and params == '{}':
                return json.loads(gzip.open(path, 'rb').read())
        raise ValueError('Resposta oficial não arquivada')

    not_replayed = lambda *a, **k: {'state': 'not_replayed', 'note': 'Produto não incluído na captura arquivada; nada foi consultado.'}
    saved = {name: getattr(collector, name) for name in ('fetch', 'fetch_meta', 'LAT', 'LON', 'TZ', 'collect_cptec', 'collect_soil_forecast',
             'collect_nasa_power', 'collect_extended', 'collect_gefs_extended', 'collect_previous_runs', 'collect_climate_era5', 'collect_openweather_free')}
    saved_official = official.http_json
    old_output = os.environ.get('OUTPUT_JSON')
    try:
        collector.LAT, collector.LON, collector.TZ = loc['latitude'], loc['longitude'], loc['timezone']
        collector.fetch = fetch
        collector.fetch_meta = lambda url: (_ for _ in ()).throw(ValueError('metadados não arquivados'))
        collector.META_FAILURES['transport'] = 0
        for name in ('collect_cptec', 'collect_soil_forecast', 'collect_nasa_power', 'collect_extended', 'collect_gefs_extended',
                     'collect_previous_runs', 'collect_climate_era5', 'collect_openweather_free'):
            setattr(collector, name, not_replayed)
        official.http_json = http_json
        os.environ['OUTPUT_JSON'] = str(output)
        output.parent.mkdir(parents=True, exist_ok=True)
        collector.main(include_local_sources=location_id == 'navirai')
        public = json.loads(output.read_text(encoding='utf-8'))
        public['site']['id'] = location_id
        public['replay'] = {'manifest': str(manifest_path), 'execution_id': manifest.get('execution_id'),
                            'captured_at_utc': manifest.get('collected_at_utc'), 'missing_requests': len(missing)}
        apply_acquisition_times(public, manifest.get('requests', []))
        public['freshness'] = summarize(public, now=now)
        output.write_text(json.dumps(public, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
        return public
    finally:
        for name, value in saved.items():
            setattr(collector, name, value)
        official.http_json = saved_official
        collector.RUN_AVAILABILITY.clear()
        if old_output is None:
            os.environ.pop('OUTPUT_JSON', None)
        else:
            os.environ['OUTPUT_JSON'] = old_output


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--objects-root', required=True)
    parser.add_argument('--location', choices=['navirai', 'diamantino'], required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args(argv)
    public = replay(Path(args.manifest), Path(args.objects_root), args.location, Path(args.output))
    print(json.dumps({'output': args.output, 'models_valid_rain': public['freshness']['models_valid_rain'],
                      'missing_requests': public['replay']['missing_requests']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
