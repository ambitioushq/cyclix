import sqlite3

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from cyclix.state.sqlite import SqliteStateCore

TENANT = "test"

scenarios("state_core.feature")


@pytest.fixture
def core(world):
    core = SqliteStateCore(world.state_dir)
    yield core
    core.close()


@pytest.fixture
def seen():
    """What the When steps saw, for the Then steps to check."""
    return {}


# Given


@given(parsers.parse("one run holds issue #{issue:d}"))
def run_holds(core, issue):
    assert core.claim(TENANT, issue, "r1")


@given(parsers.parse("the state file was written by a newer Cyclix, at schema version {version:d}"))
def newer_state_file(world, version):
    world.state_dir.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(world.state_dir / "state.db") as db:
        db.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        db.execute("INSERT INTO meta VALUES ('schema_version', ?)", (str(version),))
    db.close()


# When


@when(parsers.parse("a second run tries to take issue #{issue:d}"))
def second_run_takes(core, seen, issue):
    seen["taken"] = core.claim(TENANT, issue, "r2")


# Then


@then(parsers.parse("the second run does not get issue #{issue:d}"))
def second_run_refused(seen, issue):
    assert seen["taken"] is False


@then(parsers.parse("issue #{issue:d} stays with the first run"))
def stays_with_first(core, issue):
    assert [(c.issue, c.run_id) for c in core.claims(TENANT)] == [(issue, "r1")]
