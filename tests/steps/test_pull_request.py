import re

import pytest
from fakes.world import PLAN_ANSWER, git
from pytest_bdd import given, parsers, scenarios, then

from cyclix import config
from cyclix.adapters.github_codehost import GitHubCodeHost
from cyclix.state.core import RunStart
from cyclix.state.sqlite import SqliteStateCore

scenarios("pull_request.feature")

TENANT = "test"
EARLIER_RUN = "r-earlier"


@pytest.fixture
def core(world):
    core = SqliteStateCore(world.state_dir)
    yield core
    core.close()


def run_dir(world, issue, run_id=EARLIER_RUN):
    return world.state_dir / "runs" / TENANT / str(issue) / run_id


def earlier_run(world, core, issue):
    """Claim the issue for an earlier run and give that run a worktree with one pushed commit."""
    assert core.claim(TENANT, issue, EARLIER_RUN)
    codehost = GitHubCodeHost(config.load(world.config))
    worktree = codehost.new_worktree(issue, f"issue-{issue}", run_dir(world, issue))
    (worktree.path / "earlier.txt").write_text("earlier work\n")
    git(worktree.path, "add", "earlier.txt")
    git(worktree.path, "commit", "-q", "-m", "Earlier work")
    codehost.push(worktree)
    return worktree


def set_pr_state(world, number, state, at="2026-10-01T12:00:00Z"):
    data = world.load()
    pr = next(p for p in data["prs"] if p["number"] == number)
    pr["state"] = state
    pr["closedAt"] = at
    pr["mergedAt"] = at if state == "MERGED" else None
    world.save(data)


# Given


@given(parsers.parse("issue #{issue:d} is In review with PR #{pr:d}"))
def in_review_with_pr(world, core, issue, pr):
    world.add_issue(issue, state="In review")
    earlier_run(world, core, issue)
    world.add_pr(issue, number=pr)


@given(parsers.parse("PR #{pr:d} is merged"))
def pr_merged(world, pr):
    set_pr_state(world, pr, "MERGED")


@given(parsers.parse("PR #{pr:d} is closed without merging"))
def pr_closed(world, pr):
    set_pr_state(world, pr, "CLOSED")


@given(parsers.parse('a run for #{issue:d} crashed in phase "{phase}" after the PR was created'))
def crashed_after_pr(world, core, issue, phase):
    world.add_issue(issue, state="In progress")
    earlier_run(world, core, issue)
    world.add_pr(issue)
    core.begin_run(RunStart(run_id=EARLIER_RUN, tenant=TENANT, issue=issue, stage="pr"))
    core.set_phase(EARLIER_RUN, phase)


@given(parsers.parse('a human moves #{issue:d} back to "{state}"'))
def human_moves_back(world, issue, state):
    data = world.load()
    item = next(i for i in data["board"]["items"] if i.get("issue") == issue)
    item["status"] = state
    world.save(data)


# Then


@then(parsers.parse("the worktree for #{issue:d} is removed"))
def worktree_removed(world, core, issue):
    assert not (run_dir(world, issue) / "worktree").exists()
    assert core.claims(TENANT) == []


@then(parsers.parse("exactly one PR exists for #{issue:d}'s branch"))
def one_pr(world, result, issue):
    prs = world.prs_for(issue)
    assert len(prs) == 1, prs
    pr_events = [
        e["attributes"]["cyclix.outcome"]
        for e in world.events()
        if e["attributes"]["cyclix.stage"] == "pr"
    ]
    # The earlier run's pr row ended as crashed. This pass's pr stage passed.
    assert pr_events == ["crashed", "passed"], result.stdout + result.stderr


def only_pr(world, issue):
    [pr] = world.prs_for(issue)
    return pr


@then(parsers.parse("the PR for #{issue:d} is titled with the issue's title and no issue number"))
def pr_title(world, result, issue):
    title = next(i["title"] for i in world.load()["issues"] if i["number"] == issue)
    pr = only_pr(world, issue)
    assert pr["title"] == title, result.stderr
    assert not re.search(r"\(#\d+\)", pr["title"])


@then(parsers.parse('the PR body for #{issue:d} starts with "{text}"'))
def pr_body_starts(world, result, issue, text):
    assert only_pr(world, issue)["body"].splitlines()[0] == text, result.stderr


@then("it has each section of the PR template")
def body_has_sections(world):
    [pr] = world.load()["prs"]
    lines = pr["body"].splitlines()
    headings = world.pr_template_headings()
    assert headings
    for heading in headings:
        assert heading in lines, heading


@then("it does not contain the plan")
def body_has_no_plan(world):
    [pr] = world.load()["prs"]
    body = pr["body"]
    assert PLAN_ANSWER.strip() not in body
    assert "## Approach" not in body
