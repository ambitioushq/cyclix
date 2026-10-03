import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from cyclix import config
from cyclix.adapters.gh import GhError
from cyclix.adapters.github_tracker import GitHubTracker
from cyclix.workstate import State

scenarios("tracker.feature")

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


@given(parsers.parse("{count:d} items on the board"))
def many_items(world, count):
    for number in range(1, count + 1):
        world.add_issue(number, state="Ready")


# When


@when("the tracker lists Ready items")
def list_ready(tracker, seen):
    try:
        seen["items"] = tracker.ready_items()
    except GhError as error:
        seen["error"] = error


@when("the tracker lists all items")
def list_all(tracker, seen):
    seen["items"] = tracker.items()


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


@then(parsers.parse("it returns {count:d} items"))
def returns_count(seen, count):
    assert len(seen["items"]) == count
