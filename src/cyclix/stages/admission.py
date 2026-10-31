"""The admission stage: move the claimed item to In progress, read the issue, make the worktree.

The runner picks the oldest Ready item on the board and claims it before this
stage runs. Admission reads only the issue's own fields, never its comments.
It is the one stage that runs before a worktree exists, so it fills in the
issue and the worktree on the run's context for the stages after it.
When the config names an instruction folder, admission copies its files into
the worktree, and parks the item if the repository tracks one of their paths.
"""

from cyclix.adapters.github_codehost import slug
from cyclix.stages.base import StageResult
from cyclix.workstate import State, Writer, move


class Admission:
    name = "admission"

    def run(self, ctx):
        ctx.state.set_phase(ctx.run_id, "move")
        move(ctx.tracker, ctx.number, State.READY, State.IN_PROGRESS, Writer.ADMISSION)
        ctx.issue = ctx.tracker.issue(ctx.number)
        ctx.state.set_phase(ctx.run_id, "worktree")
        ctx.worktree = ctx.codehost.new_worktree(ctx.number, slug(ctx.issue.title), ctx.run_dir)
        if (instructions := ctx.config.agent.instructions) is not None:
            ctx.state.set_phase(ctx.run_id, "instructions")
            if tracked := ctx.codehost.add_local_files(ctx.worktree, instructions.files):
                reason = (
                    f"the repository tracks {', '.join(tracked)}, "
                    "which the instruction folder also holds"
                )
                return StageResult("parked", reason)
        return StageResult("passed")
