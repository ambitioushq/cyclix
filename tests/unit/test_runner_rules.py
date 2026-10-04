"""Rules of the sweep that sweep.feature does not reach until #14 adds the real stages.

The sweep runs in-process against the fake world, with fake stages in place of STAGES.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import pytest

from cyclix import config, runner
from cyclix.adapters.github_tracker import GitHubTracker
from cyclix.stages.base import StageResult
from cyclix.state.core import RunStart
from cyclix.state.sqlite import SqliteStateCore
from cyclix.workstate import State

TENANT = "test"


@dataclass
class FakeStage:
    name: str
    result: StageResult | None = None
    error: Exception | None = None
    seen: list = field(default_factory=list)

    def run(self, ctx):
        self.seen.append(ctx)
        if self.error is not None:
            raise self.error
        return self.result


def passing(name):
    return FakeStage(name, StageResult("passed"))


@pytest.fixture
def stages(monkeypatch):
    def use(*stages):
        monkeypatch.setattr(runner, "STAGES", stages)

    return use


@pytest.fixture
def core(world):
    core = SqliteStateCore(world.state_dir)
    yield core
    core.close()


def sweep(world):
    return runner.sweep(config.load(world.config))


def events(world, issue):
    return [e["attributes"] for e in world.events() if e["attributes"]["cyclix.issue.id"] == issue]


def test_admission_claims_moves_and_makes_a_worktree(world, core, stages):
    stages(plan := passing("plan"))
    world.add_issue(12, title="Add the sweep", state="Ready")
    assert sweep(world) == 0
    assert world.board_state(12) == "In progress"
    [admission, _] = events(world, 12)
    assert admission["cyclix.stage"] == "admission"
    assert admission["cyclix.outcome"] == "passed"
    assert admission["vcs.ref.head.name"] == "cyclix/12-add-the-sweep"
    assert admission["cyclix.config.version"].startswith("sha256:")
    ctx = plan.seen[0]
    assert ctx.issue.title == "Add the sweep"
    assert ctx.worktree.path == ctx.run_dir / "worktree"
    assert ctx.worktree.path.exists()
    assert [c.run_id for c in core.claims(TENANT)] == [ctx.run_id]


def test_the_oldest_ready_issue_is_admitted(world, stages):
    stages()
    world.add_issue(14, state="Ready")
    world.add_issue(13, state="Ready")
    sweep(world)
    assert (world.board_state(13), world.board_state(14)) == ("In progress", "Ready")


def test_the_run_stops_at_the_first_stage_that_does_not_pass(world, core, stages):
    gate = FakeStage("gate", StageResult("parked", "gate command 2 exited 1"))
    pr = passing("pr")
    stages(passing("plan"), FakeStage("build", StageResult("skipped")), gate, pr)
    world.add_issue(12, state="Ready")
    assert sweep(world) == 0
    outcomes = [(e["cyclix.stage"], e["cyclix.outcome"]) for e in events(world, 12)]
    assert outcomes == [
        ("admission", "passed"),
        ("plan", "passed"),
        ("build", "skipped"),
        ("gate", "parked"),
    ]
    assert pr.seen == []
    assert world.board_state(12) == "Parked"
    assert world.comments(12) == ["Parked: gate command 2 exited 1"]
    assert core.claims(TENANT) == []
    assert not gate.seen[0].worktree.path.exists()


def test_a_stage_that_raises_fails_and_parks(world, stages):
    stages(FakeStage("build", error=RuntimeError("disk full")))
    world.add_issue(12, state="Ready")
    assert sweep(world) == 0
    build = events(world, 12)[-1]
    assert (build["cyclix.outcome"], build["cyclix.outcome.reason"]) == (
        "failed",
        "build raised RuntimeError: disk full",
    )
    assert world.board_state(12) == "Parked"


def test_a_stage_moves_its_item_to_the_state_it_asks_for(world, core, stages):
    asks = StageResult("stopped", "which file?", move_to=State.NEEDS_DECISION)
    stages(FakeStage("plan", asks))
    world.add_issue(12, state="Ready")
    sweep(world)
    assert world.board_state(12) == "Needs decision"
    assert world.comments(12) == ["Needs decision: which file?"]
    assert core.claims(TENANT) == []


def test_a_stage_fields_reach_its_event(world, stages):
    stages(FakeStage("gate", StageResult("passed", fields={"vcs.ref.head.revision": "abc"})))
    world.add_issue(12, state="Ready")
    sweep(world)
    assert events(world, 12)[-1]["vcs.ref.head.revision"] == "abc"


def test_a_long_reason_is_cut_to_fit_the_event(world, stages):
    stages(FakeStage("gate", StageResult("parked", "x" * 600)))
    world.add_issue(12, state="Ready")
    assert sweep(world) == 0
    assert len(events(world, 12)[-1]["cyclix.outcome.reason"]) == 500


def test_the_day_limit_stops_admission(world, core, stages):
    stages()
    for n in range(6):
        core.begin_run(RunStart(run_id=f"r{n}", tenant=TENANT, issue=n + 1, stage="admission"))
        core.end_run(f"r{n}", "passed", "")
    world.add_issue(12, state="Ready")
    sweep(world)
    assert world.board_state(12) == "Ready"


def test_a_claim_on_an_item_in_review_stays(world, core, stages):
    stages()
    world.add_issue(12, state="In review")
    core.claim(TENANT, 12, "r-earlier")
    sweep(world)
    assert [c.issue for c in core.claims(TENANT)] == [12]


def test_a_crashed_run_whose_item_a_human_moved_is_ended_but_not_moved(world, core, stages):
    stages()
    world.add_issue(12, state="Ready")
    world.add_issue(13, state="Done")
    core.claim(TENANT, 13, "r-crashed")
    core.begin_run(RunStart(run_id="r-crashed", tenant=TENANT, issue=13, stage="build"))
    sweep(world)
    [crashed] = events(world, 13)
    assert crashed["cyclix.outcome.reason"] == "run crashed in phase none"
    assert world.board_state(13) == "Done"
    assert world.comments(13) == []
    assert core.open_runs(TENANT) == []
    assert [c.issue for c in core.claims(TENANT)] == [12]


def test_a_failed_board_read_fails_the_pass(world, capsys):
    world.add_fault("api graphql", exit=1, stderr="HTTP 502")
    assert sweep(world) == 1
    assert "HTTP 502" in capsys.readouterr().err


def test_runs_today_counts_each_run_once_by_the_utc_date(tmp_path):
    now = datetime(2026, 10, 3, 1, 0, tzinfo=UTC)
    core = SqliteStateCore(tmp_path, clock=lambda: now)
    core.begin_run(RunStart(run_id="r1", tenant=TENANT, issue=1, stage="admission"))
    core.end_run("r1", "passed", "")
    core.begin_run(RunStart(run_id="r1", tenant=TENANT, issue=1, stage="plan"))
    core.end_run("r1", "passed", "")
    core.begin_run(RunStart(run_id="r2", tenant="other", issue=2, stage="admission"))
    assert core.runs_today(TENANT) == 1
    now += timedelta(days=1)
    assert core.runs_today(TENANT) == 0
    core.close()


def test_a_comment_is_posted_on_the_issue(world):
    world.add_issue(12, state="Parked")
    GitHubTracker(config.load(world.config)).comment(12, "Parked: why")
    assert world.comments(12) == ["Parked: why"]
    assert world.calls()[-1]["argv"] == [
        "issue",
        "comment",
        "12",
        "-R",
        "o/r",
        "--body",
        "Parked: why",
    ]
