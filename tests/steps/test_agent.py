import json
import os
import shlex
import time

import pytest
from conftest import name_list
from fakes.runner import environment
from pytest_bdd import given, parsers, scenarios, then, when

from cyclix import config
from cyclix.adapters import claude_code

scenarios("agent.feature")

PROMPT = "Write a plan for issue #3."


@pytest.fixture
def fake_env(world, monkeypatch):
    for key, value in environment(world).items():
        monkeypatch.setenv(key, value)


# Given


@given(
    parsers.parse(
        'the agent answers "{answer}" with {input_tokens:d} input tokens, '
        "{output_tokens:d} output tokens and cost {cost:g}"
    )
)
def agent_answers_with_numbers(world, answer, input_tokens, output_tokens, cost):
    world.add_agent_step(
        answer=answer, input_tokens=input_tokens, output_tokens=output_tokens, cost_usd=cost
    )


@given("the agent takes longer than the timeout")
def agent_takes_too_long(world, monkeypatch):
    # The test config's timeout is 1 minute. Here a minute lasts one second; the agent sleeps 30.
    monkeypatch.setattr(claude_code, "SECONDS_PER_MINUTE", 1)
    world.add_agent_step(sleep_seconds=30)


@given(parsers.parse('the agent stops with subtype "{subtype}"'))
def agent_stops(world, subtype):
    world.add_agent_step(subtype=subtype, exit=1)


@given(parsers.parse('the engine\'s git config names the user "{name}" with email "{email}"'))
def engine_git_identity(world, fake_env, monkeypatch, tmp_path, name, email):
    gitconfig = tmp_path / "gitconfig"
    gitconfig.write_text(f"[user]\n\tname = {name}\n\temail = {email}\n")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(gitconfig))
    for key in ("AUTHOR", "COMMITTER"):
        monkeypatch.delenv(f"GIT_{key}_NAME", raising=False)
        monkeypatch.delenv(f"GIT_{key}_EMAIL", raising=False)


@given(parsers.parse('the agent prints "{text}" and exits {code:d}'))
def agent_prints(world, text, code):
    world.add_agent_step(stdout=text + "\n", exit=code)


# When


@when("the adapter runs a prompt", target_fixture="result")
def adapter_runs(world, fake_env):
    return run_stage(world, "plan")


@when(parsers.parse("the adapter runs a prompt for the {stage} stage"), target_fixture="result")
def adapter_runs_stage(world, fake_env, stage):
    return run_stage(world, stage)


def run_stage(world, stage):
    agent_config = config.load(world.config).agent
    agent = claude_code.ClaudeCode(agent_config)
    work = world.root / "work"
    work.mkdir()
    return agent.run(PROMPT, work, getattr(agent_config, stage), world.root / "run")


# Then


@then(parsers.parse('the result\'s answer is "{answer}"'))
def answer_is(result, answer):
    assert not result.is_error, result.reason
    assert result.answer == answer


@then(
    parsers.parse("its tokens are {input_tokens:d} and {output_tokens:d} and its cost is {cost:g}")
)
def numbers_are(result, input_tokens, output_tokens, cost):
    assert (result.input_tokens, result.output_tokens) == (input_tokens, output_tokens)
    assert result.cost_usd == cost


@then("the prompt and the raw output are saved in the run folder")
def saved_in_run_folder(world):
    run_dir = world.root / "run"
    assert (run_dir / "prompt-1.txt").read_text() == PROMPT
    assert json.loads((run_dir / "answer-1.json").read_text())["result"] == "plan written"


@then(parsers.parse('the result is an error with reason "{reason}"'))
def error_with_reason(result, reason):
    assert result.is_error
    assert result.reason == reason


@then("no agent process is left running")
def nothing_left_running(world):
    pids = world.agent_pids()
    assert len(pids) == 2, "the fake agent and its child should both be recorded"
    # A killed grandchild is reaped by init, not by us, so give that a moment.
    deadline = time.monotonic() + 2
    while (running := [pid for pid in pids if alive(pid)]) and time.monotonic() < deadline:
        time.sleep(0.05)
    assert running == []


def alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


def last_call(world):
    return world.agent_calls()[-1]


@then(parsers.parse('the agent was started with "{args}"'))
def started_with(world, args):
    argv, want = last_call(world)["argv"], shlex.split(args)
    starts = range(len(argv) - len(want) + 1)
    assert any(argv[i : i + len(want)] == want for i in starts), argv


@then(parsers.parse("the agent's environment lacks {names}"))
def environment_lacks(world, names):
    env = last_call(world)["env"]
    assert [name for name in name_list(names) if name in env] == []


@then(parsers.parse("the agent's environment holds {names}"))
def environment_holds(world, names):
    env = last_call(world)["env"]
    assert [name for name in name_list(names) if name not in env] == []


@then(
    parsers.parse(
        'the agent\'s environment sets {first} to "{first_value}" and {second} to "{second_value}"'
    )
)
def environment_sets(world, first, first_value, second, second_value):
    env = last_call(world)["env"]
    assert (env.get(first), env.get(second)) == (first_value, second_value)


@then(parsers.parse("the agent's environment sets {name} to the null device"))
def environment_sets_null(world, name):
    assert last_call(world)["env"].get(name) == os.devnull


@then("the agent's GH_CONFIG_DIR is an empty folder")
def gh_config_dir_empty(world):
    folder = last_call(world)["env"]["GH_CONFIG_DIR"]
    assert os.path.isdir(folder)
    assert os.listdir(folder) == []
