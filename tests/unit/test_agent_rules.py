"""Rules of the Claude Code adapter that the scenarios do not reach."""

import json

from cyclix.adapters import claude_code
from cyclix.config import Agent

STARTED = 0.0


def result_json(**fields):
    out = {
        "result": "done",
        "is_error": False,
        "usage": {"input_tokens": 10, "output_tokens": 2},
        "total_cost_usd": 0.01,
        "duration_ms": 50,
        "num_turns": 1,
        "modelUsage": {"claude-sonnet-5-5": {}},
    }
    return json.dumps({**out, **fields})


def test_the_model_is_the_one_key_of_model_usage():
    result = claude_code.parse(result_json(), "", 0, "claude-opus-5-5", STARTED)
    assert result.model == "claude-sonnet-5-5"


def test_with_several_models_in_model_usage_the_requested_model_is_kept():
    out = result_json(modelUsage={"claude-haiku-4-5-20251001": {}, "claude-opus-5-5": {}})
    assert claude_code.parse(out, "", 0, "claude-opus-5-5", STARTED).model == "claude-opus-5-5"


def test_an_error_reported_by_the_agent_carries_its_text():
    out = result_json(is_error=True, result="Credit balance is too low")
    result = claude_code.parse(out, "", 1, "m", STARTED)
    assert (result.is_error, result.reason) == (True, "Credit balance is too low")


def test_a_failed_exit_without_json_carries_stderr():
    result = claude_code.parse("", "boom\n", 3, "m", STARTED)
    assert (result.is_error, result.reason, result.exit_code) == (True, "agent exited 3: boom", 3)


def test_a_missing_command_is_an_error_not_an_exception(tmp_path):
    agent = claude_code.ClaudeCode(Agent(("no-such-agent-cmd",), "a", "b", 1))
    result = agent.run("hi", cwd=tmp_path, model="m", run_dir=tmp_path / "run")
    assert (result.is_error, result.reason) == (True, "agent command not found: no-such-agent-cmd")


def test_calls_in_one_run_folder_are_numbered(tmp_path):
    agent = claude_code.ClaudeCode(Agent(("true",), "a", "b", 1))
    for _ in range(2):
        agent.run("hi", cwd=tmp_path, model="m", run_dir=tmp_path / "run")
    assert sorted(p.name for p in (tmp_path / "run").iterdir()) == [
        "answer-1.json", "answer-2.json", "prompt-1.txt", "prompt-2.txt",
    ]  # fmt: skip
