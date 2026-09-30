from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from court_rules_api import call_api, int_param, text_param
from court_rules_text import as_dict, as_list, court_line

DEFAULT_LIMIT = 25
MAX_LIMIT = 200


def court_matches(court: Any, words: list[str], state: str, status: str) -> bool:
    court = as_dict(court)
    if status != "any" and court.get("status") != status:
        return False
    if state != "" and state not in str(court.get("state") or "").lower():
        return False
    name_and_id = (str(court.get("name") or "") + " " + str(court.get("district_id") or "")).lower()
    for word in words:
        if word not in name_and_id:
            return False
    return True


class ListCourtsTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        words = text_param(tool_parameters, "query", lowercase=True).split()
        state = text_param(tool_parameters, "state", lowercase=True)
        status = text_param(tool_parameters, "status", lowercase=True) or "live"
        limit = int_param(tool_parameters, "limit", DEFAULT_LIMIT, 1, MAX_LIMIT)

        payload = call_api(self.runtime.credentials, "GET", "/api/v1/courts")
        meta = as_dict(payload.get("meta"))
        matched = []
        for court in as_list(payload.get("courts")):
            if court_matches(court, words, state, status):
                matched.append(court)
        shown = matched[:limit]

        result = {
            "courts": shown,
            "meta": {
                "matched": len(matched),
                "returned": len(shown),
                "total_districts": meta.get("total_districts"),
                "districts_with_data": meta.get("districts_with_data"),
            },
        }
        if len(shown) == 0:
            digest = "No courts matched. Use a shorter query, drop the state filter, or set status to any."
        else:
            lines = [
                "Showing " + str(len(shown)) + " of " + str(len(matched)) + " matching courts. "
                "Pass district_id to the other Court Rules tools."
            ]
            for court in shown:
                lines.append(court_line(court))
            digest = "\n".join(lines)
        yield self.create_text_message(digest)
        yield self.create_json_message(result)
