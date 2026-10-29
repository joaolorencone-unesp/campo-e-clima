"""Monthly lossless scientific volumes. New destinations only; no deletion or push."""
from __future__ import annotations
import argparse
import json
from pathlib import Path, PurePosixPath
import zipfile
from scripts.science.archive import referenced, verify_manifest
from scripts.science.common import atomic, digest, now, write_json

def create(root,output):
    root,output=Path(root),Path(output)
    if output.exists():raise FileExistsError('Backup exige diretório novo')
    months={}
    for p in sorted(root.glob('manifests/**/*.json'))+sorted(root.glob('imports/**/*.json')):
        doc=verify_manifest(root,p);bucket=months.setdefault(doc['collected_at_utc'][:7],set())
        bucket.update([p.relative_to(root).as_posix(),p.with_suffix('.sha256').relative_to(root).as_posix()])
        bucket.update(e['relative_path'] for e in referenced(doc))
    if not months:raise ValueError('Arquivo científico vazio')
    output.mkdir(parents=True)
    parts={}
    for month,names in months.items():
        target=output/f'weather-{month}.zip'
        # Objects are already gzip level 9; ZIP_STORED avoids redundant compression.
        hashes={name:digest((root/name).read_bytes()) for name in sorted(names)}
        with zipfile.ZipFile(target,'x',compression=zipfile.ZIP_STORED) as z:
            for name in sorted(names):z.write(root/name,name)
            z.writestr('VOLUME.json',json.dumps({'files':hashes},sort_keys=True))
        parts[target.name]=digest(target.read_bytes())
    catalog={'schema_version':1,'created_at_utc':now(),'parts':parts,
             'policy':'Backup adicional. Preservar Git e RAW originais; não reduz histórico remoto.'}
    write_json(output/'CATALOG.json',catalog)
    atomic(output/'CATALOG.sha256',digest((output/'CATALOG.json').read_bytes()).encode())
    return verify(output)

def verify(root,restore=None):
    root=Path(root);body=(root/'CATALOG.json').read_bytes()
    if digest(body)!=(root/'CATALOG.sha256').read_text().strip():raise ValueError('Hash do catálogo divergente')
    catalog=json.loads(body);contents={}
    for name,sha in catalog['parts'].items():
        if PurePosixPath(name).name!=name:raise ValueError('Volume fora do diretório')
        path=root/name
        if digest(path.read_bytes())!=sha:raise ValueError('Hash de volume divergente')
        with zipfile.ZipFile(path) as z:
            if z.testzip() is not None:raise ValueError('Volume corrompido')
            if len(z.namelist())!=len(set(z.namelist())):raise ValueError('Entradas duplicadas no ZIP')
            files=json.loads(z.read('VOLUME.json'))['files']
            if set(z.namelist())!=set(files)|{'VOLUME.json'}:raise ValueError('Conteúdo fora do manifesto')
            for rel,expected in files.items():
                p=PurePosixPath(rel)
                if p.is_absolute() or '..' in p.parts or '\\' in rel or ':' in rel or p.parts[0] not in ('objects','manifests','imports'):
                    raise ValueError('Caminho inseguro no volume')
                data=z.read(rel)
                if digest(data)!=expected:raise ValueError('Hash de arquivo divergente')
                if rel in contents and contents[rel]!=data:raise ValueError('Conflito entre volumes')
                contents[rel]=data
    if restore is not None:
        restore=Path(restore)
        if restore.exists():raise FileExistsError('Restauração exige diretório novo')
        restore.mkdir(parents=True)
        for rel,data in contents.items():atomic(restore/rel,data)
        for p in list(restore.glob('manifests/**/*.json'))+list(restore.glob('imports/**/*.json')):verify_manifest(restore,p)
    return {'parts':len(catalog['parts']),'files_verified':len(contents),'restored':str(restore) if restore else None}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['create','verify','restore'])
    p.add_argument('--archive',default='weather-archive');p.add_argument('--backup',required=True);p.add_argument('--output')
    a=p.parse_args()
    if a.command=='restore' and not a.output:p.error('--output obrigatório')
    result=create(a.archive,a.backup) if a.command=='create' else verify(a.backup,a.output if a.command=='restore' else None)
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
