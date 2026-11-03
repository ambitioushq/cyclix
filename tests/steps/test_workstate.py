import pytest
from pytest_bdd import parsers, scenarios, then, when

from cyclix import config
from cyclix.workstate import IllegalMove, Mover, State, move

scenarios("workstate.feature")

STATES = {state.label: state for state in State}


@pytest.fixture
def seen():
    """What the When steps saw, for the Then steps to check."""
    return {}


# When


@when(parsers.parse('the PR stage tries to move #{number:d} to "{state}"'))
def pr_stage_moves(world, seen, number, state):
    # No pass makes an illegal move, since each stage names a from-state the table
    # allows, so the step calls the move the way a stage does.
    from cyclix.adapters.github_tracker import GitHubTracker  # built by #9

    tracker = GitHubTracker(config.load(world.config))
    with pytest.raises(IllegalMove) as raised:
        move(tracker, number, tracker.item_state(number), STATES[state], Mover.PR)
    seen["error"] = raised.value


# Then


@then(parsers.parse("no stage runs for #{number:d}"))
def no_stage_runs(world, result, number):
    assert result.returncode == 0, result.stdout + result.stderr
    assert [e for e in world.events() if e["attributes"]["cyclix.issue.id"] == number] == []
    assert world.agent_calls() == []


@then("the move is refused")
def move_refused(seen):
    assert isinstance(seen["error"], IllegalMove)


@then(parsers.parse('the board still shows #{number:d} in "{state}"'))
def board_still_shows(world, number, state):
    assert world.board_state(number) == state
