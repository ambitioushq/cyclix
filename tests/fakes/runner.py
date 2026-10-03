"""Run Cyclix, or one of the fakes, as a subprocess against a scenario's world."""

import os
import subprocess
import sys
from pathlib import Path

from fakes.world import ENV, git_env

BIN = Path(__file__).resolve().parent / "bin"


def environment(world):
    """PATH finds the fakes first, then the virtualenv's tools, then the system."""
    env = git_env()
    path = os.pathsep.join([str(BIN), str(Path(sys.executable).parent), env["PATH"]])
    env.update(
        {
            "PATH": path,
            ENV: str(world.root),
            "CYCLIX_CONFIG": str(world.config),
            "CYCLIX_STATE_DIR": str(world.state_dir),
            "XDG_CONFIG_HOME": str(world.xdg_config),
        }
    )
    return env


def run(world, argv, cwd=None, input=None):
    return subprocess.run(
        argv,
        cwd=cwd or world.root,
        env=environment(world),
        input=input,
        capture_output=True,
        text=True,
        check=False,
    )


def run_cyclix(world, *args, cwd=None, input=None):
    return run(world, ["cyclix", *args], cwd=cwd, input=input)


def run_gh(world, *args):
    return run(world, [str(BIN / "gh"), *args])


def run_agent(world, prompt, cwd):
    return run(world, [str(BIN / "fake-agent")], cwd=cwd, input=prompt)
