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
    if not any(x.get('http_status')==200 and x.get('raw_sha256') and x.get('payload_valid',True) and x.get('product')!='official_response' for x in manifest['requests']):
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
    # Validate the ORIGINAL capture before changing any reference. A raw-content
    # address can be shared by different, equally valid gzip representations
    # (for example the OS header is 0x03 on Python 3.11 and 0xff on 3.13).
    entries=referenced(manifest)
    incoming={}
    for entry in entries:
        rel=entry['relative_path']
        checked_object(capture_dir,entry)
        if rel in incoming and incoming[rel]['gzip_sha256']!=entry['gzip_sha256']:
            raise ValueError('Mesmo caminho RAW com GZIP inconsistente na captura')
        incoming[rel]=entry

    # NEVER overwrite a historical object: its hash is still used by earlier
    # immutable manifests. If compressed bytes differ for the same raw content,
    # preserve the new original gzip under an additional content-addressed path.
    # Only relative_path changes in the new *archived* manifest, and the
    # unmodified capture artifact remains the provenance of the source bytes.
    resolved={}
    for rel,entry in incoming.items():
        dest=archive_root/rel
        actual=rel
        if dest.exists():
            existing_gzip_sha=digest(dest.read_bytes())
            if existing_gzip_sha==entry['gzip_sha256']:
                checked_object(archive_root,entry)
            else:
                # Require the old object to contain the very same RAW content.
                # If it does not, stop: this is a genuine archive corruption.
                checked_object(archive_root,{**entry,'gzip_sha256':existing_gzip_sha})
                variant=f"{entry['raw_sha256']}-{entry['gzip_sha256']}.json.gz"
                actual=f"objects/{entry['raw_sha256'][:2]}/{variant}"
                candidate={**entry,'relative_path':actual}
                if (archive_root/actual).exists():
                    checked_object(archive_root,candidate)
        resolved[rel]=actual

    for entry in entries:
        previous=entry['relative_path']
        if resolved[previous]!=previous:
            entry['capture_relative_path']=previous
            entry['relative_path']=resolved[previous]

    unique={e['relative_path']:e for e in entries}
    source_for={new:old for old,new in resolved.items()}
    size=sum((capture_dir/old).stat().st_size for old in resolved)
    existing=sum(p.stat().st_size for p in archive_root.rglob('*') if p.is_file() and '.git' not in p.parts) if archive_root.exists() else 0
    new_size=sum((capture_dir/old).stat().st_size for old,new in resolved.items() if not (archive_root/new).exists())
    limits=config()
    if (archive_root/'.git').exists():
        from .storage import inventory
        storage=inventory(archive_root,limits=limits)
        if storage['git_object_bytes'] is not None and storage['git_object_bytes']>=storage['git_limit_bytes']:
            raise ValueError('Limite Git atingido; preservar captura e preparar rotação aprovada')
    if size>limits['archive_max_bundle_bytes'] or existing+new_size+len(packed(manifest))>limits['archive_max_bytes']:
        raise ValueError('Limite conservador de armazenamento; migração gratuita precisa ser planejada')
    for rel,entry in unique.items():
        dest=archive_root/rel
        if dest.exists():
            checked_object(archive_root,entry)
        else:
            atomic(dest,(capture_dir/source_for[rel]).read_bytes())
            checked_object(archive_root,entry)
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
