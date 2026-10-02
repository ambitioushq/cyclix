import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "names_check.py"

scenarios("names_check.feature")


def git(repo, *args):
    env = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
    return subprocess.run(
        ["git", *args], cwd=repo, env=env, capture_output=True, text=True, check=True
    ).stdout.strip()


@pytest.fixture
def repo(tmp_path):
    git(tmp_path, "init", "-q")
    git(tmp_path, "config", "user.name", "Test")
    git(tmp_path, "config", "user.email", "test@example.com")
    git(tmp_path, "commit", "-q", "--allow-empty", "-m", "Start")
    return tmp_path


@pytest.fixture
def env():
    env = dict(os.environ)
    env.pop("CYCLIX_FORBIDDEN_NAMES", None)
    return env


@given(parsers.re(r"the forbidden names (?P<names>.+)"))
def forbidden_names(env, names):
    env["CYCLIX_FORBIDDEN_NAMES"] = "\n".join(re.findall(r'"([^"]*)"', names))


@given("no forbidden names are set")
def no_forbidden_names(env):
    pass


@given(parsers.parse('a tracked file "{path}" whose line {line:d} reads "{text}"'))
def tracked_file(repo, path, line, text):
    lines = [f"Line {n}" for n in range(1, line)] + [text]
    (repo / path).write_text("\n".join(lines) + "\n")
    git(repo, "add", path)


@given(parsers.parse('a commit whose message reads "{message}"'), target_fixture="commit")
def commit(repo, message):
    git(repo, "commit", "-q", "--allow-empty", "-m", message)
    return git(repo, "rev-parse", "--short", "HEAD")


def run_check(repo, env, *args):
    return subprocess.run(
        [sys.executable, SCRIPT, *args],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


@when("the names check runs", target_fixture="result")
def names_check_runs(repo, env):
    return run_check(repo, env)


@when("the names check runs over that commit", target_fixture="result")
def names_check_runs_over_commit(repo, env):
    return run_check(repo, env, "--commits", "HEAD~1..HEAD")


@then(parsers.parse("it exits {code:d}"))
def exits_with(result, code):
    assert result.returncode == code, result.stdout + result.stderr


@then(parsers.parse('it prints "{text}"'))
def prints(result, text):
    assert text in result.stdout.splitlines()


@then(parsers.parse('the output does not contain "{text}" in any case'))
def output_omits(result, text):
    assert text.lower() not in (result.stdout + result.stderr).lower()


@then(parsers.parse('it prints the commit\'s short SHA and "{text}"'))
def prints_sha_and(result, commit, text):
    assert any(commit in line and text in line for line in result.stdout.splitlines())
