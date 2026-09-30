from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from court_rules_api import bool_param, call_api, get_api_key, int_param, required_text_param, text_param
from court_rules_text import as_dict, as_list

DEFAULT_LIMIT = 50
MAX_LIMIT = 500


def judge_line(judge: Any) -> str:
    judge = as_dict(judge)
    kind = str(judge.get("judge_type") or "judge")
    rules = "yes" if judge.get("has_rules") else "no"
    profile = "yes" if judge.get("has_profile") else "no"
    return (
        "- "
        + str(judge.get("slug") or "")
        + ": "
        + str(judge.get("name") or "")
        + " ("
        + kind
        + "), own rules: "
        + rules
        + ", compliance profile: "
        + profile
    )


class ListJudgesTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        api_key = get_api_key(self.runtime.credentials)
        district_id = required_text_param(tool_parameters, "district_id", lowercase=True)
        words = text_param(tool_parameters, "name", lowercase=True).split()
        only_with_rules = bool_param(tool_parameters, "only_with_rules", False)
        limit = int_param(tool_parameters, "limit", DEFAULT_LIMIT, 1, MAX_LIMIT)

        payload = call_api(api_key, "GET", "/api/v1/judges", params={"district_id": district_id})
        meta = as_dict(payload.get("meta"))
        matched = []
        for judge in as_list(payload.get("judges")):
            judge = as_dict(judge)
            if only_with_rules and not judge.get("has_rules"):
                continue
            name = str(judge.get("name") or "").lower()
            if all(word in name for word in words):
                matched.append(judge)
        shown = matched[:limit]

        result = {
            "district_id": payload.get("district_id", district_id),
            "judges": shown,
            "meta": {
                "matched": len(matched),
                "returned": len(shown),
                "total": meta.get("total"),
                "with_rules": meta.get("with_rules"),
                "profiled": meta.get("profiled"),
                "court_level_rules": meta.get("court_level_rules"),
            },
        }
        if len(shown) == 0:
            digest = "No judges matched in " + district_id + ". Check the court id with the List Courts tool."
        else:
            lines = [
                "Showing " + str(len(shown)) + " of " + str(len(matched)) + " matching judges in " + district_id + ". "
                "Pass the slug as judge_slug to Get Judge Rules or Search Filing Rules."
            ]
            for judge in shown:
                lines.append(judge_line(judge))
            if meta.get("court_level_rules"):
                lines.append("This court also has court-wide rules under judge_slug 'court'.")
            digest = "\n".join(lines)
        yield self.create_text_message(digest)
        yield self.create_json_message(result)
