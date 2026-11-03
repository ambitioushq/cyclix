import pytest
from pytest_bdd import parsers, scenarios, then, when

from cyclix import config
from cyclix.workstate import IllegalMove, Mover, State, allowed, move

scenarios("workstate.feature")

STATES = {state.label: state for state in State}


@pytest.fixture
def seen():
    """What the When steps saw, for the Then steps to check."""
    return {}


# When


@when(parsers.parse('the PR stage tries to move #{number:d} to "{state}"'))
def pr_stage_moves(world, seen, number, state):
    from cyclix.adapters.github_tracker import GitHubTracker  # built by #9

    tracker = GitHubTracker(config.load(world.config))
    with pytest.raises(IllegalMove) as raised:
        move(tracker, number, tracker.item_state(number), STATES[state], Mover.PR)
    seen["error"] = raised.value


# Then


@then(parsers.re(r"(?P<mover>\w+) may move an item from (?P<from_state>.+) to (?P<to_state>.+)"))
def mover_may_move(mover, from_state, to_state):
    assert allowed(STATES[from_state], STATES[to_state], Mover(mover))


@then(parsers.parse("no engine mover may move an item from {from_state} to {to_state}"))
def no_mover_may_move(from_state, to_state):
    movers = [m for m in Mover if allowed(STATES[from_state], STATES[to_state], m)]
    assert movers == []


@then("the move fails as illegal")
def move_failed(seen):
    assert isinstance(seen["error"], IllegalMove)


@then(parsers.parse('the board still shows #{number:d} in "{state}"'))
def board_still_shows(world, number, state):
    assert world.board_state(number) == state
