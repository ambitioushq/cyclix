"""Fixtures and the steps every feature can use. tests/README.md lists the step phrases."""

import json
import re
import shlex
from pathlib import Path

import pytest
from fakes.runner import environment, run_cyclix
from fakes.world import World
from pytest_bdd import given, parsers, then, when

FEATURES = Path(__file__).resolve().parent / "features"


def pytest_configure(config):
    """Register a marker for every @issue-<n> tag, so `pytest -m issue_<n>` runs one issue."""
    tags = set()
    for feature in FEATURES.rglob("*.feature"):
        tags.update(re.findall(r"@issue-(\d+)\b", feature.read_text()))
    for n in sorted(tags, key=int):
        config.addinivalue_line("markers", f"issue_{n}: scenarios introduced by #{n}")


def pytest_bdd_apply_tag(tag, function):
    """Turn the tag @issue-4 into the marker issue_4, and @xfail-until-9 into a strict xfail.

    Other tags keep the default handling.
    """
    if match := re.fullmatch(r"issue-(\d+)", tag):
        getattr(pytest.mark, f"issue_{match[1]}")(function)
        return True
    if match := re.fullmatch(r"xfail-until-(\d+)", tag):
        pytest.mark.xfail(strict=True, reason=f"needs #{match[1]}")(function)
        return True
    return None


@pytest.fixture
def world(tmp_path, monkeypatch):
    """A fresh fake world for each scenario: issues, board, PRs, state dir and a bare remote.

    The environment points at the fakes too, so code called in-process runs the fake gh.
    """
    world = World(tmp_path).create()
    for key, value in environment(world).items():
        monkeypatch.setenv(key, value)
    return world


# Given


@given(
    parsers.re(
        r'an issue #(?P<number>\d+) titled "(?P<title>[^"]*)" in state "(?P<state>[^"]*)" on the board'
    )
)
def issue_with_title_on_board(world, number, title, state):
    world.add_issue(int(number), title=title, state=state)


@given(parsers.re(r'an issue #(?P<number>\d+) in state "(?P<state>[^"]*)" on the board'))
def issue_on_board(world, number, state):
    world.add_issue(int(number), state=state)


@given(parsers.parse("a PR for #{number:d} is open"))
def pr_is_open(world, number):
    world.add_pr(number)


@given(
    parsers.re(
        r'(?:gh call )?"(?P<command>[^"]+)" fails with exit (?P<code>\d+)'
        r'(?: and stderr "(?P<stderr>[^"]*)")? once'
    )
)
def gh_call_fails_once(world, command, code, stderr):
    world.add_fault(command, exit=int(code), stderr=stderr or "")


@given(parsers.parse('the agent answers "{answer}"'))
def agent_answers(world, answer):
    world.add_agent_step(answer=answer)


# When


@when(parsers.parse('I run "{command}"'), target_fixture="result")
def run_command(world, command):
    program, *args = shlex.split(command)
    assert program == "cyclix", command
    return run_cyclix(world, *args)


# Then


@then(parsers.parse('the board shows #{number:d} in "{state}"'))
def board_shows(world, number, state):
    assert world.board_state(number) == state


@then(parsers.parse("a PR for #{number:d} is open"))
def pr_is_open_now(world, number):
    assert [pr for pr in world.prs_for(number) if pr["state"] == "OPEN"], world.load()["prs"]


@then(
    parsers.parse(
        'the event log holds a stage_run event for #{number:d} at stage "{stage}" '
        'with outcome "{outcome}"'
    )
)
def event_logged(world, number, stage, outcome):
    wanted = {"cyclix.issue.id": number, "cyclix.stage": stage, "cyclix.outcome": outcome}
    events = world.events()
    assert any(
        e["body"] == "stage_run" and all(e["attributes"].get(k) == v for k, v in wanted.items())
        for e in events
    ), json.dumps(events, indent=2)


@then(parsers.parse("it exits {code:d}"))
def exits_with(result, code):
    assert result.returncode == code, result.stdout + result.stderr


@then(parsers.parse('it prints "{text}"'))
def prints(result, text):
    text = text.replace('\\"', '"')  # a quote inside the quoted text is written \"
    assert text in result.stdout.splitlines(), result.stdout
