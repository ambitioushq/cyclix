"""Run Claude Code in print mode and read its JSON result.

The configured command (by default `claude -p`) runs with the stage's model,
caps and tools added, and stream-json output, which prints each message as it
comes, so a call killed at its timeout still shows the tokens and turns it used, the prompt on stdin, the worktree as its
working directory, and only the environment that adapters/environment.py allows.
The agent runs restricted and in dontAsk mode, so a tool call outside the stage's
list is refused, and the repository's own settings, hooks and MCP servers do not load. Call n in a run folder saves prompt-<n>.txt and the raw output as
answer-<n>.jsonl, so the prompt and the full answer stay in the run folder and
only the numbers reach the event log.

A failed call does not raise. It returns an AgentResult with is_error set and
the reason, so a stage handles every failure the same way.
"""

import json
import shutil
import signal
import subprocess
import time
from dataclasses import replace
from pathlib import Path

from cyclix.adapters import environment
from cyclix.adapters.agent import AgentResult
from cyclix.adapters.process import kill_group
from cyclix.adapters.readiness import Result

# How long the agent has to print its result after SIGINT, before SIGKILL.
GRACE_SECONDS = 30

# The result subtypes Claude Code ends with when a cap stops the session.
CAP_REASONS = {
    "error_max_turns": "turn cap reached",
    "error_max_budget_usd": "budget cap reached",
}


class ClaudeCode:
    def __init__(self, agent_config, timeout_seconds=None, grace_seconds=GRACE_SECONDS):
        """timeout_seconds, when given, takes the place of the config's timeout."""
        self.command = agent_config.command
        self.timeout_minutes = agent_config.timeout_minutes
        if timeout_seconds is None:
            timeout_seconds = agent_config.timeout_minutes * 60
        self.timeout_seconds = timeout_seconds
        self.grace_seconds = grace_seconds
        self.pass_env = agent_config.pass_env

    def readiness(self, config_path):
        """Is the agent command on PATH?"""
        what = f"agent command {self.command[0]}"
        if shutil.which(self.command[0]) is None:
            fix = f"install it, or change [agent] command in {config_path}"
            return [Result(what, "not on PATH", fix)]
        return [Result(what)]

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
        (run_dir / f"answer-{n}.jsonl").write_text(stdout)
        if code is None:
            # An interrupted call may still have printed its result, which holds what it cost.
            result = parse(stdout, stderr, -9, model, started)
            return replace(
                result, answer="", reason=f"timeout after {self.timeout_minutes} minutes"
            )
        return parse(stdout, stderr, code, model, started)

    def _call(self, argv, prompt, cwd, env):
        """Run the agent in its own process group, and stop the whole group on a timeout.

        On a timeout the group gets SIGINT, so Claude Code ends its turn and prints its
        result, then SIGKILL after the grace period. The exit code is None after a
        timeout, and the output is whatever the agent printed.
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
            stdout, stderr = process.communicate(prompt, timeout=self.timeout_seconds)
        except subprocess.TimeoutExpired:
            kill_group(process, signal.SIGINT)
            try:
                stdout, stderr = process.communicate(timeout=self.grace_seconds)
            except subprocess.TimeoutExpired:
                kill_group(process)
                stdout, stderr = process.communicate()
            # The agent may have exited on SIGINT and left a tool's process behind.
            kill_group(process)
            return stdout, stderr, None
        except BaseException:
            # The group does not get the terminal's SIGINT, so a Ctrl-C would leave it running.
            kill_group(process)
            process.wait()
            raise
        return stdout, stderr, process.returncode


def stage_flags(stage):
    """The flags that set the stage's model, caps and tools, and keep the agent to them.

    --tools names the built-in tools the session has at all. Each rule in the stage's
    list adds its tool, so `Bash(git commit *)` adds Bash, and a stage with no Bash
    rule has no shell. --allowedTools comes last because it takes every argument after it.
    """
    tools = list(dict.fromkeys(rule.split("(", 1)[0] for rule in stage.tools))
    return [
        "--model", stage.model, "--output-format", "stream-json", "--verbose",
        "--restricted", "--strict-mcp-config", "--tools", ",".join(tools),
        "--permission-mode", "dontAsk", "--permission-prompts", "none",
        "--max-turns", str(stage.max_turns), "--max-budget-usd", str(stage.max_budget_usd),
        "--allowedTools", *stage.tools,
    ]  # fmt: skip


def parse(stdout, stderr, code, model, started):
    """Read the stream's result line, or what the assistant lines show when there is none.

    A call that was killed, or crashed, prints no result line. Its assistant lines
    still say how many tokens and turns it used, but not what it cost.
    """
    lines = json_lines(stdout)
    out = next((line for line in reversed(lines) if line.get("type") == "result"), None)
    if out is None:
        messages = assistant_messages(lines)
        if code != 0:
            reason = f"agent exited {code}: {stderr.strip()[-500:]}"
        elif lines:
            reason = "agent printed no result"
        else:
            reason = "agent output was not JSON"
        return partial(model, reason, code, started, messages)

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


def json_lines(stdout):
    """Each line of the stream that is a JSON object. Anything else is skipped."""
    lines = []
    for text in stdout.splitlines():
        try:
            line = json.loads(text)
        except ValueError:
            continue
        if isinstance(line, dict):
            lines.append(line)
    return lines


def assistant_messages(lines):
    """The assistant messages by id. A message comes once per content block, with the same usage."""
    messages = {}
    for line in lines:
        message = line.get("message") if line.get("type") == "assistant" else None
        if isinstance(message, dict) and "id" in message:
            messages[message["id"]] = message
    return list(messages.values())


def model_used(out, requested):
    """The result has no top-level model key. The model is the one key of modelUsage.

    When modelUsage names more than one model, the requested model is the one that did the work.
    """
    models = list(out.get("modelUsage") or {})
    return models[0] if len(models) == 1 else requested


def failed(model, reason, code, started):
    return partial(model, reason, code, started, [])


def partial(model, reason, code, started, messages):
    """A call with no result line: the tokens and turns its messages show, and no cost."""
    usage = [message.get("usage") or {} for message in messages]
    return AgentResult(
        answer="",
        is_error=True,
        reason=reason,
        exit_code=code,
        model=next((m["model"] for m in reversed(messages) if m.get("model")), model),
        input_tokens=sum(u.get("input_tokens", 0) for u in usage),
        output_tokens=sum(u.get("output_tokens", 0) for u in usage),
        cost_usd=None,
        duration_ms=elapsed_ms(started),
        turns=len(messages),
    )


def elapsed_ms(started):
    return round((time.monotonic() - started) * 1000)
