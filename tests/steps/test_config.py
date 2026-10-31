import json
import re
import shlex
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from cyclix import config

EXAMPLE = Path(__file__).resolve().parents[2] / "docs" / "examples" / "tenant.toml"

scenarios("config.feature")


@pytest.fixture
def config_file(tmp_path):
    path = tmp_path / "tenant.toml"
    path.write_text(EXAMPLE.read_text())
    return path


def edit_table(path, table, change):
    """Apply change(lines) to the lines of one table in a TOML file."""
    text = path.read_text()
    header = f"[{table}]"
    lines = text.splitlines()
    start = next(i for i, line in enumerate(lines) if line.split("#")[0].strip() == header)
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("[")), len(lines))
    lines[start + 1 : end] = change(lines[start + 1 : end])
    path.write_text("\n".join(lines) + "\n")


@given("the example tenant config")
def example_config(config_file):
    pass


@given(parsers.re(r'the example config without "(?P<key>\w+)" under \[(?P<table>[\w.]+)\]'))
def example_without(config_file, key, table):
    edit_table(
        config_file, table, lambda lines: [l for l in lines if not re.match(rf"{key}\s*=", l)]
    )


@given(parsers.re(r'the example config with "(?P<line>[^"]+)" under \[(?P<table>[\w.]+)\]'))
def example_with(config_file, line, table):
    edit_table(config_file, table, lambda lines: [line, *lines])


@given(
    parsers.re(
        r'the example config with "(?P<key>\w+)" set to (?P<value>.+) under \[(?P<table>[\w.]+)\]'
    )
)
def example_setting(config_file, key, value, table):
    edit_table(config_file, table, lambda lines: set_key(lines, key, value))


def set_key(lines, key, value):
    """Replace one key's value, including the lines a list spread over several lines takes."""
    start = next(i for i, line in enumerate(lines) if line.startswith(f"{key} ="))
    end = start + 1
    while (taken := "".join(lines[start:end])).count("[") > taken.count("]"):
        end += 1
    return [*lines[:start], f"{key} = {value}", *lines[end:]]


@given(parsers.parse('the example config with the agent command "{command}"'))
def example_with_command(config_file, command):
    line = f"command = {json.dumps(shlex.split(command))}"
    edit_table(
        config_file, "agent",
        lambda lines: [line if l.startswith("command =") else l for l in lines],
    )  # fmt: skip


@given(parsers.parse('CYCLIX_CONFIG points at a config for tenant "{name}"'))
def env_points_at(config_file, monkeypatch, name):
    edit_table(config_file, "tenant", lambda lines: [f'name = "{name}"'])
    monkeypatch.setenv("CYCLIX_CONFIG", str(config_file))


@when("the config is loaded", target_fixture="loaded")
def load_config(config_file):
    return attempt(lambda: config.load(config_file))


@when("the config is loaded with no path", target_fixture="loaded")
def load_config_from_env():
    return attempt(config.load)


def attempt(load):
    try:
        return load()
    except config.ConfigError as error:
        return error


@then(parsers.parse('the tenant is "{name}"'))
def tenant_is(loaded, name):
    assert loaded.tenant.name == name, loaded


@then(parsers.parse('the version starts with "{prefix}"'))
def version_starts(loaded, prefix):
    assert loaded.version.startswith(prefix)


@then(parsers.parse("it fails with '{message}'"))
def fails_with(loaded, message):
    assert isinstance(loaded, config.ConfigError), loaded
    assert str(loaded) == message


@then(
    parsers.parse(
        'the plan stage uses "{model}" with {turns:d} turns, a budget of {budget:g} '
        'and the tools "{tools}"'
    )
)
def plan_stage_uses(loaded, model, turns, budget, tools):
    plan = loaded.agent.plan
    assert (plan.model, plan.max_turns, plan.max_budget_usd) == (model, turns, budget)
    assert plan.tools == tuple(tools.split())


@then(parsers.parse('the agent command is "{command}"'))
def agent_command_is(loaded, command):
    assert not isinstance(loaded, Exception), loaded
    assert loaded.agent.command == tuple(shlex.split(command))


@pytest.fixture
def home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    return home


@pytest.fixture
def named():
    """The instruction folder a scenario names, as written in the config."""
    return {}


def name_folder(config_file, folder):
    edit_table(config_file, "agent", lambda lines: [f"instructions = {json.dumps(folder)}", *lines])


@given(parsers.parse('a folder "{name}" in the home folder holding "{path}"'))
def home_folder(home, name, path):
    (home / name).mkdir()
    (home / name / path).write_text("The rules.\n")


@given(parsers.parse('the example config names the instruction folder "{folder}"'))
def example_names_folder(config_file, folder):
    name_folder(config_file, folder)


@given(parsers.parse("the example config names {kind} as its instruction folder"))
def example_names_bad_folder(config_file, tmp_path, named, kind):
    if kind == "a missing folder":
        folder = str(tmp_path / "no-such-folder")
    elif kind == "a file":
        folder = str(config_file)
    else:
        assert kind == "a relative path", kind
        folder = "instructions"
    named["folder"] = folder
    name_folder(config_file, folder)


@then("it names no instruction folder")
def no_instruction_folder(loaded):
    assert loaded.agent.instructions is None


@then(parsers.parse('the instruction folder is "{name}" in the home folder'))
def instruction_folder_is(loaded, home, name):
    assert loaded.agent.instructions.folder == home / name, loaded


@then(parsers.parse("it fails with '{message}' about that folder"))
def fails_about_folder(loaded, named, message):
    fails_with(loaded, message.replace("<folder>", named["folder"]))
