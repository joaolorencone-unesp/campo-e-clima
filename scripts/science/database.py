from __future__ import annotations
import contextlib
import json
import sqlite3
from pathlib import Path
from . import SYSTEM_VERSION, PIPELINE_VERSION, SCHEMA_VERSION
from .common import config, digest, now

@contextlib.contextmanager
def connect(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA foreign_keys=ON')
    con.execute('PRAGMA journal_mode=WAL')
    try:
        yield con
        con.commit()
    except BaseException:
        con.rollback()
        raise
    finally:
        con.close()

def migrate(path, commit=None):
    with connect(path) as con:
        version = con.execute('PRAGMA user_version').fetchone()[0]
        for file in sorted((Path(__file__).parent/'migrations').glob('*.sql')):
            number = int(file.name.split('_')[0])
            content = file.read_bytes()
            sha = digest(content)
            if number <= version:
                if con.execute('SELECT sha256 FROM schema_migrations WHERE version=?',(number,)).fetchone()[0] != sha:
                    raise ValueError('Migração aplicada foi alterada')
                continue
            # executescript commits a preceding transaction; explicit transaction covers the migration.
            script = 'BEGIN IMMEDIATE;\n' + content.decode('utf-8')
            con.executescript(script)
            con.execute('INSERT INTO schema_migrations VALUES(?,?,?)',(number,sha,now()))
            con.execute(f'PRAGMA user_version={number}')
            con.commit()
        for loc in config()['locations']:
            con.execute('INSERT OR IGNORE INTO locations VALUES(?,?,?,?,?)',tuple(loc[k] for k in ('id','name','latitude','longitude','timezone')))
        con.execute('INSERT INTO system_versions VALUES(?,?,?,?) ON CONFLICT(id) DO UPDATE SET schema_version=excluded.schema_version',(SYSTEM_VERSION,PIPELINE_VERSION,SCHEMA_VERSION,commit))
        if con.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('SQLite integrity_check falhou')

def counts(path):
    with connect(path) as con:
        tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        return {t:con.execute(f'SELECT count(*) FROM "{t}"').fetchone()[0] for t in tables}

def backup(path, target):
    if Path(target).exists():
        raise FileExistsError(target)
    Path(target).parent.mkdir(parents=True,exist_ok=True)
    with connect(path) as source:
        dest = sqlite3.connect(target)
        try:
            source.backup(dest)
            if dest.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise ValueError('Backup inválido')
        finally:
            dest.close()
    return {'path':str(target),'sha256':digest(Path(target).read_bytes())}
