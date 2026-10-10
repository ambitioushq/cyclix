"""The minimal gate: run each gate command in the worktree, in order, and stop at the first failure.

Each command's result is recorded against the head SHA, and its output is saved
as gate-<n>.txt in the run folder. The commands run code the agent wrote, so they
get the gate's allowed environment, which holds no credential. There are no fix rounds: a failure parks the item.
"""

import shlex
import subprocess
import time

from cyclix.adapters import environment
from cyclix.events import schema
from cyclix.stages.base import StageResult

# The exit code a shell gives a command it cannot find.
NOT_FOUND = 127


class Gate:
    name = "gate"

    def run(self, ctx):
        sha = ctx.codehost.head_sha(ctx.worktree)
        checks = []
        fields = {schema.HEAD_REVISION: sha, schema.GATE_CHECKS: checks}
        env = environment.for_gate(ctx.config.gate.pass_env, ctx.run_dir)
        for n, command in enumerate(ctx.config.gate.commands, 1):
            name = shlex.join(command)[: schema.MAX_STRING]
            started = time.monotonic()
            code = run(command, ctx.worktree.path, env, ctx.run_dir / f"gate-{n}.txt")
            passed = code == 0
            ctx.state.record_check(ctx.run_id, sha, name, passed)
            duration = round((time.monotonic() - started) * 1000)
            checks.append({"name": name, "passed": passed, "duration_ms": duration})
            if not passed:
                return StageResult("parked", f"gate command {n} exited {code}", fields)
        return StageResult("passed", fields=fields)


def run(command, cwd, env, output):
    """Run one command, save its stdout and stderr to output, and return its exit code."""
    try:
        done = subprocess.run(
            command, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            check=False,
        )  # fmt: skip
    except FileNotFoundError:
        output.write_text(f"command not found: {command[0]}\n")
        return NOT_FOUND
    output.write_text(done.stdout)
    return done.returncode
