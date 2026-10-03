import pytest
from fakes.runner import environment
from fakes.world import git
from pytest_bdd import given, parsers, scenarios, then, when

from cyclix import config
from cyclix.adapters.codehost import CodeHostError
from cyclix.adapters.github_codehost import GitHubCodeHost, slug

scenarios("codehost.feature")

BRANCH = "cyclix/12-add-the-state-core"


@pytest.fixture
def codehost(world, monkeypatch):
    """The adapter, run in-process with the fakes first on PATH."""
    for key, value in environment(world).items():
        monkeypatch.setenv(key, value)
    return GitHubCodeHost(config.load())


@pytest.fixture
def seen():
    """Commits named by the Given steps, and what the When steps saw."""
    return {"commits": {}}


def seed(world):
    """A plain clone of the remote, for steps that change the remote behind the adapter."""
    path = world.root / "seed"
    git(path, "fetch", "-q", "origin")
    return path


def commit(path, name):
    (path / f"{name}.txt").write_text(f"{name}\n")
    git(path, "add", f"{name}.txt")
    git(path, "commit", "-q", "-m", name)
    return git(path, "rev-parse", "HEAD")


def remote_sha(world, branch):
    return git(world.root, "--git-dir", str(world.remote), "rev-parse", f"refs/heads/{branch}")


def run_dir(world, issue):
    return world.state_dir / "runs" / "test" / str(issue) / "run-1"


# Given


@given(parsers.parse('the remote\'s main branch at commit "{name}"'))
def remote_main_at(world, seen, name):
    path = seed(world)
    seen["commits"][name] = commit(path, name)
    git(path, "push", "-q", "origin", "HEAD:main")


@given(parsers.parse('a pushed branch "{branch}"'))
def pushed_branch(world, branch):
    path = seed(world)
    git(path, "checkout", "-q", "-b", branch, "origin/main")
    commit(path, "work")
    git(path, "push", "-q", "origin", branch)


@given("the remote branch has a commit the worktree lacks", target_fixture="worktree")
def remote_ahead(world, codehost, seen):
    worktree = codehost.new_worktree(12, slug("Add the state core"), run_dir(world, 12))
    commit(worktree.path, "mine")
    codehost.push(worktree)
    path = seed(world)
    git(path, "checkout", "-q", "-b", "theirs", f"origin/{BRANCH}")
    commit(path, "theirs")
    git(path, "push", "-q", "origin", f"HEAD:{BRANCH}")
    seen["remote"] = remote_sha(world, BRANCH)
    commit(worktree.path, "mine-again")
    return worktree


@given(parsers.parse("PR #{pr:d} for #{issue:d} is merged"))
def pr_merged(world, pr, issue):
    world.add_issue(issue, title="Add the state core")
    world.add_pr(issue, number=pr, state="MERGED", merged_at="2026-10-01T12:00:00Z")


# When


@when(
    parsers.parse('a worktree is made for #{issue:d} titled "{title}"'),
    target_fixture="worktree",
)
def make_worktree(world, codehost, issue, title):
    return codehost.new_worktree(issue, slug(title), run_dir(world, issue))


@when("a PR is opened for it")
@when("a PR is opened for it again")
def open_pr(codehost, seen):
    seen.setdefault("prs", []).append(codehost.open_pr(BRANCH, "Add the state core", "Closes #12"))


@when("the worktree is pushed")
def push(codehost, worktree, seen):
    try:
        codehost.push(worktree)
    except CodeHostError as error:
        seen["error"] = error


@when("its state is read", target_fixture="state")
def read_state(codehost):
    return codehost.pr_state(20)


# Then


@then(parsers.parse('the worktree is on branch "{branch}"'))
def on_branch(worktree, branch):
    assert worktree.branch == branch
    assert git(worktree.path, "branch", "--show-current") == branch


@then(parsers.parse('its head is "{name}"'))
def head_is(codehost, worktree, seen, name):
    assert codehost.head_sha(worktree) == seen["commits"][name]


@then("exactly one PR exists for the branch")
def one_pr(world, seen):
    prs = [pr for pr in world.load()["prs"] if pr["head"] == BRANCH]
    assert len(prs) == 1, prs
    first, second = seen["prs"]
    assert first.number == second.number == prs[0]["number"]


@then("the push fails")
def push_fails(seen):
    assert "error" in seen


@then("the remote branch is unchanged")
def remote_unchanged(world, seen):
    assert remote_sha(world, BRANCH) == seen["remote"]


@then("it is merged, with its merge time")
def is_merged(state):
    assert state.state == "merged"
    assert state.merged_at.isoformat() == "2026-10-01T12:00:00+00:00"
