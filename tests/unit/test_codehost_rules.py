"""Rules of the GitHub code-host adapter that the scenarios do not reach."""

import pytest
from fakes.runner import environment
from fakes.world import git

from cyclix import config
from cyclix.adapters.codehost import CodeHostError
from cyclix.adapters.github_codehost import GitHubCodeHost, slug


@pytest.fixture
def codehost(world, monkeypatch):
    for key, value in environment(world).items():
        monkeypatch.setenv(key, value)
    return GitHubCodeHost(config.load())


def advance_main(world):
    seed = world.root / "seed"
    (seed / "next.txt").write_text("next\n")
    git(seed, "add", "next.txt")
    git(seed, "commit", "-q", "-m", "Next")
    git(seed, "push", "-q", "origin", "HEAD:main")
    return git(seed, "rev-parse", "HEAD")


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Add the state core", "add-the-state-core"),
        ("Write `cyclix check` (again)!", "write-cyclix-check-again"),
        ("x" * 50, "x" * 40),
        ("x" * 39 + " and more", "x" * 39),  # a hyphen left at the cut is dropped
    ],
)
def test_slug(title, expected):
    assert slug(title) == expected


def test_the_repo_is_cloned_once(world, codehost):
    codehost.ensure_clone()
    codehost.ensure_clone()
    clones = [c for c in world.calls() if c["argv"][:2] == ["repo", "clone"]]
    assert len(clones) == 1
    assert (world.state_dir / "repos" / "test" / ".git").is_dir()


def test_a_new_worktree_starts_from_the_base_as_fetched_now(world, codehost, tmp_path):
    codehost.ensure_clone()
    head = advance_main(world)
    worktree = codehost.new_worktree(12, "add-the-state-core", tmp_path / "run")
    assert worktree.path == tmp_path / "run" / "worktree"
    assert codehost.head_sha(worktree) == head


def test_a_removed_worktree_is_gone(world, codehost, tmp_path):
    worktree = codehost.new_worktree(12, "add-the-state-core", tmp_path / "run")
    (worktree.path / "untracked.txt").write_text("left by the agent\n")
    codehost.remove_worktree(worktree)
    assert not worktree.path.exists()
    codehost.remove_worktree(worktree)  # a second removal is harmless


def test_a_closed_pr_is_not_reused(world, codehost):
    world.add_issue(12, title="Add the state core")
    closed = world.add_pr(12, state="CLOSED")
    pr = codehost.open_pr("cyclix/12-add-the-state-core", "Add the state core", "Closes #12")
    assert pr.number != closed
    assert codehost.find_pr("cyclix/12-add-the-state-core").number == pr.number


def test_an_open_pr_has_no_merge_time(world, codehost):
    world.add_issue(12, title="Add the state core")
    number = world.add_pr(12)
    state = codehost.pr_state(number)
    assert (state.state, state.merged_at, state.closed_at) == ("open", None, None)


def test_no_pr_on_a_branch_is_none(codehost):
    assert codehost.find_pr("cyclix/99-nothing") is None


def test_a_gh_failure_is_a_code_host_error(world, codehost):
    world.add_fault("pr view", exit=1, stderr="HTTP 502")
    with pytest.raises(CodeHostError, match="HTTP 502"):
        codehost.pr_state(20)
