"""The minimal reconciler: carry an item In review to where its PR ended up.

It finds the PR by the item's branch. Merged moves the item to Done. Closed
without merging parks it. An open PR, or none at all, leaves it In review.
"""

from cyclix.adapters.github_codehost import branch_name, slug
from cyclix.events import schema
from cyclix.stages.base import StageResult
from cyclix.workstate import State, Writer, move

name = "reconciler"

CLOSED_REASON = "PR closed without merge"


def ended_pr(codehost, item):
    """The item's PR if it has merged or closed, else None."""
    pr = codehost.find_pr(branch_name(item.issue, slug(item.title)))
    if pr is None or pr.state == "open":
        return None
    return pr


def reconcile(state, tracker, run_id, item, pr):
    """Move the item to match its ended PR. A park says why in a comment on the issue."""
    to, reason = (
        (State.DONE, "PR merged") if pr.state == "merged" else (State.PARKED, CLOSED_REASON)
    )
    state.set_phase(run_id, "move")
    move(tracker, item.issue, State.IN_REVIEW, to, Writer.RECONCILER)
    if to is State.PARKED:
        tracker.comment(item.issue, f"{to.label}: {reason}")
    fields = {
        schema.CHANGE_ID: str(pr.number),
        schema.HEAD_NAME: branch_name(item.issue, slug(item.title)),
    }
    return StageResult("passed", reason, fields)
