from typing import Any

from dify_plugin import ToolProvider
from dify_plugin.errors.tool import ToolProviderCredentialValidationError

from court_rules_api import CourtRulesError, call_api


class CourtRulesProvider(ToolProvider):
    def _validate_credentials(self, credentials: dict[str, Any]) -> None:
        """Read one court. A wrong or missing key is answered with 401 or 403."""
        try:
            call_api(credentials, "GET", "/api/v1/courts/edny")
        except CourtRulesError as error:
            raise ToolProviderCredentialValidationError(str(error)) from error
