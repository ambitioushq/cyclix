import json

import pytest
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
