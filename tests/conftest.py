"""CI tests must never quietly spend a real weather API quota."""
import os
import pytest

@pytest.fixture(autouse=True)
def prohibit_external_requests_in_offline_ci(monkeypatch):
    if os.environ.get('CAMPO_OFFLINE_TESTS')=='1':
        import requests
        def blocked(*args,**kwargs):raise AssertionError('Real HTTP is forbidden in offline tests')
        monkeypatch.setattr(requests.sessions.Session,'request',blocked)
