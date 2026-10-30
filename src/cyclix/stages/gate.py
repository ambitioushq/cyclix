"""The minimal gate: run each gate command in the worktree, in order, and stop at the first failure.

Each command's result is recorded against the head SHA, and its output is saved
as gate-<n>.txt in the run folder. The commands run code the agent wrote, so they
get the gate's allowed environment, which holds no credential. There are no fix rounds: a failure parks the item.
"""

import shlex
import subprocess
import time

from cyclix.adapters import environment, process
from cyclix.events import schema
from cyclix.stages.base import StageResult

# The exit code a shell gives a command it cannot find.
NOT_FOUND = 127
# A test shortens the minute so the timeout test does not take one.
SECONDS_PER_MINUTE = 60


class Gate:
    name = "gate"

    def run(self, ctx):
        sha = ctx.codehost.head_sha(ctx.worktree)
        checks = []
        fields = {schema.HEAD_REVISION: sha, schema.GATE_CHECKS: checks}
        timeout_minutes = ctx.config.gate.timeout_minutes
        env = environment.for_gate(ctx.config.gate.pass_env, ctx.run_dir, ctx.worktree.path)
        for n, command in enumerate(ctx.config.gate.commands, 1):
            name = shlex.join(command)[: schema.MAX_STRING]
            started = time.monotonic()
            output = ctx.run_dir / f"gate-{n}.txt"
            code = run(command, ctx.worktree.path, env, output, timeout_minutes)
            passed = code == 0
            ctx.state.record_check(ctx.run_id, sha, name, passed)
            duration = round((time.monotonic() - started) * 1000)
            checks.append({"name": name, "passed": passed, "duration_ms": duration})
            if code is None:
                reason = f"gate command {n} ran past {timeout_minutes} minutes"
                return StageResult("parked", reason, fields)
            if not passed:
                return StageResult("parked", f"gate command {n} exited {code}", fields)
        return StageResult("passed", fields=fields)


def run(command, cwd, env, output, timeout_minutes):
    """Run one command, save its stdout and stderr to output, and return its exit code.

    Past the timeout the command's whole process group is killed, so a test that
    started a server leaves nothing behind, and the exit code is None.
    """
    try:
        stdout, _, code = process.run(
            command, timeout_minutes * SECONDS_PER_MINUTE, cwd=cwd, env=env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )  # fmt: skip
    except FileNotFoundError:
        output.write_text(f"command not found: {command[0]}\n")
        return NOT_FOUND
    if code is None:
        stdout += f"\ncyclix: stopped after {timeout_minutes} minutes\n"
    output.write_text(stdout)
    return code
