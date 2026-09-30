import pytest
import requests
from helpers import FakeResponse

import court_rules_api
from court_rules_api import CourtRulesError


def test_call_api_uses_the_fixed_host_and_a_bearer_key(fake_api):
    fake_api.queue(FakeResponse(payload={"courts": []}))
    result = court_rules_api.call_api({"api_key": "secret-key"}, "GET", "/api/v1/courts")
    assert result == {"courts": []}
    call = fake_api.last
    assert call["method"] == "GET"
    assert call["url"] == "https://api.courtrules.app/api/v1/courts"
    assert call["headers"]["Authorization"] == "Bearer secret-key"
    assert call["headers"]["Accept"] == "application/json"
    assert call["timeout"] == 30


def test_call_api_drops_empty_params_and_lowercases_booleans(fake_api):
    fake_api.queue(FakeResponse(payload={}))
    court_rules_api.call_api(
        {"api_key": "k"},
        "GET",
        "/api/v1/extracted-rules",
        params={"q": "  ", "district_id": "edny", "year": None, "include_court_rules": True, "limit": 10},
    )
    assert fake_api.last["params"] == {"district_id": "edny", "include_court_rules": "true", "limit": "10"}


def test_call_api_sends_a_json_body_for_post(fake_api):
    fake_api.queue(FakeResponse(payload={"ok": True}))
    court_rules_api.call_api({"api_key": "k"}, "POST", "/api/v1/check", body={"judge_slug": "a"})
    assert fake_api.last["method"] == "POST"
    assert fake_api.last["json"] == {"judge_slug": "a"}


@pytest.mark.parametrize(
    "status, payload, headers, expected",
    [
        (401, {"error": "Missing Authorization header. Use: Bearer <api_key>"}, {}, "Court Rules API error 401"),
        (403, {"error": "Invalid API key"}, {}, "Invalid API key"),
        (
            400,
            {"error": "Invalid request", "details": [{"path": "q", "message": "Too long"}]},
            {},
            "q: Too long",
        ),
        (
            422,
            {"error": "Search too broad", "suggestion": "Narrow the search with district_id."},
            {},
            "Narrow the search with district_id.",
        ),
        (429, {"error": "Rate limit exceeded"}, {"Retry-After": "30"}, "Retry after 30 seconds."),
    ],
)
def test_error_answers_become_readable_messages(fake_api, status, payload, headers, expected):
    fake_api.queue(FakeResponse(status_code=status, payload=payload, headers=headers))
    with pytest.raises(CourtRulesError) as caught:
        court_rules_api.call_api({"api_key": "secret-key"}, "GET", "/api/v1/courts")
    assert expected in str(caught.value)
    assert "secret-key" not in str(caught.value)


def test_a_bad_key_message_points_to_the_plugin_credentials(fake_api):
    fake_api.queue(FakeResponse(status_code=403, payload={"error": "Invalid API key"}))
    with pytest.raises(CourtRulesError) as caught:
        court_rules_api.call_api({"api_key": "k"}, "GET", "/api/v1/courts")
    assert "plugin credentials" in str(caught.value)


def test_a_non_json_error_still_reports_the_status(fake_api):
    fake_api.queue(FakeResponse(status_code=502, payload=None, reason="Bad Gateway"))
    with pytest.raises(CourtRulesError) as caught:
        court_rules_api.call_api({"api_key": "k"}, "GET", "/api/v1/courts")
    assert "502" in str(caught.value)
    assert "Bad Gateway" in str(caught.value)


def test_a_non_json_success_is_an_error(fake_api):
    fake_api.queue(FakeResponse(status_code=200, payload=None))
    with pytest.raises(CourtRulesError, match="not JSON"):
        court_rules_api.call_api({"api_key": "k"}, "GET", "/api/v1/courts")


def test_a_json_list_is_an_error(fake_api):
    fake_api.queue(FakeResponse(status_code=200, payload=[1, 2]))
    with pytest.raises(CourtRulesError, match="unexpected"):
        court_rules_api.call_api({"api_key": "k"}, "GET", "/api/v1/courts")


def test_timeouts_and_connection_errors_hide_the_url(fake_api):
    fake_api.queue(requests.exceptions.Timeout("boom https://api.courtrules.app/x"))
    with pytest.raises(CourtRulesError, match="did not answer within 30 seconds") as caught:
        court_rules_api.call_api({"api_key": "k"}, "GET", "/api/v1/courts")
    assert "boom" not in str(caught.value)

    fake_api.queue(requests.exceptions.ConnectionError("dns failure for api.courtrules.app"))
    with pytest.raises(CourtRulesError, match="ConnectionError") as caught:
        court_rules_api.call_api({"api_key": "k"}, "GET", "/api/v1/courts")
    assert "dns failure" not in str(caught.value)


def test_a_missing_key_is_reported_before_any_request(fake_api):
    with pytest.raises(CourtRulesError, match="plugin credentials"):
        court_rules_api.call_api({}, "GET", "/api/v1/courts")
    with pytest.raises(CourtRulesError, match="No Court Rules API key"):
        court_rules_api.call_api({"api_key": "   "}, "GET", "/api/v1/courts")
    assert fake_api.calls == []


def test_the_key_is_trimmed(fake_api):
    fake_api.queue(FakeResponse(payload={}))
    court_rules_api.call_api({"api_key": " abc "}, "GET", "/api/v1/courts")
    assert fake_api.last["headers"]["Authorization"] == "Bearer abc"


def test_int_param_defaults_and_clamps():
    assert court_rules_api.int_param({}, "limit", 25, 1, 200) == 25
    assert court_rules_api.int_param({"limit": ""}, "limit", 25, 1, 200) == 25
    assert court_rules_api.int_param({"limit": 500}, "limit", 25, 1, 200) == 200
    assert court_rules_api.int_param({"limit": 0}, "limit", 25, 1, 200) == 1
    assert court_rules_api.int_param({"limit": 12.0}, "limit", 25, 1, 200) == 12
    assert court_rules_api.int_param({"limit": "7"}, "limit", 25, 1, 200) == 7
    with pytest.raises(CourtRulesError, match="limit"):
        court_rules_api.int_param({"limit": "many"}, "limit", 25, 1, 200)


def test_required_int_param():
    assert court_rules_api.required_int_param({"page_count": 18.0}, "page_count", 0) == 18
    with pytest.raises(CourtRulesError, match="required"):
        court_rules_api.required_int_param({}, "page_count", 0)
    with pytest.raises(CourtRulesError, match="at least 0"):
        court_rules_api.required_int_param({"page_count": -1}, "page_count", 0)
    with pytest.raises(CourtRulesError, match="number"):
        court_rules_api.required_int_param({"page_count": "x"}, "page_count", 0)


def test_optional_int_param():
    assert court_rules_api.optional_int_param({}, "year") is None
    assert court_rules_api.optional_int_param({"year": ""}, "year") is None
    assert court_rules_api.optional_int_param({"year": 2026.0}, "year") == 2026
    with pytest.raises(CourtRulesError, match="year"):
        court_rules_api.optional_int_param({"year": "next"}, "year")


def test_bool_param():
    assert court_rules_api.bool_param({}, "flag", True) is True
    assert court_rules_api.bool_param({"flag": False}, "flag", True) is False
    assert court_rules_api.bool_param({"flag": "Yes"}, "flag", False) is True
    assert court_rules_api.bool_param({"flag": "no"}, "flag", True) is False
    with pytest.raises(CourtRulesError, match="true or false"):
        court_rules_api.bool_param({"flag": "maybe"}, "flag", False)


def test_text_params():
    assert court_rules_api.text_param({"a": "  Hello "}, "a") == "Hello"
    assert court_rules_api.text_param({"a": "  Hello "}, "a", lowercase=True) == "hello"
    assert court_rules_api.text_param({}, "a") == ""
    with pytest.raises(CourtRulesError, match="required"):
        court_rules_api.required_text_param({"a": " "}, "a")
