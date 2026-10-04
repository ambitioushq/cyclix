"""Rules of the GitHub tracker that the scenarios do not reach."""

import json

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


def test_the_board_is_read_once_per_tracker(world, tracker):
    world.add_issue(3, state="Ready")
    world.add_issue(4, state="Ready")
    assert [item.issue for item in tracker.items()] == [3, 4]
    assert [item.issue for item in tracker.ready_items()] == [3, 4]
    tracker.set_state(3, State.IN_PROGRESS)
    tracker.set_state(4, State.IN_PROGRESS)
    assert len(world.graphql_calls("BoardItems")) == 1
    assert len(world.graphql_calls("BoardFields")) == 1
    assert [item.state for item in tracker.items()] == [State.IN_PROGRESS] * 2
    assert len(world.graphql_calls("BoardItems")) == 1


def test_item_state_after_a_move_reads_only_that_item(world, tracker):
    world.add_issue(3, state="Ready")
    world.add_issue(4, state="Ready")
    tracker.set_state(3, State.IN_PROGRESS)
    assert tracker.item_state(3) is State.IN_PROGRESS
    assert len(world.graphql_calls("BoardItems")) == 1
    assert len(world.graphql_calls("BoardItem")) == 1


def test_item_state_sees_a_move_a_human_made_after_the_first_read(world, tracker):
    world.add_issue(3, state="In progress")
    assert [item.state for item in tracker.items()] == [State.IN_PROGRESS]
    data = world.load()
    data["board"]["items"][0]["status"] = "Done"
    world.save(data)
    assert tracker.item_state(3) is State.DONE


def test_item_state_of_an_issue_not_on_the_board_makes_no_call(world, tracker):
    world.add_issue(3, state="Ready")
    assert tracker.item_state(9) is None
    assert len(world.graphql_calls("BoardItem")) == 0


def test_item_state_of_an_item_removed_mid_pass_is_none(world, tracker):
    world.add_issue(3, state="In progress")
    tracker.items()
    data = world.load()
    data["board"]["items"] = []
    world.save(data)
    assert tracker.item_state(3) is None


def test_a_missing_status_field_is_a_tracker_error(world, tracker):
    data = world.load()
    data["board"]["status_field"]["name"] = "Stage"
    world.save(data)
    with pytest.raises(TrackerError, match='no single-select field "Status"'):
        tracker.board()


def test_a_status_field_that_is_not_single_select_is_a_tracker_error(world, tracker):
    reply = {"data": {"repositoryOwner": {"projectV2": {"id": "PVT_1", "field": {}}}}}
    world.add_fault("api graphql", exit=0, stdout=json.dumps(reply))
    with pytest.raises(TrackerError, match='no single-select field "Status"'):
        tracker.board()


def test_a_missing_project_is_a_tracker_error(world, tracker):
    reply = {"data": {"repositoryOwner": None}}
    world.add_fault("api graphql", exit=0, stdout=json.dumps(reply))
    with pytest.raises(TrackerError, match="no project 1 for owner o"):
        tracker.board()


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
