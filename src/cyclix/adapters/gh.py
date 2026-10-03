"""Run the gh CLI. Nothing else in the engine calls gh.

A failed call raises GhError with the exit code and stderr, so callers handle
one error type whatever went wrong.
"""

import json as jsonlib
import subprocess


class GhError(Exception):
    def __init__(self, args, code, stderr):
        self.argv = ["gh", *args]
        self.code = code
        self.stderr = stderr.strip()
        super().__init__(f"{' '.join(self.argv[:3])} exited {code}: {self.stderr}")


def run(*args):
    """Run gh with these arguments and return its stdout."""
    try:
        done = subprocess.run(["gh", *args], capture_output=True, text=True, check=False)
    except FileNotFoundError:
        raise GhError(args, 127, "gh is not on PATH") from None
    if done.returncode != 0:
        raise GhError(args, done.returncode, done.stderr)
    return done.stdout


def json(*args):
    """Run gh and parse its stdout as JSON."""
    out = run(*args)
    try:
        return jsonlib.loads(out)
    except ValueError:
        raise GhError(args, 0, f"output is not JSON: {out[:200]}") from None
