"""Rules of the time-limited runner: nothing it starts outlives the call."""

import signal
import subprocess

import pytest

from cyclix.adapters import process


def test_an_interrupt_kills_and_reaps_the_command(monkeypatch):
    started = []

    def interrupted(self, *args, **kwargs):
        started.append(self)
        raise KeyboardInterrupt

    monkeypatch.setattr(subprocess.Popen, "communicate", interrupted)
    with pytest.raises(KeyboardInterrupt):
        process.run(["/bin/sleep", "30"], 10)
    assert started[0].returncode == -signal.SIGKILL
