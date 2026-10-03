import pytest
from pytest_bdd import parsers, scenarios, then, when

from cyclix import config
from cyclix.workstate import IllegalMove, State, Writer, allowed, move

scenarios("workstate.feature")

STATES = {state.label: state for state in State}


@pytest.fixture
def seen():
    """What the When steps saw, for the Then steps to check."""
    return {}


# When


@when(parsers.parse('the PR station tries to move #{number:d} to "{state}"'))
def pr_station_moves(world, seen, number, state):
    from cyclix.adapters.github_tracker import GitHubTracker  # built by #9

    tracker = GitHubTracker(config.load(world.config))
    with pytest.raises(IllegalMove) as raised:
        move(tracker, number, tracker.item_state(number), STATES[state], Writer.PR)
    seen["error"] = raised.value


# Then


@then(parsers.re(r"(?P<writer>\w+) may move an item from (?P<from_state>.+) to (?P<to_state>.+)"))
def writer_may_move(writer, from_state, to_state):
    assert allowed(STATES[from_state], STATES[to_state], Writer(writer))


@then(parsers.parse("no engine writer may move an item from {from_state} to {to_state}"))
def no_writer_may_move(from_state, to_state):
    movers = [w for w in Writer if allowed(STATES[from_state], STATES[to_state], w)]
    assert movers == []


@then("the move fails as illegal")
def move_failed(seen):
    assert isinstance(seen["error"], IllegalMove)


@then(parsers.parse('the board still shows #{number:d} in "{state}"'))
def board_still_shows(world, number, state):
    assert world.board_state(number) == state
