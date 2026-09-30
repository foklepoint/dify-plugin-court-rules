"""Client for the Court Rules REST API (https://docs.courtrules.app).

Every request goes to one fixed host. The API key travels only in the Authorization header.
"""

from typing import Any

import requests

API_BASE_URL = "https://api.courtrules.app"
REQUEST_TIMEOUT_SECONDS = 30
USER_AGENT = "dify-plugin-court-rules/0.0.1"
KEY_HELP = "Check the API key in the plugin credentials."
MAX_ERROR_LENGTH = 600


class CourtRulesError(Exception):
    """A Court Rules call failed. The message is safe to show to the user."""


def clean_params(params: dict[str, Any] | None) -> dict[str, str]:
    """Drop empty values and turn everything else into the strings the API expects."""
    cleaned: dict[str, str] = {}
    if not params:
        return cleaned
    for name, value in params.items():
        if value is None:
            continue
        if isinstance(value, bool):
            cleaned[name] = "true" if value else "false"
            continue
        text = str(value).strip()
        if text == "":
            continue
        cleaned[name] = text
    return cleaned


def describe_error(response: requests.Response) -> str:
    status = response.status_code
    message = ""
    suggestion = ""
    details = ""
    try:
        payload = response.json()
    except ValueError:
        payload = None
    if isinstance(payload, dict):
        message = str(payload.get("error") or "")
        suggestion = str(payload.get("suggestion") or "")
        items = payload.get("details")
        if isinstance(items, list):
            pieces = []
            for item in items:
                if isinstance(item, dict):
                    pieces.append(str(item.get("path", "")) + ": " + str(item.get("message", "")))
            details = "; ".join(pieces)
    if message == "":
        message = response.reason or "request failed"

    parts = ["Court Rules API error " + str(status) + ": " + message.rstrip(".") + "."]
    if details != "":
        parts.append("Details: " + details + ".")
    if suggestion != "":
        parts.append(suggestion)
    if status in (401, 403):
        parts.append(KEY_HELP)
    if status == 429:
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            parts.append("Retry after " + str(retry_after) + " seconds.")
    return " ".join(parts)[:MAX_ERROR_LENGTH]


def call_api(
    credentials: dict[str, Any],
    method: str,
    path: str,
    params: dict[str, Any] | None = None,
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Call one Court Rules endpoint with the plugin credentials and return the decoded JSON object."""
    api_key = str(credentials.get("api_key") or "").strip()
    if api_key == "":
        raise CourtRulesError("No Court Rules API key is set. Add one in the plugin credentials.")
    headers = {
        "Authorization": "Bearer " + api_key,
        "Accept": "application/json",
        "User-Agent": USER_AGENT,
    }
    try:
        response = requests.request(
            method,
            API_BASE_URL + path,
            params=clean_params(params),
            json=body,
            headers=headers,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except requests.exceptions.Timeout:
        raise CourtRulesError(
            "The Court Rules API did not answer within " + str(REQUEST_TIMEOUT_SECONDS) + " seconds."
        ) from None
    except requests.exceptions.RequestException as error:
        raise CourtRulesError("Could not reach the Court Rules API (" + type(error).__name__ + ").") from None

    if response.status_code >= 400:
        raise CourtRulesError(describe_error(response))
    try:
        payload = response.json()
    except ValueError:
        raise CourtRulesError("The Court Rules API returned a response that is not JSON.") from None
    if not isinstance(payload, dict):
        raise CourtRulesError("The Court Rules API returned an unexpected response.")
    return payload


def text_param(parameters: dict[str, Any], name: str, lowercase: bool = False) -> str:
    value = parameters.get(name)
    if value is None:
        return ""
    text = str(value).strip()
    if lowercase:
        return text.lower()
    return text


def required_text_param(parameters: dict[str, Any], name: str, lowercase: bool = False) -> str:
    text = text_param(parameters, name, lowercase)
    if text == "":
        raise CourtRulesError("The " + name + " parameter is required.")
    return text


def int_param(parameters: dict[str, Any], name: str, default: int, minimum: int, maximum: int) -> int:
    """Read a whole number, fall back to the default when it is empty, and keep it in range."""
    value = parameters.get(name)
    if value is None or value == "":
        return default
    try:
        number = int(float(value))
    except (TypeError, ValueError):
        raise CourtRulesError("The " + name + " parameter must be a number.") from None
    if number < minimum:
        return minimum
    if number > maximum:
        return maximum
    return number


def required_int_param(parameters: dict[str, Any], name: str, minimum: int) -> int:
    value = parameters.get(name)
    if value is None or value == "":
        raise CourtRulesError("The " + name + " parameter is required.")
    try:
        number = int(float(value))
    except (TypeError, ValueError):
        raise CourtRulesError("The " + name + " parameter must be a number.") from None
    if number < minimum:
        raise CourtRulesError("The " + name + " parameter must be at least " + str(minimum) + ".")
    return number


def optional_int_param(parameters: dict[str, Any], name: str) -> int | None:
    value = parameters.get(name)
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        raise CourtRulesError("The " + name + " parameter must be a number.") from None


def bool_param(parameters: dict[str, Any], name: str, default: bool) -> bool:
    value = parameters.get(name)
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in ("true", "1", "yes", "y"):
        return True
    if text in ("false", "0", "no", "n"):
        return False
    raise CourtRulesError("The " + name + " parameter must be true or false.")
