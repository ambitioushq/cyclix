import re
from pathlib import Path

import pytest
from fakes.world import World

from cyclix import config

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "docs" / "examples" / "tenant.toml"


# Everything under [limits] in the example, [limits.wip] included, so the table is gone.
LIMITS_SECTION = EXAMPLE.read_text()[EXAMPLE.read_text().index("[limits]") :]


def write(tmp_path, text):
    path = tmp_path / "tenant.toml"
    path.write_text(text)
    return path


def fails(tmp_path, text):
    with pytest.raises(config.ConfigError) as error:
        config.load(write(tmp_path, text))
    return str(error.value)


def example():
    return EXAMPLE.read_text()


def test_the_example_matches_the_design_doc():
    design = (ROOT / "docs" / "design" / "iteration-0.md").read_text()
    section = design.split("## The config file")[1]
    block = re.search(r"```toml\n(.*?)```", section, re.DOTALL)[1]
    assert block == example()


def test_the_example_loads_in_full(monkeypatch):
    monkeypatch.setenv("CYCLIX_STATE_DIR", "/state")
    loaded = config.load(EXAMPLE)
    assert loaded.tracker.project == 1
    assert loaded.tracker.states.needs_decision == "Needs decision"
    assert loaded.agent.command == ("claude", "-p", "--output-format", "json")
    assert loaded.agent.build.tools[-1] == "Bash(uv run *)"
    assert loaded.gate.commands[2] == ("uv", "run", "pytest", "-q")
    assert loaded.limits.runs_per_day == 6
    assert loaded.state_dir == Path("/state")


def test_the_test_world_config_loads(tmp_path):
    assert config.load(World(tmp_path).create().config).tenant.name == "test"


def test_the_version_changes_with_the_file(tmp_path):
    first = config.load(write(tmp_path, example())).version
    second = config.load(write(tmp_path, example() + "\n")).version
    assert first != second


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        ('owner = "ambitioushq"\n', "", 'config: [tracker] is missing "owner"'),
        (LIMITS_SECTION, "", "config: missing table [limits]"),
        ("[limits]", "[limits.extra]\n[limits]", "config: unknown table [limits.extra]"),
        ("[tenant]", "[other]\n[tenant]", "config: unknown table [other]"),
        ('kind = "github"\nowner', 'kind = "jira"\nowner', 'config: [tracker] kind must be "github", not "jira"'),
        ('kind = "github"\nrepo', 'kind = "gitlab"\nrepo', 'config: [codehost] kind must be "github", not "gitlab"'),
        ("project = 1", 'project = "1"', 'config: [tracker] "project" must be a whole number'),
        ("project = 1", "project = true", 'config: [tracker] "project" must be a whole number'),
        ('name = "cyclix"', "name = 5", 'config: [tenant] "name" must be a string'),
        ("runs_per_day = 6", "runs_per_day = 6\nrun_per_day = 6", 'config: unknown key "run_per_day" in [limits]'),
    ],
)  # fmt: skip
def test_bad_keys_are_named(tmp_path, old, new, message):
    assert old in example()
    assert fails(tmp_path, example().replace(old, new, 1)) == message


@pytest.mark.parametrize(
    ("commands", "message"),
    [
        ("[]", 'config: [gate] "commands" must list at least one command'),
        ("[[]]", 'config: [gate] "commands" must hold commands, each a non-empty list of strings'),
        (
            '["ruff"]',
            'config: [gate] "commands" must hold commands, each a non-empty list of strings',
        ),
    ],
)
def test_gate_commands_must_be_commands(tmp_path, commands, message):
    text = re.sub(r"commands = .*", f"commands = {commands}", example())
    assert fails(tmp_path, text) == message


def test_the_agent_command_must_not_be_empty(tmp_path):
    text = re.sub(r"command = .*", "command = []", example())
    assert fails(tmp_path, text) == 'config: [agent] "command" must be a non-empty list of strings'


def test_states_must_be_a_table(tmp_path):
    text = example().split("[tracker.states]")
    text = text[0].replace('status_field = "Status"', 'status_field = "Status"\nstates = 1')
    assert fails(tmp_path, text) == "config: tracker.states must be a table"


def test_invalid_toml_is_reported(tmp_path):
    assert "is not valid TOML" in fails(tmp_path, "[tenant\n")


def test_a_missing_file_is_reported(tmp_path):
    with pytest.raises(config.ConfigError, match="cannot read"):
        config.load(tmp_path / "nope.toml")


@pytest.mark.parametrize("xdg", [None, "xdg"])
def test_the_tenant_name_finds_the_file_in_the_config_folder(monkeypatch, tmp_path, xdg):
    monkeypatch.delenv("CYCLIX_CONFIG", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    if xdg:
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / xdg))
        folder = tmp_path / xdg
    else:
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        folder = tmp_path / ".config"
    path = folder / "cyclix" / "cyclix.toml"
    path.parent.mkdir(parents=True)
    path.write_text(example())
    assert config.load(tenant="cyclix").tenant.name == "cyclix"


def test_the_path_argument_wins_over_the_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("CYCLIX_CONFIG", str(tmp_path / "nope.toml"))
    assert config.load(EXAMPLE).tenant.name == "cyclix"


def test_no_path_no_env_no_tenant_is_an_error(monkeypatch):
    monkeypatch.delenv("CYCLIX_CONFIG", raising=False)
    with pytest.raises(config.ConfigError, match="set CYCLIX_CONFIG or pass --tenant"):
        config.load()


def test_the_state_dir_is_found_in_three_steps(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("CYCLIX_STATE_DIR", raising=False)
    monkeypatch.delenv("XDG_STATE_HOME", raising=False)
    assert config.state_dir() == tmp_path / ".local" / "state" / "cyclix"
    monkeypatch.setenv("XDG_STATE_HOME", "/xdg")
    assert config.state_dir() == Path("/xdg/cyclix")
    monkeypatch.setenv("CYCLIX_STATE_DIR", "/own")
    assert config.state_dir() == Path("/own")


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        ("pass_env = []\n\n[agent.plan]", "pass_env = [1]\n\n[agent.plan]",
         'config: [agent] "pass_env" must be a list of names'),
        ("max_budget_usd = 2.0", "max_budget_usd = 0",
         'config: [agent.plan] "max_budget_usd" must be a number above 0'),
        ("max_budget_usd = 2.0", 'max_budget_usd = "2"',
         'config: [agent.plan] "max_budget_usd" must be a number above 0'),
    ],
)  # fmt: skip
def test_agent_stage_values_are_checked(tmp_path, old, new, message):
    assert old in example()
    assert fails(tmp_path, example().replace(old, new, 1)) == message
