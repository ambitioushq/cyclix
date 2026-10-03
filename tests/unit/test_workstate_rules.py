"""Rules of the transition table that the scenarios in workstate.feature do not reach."""

import re
from pathlib import Path

import pytest

from cyclix.workstate import STAGES, TRANSITIONS, IllegalMove, State, Writer, allowed, move

DOC = Path(__file__).resolve().parents[2] / "docs" / "design" / "iteration-0.md"
SECTION = "## Work states and who moves them"

# The doc's "Written by" names for each writer.
WRITERS = {
    "Runner (admission)": Writer.ADMISSION,
    "Plan stage": Writer.PLAN,
    "Any stage": Writer.ANY_STATION,
    "PR stage": Writer.PR,
    "Reconciler": Writer.RECONCILER,
    "the sweep": Writer.SWEEP,
}
STATES = {state.label: state for state in State}


def doc_transitions():
    """The engine's moves in the doc's table, as (from, to, writer). Rows a human writes are skipped."""
    text = DOC.read_text().split(SECTION, 1)[1]
    rows = re.findall(r"^\|(.+)\|$", text.split("\n\n", 2)[1], re.MULTILINE)[2:]
    found = set()
    for row in rows:
        starts, end, writers, _ = (cell.strip() for cell in row.split("|"))
        if writers.startswith("A human"):
            continue
        for start in starts.split(", "):
            for writer in re.split(r",\s*(?:or\s+)?", writers):
                found.add((STATES[start], STATES[end], WRITERS[writer]))
    return found


def test_the_doc_and_the_code_hold_the_same_table():
    assert doc_transitions() == set(TRANSITIONS)


def test_any_stage_may_park_an_item_in_progress():
    for writer in STAGES:
        assert allowed(State.IN_PROGRESS, State.PARKED, writer)


def test_the_sweep_parks_an_item_in_progress_and_moves_nothing_else():
    moves = {(a, b) for a in State for b in State if allowed(a, b, Writer.SWEEP)}
    assert moves == {(State.IN_PROGRESS, State.PARKED)}


def test_any_stage_rows_do_not_widen_other_moves():
    assert not allowed(State.IN_REVIEW, State.PARKED, Writer.PR)
    assert not allowed(State.IN_PROGRESS, State.IN_REVIEW, Writer.ANY_STATION)


class Tracker:
    def __init__(self):
        self.calls = []

    def set_state(self, issue, state):
        self.calls.append((issue, state))


def test_an_allowed_move_sets_the_state_on_the_tracker():
    tracker = Tracker()
    move(tracker, 4, State.IN_PROGRESS, State.IN_REVIEW, Writer.PR)
    assert tracker.calls == [(4, State.IN_REVIEW)]


def test_an_illegal_move_raises_and_does_not_call_the_tracker():
    tracker = Tracker()
    with pytest.raises(IllegalMove, match="pr may not move #4 from Parked to In review"):
        move(tracker, 4, State.PARKED, State.IN_REVIEW, Writer.PR)
    assert tracker.calls == []


def test_an_item_with_no_state_cannot_be_moved():
    with pytest.raises(IllegalMove, match="from no state to In progress"):
        move(Tracker(), 4, None, State.IN_PROGRESS, Writer.ADMISSION)
