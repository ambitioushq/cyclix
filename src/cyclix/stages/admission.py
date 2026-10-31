"""The minimal admission stage: move the claimed item to In progress, read the issue, make the worktree.

The runner picks the oldest Ready item on the board and claims it before this
stage runs. Admission reads only the issue's own fields, never its comments.
It is the one stage that runs before a RunContext exists, so it makes one.
When the config names an instruction folder, admission copies its files into
the worktree, and parks the item if the repository tracks one of their paths.
"""

from cyclix.adapters.github_codehost import slug
from cyclix.events import schema
from cyclix.stages.base import RunContext, StageResult
from cyclix.workstate import State, Writer, move

name = "admission"


def admit(config, state, tracker, codehost, agent, issue, run_id, run_dir):
    """Return the stage's result and the RunContext the later stages share."""
    state.set_phase(run_id, "move")
    move(tracker, issue, State.READY, State.IN_PROGRESS, Writer.ADMISSION)
    details = tracker.issue(issue)
    state.set_phase(run_id, "worktree")
    worktree = codehost.new_worktree(issue, slug(details.title), run_dir)
    ctx = RunContext(
        config=config, state=state, tracker=tracker, codehost=codehost, agent=agent,
        run_id=run_id, issue=details, worktree=worktree, run_dir=run_dir,
    )  # fmt: skip
    fields = {schema.HEAD_NAME: worktree.branch}
    if (instructions := config.agent.instructions) is not None:
        state.set_phase(run_id, "instructions")
        if tracked := codehost.add_local_files(worktree, instructions.files):
            reason = (
                f"the repository tracks {', '.join(tracked)}, "
                "which the instruction folder also holds"
            )
            return StageResult("parked", reason, fields), ctx
    return StageResult("passed", fields=fields), ctx
