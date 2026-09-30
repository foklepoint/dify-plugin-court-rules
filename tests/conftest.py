import pytest
from helpers import FakeApi

import court_rules_api


@pytest.fixture
def fake_api(monkeypatch):
    api = FakeApi()
    monkeypatch.setattr(court_rules_api.requests, "request", api)
    return api
