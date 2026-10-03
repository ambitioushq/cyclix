"""The minimal build stage: one agent call in the worktree that leaves its work committed."""

from cyclix.events import schema
from cyclix.stages.base import StageResult, call_agent, prompt


class Build:
    name = "build"

    def run(self, ctx):
        issue = ctx.issue
        plan = (ctx.run_dir / "plan.md").read_text()
        text = prompt("build", number=issue.number, title=issue.title, body=issue.body, plan=plan)
        before = ctx.codehost.head_sha(ctx.worktree)
        result, fields = call_agent(ctx, text, ctx.config.agent.model_build)
        after = ctx.codehost.head_sha(ctx.worktree)
        fields[schema.HEAD_REVISION] = after
        if result.is_error:
            return StageResult("failed", f"agent: {result.reason}", fields)
        if after == before:
            return StageResult("failed", "the agent made no commit", fields)
        return StageResult("passed", fields=fields)
