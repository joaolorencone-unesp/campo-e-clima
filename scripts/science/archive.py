"""Immutable gzip objects + manifest; SQLite is a rebuildable local derivative."""
from __future__ import annotations
import datetime as dt
import gzip
import json
import os
import shutil
import tempfile
from pathlib import Path
from .common import atomic, config, digest, instant, location, packed, write_json

def referenced(manifest):
    return [x for x in manifest.get('requests',[]) + [manifest.get('public_snapshot',{})]
            if x.get('relative_path')]

def checked_object(root, entry):
    root=Path(root).resolve()
    path=(root/entry['relative_path']).resolve()
    if not path.is_relative_to(root) or path.suffix!='.gz' or path.is_symlink():
        raise ValueError('Caminho inseguro no manifesto')
    compressed=path.read_bytes()
    if digest(compressed)!=entry['gzip_sha256']:
        raise ValueError('SHA-256 gzip divergente')
    with gzip.open(path,'rb') as stream:
        body=stream.read(100_000_001)
    if len(body)>100_000_000 or len(body)!=entry['byte_count'] or digest(body)!=entry['raw_sha256']:
        raise ValueError('SHA-256 ou tamanho original divergente')
    return body

def verify_manifest(root, file):
    file=Path(file)
    raw=file.read_bytes()
    if file.with_suffix('.sha256').read_text().strip()!=digest(raw):
        raise ValueError('SHA-256 do manifesto divergente')
    manifest=json.loads(raw)
    for entry in referenced(manifest):
        checked_object(root,entry)
    return manifest

def archive_capture(capture_dir, archive_root, *, force_slot=None):
    capture_dir,archive_root=Path(capture_dir),Path(archive_root)
    manifest=json.loads((capture_dir/'manifest.json').read_text(encoding='utf-8'))
    loc=location(manifest['location']['id'])
    if manifest['location']!=loc or not loc['public']:
        raise ValueError('Somente localidades públicas cadastradas podem ser arquivadas')
    if not any(x.get('http_status')==200 and x.get('raw_sha256') and x.get('product')!='official_response' for x in manifest['requests']):
        raise ValueError('Nenhum produto HTTP válido; janela não será consumida')
    stamp=instant(manifest['collected_at_utc'])
    slot=stamp.replace(hour=stamp.hour//6*6,minute=0,second=0,microsecond=0)
    name=f"manifests/{slot:%Y-%m}/{slot:%Y%m%dT%H}-{loc['id']}.json"
    if force_slot:
        # For explicit historical/observation imports, names are content-addressed.
        identity=[[x.get('product'),x.get('source_url'),x.get('params'),x.get('raw_sha256')] for x in manifest['requests']]
        name=f"imports/{loc['id']}/{digest(packed(identity))}.json"
    target=archive_root/name
    if target.exists():
        verify_manifest(archive_root,target)
        return {'state':'already_archived','manifest':name}
    entries=referenced(manifest)
    unique={x['relative_path']:x for x in entries}
    for entry in unique.values():
        checked_object(capture_dir,entry)
    size=sum((capture_dir/x).stat().st_size for x in unique)
    existing=sum(p.stat().st_size for p in archive_root.rglob('*') if p.is_file() and '.git' not in p.parts) if archive_root.exists() else 0
    new_size=sum((capture_dir/x).stat().st_size for x in unique if not (archive_root/x).exists())
    limits=config()
    if size>limits['archive_max_bundle_bytes'] or existing+new_size+len(packed(manifest))>limits['archive_max_bytes']:
        raise ValueError('Limite conservador de armazenamento; migração gratuita precisa ser planejada')
    for rel,entry in unique.items():
        dest=archive_root/rel
        if dest.exists():
            checked_object(archive_root,entry)
        else:
            atomic(dest,(capture_dir/rel).read_bytes())
    # Manifest is the commit marker. Objects without a manifest are ignored during replay.
    atomic(target,packed(manifest))
    atomic(target.with_suffix('.sha256'),digest(packed(manifest)).encode())
    verify_manifest(archive_root,target)
    return {'state':'archived','manifest':name,'compressed_bytes':size,'new_bytes':new_size,
        'projected_30_days_two_locations_bytes':size*2*4*30,
        'projected_365_days_two_locations_bytes':size*2*4*365}

def rebuild(archive_root, target, *, since=None):
    from .database import migrate, connect, counts
    from .ingest import ingest_manifest
    archive_root,target=Path(archive_root),Path(target)
    if since:
        since=dt.date.fromisoformat(since).isoformat()
    if target.exists():
        raise FileExistsError('Reconstrução exige destino novo')
    target.parent.mkdir(parents=True,exist_ok=True)
    work=target.with_name(target.name+'.building')
    if work.exists():
        raise FileExistsError('Reconstrução interrompida existente; preserve e selecione novo destino')
    migrate(work)
    try:
        files=sorted(archive_root.glob('manifests/**/*.json'))+sorted(archive_root.glob('imports/**/*.json'))
        selected=0
        for file in files:
            manifest=verify_manifest(archive_root,file)
            if since and manifest['collected_at_utc'][:10]<since:continue
            ingest_manifest(work,archive_root,manifest)
            selected+=1
        with connect(work) as con:
            if con.execute('PRAGMA integrity_check').fetchone()[0]!='ok' or con.execute('PRAGMA foreign_key_check').fetchall():
                raise ValueError('Falha de integridade na reconstrução')
            con.execute('PRAGMA wal_checkpoint(TRUNCATE)')
        os.replace(work,target)
        return {'manifests':selected,'available_manifests':len(files),'counts':counts(target),'integrity':'ok','since_collection_date_utc':since}
    except BaseException:
        # Preserve the interrupted derivative for diagnosis; do not replace destination.
        raise
