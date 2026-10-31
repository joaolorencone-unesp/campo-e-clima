"""Regression: immutable gzip object variants can represent the same RAW bytes.

Reproduces the Naviraí HTTP 204 empty response collision observed on
2026-10-30 without contacting APIs or modifying the real weather archive.
"""
import gzip
import json
from pathlib import Path

import pytest

from scripts.science.archive import archive_capture, verify_manifest
from scripts.science.capture import Capture
from scripts.science.common import digest, packed


def _capture(root, date):
    capture = Capture(root, 'navirai', collected_at=f'2026-10-{date}T18:00:00Z')
    payload = packed({'latitude': -23.065, 'longitude': -54.19, 'timezone': 'UTC',
                      'hourly': {'time': [f'2026-10-{date}T19:00'], 'temperature_2m': [25.0]}})
    capture.record('https://api.open-meteo.com/v1/forecast',
                   {'latitude': -23.065, 'longitude': -54.19}, content=payload, status=200)
    empty = capture.record('https://apitempo.inmet.gov.br/estacao/2026-10-27/2026-10-30/S735',
                           {}, content=b'', status=204, product='official_response')
    capture.finish()
    return capture, empty


def test_gzip_header_variant_keeps_both_original_byte_streams(tmp_path):
    archive = tmp_path/'archive'
    older, e_old = _capture(tmp_path/'old', '29')
    old_path = older.root/e_old['relative_path']
    old_bytes = bytearray(old_path.read_bytes())
    assert len(gzip.decompress(old_bytes)) == 0
    # Older environments wrote OS=255; Python 3.11 wrote OS=3.
    old_bytes[9] = 255 if old_bytes[9] != 255 else 3
    old_path.write_bytes(old_bytes)
    e_old['gzip_sha256'] = digest(bytes(old_bytes))
    older.flush()
    first = archive_capture(older.root, archive)
    assert first['state'] == 'archived'
    older_digest = digest(old_path.read_bytes())

    newer, e_new = _capture(tmp_path/'new', '30')
    second = archive_capture(newer.root, archive)
    assert second['state'] == 'archived'
    assert (archive/e_old['relative_path']).read_bytes() == old_path.read_bytes()
    assert digest((archive/e_old['relative_path']).read_bytes()) == older_digest

    archived = archive/second['manifest']
    manifest = verify_manifest(archive, archived)
    new_entry = next(e for e in manifest['requests'] if e.get('http_status') == 204)
    assert new_entry['raw_sha256'] == e_old['raw_sha256']
    assert new_entry['gzip_sha256'] == e_new['gzip_sha256']
    assert new_entry['relative_path'] != e_old['relative_path']
    assert new_entry['capture_relative_path'] == e_new['relative_path']
    assert (archive/new_entry['relative_path']).read_bytes() == (newer.root/e_new['relative_path']).read_bytes()
    assert verify_manifest(archive, archive/first['manifest'])
    assert archive_capture(newer.root,archive)['state'] == 'already_archived'
    assert json.loads((newer.root/'manifest.json').read_text())['requests'][-1]['relative_path'] == e_new['relative_path']


def test_genuine_existing_object_corruption_is_rejected(tmp_path):
    archive = tmp_path/'archive'
    newer, empty = _capture(tmp_path/'new', '30')
    bad = archive/empty['relative_path']
    bad.parent.mkdir(parents=True)
    bad.write_bytes(gzip.compress(b'NOT SAME RAW',mtime=0))
    with pytest.raises(ValueError,match='SHA-256 ou tamanho original divergente'):
        archive_capture(newer.root,archive)
    assert not list(archive.glob('manifests/**/*.json'))
