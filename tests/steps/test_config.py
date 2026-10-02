import re
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
