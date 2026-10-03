"""Rules of cyclix install that the scenarios in install.feature do not reach."""

import os
import subprocess
from pathlib import Path

import pytest
from fakes.runner import environment, run_cyclix

from cyclix import install


def test_a_path_with_a_space_and_a_percent_is_quoted_and_escaped():
    unit = install.service_unit("t", Path("/opt/my tools/cyclix"), Path("/etc/100% cyclix.toml"))
    assert 'ExecStart="/opt/my tools/cyclix" run --once --tenant t' in unit.splitlines()
    assert 'Environment="CYCLIX_CONFIG=/etc/100%% cyclix.toml"' in unit.splitlines()


@pytest.mark.parametrize("every", ["10min", "1h30min", "45s", "2d"])
def test_every_accepts_a_time_span(every):
    assert install.TIME_SPAN.fullmatch(every)


@pytest.mark.parametrize("every", ["10", "ten minutes", "10 min", "-5min"])
def test_every_rejects_anything_else(world, every):
    result = run_cyclix(world, "install", "--tenant", "test", "--every", every)
    assert result.returncode == 1
    assert "--every must be a time span" in result.stderr
    assert not world.units_dir.exists()


def test_install_refuses_a_config_for_another_tenant(world):
    result = run_cyclix(world, "install", "--tenant", "other")
    assert result.returncode == 1
    assert 'is the config for tenant "test", not "other"' in result.stderr


def test_a_tenant_name_that_cannot_name_a_unit_is_refused(world):
    result = run_cyclix(world, "install", "--tenant", "../x")
    assert result.returncode == 1
    assert "cannot be part of a unit name" in result.stderr


def test_installing_twice_leaves_the_same_units(world):
    assert run_cyclix(world, "install", "--tenant", "test").returncode == 0
    before = {p.name: p.read_text() for p in world.units_dir.iterdir()}
    assert run_cyclix(world, "install", "--tenant", "test").returncode == 0
    assert {p.name: p.read_text() for p in world.units_dir.iterdir()} == before


def test_a_dry_run_reports_a_different_unit_and_changes_nothing(world):
    world.units_dir.mkdir(parents=True)
    (world.units_dir / "cyclix-test.timer").write_text("[Timer]\nOnCalendar=daily\n")
    result = run_cyclix(world, "install", "--tenant", "test", "--dry-run")
    assert result.returncode == 1
    assert "-OnCalendar=daily" in result.stdout.splitlines()
    assert (world.units_dir / "cyclix-test.timer").read_text() == "[Timer]\nOnCalendar=daily\n"
    assert not world.systemctl_path.exists()


def test_uninstall_with_nothing_installed_calls_no_systemctl(world):
    result = run_cyclix(world, "uninstall", "--tenant", "test")
    assert result.returncode == 0
    assert result.stdout == 'no units installed for tenant "test"\n'
    assert not world.systemctl_path.exists()


def test_a_failing_systemctl_fails_install(world, tmp_path):
    failing = tmp_path / "failing-bin"
    failing.mkdir()
    (failing / "systemctl").write_text("#!/bin/sh\necho 'Failed to connect to bus' >&2\nexit 1\n")
    (failing / "systemctl").chmod(0o755)
    env = environment(world)
    env["PATH"] = f"{failing}{os.pathsep}{env['PATH']}"
    argv = ["cyclix", "install", "--tenant", "test"]
    result = subprocess.run(argv, env=env, capture_output=True, text=True, check=False)
    assert result.returncode == 1
    assert "systemctl --user daemon-reload exited 1: Failed to connect to bus" in result.stderr
