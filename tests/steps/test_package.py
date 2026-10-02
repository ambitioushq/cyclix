import json
import os
import shlex
import subprocess
import sys
from importlib.metadata import distribution
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenario, when

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.xfail(reason="the CLI is built in #5", strict=True)
@scenario("package.feature", "The CLI prints the version")
def test_the_cli_prints_the_version():
    pass


@given("Cyclix is installed from the working tree")
def installed_from_working_tree():
    direct_url = json.loads(distribution("cyclix").read_text("direct_url.json"))
    assert direct_url["url"] == REPO_ROOT.as_uri()


@when(parsers.parse('I run "{command}"'), target_fixture="result")
def run_command(command):
    bin_dir = Path(sys.executable).parent
    env = {**os.environ, "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"}
    return subprocess.run(
        shlex.split(command), capture_output=True, text=True, env=env, check=False
    )
