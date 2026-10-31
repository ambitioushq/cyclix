"""Rules of the GitHub code-host adapter that the scenarios do not reach."""

import os

import pytest
from fakes.runner import environment
from fakes.world import git

from cyclix import config
from cyclix.adapters import gh, github_codehost
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


def fake_git(monkeypatch, tmp_path, script):
    """Put a git that runs this shell script first on PATH."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    git_path = bin_dir / "git"
    git_path.write_text(f"#!/bin/sh\n{script}\n")
    git_path.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")


def test_git_never_prompts_for_a_password(monkeypatch, tmp_path):
    fake_git(monkeypatch, tmp_path, 'echo "$GIT_TERMINAL_PROMPT"')
    assert github_codehost.git(tmp_path, "status") == "0"


@pytest.mark.parametrize(
    ("command", "limit"), [("fetch", "GIT_NETWORK_SECONDS"), ("status", "GIT_LOCAL_SECONDS")]
)
def test_a_git_call_past_its_time_limit_is_an_error(monkeypatch, tmp_path, command, limit):
    # A child holds the output pipe open, as git's credential helper would.
    fake_git(monkeypatch, tmp_path, "sleep 30 & wait")
    monkeypatch.setattr(github_codehost, "GIT_NETWORK_SECONDS", 100)
    monkeypatch.setattr(github_codehost, "GIT_LOCAL_SECONDS", 100)
    monkeypatch.setattr(github_codehost, limit, 1)
    with pytest.raises(CodeHostError, match=f"git {command} gave no answer after 1 seconds"):
        github_codehost.git(tmp_path, command)


def test_the_clone_gets_the_network_time_limit(codehost, monkeypatch):
    calls = []
    monkeypatch.setattr(gh, "run", lambda *args, **kwargs: calls.append((args, kwargs)))
    codehost.ensure_clone()
    [(args, kwargs)] = calls
    assert args[:2] == ("repo", "clone")
    assert kwargs == {"timeout": github_codehost.GIT_NETWORK_SECONDS}


def test_a_local_file_goes_in_the_shared_exclude_file_once(world, codehost, tmp_path):
    files = (("CLAUDE.md", b"rules\n"),)
    first = codehost.new_worktree(1, "one", tmp_path / "r1")
    second = codehost.new_worktree(2, "two", tmp_path / "r2")
    assert codehost.add_local_files(first, files) == []
    assert codehost.add_local_files(second, files) == []
    exclude = world.state_dir / "repos" / "test" / ".git" / "info" / "exclude"
    assert exclude.read_text().splitlines().count("/CLAUDE.md") == 1
    assert (second.path / "CLAUDE.md").read_bytes() == b"rules\n"
    assert git(second.path, "status", "--porcelain") == ""


def test_a_tracked_clash_writes_nothing(world, codehost, tmp_path):
    worktree = codehost.new_worktree(1, "one", tmp_path / "r1")
    files = (("README.md", b"mine\n"), ("notes/a.md", b"a\n"))
    assert codehost.add_local_files(worktree, files) == ["README.md"]
    assert (worktree.path / "README.md").read_text() == "A test repository.\n"
    assert not (worktree.path / "notes").exists()


@pytest.mark.parametrize(
    ("path", "pattern"),
    [
        ("CLAUDE.md", "/CLAUDE.md"),
        ("docs/CLAUDE.md", "/docs/CLAUDE.md"),
        ("a*b?[c].md", "/a\\*b\\?\\[c].md"),
        ("trailing ", "/trailing\\ "),
    ],
)
def test_an_exclude_pattern_matches_only_its_path(path, pattern):
    assert github_codehost.exclude_pattern(path) == pattern
