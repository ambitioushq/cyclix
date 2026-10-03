"""Rules of the gh runner: every failure becomes a GhError."""

import pytest
from fakes.runner import environment

from cyclix.adapters import gh


@pytest.fixture
def fake_env(world, monkeypatch):
    for key, value in environment(world).items():
        monkeypatch.setenv(key, value)


def test_gh_missing_from_path_is_a_gh_error(monkeypatch, tmp_path):
    monkeypatch.setenv("PATH", str(tmp_path))
    with pytest.raises(gh.GhError) as error:
        gh.run("auth", "status")
    assert (error.value.code, error.value.stderr) == (127, "gh is not on PATH")


def test_a_failed_call_carries_the_exit_code_and_stderr(world, fake_env):
    world.add_fault("auth status", exit=4, stderr="token expired\n")
    with pytest.raises(gh.GhError) as error:
        gh.run("auth", "status")
    assert (error.value.code, error.value.stderr) == (4, "token expired")
    assert str(error.value) == "gh auth status exited 4: token expired"


def test_output_that_is_not_json_is_a_gh_error(world, fake_env):
    world.add_fault("project field-list", exit=0, stdout="<html>")
    with pytest.raises(gh.GhError) as error:
        gh.json("project", "field-list", "1", "--owner", "o", "--format", "json")
    assert error.value.stderr == "output is not JSON: <html>"


def test_json_output_is_parsed(world, fake_env):
    fields = gh.json("project", "field-list", "1", "--owner", "o", "--format", "json")["fields"]
    assert "Status" in [field["name"] for field in fields]
