"""Run the gh CLI. Nothing else in the engine calls gh.

A failed call raises GhError with the exit code and stderr, so callers handle
one error type whatever went wrong.
"""

import json as jsonlib
import subprocess

from cyclix.adapters import process

# Seconds one gh call may take, unless the caller gives another. A call that runs
# longer fails as exit 124, like timeout(1).
TIMEOUT = 60


class GhError(Exception):
    def __init__(self, args, code, stderr):
        self.argv = ["gh", *args]
        self.code = code
        self.stderr = stderr.strip()
        super().__init__(f"{' '.join(self.argv[:3])} exited {code}: {self.stderr}")


def run(*args, timeout=None):
    """Run gh with these arguments and return its stdout."""
    timeout = timeout or TIMEOUT
    try:
        stdout, stderr, code = process.run(
            ["gh", *args], timeout,
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )  # fmt: skip
    except FileNotFoundError:
        raise GhError(args, 127, "gh is not on PATH") from None
    if code is None:
        raise GhError(args, 124, f"no answer after {timeout} seconds")
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
