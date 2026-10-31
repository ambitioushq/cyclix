import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from cyclix import config
from cyclix.adapters.gh import GhError
from cyclix.adapters.github_tracker import GitHubTracker
from cyclix.workstate import State

scenarios("board.feature")

STATES = {state.label: state for state in State}


@pytest.fixture
def seen():
    """What the When steps saw, for the Then steps to check."""
    return {}


@pytest.fixture
def tracker(world):
    return GitHubTracker(config.load(world.config))


# Given


@given(
    parsers.parse(
        'issues #{later:d} and #{earlier:d} in state "{state}" on the board, '
        "#{first:d} created first"
    )
)
def two_issues(world, later, earlier, state, first):
    # The board lists the later issue first, so the order must come from the tracker.
    assert first == earlier
    world.add_issue(later, state=state)
    world.add_issue(earlier, state=state)


@given(parsers.parse("a Ready item for issue #{number:d} of another repository"))
def foreign_item(world, number):
    world.add_foreign_item("other/repo", number, "Ready")


@given("a Ready draft item")
def draft_item(world):
    world.add_draft_item("A draft", "Ready")


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
def list_board(tracker, seen):
    try:
        seen["items"] = tracker.items()
    except GhError as error:
        seen["error"] = error


@when(parsers.parse("the tracker sets #{number:d} to {state}"))
def set_state(tracker, number, state):
    tracker.set_state(number, STATES[state])


# Then


@then(parsers.parse("it returns #{first:d}, then #{second:d}"))
def returns_in_order(seen, first, second):
    assert [item.issue for item in seen["items"]] == [first, second]


@then("neither is returned")
def none_returned(seen):
    assert seen["items"] == []


@then(parsers.parse('the board shows #{number:d} in the option mapped to "{key}"'))
def board_shows_mapped(world, number, key):
    mapped = getattr(config.load(world.config).tracker.states, key)
    assert world.board_state(number) == mapped


@then(parsers.parse('it raises a GhError holding exit {code:d} and "{stderr}"'))
def raised_gh_error(seen, code, stderr):
    error = seen["error"]
    assert (error.code, error.stderr) == (code, stderr)


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
