"""Rules of the cyclix command that the scenarios in cli.feature do not reach."""

import logging
import os
import subprocess
import sys
from pathlib import Path

import pytest
from fakes.runner import BIN, environment, run, run_cyclix

from cyclix import cli


def lines(result):
    return result.stdout.splitlines()


def reports(result, failure, fix):
    """Does the output hold the failure line, then its fix line?"""
    output = lines(result)
    if failure not in output:
        return False
    index = output.index(failure)
    return output[index + 1 : index + 2] == [f"  fix: {fix}"]


def test_run_with_a_bad_config_fails(world):
    world.config.write_text("[tenant]\n")
    result = run_cyclix(world, "run")
    assert result.returncode == 1
    assert result.stderr == 'config: [tenant] is missing "name"\n'


def test_setting_up_logging_again_replaces_the_handler():
    cyclix = logging.getLogger("cyclix")
    try:
        cli.set_up_logging(verbose=False)
        cli.set_up_logging(verbose=True)
        assert len(cyclix.handlers) == 1
        assert cyclix.level == logging.DEBUG
    finally:
        for handler in cyclix.handlers[:]:
            cyclix.removeHandler(handler)
        cyclix.setLevel(logging.NOTSET)


def test_no_subcommand_is_a_usage_error(world):
    result = run_cyclix(world)
    assert result.returncode == 2
    assert result.stdout == ""
    assert result.stderr.startswith("usage: cyclix")


def test_a_bad_config_fails_and_skips_the_checks_that_need_it(world):
    world.config.write_text("[tenant]\n")
    result = run_cyclix(world, "check")
    assert result.returncode == 1
    assert reports(result, 'FAIL: config: [tenant] is missing "name"', f"edit {world.config}")
    assert "skipped: agent command: needs the config" in lines(result)
    assert "skipped: board: needs the config" in lines(result)
    assert "skipped: protection of the base branch: needs the config" in lines(result)


def test_a_skipped_check_names_only_the_failed_checks_it_needs(world):
    world.config.write_text("[tenant]\n")
    world.set_logged_in(False)
    result = run_cyclix(world, "check")
    assert result.returncode == 1
    assert "skipped: agent command: needs the config" in lines(result), result.stdout
    assert "skipped: board: needs the config and gh signed in" in lines(result), result.stdout


def test_check_without_a_config_file_says_how_to_name_one(world):
    env = environment(world)
    del env["CYCLIX_CONFIG"]
    result = subprocess.run(
        ["cyclix", "check"], env=env, capture_output=True, text=True, check=False
    )
    assert result.returncode == 1
    assert reports(
        result,
        "FAIL: config: no config file given: set CYCLIX_CONFIG or pass --tenant",
        "pass --tenant NAME, or set CYCLIX_CONFIG to the config file's path",
    ), result.stdout


def test_check_for_a_tenant_without_a_config_file_names_the_file_to_write(world):
    env = environment(world)
    del env["CYCLIX_CONFIG"]
    result = subprocess.run(
        ["cyclix", "check", "--tenant", "nosuch"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    path = world.xdg_config / "cyclix" / "nosuch.toml"
    assert result.returncode == 1
    assert reports(
        result,
        f"FAIL: config: cannot read {path}: No such file or directory",
        f"write the tenant config at {path}",
    ), result.stdout


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
    assert reports(
        result, "FAIL: gh: not on PATH", "install gh, the GitHub CLI, and put it on PATH"
    ), result.stdout
    assert "skipped: board o/1: needs gh signed in" in lines(result)


def test_an_unreadable_board_fails(world):
    world.add_fault("project field-list", exit=1, stderr="HTTP 502")
    result = run_cyclix(world, "check")
    assert result.returncode == 1
    assert reports(
        result,
        "FAIL: board o/1: cannot read it: HTTP 502",
        f"check [tracker] owner and project in {world.config}; "
        'if they are right, run "gh auth refresh -s read:project"',
    ), result.stdout


def test_a_failure_over_several_lines_prints_on_one(world):
    world.add_fault("project field-list", exit=1, stderr="error: one\nTo fix it: two\n")
    result = run_cyclix(world, "check")
    assert result.returncode == 1
    assert reports(
        result,
        "FAIL: board o/1: cannot read it: error: one To fix it: two",
        f"check [tracker] owner and project in {world.config}; "
        'if they are right, run "gh auth refresh -s read:project"',
    ), result.stdout


def test_unreadable_protection_says_to_add_a_ruleset_or_sign_in_as_an_admin(world):
    data = world.load()
    data["rules"] = []
    world.save(data)
    world.add_fault(
        "api repos/o/r/branches/main/protection",
        stderr="gh: Must have admin rights to Repository. (HTTP 403)\n",
    )
    result = run_cyclix(world, "check")
    assert result.returncode == 1
    assert reports(
        result,
        'FAIL: protection of the base branch "main": cannot read it: '
        "gh: Must have admin rights to Repository. (HTTP 403)",
        'protect "main" with a ruleset in the settings of o/r, or sign gh in as an admin of o/r',
    ), result.stdout


@pytest.mark.skipif(os.geteuid() == 0, reason="root can write anywhere")
def test_a_state_dir_that_cannot_be_written_fails(world):
    world.state_dir.chmod(0o500)
    try:
        result = run_cyclix(world, "check")
    finally:
        world.state_dir.chmod(0o700)
    assert result.returncode == 1
    assert reports(
        result,
        f"FAIL: state directory {world.state_dir}: not writable: Permission denied",
        f"make {world.state_dir} writable, or set CYCLIX_STATE_DIR to a directory you can write",
    ), result.stdout


def test_a_board_without_the_status_field_fails(world):
    text = world.config.read_text().replace('status_field = "Status"', 'status_field = "Stage"')
    world.config.write_text(text)
    result = run_cyclix(world, "check")
    assert result.returncode == 1
    assert reports(
        result,
        'FAIL: board o/1: no single-select field "Stage"',
        'add a single-select field "Stage" to the board, '
        f"or change [tracker] status_field in {world.config}",
    ), result.stdout


def test_cyclix_runs_without_argcomplete(world):
    # None in sys.modules makes the import fail, as it does when the extras group is not installed.
    code = (
        "import sys; sys.modules['argcomplete'] = None; from cyclix import cli; "
        "assert cli.argcomplete is None; sys.exit(cli.main(['--help']))"
    )
    result = run(world, [sys.executable, "-c", code])
    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith("usage: cyclix")


def test_with_argcomplete_the_shell_completes_a_command(world, tmp_path):
    completions = tmp_path / "completions"
    env = {
        **environment(world),
        "_ARGCOMPLETE": "1",
        "COMP_LINE": "cyclix ch",
        "COMP_POINT": "9",
        "_ARGCOMPLETE_STDOUT_FILENAME": str(completions),
    }
    result = subprocess.run(["cyclix"], env=env, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    assert completions.read_text() == "check "  # the space ends a whole word
