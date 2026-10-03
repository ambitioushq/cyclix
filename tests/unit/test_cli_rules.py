"""Rules of the cyclix command that the scenarios in cli.feature do not reach."""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from fakes.runner import BIN, environment, run_cyclix


def lines(result):
    return result.stdout.splitlines()


def test_run_once_with_a_bad_config_fails(world):
    world.config.write_text("[tenant]\n")
    result = run_cyclix(world, "run", "--once")
    assert result.returncode == 1
    assert result.stderr == 'config: [tenant] is missing "name"\n'


def test_run_without_once_is_a_usage_error(world):
    assert run_cyclix(world, "run").returncode == 2


def test_no_subcommand_is_a_usage_error(world):
    result = run_cyclix(world)
    assert result.returncode == 2
    assert result.stdout == ""
    assert result.stderr.startswith("usage: cyclix")


def test_a_bad_config_fails_and_skips_the_checks_that_need_it(world):
    world.config.write_text("[tenant]\n")
    result = run_cyclix(world, "check")
    assert result.returncode == 1
    assert 'FAIL: config: [tenant] is missing "name"' in lines(result)
    assert not any("agent" in line or "board" in line for line in lines(result))


def test_gh_missing_from_path_fails_and_skips_the_board(world, tmp_path):
    # PATH holds only cyclix and the fake agent, so there is no gh to find.
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "cyclix").symlink_to(Path(sys.executable).parent / "cyclix")
    (bin_dir / "fake-agent").symlink_to(BIN / "fake-agent")
    result = subprocess.run(
        ["cyclix", "check"],
        env={**environment(world), "PATH": str(bin_dir)},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert "FAIL: gh is not on PATH" in lines(result)
    assert not any("board" in line for line in lines(result))


def test_an_agent_command_not_on_path_fails(world):
    text = world.config.read_text().replace(
        'command = ["fake-agent"]', 'command = ["no-such-agent"]'
    )
    world.config.write_text(text)
    result = run_cyclix(world, "check")
    assert result.returncode == 1
    assert 'FAIL: the agent command "no-such-agent" is not on PATH' in lines(result)


def test_an_unreadable_board_fails(world):
    world.add_fault("project field-list", exit=1, stderr="HTTP 502")
    result = run_cyclix(world, "check")
    assert result.returncode == 1
    assert "FAIL: cannot read board o/1: HTTP 502" in lines(result)


@pytest.mark.skipif(os.geteuid() == 0, reason="root can write anywhere")
def test_a_state_dir_that_cannot_be_written_fails(world):
    world.state_dir.chmod(0o500)
    try:
        result = run_cyclix(world, "check")
    finally:
        world.state_dir.chmod(0o700)
    assert result.returncode == 1
    assert any(
        line.startswith(f"FAIL: the state directory {world.state_dir} is not writable")
        for line in lines(result)
    ), result.stdout


def test_a_board_without_the_status_field_fails(world):
    text = world.config.read_text().replace('status_field = "Status"', 'status_field = "Stage"')
    world.config.write_text(text)
    result = run_cyclix(world, "check")
    assert result.returncode == 1
    assert 'FAIL: the board has no single-select field "Stage"' in lines(result)
