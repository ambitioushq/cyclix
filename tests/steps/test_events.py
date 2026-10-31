import hashlib
import json
from decimal import Decimal

import pytest
from fakes.world import PLAN_ANSWER, PR_BODY_ANSWER, REPO
from pytest_bdd import given, parsers, scenarios, then, when

from cyclix.events.log import EventError, write_stage_run
from cyclix.events.schema import STAGE_RUN_KEYS
from cyclix.state.core import RunStart
from cyclix.state.sqlite import SqliteStateCore

TENANT = "test"

scenarios("events.feature")


@pytest.fixture
def state_dir(tmp_path):
    return tmp_path / "state"


@pytest.fixture
def core(state_dir):
    core = SqliteStateCore(state_dir)
    yield core
    core.close()


@pytest.fixture
def seen():
    """The fields to write, and what the When steps saw."""
    return {"runs": []}


def log_path(state_dir):
    return state_dir / "events" / f"{TENANT}.jsonl"


def log_lines(state_dir):
    path = log_path(state_dir)
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def stage_run(core, run_id, stage, outcome, reason, extra=None):
    """Build a stage run's fields the way the runner will: through the state core."""
    core.begin_run(RunStart(run_id=run_id, tenant=TENANT, issue=12, stage=stage))
    if extra:
        core.add_fields(run_id, extra)
    return core.end_run(run_id, outcome, reason)


# Given


@given(
    parsers.parse(
        'a stage run for #12 at stage "{stage}" ending "{outcome}" with reason "{reason}"'
    )
)
def run_ending(core, seen, stage, outcome, reason):
    seen["runs"].append(stage_run(core, "r1", stage, outcome, reason))


@given(parsers.parse("a stage run whose reason is {length:d} characters long"))
def run_long_reason(core, seen, length):
    seen["runs"].append(stage_run(core, "r1", "plan", "stopped", "x" * length))


@given(parsers.parse('a stage run with the extra field "{key}" = "{value}"'))
def run_extra_field(core, seen, key, value):
    seen["runs"].append(stage_run(core, "r1", "plan", "passed", "", extra={key: value}))


@given("two stage runs for #12")
def two_runs(core, seen):
    seen["runs"].append(stage_run(core, "r1", "plan", "passed", ""))
    seen["runs"].append(stage_run(core, "r1", "build", "passed", ""))


@given(parsers.parse("the agent reports a cost of {cost}"))
def agent_reports_cost(world, cost):
    world.add_agent_step(answer="## Approach\nChange one file.\n", cost_usd=float(cost))
    world.add_agent_step(
        files={"change.txt": "a change\n"}, commit=True, answer="done", cost_usd=float(cost)
    )


@given(
    parsers.parse(
        "the agent writes a plan in {plan_turns:d} turns, "
        "then commits a change in {build_turns:d} turns"
    )
)
def plan_and_build_in_turns(world, plan_turns, build_turns):
    world.add_agent_step(answer=PLAN_ANSWER, num_turns=plan_turns)
    world.add_agent_step(
        files={"change.txt": "a change\n"}, commit=True, answer=PR_BODY_ANSWER,
        num_turns=build_turns,
    )  # fmt: skip


# When


@when("its event is written")
@when("both events are written")
def events_written(state_dir, seen):
    seen["before"] = log_path(state_dir).read_bytes() if log_path(state_dir).exists() else None
    try:
        for fields in seen["runs"]:
            write_stage_run(state_dir, TENANT, fields)
    except EventError as error:
        seen["error"] = error


# Then


@then("the event log holds one line for #12")
def one_line(state_dir):
    lines = log_lines(state_dir)
    assert [line["attributes"]["cyclix.issue.id"] for line in lines] == [12], lines


@then(parsers.parse('the line has schema "{schema}" and body "{body}"'))
def line_schema_body(state_dir, schema, body):
    (line,) = log_lines(state_dir)
    assert (line["schema"], line["body"]) == (schema, body), line


@then("it has every stage-run key, with null for the model fields")
def every_key(state_dir):
    (line,) = log_lines(state_dir)
    attributes = line["attributes"]
    assert list(attributes) == list(STAGE_RUN_KEYS), attributes
    for key in ("gen_ai.request.model", "gen_ai.usage.input_tokens", "gen_ai.usage.output_tokens"):
        assert attributes[key] is None, key
    assert attributes["cyclix.stage"] == "gate"
    assert attributes["cyclix.outcome"] == "parked"
    assert attributes["cyclix.outcome.reason"] == "gate command 2 exited 1"


@then(parsers.parse('it fails with "{message}"'))
def fails_with(seen, message):
    assert str(seen.get("error")) == message


@then("the event log is unchanged")
def log_unchanged(state_dir, seen):
    after = log_path(state_dir).read_bytes() if log_path(state_dir).exists() else None
    assert after == seen["before"]


@then("the two lines have different trace IDs")
def different_traces(state_dir):
    first, second = log_lines(state_dir)
    assert first["trace_id"] != second["trace_id"]


@then(parsers.parse("both carry cyclix.issue.id {issue:d}"))
def both_carry(state_dir, issue):
    assert [line["attributes"]["cyclix.issue.id"] for line in log_lines(state_dir)] == [issue] * 2


@then(
    parsers.parse(
        'every stage_run event for #{issue:d} has "{key}" set to the tenant\'s repository URL'
    )
)
def events_carry_repository_url(world, result, issue, key):
    found = [e["attributes"] for e in world.events() if e["attributes"]["cyclix.issue.id"] == issue]
    assert found, result.stdout + result.stderr
    assert [a.get(key) for a in found] == [f"https://github.com/{REPO}"] * len(found)


@then(
    parsers.parse(
        'the plan event\'s "{key}" is written with no more than the settled number of decimal places'
    )
)
def plan_cost_is_rounded(world, result, key):
    plans = [e["attributes"] for e in world.events() if e["attributes"]["cyclix.stage"] == "plan"]
    assert len(plans) == 1, result.stdout + result.stderr
    cost = plans[0][key]
    # 6 places is the rule in docs/design/v0.0.md, "The event log, schema version 0".
    assert Decimal(repr(cost)).as_tuple().exponent >= -6, cost
    assert cost == 0.366166


@then(parsers.parse("the {stage} event records {turns:d} agent turns"))
def event_records_turns(world, result, stage, turns):
    [event] = [e for e in world.events() if e["attributes"]["cyclix.stage"] == stage]
    assert event["attributes"]["cyclix.agent.turns"] == turns


def folder_version(folder):
    """The rule in docs/design/v0.0.md: each file's relative path, its length and its content."""
    digest = hashlib.sha256()
    for path in sorted(p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file()):
        content = (folder / path).read_bytes()
        digest.update(f"{path}\0{len(content)}\0".encode() + content)
    return "sha256:" + digest.hexdigest()


@then(
    parsers.parse(
        'every stage_run event for #{issue:d} has "{key}" set to the instruction folder\'s version'
    )
)
def events_carry_instructions_version(world, result, issue, key):
    found = [e["attributes"] for e in world.events() if e["attributes"]["cyclix.issue.id"] == issue]
    assert found, result.stdout + result.stderr
    assert [a.get(key) for a in found] == [folder_version(world.instructions)] * len(found)


@then(parsers.parse('every stage_run event for #{issue:d} has "{key}" set to null'))
def events_carry_null(world, result, issue, key):
    found = [e["attributes"] for e in world.events() if e["attributes"]["cyclix.issue.id"] == issue]
    assert found, result.stdout + result.stderr
    assert all(key in a and a[key] is None for a in found), found
