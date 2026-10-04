import fcntl
import re

import pytest
from fakes.runner import run_cyclix
from fakes.world import REPO
from pytest_bdd import given, parsers, scenarios, then, when

from cyclix.state.core import RunStart
from cyclix.state.sqlite import SqliteStateCore

scenarios("sweep.feature")

TENANT = "test"


@pytest.fixture
def core(world):
    core = SqliteStateCore(world.state_dir)
    yield core
    core.close()


def set_gate(world, commands):
    """Replace the test config's gate commands."""
    listed = ", ".join("[" + ", ".join(f'"{word}"' for word in c) + "]" for c in commands)
    text, count = re.subn(
        r"(?m)^commands = .*$", f"commands = [{listed}]", world.config.read_text()
    )
    assert count == 1
    world.config.write_text(text)


# Given


@given("the gate commands pass")
def gate_passes(world):
    set_gate(world, [["true"], ["true"]])


@given("the gate's second command fails")
def gate_fails_second(world):
    # The run has to reach the gate, so the plan and the build succeed first.
    world.add_plan_and_commit()
    set_gate(world, [["true"], ["false"]])


@given(parsers.parse("issue #{issue:d} is claimed in the state core and In progress on the board"))
def claimed_in_progress(world, core, issue):
    world.add_issue(issue, state="In progress")
    assert core.claim(TENANT, issue, "r-earlier")


@given(parsers.parse('a human moves #{issue:d} to "{state}" on the board'))
def human_moves(world, issue, state):
    data = world.load()
    item = next(i for i in data["board"]["items"] if i.get("issue") == issue)
    item["status"] = state
    world.save(data)


@given(
    parsers.parse(
        'a run for #{issue:d} began at stage "{stage}" in phase "{phase}" and its process is gone'
    )
)
def crashed_run(world, core, issue, stage, phase):
    world.add_issue(issue, state="In progress")
    assert core.claim(TENANT, issue, "r-crashed")
    core.begin_run(RunStart(run_id="r-crashed", tenant=TENANT, issue=issue, stage=stage))
    core.set_phase("r-crashed", phase)


@given("a pass is running for the tenant")
def pass_running(world):
    lock = (world.state_dir / f"{TENANT}.lock").open("w")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    yield
    lock.close()


@given(parsers.parse("issue #{busy:d} is In progress and issue #{ready:d} is Ready"))
def one_in_progress(world, busy, ready):
    world.add_issue(busy, state="In progress")
    world.add_issue(ready, state="Ready")


# When


@when("a second pass starts", target_fixture="result")
def second_pass(world):
    return run_cyclix(world, "run", "--once")


# Then


@then(
    parsers.parse(
        "the event log holds stage_run events for #{issue:d} at {first}, {middle} and {last}"
    )
)
def events_at_stages(world, result, issue, first, middle, last):
    wanted = [first, *middle.split(", "), last]
    stages = [
        e["attributes"]["cyclix.stage"]
        for e in world.events()
        if e["attributes"]["cyclix.issue.id"] == issue
    ]
    assert stages == wanted, result.stdout + result.stderr


@then(
    parsers.parse(
        'every stage_run event for #{issue:d} has "{key}" set to the tenant\'s repository URL'
    )
)
def events_carry_repository_url(world, result, issue, key):
    found = [e["attributes"] for e in world.events() if e["attributes"]["cyclix.issue.id"] == issue]
    assert found, result.stdout + result.stderr
    assert [a.get(key) for a in found] == [f"https://github.com/{REPO}"] * len(found)


@then(parsers.parse("no PR for #{issue:d} exists"))
def no_pr(world, issue):
    assert world.prs_for(issue) == []


@then(parsers.parse("the claim on #{issue:d} is released"))
def claim_released(core, result, issue):
    assert result.returncode == 0, result.stderr
    assert [c.issue for c in core.claims(TENANT)] == []


@then(parsers.parse("issue #{issue:d} is not run"))
def not_run(world, core, issue):
    assert core.runs_today(TENANT) == 0
    assert [e for e in world.events() if e["attributes"]["cyclix.issue.id"] == issue] == []
    assert world.agent_script() == [] and world.prompts() == []


@then(parsers.parse('a stage_run event for #{issue:d} at "{stage}" has outcome "{outcome}"'))
def stage_event(world, result, issue, stage, outcome):
    found = [
        e["attributes"]
        for e in world.events()
        if e["attributes"]["cyclix.issue.id"] == issue and e["attributes"]["cyclix.stage"] == stage
    ]
    assert [a["cyclix.outcome"] for a in found] == [outcome], result.stdout + result.stderr


@then(parsers.parse('the board shows #{issue:d} in "{state}" with reason "{reason}"'))
def board_shows_with_reason(world, issue, state, reason):
    assert world.board_state(issue) == state
    assert world.comments(issue) == [f"Parked: {reason}"]


@then(parsers.parse('issue #{issue:d} stays in "{state}"'))
def stays_in(world, result, issue, state):
    assert result.returncode == 0, result.stderr
    assert world.board_state(issue) == state
