import json
import sqlite3

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from cyclix.state.core import RunStart, StateError
from cyclix.state.sqlite import SqliteStateCore

TENANT = "test"

scenarios("state_core.feature")


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
    """What the When steps saw, for the Then steps to check."""
    return {}


# Given


@given("an empty state core")
def empty_core(core):
    pass


@given(parsers.parse('run "{run_id}" has begun for #{issue:d} at stage "{stage}"'))
def run_begun(core, run_id, issue, stage):
    core.begin_run(RunStart(run_id=run_id, tenant=TENANT, issue=issue, stage=stage))


@given(parsers.parse('run "{run_id}" has begun and not ended'))
def run_open(core, seen, run_id):
    core.begin_run(RunStart(run_id=run_id, tenant=TENANT, issue=5, stage="pr"))
    core.set_phase(run_id, "push")
    core.set_phase(run_id, "open_pr")
    seen["last_phase"] = "open_pr"


@given(
    parsers.parse(
        'checks recorded for #{issue:d}: sha "{good}" all passed, then sha "{bad}" with one failed'
    )
)
def checks_recorded(core, issue, good, bad):
    core.begin_run(RunStart(run_id="r1", tenant=TENANT, issue=issue, stage="gate", round=1))
    core.record_check("r1", good, "lint", True)
    core.record_check("r1", good, "tests", True)
    core.end_run("r1", "passed", "")
    core.begin_run(RunStart(run_id="r1", tenant=TENANT, issue=issue, stage="gate", round=2))
    core.record_check("r1", bad, "lint", True)
    core.record_check("r1", bad, "tests", False)
    core.end_run("r1", "parked", "gate command 2 exited 1")


@given(parsers.parse("a state file at schema version {version:d}"))
def state_file_at(state_dir, version):
    state_dir.mkdir(parents=True)
    with sqlite3.connect(state_dir / "state.db") as db:
        db.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        db.execute("INSERT INTO meta VALUES ('schema_version', ?)", (str(version),))
    db.close()


# When


@when(parsers.parse('run "{run_id}" claims #{issue:d}'))
def claims(core, seen, run_id, issue):
    seen.setdefault("claims", []).append(core.claim(TENANT, issue, run_id))


@when(parsers.re(r"the fields (?P<pairs>.+) are added"))
def fields_added(core, pairs):
    fields = {}
    for pair in pairs.split(" and "):
        key, value = pair.split(" = ")
        fields[json.loads(key)] = json.loads(value)
    core.add_fields("r1", fields)


@when(parsers.parse('the run ends with outcome "{outcome}"'))
def run_ends(core, seen, outcome):
    seen["fields"] = core.end_run("r1", outcome, "")


@when("open runs are listed")
def list_open(core, seen):
    seen["open"] = core.open_runs(TENANT)


@when(parsers.parse("the best verified commit for #{issue:d} is read"))
def read_best(core, seen, issue):
    seen["best"] = core.best_verified(TENANT, issue)


@when("the state core opens it")
def opens(state_dir, seen):
    try:
        SqliteStateCore(state_dir).close()
    except StateError as error:
        seen["error"] = error


# Then


@then("the first claim succeeds")
def first_succeeds(seen):
    assert seen["claims"][0] is True


@then("the second claim fails")
def second_fails(seen):
    assert seen["claims"][1] is False


@then("the returned fields hold the round, the cost and the outcome")
def fields_hold(seen):
    fields = seen["fields"]
    assert fields["cyclix.round"] == 1, fields
    assert fields["cyclix.cost.usd"] == 0.4, fields
    assert fields["cyclix.outcome"] == "passed", fields


@then(parsers.parse('"{run_id}" is listed with its last phase'))
def listed_with_phase(seen, run_id):
    assert [(r.run_id, r.phase) for r in seen["open"]] == [(run_id, seen["last_phase"])]


@then(parsers.parse('it is "{sha}"'))
def it_is(seen, sha):
    assert seen["best"] == sha


@then(parsers.parse('it fails with "{message}"'))
def fails_with(seen, message):
    assert str(seen.get("error")) == message
