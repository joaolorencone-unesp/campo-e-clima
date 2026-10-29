"""Capture the existing collector's successful and failed HTTP calls once.

The operational collector keeps its public output. This optional sidecar retains
the response, without asking providers a second time or archiving credentials.
"""
from __future__ import annotations
import gzip
import json
import os
import uuid
import subprocess
from pathlib import Path
from urllib.parse import urlsplit
from . import SYSTEM_VERSION, PIPELINE_VERSION, SCHEMA_VERSION
from .common import ROOT, atomic, digest, iso, location, now, packed, safe_parameters, write_json

ALLOWED_HOSTS = {'api.open-meteo.com','ensemble-api.open-meteo.com',
    'previous-runs-api.open-meteo.com','single-runs-api.open-meteo.com',
    'historical-forecast-api.open-meteo.com','archive-api.open-meteo.com',
    'apitempo.inmet.gov.br','apiprevmet3.inmet.gov.br'}

class Capture:
    def __init__(self, directory, location_id, *, execution_id=None, collected_at=None, commit=None):
        self.root = Path(directory)
        self.location = location(location_id)
        self.manifest = {'schema_version':SCHEMA_VERSION,'system_version':SYSTEM_VERSION,
            'pipeline_version':PIPELINE_VERSION,'execution_id':execution_id or uuid.uuid4().hex,
            'collected_at_utc':iso(collected_at or now()),'location':self.location,
            'git_commit':commit or os.environ.get('GITHUB_SHA'),'requests':[], 'status':'running'}
        code_hashes={str(p.relative_to(ROOT)).replace('\\','/'):digest(p.read_bytes())
                     for p in sorted((ROOT/'scripts').rglob('*.py'))}
        self.manifest['code_sha256']=digest(packed(code_hashes))
        self.manifest['code_files']=code_hashes
        if not self.manifest['git_commit'] and (ROOT/'.git').exists():
            git=subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,capture_output=True,text=True)
            if git.returncode==0:
                self.manifest['git_commit']=git.stdout.strip()
                dirty=subprocess.run(['git','status','--porcelain'],cwd=ROOT,capture_output=True,text=True)
                self.manifest['working_tree_dirty']=bool(dirty.stdout.strip())
        self.root.mkdir(parents=True,exist_ok=True)
        self.flush()

    def flush(self):
        write_json(self.root/'manifest.json',self.manifest)

    def record(self, url, params, *, content=None, status=None, error=None, product='operational', initialization=None, headers=None):
        parsed = urlsplit(url)
        if parsed.scheme != 'https' or parsed.hostname not in ALLOWED_HOSTS or parsed.query or parsed.username:
            raise ValueError('Fonte ou endereço não permitido')
        safe_parameters(params)
        event = {'source_url':url,'params':params,'http_status':status,'error':error,
            'collected_at_utc':now(),'product':product,
            'initialization_utc':iso(initialization) if initialization else None,
            'headers':{k:v for k,v in (headers or {}).items() if k.lower() in ('etag','last-modified','retry-after','content-type')}}
        if content is not None:
            sha = digest(content)
            path = f'objects/{sha[:2]}/{sha}.json.gz'
            atomic(self.root/path,gzip.compress(content,compresslevel=9,mtime=0))
            event.update(raw_sha256=sha,relative_path=path,byte_count=len(content),gzip_sha256=digest((self.root/path).read_bytes()))
        self.manifest['requests'].append(event)
        self.flush()
        return event

    def finish(self, status='complete'):
        self.manifest['status']=status
        self.flush()
        return self.manifest

ACTIVE = None

def record_response(url, params, response=None, error=None):
    if ACTIVE is None:
        return
    ACTIVE.record(url,params,content=getattr(response,'content',None),
        status=getattr(response,'status_code',None),error=type(error).__name__ if error else None,
        headers=dict(getattr(response,'headers',{})))

def record_auxiliary_latest(path):
    """Keep official observations and their original identifiers in the same bundle."""
    if ACTIVE is None:
        return
    body = Path(path).read_bytes()
    sha = digest(body)
    dest = f'objects/{sha[:2]}/{sha}.json.gz'
    atomic(ACTIVE.root/dest,gzip.compress(body,compresslevel=9,mtime=0))
    ACTIVE.manifest['public_snapshot']={'relative_path':dest,'raw_sha256':sha,
        'gzip_sha256':digest((ACTIVE.root/dest).read_bytes()),'byte_count':len(body)}
    ACTIVE.finish()
