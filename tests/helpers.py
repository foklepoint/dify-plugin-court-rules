class FakeResponse:
    def __init__(self, status_code=200, payload=None, headers=None, reason="OK"):
        self.status_code = status_code
        self._payload = payload
        self.headers = headers or {}
        self.reason = reason

    def json(self):
        if self._payload is None:
            raise ValueError("not json")
        return self._payload


class FakeApi:
    """Stands in for requests.request. It records every call and plays back queued answers."""

    def __init__(self):
        self.calls = []
        self.queued = []

    def queue(self, answer):
        self.queued.append(answer)

    def __call__(self, method, url, params=None, json=None, headers=None, timeout=None):
        self.calls.append(
            {"method": method, "url": url, "params": params, "json": json, "headers": headers, "timeout": timeout}
        )
        answer = self.queued.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer

    @property
    def last(self):
        return self.calls[-1]


def run_tool(tool_class, parameters, api_key="test-key"):
    """Run a tool the way Dify does, without a Dify session, and return its messages."""
    tool = tool_class.from_credentials({"api_key": api_key})
    return list(tool._invoke(parameters))


def text_of(messages):
    lines = []
    for message in messages:
        if message.type.value == "text":
            lines.append(message.message.text)
    return "\n".join(lines)


def json_of(messages):
    for message in messages:
        if message.type.value == "json":
            return message.message.json_object
    raise AssertionError("no json message")
