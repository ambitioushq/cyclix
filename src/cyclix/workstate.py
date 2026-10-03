"""The work states and the transition table: every move the engine may make, and who makes it.

docs/design/iteration-0.md, "Work states and who moves them", holds the same table.
A unit test checks that the two agree.
"""

from enum import StrEnum


class State(StrEnum):
    """Cyclix's own work states. The values are the keys of [tracker.states] in the config."""

    READY = "ready"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    PARKED = "parked"
    NEEDS_DECISION = "needs_decision"
    DONE = "done"

    @property
    def label(self):
        """The name the design docs use, such as "In progress"."""
        return self.value.replace("_", " ").capitalize()


class Writer(StrEnum):
    """Who in the engine moves an item. A human is not a writer: a human may make any move."""

    ADMISSION = "admission"
    PLAN = "plan"
    ANY_STATION = "any"
    PR = "pr"
    RECONCILER = "reconciler"
    SWEEP = "sweep"


# The writers that are stages. A move written by ANY_STATION may be made by any of them.
STAGES = frozenset(
    {Writer.ADMISSION, Writer.PLAN, Writer.ANY_STATION, Writer.PR, Writer.RECONCILER}
)

# (from, to, writer): the only moves the engine makes.
TRANSITIONS = (
    (State.READY, State.IN_PROGRESS, Writer.ADMISSION),
    (State.IN_PROGRESS, State.IN_REVIEW, Writer.PR),
    (State.IN_PROGRESS, State.PARKED, Writer.ANY_STATION),
    (State.IN_PROGRESS, State.PARKED, Writer.SWEEP),
    (State.IN_PROGRESS, State.NEEDS_DECISION, Writer.PLAN),
    (State.IN_REVIEW, State.DONE, Writer.RECONCILER),
    (State.IN_REVIEW, State.PARKED, Writer.RECONCILER),
)


class IllegalMove(Exception):
    """A move that is not in the transition table."""

    def __init__(self, issue, from_state, to_state, writer):
        self.issue = issue
        self.from_state = from_state
        self.to_state = to_state
        self.writer = writer
        super().__init__(
            f"{writer} may not move #{issue} from {_label(from_state)} to {_label(to_state)}"
        )


def allowed(from_state, to_state, writer):
    """Whether the writer may move an item from from_state to to_state."""
    return any(
        (start, end) == (from_state, to_state)
        and (who == writer or (who is Writer.ANY_STATION and writer in STAGES))
        for start, end, who in TRANSITIONS
    )


def move(tracker, issue, from_state, to_state, writer):
    """Move the issue on the tracker. A move not in the table raises IllegalMove and changes nothing."""
    if not allowed(from_state, to_state, writer):
        raise IllegalMove(issue, from_state, to_state, writer)
    tracker.set_state(issue, to_state)


def _label(state):
    return state.label if state else "no state"
