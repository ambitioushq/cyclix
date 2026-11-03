"""Rules of the transition table that the scenarios in workstate.feature do not reach."""

import re
from pathlib import Path

import pytest

from cyclix.events import schema
from cyclix.workstate import TRANSITIONS, IllegalMove, Mover, State, allowed, move

DOC = Path(__file__).resolve().parents[2] / "docs/src/content/docs/concepts/how-cyclix-works.md"
SECTION = "## The work states and who moves them"

# The doc's "Moved by" names for each mover, in lower case.
MOVERS = {
    "admission stage": Mover.ADMISSION,
    "plan stage": Mover.PLAN,
    "build stage": Mover.BUILD,
    "gate stage": Mover.GATE,
    "pr stage": Mover.PR,
    "reconciler": Mover.RECONCILER,
    "the sweep": Mover.SWEEP,
}
STATES = {state.label: state for state in State}


def doc_transitions():
    """The engine's moves in the doc's table, as (from, to, mover). Rows a human moves are skipped."""
    text = DOC.read_text().split(SECTION, 1)[1]
    rows = re.findall(r"^\|(.+)\|$", text.split("\n\n", 2)[1], re.MULTILINE)[2:]
    found = set()
    for row in rows:
        starts, end, movers, _ = (cell.strip() for cell in row.split("|"))
        if movers.startswith("A human"):
            continue
        for start in starts.split(", "):
            for mover in re.split(r",\s*(?:or\s+)?", movers):
                found.add((STATES[start], STATES[end], MOVERS[mover.lower()]))
    return found


def test_the_doc_and_the_code_hold_the_same_table():
    assert doc_transitions() == set(TRANSITIONS)


def test_every_stage_may_park_an_item_in_progress():
    for stage in schema.STAGES:
        assert allowed(State.IN_PROGRESS, State.PARKED, Mover(stage))


def test_the_sweep_parks_an_item_in_progress_and_moves_nothing_else():
    moves = {(a, b) for a in State for b in State if allowed(a, b, Mover.SWEEP)}
    assert moves == {(State.IN_PROGRESS, State.PARKED)}


def test_the_park_rows_do_not_widen_other_moves():
    assert not allowed(State.IN_REVIEW, State.PARKED, Mover.PR)
    assert not allowed(State.IN_PROGRESS, State.IN_REVIEW, Mover.BUILD)


class Tracker:
    def __init__(self):
        self.calls = []

    def set_state(self, issue, state):
        self.calls.append((issue, state))


def test_an_allowed_move_sets_the_state_on_the_tracker():
    tracker = Tracker()
    move(tracker, 4, State.IN_PROGRESS, State.IN_REVIEW, Mover.PR)
    assert tracker.calls == [(4, State.IN_REVIEW)]


def test_an_illegal_move_raises_and_does_not_call_the_tracker():
    tracker = Tracker()
    with pytest.raises(IllegalMove, match="pr may not move #4 from Parked to In review"):
        move(tracker, 4, State.PARKED, State.IN_REVIEW, Mover.PR)
    assert tracker.calls == []


def test_an_item_with_no_state_cannot_be_moved():
    with pytest.raises(IllegalMove, match="from no state to In progress"):
        move(Tracker(), 4, None, State.IN_PROGRESS, Mover.ADMISSION)
