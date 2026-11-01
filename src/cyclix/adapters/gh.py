"""Run the gh CLI. Nothing else in the engine calls gh.

A failed call raises GhError with the exit code and stderr, so callers handle
one error type whatever went wrong.
"""

import json as jsonlib
import logging
import shutil
import subprocess
import time

from cyclix.adapters import process
from cyclix.adapters.readiness import Prerequisite, Result

logger = logging.getLogger(__name__)

# Seconds one gh call may take, unless the caller gives another. A call that runs
# longer fails as exit 124, like timeout(1).
TIMEOUT = 60


class GhError(Exception):
    def __init__(self, args, code, stderr):
        self.argv = ["gh", *args]
        self.code = code
        self.stderr = stderr.strip()
        super().__init__(f"{name(args)} exited {code}: {self.stderr}")


def name(args):
    """Name a call by its first three words. The rest can hold a body."""
    return " ".join(["gh", *args][:3])


def run(*args, timeout=None):
    """Run gh with these arguments and return its stdout."""
    timeout = timeout or TIMEOUT
    started = time.monotonic()
    try:
        stdout, stderr, code = process.run(
            ["gh", *args], timeout,
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )  # fmt: skip
    except FileNotFoundError:
        code, stderr = 127, "gh is not on PATH"
    if code is None:
        code, stderr = 124, f"no answer after {timeout} seconds"
    ms = round((time.monotonic() - started) * 1000)
    logger.debug("%s exited %d after %d ms", name(args), code, ms)
    if code != 0:
        raise GhError(args, code, stderr)
    return stdout


def json(*args):
    """Run gh and parse its stdout as JSON."""
    out = run(*args)
    try:
        return jsonlib.loads(out)
    except ValueError:
        raise GhError(args, 0, f"output is not JSON: {out[:200]}") from None


def signed_in():
    """Is gh on PATH and signed in?"""
    if shutil.which("gh") is None:
        return Result("gh", "not on PATH", "install gh, the GitHub CLI, and put it on PATH")
    try:
        run("auth", "status")
    except GhError:
        return Result("gh", "not signed in", 'run "gh auth login"')
    return Result("gh is signed in")


# Every adapter that calls gh needs this check, so cyclix check runs it once for them all.
SIGNED_IN = Prerequisite("gh signed in", signed_in)
