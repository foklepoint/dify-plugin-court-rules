from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from court_rules_api import bool_param, call_api, int_param, text_param
from court_rules_text import as_dict, as_list, extracted_rule_line

DEFAULT_LIMIT = 10
MAX_LIMIT = 100
MAX_QUERY_LENGTH = 200


def case_type_value(parameters: dict[str, Any]) -> str:
    """The API lists case types in lowercase with underscores, such as small_claims."""
    text = text_param(parameters, "case_type", lowercase=True)
    return text.replace(" ", "_").replace("-", "_")


class SearchFilingRulesTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        params = {
            "q": text_param(tool_parameters, "q")[:MAX_QUERY_LENGTH],
            "district_id": text_param(tool_parameters, "district_id", lowercase=True),
            "judge_slug": text_param(tool_parameters, "judge_slug", lowercase=True),
            "include_court_rules": bool_param(tool_parameters, "include_court_rules", True),
            "logic_type": text_param(tool_parameters, "logic_type"),
            "workflow_phase": text_param(tool_parameters, "workflow_phase"),
            "case_type": case_type_value(tool_parameters),
            "limit": int_param(tool_parameters, "limit", DEFAULT_LIMIT, 1, MAX_LIMIT),
            "offset": int_param(tool_parameters, "offset", 0, 0, 1000000),
        }
        result = call_api(self.runtime.credentials, "GET", "/api/v1/extracted-rules", params=params)

        rules = as_list(result.get("rules"))
        meta = as_dict(result.get("meta"))
        if len(rules) == 0:
            digest = "No filing rules matched. Try fewer filters or different words."
        else:
            lines = ["Showing " + str(len(rules)) + " of " + str(meta.get("total", len(rules))) + " matching rules."]
            for rule in rules:
                lines.append(extracted_rule_line(rule))
            if meta.get("next_offset") is not None:
                lines.append("More rules are available. Call again with offset " + str(meta["next_offset"]) + ".")
            digest = "\n".join(lines)
        yield self.create_text_message(digest)
        yield self.create_json_message(result)
