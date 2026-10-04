"""The minimal PR stage: push the branch, open the PR (or find the open one), move to In review.

The PR has the issue's title and the build agent's answer (pr.md) as its body.

Each step that changes the outside world sets its phase first, so the sweep can
tell after a crash how far the stage got.
"""

from cyclix.events import schema
from cyclix.stages.base import StageResult
from cyclix.workstate import State, Writer, move


def ensure_closes(body, number):
    """Put `Closes #N` first, unless the body's first non-blank line already is that."""
    line = f"Closes #{number}"
    lines = body.strip().splitlines()
    if lines and lines[0].strip() == line:
        return body.strip() + "\n"
    return f"{line}\n\n{body.strip()}".strip() + "\n"


class PR:
    name = "pr"

    def run(self, ctx):
        issue = ctx.issue
        ctx.state.set_phase(ctx.run_id, "push")
        ctx.codehost.push(ctx.worktree)
        ctx.state.set_phase(ctx.run_id, "open_pr")
        written = ctx.run_dir / "pr.md"
        body = ensure_closes(written.read_text() if written.exists() else "", issue.number)
        pr = ctx.codehost.open_pr(ctx.worktree.branch, issue.title, body)
        ctx.state.set_phase(ctx.run_id, "move")
        move(ctx.tracker, issue.number, State.IN_PROGRESS, State.IN_REVIEW, Writer.PR)
        ctx.tracker.comment(issue.number, f"{State.IN_REVIEW.label}: {pr.url}")
        fields = {
            schema.CHANGE_ID: str(pr.number),
            schema.HEAD_REVISION: ctx.codehost.head_sha(ctx.worktree),
        }
        return StageResult("passed", fields=fields)
