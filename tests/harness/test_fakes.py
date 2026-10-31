import json
import shlex
from pathlib import Path

from fakes.runner import run_agent, run_gh
from fakes.world import git
from pytest_bdd import given, parsers, scenarios, then, when

from cyclix.adapters.github_tracker import BOARD_ITEMS

scenarios(str(Path(__file__).parent / "fakes.feature"))


# The fake gh


@when(parsers.parse('the fake gh runs "{command}"'), target_fixture="result")
def fake_gh_runs(world, command):
    return run_gh(world, *shlex.split(command))


@when("the fake gh lists the board through the BoardItems query", target_fixture="result")
def fake_gh_lists_board(world):
    return run_gh(
        world,
        "api", "graphql",
        "-f", f"query={BOARD_ITEMS}",
        "-f", "owner=o", "-F", "number=1", "-f", "field=Status",
    )  # fmt: skip


@when(
    parsers.parse(
        'the fake gh runs "project item-edit" setting #{number:d} to the "{state}" option'
    ),
    target_fixture="result",
)
def fake_gh_moves(world, number, state):
    board = world.load()["board"]
    field = board["status_field"]
    option = next(o["id"] for o in field["options"] if o["name"] == state)
    return run_gh(
        world,
        "project", "item-edit",
        "--id", world.item_id(number),
        "--project-id", board["id"],
        "--field-id", field["id"],
        "--single-select-option-id", option,
    )  # fmt: skip


@when('the fake gh runs "pr create" twice', target_fixture="results")
def fake_gh_creates_twice(world):
    body = world.root / "body.md"
    body.write_text("Closes #3\n")
    argv = ["pr", "create", "-R", "o/r", "--head", "b", "--base", "main"]
    argv += ["--title", "T", "--body-file", str(body)]
    return [run_gh(world, *argv) for _ in range(2)]


@then(parsers.parse('the output lists one item for #{number:d} with status "{status}"'))
def lists_one_item(result, number, status):
    assert result.returncode == 0, result.stderr
    nodes = json.loads(result.stdout)["data"]["repositoryOwner"]["projectV2"]["items"]["nodes"]
    found = [(n["content"]["number"], n["fieldValueByName"]["name"]) for n in nodes]
    assert found == [(number, status)]


@then("the call is recorded")
def call_recorded(world):
    calls = world.calls()
    assert calls[-1] == {
        "argv": [
            "api", "graphql", "-f", f"query={BOARD_ITEMS}",
            "-f", "owner=o", "-F", "number=1", "-f", "field=Status",
        ],
        "exit": 0,
    }  # fmt: skip


@then(parsers.parse('the first call exits {code:d} with "{text}"'))
def first_call_fails(results, code, text):
    assert results[0].returncode == code
    assert text in results[0].stderr


@then("the second call succeeds")
def second_call_succeeds(results):
    assert results[1].returncode == 0, results[1].stderr
    assert results[1].stdout.strip().startswith("https://github.com/o/r/pull/")


# The fake agent


@given(
    parsers.parse('the agent script writes "{path}", commits it, and answers "{answer}"'),
    target_fixture="script",
)
def agent_script(world, path, answer):
    step = {
        "files": {path: "written by the fake agent\n"},
        "commit": True,
        "answer": answer,
        "input_tokens": 1234,
        "output_tokens": 567,
        "cost_usd": 0.042,
        "duration_ms": 3210,
        "num_turns": 4,
        "model": "claude-sonnet-5-5",
    }
    world.add_agent_step(**step)
    return step


@when("the fake agent runs in a git worktree", target_fixture="result")
def fake_agent_runs(world):
    clone = world.root / "clone"
    git(world.root, "clone", "-q", str(world.remote), str(clone))
    worktree = world.root / "worktree"
    git(clone, "worktree", "add", "-q", "-b", "cyclix/3-add-a-thing", str(worktree))
    world.worktree = worktree
    return run_agent(world, "Build issue #3.", cwd=worktree)


@then(parsers.parse('"{path}" is committed'))
def file_committed(world, path):
    assert git(world.worktree, "ls-tree", "--name-only", "HEAD", path) == path
    assert git(world.worktree, "status", "--porcelain") == ""


@then(
    parsers.parse(
        'the output ends in a result line with result "{answer}" and the scripted usage numbers'
    )
)
def agent_output(world, result, script, answer):
    assert result.returncode == 0, result.stderr
    out = json.loads(result.stdout.splitlines()[-1])
    assert out["type"] == "result"
    assert out["result"] == answer
    assert out["is_error"] is False
    assert out["total_cost_usd"] == script["cost_usd"]
    assert out["usage"]["input_tokens"] == script["input_tokens"]
    assert out["usage"]["output_tokens"] == script["output_tokens"]
    assert out["duration_ms"] == script["duration_ms"]
    assert out["num_turns"] == script["num_turns"]
    assert list(out["modelUsage"]) == [script["model"]]
    assert world.prompts() == ["Build issue #3."]
