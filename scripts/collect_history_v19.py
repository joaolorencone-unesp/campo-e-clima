#!/usr/bin/env python3
"""Run after scripts/collect.py in GitHub Actions; failures never block Pages."""
from pathlib import Path
from scripts.sources.history_navirai_v19 import publish

if __name__ == '__main__':
    result = publish(Path('site/data/history_daily_cache.json'), Path('site/data/history_navirai.json'))
    print('Navirai historical sources: ', result['state'])
