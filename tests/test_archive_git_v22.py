"""Actual local Git archive commit/replay; no push or network in the test."""
import subprocess
from pathlib import Path
from scripts.archive_git import publish
from scripts.science.capture import Capture
from scripts.science.common import packed

def test_incremental_branch_commit_no_repeated_commit(tmp_path):
    root=tmp_path/'archive';root.mkdir()
    def git(*args):return subprocess.run(['git','-C',str(root),*args],capture_output=True,text=True,check=True).stdout.strip()
    git('init','--initial-branch','weather-archive')
    git('config','user.name','Local test');git('config','user.email','local-test@example.invalid')
    cap=Capture(tmp_path/'captures/navirai','navirai',collected_at='2026-01-01T00:00:00Z')
    body={'latitude':-23.065,'longitude':-54.19,'timezone':'UTC',
        'hourly':{'time':['2026-01-02T00:00'],'temperature_2m':[25]},'hourly_units':{'temperature_2m':'°C'}}
    e=cap.record('https://api.open-meteo.com/v1/forecast',{'latitude':-23.065,'longitude':-54.19,'models':'synthetic'},content=packed(body),status=200)
    e['collected_at_utc']='2026-01-01T00:00:00Z';cap.finish()
    result=publish(tmp_path/'captures',root,push=False)
    first=git('rev-parse','HEAD')
    assert not result['pushed'] and git('branch','--show-current')=='weather-archive'
    publish(tmp_path/'captures',root,push=False)
    assert git('rev-parse','HEAD')==first
    assert git('status','--porcelain')==''
    assert (root/'public/verification.json').exists()
