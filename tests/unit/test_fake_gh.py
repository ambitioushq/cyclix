"""How the fake gh behaves beyond the shape of its output.

The shape scenario (features/gh_shapes.feature) checks that its output has the
same keys as real gh, from recordings made on the sandbox.
"""

import json

import pytest
from fakes.runner import run_agent, run_gh

from cyclix.adapters.github_tracker import BOARD_ITEMS

VARIABLES = ["-f", "owner=o", "-F", "number=1", "-f", "field=Status"]
ITEMS = ["api", "graphql", "-f", f"query={BOARD_ITEMS}", *VARIABLES]


def board_items(world, *extra):
    """The `items` connection of a BoardItems call."""
    out = gh_json(world, *ITEMS, *extra)
    return out["data"]["repositoryOwner"]["projectV2"]["items"]


@pytest.fixture
def board(world):
    world.add_issue(3, title="Add a thing", state="Ready", body="Body")
    return world


def gh_json(world, *args):
    result = run_gh(world, *args)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_board_items_has_a_null_status_when_unset(world):
    world.add_issue(5, state=None)
    data = world.load()
    data["board"]["items"].append({"id": "PVTI_5", "issue": 5, "status": None})
    world.save(data)
    [node] = board_items(world)["nodes"]
    assert node["fieldValueByName"] is None


def test_board_items_pages_by_cursor(world):
    for number in range(1, 151):
        world.add_issue(number, state="Ready")
    first = board_items(world)
    assert len(first["nodes"]) == 100
    assert first["pageInfo"]["hasNextPage"] is True
    after = first["pageInfo"]["endCursor"]
    second = board_items(world, "-f", f"after={after}")
    assert [n["content"]["number"] for n in second["nodes"]] == list(range(101, 151))
    assert second["pageInfo"]["hasNextPage"] is False


def test_an_unknown_graphql_operation_is_unsupported(board):
    result = run_gh(board, "api", "graphql", "-f", "query=query Other { viewer { login } }")
    assert result.returncode == 2
    assert "fake gh: unsupported command" in result.stderr


def test_a_graphql_call_for_another_project_fails(board):
    other = ["-f", f"query={BOARD_ITEMS}", "-f", "owner=o", "-F", "number=2", "-f", "field=Status"]
    result = run_gh(board, "api", "graphql", *other)
    assert result.returncode == 1
    assert "Could not resolve to a ProjectV2" in result.stderr


def test_board_item_reads_one_item_and_null_for_a_missing_one(board):
    query = "query BoardItem($item: ID!, $field: String!) { node(id: $item) { id } }"
    args = ["api", "graphql", "-f", f"query={query}", "-f", "field=Status"]
    found = gh_json(board, *args, "-f", "item=PVTI_3")
    assert found["data"]["node"] == {"fieldValueByName": {"name": "Ready"}}
    missing = gh_json(board, *args, "-f", "item=PVTI_99")
    assert missing["data"]["node"] is None


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
    empty = {"data": {"repositoryOwner": {"projectV2": {"items": {"nodes": []}}}}}
    board.add_fault("api graphql", exit=0, stdout=json.dumps(empty) + "\n")
    assert gh_json(board, *ITEMS) == empty
    assert len(board_items(board)["nodes"]) == 1


def test_the_fake_agent_fails_without_a_script_entry(world, tmp_path):
    result = run_agent(world, "Anything", cwd=tmp_path)
    assert result.returncode == 2
    assert "no script entry for call 1" in result.stderr
