from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from court_rules_api import call_api, required_text_param, text_param
from court_rules_text import DIGEST_ROW_LIMIT, as_dict, as_list, extracted_rule_line, more_note, shorten

SEARCH_HINT = "The JSON output has all of them. Search Filing Rules can narrow by topic."


def layered_rule_line(rule: Any) -> str:
    """A rule from the FRCP or local-rules layer of a court with a compliance profile."""
    rule = as_dict(rule)
    label = str(rule.get("citation") or rule.get("label") or rule.get("rule_key") or "rule")
    severity = str(rule.get("severity") or "")
    tag = label
    if severity != "":
        tag = label + ", " + severity
    return "- [" + tag + "] " + shorten(rule.get("summary"))


def standing_order_line(rule: Any) -> str:
    rule = as_dict(rule)
    return (
        "- ["
        + str(rule.get("category") or "rule")
        + "] "
        + shorten(rule.get("summary"))
        + " ("
        + str(rule.get("source") or "standing order")
        + ")"
    )


def group_lines(title: str, rules: list[Any], line_function: Any) -> list[str]:
    if len(rules) == 0:
        return []
    lines = [title + " (" + str(len(rules)) + "):"]
    for rule in rules[:DIGEST_ROW_LIMIT]:
        lines.append(line_function(rule))
    note = more_note(DIGEST_ROW_LIMIT, len(rules), SEARCH_HINT)
    if note != "":
        lines.append(note)
    return lines


def rules_digest(result: dict[str, Any]) -> str:
    judge = as_dict(result.get("judge"))
    rules = as_dict(result.get("rules"))
    meta = as_dict(result.get("meta"))
    heading = "Rules for " + str(judge.get("name") or judge.get("slug") or "the judge")
    if result.get("district_id"):
        heading = heading + " in " + str(result["district_id"])
    heading = heading + ": " + str(meta.get("total_rules", 0)) + " in total."

    lines = [heading]
    if "frcp" in rules or "local_rules" in rules or "standing_order" in rules:
        lines.extend(group_lines("Federal Rules of Civil Procedure", as_list(rules.get("frcp")), layered_rule_line))
        lines.extend(group_lines("Local rules", as_list(rules.get("local_rules")), layered_rule_line))
        lines.extend(group_lines("Standing order", as_list(rules.get("standing_order")), standing_order_line))
    else:
        lines.extend(group_lines("Court-wide rules", as_list(rules.get("court")), extracted_rule_line))
        lines.extend(group_lines("Judge rules", as_list(rules.get("judge")), extracted_rule_line))
    if len(lines) == 1:
        lines.append("No rules were returned for this judge.")
    return "\n".join(lines)


class GetJudgeRulesTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        params = {
            "district_id": required_text_param(tool_parameters, "district_id", lowercase=True),
            "judge_slug": required_text_param(tool_parameters, "judge_slug", lowercase=True),
            "document_scope": text_param(tool_parameters, "document_scope"),
            "motion_type": text_param(tool_parameters, "motion_type"),
        }
        result = call_api(self.runtime.credentials, "GET", "/api/v1/rules", params=params)
        yield self.create_text_message(rules_digest(result))
        yield self.create_json_message(result)
