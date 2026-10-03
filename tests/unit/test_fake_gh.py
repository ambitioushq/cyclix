"""How the fake gh behaves beyond the shape of its output.

The shape scenario (features/gh_shapes.feature) checks that its output has the
same keys as real gh, from recordings made on the sandbox.
"""

import json

import pytest
from fakes.runner import run_agent, run_gh

PROJECT = ["--owner", "o", "--format", "json"]


@pytest.fixture
def board(world):
    world.add_issue(3, title="Add a thing", state="Ready", body="Body")
    return world


def gh_json(world, *args):
    result = run_gh(world, *args)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_project_item_list_leaves_out_an_unset_status(world):
    world.add_issue(5, state=None)
    data = world.load()
    data["board"]["items"].append({"id": "PVTI_5", "issue": 5, "status": None})
    world.save(data)
    out = gh_json(world, "project", "item-list", "1", *PROJECT)
    assert "status" not in out["items"][0]


def test_issue_view_of_a_missing_issue_fails(board):
    result = run_gh(board, "issue", "view", "99", "-R", "o/r", "--json", "number")
    assert result.returncode == 1
    assert "Could not resolve" in result.stderr


def test_unknown_json_field_fails(board):
    result = run_gh(board, "issue", "view", "3", "-R", "o/r", "--json", "nope")
    assert result.returncode == 1
    assert 'Unknown JSON field: "nope"' in result.stderr


def test_unknown_flag_is_unsupported(board):
    result = run_gh(board, "issue", "view", "3", "-R", "o/r", "--web")
    assert result.returncode == 2
    assert "fake gh: unsupported command" in result.stderr


def test_pr_create_list_and_view(board, tmp_path):
    body = tmp_path / "body.md"
    body.write_text("Closes #3\n")
    create = ["pr", "create", "-R", "o/r", "--head", "cyclix/3-add-a-thing", "--base", "main"]
    create += ["--title", "Add a thing", "--body-file", str(body)]
    url = run_gh(board, *create).stdout.strip()
    assert url == "https://github.com/o/r/pull/4"

    again = run_gh(board, *create)
    assert again.returncode == 1
    assert "already exists" in again.stderr

    listed = gh_json(
        board, "pr", "list", "-R", "o/r", "--head", "cyclix/3-add-a-thing",
        "--state", "all", "--json", "number,state,url",
    )  # fmt: skip
    assert listed == [{"number": 4, "state": "OPEN", "url": url}]


def test_pr_list_counts_merged_as_closed(board):
    board.add_pr(3, state="MERGED")
    listed = gh_json(board, "pr", "list", "-R", "o/r", "--state", "closed", "--json", "state")
    assert listed == [{"state": "MERGED"}]


def test_auth_status(board):
    assert run_gh(board, "auth", "status").returncode == 0


def test_a_fault_can_return_stale_output(board):
    board.add_fault("project item-list", exit=0, stdout='{"items": [], "totalCount": 0}\n')
    out = gh_json(board, "project", "item-list", "1", *PROJECT)
    assert out == {"items": [], "totalCount": 0}
    assert len(gh_json(board, "project", "item-list", "1", *PROJECT)["items"]) == 1


def test_the_fake_agent_fails_without_a_script_entry(world, tmp_path):
    result = run_agent(world, "Anything", cwd=tmp_path)
    assert result.returncode == 2
    assert "no script entry for call 1" in result.stderr
