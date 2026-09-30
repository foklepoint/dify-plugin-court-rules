import pytest
from helpers import FakeResponse, json_of, run_tool, text_of

from court_rules_api import CourtRulesError
from tools.check_document import CheckDocumentTool
from tools.get_judge_rules import GetJudgeRulesTool
from tools.list_court_holidays import ListCourtHolidaysTool
from tools.list_courts import ListCourtsTool
from tools.list_judges import ListJudgesTool
from tools.search_filing_rules import SearchFilingRulesTool

COURTS = {
    "courts": [
        {
            "district_id": "edny",
            "name": "Eastern District of New York",
            "circuit": "2nd Circuit",
            "state": "New York",
            "status": "live",
            "judges_mapped": 62,
            "judges_profiled": 5,
        },
        {
            "district_id": "sdny",
            "name": "Southern District of New York",
            "circuit": "2nd Circuit",
            "state": "New York",
            "status": "coming_soon",
            "judges_mapped": 0,
        },
        {
            "district_id": "ca-los-angeles-superior",
            "name": "Superior Court of California, County of Los Angeles",
            "circuit": None,
            "state": "California",
            "status": "live",
            "judges_mapped": 400,
        },
    ],
    "meta": {"total_districts": 1052, "districts_with_data": 51, "total_judges_mapped": 3232},
}

JUDGES = {
    "district_id": "edny",
    "judges": [
        {"slug": "gary-r-brown", "name": "Gary R. Brown", "has_profile": True, "has_rules": True, "judge_type": "district"},
        {"slug": "jane-doe", "name": "Jane Doe", "has_profile": False, "has_rules": False, "judge_type": "magistrate"},
    ],
    "meta": {"total": 2, "profiled": 1, "with_rules": 1, "court_level_rules": True},
}

EXTRACTED_RULE = {
    "rule_id": "6f2d2b1c-0000-4000-8000-000000000001",
    "district_id": "il-cook-circuit",
    "judge_slug": "court",
    "source_url": "https://www.cookcountycourt.org/rules.pdf",
    "doc_kind": "local rules",
    "logic_type": "CourtesyCopyRule",
    "workflow_phase": "FILING",
    "content": {
        "source_text": "Courtesy copies are required for motions over ten pages.",
        "summary": "Courtesy copies are required for motions over ten pages.",
        "rule_tags": ["courtesy copy"],
        "visual_severity": "WARNING",
        "citation_source": {"page": 3, "section": "II.A"},
    },
}


def test_list_courts_filters_by_words_and_status(fake_api):
    fake_api.queue(FakeResponse(payload=COURTS))
    messages = run_tool(ListCourtsTool, {"query": "eastern district"})
    assert fake_api.last["url"] == "https://api.courtrules.app/api/v1/courts"
    result = json_of(messages)
    assert [court["district_id"] for court in result["courts"]] == ["edny"]
    assert result["meta"]["matched"] == 1
    assert result["meta"]["total_districts"] == 1052
    digest = text_of(messages)
    assert "edny: Eastern District of New York (2nd Circuit, New York), live, 62 judges mapped" in digest


def test_list_courts_status_any_and_state_and_limit(fake_api):
    fake_api.queue(FakeResponse(payload=COURTS))
    messages = run_tool(ListCourtsTool, {"state": "new york", "status": "any", "limit": 1})
    result = json_of(messages)
    assert result["meta"]["matched"] == 2
    assert result["meta"]["returned"] == 1
    assert "Showing 1 of 2 matching courts" in text_of(messages)


def test_list_courts_default_status_is_live(fake_api):
    fake_api.queue(FakeResponse(payload=COURTS))
    result = json_of(run_tool(ListCourtsTool, {}))
    assert [court["district_id"] for court in result["courts"]] == ["edny", "ca-los-angeles-superior"]


def test_list_courts_with_no_match_says_so(fake_api):
    fake_api.queue(FakeResponse(payload=COURTS))
    messages = run_tool(ListCourtsTool, {"query": "nowhere"})
    assert "No courts matched" in text_of(messages)
    assert json_of(messages)["courts"] == []


def test_list_judges_sends_the_court_and_filters_by_name(fake_api):
    fake_api.queue(FakeResponse(payload=JUDGES))
    messages = run_tool(ListJudgesTool, {"district_id": " EDNY ", "name": "brown"})
    assert fake_api.last["params"] == {"district_id": "edny"}
    result = json_of(messages)
    assert [judge["slug"] for judge in result["judges"]] == ["gary-r-brown"]
    digest = text_of(messages)
    assert "gary-r-brown: Gary R. Brown (district), own rules: yes, compliance profile: yes" in digest
    assert "judge_slug 'court'" in digest


def test_list_judges_only_with_rules(fake_api):
    fake_api.queue(FakeResponse(payload=JUDGES))
    result = json_of(run_tool(ListJudgesTool, {"district_id": "edny", "only_with_rules": True}))
    assert [judge["slug"] for judge in result["judges"]] == ["gary-r-brown"]


def test_list_judges_needs_a_court(fake_api):
    with pytest.raises(CourtRulesError, match="district_id"):
        run_tool(ListJudgesTool, {})
    assert fake_api.calls == []


def test_get_judge_rules_layered_answer_for_edny(fake_api):
    payload = {
        "judge": {"slug": "gary-r-brown", "name": "Gary R. Brown"},
        "rules": {
            "frcp": [{"rule_key": "FormatConstraint:caption", "citation": "FRCP 10(a)", "summary": "Every pleading needs a caption.", "severity": "CRITICAL"}],
            "local_rules": [],
            "standing_order": [{"category": "PAGE_LIMIT", "summary": "Support briefs limited to 25 pages", "source": "Brown SO IV.B"}],
        },
        "meta": {"total_rules": 2},
    }
    fake_api.queue(FakeResponse(payload=payload))
    messages = run_tool(
        GetJudgeRulesTool,
        {"district_id": "edny", "judge_slug": "Gary-R-Brown", "document_scope": "brief_support", "motion_type": "Rule_56"},
    )
    assert fake_api.last["url"] == "https://api.courtrules.app/api/v1/rules"
    assert fake_api.last["params"] == {
        "district_id": "edny",
        "judge_slug": "gary-r-brown",
        "document_scope": "brief_support",
        "motion_type": "Rule_56",
    }
    digest = text_of(messages)
    assert "Rules for Gary R. Brown: 2 in total." in digest
    assert "- [FRCP 10(a), CRITICAL] Every pleading needs a caption." in digest
    assert "- [PAGE_LIMIT] Support briefs limited to 25 pages (Brown SO IV.B)" in digest
    assert "Local rules" not in digest
    assert json_of(messages) == payload


def test_get_judge_rules_answer_for_a_state_court(fake_api):
    payload = {
        "judge": {"slug": "il-cook-reilly-eve-m", "name": "Eve M. Reilly", "status": "active"},
        "district_id": "il-cook-circuit",
        "rules": {"court": [EXTRACTED_RULE], "judge": []},
        "meta": {"total_rules": 1, "court_rules": 1, "judge_rules": 0},
    }
    fake_api.queue(FakeResponse(payload=payload))
    messages = run_tool(GetJudgeRulesTool, {"district_id": "il-cook-circuit", "judge_slug": "il-cook-reilly-eve-m"})
    assert fake_api.last["params"] == {"district_id": "il-cook-circuit", "judge_slug": "il-cook-reilly-eve-m"}
    digest = text_of(messages)
    assert "Rules for Eve M. Reilly in il-cook-circuit: 1 in total." in digest
    assert "Court-wide rules (1):" in digest
    assert "[CourtesyCopyRule, WARNING] Courtesy copies are required for motions over ten pages." in digest
    assert "page 3, section II.A" in digest
    assert "https://www.cookcountycourt.org/rules.pdf" in digest


def test_get_judge_rules_shortens_long_groups(fake_api):
    many = [{"category": "FORMAT", "summary": "Rule " + str(number), "source": "SO"} for number in range(40)]
    payload = {"judge": {"slug": "a", "name": "A"}, "rules": {"frcp": [], "local_rules": [], "standing_order": many}, "meta": {"total_rules": 40}}
    fake_api.queue(FakeResponse(payload=payload))
    digest = text_of(run_tool(GetJudgeRulesTool, {"district_id": "edny", "judge_slug": "a"}))
    assert "Standing order (40):" in digest
    assert "- [FORMAT] Rule 14 (SO)" in digest
    assert "Rule 15 (SO)" not in digest
    assert "... 25 more." in digest


def test_search_filing_rules_builds_the_query(fake_api):
    payload = {
        "rules": [EXTRACTED_RULE],
        "meta": {"total": 12, "returned": 1, "limit": 10, "offset": 0, "next_offset": 10, "include_court_rules": True},
    }
    fake_api.queue(FakeResponse(payload=payload))
    messages = run_tool(
        SearchFilingRulesTool,
        {
            "q": "courtesy copy",
            "district_id": "IL-COOK-CIRCUIT",
            "logic_type": "CourtesyCopyRule",
            "case_type": "Small Claims",
            "limit": 10,
            "offset": 0,
        },
    )
    assert fake_api.last["url"] == "https://api.courtrules.app/api/v1/extracted-rules"
    assert fake_api.last["params"] == {
        "q": "courtesy copy",
        "district_id": "il-cook-circuit",
        "include_court_rules": "true",
        "logic_type": "CourtesyCopyRule",
        "case_type": "small_claims",
        "limit": "10",
        "offset": "0",
    }
    digest = text_of(messages)
    assert "Showing 1 of 12 matching rules." in digest
    assert "Call again with offset 10." in digest
    assert json_of(messages) == payload


def test_search_filing_rules_defaults_and_limits(fake_api):
    fake_api.queue(FakeResponse(payload={"rules": [], "meta": {"total": 0}}))
    messages = run_tool(SearchFilingRulesTool, {"q": "x" * 300, "limit": 5000})
    sent = fake_api.last["params"]
    assert len(sent["q"]) == 200
    assert sent["limit"] == "100"
    assert sent["offset"] == "0"
    assert sent["include_court_rules"] == "true"
    assert "No filing rules matched" in text_of(messages)


def test_list_court_holidays(fake_api):
    payload = {
        "holidays": [
            {
                "district_id": "edny",
                "calendar_year": 2026,
                "holiday_date": "2026-01-01",
                "holiday_name": "New Year's Day",
                "source_url": "https://www.nyed.uscourts.gov/holiday-schedule",
                "last_checked_at": "2026-05-13T12:00:00.000Z",
            }
        ],
        "meta": {"total": 1, "district_id": "edny", "year": 2026, "limit": 50},
    }
    fake_api.queue(FakeResponse(payload=payload))
    messages = run_tool(ListCourtHolidaysTool, {"district_id": "edny", "year": 2026.0})
    assert fake_api.last["url"] == "https://api.courtrules.app/api/v1/holidays"
    assert fake_api.last["params"] == {"district_id": "edny", "year": "2026", "limit": "50"}
    digest = text_of(messages)
    assert "- 2026-01-01: New Year's Day (edny)" in digest
    assert "Official schedule: https://www.nyed.uscourts.gov/holiday-schedule" in digest
    assert json_of(messages) == payload


def test_list_court_holidays_with_no_match(fake_api):
    fake_api.queue(FakeResponse(payload={"holidays": [], "meta": {"total": 0}}))
    assert "No court holidays matched" in text_of(run_tool(ListCourtHolidaysTool, {"district_id": "edny", "year": 1999}))


CHECK_ANSWER = {
    "judge": {"slug": "gary-r-brown", "name": "Gary R. Brown"},
    "summary": {"status": "NON_COMPLIANT", "failures": 1, "warnings": 0, "passes": 2, "action_items": 1},
    "results": [
        {"severity": "CRITICAL", "category": "PAGE_LIMIT", "message": "22pp exceeds 20pp limit", "source": "Brown SO IV.B", "status": "FAIL"},
        {"severity": "INFO", "category": "COURTESY_COPY", "message": "Deliver a courtesy copy", "source": "Brown SO V", "status": "ACTION_REQUIRED"},
        {"severity": "INFO", "category": "CAPTION", "message": "Caption present", "source": "FRCP 10(a)", "status": "PASS"},
        {"severity": "INFO", "category": "SIGNATURE", "message": "Signature present", "source": "FRCP 11", "status": "PASS"},
    ],
    "meta": {"checks_run": 4, "checks_skipped": 3},
}


def test_check_document_sends_the_filing_facts(fake_api):
    fake_api.queue(FakeResponse(payload=CHECK_ANSWER))
    messages = run_tool(
        CheckDocumentTool,
        {
            "judge_slug": "gary-r-brown",
            "document_scope": "brief_support",
            "motion_type": "Rule_56",
            "page_count": 22,
            "word_count": 7200.0,
            "filing_role": "movant",
            "pmc_completed": True,
        },
    )
    call = fake_api.last
    assert call["method"] == "POST"
    assert call["url"] == "https://api.courtrules.app/api/v1/check"
    assert call["json"] == {
        "judge_slug": "gary-r-brown",
        "district_id": "edny",
        "document_scope": "brief_support",
        "is_pro_se": False,
        "pmc_completed": True,
        "opposing_party_pro_se": False,
        "filing_role": "movant",
        "document": {"page_count": 22, "word_count": 7200},
        "motion_type": "Rule_56",
    }
    digest = text_of(messages)
    assert "Compliance check for Gary R. Brown: NON_COMPLIANT. 1 failures, 0 warnings, 2 passes, 1 action items" in digest
    assert "- FAIL [CRITICAL] PAGE_LIMIT: 22pp exceeds 20pp limit (Brown SO IV.B)" in digest
    assert "- ACTION_REQUIRED [INFO] COURTESY_COPY: Deliver a courtesy copy (Brown SO V)" in digest
    assert "2 checks passed." in digest
    assert "Caption present" not in digest
    assert json_of(messages) == CHECK_ANSWER


def test_check_document_rejects_bad_input_before_calling_the_api(fake_api):
    base = {"judge_slug": "gary-r-brown", "document_scope": "brief_support", "page_count": 10, "word_count": 100}
    with pytest.raises(CourtRulesError, match="page_count"):
        run_tool(CheckDocumentTool, {**base, "page_count": None})
    with pytest.raises(CourtRulesError, match="word_count"):
        run_tool(CheckDocumentTool, {**base, "word_count": -5})
    with pytest.raises(CourtRulesError, match="filing_role"):
        run_tool(CheckDocumentTool, {**base, "filing_role": "judge"})
    with pytest.raises(CourtRulesError, match="judge_slug"):
        run_tool(CheckDocumentTool, {**base, "judge_slug": ""})
    assert fake_api.calls == []


def test_a_court_without_checks_reports_the_api_message(fake_api):
    fake_api.queue(
        FakeResponse(
            status_code=422,
            payload={
                "error": "Compliance checks are not available for Superior Court of California, County of Los Angeles yet.",
                "suggestion": "Read the judge's rules with GET /api/v1/rules.",
            },
        )
    )
    with pytest.raises(CourtRulesError, match="not available for Superior Court"):
        run_tool(
            CheckDocumentTool,
            {
                "judge_slug": "x",
                "district_id": "ca-los-angeles-superior",
                "document_scope": "letter",
                "page_count": 1,
                "word_count": 10,
            },
        )


def test_every_tool_needs_a_key(fake_api):
    for tool_class, parameters in (
        (ListCourtsTool, {}),
        (ListJudgesTool, {"district_id": "edny"}),
        (GetJudgeRulesTool, {"district_id": "edny", "judge_slug": "a"}),
        (SearchFilingRulesTool, {}),
        (ListCourtHolidaysTool, {}),
        (CheckDocumentTool, {"judge_slug": "a", "document_scope": "letter", "page_count": 1, "word_count": 1}),
    ):
        with pytest.raises(CourtRulesError, match="API key"):
            run_tool(tool_class, parameters, api_key="")
    assert fake_api.calls == []


def test_tools_survive_unexpected_response_shapes(fake_api):
    for tool_class, parameters in (
        (ListCourtsTool, {}),
        (ListJudgesTool, {"district_id": "edny"}),
        (GetJudgeRulesTool, {"district_id": "edny", "judge_slug": "a"}),
        (SearchFilingRulesTool, {}),
        (ListCourtHolidaysTool, {}),
        (CheckDocumentTool, {"judge_slug": "a", "document_scope": "letter", "page_count": 1, "word_count": 1}),
    ):
        fake_api.queue(FakeResponse(payload={"unexpected": True}))
        messages = run_tool(tool_class, parameters)
        assert len(messages) == 2


def test_the_public_invoke_path_works_like_the_private_one(fake_api):
    fake_api.queue(FakeResponse(payload=COURTS))
    tool = ListCourtsTool.from_credentials({"api_key": "k"})
    messages = list(tool.invoke({"query": "new york", "status": "any"}))
    assert len(messages) == 2
    assert len(json_of(messages)["courts"]) == 2
