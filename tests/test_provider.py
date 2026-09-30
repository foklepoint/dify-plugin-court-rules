import pytest
from dify_plugin.errors.tool import ToolProviderCredentialValidationError
from helpers import FakeResponse

from provider.court_rules import CourtRulesProvider


def test_a_good_key_passes_after_one_read(fake_api):
    fake_api.queue(FakeResponse(payload={"court": {"district_id": "edny"}}))
    CourtRulesProvider().validate_credentials({"api_key": "good-key"})
    assert len(fake_api.calls) == 1
    assert fake_api.last["url"] == "https://api.courtrules.app/api/v1/courts/edny"
    assert fake_api.last["headers"]["Authorization"] == "Bearer good-key"


def test_a_rejected_key_fails_validation_without_echoing_the_key(fake_api):
    fake_api.queue(FakeResponse(status_code=403, payload={"error": "Invalid API key"}))
    with pytest.raises(ToolProviderCredentialValidationError) as caught:
        CourtRulesProvider().validate_credentials({"api_key": "bad-key"})
    assert "Invalid API key" in str(caught.value)
    assert "bad-key" not in str(caught.value)


def test_a_missing_key_fails_validation_without_a_request(fake_api):
    with pytest.raises(ToolProviderCredentialValidationError, match="plugin credentials"):
        CourtRulesProvider().validate_credentials({})
    assert fake_api.calls == []
