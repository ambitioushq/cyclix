"""The minimal PR stage: push the branch, open the PR (or find the open one), move to In review.

Each step that changes the outside world sets its phase first, so the sweep can
tell after a crash how far the stage got.
"""

from cyclix.events import schema
from cyclix.stages.base import StageResult
from cyclix.workstate import State, Writer, move


class PR:
    name = "pr"

    def run(self, ctx):
        issue = ctx.issue
        ctx.state.set_phase(ctx.run_id, "push")
        ctx.codehost.push(ctx.worktree)
        ctx.state.set_phase(ctx.run_id, "open_pr")
        plan = (ctx.run_dir / "plan.md").read_text()
        body = f"Closes #{issue.number}\n\n{plan}"
        pr = ctx.codehost.open_pr(ctx.worktree.branch, f"{issue.title} (#{issue.number})", body)
        ctx.state.set_phase(ctx.run_id, "move")
        move(ctx.tracker, issue.number, State.IN_PROGRESS, State.IN_REVIEW, Writer.PR)
        ctx.tracker.comment(issue.number, f"{State.IN_REVIEW.label}: {pr.url}")
        fields = {
            schema.CHANGE_ID: str(pr.number),
            schema.HEAD_REVISION: ctx.codehost.head_sha(ctx.worktree),
        }
        return StageResult("passed", fields=fields)
