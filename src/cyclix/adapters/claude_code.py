"""Run Claude Code in print mode and read its JSON result.

The configured command (by default `claude -p --output-format json`) runs with
the stage's model, caps and tools added, the prompt on stdin, the worktree as its
working directory, and only the environment that adapters/environment.py allows.
The agent runs restricted and in dontAsk mode, so a tool call outside the stage's
list is refused, and the repository's own settings, hooks and MCP servers do not load. Call n in a run folder saves prompt-<n>.txt and the raw output as
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

from cyclix.adapters import environment
from cyclix.adapters.agent import AgentResult

# A test shortens the minute so the timeout scenario does not take one.
SECONDS_PER_MINUTE = 60

# The result subtypes Claude Code ends with when a cap stops the session.
CAP_REASONS = {
    "error_max_turns": "turn cap reached",
    "error_max_budget_usd": "budget cap reached",
}


class ClaudeCode:
    def __init__(self, agent_config):
        self.command = agent_config.command
        self.timeout_minutes = agent_config.timeout_minutes
        self.pass_env = agent_config.pass_env

    def run(self, prompt, cwd, stage, run_dir):
        run_dir = Path(run_dir)
        run_dir.mkdir(parents=True, exist_ok=True)
        n = len(list(run_dir.glob("prompt-*.txt"))) + 1
        (run_dir / f"prompt-{n}.txt").write_text(prompt)

        model = stage.model
        argv = [*self.command, *stage_flags(stage)]
        env = environment.for_agent(self.pass_env, run_dir, cwd)
        started = time.monotonic()
        try:
            stdout, stderr, code = self._call(argv, prompt, cwd, env)
        except FileNotFoundError:
            return failed(model, f"agent command not found: {argv[0]}", 127, started)
        (run_dir / f"answer-{n}.json").write_text(stdout)
        if code is None:
            return failed(model, f"timeout after {self.timeout_minutes} minutes", -9, started)
        return parse(stdout, stderr, code, model, started)

    def _call(self, argv, prompt, cwd, env):
        """Run the agent in its own process group, and kill the whole group on a timeout.

        The exit code is None after a timeout. The output is whatever came before it.
        """
        process = subprocess.Popen(
            argv,
            cwd=cwd,
            env=env,
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


def stage_flags(stage):
    """The flags that set the stage's model, caps and tools, and keep the agent to them.

    --tools names the built-in tools the session has at all. Each rule in the stage's
    list adds its tool, so `Bash(git commit *)` adds Bash, and a stage with no Bash
    rule has no shell. --allowedTools comes last because it takes every argument after it.
    """
    tools = list(dict.fromkeys(rule.split("(", 1)[0] for rule in stage.tools))
    return [
        "--model", stage.model,
        "--restricted", "--strict-mcp-config", "--tools", ",".join(tools),
        "--permission-mode", "dontAsk", "--permission-prompts", "none",
        "--max-turns", str(stage.max_turns), "--max-budget-usd", str(stage.max_budget_usd),
        "--allowedTools", *stage.tools,
    ]  # fmt: skip


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
        subtype = out.get("subtype")
        reason = CAP_REASONS.get(subtype) or out.get("result") or subtype or f"agent exited {code}"
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
