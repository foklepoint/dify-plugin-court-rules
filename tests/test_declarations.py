import os
import re
from pathlib import Path

import pytest
import yaml
from dify_plugin.config.config import DifyPluginEnv
from dify_plugin.core.plugin_registration import PluginRegistration

ROOT = Path(__file__).resolve().parent.parent
TOOL_NAMES = [
    "list_courts",
    "list_judges",
    "get_judge_rules",
    "search_filing_rules",
    "list_court_holidays",
    "check_document",
]


@pytest.fixture(scope="module")
def registration():
    """Load the plugin the way the Dify daemon does: manifest, provider, tool YAML and Python classes."""
    previous = Path.cwd()
    os.chdir(ROOT)
    try:
        yield PluginRegistration(DifyPluginEnv())
    finally:
        os.chdir(previous)


def test_the_plugin_loads_with_one_provider_and_six_tools(registration):
    assert registration.configuration.name == "court_rules"
    assert registration.configuration.author == "foklepoint"
    provider, provider_class, tools = registration.tools_mapping["court_rules"]
    assert provider_class.__name__ == "CourtRulesProvider"
    assert sorted(tools.keys()) == sorted(TOOL_NAMES)


def test_the_provider_asks_for_one_secret_api_key(registration):
    provider, _, _ = registration.tools_mapping["court_rules"]
    assert [credential.name for credential in provider.credentials_schema] == ["api_key"]
    assert provider.credentials_schema[0].required is True
    assert provider.credentials_schema[0].type.value == "secret-input"


def test_the_icons_named_in_the_manifest_exist():
    manifest = yaml.safe_load((ROOT / "manifest.yaml").read_text())
    assert (ROOT / "_assets" / manifest["icon"]).is_file()
    assert (ROOT / "_assets" / manifest["icon_dark"]).is_file()
    assert (ROOT / manifest["privacy"]).is_file()


def test_the_manifest_declares_only_the_court_rules_host():
    manifest = yaml.safe_load((ROOT / "manifest.yaml").read_text())
    assert manifest["network"]["domains"] == ["api.courtrules.app"]


@pytest.mark.parametrize("tool_name", TOOL_NAMES)
def test_yaml_parameters_match_the_parameters_the_code_reads(tool_name):
    declaration = yaml.safe_load((ROOT / "tools" / (tool_name + ".yaml")).read_text())
    declared = set()
    for parameter in declaration["parameters"]:
        declared.add(parameter["name"])
    source = (ROOT / "tools" / (tool_name + ".py")).read_text()
    used = set(re.findall(r'(?:tool_parameters|parameters), "([a-z_0-9]+)"', source))
    assert declared == used


@pytest.mark.parametrize("tool_name", TOOL_NAMES)
def test_every_parameter_has_a_description_for_people_and_for_the_model(tool_name):
    declaration = yaml.safe_load((ROOT / "tools" / (tool_name + ".yaml")).read_text())
    for parameter in declaration["parameters"]:
        assert parameter["human_description"]["en_US"].strip() != ""
        assert parameter["llm_description"].strip() != ""
        assert parameter["form"] == "llm"


def test_select_defaults_are_valid_options():
    for tool_name in TOOL_NAMES:
        declaration = yaml.safe_load((ROOT / "tools" / (tool_name + ".yaml")).read_text())
        for parameter in declaration["parameters"]:
            if parameter["type"] != "select":
                continue
            values = [option["value"] for option in parameter["options"]]
            if "default" in parameter:
                assert parameter["default"] in values


def has_cjk(text):
    for character in text:
        if 0x4E00 <= ord(character) <= 0x9FFF:
            return True
    return False


def test_readme_and_privacy_are_english_only():
    for name in ("README.md", "PRIVACY.md"):
        text = (ROOT / name).read_text()
        assert has_cjk(text) is False
        assert "Please fill in" not in text
