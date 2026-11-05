"""python -m scripts.station_calibration: verification and bias correction at physical stations.

Offline (tests/UI development): --fixture <json>. Network (GitHub Actions): --fetch.
Outputs <output-dir>/index.json and one JSON per station. Nothing here replaces the
operational forecast: recommended corrections are published with their out-of-sample evidence.
"""
from __future__ import annotations
import argparse
import json
from scripts.science.station_calibration import run


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fetch', action='store_true', help='consultar o Previous Runs API nas coordenadas das estações')
    parser.add_argument('--fixture', help='JSON offline {station_id: {model: {lead: payload}}}')
    parser.add_argument('--output-dir', default='site/data/stations')
    parser.add_argument('--runtime', default='runtime')
    parser.add_argument('--models', help='lista separada por vírgula (padrão: STATION_MODELS ou lista interna)')
    parser.add_argument('--stations', help='ids ou slugs separados por vírgula')
    parser.add_argument('--root', default='.')
    args = parser.parse_args(argv)
    if not args.fetch and not args.fixture:
        parser.error('Informe --fetch (rede) ou --fixture (offline)')
    index, _ = run(fetch=args.fetch, fixture=args.fixture, output_dir=args.output_dir, runtime=args.runtime,
                   models=args.models.split(',') if args.models else None, stations=set(args.stations.split(',')) if args.stations else None, root=args.root)
    summary = [{'station': s['id'], 'state': s['state'], 'models': s['models'], 'headline': s['headline'], 'recommendations': s['recommendations'], 'groups': s['groups_evaluated']}
               for s in index['stations']]
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return index


if __name__ == '__main__':
    main()
