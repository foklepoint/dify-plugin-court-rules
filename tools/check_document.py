from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from court_rules_api import (
    CourtRulesError,
    bool_param,
    call_api,
    required_int_param,
    required_text_param,
    text_param,
)
from court_rules_text import as_dict, as_list, shorten

FILING_ROLES = ("movant", "opponent", "reply")


def result_line(result: Any) -> str:
    result = as_dict(result)
    return (
        "- "
        + str(result.get("status") or "")
        + " ["
        + str(result.get("severity") or "")
        + "] "
        + str(result.get("category") or "")
        + ": "
        + shorten(result.get("message"))
        + " ("
        + str(result.get("source") or "")
        + ")"
    )


def check_digest(result: dict[str, Any]) -> str:
    judge = as_dict(result.get("judge"))
    summary = as_dict(result.get("summary"))
    meta = as_dict(result.get("meta"))
    lines = [
        "Compliance check for "
        + str(judge.get("name") or judge.get("slug") or "the judge")
        + ": "
        + str(summary.get("status") or "unknown")
        + ". "
        + str(summary.get("failures", 0))
        + " failures, "
        + str(summary.get("warnings", 0))
        + " warnings, "
        + str(summary.get("passes", 0))
        + " passes, "
        + str(summary.get("action_items", 0))
        + " action items ("
        + str(meta.get("checks_run", 0))
        + " checks run, "
        + str(meta.get("checks_skipped", 0))
        + " skipped)."
    ]
    passed = 0
    for item in as_list(result.get("results")):
        if as_dict(item).get("status") == "PASS":
            passed = passed + 1
            continue
        lines.append(result_line(item))
    if passed > 0:
        lines.append(str(passed) + " checks passed. The JSON output lists them.")
    for warning in as_list(result.get("warnings")):
        lines.append("Note: " + shorten(warning))
    return "\n".join(lines)


class CheckDocumentTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        filing_role = text_param(tool_parameters, "filing_role", lowercase=True) or "movant"
        if filing_role not in FILING_ROLES:
            raise CourtRulesError("The filing_role parameter must be movant, opponent or reply.")
        body: dict[str, Any] = {
            "judge_slug": required_text_param(tool_parameters, "judge_slug", lowercase=True),
            "district_id": text_param(tool_parameters, "district_id", lowercase=True) or "edny",
            "document_scope": required_text_param(tool_parameters, "document_scope"),
            "is_pro_se": bool_param(tool_parameters, "is_pro_se", False),
            "pmc_completed": bool_param(tool_parameters, "pmc_completed", False),
            "opposing_party_pro_se": bool_param(tool_parameters, "opposing_party_pro_se", False),
            "filing_role": filing_role,
            "document": {
                "page_count": required_int_param(tool_parameters, "page_count", 0),
                "word_count": required_int_param(tool_parameters, "word_count", 0),
            },
        }
        motion_type = text_param(tool_parameters, "motion_type")
        if motion_type != "":
            body["motion_type"] = motion_type

        result = call_api(self.runtime.credentials, "POST", "/api/v1/check", body=body)
        yield self.create_text_message(check_digest(result))
        yield self.create_json_message(result)
