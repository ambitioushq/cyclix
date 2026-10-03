"""Run Claude Code in print mode and read its JSON result.

The configured command (by default `claude -p --output-format json`) runs with
`--model <model>` added, the prompt on stdin and the worktree as its working
directory. Call n in a run folder saves prompt-<n>.txt and the raw output as
answer-<n>.json, so the prompt and the full answer stay in the run folder and
only the numbers reach the event log.

A failed call does not raise. It returns an AgentResult with is_error set and
the reason, so a stage handles every failure the same way.
"""

import json
import os
import signal
import subprocess
import time
from pathlib import Path

from cyclix.adapters.agent import AgentResult

# A test shortens the minute so the timeout scenario does not take one.
SECONDS_PER_MINUTE = 60


class ClaudeCode:
    def __init__(self, agent_config):
        self.command = agent_config.command
        self.timeout_minutes = agent_config.timeout_minutes

    def run(self, prompt, cwd, model, run_dir):
        run_dir = Path(run_dir)
        run_dir.mkdir(parents=True, exist_ok=True)
        n = len(list(run_dir.glob("prompt-*.txt"))) + 1
        (run_dir / f"prompt-{n}.txt").write_text(prompt)

        argv = [*self.command, "--model", model]
        started = time.monotonic()
        try:
            stdout, stderr, code = self._call(argv, prompt, cwd)
        except FileNotFoundError:
            return failed(model, f"agent command not found: {argv[0]}", 127, started)
        (run_dir / f"answer-{n}.json").write_text(stdout)
        if code is None:
            return failed(model, f"timeout after {self.timeout_minutes} minutes", -9, started)
        return parse(stdout, stderr, code, model, started)

    def _call(self, argv, prompt, cwd):
        """Run the agent in its own process group, and kill the whole group on a timeout.

        The exit code is None after a timeout. The output is whatever came before it.
        """
        process = subprocess.Popen(
            argv,
            cwd=cwd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
        try:
            stdout, stderr = process.communicate(
                prompt, timeout=self.timeout_minutes * SECONDS_PER_MINUTE
            )
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            stdout, stderr = process.communicate()
            return stdout, stderr, None
        return stdout, stderr, process.returncode


def parse(stdout, stderr, code, model, started):
    try:
        out = json.loads(stdout)
    except ValueError:
        out = None
    if not isinstance(out, dict):
        if code != 0:
            return failed(model, f"agent exited {code}: {stderr.strip()[-500:]}", code, started)
        return failed(model, "agent output was not JSON", code, started)

    usage = out.get("usage") or {}
    is_error = bool(out.get("is_error")) or code != 0
    reason = ""
    if is_error:
        reason = out.get("result") or out.get("subtype") or f"agent exited {code}"
    return AgentResult(
        answer=out.get("result") or "",
        is_error=is_error,
        reason=reason,
        exit_code=code,
        model=model_used(out, model),
        input_tokens=usage.get("input_tokens", 0),
        output_tokens=usage.get("output_tokens", 0),
        cost_usd=out.get("total_cost_usd", 0.0),
        duration_ms=out.get("duration_ms", elapsed_ms(started)),
        turns=out.get("num_turns", 0),
    )


def model_used(out, requested):
    """The result has no top-level model key. The model is the one key of modelUsage.

    When modelUsage names more than one model, the requested model is the one that did the work.
    """
    models = list(out.get("modelUsage") or {})
    return models[0] if len(models) == 1 else requested


def failed(model, reason, code, started):
    return AgentResult(
        answer="",
        is_error=True,
        reason=reason,
        exit_code=code,
        model=model,
        input_tokens=0,
        output_tokens=0,
        cost_usd=0.0,
        duration_ms=elapsed_ms(started),
        turns=0,
    )


def elapsed_ms(started):
    return round((time.monotonic() - started) * 1000)
