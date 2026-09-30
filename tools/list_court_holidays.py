from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from court_rules_api import call_api, int_param, optional_int_param, text_param
from court_rules_text import as_dict, as_list

DEFAULT_LIMIT = 50
MAX_LIMIT = 500


def holiday_line(holiday: Any) -> str:
    holiday = as_dict(holiday)
    return (
        "- "
        + str(holiday.get("holiday_date") or "")
        + ": "
        + str(holiday.get("holiday_name") or "")
        + " ("
        + str(holiday.get("district_id") or "")
        + ")"
    )


class ListCourtHolidaysTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        params = {
            "district_id": text_param(tool_parameters, "district_id", lowercase=True),
            "year": optional_int_param(tool_parameters, "year"),
            "date_from": text_param(tool_parameters, "date_from"),
            "date_to": text_param(tool_parameters, "date_to"),
            "limit": int_param(tool_parameters, "limit", DEFAULT_LIMIT, 1, MAX_LIMIT),
        }
        result = call_api(self.runtime.credentials, "GET", "/api/v1/holidays", params=params)

        holidays = as_list(result.get("holidays"))
        if len(holidays) == 0:
            digest = "No court holidays matched. Check the court id with the List Courts tool."
        else:
            lines = [str(len(holidays)) + " court holidays. Each line ends with the court id."]
            for holiday in holidays:
                lines.append(holiday_line(holiday))
            first = as_dict(holidays[0])
            if first.get("source_url"):
                lines.append("Official schedule: " + str(first["source_url"]))
            digest = "\n".join(lines)
        yield self.create_text_message(digest)
        yield self.create_json_message(result)
