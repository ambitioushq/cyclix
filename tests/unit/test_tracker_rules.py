"""Rules of the GitHub tracker that the scenarios do not reach."""

import pytest

from cyclix import config
from cyclix.adapters.github_tracker import GitHubTracker
from cyclix.adapters.tracker import Issue, TrackerError
from cyclix.workstate import State


@pytest.fixture
def tracker(world):
    return GitHubTracker(config.load(world.config))


def calls(world, *prefix):
    return [c for c in world.calls() if c["argv"][: len(prefix)] == list(prefix)]


def test_an_item_in_an_unmapped_option_has_no_state(world, tracker):
    world.add_issue(5, state="Next")
    world.add_issue(6, state=None)
    assert tracker.items() == []
    assert tracker.item_state(5) is None


def test_the_board_ids_are_read_once_per_tracker(world, tracker):
    world.add_issue(3, state="Ready")
    world.add_issue(4, state="Ready")
    tracker.set_state(3, State.IN_PROGRESS)
    tracker.set_state(4, State.IN_PROGRESS)
    assert len(calls(world, "project", "view")) == 1
    assert len(calls(world, "project", "field-list")) == 1
    assert tracker.item_state(4) is State.IN_PROGRESS


def test_moving_an_issue_not_on_the_board_is_a_tracker_error(world, tracker):
    with pytest.raises(TrackerError, match="#9 is not on the board"):
        tracker.set_state(9, State.PARKED)


def test_moving_to_a_state_whose_option_is_gone_is_a_tracker_error(world, tracker):
    world.add_issue(3, state="In progress")
    world.remove_option("Parked")
    with pytest.raises(TrackerError, match='no Status option "Parked"'):
        tracker.set_state(3, State.PARKED)


def test_an_issue_is_read_with_its_author_and_labels(world, tracker):
    world.add_issue(3, title="Fix it", body="Steps")
    assert tracker.issue(3) == Issue(3, "Fix it", "Steps", "OPEN", "maintainer", ())
