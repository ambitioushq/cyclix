"""The work states and the transition table: every move the engine may make, and who makes it.

Each mover may make only its own moves, so a stage cannot put an item in a state
another mover owns. The design doc holds the same table, and a unit test checks
that the two agree.
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


class Mover(StrEnum):
    """Who in the engine moves an item. A human is not a mover: a human may make any move.

    Each stage's value is its name in `schema.STAGES`, so `Mover(stage)` finds a stage's mover.
    """

    ADMISSION = "admission"
    PLAN = "plan"
    BUILD = "build"
    GATE = "gate"
    PR = "pr"
    RECONCILER = "reconciler"
    SWEEP = "sweep"


# (from, to, mover): the only moves the engine makes.
TRANSITIONS = (
    (State.READY, State.IN_PROGRESS, Mover.ADMISSION),
    (State.IN_PROGRESS, State.IN_REVIEW, Mover.PR),
    (State.IN_PROGRESS, State.PARKED, Mover.ADMISSION),
    (State.IN_PROGRESS, State.PARKED, Mover.PLAN),
    (State.IN_PROGRESS, State.PARKED, Mover.BUILD),
    (State.IN_PROGRESS, State.PARKED, Mover.GATE),
    (State.IN_PROGRESS, State.PARKED, Mover.PR),
    (State.IN_PROGRESS, State.PARKED, Mover.RECONCILER),
    (State.IN_PROGRESS, State.PARKED, Mover.SWEEP),
    (State.IN_PROGRESS, State.NEEDS_DECISION, Mover.PLAN),
    (State.IN_REVIEW, State.DONE, Mover.RECONCILER),
    (State.IN_REVIEW, State.PARKED, Mover.RECONCILER),
)


class IllegalMove(Exception):
    """A move that is not in the transition table."""

    def __init__(self, issue, from_state, to_state, mover):
        self.issue = issue
        self.from_state = from_state
        self.to_state = to_state
        self.mover = mover
        super().__init__(
            f"{mover} may not move #{issue} from {_label(from_state)} to {_label(to_state)}"
        )


def allowed(from_state, to_state, mover):
    """Whether the mover may move an item from from_state to to_state."""
    return (from_state, to_state, mover) in TRANSITIONS


def move(tracker, issue, from_state, to_state, mover):
    """Move the issue on the tracker. A move not in the table raises IllegalMove and changes nothing."""
    if not allowed(from_state, to_state, mover):
        raise IllegalMove(issue, from_state, to_state, mover)
    tracker.set_state(issue, to_state)


def _label(state):
    return state.label if state else "no state"
