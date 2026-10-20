"""Run a command with a time limit, in its own process group.

On a timeout the whole group is killed, not only the command: a test runner's
server, or git's credential helper, would otherwise keep running and hold the
output pipe open, so waiting for the output would never end.
"""

import os
import signal
import subprocess


def run(argv, timeout_seconds, **popen):
    """Return (stdout, stderr, exit code), with exit code None after a timeout."""
    process = subprocess.Popen(argv, text=True, start_new_session=True, **popen)
    try:
        stdout, stderr = process.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        kill_group(process)
        stdout, stderr = process.communicate()
        return stdout, stderr, None
    return stdout, stderr, process.returncode


def kill_group(process, signum=signal.SIGKILL):
    try:
        os.killpg(process.pid, signum)
    # macOS refuses with EPERM, not ESRCH, when every process left in the group has exited.
    except ProcessLookupError, PermissionError:
        pass
