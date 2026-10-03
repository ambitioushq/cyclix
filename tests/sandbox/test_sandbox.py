"""The sandbox scenarios: real gh, the real agent, the sandbox repo and board.

They run only with CYCLIX_SANDBOX=1. Each one clears what an earlier run left,
and closes and deletes what it made, even when it fails.
"""

import os
import subprocess
import sys
import time
from datetime import UTC, datetime

import pytest
import record_gh_shapes as recorder
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("sandbox.feature")

# A task any build can do, and a new one each run, since the last run's change is merged.
BODY = """\
Add one line to the file `runs.txt` at the repository root, creating the file if it
is missing. The line is:

    {stamp}

Change nothing else.
"""

# Seconds to wait for the board to show a move.
BOARD_WAIT = 60


@pytest.fixture
def sandbox():
    box = recorder.Sandbox.load()
    box.clear()
    yield box
    box.cleanup()


@pytest.fixture
def state_dir(tmp_path):
    return tmp_path / "state"


def one_pass(state_dir):
    env = {**os.environ, "CYCLIX_CONFIG": str(recorder.CONFIG), "CYCLIX_STATE_DIR": str(state_dir)}
    result = subprocess.run(
        [sys.executable, "-m", "cyclix", "run", "--once"],
        env=env, capture_output=True, text=True, check=False,
    )  # fmt: skip
    assert result.returncode == 0, result.stdout + result.stderr
    return result


def wait_for_state(sandbox, issue, state):
    """The board shows a move only after a few seconds. Return the state it shows."""
    deadline = time.monotonic() + BOARD_WAIT
    while (shown := sandbox.board_state(issue)) != state and time.monotonic() < deadline:
        time.sleep(3)
    return shown


def events(state_dir):
    path = state_dir / "events" / "sandbox.jsonl"
    return path.read_text() if path.exists() else "(no events)"


@given(
    parsers.parse('a new issue in the sandbox repository, in state "{state}" on the sandbox board'),
    target_fixture="issue",
)
def new_issue(sandbox, state):
    stamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    number = sandbox.new_issue(f"Record the sandbox run of {stamp}", BODY.format(stamp=stamp))
    sandbox.set_state(number, state)
    assert wait_for_state(sandbox, number, state) == state
    return number


@when("one pass runs with the real gh and the real agent")
def real_pass(state_dir):
    one_pass(state_dir)


@then("a PR for the issue is open in the sandbox repository", target_fixture="pr")
def pr_open(sandbox, issue, state_dir):
    prs = sandbox.open_prs(issue)
    for pr in prs:
        sandbox.adopt_pr(pr["number"], pr["headRefName"])
    assert len(prs) == 1, events(state_dir)
    return prs[0]


@then(parsers.parse('the sandbox board shows the issue in "{state}"'))
def board_shows(sandbox, issue, state, state_dir):
    assert wait_for_state(sandbox, issue, state) == state, events(state_dir)


@when("the PR is merged by hand and one pass runs")
def merge_and_pass(sandbox, pr, state_dir):
    sandbox.merge(pr["number"], pr["headRefName"])
    one_pass(state_dir)
