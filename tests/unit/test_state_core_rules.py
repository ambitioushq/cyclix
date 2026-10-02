import ast
import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path

import pytest

from cyclix.state import sqlite as state_sqlite
from cyclix.state.core import RunStart, StateError
from cyclix.state.sqlite import SqliteStateCore

SRC = Path(__file__).resolve().parents[2] / "src" / "cyclix"


@pytest.fixture
def core(tmp_path):
    core = SqliteStateCore(tmp_path)
    yield core
    core.close()


def begin(core, run_id="r1", issue=5, station="gate", round=1):
    core.begin_run(RunStart(run_id=run_id, tenant="t", issue=issue, station=station, round=round))


def raw(tmp_path):
    return sqlite3.connect(tmp_path / "state.db")


# Opening and the schema


def test_a_new_file_is_wal_at_schema_1(core, tmp_path):
    db = raw(tmp_path)
    assert db.execute("PRAGMA journal_mode").fetchone() == ("wal",)
    assert db.execute("SELECT value FROM meta").fetchall() == [("1",)]
    assert core.db.execute("PRAGMA busy_timeout").fetchone() == (5000,)


def test_reopening_keeps_the_data(tmp_path):
    first = SqliteStateCore(tmp_path)
    first.claim("t", 5, "r1")
    first.close()
    again = SqliteStateCore(tmp_path)
    assert [c.run_id for c in again.claims("t")] == ["r1"]
    again.close()


def test_an_older_file_is_migrated_by_numbered_steps(tmp_path, monkeypatch):
    SqliteStateCore(tmp_path).close()
    step_2 = "CREATE TABLE extra (x INTEGER); INSERT INTO extra VALUES (7)"
    monkeypatch.setattr(state_sqlite, "MIGRATIONS", [*state_sqlite.MIGRATIONS, step_2])
    monkeypatch.setattr(state_sqlite, "SCHEMA_VERSION", 2)
    SqliteStateCore(tmp_path).close()
    db = raw(tmp_path)
    assert db.execute("SELECT value FROM meta").fetchall() == [("2",)]
    assert db.execute("SELECT x FROM extra").fetchall() == [(7,)]


def test_a_failed_migration_step_leaves_the_old_version(tmp_path, monkeypatch):
    SqliteStateCore(tmp_path).close()
    monkeypatch.setattr(state_sqlite, "MIGRATIONS", [*state_sqlite.MIGRATIONS, "NOT SQL"])
    monkeypatch.setattr(state_sqlite, "SCHEMA_VERSION", 2)
    with pytest.raises(sqlite3.OperationalError):
        SqliteStateCore(tmp_path)
    assert raw(tmp_path).execute("SELECT value FROM meta").fetchall() == [("1",)]


# Claims


def test_only_one_of_many_concurrent_claims_wins(tmp_path):
    SqliteStateCore(tmp_path).close()
    results = []
    start = threading.Barrier(8)

    def contend(n):
        core = SqliteStateCore(tmp_path)
        start.wait()
        results.append(core.claim("t", 5, f"r{n}"))
        core.close()

    threads = [threading.Thread(target=contend, args=(n,)) for n in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sorted(results) == [False] * 7 + [True]


def test_a_released_issue_can_be_claimed_again(core):
    assert core.claim("t", 5, "r1")
    core.release("t", 5)
    assert core.claim("t", 5, "r2")
    assert [(c.issue, c.run_id) for c in core.claims("t")] == [(5, "r2")]


def test_claims_are_per_tenant(core):
    assert core.claim("a", 5, "r1")
    assert core.claim("b", 5, "r2")
    assert [c.tenant for c in core.claims("a")] == ["a"]


# Runs


def test_a_run_has_one_row_per_station(core):
    begin(core, station="plan")
    core.end_run("r1", "passed", "")
    begin(core, station="build")
    assert [r.station for r in core.open_runs("t")] == ["build"]


def test_a_run_cannot_open_a_second_station(core):
    begin(core, station="plan")
    with pytest.raises(StateError, match="already has an open station"):
        begin(core, station="build")


def test_a_call_on_a_run_with_no_open_station_is_refused(core):
    with pytest.raises(StateError, match="run r9 has no open station"):
        core.set_phase("r9", "push")


def test_begin_run_seeds_the_event_identity(core):
    begin(core, issue=12, station="pr", round=2)
    fields = core.end_run("r1", "stopped", "STOP: unclear")
    assert fields == {
        "cyclix.tenant": "t",
        "cyclix.issue.id": 12,
        "cyclix.run.id": "r1",
        "cyclix.station": "pr",
        "cyclix.round": 2,
        "cyclix.outcome": "stopped",
        "cyclix.outcome.reason": "STOP: unclear",
    }


def test_adding_the_round_field_moves_the_round_column(core):
    begin(core)
    core.add_fields("r1", {"cyclix.round": 3})
    assert core.open_runs("t")[0].round == 3


def test_an_ended_run_is_not_open(core):
    begin(core)
    core.end_run("r1", "passed", "")
    assert core.open_runs("t") == []


# Checks


def test_checks_in_a_crashed_station_never_count(core):
    begin(core)
    core.record_check("r1", "a", "lint", True)
    core.end_run("r1", "crashed", "no live process")
    assert core.best_verified("t", 5) is None


def test_checks_in_an_open_station_do_not_count_yet(core):
    begin(core)
    core.record_check("r1", "a", "lint", True)
    assert core.best_verified("t", 5) is None


def test_a_later_passing_commit_wins(core):
    for round, sha in ((1, "a"), (2, "b")):
        begin(core, round=round)
        core.record_check("r1", sha, "tests", True)
        core.end_run("r1", "passed", "")
    assert core.best_verified("t", 5) == "b"


def test_best_verified_is_per_issue(core):
    begin(core, issue=6)
    core.record_check("r1", "a", "tests", True)
    core.end_run("r1", "passed", "")
    assert core.best_verified("t", 5) is None


# Spend


def test_spend_adds_up_by_utc_day(tmp_path):
    days = iter(
        [datetime(2026, 10, 2, 23, tzinfo=UTC)] * 2 + [datetime(2026, 10, 3, 1, tzinfo=UTC)]
    )
    core = SqliteStateCore(tmp_path, clock=lambda: next(days))
    core.add_spend("t", 0.25, 100)
    core.add_spend("t", 0.5, 50)
    core.add_spend("t", 1.0, 10)
    rows = core.db.execute("SELECT day, usd, tokens FROM spend ORDER BY day").fetchall()
    assert rows == [("2026-10-02", 0.75, 150), ("2026-10-03", 1.0, 10)]
    core.close()


# The interface boundary


def state_modules(source):
    """The modules under cyclix.state that a source file imports from."""
    found = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ImportFrom) and node.module:
            found.update(f"{node.module}.{a.name}" for a in node.names)
        elif isinstance(node, ast.Import):
            found.update(a.name for a in node.names)
    return {n.split(".")[2] for n in found if n.startswith("cyclix.state.")}


def test_stations_import_only_state_core():
    for path in (SRC / "stations").rglob("*.py"):
        assert state_modules(path.read_text()) <= {"core"}, path


def test_the_import_check_catches_the_sqlite_module():
    assert state_modules("from cyclix.state.core import RunStart") == {"core"}
    assert state_modules("from cyclix.state import sqlite") == {"sqlite"}
    assert state_modules("import cyclix.state.sqlite") == {"sqlite"}
