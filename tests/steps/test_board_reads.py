import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from cyclix import config
from cyclix.adapters.github_tracker import GitHubTracker

scenarios("board_reads.feature")


@pytest.fixture
def seen():
    """What the When steps saw, for the Then steps to check."""
    return {}


# Given


@given(
    parsers.parse(
        'a board with issues #{first:d} in state "{first_state}" '
        'and #{second:d} in state "{second_state}"'
    )
)
def board_with_two_issues(world, first, first_state, second, second_state):
    world.add_issue(first, state=first_state)
    world.add_issue(second, state=second_state)


@given(parsers.parse("a board with {count:d} items"))
def board_with_many_items(world, count):
    for number in range(1, count + 1):
        world.add_issue(number, state="Ready")


# When


@when("the tracker lists the board")
def list_board(world, seen):
    seen["items"] = GitHubTracker(config.load(world.config)).items()


# Then


@then("the board's items are read with one paged GraphQL query")
def read_with_one_query(world):
    [call] = world.graphql_calls("BoardItems")
    assert call["argv"][:2] == ["api", "graphql"]


@then(parsers.parse('no "gh project item-list" or "gh project field-list" call is made'))
def no_project_reads(world):
    calls = [c["argv"][:2] for c in world.calls()]
    assert ["project", "item-list"] not in calls
    assert ["project", "field-list"] not in calls


@then("it reads two pages and returns all 150 items")
def reads_two_pages(world, seen):
    first, second = world.graphql_calls("BoardItems")
    assert not any(arg.startswith("after=") for arg in first["argv"])
    assert any(arg.startswith("after=") for arg in second["argv"])
    assert len(seen["items"]) == 150
